"""Cliente HTTP para a API v2 do ClickUp.

Padres críticos documentados no briefing:
- Time entries sempre consultados pela tarefa-mãe, nunca pela subtarefa.
- Não usar endpoint /team/{id}/time_entries com assignee.
- Paginação cursor-based em search_tasks.
"""
from __future__ import annotations

import os
import time
import logging
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.clickup.com/api/v2"
_MAX_RETRIES = 4
_BACKOFF = [2, 4, 8, 16]  # segundos


class ClickUpClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ["CLICKUP_API_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update({"Authorization": self.token})

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        for attempt, wait in enumerate([0] + _BACKOFF):
            if wait:
                time.sleep(wait)
            try:
                r = self.session.get(url, params=params, timeout=30)
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", wait or 2))
                    log.warning("Rate limited. Aguardando %ds", retry_after)
                    time.sleep(retry_after)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as exc:
                if attempt == len(_BACKOFF):
                    raise
                log.warning("Tentativa %d falhou (%s). Retry em %ds", attempt + 1, exc, _BACKOFF[attempt])
        raise RuntimeError(f"Falha após {_MAX_RETRIES} tentativas: {url}")

    # ------------------------------------------------------------------
    # Hierarquia
    # ------------------------------------------------------------------

    def get_workspace_hierarchy(self) -> list[dict]:
        """Retorna spaces com folders e lists aninhados (max_depth=2)."""
        data = self._get("/team")
        teams = data.get("teams", [])
        if not teams:
            return []
        team_id = teams[0]["id"]

        spaces_data = self._get(f"/team/{team_id}/space", {"archived": "false"})
        spaces = spaces_data.get("spaces", [])

        hierarchy = []
        for space in spaces:
            space_id = space["id"]
            folders_data = self._get(f"/space/{space_id}/folder", {"archived": "false"})
            folders = folders_data.get("folders", [])

            enriched_folders = []
            for folder in folders:
                folder_id = folder["id"]
                lists_data = self._get(f"/folder/{folder_id}/list", {"archived": "false"})
                folder["lists"] = lists_data.get("lists", [])
                enriched_folders.append(folder)

            # Lists direto no space (sem folder)
            spacelists_data = self._get(f"/space/{space_id}/list", {"archived": "false"})
            space["folders"] = enriched_folders
            space["direct_lists"] = spacelists_data.get("lists", [])
            hierarchy.append(space)

        return hierarchy

    # ------------------------------------------------------------------
    # Tarefas
    # ------------------------------------------------------------------

    def get_tasks_in_list(self, list_id: str) -> list[dict]:
        """Busca todas as tarefas de uma lista com paginação."""
        tasks: list[dict] = []
        page = 0
        while True:
            data = self._get(
                f"/list/{list_id}/task",
                {
                    "archived": "false",
                    "include_closed": "true",
                    "subtasks": "false",   # apenas tarefas-mãe
                    "page": page,
                },
            )
            batch = data.get("tasks", [])
            tasks.extend(batch)
            if len(batch) < 100 or data.get("last_page"):
                break
            page += 1
        return tasks

    def get_task(self, task_id: str) -> dict:
        """Detalhes de uma tarefa (custom fields, assignees, time_spent)."""
        return self._get(f"/task/{task_id}", {"custom_task_ids": "false", "include_subtasks": "false"})

    # ------------------------------------------------------------------
    # Time Entries
    # ------------------------------------------------------------------

    def get_time_entries(
        self,
        task_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Time entries de uma tarefa-mãe (inclui entries de subtarefas).

        Datas no formato 'YYYY-MM-DD'. A API espera Unix ms.
        IMPORTANTE: Consultar sempre pela tarefa-mãe — IDs de subtarefas
        podem retornar erro.
        """
        params: dict = {}
        if start_date:
            params["start_date"] = _to_unix_ms(start_date)
        if end_date:
            params["end_date"] = _to_unix_ms(end_date, end_of_day=True)

        data = self._get(f"/task/{task_id}/time", params)
        return data.get("data", [])


# ------------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------------

def _to_unix_ms(date_str: str, end_of_day: bool = False) -> int:
    """Converte 'YYYY-MM-DD' para Unix timestamp em milissegundos."""
    from datetime import datetime, timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
