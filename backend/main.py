"""FastAPI — CFPazziniGil BI System.

Execução local:
    uvicorn main:app --reload --port 8000

Endpoints disponíveis:
    GET  /api/faturamento
    GET  /api/produtividade
    GET  /api/rentabilidade
    GET  /api/orcado-vs-realizado
    GET  /api/alertas
    GET  /api/clientes
    POST /api/contratos
    GET  /api/contratos
    GET  /api/etl/status
    POST /api/etl/run
    POST /api/relatorios/excel
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    faturamento,
    produtividade,
    rentabilidade,
    orcamento,
    alertas,
    clientes,
    contratos,
    etl,
    relatorios,
)

app = FastAPI(
    title="CFPazziniGil BI API",
    version="1.0.0",
    description="Sistema de Business Intelligence para o escritório CFPazziniGil.",
)

# CORS — liberar para o domínio do frontend (Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restringir ao domínio real em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(faturamento.router, prefix="/api")
app.include_router(produtividade.router, prefix="/api")
app.include_router(rentabilidade.router, prefix="/api")
app.include_router(orcamento.router, prefix="/api")
app.include_router(alertas.router, prefix="/api")
app.include_router(clientes.router, prefix="/api")
app.include_router(contratos.router, prefix="/api")
app.include_router(etl.router, prefix="/api")
app.include_router(relatorios.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
