"""
Fixtures compartilhadas para todos os testes.

Estratégia de banco:
- Uma vez por sessão: cria sirs_test_db, extension vector, todas as tabelas.
- Por teste: abre uma conexão, começa uma transação, usa SAVEPOINT para que
  os commits do endpoint não persistam — rollback no final isola cada teste.
- Célery/AI: patchados para não rodar de verdade.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# ── URLs ─────────────────────────────────────────────────────────────────────
# Derivadas de DATABASE_URL para funcionar tanto no Docker (host=db)
# quanto no CI do GitHub Actions (host=localhost).
from app.core.config import settings as _settings
_base = _settings.DATABASE_URL.rsplit("/", 1)[0]   # strip nome do banco
ADMIN_DB_URL = _settings.DATABASE_URL
TEST_DB_URL  = f"{_base}/sirs_test_db"

# ── Criação/destruição da base de teste (escopo de sessão) ────────────────────
@pytest.fixture(scope="session", autouse=True)
def test_database():
    admin = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS sirs_test_db"))
        conn.execute(text("CREATE DATABASE sirs_test_db"))
    admin.dispose()

    eng = create_engine(TEST_DB_URL)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    from app.db.session import Base
    Base.metadata.create_all(eng)
    eng.dispose()

    yield

    eng2 = create_engine(TEST_DB_URL)
    from app.db.session import Base as B
    B.metadata.drop_all(eng2)
    eng2.dispose()

    admin2 = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin2.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS sirs_test_db"))
    admin2.dispose()


@pytest.fixture(scope="session")
def engine(test_database):
    eng = create_engine(TEST_DB_URL)
    yield eng
    eng.dispose()


# ── Sessão por teste com rollback automático ──────────────────────────────────
@pytest.fixture
def db(engine):
    """
    Sessão isolada por teste via savepoint.
    Qualquer commit() dentro dos endpoints fica contido no savepoint;
    o rollback externo desfaz tudo ao fim do teste.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── TestClient com DB injetado ────────────────────────────────────────────────
@pytest.fixture
def client(db):
    from app.main import app
    from app.db.session import get_db

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Patch global de Celery e AI ───────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Impede que tarefas Celery disparem de verdade durante os testes."""
    with patch("app.ai.tasks.processar_curriculo.delay") as m1, \
         patch("app.ai.tasks.atualizar_mercado_vaga.delay") as m2:
        m1.return_value = MagicMock(id="fake-task-id")
        m2.return_value = MagicMock(id="fake-task-id")
        yield m1, m2


@pytest.fixture(autouse=True)
def mock_vetorizar():
    """Evita carregar o modelo de embeddings durante testes de API."""
    with patch("app.ai.resume_parser.vetorizar_texto", return_value=[0.1] * 384), \
         patch("app.api.endpoints.vagas.vetorizar_texto", return_value=[0.1] * 384):
        yield


@pytest.fixture(autouse=True)
def mock_rate_limit():
    """Desativa o rate limiter durante testes — evita 429 por acúmulo no Redis."""
    with patch("app.api.endpoints.webhook.checar_rate_limit", new_callable=AsyncMock):
        yield


# ── Factories ─────────────────────────────────────────────────────────────────
from app.models.usuario import Usuario, PapelUsuario
from app.models.vaga import Vaga
from app.models.candidato import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.entrevista import Entrevista
from app.models.curriculo import Curriculo  # garante que a tabela curriculos é criada no banco de testes
from app.core.auth import hash_senha, criar_token
from datetime import datetime, timedelta


def make_usuario(
    db, papel=PapelUsuario.RH,
    nome="Teste RH", email="rh@teste.com",
) -> Usuario:
    u = Usuario(
        nome=nome, email=email,
        senha_hash=hash_senha("senha123"),
        papel=papel, ativo=True,
    )
    db.add(u)
    db.flush()
    return u


def token_para(usuario: Usuario) -> str:
    return criar_token({"sub": usuario.email, "papel": usuario.papel})


def auth_header(usuario: Usuario) -> dict:
    return {"Authorization": f"Bearer {token_para(usuario)}"}


def make_vaga(
    db,
    nome="Dev Python",
    requisitos="Python, FastAPI, PostgreSQL",
    gestores_ids=None,
    criado_por_id=None,
    rhs_autorizados=None,
) -> Vaga:
    v = Vaga(
        nome=nome,
        requisitos_texto=requisitos,
        vetor_vaga=[0.1] * 384,
        peso_rh=0.6, peso_mercado=0.4,
        peso_curriculo=0.5,
        peso_entrevista_rh=0.25,
        peso_entrevista_tec=0.25,
        status="aberta",
        gestores_ids=gestores_ids or [],
        criado_por_id=criado_por_id,
        rhs_autorizados=rhs_autorizados,
    )
    db.add(v)
    db.flush()
    return v


def make_candidato(
    db,
    nome="João Silva",
    email="joao@teste.com",
) -> Candidato:
    c = Candidato(nome=nome, email=email, formacao=[])
    db.add(c)
    db.flush()
    return c


def make_candidatura(
    db,
    candidato: Candidato,
    vaga: Vaga,
    status: StatusCandidatura = StatusCandidatura.NOVO,
    origem: str = "manual",
    fonte: str | None = None,
) -> Candidatura:
    c = Candidatura(
        candidato_id=candidato.id,
        vaga_id=vaga.id,
        status=status,
        historico=[],
        origem=origem,
        fonte=fonte,
    )
    db.add(c)
    db.flush()
    return c


def make_entrevista(
    db,
    candidatura: Candidatura,
    entrevistador: Usuario,
    tipo: str = "rh",
    status: str = "agendada",
) -> Entrevista:
    e = Entrevista(
        candidatura_id=candidatura.id,
        entrevistador_id=entrevistador.id,
        tipo=tipo,
        status=status,
        agendada_para=datetime.utcnow() + timedelta(days=1),
    )
    db.add(e)
    db.flush()
    return e


def make_pdf_bytes() -> bytes:
    """PDF mínimo válido para testes de upload."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Curriculo teste) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f\n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n0\n%%EOF"
    )


# ── Fixtures de conveniência ──────────────────────────────────────────────────
@pytest.fixture
def rh(db):
    return make_usuario(db, PapelUsuario.RH, "Ana RH", "ana@teste.com")


@pytest.fixture
def gestor(db):
    return make_usuario(db, PapelUsuario.GESTOR, "Carlos Gestor", "carlos@teste.com")


@pytest.fixture
def admin(db):
    return make_usuario(db, PapelUsuario.ADMIN, "Admin Teste", "admin_t@teste.com")


@pytest.fixture
def vaga(db):
    return make_vaga(db)


@pytest.fixture
def candidato(db):
    return make_candidato(db)


@pytest.fixture
def candidatura(db, candidato, vaga):
    return make_candidatura(db, candidato, vaga)
