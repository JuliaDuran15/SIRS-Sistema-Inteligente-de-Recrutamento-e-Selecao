from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import DB
from app.models.candidato import Candidato
from app.schemas.candidato import CandidatoCreate, CandidatoResponse, CandidatoUpdate

router = APIRouter()

@router.post("/", response_model=CandidatoResponse, status_code=201)
def criar_candidato(dados: CandidatoCreate, db: Session = DB):
    existe = db.query(Candidato).filter(Candidato.email == dados.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    payload = dados.model_dump()
    # converte lista de FormacaoItem em lista de dicts para salvar no JSONB
    payload["formacao"] = [f.model_dump() for f in dados.formacao]

    candidato = Candidato(**payload)
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.post("/webhook", response_model=CandidatoResponse, status_code=201)
def webhook_candidato(dados: CandidatoCreate, db: Session = DB):
    """Recebe candidatos vindos de sistemas externos (ATS, HRIS)."""
    dados.origem = "externo"
    return criar_candidato(dados, db)


@router.get("/", response_model=list[CandidatoResponse])
def listar_candidatos(db: Session = DB):
    return db.query(Candidato).all()


@router.get("/{candidato_id}", response_model=CandidatoResponse)
def buscar_candidato(candidato_id: str, db: Session = DB):
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    return candidato


@router.patch("/{candidato_id}", response_model=CandidatoResponse)
def atualizar_candidato(candidato_id: str, dados: CandidatoUpdate, db: Session = DB):
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo == "formacao" and valor is not None:
            valor = [f if isinstance(f, dict) else f.model_dump() for f in valor]
        setattr(candidato, campo, valor)

    db.commit()
    db.refresh(candidato)
    return candidato