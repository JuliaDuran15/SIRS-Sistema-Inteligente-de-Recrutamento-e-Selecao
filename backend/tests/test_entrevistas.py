"""Testes dos endpoints de entrevistas — /entrevistas/"""
from datetime import datetime, timedelta
from tests.conftest import (
    make_vaga, make_candidato,
    make_candidatura, make_entrevista, auth_header,
)
from app.models.candidatura import StatusCandidatura


def _dt_futuro():
    return (datetime.utcnow() + timedelta(days=3)).isoformat()


class TestAgendarEntrevista:
    def test_rh_agenda_entrevista_rh(self, client, rh, db):
        c = make_candidato(db, email="ag_rh@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))
        assert r.status_code == 201
        assert r.json()["tipo"] == "rh"
        assert r.json()["status"] == "agendada"

    def test_rh_pode_agendar_tecnica(self, client, rh, db):
        c = make_candidato(db, email="rh_ag_tec@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "tecnica",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))
        assert r.status_code == 201

    def test_gestor_nao_pode_agendar_nenhuma_entrevista(self, client, gestor, db):
        c = make_candidato(db, email="gestor_ag@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_gestor_nao_pode_agendar_tecnica_tambem(self, client, gestor, db):
        c = make_candidato(db, email="gestor_tec_ag@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "tecnica",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_admin_pode_agendar_qualquer_tipo(self, client, admin, db):
        c = make_candidato(db, email="adm_any@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(admin))
        assert r.status_code == 201

    def test_tipo_invalido_retorna_400(self, client, rh, db):
        c = make_candidato(db, email="tipo_inv@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "invalido",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))
        assert r.status_code == 400

    def test_sem_token_retorna_401(self, client, rh, db):
        c = make_candidato(db, email="no_tok@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)
        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        })
        assert r.status_code == 401

    def test_agendar_avanca_status_candidatura(self, client, rh, db):
        c = make_candidato(db, email="ag_status@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))

        db.refresh(cand)
        assert cand.status == StatusCandidatura.ENTREVISTA_RH_AGENDADA

    def test_candidatura_inexistente_retorna_404(self, client, rh):
        r = client.post("/entrevistas/", json={
            "candidatura_id": "00000000-0000-0000-0000-000000000000",
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))
        assert r.status_code == 404


class TestRegistrarResultado:
    _resultado = {
        "score_manual": 8.5,
        "anotacoes": "Candidato muito bom, comunicativo e proativo.",
        "pontos_fortes": ["comunicação", "proatividade"],
        "pontos_fracos": ["pouca experiência em Docker"],
    }

    def test_rh_registra_entrevista_rh(self, client, rh, db):
        c = make_candidato(db, email="reg_rh@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(rh))
        assert r.status_code == 200

    def test_resultado_campos_corretos(self, client, rh, db):
        c = make_candidato(db, email="reg_campos@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(rh))
        body = r.json()
        assert body["score_manual"] == 8.5
        assert body["anotacoes"] == self._resultado["anotacoes"]
        assert body["pontos_fortes"] == ["comunicação", "proatividade"]
        assert body["status"] == "realizada"

    def test_gestor_registra_entrevista_tecnica(self, client, gestor, db):
        c = make_candidato(db, email="reg_tec@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_TEC_AGENDADA)
        ent = make_entrevista(db, cand, gestor, tipo="tecnica")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(gestor))
        assert r.status_code == 200

    def test_rh_nao_pode_registrar_tecnica(self, client, rh, db):
        c = make_candidato(db, email="rh_tec_reg@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_TEC_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="tecnica")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(rh))
        assert r.status_code == 403

    def test_gestor_nao_pode_registrar_rh(self, client, gestor, db):
        c = make_candidato(db, email="gestor_rh_reg@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, gestor, tipo="rh")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_entrevista_ja_realizada_retorna_400(self, client, rh, db):
        c = make_candidato(db, email="ja_real@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(rh))
        assert r.status_code == 400

    def test_score_acima_de_10_retorna_400(self, client, rh, db):
        c = make_candidato(db, email="score_alto@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json={**self._resultado, "score_manual": 11.0},
                         headers=auth_header(rh))
        assert r.status_code == 400

    def test_score_negativo_retorna_400(self, client, rh, db):
        c = make_candidato(db, email="score_neg@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json={**self._resultado, "score_manual": -1.0},
                         headers=auth_header(rh))
        assert r.status_code == 400

    def test_registrar_avanca_status_candidatura(self, client, rh, db):
        c = make_candidato(db, email="reg_avanca@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")

        client.patch(f"/entrevistas/{ent.id}/resultado",
                     json=self._resultado, headers=auth_header(rh))
        db.refresh(cand)
        assert cand.status == StatusCandidatura.ENTREVISTA_RH_REALIZADA

    def test_entrevista_inexistente_retorna_404(self, client, rh):
        r = client.patch("/entrevistas/00000000-0000-0000-0000-000000000000/resultado",
                         json=self._resultado, headers=auth_header(rh))
        assert r.status_code == 404


class TestListarPorCandidatura:
    def test_lista_entrevistas_da_candidatura(self, client, rh, db):
        c = make_candidato(db, email="lista_ent@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        make_entrevista(db, cand, rh, tipo="rh")

        r = client.get(f"/entrevistas/candidatura/{cand.id}", headers=auth_header(rh))
        assert r.status_code == 200
        lista = r.json()
        assert len(lista) == 1
        assert lista[0]["tipo"] == "rh"

    def test_candidatura_sem_entrevistas_retorna_lista_vazia(self, client, rh, candidatura):
        r = client.get(f"/entrevistas/candidatura/{candidatura.id}",
                       headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json() == []

    def test_gestor_pode_listar(self, client, gestor, db):
        c = make_candidato(db, email="gestor_list_ent@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v)
        r = client.get(f"/entrevistas/candidatura/{cand.id}",
                       headers=auth_header(gestor))
        assert r.status_code == 200

    def test_sem_token_retorna_401(self, client, candidatura):
        r = client.get(f"/entrevistas/candidatura/{candidatura.id}")
        assert r.status_code == 401
