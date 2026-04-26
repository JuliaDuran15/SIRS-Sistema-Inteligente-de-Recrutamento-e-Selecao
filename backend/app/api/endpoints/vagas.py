from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import DB
from app.core.auth import RH_OU_ADMIN, QUALQUER_PAPEL, APENAS_ADMIN
from app.models.vaga import Vaga
from app.schemas.vaga import VagaCreate, VagaResponse, VagaUpdatePesos
from app.ai.resume_parser import vetorizar_texto
from app.ai.market_analyzer import analisar_mercado
from app.ai.tasks import atualizar_mercado_vaga

router = APIRouter()

@router.post("/", response_model=VagaResponse, status_code=201)
def criar_vaga(dados: VagaCreate, db: Session = DB, _=RH_OU_ADMIN):
    payload = dados.model_dump()
    payload["vetor_vaga"] = vetorizar_texto(dados.requisitos_texto)
    vaga = Vaga(**payload)
    db.add(vaga)
    db.commit()
    db.refresh(vaga)
    atualizar_mercado_vaga.delay(str(vaga.id))
    return vaga


@router.patch("/{vaga_id}/requisitos", response_model=VagaResponse)
def atualizar_requisitos(vaga_id: str, requisitos_texto: str, db: Session = DB, _=RH_OU_ADMIN):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.requisitos_texto = requisitos_texto
    vaga.vetor_vaga       = vetorizar_texto(requisitos_texto)
    db.commit()
    db.refresh(vaga)
    return vaga


@router.get("/", response_model=list[VagaResponse])
def listar_vagas(db: Session = DB, _=QUALQUER_PAPEL):
    return db.query(Vaga).filter(Vaga.status == "aberta").all()


@router.get("/{vaga_id}", response_model=VagaResponse)
def buscar_vaga(vaga_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return vaga


@router.patch("/{vaga_id}/pesos", response_model=VagaResponse)
def atualizar_pesos(vaga_id: str, dados: VagaUpdatePesos, db: Session = DB, _=RH_OU_ADMIN):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.peso_rh             = dados.peso_rh
    vaga.peso_mercado        = dados.peso_mercado
    vaga.peso_curriculo      = dados.peso_curriculo
    vaga.peso_entrevista_rh  = dados.peso_entrevista_rh
    vaga.peso_entrevista_tec = dados.peso_entrevista_tec
    db.commit()
    db.refresh(vaga)
    return vaga


@router.patch("/{vaga_id}/status", response_model=VagaResponse)
def atualizar_status(vaga_id: str, status: str, db: Session = DB, _=RH_OU_ADMIN):
    if status not in ("aberta", "pausada", "fechada"):
        raise HTTPException(status_code=400, detail="Status inválido")
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.status = status
    db.commit()
    db.refresh(vaga)
    return vaga


@router.delete("/{vaga_id}", status_code=204)
def deletar_vaga(vaga_id: str, db: Session = DB, _=APENAS_ADMIN):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.status = "fechada"
    db.commit()


@router.post("/{vaga_id}/analisar-mercado", response_model=VagaResponse)
async def analisar_mercado_vaga(vaga_id: str, db: Session = DB, _=RH_OU_ADMIN):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    resultado = await analisar_mercado(vaga.nome)
    vaga.vetor_mercado   = resultado["vetor_mercado"]
    vaga.ranking_mercado = {
        "termos"               : resultado["termos_frequentes"],
        "total_vagas_analisadas": resultado["total_vagas_analisadas"],
        "fonte"                : resultado["fonte"],
    }
    db.commit()
    db.refresh(vaga)
    return vaga
