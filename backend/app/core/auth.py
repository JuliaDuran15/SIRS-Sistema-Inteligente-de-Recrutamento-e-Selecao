from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db

pwd_context    = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_token(dados: dict, expira_em_horas: int = 8) -> str:
    payload = dados.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=expira_em_horas)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Dependency — injeta o usuário logado em qualquer endpoint protegido."""
    from app.models.usuario import Usuario

    payload  = decodificar_token(token)
    email    = payload.get("sub")

    if not email:
        raise HTTPException(status_code=401, detail="Token inválido")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")

    return usuario


def exigir_papel(*papeis: str):
    """Dependency — restringe endpoint a papéis específicos."""
    def verificar(usuario=Depends(get_usuario_atual)):
        if usuario.papel not in papeis:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Papel necessário: {', '.join(papeis)}"
            )
        return usuario
    return verificar


# Shortcuts prontos para usar nos endpoints
RH_OU_ADMIN     = Depends(exigir_papel("rh", "admin"))
GESTOR_OU_ADMIN = Depends(exigir_papel("gestor", "admin"))
APENAS_ADMIN    = Depends(exigir_papel("admin"))
QUALQUER_PAPEL  = Depends(get_usuario_atual)