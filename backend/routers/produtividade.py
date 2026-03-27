"""GET /api/produtividade?mes=2026-03&colaborador_id=...

Horas faturáveis = entries com produto preenchido (Hora | LaaS | Escopo Fechado).
Horas não faturáveis = entries sem produto OU tarefas internas.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from db import get_db
from models import ProdutividadeColaborador

router = APIRouter(tags=["produtividade"])


@router.get("/produtividade", response_model=list[ProdutividadeColaborador])
def get_produtividade(
    mes: str = Query(..., description="YYYY-MM"),
    colaborador_id: Optional[str] = Query(None),
):
    db = get_db()

    q = db.table("colaboradores").select("id, nome, meta_horas_mes").eq("ativo", True)
    if colaborador_id:
        q = q.eq("id", colaborador_id)
    colaboradores = q.execute().data

    result = []
    for col in colaboradores:
        cid = col["id"]
        meta = col["meta_horas_mes"] or 160

        entries = (
            db.table("time_entries")
            .select("duracao_minutos, produto")
            .eq("colaborador_id", cid)
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .execute()
            .data
        )

        total_min = sum(e["duracao_minutos"] for e in entries)
        fat_min = sum(
            e["duracao_minutos"] for e in entries if e.get("produto")
        )
        nao_fat_min = total_min - fat_min
        total_h = total_min / 60
        fat_h = fat_min / 60
        nao_fat_h = nao_fat_min / 60

        result.append(ProdutividadeColaborador(
            colaborador_id=cid,
            colaborador_nome=col["nome"],
            total_horas=round(total_h, 2),
            horas_faturaveis=round(fat_h, 2),
            horas_nao_faturaveis=round(nao_fat_h, 2),
            pct_faturavel=round(fat_h / total_h * 100, 1) if total_h else 0.0,
            meta_horas=meta,
            pct_meta=round(total_h / meta * 100, 1),
            mes_referencia=mes,
        ))

    return result
