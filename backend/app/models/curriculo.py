import uuid
from datetime import datetime

from app.db.session import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Curriculo(Base):
    __tablename__ = "curriculos"

    id               : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidatura_id   : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("candidaturas.id"), unique=True)
    texto_extraido   : Mapped[str | None]   = mapped_column(Text)
    vetor_embedding                         = mapped_column(Vector(384), nullable=True)
    skills_extraidas : Mapped[dict | None]  = mapped_column(JSONB)
    score_rh         : Mapped[float | None] = mapped_column(Float)
    score_mercado    : Mapped[float | None] = mapped_column(Float)
    score_curriculo  : Mapped[float | None] = mapped_column(Float)
    processado_em    : Mapped[datetime | None] = mapped_column(DateTime)
    criado_em        : Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

    candidatura: Mapped["Candidatura"] = relationship(back_populates="curriculo")
