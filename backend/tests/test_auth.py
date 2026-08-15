"""Testes do módulo de autenticação — /auth/login e /auth/me."""
import pytest
from unittest.mock import patch
from tests.conftest import make_usuario, auth_header
from app.models.usuario import PapelUsuario
from app.core.auth import criar_token, hash_senha, verificar_senha, exigir_papel
from fastapi import HTTPException

# Garante que smtp_configurado() retorna False em todos os testes desta suite
pytestmark = pytest.mark.usefixtures("_no_smtp")

@pytest.fixture(autouse=True)
def _no_smtp():
    with patch("app.api.endpoints.auth.smtp_configurado", return_value=False):
        yield


# ── Funções puras de auth ─────────────────────────────────────────────────────
class TestHashSenha:
    def test_hash_diferente_do_original(self):
        h = hash_senha("minha_senha")
        assert h != "minha_senha"

    def test_verificar_senha_correta(self):
        h = hash_senha("minha_senha")
        assert verificar_senha("minha_senha", h) is True

    def test_verificar_senha_errada(self):
        h = hash_senha("minha_senha")
        assert verificar_senha("outra_senha", h) is False


class TestCriarToken:
    def test_retorna_string(self):
        token = criar_token({"sub": "usuario@test.com"})
        assert isinstance(token, str)

    def test_token_nao_vazio(self):
        assert criar_token({"sub": "x@x.com"}) != ""

    def test_tokens_diferentes_para_payloads_diferentes(self):
        t1 = criar_token({"sub": "a@a.com"})
        t2 = criar_token({"sub": "b@b.com"})
        assert t1 != t2


# ── Endpoint POST /auth/login ─────────────────────────────────────────────────
class TestLogin:
    def test_login_valido_retorna_token(self, client, db):
        u = make_usuario(db, email="login_ok@teste.com")
        r = client.post("/auth/login", data={
            "username": "login_ok@teste.com",
            "password": "senha123",
        })
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_valido_retorna_dados_usuario(self, client, db):
        u = make_usuario(db, email="login_dados@teste.com", nome="Login Dados")
        r = client.post("/auth/login", data={
            "username": "login_dados@teste.com",
            "password": "senha123",
        })
        assert r.status_code == 200
        u_data = r.json()["usuario"]
        assert u_data["email"] == "login_dados@teste.com"
        assert u_data["nome"] == "Login Dados"

    def test_senha_errada_retorna_401(self, client, db):
        make_usuario(db, email="login_fail@teste.com")
        r = client.post("/auth/login", data={
            "username": "login_fail@teste.com",
            "password": "senha_errada",
        })
        assert r.status_code == 401

    def test_email_inexistente_retorna_401(self, client):
        r = client.post("/auth/login", data={
            "username": "nao_existe@teste.com",
            "password": "qualquer",
        })
        assert r.status_code == 401

    def test_usuario_inativo_retorna_403(self, client, db):
        u = make_usuario(db, email="inativo@teste.com")
        u.ativo = False
        db.flush()
        r = client.post("/auth/login", data={
            "username": "inativo@teste.com",
            "password": "senha123",
        })
        assert r.status_code == 403

    def test_login_rh_retorna_papel_correto(self, client, db):
        make_usuario(db, PapelUsuario.RH, email="rh_papel@teste.com")
        r = client.post("/auth/login", data={
            "username": "rh_papel@teste.com",
            "password": "senha123",
        })
        assert r.json()["usuario"]["papel"] == "rh"

    def test_login_gestor_retorna_papel_correto(self, client, db):
        make_usuario(db, PapelUsuario.GESTOR, email="gestor_papel@teste.com")
        r = client.post("/auth/login", data={
            "username": "gestor_papel@teste.com",
            "password": "senha123",
        })
        assert r.json()["usuario"]["papel"] == "gestor"


