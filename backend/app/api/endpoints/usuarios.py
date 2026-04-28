from app.api.deps import DB
from app.core.auth import APENAS_ADMIN, QUALQUER_PAPEL
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/", response_model=UsuarioResponse, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = DB, _=APENAS_ADMIN):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=pwd_context.hash(dados.senha),
        papel=dados.papel,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = DB, _=QUALQUER_PAPEL):
    return db.query(Usuario).filter(Usuario.ativo == True).all()


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def buscar_usuario(usuario_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@router.delete("/{usuario_id}", status_code=204)
def desativar_usuario(usuario_id: str, db: Session = DB, _=APENAS_ADMIN):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if usuario.papel == PapelUsuario.ADMIN:
        raise HTTPException(status_code=403, detail="O administrador não pode ser desativado")
    usuario.ativo = False
    db.commit()
