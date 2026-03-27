"""ETL principal: ClickUp → Supabase — CFPazziniGil."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta

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


_CF_NAMES = {"Providência", "Demanda Legal", "Produto"}


def _extract_custom_fields(task: dict) -> dict[str, str | None]:
    """Extrai campos customizados de uma tarefa.

    Suporta tipos:
    - labels: val é lista de IDs (UUIDs) → busca label pelo ID
    - drop_down: val é índice numérico → busca option pelo índice
    """
    result: dict[str, str | None] = {k: None for k in _CF_NAMES}
    for cf in task.get("custom_fields", []):
        name = cf.get("name", "")
        if name not in _CF_NAMES:
            continue
        val = cf.get("value")
        if val is None:
            continue

        cf_type = cf.get("type", "")
        options = cf.get("type_config", {}).get("options", [])

        if cf_type == "labels" and options:
            # val é uma lista de label IDs (UUIDs)
            label_ids = val if isinstance(val, list) else [val]
            if label_ids:
                id_to_label = {
                    opt["id"]: opt.get("label", opt.get("name", ""))
                    for opt in options
                }
                result[name] = id_to_label.get(str(label_ids[0]))
        elif cf_type == "drop_down" and options:
            try:
                idx = int(val[0] if isinstance(val, list) else val)
                result[name] = options[idx].get("name", options[idx].get("label"))
            except (ValueError, IndexError, KeyError, TypeError):
                result[name] = str(val)
        else:
            result[name] = str(val) if not isinstance(val, list) else (
                str(val[0]) if val else None
            )

    return result


def _entry_to_row(
    entry: dict,
    task: dict,
    list_id: str,
    resolver: Resolver,
    custom_fields: dict,
) -> dict:
    from datetime import datetime, timezone

    duracao_ms = int(entry.get("duration", 0))
    duracao_min = max(1, round(duracao_ms / 60000)) if duracao_ms > 0 else 0
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


def run_etl(start_date: str, end_date: str) -> None:
    from supabase import create_client

    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )

    clickup = ClickUpClient()
    team_id = clickup.get_team_id()
    log.info("Usando workspace ID: %s", team_id)

    resolver = Resolver(db)
    writer = SupabaseWriter(db)

    imported = 0
    skipped_no_list = 0
    errors: list[dict] = []

    log.info("Iniciando ETL: %s → %s", start_date, end_date)

    # Busca TODAS as time entries do workspace no período (muito mais eficiente)
    all_entries = clickup.get_workspace_time_entries(team_id, start_date, end_date)
    log.info("Total de time entries no período: %d", len(all_entries))

    if not all_entries:
        log.warning("Nenhuma time entry encontrada no período %s → %s", start_date, end_date)

    # Agrupar entries por task_id para buscar cada tarefa apenas uma vez
    task_entries: dict[str, list[dict]] = {}
    for entry in all_entries:
        task_info = entry.get("task") or {}
        task_id = task_info.get("id")
        if task_id:
            task_entries.setdefault(task_id, []).append(entry)

    log.info("Tasks únicas com entries: %d", len(task_entries))

    # Cache de detalhes de tarefas
    task_cache: dict[str, dict] = {}

    for task_id, entries in task_entries.items():
        # Busca detalhes da tarefa (list_id + custom fields)
        if task_id not in task_cache:
            try:
                task_cache[task_id] = clickup.get_task(task_id)
            except Exception as exc:
                log.error("Erro ao buscar task %s: %s", task_id, exc)
                errors.append({"task_id": task_id, "error": str(exc)})
                continue

        task = task_cache[task_id]
        list_id = (task.get("list") or {}).get("id")

        if not list_id:
            log.warning("Task %s '%s' sem list_id — ignorada",
                        task_id, task.get("name", "?"))
            skipped_no_list += 1
            continue

        custom_fields = _extract_custom_fields(task)
        produto = custom_fields.get("Produto")

        if produto is None:
            log.warning("Task '%s' sem campo Produto — importando sem produto",
                        task.get("name", task_id))

        for entry in entries:
            if int(entry.get("duration", 0)) == 0:
                log.debug("Entry %s com duração zero — ignorada", entry.get("id"))
                continue
            try:
                row = _entry_to_row(entry, task, list_id, resolver, custom_fields)
                writer.upsert_time_entry(row)
                imported += 1
            except Exception as exc:
                log.error("Erro ao gravar entry %s: %s", entry.get("id"), exc)
                errors.append({"entry_id": entry.get("id"), "error": str(exc)})

    writer.save_etl_log(
        status="success" if not errors else "partial_error",
        entries_importadas=imported,
        entries_alertas=skipped_no_list,
        detalhes={
            "start_date": start_date,
            "end_date": end_date,
            "total_entries_clickup": len(all_entries),
            "tasks_unicas": len(task_entries),
            "skipped_no_list": skipped_no_list,
            "errors": errors[:50],
        },
    )

    log.info("ETL concluído. Importadas: %d | Sem lista: %d | Erros: %d",
             imported, skipped_no_list, len(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--start", type=str)
    parser.add_argument("--end", type=str)
    args = parser.parse_args()

    if args.start and args.end:
        start, end = args.start, args.end
    else:
        today = date.today()
        start = (today - timedelta(days=args.days)).isoformat()
        end = today.isoformat()

    run_etl(start, end)
