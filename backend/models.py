"""Modelos Pydantic para validação de entrada e serialização de resposta."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Clientes
# ------------------------------------------------------------------

class ClienteCreate(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    contato_nome: Optional[str] = None
    contato_email: Optional[str] = None
    clickup_list_id: Optional[str] = None


class ClienteOut(ClienteCreate):
    id: str
    ativo: bool


# ------------------------------------------------------------------
# Contratos
# ------------------------------------------------------------------

ModeloContrato = Literal["hora", "laas", "escopo_fechado"]


class ContratoCreate(BaseModel):
    cliente_id: str
    modelo: ModeloContrato
    descricao: Optional[str] = None
    # Hora
    valor_hora: Optional[float] = None
    # LaaS
    valor_fixo_mensal: Optional[float] = None
    horas_laas_limite: Optional[int] = None
    # Escopo fechado
    valor_escopo: Optional[float] = None
    horas_escopo: Optional[int] = None
    # Vigência
    data_inicio: date
    data_fim: Optional[date] = None


class ContratoOut(ContratoCreate):
    id: str
    status: str


# ------------------------------------------------------------------
# Respostas dos endpoints de BI
# ------------------------------------------------------------------

class FaturamentoCliente(BaseModel):
    cliente_id: str
    cliente_nome: str
    modelo: str
    total_horas: float
    valor_faturamento: float
    mes_referencia: str


class ProdutividadeColaborador(BaseModel):
    colaborador_id: str
    colaborador_nome: str
    total_horas: float
    horas_faturaveis: float
    horas_nao_faturaveis: float
    pct_faturavel: float
    meta_horas: int
    pct_meta: float
    mes_referencia: str


class RentabilidadeContrato(BaseModel):
    contrato_id: str
    cliente_nome: str
    modelo: str
    receita: float
    custo: float
    margem: float
    pct_margem: float
    mes_referencia: str


class OrcadoVsRealizado(BaseModel):
    cliente_id: str
    cliente_nome: str
    horas_previstas: Optional[int]
    horas_realizadas: float
    receita_prevista: Optional[float]
    receita_realizada: float
    mes_referencia: str


class Alerta(BaseModel):
    tipo: str       # 'escopo_critico' | 'laas_extrapolado' | 'colabo_abaixo_meta' | 'sem_entry' | 'sem_produto'
    severidade: str # 'info' | 'warning' | 'critical'
    descricao: str
    cliente_nome: Optional[str] = None
    colaborador_nome: Optional[str] = None
    contrato_id: Optional[str] = None
    mes_referencia: str


class ETLStatus(BaseModel):
    ultima_execucao: Optional[str]
    status: Optional[str]
    entries_importadas: Optional[int]
    entries_alertas: Optional[int]
    detalhes: Optional[dict]
