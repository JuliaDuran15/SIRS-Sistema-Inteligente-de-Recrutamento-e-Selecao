"""Testes dos endpoints de candidaturas — /candidaturas/ — incluindo upload de currículo."""
import io
from tests.conftest import (
    make_vaga, make_candidato, make_candidatura,
    auth_header, make_pdf_bytes,
)
from app.models.candidatura import StatusCandidatura


class TestCriarCandidatura:
    def test_rh_pode_criar(self, client, rh, candidato, vaga):
        r = client.post("/candidaturas/", json={
            "candidato_id": str(candidato.id),
            "vaga_id": str(vaga.id),
        }, headers=auth_header(rh))
        assert r.status_code == 201

    def test_retorna_campos_corretos(self, client, rh, db):
        c = make_candidato(db, email="cand_campos@teste.com")
        v = make_vaga(db, nome="Vaga Campos")
        r = client.post("/candidaturas/", json={
            "candidato_id": str(c.id),
            "vaga_id": str(v.id),
        }, headers=auth_header(rh))
        body = r.json()
        assert body["candidato_id"] == str(c.id)
        assert body["vaga_id"] == str(v.id)
        assert body["status"] == "novo"
        assert "id" in body

    def test_gestor_nao_pode_criar(self, client, gestor, candidato, vaga):
        r = client.post("/candidaturas/", json={
            "candidato_id": str(candidato.id),
            "vaga_id": str(vaga.id),
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_sem_token_retorna_401(self, client, candidato, vaga):
        r = client.post("/candidaturas/", json={
            "candidato_id": str(candidato.id),
            "vaga_id": str(vaga.id),
        })
        assert r.status_code == 401

    def test_candidato_inexistente_retorna_404(self, client, rh, vaga):
        r = client.post("/candidaturas/", json={
            "candidato_id": "00000000-0000-0000-0000-000000000000",
            "vaga_id": str(vaga.id),
        }, headers=auth_header(rh))
        assert r.status_code == 404

    def test_vaga_inexistente_retorna_404(self, client, rh, candidato):
        r = client.post("/candidaturas/", json={
            "candidato_id": str(candidato.id),
            "vaga_id": "00000000-0000-0000-0000-000000000000",
        }, headers=auth_header(rh))
        assert r.status_code == 404


class TestListarCandidaturas:
    def test_rh_pode_listar(self, client, rh, candidatura):
        r = client.get("/candidaturas/", headers=auth_header(rh))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filtrar_por_vaga(self, client, rh, db):
        v1 = make_vaga(db, nome="Vaga Filtro 1")
        v2 = make_vaga(db, nome="Vaga Filtro 2")
        c1 = make_candidato(db, email="filtro1@teste.com")
        c2 = make_candidato(db, email="filtro2@teste.com")
        make_candidatura(db, c1, v1)
        make_candidatura(db, c2, v2)

        r = client.get(f"/candidaturas/?vaga_id={v1.id}", headers=auth_header(rh))
        ids_vaga = [c["vaga_id"] for c in r.json()]
        assert all(i == str(v1.id) for i in ids_vaga)

    def test_gestor_pode_listar(self, client, gestor, candidatura):
        r = client.get("/candidaturas/", headers=auth_header(gestor))
        assert r.status_code == 200

    def test_sem_token_retorna_401(self, client):
        assert client.get("/candidaturas/").status_code == 401


class TestBuscarCandidatura:
    def test_buscar_por_id(self, client, rh, candidatura):
        r = client.get(f"/candidaturas/{candidatura.id}", headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["id"] == str(candidatura.id)

    def test_inclui_candidato_aninhado(self, client, rh, candidatura):
        r = client.get(f"/candidaturas/{candidatura.id}", headers=auth_header(rh))
        body = r.json()
        assert "candidato" in body
        assert body["candidato"]["nome"] == candidatura.candidato.nome

    def test_inclui_vaga_aninhada(self, client, rh, candidatura):
        r = client.get(f"/candidaturas/{candidatura.id}", headers=auth_header(rh))
        assert "vaga" in r.json()
        assert r.json()["vaga"]["nome"] == candidatura.vaga.nome

    def test_id_inexistente_retorna_404(self, client, rh):
        r = client.get("/candidaturas/00000000-0000-0000-0000-000000000000",
                       headers=auth_header(rh))
        assert r.status_code == 404


class TestMaquinaDeEstados:
    def test_transicao_valida_triagem_aprovado(self, client, rh, db):
        c = make_candidato(db, email="estat1@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "aprovado_triagem", "ator": "ana"},
                         headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["status"] == "aprovado_triagem"

    def test_transicao_valida_triagem_reprovado(self, client, rh, db):
        c = make_candidato(db, email="estat2@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "reprovado_triagem"},
                         headers=auth_header(rh))
        assert r.status_code == 200

    def test_transicao_invalida_retorna_400(self, client, rh, db):
        # Não pode ir de NOVO direto para CONTRATADO
        c = make_candidato(db, email="estat3@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.NOVO)
        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "contratado"},
                         headers=auth_header(rh))
        assert r.status_code == 400

    def test_historico_registrado(self, client, rh, db):
        c = make_candidato(db, email="hist@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        client.patch(f"/candidaturas/{cand.id}/status",
                     params={"novo_status": "aprovado_triagem", "ator": "ana"},
                     headers=auth_header(rh))
        db.refresh(cand)
        assert len(cand.historico) >= 1
        assert cand.historico[-1]["de"] == "triagem_pendente"
        assert cand.historico[-1]["para"] == "aprovado_triagem"

    def test_gestor_nao_pode_alterar_status(self, client, gestor, db):
        c = make_candidato(db, email="gestor_stat@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.TRIAGEM_PENDENTE)
        r = client.patch(f"/candidaturas/{cand.id}/status",
                         params={"novo_status": "aprovado_triagem"},
                         headers=auth_header(gestor))
        assert r.status_code == 403


class TestUploadCurriculo:
    def test_rh_pode_fazer_upload(self, client, rh, candidatura):
        pdf = make_pdf_bytes()
        r = client.post(
            f"/candidaturas/{candidatura.id}/curriculo",
            files={"arquivo": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
            headers=auth_header(rh),
        )
        assert r.status_code == 200

    def test_upload_muda_status_para_aguardando(self, client, rh, db):
        c = make_candidato(db, email="upload_status@teste.com")
        v = make_vaga(db)
        cand = make_candidatura(db, c, v, StatusCandidatura.NOVO)
        r = client.post(
            f"/candidaturas/{cand.id}/curriculo",
            files={"arquivo": ("cv.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")},
            headers=auth_header(rh),
        )
        assert r.json()["status"] == "aguardando_processamento"

    def test_upload_dispara_task_celery(self, client, rh, candidatura, mock_celery_tasks):
        mock_proc, _ = mock_celery_tasks
        client.post(
            f"/candidaturas/{candidatura.id}/curriculo",
            files={"arquivo": ("cv.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")},
            headers=auth_header(rh),
        )
        mock_proc.assert_called_once()
        args = mock_proc.call_args[0]
        assert args[0] == str(candidatura.id)

    def test_arquivo_nao_pdf_retorna_400(self, client, rh, candidatura):
        r = client.post(
            f"/candidaturas/{candidatura.id}/curriculo",
            files={"arquivo": ("cv.txt", io.BytesIO(b"texto"), "text/plain")},
            headers=auth_header(rh),
        )
        assert r.status_code == 400

    def test_gestor_nao_pode_fazer_upload(self, client, gestor, candidatura):
        r = client.post(
            f"/candidaturas/{candidatura.id}/curriculo",
            files={"arquivo": ("cv.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")},
            headers=auth_header(gestor),
        )
        assert r.status_code == 403

    def test_candidatura_inexistente_retorna_404(self, client, rh):
        r = client.post(
            "/candidaturas/00000000-0000-0000-0000-000000000000/curriculo",
            files={"arquivo": ("cv.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")},
            headers=auth_header(rh),
        )
        assert r.status_code == 404
