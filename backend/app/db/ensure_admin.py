from app.core.auth import hash_senha, verificar_senha
from app.core.config import settings
from app.core.logger import get_logger
from app.db.session import SessionLocal
from app.models.usuario import PapelUsuario, Usuario
from sqlalchemy.orm import Session

logger = get_logger("ADMIN")


def garantir_admin():
    db: Session = SessionLocal()
    try:
        admin = db.query(Usuario).filter(
            Usuario.email == settings.ADMIN_EMAIL
        ).first()

        if not admin:
            # Cria o admin do zero
            admin = Usuario(
                nome       = "Administrador",
                email      = settings.ADMIN_EMAIL,
                senha_hash = hash_senha(settings.ADMIN_SENHA),
                papel      = PapelUsuario.ADMIN,
                ativo      = True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Admin criado: {settings.ADMIN_EMAIL}")

        else:
            # Verifica se a senha está correta — corrige se for placeholder
            senha_ok = False
            try:
                senha_ok = verificar_senha(settings.ADMIN_SENHA, admin.senha_hash)
            except Exception:
                senha_ok = False

            if not senha_ok:
                admin.senha_hash = hash_senha(settings.ADMIN_SENHA)
                admin.ativo      = True
                db.commit()
                logger.info(f"Senha do admin corrigida: {settings.ADMIN_EMAIL}")
            else:
                logger.info(f"Admin OK: {settings.ADMIN_EMAIL}")

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao garantir admin: {e}")
    finally:
        db.close()