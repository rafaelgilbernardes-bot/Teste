"""Cliente HTTP para a API v2 do ClickUp."""
from __future__ import annotations

import os
import time
import logging
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.clickup.com/api/v2"
_BACKOFF = [2, 4, 8, 16]


class ClickUpClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ["CLICKUP_API_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update({"Authorization": self.token})

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
                log.warning("Tentativa %d falhou (%s). Retry em %ds",
                            attempt + 1, exc, _BACKOFF[attempt])
        raise RuntimeError(f"Falha após {len(_BACKOFF)} tentativas: {url}")

    def get_team_id(self) -> str:
        """Detecta o workspace correto.

        Se CLICKUP_TEAM_ID estiver definido, usa ele.
        Caso contrário, lista todos os workspaces do token e usa o que
        tiver um space chamado 'Consultivo' (padrão CFPazziniGil).
        Se não encontrar, usa o primeiro da lista.
        """
        if team_id_env := os.environ.get("CLICKUP_TEAM_ID"):
            log.info("Usando CLICKUP_TEAM_ID do ambiente: %s", team_id_env)
            return team_id_env

        data = self._get("/team")
        teams = data.get("teams", [])
        if not teams:
            raise ValueError("Nenhum workspace encontrado para este token")

        log.info("Workspaces acessíveis com este token:")
        for t in teams:
            log.info("  - %s (ID: %s)", t.get("name", "?"), t["id"])

        # Procura o workspace que tem space 'Consultivo'
        for team in teams:
            try:
                spaces = self._get(
                    f"/team/{team['id']}/space", {"archived": "false"}
                ).get("spaces", [])
                space_names = [s["name"] for s in spaces]
                log.info("  Workspace '%s' tem spaces: %s",
                         team.get("name"), space_names)
                if "Consultivo" in space_names:
                    log.info("  >>> Workspace correto encontrado: %s (ID: %s)",
                             team.get("name"), team["id"])
                    return str(team["id"])
            except Exception as e:
                log.warning("  Não foi possível acessar workspace %s: %s",
                            team["id"], e)

        log.warning("Workspace com 'Consultivo' não encontrado. Usando o primeiro.")
        return str(teams[0]["id"])

    def get_all_lists(self, team_id: str) -> list[dict]:
        """Retorna lista plana de todas as lists do workspace."""
        spaces_data = self._get(
            f"/team/{team_id}/space", {"archived": "false"}
        )
        spaces = spaces_data.get("spaces", [])
        log.info("%d spaces encontrados: %s",
                 len(spaces), [s["name"] for s in spaces])

        all_lists: list[dict] = []
        for space in spaces:
            space_id = space["id"]
            space_name = space["name"]

            folders_data = self._get(
                f"/space/{space_id}/folder", {"archived": "false"}
            )
            for folder in folders_data.get("folders", []):
                # Pular pastas internas
                if folder.get("name", "") == "Interno":
                    continue
                folder_id = folder["id"]
                lists_data = self._get(
                    f"/folder/{folder_id}/list", {"archived": "false"}
                )
                for lst in lists_data.get("lists", []):
                    all_lists.append({
                        "list_id": lst["id"],
                        "list_name": lst["name"],
                        "space_name": space_name,
                    })

            # Lists sem folder
            fl_data = self._get(
                f"/space/{space_id}/list", {"archived": "false"}
            )
            for lst in fl_data.get("lists", []):
                all_lists.append({
                    "list_id": lst["id"],
                    "list_name": lst["name"],
                    "space_name": space_name,
                })

        return all_lists

    def get_tasks_in_list(self, list_id: str) -> list[dict]:
        tasks: list[dict] = []
        page = 0
        while True:
            data = self._get(
                f"/list/{list_id}/task",
                {
                    "archived": "false",
                    "include_closed": "true",
                    "subtasks": "false",
                    "page": page,
                },
            )
            batch = data.get("tasks", [])
            tasks.extend(batch)
            if len(batch) < 100 or data.get("last_page"):
                break
            page += 1
        return tasks

    def get_time_entries(
        self,
        task_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        params: dict = {}
        if start_date:
            params["start_date"] = _to_unix_ms(start_date)
        if end_date:
            params["end_date"] = _to_unix_ms(end_date, end_of_day=True)
        data = self._get(f"/task/{task_id}/time", params)
        return data.get("data", [])


def _to_unix_ms(date_str: str, end_of_day: bool = False) -> int:
    from datetime import datetime, timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
