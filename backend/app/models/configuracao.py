from datetime import datetime

from app.db.session import Base
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class ConfiguracaoSistema(Base):
    __tablename__ = "configuracao_sistema"

    id            : Mapped[int]      = mapped_column(Integer, primary_key=True, default=1)
    nome_empresa  : Mapped[str]      = mapped_column(String(200), nullable=False, default="SIRS")
    atualizado_em : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
