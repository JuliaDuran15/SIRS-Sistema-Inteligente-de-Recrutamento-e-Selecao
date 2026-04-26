import enum
import uuid
from datetime import datetime

from app.db.session import Base
from sqlalchemy import DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class PapelUsuario(str, enum.Enum):
    RH      = "rh"
    GESTOR  = "gestor"
    ADMIN   = "admin"

class Usuario(Base):
    __tablename__ = "usuarios"

    id         : Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome       : Mapped[str]        = mapped_column(String(200), nullable=False)
    email      : Mapped[str]        = mapped_column(String(200), unique=True, nullable=False)
    senha_hash : Mapped[str]        = mapped_column(String(255), nullable=False)
    papel      : Mapped[PapelUsuario] = mapped_column(SAEnum(PapelUsuario), default=PapelUsuario.RH)
    ativo      : Mapped[bool]       = mapped_column(default=True)
    criado_em  : Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    entrevistas: Mapped[list["Entrevista"]] = relationship(back_populates="entrevistador")