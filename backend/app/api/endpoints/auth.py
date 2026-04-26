from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.api.deps import DB
from app.models.usuario import Usuario
from app.core.auth import verificar_senha, criar_token, get_usuario_atual

router = APIRouter()


class LoginResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"
    usuario      : dict


class UsuarioAtualResponse(BaseModel):
    id    : UUID
    nome  : str
    email : str
    papel : str

    model_config = {"from_attributes": True}


@router.post("/login", response_model=LoginResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db  : Session = DB,
):
    """
    OAuth2 password flow — compatível com o Swagger UI.
    username = email do usuário.
    """
    usuario = db.query(Usuario).filter(Usuario.email == form.username).first()

    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos",
        )

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    token = criar_token({"sub": usuario.email, "papel": usuario.papel})

    return {
        "access_token": token,
        "token_type"  : "bearer",
        "usuario"     : {
            "id"   : str(usuario.id),
            "nome" : usuario.nome,
            "email": usuario.email,
            "papel": usuario.papel,
        },
    }


@router.get("/me", response_model=UsuarioAtualResponse)
def me(usuario=Depends(get_usuario_atual)):
    return usuario