import uuid
from datetime import datetime
from sqlalchemy import Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class Curriculo(Base):
    __tablename__ = "curriculos"

    id              : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidato_id    : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("candidatos.id"), unique=True)
    texto_extraido  : Mapped[str | None]   = mapped_column(Text)
    vetor_embedding                        = mapped_column(Vector(384), nullable=True)
    skills_extraidas: Mapped[dict | None]  = mapped_column(JSONB)
    score_rh        : Mapped[float | None] = mapped_column(Float)
    score_mercado   : Mapped[float | None] = mapped_column(Float)
    score_curriculo : Mapped[float | None] = mapped_column(Float)
    processado_em   : Mapped[datetime | None] = mapped_column(DateTime)
    criado_em       : Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

    candidato: Mapped["Candidato"] = relationship(back_populates="curriculo")