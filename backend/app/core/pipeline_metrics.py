import time
from dataclasses import dataclass, field

from app.core.logger import logger_pipeline


@dataclass
class EtapaPipeline:
    nome      : str
    inicio    : float = field(default_factory=time.time)
    fim       : float = None
    sucesso   : bool  = True
    detalhes  : dict  = field(default_factory=dict)

    @property
    def duracao_ms(self) -> float:
        if self.fim:
            return round((self.fim - self.inicio) * 1000, 1)
        return 0.0


class PipelineTracker:
    """
    Rastreia cada etapa do pipeline e exibe um resumo no terminal.

    Uso:
        tracker = PipelineTracker(candidatura_id="abc123")
        with tracker.etapa("Resume Parser"):
            resultado = parsear_curriculo(pdf)
            tracker.registrar(chars=len(resultado["texto"]))
        tracker.finalizar()
    """

    def __init__(self, candidatura_id: str):
        self.candidatura_id = candidatura_id
        self.inicio_total   = time.time()
        self.etapas         : list[EtapaPipeline] = []
        self._etapa_atual   : EtapaPipeline = None

        logger_pipeline.info(
            f"candidatura={candidatura_id} → iniciando pipeline"
        )

    def iniciar_etapa(self, nome: str) -> "PipelineTracker":
        self._etapa_atual = EtapaPipeline(nome=nome)
        logger_pipeline.debug(
            f"candidatura={self.candidatura_id} → [{nome}] iniciando..."
        )
        return self

    def registrar(self, **kwargs):
        """Registra métricas da etapa atual."""
        if self._etapa_atual:
            self._etapa_atual.detalhes.update(kwargs)

    def concluir_etapa(self):
        if self._etapa_atual:
            self._etapa_atual.fim = time.time()
            self.etapas.append(self._etapa_atual)

            detalhes_str = " | ".join(
                f"{k}={v}" for k, v in self._etapa_atual.detalhes.items()
            )
            logger_pipeline.info(
                f"candidatura={self.candidatura_id} → "
                f"[{self._etapa_atual.nome}] "
                f"concluído em {self._etapa_atual.duracao_ms}ms"
                + (f" | {detalhes_str}" if detalhes_str else "")
            )
            self._etapa_atual = None

    def registrar_erro(self, erro: Exception):
        if self._etapa_atual:
            self._etapa_atual.fim     = time.time()
            self._etapa_atual.sucesso = False
            self.etapas.append(self._etapa_atual)

            logger_pipeline.error(
                f"candidatura={self.candidatura_id} → "
                f"[{self._etapa_atual.nome}] "
                f"ERRO: {str(erro)}"
            )
            self._etapa_atual = None

    def finalizar(self):
        duracao_total = round((time.time() - self.inicio_total), 2)
        etapas_ok     = sum(1 for e in self.etapas if e.sucesso)
        etapas_erro   = sum(1 for e in self.etapas if not e.sucesso)

        # resumo visual no terminal
        separador = "─" * 60
        logger_pipeline.info(separador)
        logger_pipeline.info(
            f"candidatura={self.candidatura_id} → RESUMO DO PIPELINE"
        )
        logger_pipeline.info(separador)

        for etapa in self.etapas:
            status = "✓" if etapa.sucesso else "✗"
            logger_pipeline.info(
                f"  {status} {etapa.nome:<25} {etapa.duracao_ms:>8}ms"
            )

        logger_pipeline.info(separador)
        logger_pipeline.info(
            f"  Total: {duracao_total}s | "
            f"Etapas: {etapas_ok} ok / {etapas_erro} erro"
        )
        logger_pipeline.info(separador)

        return {
            "candidatura_id": self.candidatura_id,
            "duracao_total_s": duracao_total,
            "etapas"         : [
                {
                    "nome"      : e.nome,
                    "duracao_ms": e.duracao_ms,
                    "sucesso"   : e.sucesso,
                    "detalhes"  : e.detalhes,
                }
                for e in self.etapas
            ],
        }