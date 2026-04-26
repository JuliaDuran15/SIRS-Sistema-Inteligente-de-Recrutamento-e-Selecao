import uuid
import enum
from datetime import datetime
from sqlalchemy import Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base

class StatusCandidatura(str, enum.Enum):
    NOVO                     = "novo"
    AGUARDANDO_PROC          = "aguardando_processamento"
    PROCESSANDO              = "processando_curriculo"
    TRIAGEM_PENDENTE         = "triagem_pendente"
    APROVADO_TRIAGEM         = "aprovado_triagem"
    REPROVADO_TRIAGEM        = "reprovado_triagem"
    ENTREVISTA_RH_AGENDADA   = "entrevista_rh_agendada"
    ENTREVISTA_RH_REALIZADA  = "entrevista_rh_realizada"
    REPROVADO_RH             = "reprovado_rh"
    ENTREVISTA_TEC_AGENDADA  = "entrevista_tec_agendada"
    ENTREVISTA_TEC_REALIZADA = "entrevista_tec_realizada"
    REPROVADO_TECNICO        = "reprovado_tecnico"
    DECISAO_PENDENTE         = "decisao_pendente"
    CONTRATADO               = "contratado"
    NAO_APROVADO             = "nao_aprovado"
    BANCO_TALENTOS           = "banco_de_talentos"

class Candidatura(Base):
    __tablename__ = "candidaturas"

    id           : Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidato_id : Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("candidatos.id"))
    vaga_id      : Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("vagas.id"))
    status       : Mapped[StatusCandidatura] = mapped_column(SAEnum(StatusCandidatura), default=StatusCandidatura.NOVO)
    score_total  : Mapped[float | None]      = mapped_column(Float)
    # score consolidado final — calculado após todas as entrevistas

    historico    : Mapped[dict | None]       = mapped_column(JSONB, default=list)
    # log de todas as transições de estado para auditoria
    # [{"de": "novo", "para": "aguardando_processamento", "em": "...", "ator": "sistema"}]

    criado_em    : Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow)
    atualizado_em: Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidato  : Mapped["Candidato"]        = relationship(back_populates="candidaturas")
    vaga       : Mapped["Vaga"]             = relationship(back_populates="candidaturas")
    entrevistas: Mapped[list["Entrevista"]] = relationship(back_populates="candidatura", order_by="Entrevista.agendada_para")
    curriculo  : Mapped["Curriculo"]        = relationship(back_populates="candidatura", uselist=False)