"""
Testes de integração end-to-end — fluxo completo de seleção.

Cada cenário percorre o pipeline via endpoints reais, verificando que
os estados e os dados persistem corretamente a cada etapa.

Pré-requisito de estado que envolve Celery (NOVO → TRIAGEM_PENDENTE)
é criado diretamente via factory, pois as tasks são mockadas em todos
os testes (ver conftest.mock_celery_tasks). O resto do pipeline é
exercitado inteiramente pela API.
"""
from datetime import datetime, timedelta

import pytest
from app.models.candidatura import StatusCandidatura
from app.models.usuario import PapelUsuario
from tests.conftest import (
    auth_header, make_candidato, make_candidatura,
    make_usuario, make_vaga,
)


class TestFluxoContratacao:
    """Caminho feliz: candidato passa por todo o processo e é contratado."""

    def test_pipeline_completo(self, client, db):
        rh     = make_usuario(db, PapelUsuario.RH,     "Ana RH",       "ana_pipe@a.com")
        gestor = make_usuario(db, PapelUsuario.GESTOR,  "Carlos Gestor","carlos_pipe@a.com")
        admin  = make_usuario(db, PapelUsuario.ADMIN,   "Admin",        "admin_pipe@a.com")

        vaga = make_vaga(db, nome="Engenheiro Pipeline",
                         gestores_ids=[str(gestor.id)])
        candidato   = make_candidato(db, nome="João Pipeline", email="joao_pipe@a.com")
        candidatura = make_candidatura(db, candidato, vaga, StatusCandidatura.TRIAGEM_PENDENTE)
        cid = str(candidatura.id)

        # 1. Triagem: RH aprova
        r = client.patch(f"/candidaturas/{cid}/status",
                         params={"novo_status": "aprovado_triagem", "ator": "ana"},
                         headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["status"] == "aprovado_triagem"

        # 2. RH agenda entrevista de RH → status avança automaticamente
        amanha = (datetime.utcnow() + timedelta(days=1)).isoformat()
        r = client.post("/entrevistas/", json={
            "candidatura_id": cid,
            "tipo": "rh",
            "agendada_para": amanha,
        }, headers=auth_header(rh))
        assert r.status_code == 201
        entrevista_rh_id = r.json()["id"]
        db.refresh(candidatura)
        assert candidatura.status == StatusCandidatura.ENTREVISTA_RH_AGENDADA

        # 3. RH registra resultado → ENTREVISTA_RH_REALIZADA
        r = client.patch(f"/entrevistas/{entrevista_rh_id}/resultado", json={
            "score_manual": 8.5,
            "anotacoes": "Bom perfil comportamental.",
            "pontos_fortes": ["comunicação", "proatividade"],
            "pontos_fracos": [],
        }, headers=auth_header(rh))
        assert r.status_code == 200
        db.refresh(candidatura)
        assert candidatura.status == StatusCandidatura.ENTREVISTA_RH_REALIZADA

        # 4. Gestor agenda entrevista técnica → ENTREVISTA_TEC_AGENDADA
        r = client.post("/entrevistas/", json={
            "candidatura_id": cid,
            "tipo": "tecnica",
            "agendada_para": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }, headers=auth_header(gestor))
        assert r.status_code == 201
        entrevista_tec_id = r.json()["id"]
        db.refresh(candidatura)
        assert candidatura.status == StatusCandidatura.ENTREVISTA_TEC_AGENDADA

        # 5. Gestor registra resultado técnico → ENTREVISTA_TEC_REALIZADA
        r = client.patch(f"/entrevistas/{entrevista_tec_id}/resultado", json={
            "score_manual": 9.0,
            "anotacoes": "Domínio técnico excelente.",
            "pontos_fortes": ["Python", "arquitetura"],
            "pontos_fracos": ["documentação"],
        }, headers=auth_header(gestor))
        assert r.status_code == 200
        db.refresh(candidatura)
        assert candidatura.status == StatusCandidatura.ENTREVISTA_TEC_REALIZADA

        # 6. Admin avança para decisão pendente
        r = client.patch(f"/candidaturas/{cid}/status",
                         params={"novo_status": "decisao_pendente", "ator": "admin"},
                         headers=auth_header(admin))
        assert r.status_code == 200

        # 7. Admin contrata
        r = client.patch(f"/candidaturas/{cid}/status",
                         params={"novo_status": "contratado", "ator": "admin"},
                         headers=auth_header(admin))
        assert r.status_code == 200
        assert r.json()["status"] == "contratado"

        # 8. Status final correto
        db.refresh(candidatura)
        assert candidatura.status == StatusCandidatura.CONTRATADO

        # 9. Analytics refletem o contratado
        r = client.get("/analytics/resumo", headers=auth_header(rh))
        assert r.json()["contratados_total"] >= 1

        r = client.get(f"/analytics/funil?vaga_id={vaga.id}", headers=auth_header(rh))
        statuses = [e["status"] for e in r.json()["etapas"]]
        assert "contratado" in statuses


class TestFluxoReprovacao:
    """Candidato reprovado na triagem pode ir para banco de talentos."""

    def test_reprovado_triagem_vai_para_banco_talentos(self, client, rh, db):
        v    = make_vaga(db, nome="Vaga Reprovado")
        c    = make_candidato(db, email="reprovado@a.com")
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)

        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "reprovado_triagem"},
                         headers=auth_header(rh))
        assert r.status_code == 200

        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "banco_de_talentos"},
                         headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["status"] == "banco_de_talentos"

    def test_reprovado_rh_vai_para_banco_talentos(self, client, rh, db):
        v    = make_vaga(db, nome="Vaga Rep RH")
        c    = make_candidato(db, email="rep_rh@a.com")
        cand = make_candidatura(db, c, v, StatusCandidatura.REPROVADO_RH)

        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "banco_de_talentos"},
                         headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["status"] == "banco_de_talentos"

    def test_nao_aprovado_nao_pode_retomar_pipeline(self, client, rh, db):
        v    = make_vaga(db, nome="Vaga Nao Aprovado")
        c    = make_candidato(db, email="nao_aprov@a.com")
        cand = make_candidatura(db, c, v, StatusCandidatura.NAO_APROVADO)

        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "triagem_pendente"},
                         headers=auth_header(rh))
        assert r.status_code == 400


