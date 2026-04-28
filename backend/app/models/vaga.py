import uuid
from datetime import datetime

from app.db.session import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Vaga(Base):
    __tablename__ = "vagas"

    id               : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome             : Mapped[str]       = mapped_column(String(200), nullable=False)
    requisitos_texto : Mapped[str]       = mapped_column(Text, nullable=False)
    vetor_vaga                           = mapped_column(Vector(384), nullable=True)
    ranking_mercado  : Mapped[dict | None] = mapped_column(JSONB)
    vetor_mercado                        = mapped_column(Vector(384), nullable=True)

    peso_rh          : Mapped[float]    = mapped_column(Float, default=0.6)
    peso_mercado     : Mapped[float]    = mapped_column(Float, default=0.4)
    peso_curriculo   : Mapped[float]    = mapped_column(Float, default=0.5)
    peso_entrevista_rh  : Mapped[float] = mapped_column(Float, default=0.25)
    peso_entrevista_tec : Mapped[float] = mapped_column(Float, default=0.25)

    status           : Mapped[str]      = mapped_column(String(20), default="aberta")
    # "aberta" | "pausada" | "fechada"

    gestores_ids     : Mapped[list | None] = mapped_column(JSONB, default=list)
    # [str(uuid), ...] — gestores técnicos atribuídos a esta vaga

    criado_em        : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    candidaturas: Mapped[list["Candidatura"]] = relationship(back_populates="vaga")
