"""Escrita idempotente no Supabase.

Usa clickup_entry_id como chave de upsert para garantir que reexecuções
nunca dupliquem registros.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


class SupabaseWriter:
    def __init__(self, db):
        self.db = db

    def upsert_time_entry(self, row: dict) -> None:
        """Insere ou atualiza um time entry. Chave: clickup_entry_id."""
        self.db.table("time_entries").upsert(
            row, on_conflict="clickup_entry_id"
        ).execute()

    def save_etl_log(
        self,
        status: str,
        entries_importadas: int,
        entries_alertas: int,
        detalhes: dict,
    ) -> None:
        self.db.table("etl_log").insert({
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "entries_importadas": entries_importadas,
            "entries_alertas": entries_alertas,
            "detalhes": detalhes,
        }).execute()
