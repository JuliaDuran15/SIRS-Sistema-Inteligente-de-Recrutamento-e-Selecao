"""Testes dos endpoints de vagas — /vagas/"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import make_vaga, auth_header


_VAGA_PAYLOAD = {
    "nome": "Dev Python Sênior",
    "requisitos_texto": "Python, FastAPI, PostgreSQL, Docker",
}


class TestCriarVaga:
    def test_rh_pode_criar(self, client, rh):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(rh))
        assert r.status_code == 201

    def test_retorna_campos_corretos(self, client, rh):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(rh))
        body = r.json()
        assert body["nome"] == _VAGA_PAYLOAD["nome"]
        assert body["requisitos_texto"] == _VAGA_PAYLOAD["requisitos_texto"]
        assert body["status"] == "aberta"
        assert "id" in body

    def test_gestor_nao_pode_criar_403(self, client, gestor):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_sem_token_retorna_401(self, client):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD)
        assert r.status_code == 401

    def test_admin_pode_criar(self, client, admin):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(admin))
        assert r.status_code == 201

    def test_criar_dispara_tarefa_mercado(self, client, rh, mock_celery_tasks):
        _, mock_mercado = mock_celery_tasks
        client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(rh))
        mock_mercado.assert_called_once()

    def test_pesos_padrao_aplicados(self, client, rh):
        r = client.post("/vagas/", json=_VAGA_PAYLOAD, headers=auth_header(rh))
        body = r.json()
        assert body["peso_rh"] == 0.6
        assert body["peso_mercado"] == 0.4
        assert body["peso_curriculo"] == 0.50


class TestListarVagas:
    def test_retorna_lista(self, client, rh):
        r = client.get("/vagas/", headers=auth_header(rh))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_vaga_aberta_aparece(self, client, rh, db):
        make_vaga(db, nome="Vaga Listável")
        nomes = [v["nome"] for v in client.get("/vagas/", headers=auth_header(rh)).json()]
        assert "Vaga Listável" in nomes

    def test_vaga_fechada_aparece_por_ultimo(self, client, rh, db):
        """Vagas fechadas aparecem na lista mas ordenadas no fim."""
        v_fechada = make_vaga(db, nome="Vaga Fechada Ordenacao")
        v_fechada.status = "fechada"
        make_vaga(db, nome="Vaga Aberta Ordenacao")
        db.flush()
        lista = [v["nome"] for v in client.get("/vagas/", headers=auth_header(rh)).json()]
        # A vaga aberta deve vir antes da fechada
        idx_aberta = next((i for i, n in enumerate(lista) if n == "Vaga Aberta Ordenacao"), None)
        idx_fechada = next((i for i, n in enumerate(lista) if n == "Vaga Fechada Ordenacao"), None)
        assert idx_aberta is not None and idx_fechada is not None
        assert idx_aberta < idx_fechada

    def test_sem_token_retorna_401(self, client):
        assert client.get("/vagas/").status_code == 401

    def test_gestor_pode_listar(self, client, gestor, vaga):
        r = client.get("/vagas/", headers=auth_header(gestor))
        assert r.status_code == 200


class TestBuscarVaga:
    def test_buscar_por_id(self, client, rh, vaga):
        r = client.get(f"/vagas/{vaga.id}", headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["id"] == str(vaga.id)

    def test_id_inexistente_retorna_404(self, client, rh):
        r = client.get("/vagas/00000000-0000-0000-0000-000000000000",
                       headers=auth_header(rh))
        assert r.status_code == 404

    def test_gestor_pode_buscar(self, client, gestor, vaga):
        r = client.get(f"/vagas/{vaga.id}", headers=auth_header(gestor))
        assert r.status_code == 200


class TestAtualizarPesos:
    _PESOS = {
        "peso_rh": 0.7,
        "peso_mercado": 0.3,
        "peso_curriculo": 0.5,
        "peso_entrevista_rh": 0.25,
        "peso_entrevista_tec": 0.25,
    }

    def test_rh_pode_atualizar_pesos(self, client, rh, vaga):
        r = client.patch(f"/vagas/{vaga.id}/pesos",
                         json=self._PESOS, headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["peso_rh"] == 0.7

    def test_gestor_nao_pode_atualizar_pesos(self, client, gestor, vaga):
        r = client.patch(f"/vagas/{vaga.id}/pesos",
                         json=self._PESOS, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_vaga_inexistente_retorna_404(self, client, rh):
        r = client.patch("/vagas/00000000-0000-0000-0000-000000000000/pesos",
                         json=self._PESOS, headers=auth_header(rh))
        assert r.status_code == 404

    def test_atualizar_pesos_recalcula_score_curriculo(self, client, rh, db):
        from tests.conftest import make_candidato, make_candidatura
        from app.models.curriculo import Curriculo
        from app.models.candidatura import StatusCandidatura

        v = make_vaga(db, nome="Vaga Recalculo")
        c = make_candidato(db, email="recalculo@teste.com")
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)

        # Cria currículo com scores conhecidos
        cur = Curriculo(
            candidatura_id=cand.id,
            score_rh=80.0,       # 0–100
            score_mercado=60.0,  # 0–100
            score_curriculo=72.0,  # 0.8*0.6 + 0.6*0.4 = 0.72 → 72.0
        )
        db.add(cur)
        db.flush()

        # Muda para peso_rh=0.5, peso_mercado=0.5
        # Esperado: 0.8*0.5 + 0.6*0.5 = 0.7 → 70.0
        novos_pesos = {
            "peso_rh": 0.5, "peso_mercado": 0.5,
            "peso_curriculo": 0.5, "peso_entrevista_rh": 0.25, "peso_entrevista_tec": 0.25,
        }
        client.patch(f"/vagas/{v.id}/pesos", json=novos_pesos, headers=auth_header(rh))
        db.refresh(cur)
        assert cur.score_curriculo == pytest.approx(70.0, abs=0.2)


class TestAtualizarStatus:
    def test_rh_pode_pausar_vaga(self, client, rh, vaga):
        r = client.patch(f"/vagas/{vaga.id}/status",
                         params={"status": "pausada"}, headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["status"] == "pausada"

    def test_status_invalido_retorna_400(self, client, rh, vaga):
        r = client.patch(f"/vagas/{vaga.id}/status",
                         params={"status": "inexistente"}, headers=auth_header(rh))
        assert r.status_code == 400

    def test_gestor_nao_pode_alterar_status(self, client, gestor, vaga):
        r = client.patch(f"/vagas/{vaga.id}/status",
                         params={"status": "pausada"}, headers=auth_header(gestor))
        assert r.status_code == 403


class TestDeletarVaga:
    def test_admin_pode_deletar(self, client, admin, db):
        v = make_vaga(db, nome="Para Deletar")
        r = client.delete(f"/vagas/{v.id}", headers=auth_header(admin))
        assert r.status_code == 204

    def test_deletar_fecha_vaga(self, client, admin, db):
        v = make_vaga(db, nome="Fecha Ao Deletar")
        client.delete(f"/vagas/{v.id}", headers=auth_header(admin))
        db.refresh(v)
        assert v.status == "fechada"

    def test_rh_nao_pode_deletar(self, client, rh, vaga):
        r = client.delete(f"/vagas/{vaga.id}", headers=auth_header(rh))
        assert r.status_code == 403

    def test_gestor_nao_pode_deletar(self, client, gestor, vaga):
        r = client.delete(f"/vagas/{vaga.id}", headers=auth_header(gestor))
        assert r.status_code == 403


class TestAnalisarMercado:
    def test_rh_pode_analisar(self, client, rh, vaga):
        mock_resultado = {
            "vetor_mercado": [0.1] * 384,
            "termos_frequentes": [{"termo": "python", "frequencia": 10}],
            "total_vagas_analisadas": 5,
            "fonte": "kaggle",
        }
        with patch(
            "app.api.endpoints.vagas.analisar_mercado",
            new=AsyncMock(return_value=mock_resultado),
        ):
            r = client.post(f"/vagas/{vaga.id}/analisar-mercado",
                            headers=auth_header(rh))
        assert r.status_code == 200

    def test_gestor_nao_pode_analisar(self, client, gestor, vaga):
        r = client.post(f"/vagas/{vaga.id}/analisar-mercado",
                        headers=auth_header(gestor))
        assert r.status_code == 403
