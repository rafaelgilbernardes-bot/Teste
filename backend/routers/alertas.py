"""GET /api/alertas

Tipos de alerta (briefing § 2 e § 6):
- escopo_critico:     utilização > 80% (warning) ou > 100% (critical)
- laas_extrapolado:  horas > limite do LaaS
- colabo_abaixo_meta: horas do colaborador < 80% da meta mensal
- sem_entry:         tasks com time_spent mas sem entries individuais
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from db import get_db
from models import Alerta

router = APIRouter(tags=["alertas"])


@router.get("/alertas", response_model=list[Alerta])
def get_alertas(
    mes: str = Query(..., description="YYYY-MM"),
):
    db = get_db()
    alerts: list[Alerta] = []

    # ------------------------------------------------------------------
    # 1. Escopo fechado crítico
    # ------------------------------------------------------------------
    contratos_escopo = (
        db.table("contratos")
        .select("id, horas_escopo, cliente_id, clientes(nome)")
        .eq("modelo", "escopo_fechado")
        .eq("status", "ativo")
        .execute()
        .data
    )
    for c in contratos_escopo:
        if not c["horas_escopo"]:
            continue
        entries = (
            db.table("time_entries")
            .select("duracao_minutos")
            .eq("contrato_id", c["id"])
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .execute()
            .data
        )
        horas = sum(e["duracao_minutos"] for e in entries) / 60
        pct = horas / c["horas_escopo"]
        cliente_nome = (c.get("clientes") or {}).get("nome", "?")

        if pct > 1.0:
            alerts.append(Alerta(
                tipo="escopo_critico",
                severidade="critical",
                descricao=f"{cliente_nome}: escopo consumido a {pct:.0%} (estouro).",
                cliente_nome=cliente_nome,
                contrato_id=c["id"],
                mes_referencia=mes,
            ))
        elif pct > 0.8:
            alerts.append(Alerta(
                tipo="escopo_critico",
                severidade="warning",
                descricao=f"{cliente_nome}: escopo consumido a {pct:.0%} — risco de estouro.",
                cliente_nome=cliente_nome,
                contrato_id=c["id"],
                mes_referencia=mes,
            ))

    # ------------------------------------------------------------------
    # 2. LaaS extrapolado
    # ------------------------------------------------------------------
    contratos_laas = (
        db.table("contratos")
        .select("id, horas_laas_limite, cliente_id, clientes(nome)")
        .eq("modelo", "laas")
        .eq("status", "ativo")
        .not_.is_("horas_laas_limite", "null")
        .execute()
        .data
    )
    for c in contratos_laas:
        entries = (
            db.table("time_entries")
            .select("duracao_minutos")
            .eq("contrato_id", c["id"])
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .execute()
            .data
        )
        horas = sum(e["duracao_minutos"] for e in entries) / 60
        cliente_nome = (c.get("clientes") or {}).get("nome", "?")

        if horas > c["horas_laas_limite"]:
            alerts.append(Alerta(
                tipo="laas_extrapolado",
                severidade="warning",
                descricao=(
                    f"{cliente_nome}: {horas:.1f}h registradas vs limite de "
                    f"{c['horas_laas_limite']}h/mês — considerar renegocição."
                ),
                cliente_nome=cliente_nome,
                contrato_id=c["id"],
                mes_referencia=mes,
            ))

    # ------------------------------------------------------------------
    # 3. Colaborador abaixo da meta mensal
    # ------------------------------------------------------------------
    colabs = (
        db.table("colaboradores")
        .select("id, nome, meta_horas_mes")
        .eq("ativo", True)
        .execute()
        .data
    )
    for col in colabs:
        meta = col["meta_horas_mes"] or 160
        entries = (
            db.table("time_entries")
            .select("duracao_minutos")
            .eq("colaborador_id", col["id"])
            .eq("mes_referencia", mes)
            .eq("alerta_sem_entry", False)
            .execute()
            .data
        )
        horas = sum(e["duracao_minutos"] for e in entries) / 60
        pct = horas / meta if meta else 0

        if pct < 0.8:
            alerts.append(Alerta(
                tipo="colabo_abaixo_meta",
                severidade="info",
                descricao=(
                    f"{col['nome']}: {horas:.1f}h registradas ({pct:.0%} da meta de {meta}h)."
                ),
                colaborador_nome=col["nome"],
                mes_referencia=mes,
            ))

    # ------------------------------------------------------------------
    # 4. Entries sem registro individual (erro crítico de registro)
    # ------------------------------------------------------------------
    sem_entry = (
        db.table("time_entries")
        .select("tarefa_nome, cliente_id, clientes(nome)")
        .eq("alerta_sem_entry", True)
        .eq("mes_referencia", mes)
        .execute()
        .data
    )
    for e in sem_entry:
        cliente_nome = (e.get("clientes") or {}).get("nome", "?")
        alerts.append(Alerta(
            tipo="sem_entry",
            severidade="warning",
            descricao=(
                f"Tarefa '{e['tarefa_nome']}' ({cliente_nome}): horas registradas diretamente "
                f"no campo time_spent sem entry individual — revisão manual necessária."
            ),
            cliente_nome=cliente_nome,
            mes_referencia=mes,
        ))

    return alerts
