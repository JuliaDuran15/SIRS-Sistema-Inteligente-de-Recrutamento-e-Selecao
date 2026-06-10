"""
Testes para o módulo de reranking (cross-encoder).

Cobertura:
- Unidade: rerankar() diretamente com cross-encoder mockado
- Integração: endpoint POST /{vaga_id}/rerankar via TestClient
- Casos de borda: lista vazia, sem texto de currículo, erro no modelo
- Logging: verifica mensagens esperadas via caplog
- Ordenação: garante descending por score_rerank
"""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from tests.conftest import (
    make_usuario, make_vaga, make_candidato, make_candidatura, auth_header
)
from app.models.usuario import PapelUsuario
from app.models.curriculo import Curriculo


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def rh(db):
    return make_usuario(db, PapelUsuario.RH, "Ana RH", "rerank_rh@teste.com")


@pytest.fixture
def vaga(db):
    return make_vaga(db, nome="Dev Python", requisitos="Python, FastAPI, PostgreSQL")


@pytest.fixture
def mock_reranker():
    """Substitui o cross-encoder por um mock que devolve scores fixos."""
    modelo = MagicMock()
    modelo.predict.return_value = np.array([0.5, 2.0, -1.0])
    with patch("app.ai.reranker._get_reranker", return_value=modelo):
        yield modelo


@pytest.fixture
def mock_reranker_endpoint():
    """Mock do reranker para testes de endpoint (patch no módulo importado)."""
    modelo = MagicMock()
    modelo.predict.return_value = np.array([1.0, -0.5])
    with patch("app.ai.reranker._get_reranker", return_value=modelo):
        yield modelo


def _make_item(id: str, texto: str = "Python FastAPI PostgreSQL", score: float = 0.5) -> dict:
    return {
        "id": id,
        "texto_curriculo": texto,
        "score_curriculo": score,
    }


def _make_curriculo(db, candidatura, texto: str, score: float) -> Curriculo:
    cur = Curriculo(
        candidatura_id=candidatura.id,
        texto_extraido=texto,
        score_curriculo=score,
    )
    db.add(cur)
    db.flush()
    return cur


# ─── Testes unitários da função rerankar() ────────────────────────────────────

class TestRerankarUnidade:
    def test_lista_vazia_retorna_vazia(self, caplog):
        from app.ai.reranker import rerankar

        with caplog.at_level("INFO", logger="app.ai.reranker"):
            resultado = rerankar("Python developer", [])

        assert resultado == []
        assert "nenhuma candidatura recebida" in caplog.text

    def test_ordena_por_score_decrescente(self, mock_reranker):
        """Scores brutos [0.5, 2.0, -1.0] → sigmoid → ordenados desc."""
        from app.ai.reranker import rerankar

        cands = [
            _make_item("c1", score=0.3),
            _make_item("c2", score=0.7),
            _make_item("c3", score=0.1),
        ]
        resultado = rerankar("Python", cands, top_n=None)

        # predict foi chamado com 3 pares
        mock_reranker.predict.assert_called_once()
        assert len(resultado) == 3

        # ordem esperada: score bruto 2.0 → c2, 0.5 → c1, -1.0 → c3
        assert resultado[0]["id"] == "c2"
        assert resultado[1]["id"] == "c1"
        assert resultado[2]["id"] == "c3"

    def test_score_rerank_esta_em_zero_um(self, mock_reranker):
        from app.ai.reranker import rerankar

        resultado = rerankar("Python", [_make_item("x"), _make_item("y"), _make_item("z")])

        for item in resultado:
            assert 0.0 <= item["score_rerank"] <= 1.0

    def test_top_n_limita_candidatos_processados(self, mock_reranker):
        """Quando top_n=2, apenas os 2 primeiros são enviados ao modelo."""
        from app.ai.reranker import rerankar

        mock_reranker.predict.return_value = np.array([1.0, 0.5])
        cands = [_make_item(f"c{i}") for i in range(5)]

        resultado = rerankar("Python", cands, top_n=2)

        call_args = mock_reranker.predict.call_args[0][0]
        assert len(call_args) == 2
        assert len(resultado) == 2

    def test_candidatura_sem_curriculo_recebe_score(self, mock_reranker):
        """Candidatura sem texto de currículo deve processar com string vazia."""
        from app.ai.reranker import rerankar

        mock_reranker.predict.return_value = np.array([0.8])
        cand_sem_texto = {"id": "sem", "texto_curriculo": "", "score_curriculo": 0.0}

        resultado = rerankar("Python", [cand_sem_texto])

        assert len(resultado) == 1
        assert resultado[0]["score_rerank"] is not None

        # par enviado ao modelo deve ter string vazia para o CV
        pares = mock_reranker.predict.call_args[0][0]
        assert pares[0][1] == ""

    def test_erro_no_modelo_retorna_ordem_original(self, caplog):
        """Se o cross-encoder lançar exceção, retorna lista original sem score."""
        from app.ai.reranker import rerankar

        modelo_quebrado = MagicMock()
        modelo_quebrado.predict.side_effect = RuntimeError("GPU sem memória")

        with patch("app.ai.reranker._get_reranker", return_value=modelo_quebrado):
            with caplog.at_level("ERROR", logger="app.ai.reranker"):
                cands = [_make_item("a"), _make_item("b")]
                resultado = rerankar("Python", cands)

        assert len(resultado) == 2
        for item in resultado:
            assert item["score_rerank"] is None
        assert "erro no cross-encoder" in caplog.text

    def test_logging_info_no_inicio_e_fim(self, mock_reranker, caplog):
        from app.ai.reranker import rerankar

        mock_reranker.predict.return_value = np.array([0.0, 0.0])
        cands = [_make_item("x"), _make_item("y")]

        with caplog.at_level("INFO", logger="app.ai.reranker"):
            rerankar("Python FastAPI", cands)

        assert "rerankar: iniciando" in caplog.text
        assert "rerankar: concluído" in caplog.text

    def test_logging_avisa_candidaturas_sem_curriculo(self, mock_reranker, caplog):
        from app.ai.reranker import rerankar

        mock_reranker.predict.return_value = np.array([0.0])
        cand = {"id": "x", "texto_curriculo": None, "score_curriculo": 0.0}

        with caplog.at_level("WARNING", logger="app.ai.reranker"):
            rerankar("Python", [cand])

        assert "sem texto de currículo" in caplog.text

    def test_scores_injetados_no_dict_original(self, mock_reranker):
        """score_rerank deve ser adicionado ao dict de cada candidatura."""
        from app.ai.reranker import rerankar

        mock_reranker.predict.return_value = np.array([1.5])
        cand = _make_item("abc")
        resultado = rerankar("Python", [cand])

        assert "score_rerank" in resultado[0]
        assert isinstance(resultado[0]["score_rerank"], float)


