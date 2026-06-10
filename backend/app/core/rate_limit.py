"""
Rate limiting simples usando Redis (janela fixa).

Usa o mesmo Redis já disponível para Celery — chaves com prefixo "rl:"
para não colidir com filas de tarefas.

Uso no endpoint:
    @router.post("/importar")
    async def importar(request: Request, ...):
        await checar_rate_limit(request, max_por_hora=60)
"""
import logging
import time

from app.core.config import settings
from fastapi import HTTPException, Request

_log = logging.getLogger("rate_limit")


def _redis_client():
    """Cria cliente Redis com decode_responses — importação tardia para evitar
    circular import e falha de boot quando Redis ainda não está disponível."""
    import redis as redis_lib
    return redis_lib.from_url(
        settings.CELERY_BROKER_URL,
        decode_responses=True,
        socket_connect_timeout=2,
    )


async def checar_rate_limit(
    request      : Request,
    max_por_hora : int = 60,
    max_por_minuto: int = 10,
) -> None:
    """
    Dependency que levanta 429 quando o cliente ultrapassa os limites.

    Dois limites combinados:
      • burst:  max_por_minuto requisições por minuto   (evita rajadas)
      • quota:  max_por_hora   requisições por hora     (limite total)

    Identificação do cliente: API key (X-Webhook-Key) quando presente,
    senão IP do request.
    """
    try:
        r = _redis_client()
        cliente = request.headers.get("X-Webhook-Key") or (request.client.host if request.client else "unknown")

        now         = int(time.time())
        minuto_key  = f"rl:webhook:{cliente}:m:{now // 60}"
        hora_key    = f"rl:webhook:{cliente}:h:{now // 3600}"

        pipe = r.pipeline()
        pipe.incr(minuto_key)
        pipe.expire(minuto_key, 90)       # TTL um pouco maior que 1 min para segurança
        pipe.incr(hora_key)
        pipe.expire(hora_key, 3700)
        resultados = pipe.execute()

        count_minuto = resultados[0]
        count_hora   = resultados[2]

        if count_minuto > max_por_minuto:
            raise HTTPException(
                status_code=429,
                detail=f"Muitas requisições. Máximo {max_por_minuto}/minuto.",
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(max_por_minuto)},
            )
        if count_hora > max_por_hora:
            raise HTTPException(
                status_code=429,
                detail=f"Cota horária excedida. Máximo {max_por_hora}/hora.",
                headers={"Retry-After": "3600", "X-RateLimit-Limit": str(max_por_hora)},
            )

    except HTTPException:
        raise
    except Exception as exc:
        # Redis fora do ar → deixa passar (fail open) para não bloquear integrações
        _log.warning("Rate limit check falhou (Redis indisponível?): %s", exc)
