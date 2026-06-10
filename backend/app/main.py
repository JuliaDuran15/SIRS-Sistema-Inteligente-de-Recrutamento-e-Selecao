import time

import app.db.base  # noqa: F401 — importa todos os models antes de qualquer endpoint
from app.api.endpoints import (
    analytics,
    auth,
    candidatos,
    candidaturas,
    entrevistas,
    usuarios,
    vagas,
    webhook,
)
from app.core.logger import get_logger
from app.db.ensure_admin import garantir_admin
from app.db.init_extensions import criar_extensoes
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger("HTTP")

criar_extensoes()
garantir_admin()

app = FastAPI(title="SIRS", version="0.1.0")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inicio = time.time()
        response = await call_next(request)
        duracao_ms = round((time.time() - inicio) * 1000)

        qs = f"?{request.url.query}" if request.url.query else ""
        linha = f"{request.method} {request.url.path}{qs} → {response.status_code} ({duracao_ms}ms)"
        if response.status_code >= 500:
            logger.error(linha)
        elif response.status_code >= 400:
            logger.warning(linha)
        else:
            logger.info(linha)

        return response


app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
            "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/auth",         tags=["auth"])
app.include_router(usuarios.router,     prefix="/usuarios",     tags=["usuarios"])
app.include_router(vagas.router,        prefix="/vagas",        tags=["vagas"])
app.include_router(candidatos.router,   prefix="/candidatos",   tags=["candidatos"])
app.include_router(candidaturas.router, prefix="/candidaturas", tags=["candidaturas"])
app.include_router(entrevistas.router,  prefix="/entrevistas",  tags=["entrevistas"])
app.include_router(webhook.router,      prefix="/webhook",      tags=["webhook"])
app.include_router(analytics.router,    prefix="/analytics",    tags=["analytics"])

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/reprocessar-curriculos", tags=["admin"])
def reprocessar_curriculos(_=__import__("app.core.auth", fromlist=["APENAS_ADMIN"]).APENAS_ADMIN):
    """
    Enfileira reprocessamento de todos os currículos com o modelo de embedding atual.
    Necessário após trocar EMBEDDING_MODEL no .env.
    """
    from app.ai.tasks import reprocessar_todos_curriculos
    result = reprocessar_todos_curriculos.delay()
    return {"task_id": result.id, "mensagem": "Reprocessamento enfileirado. Acompanhe nos logs do worker."}