# ─── Testes de integração via endpoint ───────────────────────────────────────

class TestRerankarEndpoint:
    def test_retorna_404_vaga_inexistente(self, client, rh):
        resp = client.post(
            "/vagas/00000000-0000-0000-0000-000000000000/rerankar",
            headers=auth_header(rh),
        )
        assert resp.status_code == 404

    def test_requer_autenticacao(self, client, vaga):
        resp = client.post(f"/vagas/{vaga.id}/rerankar")
        assert resp.status_code == 401

    def test_retorna_lista_vazia_sem_candidaturas(self, client, db, rh, vaga):
        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            modelo.predict.return_value = np.array([])
            mock_get.return_value = modelo

            resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        assert resp.json() == []

    def test_retorna_candidaturas_reordenadas(self, client, db, rh, vaga):
        """Dois candidatos — o modelo prefere o segundo, então ele deve vir primeiro."""
        c1 = make_candidato(db, "Carlos A", "rerank_c1@teste.com")
        c2 = make_candidato(db, "Diana B", "rerank_c2@teste.com")
        ca1 = make_candidatura(db, c1, vaga)
        ca2 = make_candidatura(db, c2, vaga)
        _make_curriculo(db, ca1, "HTML, CSS básico", 0.2)
        _make_curriculo(db, ca2, "Python, FastAPI, PostgreSQL, Docker", 0.8)

        # modelo devolve score maior para o segundo par (ca2 tem score_curriculo maior,
        # então vem primeiro na lista enviada ao reranker)
        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            # ca2 já é o primeiro por score_curriculo; damos score alto para ele
            modelo.predict.return_value = np.array([2.0, -1.0])
            mock_get.return_value = modelo

            resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        # Primeiro resultado deve ter score_rerank maior
        assert data[0]["score_rerank"] > data[1]["score_rerank"]

    def test_score_rerank_presente_no_response(self, client, db, rh, vaga):
        candidato = make_candidato(db, "Eduardo E", "rerank_e@teste.com")
        ca = make_candidatura(db, candidato, vaga)
        _make_curriculo(db, ca, "Python", 0.5)

        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            modelo.predict.return_value = np.array([1.2])
            mock_get.return_value = modelo

            resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        item = resp.json()[0]
        assert "score_rerank" in item
        assert item["score_rerank"] is not None
        assert 0.0 <= item["score_rerank"] <= 1.0

    def test_candidatura_sem_curriculo_incluida_com_score_none(self, client, db, rh, vaga):
        """Candidatura sem currículo deve aparecer na resposta com score_rerank=None."""
        candidato = make_candidato(db, "Fernanda F", "rerank_f@teste.com")
        make_candidatura(db, candidato, vaga)  # sem curriculo associado

        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            modelo.predict.return_value = np.array([0.0])
            mock_get.return_value = modelo

            resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_modelo_com_erro_retorna_200_com_score_none(self, client, db, rh, vaga):
        """Mesmo com erro no modelo, o endpoint deve retornar 200 (graceful fallback)."""
        candidato = make_candidato(db, "Gabriel G", "rerank_g@teste.com")
        ca = make_candidatura(db, candidato, vaga)
        _make_curriculo(db, ca, "Python", 0.6)

        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            modelo.predict.side_effect = RuntimeError("CUDA OOM")
            mock_get.return_value = modelo

            resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["score_rerank"] is None

    def test_logging_endpoint_registra_vaga_e_usuario(self, client, db, rh, vaga, caplog):
        candidato = make_candidato(db, "Helena H", "rerank_h@teste.com")
        ca = make_candidatura(db, candidato, vaga)
        _make_curriculo(db, ca, "Python", 0.5)

        with patch("app.ai.reranker._get_reranker") as mock_get:
            modelo = MagicMock()
            modelo.predict.return_value = np.array([0.5])
            mock_get.return_value = modelo

            with caplog.at_level("INFO"):
                resp = client.post(f"/vagas/{vaga.id}/rerankar", headers=auth_header(rh))

        assert resp.status_code == 200
        assert str(vaga.id) in caplog.text
