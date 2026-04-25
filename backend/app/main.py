import app.db.base  # noqa: F401 — importa todos os models antes de qualquer endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_extensions import criar_extensoes
from app.db.ensure_admin import garantir_admin
from app.api.endpoints import auth, usuarios, vagas, candidatos, candidaturas, entrevistas

criar_extensoes()
garantir_admin()

app = FastAPI(title="SIRS", version="0.1.0")

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

@app.get("/health")
def health():
    return {"status": "ok"}