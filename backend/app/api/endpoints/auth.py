import hashlib
from uuid import UUID

from app.api.deps import DB
from app.core.auth import criar_token, get_usuario_atual, hash_senha, verificar_senha
from app.core.config import settings
from app.core.email import email_reset_senha, smtp_configurado
from app.models.usuario import Usuario
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt as jose_jwt


def _senha_fingerprint(senha_hash: str) -> str:
    """16 chars do SHA-256 do hash atual — invalida o token se a senha mudar."""
    return hashlib.sha256(senha_hash.encode()).hexdigest()[:16]
from pydantic import BaseModel
from sqlalchemy.orm import Session

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


from app.core.email import email_reset_senha, smtp_configurado
from app.core.config import settings


class AlterarSenhaRequest(BaseModel):
    senha_atual : str
    senha_nova  : str


@router.patch("/senha", status_code=204)
def alterar_senha(
    dados  : AlterarSenhaRequest,
    db     : Session = DB,
    usuario=Depends(get_usuario_atual),
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(dados.senha_nova) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")
    usuario.senha_hash = hash_senha(dados.senha_nova)
    db.commit()


# ── Forgot / Reset password ───────────────────────────────────────────────────

class EsqueceuSenhaRequest(BaseModel):
    email: str


class EsqueceuSenhaResponse(BaseModel):
    enviado   : bool
    reset_url : str | None  # preenchido só quando SMTP não configurado (dev)


class ResetarSenhaRequest(BaseModel):
    reset_token : str
    senha_nova  : str


@router.post("/esqueceu-senha", response_model=EsqueceuSenhaResponse)
def esqueceu_senha(dados: EsqueceuSenhaRequest, db: Session = DB):
    usuario = db.query(Usuario).filter(
        Usuario.email == dados.email, Usuario.ativo == True
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Email não encontrado")

    token = criar_token({
        "sub" : usuario.email,
        "tipo": "reset",
        "fph" : _senha_fingerprint(usuario.senha_hash),  # invalida se a senha já foi trocada
    }, expira_em_horas=1)
    reset_url = f"{settings.FRONTEND_URL}/resetar-senha?token={token}"

    if smtp_configurado():
        email_reset_senha(usuario.email, usuario.nome, reset_url)
        return {"enviado": True, "reset_url": None}

    # Sem SMTP: devolve o link para o frontend exibir (modo dev/interno)
    return {"enviado": False, "reset_url": reset_url}


@router.post("/resetar-senha", status_code=204)
def resetar_senha(dados: ResetarSenhaRequest, db: Session = DB):
    try:
        payload = jose_jwt.decode(
            dados.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if payload.get("tipo") != "reset":
        raise HTTPException(status_code=400, detail="Token inválido")

    usuario = db.query(Usuario).filter(
        Usuario.email == payload.get("sub"), Usuario.ativo == True
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Garante uso único: se a senha já foi alterada após a emissão, o fingerprint não bate
    if payload.get("fph") != _senha_fingerprint(usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Token já utilizado ou inválido")

    if len(dados.senha_nova) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")

    usuario.senha_hash = hash_senha(dados.senha_nova)
    db.commit()