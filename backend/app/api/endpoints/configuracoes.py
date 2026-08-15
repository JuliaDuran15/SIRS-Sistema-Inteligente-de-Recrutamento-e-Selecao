from datetime import datetime

from app.api.deps import DB
from app.core.auth import APENAS_ADMIN, QUALQUER_PAPEL
from app.models.configuracao import ConfiguracaoSistema
from app.schemas.configuracao import ConfiguracaoResponse, ConfiguracaoUpdate
from fastapi import APIRouter
from sqlalchemy.orm import Session

router = APIRouter()


def _obter_config(db: Session) -> ConfiguracaoSistema:
    config = db.query(ConfiguracaoSistema).filter(ConfiguracaoSistema.id == 1).first()
    if not config:
        config = ConfiguracaoSistema(id=1, nome_empresa="SIRS", atualizado_em=datetime.utcnow())
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/", response_model=ConfiguracaoResponse)
def obter_configuracao(db: Session = DB, _=QUALQUER_PAPEL):
    return _obter_config(db)


@router.patch("/", response_model=ConfiguracaoResponse)
def atualizar_configuracao(dados: ConfiguracaoUpdate, db: Session = DB, _=APENAS_ADMIN):
    config = _obter_config(db)
    config.nome_empresa  = dados.nome_empresa.strip()
    config.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return config
