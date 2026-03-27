"""ETL principal: ClickUp → Supabase.

Execução:
    python etl/run.py              # reprocessa os últimos 2 dias
    python etl/run.py --days 7    # reprocessa os últimos 7 dias
    python etl/run.py --start 2026-03-01 --end 2026-03-31

Regras críticas (briefing § 5.6, § 5.7):
- Nunca consultar subtarefas individualmente.
- Se time_spent > 0 mas entries == [] → logar alerta, não descartar.
- Se entry sem cliente_id → gravar com NULL e logar.
- Se entry sem campo Produto → logar como dado incompleto, excluir do cálculo.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from clickup_client import ClickUpClient
from resolvers import Resolver
from supabase_writer import SupabaseWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Parsers de custom fields
# ------------------------------------------------------------------

_CF_NAMES = {"Providência", "Demanda Legal", "Produto"}


def _extract_custom_fields(task: dict) -> dict[str, str | None]:
    result: dict[str, str | None] = {k: None for k in _CF_NAMES}
    for cf in task.get("custom_fields", []):
        name = cf.get("name", "")
        if name in _CF_NAMES:
            # Dropdown: valor está em cf["value"] como índice ou em cf["type_config"]["options"]
            val = cf.get("value")
            options = cf.get("type_config", {}).get("options", [])
            if val is not None and options:
                try:
                    idx = int(val)
                    result[name] = options[idx]["name"]
                except (ValueError, IndexError, KeyError):
                    # Alguns dropdowns retornam o nome diretamente
                    result[name] = str(val)
            elif val is not None:
                result[name] = str(val)
    return result


# ------------------------------------------------------------------
# Conversor de entry do ClickUp → linha do banco
# ------------------------------------------------------------------

def _entry_to_row(
    entry: dict,
    task: dict,
    list_id: str,
    resolver: Resolver,
    custom_fields: dict,
) -> dict:
    from datetime import datetime, timezone

    # Duração: o ClickUp retorna em milissegundos
    duracao_ms = int(entry.get("duration", 0))
    duracao_min = max(1, round(duracao_ms / 60000))

    # Data da entry (Unix ms)
    start_ms = int(entry.get("start", 0))
    entry_date = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).date()

    user_id = str(entry.get("user", {}).get("id", ""))
    cliente_id = resolver.cliente_id(list_id)
    colaborador_id = resolver.colaborador_id(user_id)
    produto = custom_fields.get("Produto")
    contrato_id = resolver.contrato_id(cliente_id, produto, entry_date)

    return {
        "clickup_entry_id": str(entry.get("id")),
        "clickup_task_id": task["id"],
        "clickup_user_id": user_id,
        "colaborador_id": colaborador_id,
        "cliente_id": cliente_id,
        "contrato_id": contrato_id,
        "tarefa_nome": task.get("name"),
        "descricao": entry.get("description") or task.get("description"),
        "providencia": custom_fields.get("Providência"),
        "demanda_legal": custom_fields.get("Demanda Legal"),
        "produto": produto,
        "data": entry_date.isoformat(),
        "duracao_minutos": duracao_min,
        "mes_referencia": entry_date.strftime("%Y-%m"),
        "alerta_sem_entry": False,
    }


# ------------------------------------------------------------------
# Fluxo principal
# ------------------------------------------------------------------

def run_etl(start_date: str, end_date: str) -> None:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    db = create_client(supabase_url, supabase_key)

    clickup = ClickUpClient()
    resolver = Resolver(db)
    writer = SupabaseWriter(db)

    imported = 0
    alerts = 0
    errors: list[dict] = []
    incomplete: list[dict] = []

    log.info("Iniciando ETL: %s → %s", start_date, end_date)

    # 1. Hierarquia do workspace
    hierarchy = clickup.get_workspace_hierarchy()
    log.info("%d spaces encontrados", len(hierarchy))

    for space in hierarchy:
        space_name = space.get("name", space["id"])

        # Coletar todas as lists (dentro de folders + direto no space)
        all_lists: list[dict] = list(space.get("direct_lists", []))
        for folder in space.get("folders", []):
            all_lists.extend(folder.get("lists", []))

        for lst in all_lists:
            list_id = lst["id"]
            list_name = lst.get("name", list_id)
            log.info("  Processando list '%s' (%s) / space '%s'", list_name, list_id, space_name)

            try:
                tasks = clickup.get_tasks_in_list(list_id)
            except Exception as exc:
                log.error("    Erro ao buscar tarefas da list %s: %s", list_id, exc)
                errors.append({"list_id": list_id, "error": str(exc)})
                continue

            log.info("    %d tarefas encontradas", len(tasks))

            for task in tasks:
                # Pular subtarefas que porventura aparecem no resultado
                if task.get("parent"):
                    continue

                task_id = task["id"]
                task_name = task.get("name", task_id)
                time_spent_ms = int(task.get("time_spent", 0) or 0)

                try:
                    entries = clickup.get_time_entries(
                        task_id, start_date=start_date, end_date=end_date
                    )
                except Exception as exc:
                    log.error("    Erro ao buscar entries da task %s: %s", task_id, exc)
                    errors.append({"task_id": task_id, "error": str(exc)})
                    continue

                # Erro crítico: time_spent registrado diretamente (sem entry individual)
                if time_spent_ms > 0 and len(entries) == 0:
                    log.warning(
                        "    ALERTA: task '%s' tem time_spent=%d ms mas nenhuma entry individual.",
                        task_name,
                        time_spent_ms,
                    )
                    alerts += 1
                    # Gravar registro de alerta para revisão manual
                    writer.upsert_time_entry({
                        "clickup_entry_id": f"alert_{task_id}_{start_date}",
                        "clickup_task_id": task_id,
                        "clickup_user_id": None,
                        "colaborador_id": None,
                        "cliente_id": resolver.cliente_id(list_id),
                        "contrato_id": None,
                        "tarefa_nome": task_name,
                        "descricao": "ALERTA: time_spent sem entries individuais",
                        "providencia": None,
                        "demanda_legal": None,
                        "produto": None,
                        "data": start_date,
                        "duracao_minutos": round(time_spent_ms / 60000),
                        "mes_referencia": start_date[:7],
                        "alerta_sem_entry": True,
                    })
                    continue

                # Obter custom fields uma vez por task (não por entry)
                custom_fields = _extract_custom_fields(task)

                if custom_fields.get("Produto") is None:
                    if entries:
                        log.warning(
                            "    INCOMPLETO: task '%s' sem campo Produto — excluída do cálculo.",
                            task_name,
                        )
                        incomplete.append({"task_id": task_id, "task_name": task_name})
                    continue

                for entry in entries:
                    try:
                        row = _entry_to_row(entry, task, list_id, resolver, custom_fields)
                        writer.upsert_time_entry(row)
                        imported += 1
                    except Exception as exc:
                        log.error("    Erro ao gravar entry %s: %s", entry.get("id"), exc)
                        errors.append({"entry_id": entry.get("id"), "error": str(exc)})

    status = "success" if not errors else "partial_error"
    writer.save_etl_log(
        status=status,
        entries_importadas=imported,
        entries_alertas=alerts,
        detalhes={
            "start_date": start_date,
            "end_date": end_date,
            "errors": errors[:50],  # limitar tamanho do log
            "incomplete_tasks": incomplete[:50],
        },
    )

    log.info(
        "ETL concluído. Importadas: %d | Alertas: %d | Erros: %d",
        imported, alerts, len(errors),
    )


# ------------------------------------------------------------------
# Entrypoint CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL ClickUp → Supabase")
    parser.add_argument("--days", type=int, default=2, help="Número de dias passados a reprocessar")
    parser.add_argument("--start", type=str, help="Data de início (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="Data de fim (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.start and args.end:
        start = args.start
        end = args.end
    else:
        today = date.today()
        start = (today - timedelta(days=args.days)).isoformat()
        end = today.isoformat()

    run_etl(start, end)