class TestFluxoPermissoes:
    """Garante que cada papel só pode fazer o que lhe compete."""

    def test_gestor_nao_pode_alterar_status_de_triagem(self, client, gestor, db):
        v    = make_vaga(db, nome="Vaga Perm Triagem", gestores_ids=[str(gestor.id)])
        c    = make_candidato(db, email="perm_triag@a.com")
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "aprovado_triagem"},
                         headers=auth_header(gestor))
        assert r.status_code == 403

    def test_gestor_nao_pode_agendar_entrevista_rh(self, client, db):
        gestor = make_usuario(db, PapelUsuario.GESTOR, "Gestor Perm", "g_perm@a.com")
        v      = make_vaga(db, nome="Vaga Ent RH Perm", gestores_ids=[str(gestor.id)])
        c      = make_candidato(db, email="ent_rh_perm@a.com")
        cand   = make_candidatura(db, c, v, StatusCandidatura.APROVADO_TRIAGEM)
        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "rh",
            "agendada_para": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_rh_nao_pode_registrar_resultado_tecnico(self, client, rh, db):
        g    = make_usuario(db, PapelUsuario.GESTOR, "Gestor RT", "g_rt@a.com")
        v    = make_vaga(db, nome="Vaga RT", gestores_ids=[str(g.id)])
        c    = make_candidato(db, email="res_tec@a.com")
        # Candidatura em ENTREVISTA_RH_REALIZADA para que o gestor possa agendar a técnica
        cand = make_candidatura(db, c, v, StatusCandidatura.ENTREVISTA_RH_REALIZADA)
        r = client.post("/entrevistas/", json={
            "candidatura_id": str(cand.id),
            "tipo": "tecnica",
            "agendada_para": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }, headers=auth_header(g))
        assert r.status_code == 201
        eid = r.json()["id"]
        # RH tenta registrar resultado de entrevista técnica → 403
        r = client.patch(f"/entrevistas/{eid}/resultado", json={
            "score_manual": 7.0,
            "anotacoes": "Tentativa indevida",
        }, headers=auth_header(rh))
        assert r.status_code == 403
