from fastapi import APIRouter, HTTPException
from db import get_db
from models import ContratoCreate, ContratoOut

router = APIRouter(tags=["contratos"])


@router.get("/contratos", response_model=list[ContratoOut])
def list_contratos(cliente_id: str | None = None):
    db = get_db()
    q = db.table("contratos").select("*").order("data_inicio", desc=True)
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    return q.execute().data


@router.post("/contratos", response_model=ContratoOut, status_code=201)
def create_contrato(body: ContratoCreate):
    db = get_db()
    payload = body.model_dump(exclude_none=True)
    # Converter date para ISO string
    for f in ("data_inicio", "data_fim"):
        if f in payload:
            payload[f] = str(payload[f])
    resp = db.table("contratos").insert(payload).execute()
    if not resp.data:
        raise HTTPException(500, "Erro ao criar contrato")
    return resp.data[0]


@router.patch("/contratos/{contrato_id}")
def update_contrato(contrato_id: str, body: dict):
    db = get_db()
    resp = db.table("contratos").update(body).eq("id", contrato_id).execute()
    if not resp.data:
        raise HTTPException(404, "Contrato não encontrado")
    return resp.data[0]
