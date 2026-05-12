"""Testes dos endpoints de analytics — /analytics/resumo, /funil, /scores."""
import pytest
from app.models.candidatura import StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.usuario import PapelUsuario
from tests.conftest import (
    auth_header, make_candidato, make_candidatura,
    make_entrevista, make_usuario, make_vaga,
)


class TestResumoGeral:
    def test_retorna_estrutura_correta(self, client, rh):
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.status_code == 200
        for campo in (
            "vagas_abertas", "vagas_pausadas", "candidatos_total",
            "candidaturas_ativas", "em_triagem",
            "entrevistas_agendadas", "decisoes_pendentes", "contratados_total",
        ):
            assert campo in r.json()

    def test_sem_token_retorna_401(self, client):
        assert client.get("/analytics/resumo").status_code == 401

    def test_conta_vagas_abertas(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Vagas", "rh_vagas@a.com")
        make_vaga(db, nome="Resumo V1")
        make_vaga(db, nome="Resumo V2")
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["vagas_abertas"] >= 2

    def test_candidatos_totais_conta_distintos(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Dist", "rh_dist@a.com")
        v = make_vaga(db, nome="Resumo Dist")
        c1 = make_candidato(db, email="dist1@a.com")
        c2 = make_candidato(db, email="dist2@a.com")
        make_candidatura(db, c1, v)
        make_candidatura(db, c2, v)
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["candidatos_total"] >= 2

    def test_conta_em_triagem(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Triag", "rh_triag@a.com")
        v = make_vaga(db, nome="Resumo Triag")
        c = make_candidato(db, email="triag@a.com")
        make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["em_triagem"] >= 1

    def test_conta_entrevistas_agendadas(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Entrev", "rh_entrev@a.com")
        v = make_vaga(db, nome="Resumo Entrev")
        c = make_candidato(db, email="entrev@a.com")
        cand = make_candidatura(db, c, v)
        make_entrevista(db, cand, rh, tipo="rh", status="agendada")
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["entrevistas_agendadas"] >= 1

    def test_conta_contratados(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Cont", "rh_cont@a.com")
        v = make_vaga(db, nome="Resumo Cont")
        c = make_candidato(db, email="contrat@a.com")
        make_candidatura(db, c, v, StatusCandidatura.CONTRATADO)
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["contratados_total"] >= 1

    def test_gestor_ve_apenas_suas_vagas(self, client, db):
        g = make_usuario(db, PapelUsuario.GESTOR, "Gestor Escopo", "g_escopo@a.com")
        rh = make_usuario(db, PapelUsuario.RH, "RH Escopo", "rh_escopo@a.com")
        v_dele = make_vaga(db, nome="Vaga do Gestor", gestores_ids=[str(g.id)])
        v_outra = make_vaga(db, nome="Vaga Sem Gestor")
        c1 = make_candidato(db, email="escopo1@a.com")
        c2 = make_candidato(db, email="escopo2@a.com")
        make_candidatura(db, c1, v_dele,  StatusCandidatura.CONTRATADO)
        make_candidatura(db, c2, v_outra, StatusCandidatura.CONTRATADO)
        r_gestor = client.get("/analytics/resumo", headers=auth_header(g))
        r_rh     = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r_gestor.json()["contratados_total"] < r_rh.json()["contratados_total"]


class TestFunil:
    def test_retorna_estrutura_correta(self, client, rh):
        r = client.get("/analytics/funil", headers=auth_header(rh))
        assert r.status_code == 200
        assert "etapas" in r.json()
        assert "total" in r.json()

    def test_sem_token_retorna_401(self, client):
        assert client.get("/analytics/funil").status_code == 401

    def test_funil_vazio_sem_candidaturas(self, client, db):
        rh = make_usuario(db, PapelUsuario.RH, "RH Vazio", "rh_vazio@a.com")
        r = client.get("/analytics/funil", headers=auth_header(rh))
        assert r.json()["total"] == 0
        assert r.json()["etapas"] == []

    def test_filtra_por_vaga(self, client, rh, db):
        v1 = make_vaga(db, nome="Funil V1")
        v2 = make_vaga(db, nome="Funil V2")
        c1 = make_candidato(db, email="funil1@a.com")
        c2 = make_candidato(db, email="funil2@a.com")
        make_candidatura(db, c1, v1, StatusCandidatura.TRIAGEM_PENDENTE)
        make_candidatura(db, c2, v2, StatusCandidatura.CONTRATADO)
        r = client.get(f"/analytics/funil?vaga_id={v1.id}", headers=auth_header(rh))
        body = r.json()
        assert body["vaga_id"] == str(v1.id)
        assert body["total"] == 1
        assert body["etapas"][0]["status"] == "triagem_pendente"

    def test_inclui_apenas_etapas_com_candidatos(self, client, rh, db):
        v = make_vaga(db, nome="Funil Etapas")
        c = make_candidato(db, email="funil_etapa@a.com")
        make_candidatura(db, c, v, StatusCandidatura.CONTRATADO)
        r = client.get(f"/analytics/funil?vaga_id={v.id}", headers=auth_header(rh))
        etapas = r.json()["etapas"]
        assert len(etapas) == 1
        assert etapas[0]["status"] == "contratado"

    def test_total_correto_com_multiplos_status(self, client, rh, db):
        v = make_vaga(db, nome="Funil Multi")
        for i, st in enumerate([
            StatusCandidatura.TRIAGEM_PENDENTE,
            StatusCandidatura.APROVADO_TRIAGEM,
            StatusCandidatura.CONTRATADO,
        ]):
            c = make_candidato(db, email=f"funil_m{i}@a.com")
            make_candidatura(db, c, v, st)
        r = client.get(f"/analytics/funil?vaga_id={v.id}", headers=auth_header(rh))
        assert r.json()["total"] == 3

    def test_vaga_nome_retornado_quando_filtrado(self, client, rh, db):
        v = make_vaga(db, nome="Funil Nome Vaga")
        c = make_candidato(db, email="fnv@a.com")
        make_candidatura(db, c, v, StatusCandidatura.NOVO)
        r = client.get(f"/analytics/funil?vaga_id={v.id}", headers=auth_header(rh))
        assert r.json()["vaga_nome"] == "Funil Nome Vaga"

    def test_sem_filtro_vaga_id_nulo(self, client, rh):
        r = client.get("/analytics/funil", headers=auth_header(rh))
        assert r.json()["vaga_id"] is None


class TestDistribuicaoScores:
    def test_requer_vaga_id(self, client, rh):
        r = client.get("/analytics/scores", headers=auth_header(rh))
        assert r.status_code == 422

    def test_sem_token_retorna_401(self, client, vaga):
        assert client.get(f"/analytics/scores?vaga_id={vaga.id}").status_code == 401

    def test_retorna_10_buckets(self, client, rh, vaga):
        r = client.get(f"/analytics/scores?vaga_id={vaga.id}", headers=auth_header(rh))
        assert r.status_code == 200
        assert len(r.json()["buckets"]) == 10

    def test_media_mediana_none_sem_scores(self, client, rh, vaga):
        r = client.get(f"/analytics/scores?vaga_id={vaga.id}", headers=auth_header(rh))
        assert r.json()["media"] is None
        assert r.json()["mediana"] is None

    def test_calcula_media_e_mediana(self, client, rh, db):
        v = make_vaga(db, nome="Scores Calc")
        for i, score in enumerate([40.0, 60.0, 80.0]):
            c = make_candidato(db, email=f"score_c{i}@a.com")
            cand = make_candidatura(db, c, v)
            db.add(Curriculo(candidatura_id=cand.id, texto_extraido="x", score_curriculo=score))
        db.flush()
        r = client.get(f"/analytics/scores?vaga_id={v.id}", headers=auth_header(rh))
        body = r.json()
        assert body["media"] == 60.0
        assert body["mediana"] == 60.0

    def test_bucket_correto_para_score(self, client, rh, db):
        v = make_vaga(db, nome="Scores Bucket")
        c = make_candidato(db, email="bucket@a.com")
        cand = make_candidatura(db, c, v)
        db.add(Curriculo(candidatura_id=cand.id, texto_extraido="x", score_curriculo=75.0))
        db.flush()
        r = client.get(f"/analytics/scores?vaga_id={v.id}", headers=auth_header(rh))
        buckets = {b["faixa"]: b["quantidade"] for b in r.json()["buckets"]}
        assert buckets["70-80"] == 1
        assert buckets["60-70"] == 0
