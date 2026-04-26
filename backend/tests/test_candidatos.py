"""Testes dos endpoints de candidatos — /candidatos/"""
import pytest
from tests.conftest import make_usuario, make_candidato, auth_header
from app.models.usuario import PapelUsuario


_CAND_PAYLOAD = {
    "nome": "Maria Silva",
    "email": "maria@candidato.com",
    "telefone": "11999990001",
    "formacao": [
        {
            "curso": "Ciência da Computação",
            "instituicao": "USP",
            "nivel": "graduacao",
            "status": "concluido",
            "ano_conclusao": 2020,
        }
    ],
}


class TestCriarCandidato:
    def test_rh_pode_criar(self, client, rh):
        r = client.post("/candidatos/", json=_CAND_PAYLOAD, headers=auth_header(rh))
        assert r.status_code == 201

    def test_retorna_campos_corretos(self, client, rh):
        r = client.post("/candidatos/", json=_CAND_PAYLOAD, headers=auth_header(rh))
        body = r.json()
        assert body["nome"] == "Maria Silva"
        assert body["email"] == "maria@candidato.com"
        assert body["origem"] == "manual"
        assert "id" in body

    def test_gestor_nao_pode_criar_403(self, client, gestor):
        r = client.post("/candidatos/", json=_CAND_PAYLOAD, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_sem_token_retorna_401(self, client):
        r = client.post("/candidatos/", json=_CAND_PAYLOAD)
        assert r.status_code == 401

    def test_admin_pode_criar(self, client, admin):
        payload = {**_CAND_PAYLOAD, "email": "admin_cria@candidato.com"}
        r = client.post("/candidatos/", json=payload, headers=auth_header(admin))
        assert r.status_code == 201

    def test_email_duplicado_retorna_400(self, client, rh, db):
        make_candidato(db, email="dup@candidato.com")
        r = client.post("/candidatos/",
                        json={**_CAND_PAYLOAD, "email": "dup@candidato.com"},
                        headers=auth_header(rh))
        assert r.status_code == 400

    def test_formacao_salva_corretamente(self, client, rh):
        r = client.post("/candidatos/", json=_CAND_PAYLOAD, headers=auth_header(rh))
        formacao = r.json()["formacao"]
        assert len(formacao) == 1
        assert formacao[0]["curso"] == "Ciência da Computação"


class TestWebhookCandidato:
    def test_webhook_sem_autenticacao(self, client):
        payload = {**_CAND_PAYLOAD, "email": "webhook@candidato.com"}
        r = client.post("/candidatos/webhook", json=payload)
        assert r.status_code == 201

    def test_webhook_define_origem_externo(self, client):
        payload = {**_CAND_PAYLOAD, "email": "webhook_ext@candidato.com"}
        r = client.post("/candidatos/webhook", json=payload)
        assert r.json()["origem"] == "externo"

    def test_webhook_email_duplicado_retorna_400(self, client, db):
        make_candidato(db, email="dup_webhook@candidato.com")
        r = client.post("/candidatos/webhook",
                        json={**_CAND_PAYLOAD, "email": "dup_webhook@candidato.com"})
        assert r.status_code == 400


class TestListarCandidatos:
    def test_rh_pode_listar(self, client, rh):
        r = client.get("/candidatos/", headers=auth_header(rh))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_gestor_pode_listar(self, client, gestor):
        r = client.get("/candidatos/", headers=auth_header(gestor))
        assert r.status_code == 200

    def test_sem_token_retorna_401(self, client):
        assert client.get("/candidatos/").status_code == 401

    def test_candidato_criado_aparece_na_lista(self, client, rh, candidato):
        nomes = [c["nome"] for c in client.get("/candidatos/",
                                                headers=auth_header(rh)).json()]
        assert candidato.nome in nomes


class TestBuscarCandidato:
    def test_buscar_por_id(self, client, rh, candidato):
        r = client.get(f"/candidatos/{candidato.id}", headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["email"] == candidato.email

    def test_id_inexistente_retorna_404(self, client, rh):
        r = client.get("/candidatos/00000000-0000-0000-0000-000000000000",
                       headers=auth_header(rh))
        assert r.status_code == 404

    def test_gestor_pode_buscar(self, client, gestor, candidato):
        r = client.get(f"/candidatos/{candidato.id}", headers=auth_header(gestor))
        assert r.status_code == 200


class TestAtualizarCandidato:
    def test_rh_pode_atualizar(self, client, rh, candidato):
        r = client.patch(f"/candidatos/{candidato.id}",
                         json={"nome": "João Atualizado"},
                         headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["nome"] == "João Atualizado"

    def test_gestor_nao_pode_atualizar(self, client, gestor, candidato):
        r = client.patch(f"/candidatos/{candidato.id}",
                         json={"nome": "Não Autorizado"},
                         headers=auth_header(gestor))
        assert r.status_code == 403

    def test_candidato_inexistente_retorna_404(self, client, rh):
        r = client.patch("/candidatos/00000000-0000-0000-0000-000000000000",
                         json={"nome": "Não Existe"},
                         headers=auth_header(rh))
        assert r.status_code == 404

    def test_atualizar_telefone(self, client, rh, candidato):
        r = client.patch(f"/candidatos/{candidato.id}",
                         json={"telefone": "11988887777"},
                         headers=auth_header(rh))
        assert r.json()["telefone"] == "11988887777"
