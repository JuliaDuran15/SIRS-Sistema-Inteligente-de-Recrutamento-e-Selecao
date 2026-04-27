import uuid
from datetime import datetime

from app.db.session import Base
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy import String as SAString
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Entrevista(Base):
    __tablename__ = "entrevistas"

    id               : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidatura_id   : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("candidaturas.id"))
    entrevistador_id : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    tipo             : Mapped[str]          = mapped_column(String(20))
    # "rh" | "tecnica"

    status           : Mapped[str]          = mapped_column(String(20), default="agendada")
    # "agendada" | "realizada" | "cancelada"

    score_manual     : Mapped[float | None] = mapped_column(Float)
    # 0–10

    anotacoes        : Mapped[str | None]   = mapped_column(Text)

    historico_edicoes: Mapped[list | None]  = mapped_column(JSONB, default=list)
    # [{"texto_anterior": "...", "editado_em": "...", "editado_por": "..."}]

    pontos_fortes    : Mapped[list | None]  = mapped_column(ARRAY(SAString))
    pontos_fracos    : Mapped[list | None]  = mapped_column(ARRAY(SAString))

    agendada_para    : Mapped[datetime | None] = mapped_column(DateTime)
    realizada_em     : Mapped[datetime | None] = mapped_column(DateTime)
    criado_em        : Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

    candidatura  : Mapped["Candidatura"] = relationship(back_populates="entrevistas")
    entrevistador: Mapped["Usuario"]     = relationship(back_populates="entrevistas")
