"""Testes do endpoint POST /webhook/importar — JSON e XML."""
import json
from unittest.mock import patch, MagicMock

import pytest

from tests.conftest import make_candidato, make_vaga, make_usuario
from app.models.candidatura import StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.candidatura import Candidatura
from app.models.candidato import Candidato
from app.models.vaga import Vaga


_URL = "/webhook/importar"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _json(payload: dict, api_key: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Webhook-Key"] = api_key
    return headers


def _xml_bytes(xml: str) -> bytes:
    return xml.strip().encode()


_PAYLOAD_SIMPLES = {
    "fonte": "teste",
    "candidatos": [
        {
            "external_id": "ext_001",
            "nome": "Maria Webhook",
            "email": "maria.webhook@teste.com",
        }
    ],
}

_PAYLOAD_COMPLETO = {
    "fonte": "greenhouse",
    "vagas": [
        {
            "external_id": "vaga_01",
            "nome": "Engenheiro de Dados",
            "requisitos_texto": "Python, Spark, Kafka, SQL",
        }
    ],
    "candidatos": [
        {
            "external_id": "cand_01",
            "nome": "Carlos Import",
            "email": "carlos.import@teste.com",
            "cidade": "São Paulo",
            "estado": "SP",
            "formacao": [
                {
                    "curso": "Engenharia de Computação",
                    "instituicao": "USP",
                    "nivel": "graduacao",
                    "status": "concluido",
                    "ano_conclusao": 2019,
                }
            ],
            "curriculo_texto": "Engenheiro de dados com 4 anos em pipelines Spark e Kafka.",
            "vaga_external_id": "vaga_01",
        }
    ],
}


# ── Autenticação ──────────────────────────────────────────────────────────────

class TestApiKey:
    def test_sem_chave_configurada_aceita_sem_header(self, client):
        r = client.post(_URL, json=_PAYLOAD_SIMPLES,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200

    def test_chave_correta_aceita(self, client):
        with patch("app.api.endpoints.webhook.settings") as m:
            m.WEBHOOK_SECRET_KEY = "segredo123"
            r = client.post(_URL, json=_PAYLOAD_SIMPLES,
                            headers={**_json(_PAYLOAD_SIMPLES), "X-Webhook-Key": "segredo123"})
        assert r.status_code == 200

    def test_chave_errada_retorna_401(self, client):
        with patch("app.api.endpoints.webhook.settings") as m:
            m.WEBHOOK_SECRET_KEY = "segredo123"
            r = client.post(_URL, json=_PAYLOAD_SIMPLES,
                            headers={**_json(_PAYLOAD_SIMPLES), "X-Webhook-Key": "errado"})
        assert r.status_code == 401

    def test_sem_header_com_chave_configurada_retorna_401(self, client):
        with patch("app.api.endpoints.webhook.settings") as m:
            m.WEBHOOK_SECRET_KEY = "segredo123"
            r = client.post(_URL, json=_PAYLOAD_SIMPLES,
                            headers={"Content-Type": "application/json"})
        assert r.status_code == 401


# ── Importação JSON ───────────────────────────────────────────────────────────

class TestImportacaoJSON:
    def test_cria_candidato(self, client, db):
        r = client.post(_URL, json=_PAYLOAD_SIMPLES,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        assert body["importados"]["candidatos_criados"] == 1
        assert body["total_erros"] == 0

        cand = db.query(Candidato).filter(
            Candidato.email == "maria.webhook@teste.com"
        ).first()
        assert cand is not None

    def test_cria_vaga_candidato_candidatura(self, client, db):
        r = client.post(_URL, json=_PAYLOAD_COMPLETO,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        imp = body["importados"]
        assert imp["vagas_criadas"]        == 1
        assert imp["candidatos_criados"]   == 1
        assert imp["candidaturas_criadas"] == 1

    def test_formacao_importada(self, client, db):
        r = client.post(_URL, json=_PAYLOAD_COMPLETO,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        cand = db.query(Candidato).filter(
            Candidato.email == "carlos.import@teste.com"
        ).first()
        assert cand is not None
        assert len(cand.formacao) == 1
        assert cand.formacao[0]["curso"] == "Engenharia de Computação"

    def test_curriculo_texto_dispara_task(self, client, db):
        with patch("app.api.endpoints.webhook.processar_curriculo_texto") as mock_task:
            mock_task.delay = MagicMock()
            r = client.post(_URL, json=_PAYLOAD_COMPLETO,
                            headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        assert r.json()["importados"]["curriculos_processados"] == 1
        mock_task.delay.assert_called_once()

    def test_upsert_candidato_existente(self, client, db):
        """Segundo import com mesmo email atualiza em vez de criar."""
        make_candidato(db, nome="Carlos Antigo", email="upsert@teste.com")

        payload = {
            "candidatos": [
                {"nome": "Carlos Atualizado", "email": "upsert@teste.com", "cidade": "Campinas"}
            ]
        }
        r = client.post(_URL, json=payload,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        assert body["importados"]["candidatos_criados"]     == 0
        assert body["importados"]["candidatos_atualizados"] == 1

        cand = db.query(Candidato).filter(Candidato.email == "upsert@teste.com").first()
        assert cand.nome   == "Carlos Atualizado"
        assert cand.cidade == "Campinas"

    def test_candidatura_origem_externo(self, client, db):
        """Candidatura criada via webhook tem origem='externo' e fonte registrada."""
        r = client.post(_URL, json=_PAYLOAD_COMPLETO,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        cand = db.query(Candidato).filter(
            Candidato.email == "carlos.import@teste.com"
        ).first()
        candidatura = db.query(Candidatura).filter(
            Candidatura.candidato_id == cand.id
        ).first()
        assert candidatura is not None
        assert candidatura.origem == "externo"
        assert candidatura.fonte  == "greenhouse"

    def test_candidatura_nao_duplicada(self, client, db):
        """Importar o mesmo candidato+vaga duas vezes não cria candidatura dupla."""
        r1 = client.post(_URL, json=_PAYLOAD_COMPLETO,
                         headers={"Content-Type": "application/json"})
        r2 = client.post(_URL, json=_PAYLOAD_COMPLETO,
                         headers={"Content-Type": "application/json"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Segunda importação não cria nova candidatura
        assert r2.json()["importados"]["candidaturas_criadas"] == 0

    def test_vaga_nao_duplicada(self, client, db):
        """Importar a mesma vaga duas vezes não cria duplicata."""
        r1 = client.post(_URL, json=_PAYLOAD_COMPLETO,
                         headers={"Content-Type": "application/json"})
        assert r1.json()["importados"]["vagas_criadas"] == 1

        payload2 = {"vagas": [_PAYLOAD_COMPLETO["vagas"][0]], "candidatos": []}
        r2 = client.post(_URL, json=payload2,
                         headers={"Content-Type": "application/json"})
        # Vaga já existe → não cria outra
        assert r2.json()["importados"]["vagas_criadas"] == 0

    def test_vinculo_por_vaga_nome(self, client, db):
        """Candidato pode referenciar vaga pelo nome mesmo sem external_id."""
        vaga = make_vaga(db, nome="Vaga por Nome")
        payload = {
            "candidatos": [
                {
                    "nome": "Cand Nome", "email": "cand.nome@teste.com",
                    "vaga_nome": "Vaga por Nome",
                }
            ]
        }
        r = client.post(_URL, json=payload,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        assert r.json()["importados"]["candidaturas_criadas"] == 1

    def test_payload_vazio_retorna_400(self, client):
        r = client.post(_URL, json={"vagas": [], "candidatos": []},
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_corpo_vazio_retorna_400(self, client):
        r = client.post(_URL, content=b"",
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_json_invalido_retorna_400(self, client):
        r = client.post(_URL, content=b"{invalido",
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_erro_parcial_continua_importacao(self, client, db):
        """Um candidato inválido não interrompe os demais."""
        payload = {
            "candidatos": [
                {"nome": "OK", "email": "ok@teste.com"},
                {"nome": "Sem Email", "email": "nao-e-um-email"},  # inválido
                {"nome": "Tambem OK", "email": "tambem.ok@teste.com"},
            ]
        }
        r = client.post(_URL, json=payload,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        assert body["importados"]["candidatos_criados"] == 2
        assert body["total_erros"] == 1


# ── Importação XML ────────────────────────────────────────────────────────────

class TestImportacaoXML:
    _XML_SIMPLES = """
    <importacao fonte="xml_test">
      <candidatos>
        <candidato external_id="xml_01">
          <nome>Pedro XML</nome>
          <email>pedro.xml@teste.com</email>
          <cidade>Recife</cidade>
          <estado>PE</estado>
        </candidato>
      </candidatos>
    </importacao>
    """.encode()

    _XML_COMPLETO = """
    <importacao fonte="sap">
      <vagas>
        <vaga external_id="xml_vaga_01">
          <nome>Analista XML</nome>
          <requisitos_texto>XML, JSON, ETL, SQL</requisitos_texto>
        </vaga>
      </vagas>
      <candidatos>
        <candidato external_id="xml_cand_01" vaga_external_id="xml_vaga_01">
          <nome>Ana XML</nome>
          <email>ana.xml@teste.com</email>
          <telefone>81999998888</telefone>
          <cidade>Recife</cidade>
          <estado>PE</estado>
          <curriculo_texto>Analista com experiencia em ETL e integracao de dados.</curriculo_texto>
          <formacao>
            <item nivel="graduacao" status="concluido" ano_conclusao="2018">
              <curso>Sistemas de Informacao</curso>
              <instituicao>UFPE</instituicao>
            </item>
          </formacao>
        </candidato>
      </candidatos>
    </importacao>
    """.encode()

    def test_cria_candidato_via_xml(self, client, db):
        r = client.post(_URL, content=self._XML_SIMPLES,
                        headers={"Content-Type": "application/xml"})
        assert r.status_code == 200
        body = r.json()
        assert body["importados"]["candidatos_criados"] == 1

        cand = db.query(Candidato).filter(
            Candidato.email == "pedro.xml@teste.com"
        ).first()
        assert cand is not None
        assert cand.cidade == "Recife"

    def test_xml_completo_cria_vaga_candidatura(self, client, db):
        r = client.post(_URL, content=self._XML_COMPLETO,
                        headers={"Content-Type": "application/xml"})
        assert r.status_code == 200
        imp = r.json()["importados"]
        assert imp["vagas_criadas"]        == 1
        assert imp["candidatos_criados"]   == 1
        assert imp["candidaturas_criadas"] == 1

    def test_xml_formacao_importada(self, client, db):
        r = client.post(_URL, content=self._XML_COMPLETO,
                        headers={"Content-Type": "application/xml"})
        assert r.status_code == 200
        cand = db.query(Candidato).filter(
            Candidato.email == "ana.xml@teste.com"
        ).first()
        assert len(cand.formacao) == 1
        assert cand.formacao[0]["ano_conclusao"] == 2018

    def test_xml_invalido_retorna_400(self, client):
        r = client.post(_URL, content=b"<nao fechado",
                        headers={"Content-Type": "application/xml"})
        assert r.status_code == 400

    def test_text_xml_content_type_aceito(self, client, db):
        r = client.post(_URL, content=self._XML_SIMPLES,
                        headers={"Content-Type": "text/xml"})
        assert r.status_code == 200
