from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

# Atalho para injetar o banco em qualquer endpoint
# uso: def meu_endpoint(db: DB):
DB = Depends(get_db)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.models.usuario import Usuario

    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario or not usuario.ativo:
        raise cred_exc
    return usuario


# Atalho para proteger endpoints
# uso: def meu_endpoint(usuario: USUARIO_ATUAL):
USUARIO_ATUAL = Depends(get_usuario_atual)
