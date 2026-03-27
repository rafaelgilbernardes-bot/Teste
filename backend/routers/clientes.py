from fastapi import APIRouter, HTTPException
from db import get_db
from models import ClienteCreate, ClienteOut

router = APIRouter(tags=["clientes"])


@router.get("/clientes", response_model=list[ClienteOut])
def list_clientes():
    db = get_db()
    return db.table("clientes").select("*").eq("ativo", True).order("nome").execute().data


@router.post("/clientes", response_model=ClienteOut, status_code=201)
def create_cliente(body: ClienteCreate):
    db = get_db()
    resp = db.table("clientes").insert(body.model_dump(exclude_none=True)).execute()
    if not resp.data:
        raise HTTPException(500, "Erro ao criar cliente")
    return resp.data[0]


@router.patch("/clientes/{cliente_id}", response_model=ClienteOut)
def update_cliente(cliente_id: str, body: ClienteCreate):
    db = get_db()
    resp = (
        db.table("clientes")
        .update(body.model_dump(exclude_none=True))
        .eq("id", cliente_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Cliente não encontrado")
    return resp.data[0]
