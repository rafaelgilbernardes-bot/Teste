"""GET /api/orcado-vs-realizado?mes=2026-03

Compara o orçamento planejado com o realizado (horas + receita).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from db import get_db
from models import OrcadoVsRealizado

router = APIRouter(tags=["orcamento"])


@router.get("/orcado-vs-realizado", response_model=list[OrcadoVsRealizado])
def get_orcado_vs_realizado(
    mes: str = Query(..., description="YYYY-MM"),
    cliente_id: Optional[str] = Query(None),
):
    db = get_db()

    q = db.table("clientes").select("id, nome").eq("ativo", True)
    if cliente_id:
        q = q.eq("id", cliente_id)
    clientes = q.execute().data

    result = []
    for cli in clientes:
        cid = cli["id"]

        # Orçamento
        orc_resp = (
            db.table("orcamentos")
            .select("horas_previstas, receita_prevista")
            .eq("cliente_id", cid)
            .eq("mes_referencia", mes)
            .limit(1)
            .execute()
        )
        orc = orc_resp.data[0] if orc_resp.data else {}

        # Realizado — time entries
        entries = (
            db.table("time_entries")
            .select("duracao_minutos")
            .eq("cliente_id", cid)
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .not_.is_("produto", "null")
            .execute()
            .data
        )
        total_h = sum(e["duracao_minutos"] for e in entries) / 60

        # Receita realizada via fatura calculada (se existir) ou recalcula
        fat_resp = (
            db.table("faturas")
            .select("valor_calculado")
            .eq("mes_referencia", mes)
            .in_("contrato_id",
                 [c["id"] for c in
                  db.table("contratos").select("id").eq("cliente_id", cid).execute().data]
                 )
            .execute()
        )
        receita_real = sum(f["valor_calculado"] or 0 for f in fat_resp.data)

        result.append(OrcadoVsRealizado(
            cliente_id=cid,
            cliente_nome=cli["nome"],
            horas_previstas=orc.get("horas_previstas"),
            horas_realizadas=round(total_h, 2),
            receita_prevista=orc.get("receita_prevista"),
            receita_realizada=round(receita_real, 2),
            mes_referencia=mes,
        ))

    return result
