import uuid
from datetime import date, datetime

from app.db.session import Base
from sqlalchemy import Date, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Candidato(Base):
    __tablename__ = "candidatos"

    id        : Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome      : Mapped[str]        = mapped_column(String(200), nullable=False)
    email     : Mapped[str]        = mapped_column(String(200), unique=True, nullable=False)
    telefone  : Mapped[str | None] = mapped_column(String(30))
    origem    : Mapped[str]        = mapped_column(String(30), default="manual")     # "manual" = RH cadastrou | "externo" = veio via webhook
    fonte     : Mapped[str | None] = mapped_column(String(100)) #"linkedin" "site_empresa"

    data_nascimento : Mapped[date | None] = mapped_column(Date)

    # Endereço separado em campos para facilitar filtros por cidade/estado
    logradouro  : Mapped[str | None] = mapped_column(String(255))
    numero      : Mapped[str | None] = mapped_column(String(20))
    complemento : Mapped[str | None] = mapped_column(String(100))
    bairro      : Mapped[str | None] = mapped_column(String(100))
    cidade      : Mapped[str | None] = mapped_column(String(100))
    estado      : Mapped[str | None] = mapped_column(String(2))
    cep         : Mapped[str | None] = mapped_column(String(9))


    # Formação acadêmica — JSONB porque pode ter mais de uma
    # [
    #   {
    #     "curso": "Análise e Desenvolvimento de Sistemas",
    #     "instituicao": "FATEC",
    #     "nivel": "tecnologo",
    #     "status": "concluido",
    #     "ano_conclusao": 2023
    #   }
    # ]
    formacao    : Mapped[dict | None] = mapped_column(JSONB, default=list)

    criado_em   : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    candidaturas : Mapped[list["Candidatura"]] = relationship(back_populates="candidato")