# ── Endpoint GET /auth/me ─────────────────────────────────────────────────────
class TestMe:
    def test_me_retorna_usuario_autenticado(self, client, rh):
        r = client.get("/auth/me", headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["email"] == rh.email

    def test_me_sem_token_retorna_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_token_invalido_retorna_401(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer token_invalido"})
        assert r.status_code == 401

    def test_me_retorna_nome_e_papel(self, client, gestor):
        r = client.get("/auth/me", headers=auth_header(gestor))
        body = r.json()
        assert body["nome"] == gestor.nome
        assert body["papel"] == "gestor"


# ── Endpoint PATCH /auth/senha ───────────────────────────────────────────────
class TestAlterarSenha:
    def test_altera_senha_com_sucesso(self, client, db):
        u = make_usuario(db, email="troca_senha@teste.com")
        r = client.patch("/auth/senha", json={
            "senha_atual": "senha123",
            "senha_nova": "novasenha456",
        }, headers=auth_header(u))
        assert r.status_code == 204

    def test_pode_logar_com_nova_senha(self, client, db):
        make_usuario(db, email="nova_login@teste.com")
        client.patch("/auth/senha", json={
            "senha_atual": "senha123",
            "senha_nova": "novasenha456",
        }, headers=auth_header(make_usuario(db, email="nova_login2@teste.com")))
        # tenta logar com nova senha
        r = client.post("/auth/login", data={
            "username": "nova_login2@teste.com",
            "password": "novasenha456",
        })
        assert r.status_code == 200

    def test_senha_atual_errada_retorna_400(self, client, rh):
        r = client.patch("/auth/senha", json={
            "senha_atual": "senha_errada",
            "senha_nova": "novasenha456",
        }, headers=auth_header(rh))
        assert r.status_code == 400

    def test_senha_nova_curta_retorna_400(self, client, rh):
        r = client.patch("/auth/senha", json={
            "senha_atual": "senha123",
            "senha_nova": "abc",
        }, headers=auth_header(rh))
        assert r.status_code == 400

    def test_sem_token_retorna_401(self, client):
        r = client.patch("/auth/senha", json={
            "senha_atual": "senha123",
            "senha_nova": "novasenha456",
        })
        assert r.status_code == 401


# ── Forgot / Reset password ──────────────────────────────────────────────────
class TestEsqueceuSenha:
    def test_email_valido_retorna_reset_url(self, client, db):
        make_usuario(db, email="forgot@teste.com")
        r = client.post("/auth/esqueceu-senha", json={"email": "forgot@teste.com"})
        assert r.status_code == 200
        body = r.json()
        # Sem SMTP configurado em testes, devolve reset_url
        assert body["reset_url"] is not None
        assert "token=" in body["reset_url"]

    def test_email_inexistente_retorna_200(self, client):
        r = client.post("/auth/esqueceu-senha", json={"email": "nao_existe@teste.com"})
        assert r.status_code == 200
        assert r.json()["enviado"] is True
        assert r.json()["reset_url"] is None

    def test_usuario_inativo_retorna_200(self, client, db):
        u = make_usuario(db, email="inativo_forgot@teste.com")
        u.ativo = False
        db.flush()
        r = client.post("/auth/esqueceu-senha", json={"email": "inativo_forgot@teste.com"})
        assert r.status_code == 200
        assert r.json()["enviado"] is True
        assert r.json()["reset_url"] is None


class TestResetarSenha:
    def _obter_token(self, client, db, email="reset_user@teste.com"):
        make_usuario(db, email=email)
        r = client.post("/auth/esqueceu-senha", json={"email": email})
        url = r.json()["reset_url"]
        return url.split("token=")[1]

    def test_resetar_com_token_valido(self, client, db):
        token = self._obter_token(client, db)
        r = client.post("/auth/resetar-senha", json={
            "reset_token": token,
            "senha_nova": "novasenha456",
        })
        assert r.status_code == 204

    def test_pode_logar_com_nova_senha(self, client, db):
        make_usuario(db, email="reset_login@teste.com")
        r = client.post("/auth/esqueceu-senha", json={"email": "reset_login@teste.com"})
        token = r.json()["reset_url"].split("token=")[1]

        client.post("/auth/resetar-senha", json={
            "reset_token": token,
            "senha_nova": "novasenha456",
        })
        r2 = client.post("/auth/login", data={
            "username": "reset_login@teste.com",
            "password": "novasenha456",
        })
        assert r2.status_code == 200

    def test_token_invalido_retorna_400(self, client):
        r = client.post("/auth/resetar-senha", json={
            "reset_token": "token.invalido.aqui",
            "senha_nova": "novasenha456",
        })
        assert r.status_code == 400

    def test_senha_nova_curta_retorna_400(self, client, db):
        token = self._obter_token(client, db, "reset_curta@teste.com")
        r = client.post("/auth/resetar-senha", json={
            "reset_token": token,
            "senha_nova": "abc",
        })
        assert r.status_code == 400

    def test_token_de_login_nao_funciona_para_reset(self, client, rh):
        from tests.conftest import token_para
        token_login = token_para(rh)
        r = client.post("/auth/resetar-senha", json={
            "reset_token": token_login,
            "senha_nova": "novasenha456",
        })
        assert r.status_code == 400


# ── Guards de permissão ───────────────────────────────────────────────────────
class TestExigirPapel:
    def test_papel_correto_passa(self, db):
        u = make_usuario(db, PapelUsuario.RH, email="guard_rh@teste.com")
        dep = exigir_papel("rh", "admin")
        # Não deve lançar exceção
        resultado = dep(usuario=u)
        assert resultado == u

    def test_papel_errado_lanca_403(self, db):
        u = make_usuario(db, PapelUsuario.GESTOR, email="guard_gestor@teste.com")
        dep = exigir_papel("rh", "admin")
        with pytest.raises(HTTPException) as exc:
            dep(usuario=u)
        assert exc.value.status_code == 403

    def test_admin_passa_em_qualquer_restricao(self, db):
        u = make_usuario(db, PapelUsuario.ADMIN, email="guard_admin@teste.com")
        dep = exigir_papel("rh", "admin")
        resultado = dep(usuario=u)
        assert resultado == u
