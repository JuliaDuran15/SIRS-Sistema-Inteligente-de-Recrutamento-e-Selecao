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
    # {"Python": 0.95, "Docker": 0.88, ...} vindo do Market Analyzer

    vetor_mercado = mapped_column(Vector(384), nullable=True)
    # vetor gerado pelo Market Analyzer
    # representa as top skills do mercado para aquele cargo

    # ── Pesos do score curricular ──────────────────────────────────
    peso_rh          : Mapped[float]      = mapped_column(Float, default=0.6)
    peso_mercado     : Mapped[float]      = mapped_column(Float, default=0.4)

        # ── Pesos do score consolidado final ──────────────────────────
    # (currículo + entrevista RH + entrevista técnica)
    peso_curriculo   : Mapped[float]      = mapped_column(Float, default=0.5)
    peso_entrevista_rh  : Mapped[float]   = mapped_column(Float, default=0.25)
    peso_entrevista_tec : Mapped[float]   = mapped_column(Float, default=0.25)

    status           : Mapped[str]        = mapped_column(String(20), default="aberta")
    # "aberta" | "pausada" | "fechada"
    criado_em        : Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    candidaturas: Mapped[list["Candidatura"]] = relationship(back_populates="vaga")