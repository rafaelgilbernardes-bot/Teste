"""GET /api/etl/status e POST /api/etl/run (trigger manual)."""
from __future__ import annotations

import subprocess
import sys
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Query

from db import get_db
from models import ETLStatus

router = APIRouter(tags=["etl"])


@router.get("/etl/status", response_model=ETLStatus)
def etl_status():
    db = get_db()
    resp = (
        db.table("etl_log")
        .select("*")
        .order("executado_em", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return ETLStatus(
            ultima_execucao=None, status=None,
            entries_importadas=None, entries_alertas=None, detalhes=None
        )
    row = resp.data[0]
    return ETLStatus(
        ultima_execucao=row["executado_em"],
        status=row["status"],
        entries_importadas=row["entries_importadas"],
        entries_alertas=row["entries_alertas"],
        detalhes=row["detalhes"],
    )


def _run_etl_bg(start: str, end: str):
    """Executa o ETL em background via subprocess."""
    subprocess.run(
        [sys.executable, "../etl/run.py", "--start", start, "--end", end],
        check=False,
    )


@router.post("/etl/run", status_code=202)
def trigger_etl(
    background_tasks: BackgroundTasks,
    days: int = Query(2, ge=1, le=90),
):
    today = date.today()
    start = (today - timedelta(days=days)).isoformat()
    end = today.isoformat()
    background_tasks.add_task(_run_etl_bg, start, end)
    return {"message": f"ETL iniciado em background para {start} → {end}"}
