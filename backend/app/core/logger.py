import logging
import sys
from datetime import datetime

# ── Formatter customizado ──────────────────────────────────────────────────

class SIRSFormatter(logging.Formatter):
    """
    Formato legível para o terminal com cores por nível.
    Funciona tanto no terminal quanto nos logs do Docker.
    """

    CORES = {
        "DEBUG"   : "\033[36m",   # ciano
        "INFO"    : "\033[32m",   # verde
        "WARNING" : "\033[33m",   # amarelo
        "ERROR"   : "\033[31m",   # vermelho
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"
    BOLD  = "\033[1m"

    def format(self, record):
        cor   = self.CORES.get(record.levelname, "")
        reset = self.RESET
        bold  = self.BOLD

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        nivel     = f"{cor}{record.levelname:<8}{reset}"
        modulo    = f"{bold}[{record.name}]{reset}"
        mensagem  = record.getMessage()

        return f"{timestamp} | {nivel} | {modulo} {mensagem}"


def get_logger(nome: str) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo.
    Uso: logger = get_logger("RESUME PARSER")
    """
    logger = logging.getLogger(nome)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SIRSFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger


# Loggers pré-configurados para cada módulo do sistema
logger_parser   = get_logger("RESUME PARSER")
logger_matching = get_logger("MATCHING ENGINE")
logger_mercado  = get_logger("MARKET ANALYZER")
logger_pipeline = get_logger("PIPELINE")
logger_api      = get_logger("API")