"""Resolução de IDs: ClickUp list/user → IDs internos do banco.

Regras:
- Match de cliente por clickup_list_id.
- Match de colaborador por clickup_user_id.
- Se falhar, retorna None e o ETL loga para revisão manual.
- Contrato resolvido por cliente + modelo (campo Produto) + data.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client


_PRODUTO_TO_MODELO = {
    "Hora": "hora",
    "LaaS": "laas",
    "Escopo Fechado": "escopo_fechado",
}


class Resolver:
    def __init__(self, db: "Client"):
        self.db = db
        # Cache em memória para evitar queries repetidas por execução
        self._list_to_cliente: dict[str, str | None] = {}
        self._user_to_colab: dict[str, str | None] = {}
        self._contrato_cache: dict[tuple, str | None] = {}

    def cliente_id(self, clickup_list_id: str) -> str | None:
        if clickup_list_id in self._list_to_cliente:
            return self._list_to_cliente[clickup_list_id]

        resp = (
            self.db.table("clientes")
            .select("id")
            .eq("clickup_list_id", clickup_list_id)
            .eq("ativo", True)
            .limit(1)
            .execute()
        )
        result = resp.data[0]["id"] if resp.data else None
        self._list_to_cliente[clickup_list_id] = result
        return result

    def colaborador_id(self, clickup_user_id: str) -> str | None:
        if clickup_user_id in self._user_to_colab:
            return self._user_to_colab[clickup_user_id]

        resp = (
            self.db.table("colaboradores")
            .select("id")
            .eq("clickup_user_id", str(clickup_user_id))
            .eq("ativo", True)
            .limit(1)
            .execute()
        )
        result = resp.data[0]["id"] if resp.data else None
        self._user_to_colab[clickup_user_id] = result
        return result

    def contrato_id(
        self, cliente_id: str | None, produto: str | None, data_entry: date
    ) -> str | None:
        if not cliente_id or not produto:
            return None

        modelo = _PRODUTO_TO_MODELO.get(produto)
        if not modelo:
            return None

        cache_key = (cliente_id, modelo, data_entry.isoformat())
        if cache_key in self._contrato_cache:
            return self._contrato_cache[cache_key]

        resp = (
            self.db.table("contratos")
            .select("id")
            .eq("cliente_id", cliente_id)
            .eq("modelo", modelo)
            .eq("status", "ativo")
            .lte("data_inicio", data_entry.isoformat())
            .execute()
        )

        result = None
        for row in resp.data:
            # Filtrar data_fim manualmente (pode ser NULL)
            result = row["id"]
            break

        # Refinar filtrando data_fim no lado Python
        if resp.data:
            from datetime import date as date_type
            valid = []
            for row in resp.data:
                r2 = (
                    self.db.table("contratos")
                    .select("id, data_fim")
                    .eq("id", row["id"])
                    .execute()
                )
                if r2.data:
                    df = r2.data[0].get("data_fim")
                    if df is None or date_type.fromisoformat(df) >= data_entry:
                        valid.append(row["id"])
            result = valid[0] if valid else None

        self._contrato_cache[cache_key] = result
        return result
