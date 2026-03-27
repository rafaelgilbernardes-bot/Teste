"""GET /api/faturamento?mes=2026-03&cliente_id=...

Lógica de cálculo por modelo (briefing § 6):
- hora:          horas × valor_hora do contrato
- laas:          valor_fixo_mensal (independe das horas)
- escopo_fechado: valor_escopo fixo + % de utilização
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from db import get_db
from models import FaturamentoCliente

router = APIRouter(tags=["faturamento"])


@router.get("/faturamento", response_model=list[FaturamentoCliente])
def get_faturamento(
    mes: str = Query(..., description="Mês de referência no formato YYYY-MM"),
    cliente_id: Optional[str] = Query(None),
):
    db = get_db()

    # Buscar contratos ativos com seus clientes
    q = db.table("contratos").select(
        "id, modelo, valor_hora, valor_fixo_mensal, valor_escopo, horas_escopo, "
        "cliente_id, clientes(nome)"
    ).eq("status", "ativo")

    if cliente_id:
        q = q.eq("cliente_id", cliente_id)

    contratos = q.execute().data

    result = []
    for c in contratos:
        cid = c["cliente_id"]
        contrato_id = c["id"]
        cliente_nome = (c.get("clientes") or {}).get("nome", "Desconhecido")

        # Buscar time entries do mês para este contrato
        entries = (
            db.table("time_entries")
            .select("duracao_minutos")
            .eq("contrato_id", contrato_id)
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .not_.is_("produto", "null")
            .execute()
            .data
        )

        total_min = sum(e["duracao_minutos"] for e in entries)
        total_horas = total_min / 60

        # Cálculo por modelo
        modelo = c["modelo"]
        if modelo == "hora":
            valor = total_horas * (c["valor_hora"] or 0)
        elif modelo == "laas":
            valor = c["valor_fixo_mensal"] or 0
        else:  # escopo_fechado
            valor = c["valor_escopo"] or 0

        result.append(FaturamentoCliente(
            cliente_id=cid,
            cliente_nome=cliente_nome,
            modelo=modelo,
            total_horas=round(total_horas, 2),
            valor_faturamento=round(valor, 2),
            mes_referencia=mes,
        ))

    return result
