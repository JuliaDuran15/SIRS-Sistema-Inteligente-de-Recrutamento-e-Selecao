"""Testes dos endpoints de entrevistas — /entrevistas/"""
from datetime import datetime, timedelta
from tests.conftest import (
    make_vaga, make_candidato, make_usuario,
    make_candidatura, make_entrevista, auth_header,
)
from app.models.usuario import PapelUsuario
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

    def test_rh_sem_permissao_nao_pode_agendar(self, client, rh, db):
        """RH não autorizado na vaga recebe 403 ao tentar agendar entrevista."""
        outro_rh = make_usuario(db, PapelUsuario.RH, "Outro RH Ag", "outro_rh_ag@teste.com")
        c = make_candidato(db, email="rh_nao_aut_ag@teste.com")
        v = make_vaga(db, rhs_autorizados=[str(outro_rh.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(rh))
        assert r.status_code == 403

    def test_gestor_nao_pode_agendar_entrevista_rh(self, client, gestor, db):
        """Gestor nunca pode agendar entrevistas de RH, mesmo sendo da vaga."""
        c = make_candidato(db, email="gestor_ag_rh@teste.com")
        v = make_vaga(db, gestores_ids=[str(gestor.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_gestor_da_vaga_pode_agendar_tecnica(self, client, gestor, db):
        """Gestor atribuído à vaga pode agendar entrevista técnica."""
        c = make_candidato(db, email="gestor_tec_ok@teste.com")
        v = make_vaga(db, gestores_ids=[str(gestor.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)

        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "tecnica",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(gestor))
        assert r.status_code == 201
        assert r.json()["tipo"] == "tecnica"

    def test_gestor_sem_atribuicao_nao_pode_agendar_tecnica(self, client, gestor, db):
        """Gestor não atribuído à vaga não pode agendar entrevista técnica."""
        c = make_candidato(db, email="gestor_tec_nao@teste.com")
        v = make_vaga(db)  # sem gestores_ids
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

    def test_gestor_agendar_tecnica_avanca_status_candidatura(self, client, gestor, db):
        c = make_candidato(db, email="gestor_ag_status@teste.com")
        v = make_vaga(db, gestores_ids=[str(gestor.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)

        client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "tecnica",
            "agendada_para": _dt_futuro(),
        }, headers=auth_header(gestor))

        db.refresh(cand)
        assert cand.status == StatusCandidatura.ENTREVISTA_TEC_AGENDADA

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

    def test_reeditar_entrevista_realizada_retorna_200(self, client, rh, db):
        """Re-editar uma entrevista já realizada é permitido."""
        c = make_candidato(db, email="ja_real@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        ent = make_entrevista(db, cand, rh, tipo="rh", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/resultado",
                         json=self._resultado, headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["score_manual"] == self._resultado["score_manual"]

    def test_reeditar_grava_historico(self, client, rh, db):
        """Re-edição deve registrar os valores anteriores no historico_edicoes."""
        c = make_candidato(db, email="reeditar_hist@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        ent = make_entrevista(db, cand, rh, tipo="rh", status="realizada")
        ent.score_manual = 5.0
        ent.anotacoes    = "Nota original"
        db.flush()

        client.patch(f"/entrevistas/{ent.id}/resultado",
                     json={**self._resultado, "score_manual": 9.0},
                     headers=auth_header(rh))
        db.refresh(ent)
        assert len(ent.historico_edicoes) == 1
        assert ent.historico_edicoes[0]["score_anterior"] == 5.0
        assert ent.historico_edicoes[0]["texto_anterior"] == "Nota original"

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


class TestEditarAnotacoes:
    _anot = {"anotacoes": "Candidato revisado após reflexão mais detalhada."}

    def test_rh_edita_anotacoes_entrevista_rh(self, client, rh, db):
        c = make_candidato(db, email="edit_anot_rh@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        ent = make_entrevista(db, cand, rh, tipo="rh", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["anotacoes"] == self._anot["anotacoes"]

    def test_rh_nao_pode_editar_tecnica_403(self, client, rh, db):
        c = make_candidato(db, email="edit_anot_rh_tec@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_TEC_REALIZADA)
        ent = make_entrevista(db, cand, rh, tipo="tecnica", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(rh))
        assert r.status_code == 403

    def test_gestor_da_vaga_edita_tecnica(self, client, gestor, db):
        c = make_candidato(db, email="edit_anot_gest@teste.com")
        v = make_vaga(db, gestores_ids=[str(gestor.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_TEC_REALIZADA)
        ent = make_entrevista(db, cand, gestor, tipo="tecnica", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(gestor))
        assert r.status_code == 200

    def test_gestor_sem_atribuicao_nao_pode_editar_403(self, client, gestor, db):
        c = make_candidato(db, email="edit_anot_notvaga@teste.com")
        v = make_vaga(db)  # vaga sem gestores
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_TEC_REALIZADA)
        ent = make_entrevista(db, cand, gestor, tipo="tecnica", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_gestor_nao_pode_editar_rh_403(self, client, gestor, db):
        c = make_candidato(db, email="edit_anot_gest_rh@teste.com")
        v = make_vaga(db, gestores_ids=[str(gestor.id)])
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        rh_user = make_usuario(db, email="rh_edit_anot@teste.com")
        ent = make_entrevista(db, cand, rh_user, tipo="rh", status="realizada")

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_historico_registrado(self, client, rh, db):
        c = make_candidato(db, email="edit_hist@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        ent = make_entrevista(db, cand, rh, tipo="rh", status="realizada")
        ent.anotacoes = "Texto original"
        db.flush()

        client.patch(f"/entrevistas/{ent.id}/anotacoes",
                     json=self._anot, headers=auth_header(rh))
        db.refresh(ent)
        assert len(ent.historico_edicoes) == 1
        assert ent.historico_edicoes[0]["texto_anterior"] == "Texto original"
        assert ent.historico_edicoes[0]["editado_por"] == rh.nome

    def test_nao_realizada_retorna_400(self, client, rh, db):
        c = make_candidato(db, email="edit_agendada@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_AGENDADA)
        ent = make_entrevista(db, cand, rh, tipo="rh")  # status=agendada

        r = client.patch(f"/entrevistas/{ent.id}/anotacoes",
                         json=self._anot, headers=auth_header(rh))
        assert r.status_code == 400


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
