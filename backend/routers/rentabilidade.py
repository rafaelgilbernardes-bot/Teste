"""GET /api/rentabilidade?mes=2026-03

Receita = valor_faturamento calculado (mesmo algoritmo de /faturamento).
Custo  = horas × valor_hora_custo de cada colaborador.
Margem = receita - custo.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from db import get_db
from models import RentabilidadeContrato

router = APIRouter(tags=["rentabilidade"])


@router.get("/rentabilidade", response_model=list[RentabilidadeContrato])
def get_rentabilidade(
    mes: str = Query(..., description="YYYY-MM"),
    cliente_id: Optional[str] = Query(None),
):
    db = get_db()

    q = db.table("contratos").select(
        "id, modelo, valor_hora, valor_fixo_mensal, valor_escopo, "
        "cliente_id, clientes(nome)"
    ).eq("status", "ativo")
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    contratos = q.execute().data

    # Cache de custo-hora por colaborador
    colabs = db.table("colaboradores").select("id, valor_hora_custo").execute().data
    custo_por_colab = {c["id"]: (c["valor_hora_custo"] or 0) for c in colabs}

    result = []
    for c in contratos:
        contrato_id = c["id"]
        cliente_nome = (c.get("clientes") or {}).get("nome", "Desconhecido")

        entries = (
            db.table("time_entries")
            .select("duracao_minutos, colaborador_id")
            .eq("contrato_id", contrato_id)
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .not_.is_("produto", "null")
            .execute()
            .data
        )

        total_min = sum(e["duracao_minutos"] for e in entries)
        total_h = total_min / 60

        # Custo real
        custo = sum(
            (e["duracao_minutos"] / 60) * custo_por_colab.get(e["colaborador_id"], 0)
            for e in entries
        )

        # Receita
        modelo = c["modelo"]
        if modelo == "hora":
            receita = total_h * (c["valor_hora"] or 0)
        elif modelo == "laas":
            receita = c["valor_fixo_mensal"] or 0
        else:
            receita = c["valor_escopo"] or 0

        margem = receita - custo
        pct = (margem / receita * 100) if receita else 0

        result.append(RentabilidadeContrato(
            contrato_id=contrato_id,
            cliente_nome=cliente_nome,
            modelo=modelo,
            receita=round(receita, 2),
            custo=round(custo, 2),
            margem=round(margem, 2),
            pct_margem=round(pct, 1),
            mes_referencia=mes,
        ))

    return result
