from app.api.deps import DB
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/", response_model=UsuarioResponse, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = DB):
    # Verifica se email já existe
    existe = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    usuario = Usuario(
        nome       = dados.nome,
        email      = dados.email,
        senha_hash = pwd_context.hash(dados.senha),
        papel      = dados.papel,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = DB):
    return db.query(Usuario).filter(Usuario.ativo == True).all()


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def buscar_usuario(usuario_id: str, db: Session = DB):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@router.delete("/{usuario_id}", status_code=204)
def desativar_usuario(usuario_id: str, db: Session = DB):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Admin não pode ser desativado
    if usuario.papel == "admin":
        raise HTTPException(
            status_code=403,
            detail="O administrador não pode ser desativado"
        )

    usuario.ativo = False
    db.commit()