import uuid
from datetime import datetime
from sqlalchemy import Float, DateTime, Text, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String as SAString
from app.db.session import Base

class Entrevista(Base):
    __tablename__ = "entrevistas"

    id               : Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidatura_id   : Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("candidaturas.id"))
    entrevistador_id : Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    tipo             : Mapped[str]         = mapped_column(String(20))
    # "rh" | "tecnica"

    status           : Mapped[str]         = mapped_column(String(20), default="agendada")
    # "agendada" | "realizada" | "cancelada"

    score_manual     : Mapped[float | None]= mapped_column(Float)
    # 0–10 — preenchido pelo entrevistador após a entrevista

    anotacoes        : Mapped[str | None]  = mapped_column(Text)
    # texto livre sem limite — o entrevistador escreve o que quiser

    pontos_fortes    : Mapped[list | None] = mapped_column(ARRAY(SAString))
    # ["comunicação clara", "domínio de Python"]

    pontos_fracos    : Mapped[list | None] = mapped_column(ARRAY(SAString))
    # ["pouca experiência com Docker"]

    agendada_para    : Mapped[datetime | None] = mapped_column(DateTime)
    realizada_em     : Mapped[datetime | None] = mapped_column(DateTime)
    criado_em        : Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

    candidatura  : Mapped["Candidatura"] = relationship(back_populates="entrevistas")
    entrevistador: Mapped["Usuario"]     = relationship(back_populates="entrevistas")