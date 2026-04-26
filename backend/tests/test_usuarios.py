"""Testes dos endpoints de usuários — /usuarios/"""
from tests.conftest import make_usuario, auth_header
from app.models.usuario import PapelUsuario


class TestCriarUsuario:
    def test_admin_pode_criar(self, client, admin):
        r = client.post("/usuarios/", json={
            "nome": "Novo Usuário",
            "email": "novo@teste.com",
            "senha": "senha123",
            "papel": "rh",
        }, headers=auth_header(admin))
        assert r.status_code == 201

    def test_usuario_criado_tem_campos_corretos(self, client, admin):
        r = client.post("/usuarios/", json={
            "nome": "Ana Criada",
            "email": "ana_criada@teste.com",
            "senha": "senha123",
            "papel": "rh",
        }, headers=auth_header(admin))
        body = r.json()
        assert body["nome"] == "Ana Criada"
        assert body["email"] == "ana_criada@teste.com"
        assert body["papel"] == "rh"
        assert body["ativo"] is True
        assert "id" in body
        assert "criado_em" in body

    def test_email_duplicado_retorna_400(self, client, admin, db):
        make_usuario(db, email="dup@teste.com")
        r = client.post("/usuarios/", json={
            "nome": "Dup",
            "email": "dup@teste.com",
            "senha": "senha123",
            "papel": "rh",
        }, headers=auth_header(admin))
        assert r.status_code == 400

    def test_rh_nao_pode_criar_usuario_403(self, client, rh):
        r = client.post("/usuarios/", json={
            "nome": "Tentativa",
            "email": "tentativa@teste.com",
            "senha": "senha123",
            "papel": "rh",
        }, headers=auth_header(rh))
        assert r.status_code == 403

    def test_gestor_nao_pode_criar_usuario_403(self, client, gestor):
        r = client.post("/usuarios/", json={
            "nome": "Tentativa",
            "email": "tentativa2@teste.com",
            "senha": "senha123",
            "papel": "gestor",
        }, headers=auth_header(gestor))
        assert r.status_code == 403

    def test_sem_token_retorna_401(self, client):
        r = client.post("/usuarios/", json={
            "nome": "Sem Token",
            "email": "semtoken@teste.com",
            "senha": "senha123",
        })
        assert r.status_code == 401

    def test_criar_gestor(self, client, admin):
        r = client.post("/usuarios/", json={
            "nome": "Carlos Gestor",
            "email": "carlos_g@teste.com",
            "senha": "senha123",
            "papel": "gestor",
        }, headers=auth_header(admin))
        assert r.status_code == 201
        assert r.json()["papel"] == "gestor"

    def test_papel_padrao_e_rh(self, client, admin):
        r = client.post("/usuarios/", json={
            "nome": "Sem Papel",
            "email": "sem_papel@teste.com",
            "senha": "senha123",
        }, headers=auth_header(admin))
        assert r.status_code == 201
        assert r.json()["papel"] == "rh"


class TestListarUsuarios:
    def test_qualquer_papel_pode_listar(self, client, rh):
        r = client.get("/usuarios/", headers=auth_header(rh))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_sem_token_retorna_401(self, client):
        assert client.get("/usuarios/").status_code == 401

    def test_usuario_criado_aparece_na_lista(self, client, admin, db):
        make_usuario(db, email="listavel@teste.com", nome="Listável")
        nomes = [u["nome"] for u in client.get("/usuarios/", headers=auth_header(admin)).json()]
        assert "Listável" in nomes

    def test_usuario_inativo_nao_aparece(self, client, rh, db):
        u = make_usuario(db, email="inativo_list@teste.com", nome="Inativo Lista")
        u.ativo = False
        db.flush()
        nomes = [u["nome"] for u in client.get("/usuarios/", headers=auth_header(rh)).json()]
        assert "Inativo Lista" not in nomes


class TestBuscarUsuario:
    def test_buscar_por_id_retorna_200(self, client, rh):
        r = client.get(f"/usuarios/{rh.id}", headers=auth_header(rh))
        assert r.status_code == 200
        assert r.json()["email"] == rh.email

    def test_id_inexistente_retorna_404(self, client, rh):
        r = client.get("/usuarios/00000000-0000-0000-0000-000000000000",
                       headers=auth_header(rh))
        assert r.status_code == 404


class TestDesativarUsuario:
    def test_admin_pode_desativar(self, client, admin, db):
        u = make_usuario(db, email="para_desativar@teste.com")
        r = client.delete(f"/usuarios/{u.id}", headers=auth_header(admin))
        assert r.status_code == 204

    def test_usuario_desativado_fica_inativo(self, client, admin, db):
        u = make_usuario(db, email="desativa_check@teste.com")
        client.delete(f"/usuarios/{u.id}", headers=auth_header(admin))
        db.refresh(u)
        assert u.ativo is False

    def test_desativar_admin_retorna_403(self, client, admin, db):
        outro_admin = make_usuario(db, PapelUsuario.ADMIN, email="admin_del@teste.com")
        r = client.delete(f"/usuarios/{outro_admin.id}", headers=auth_header(admin))
        assert r.status_code == 403

    def test_rh_nao_pode_desativar_403(self, client, rh, db):
        u = make_usuario(db, email="rh_nao_desativa@teste.com")
        r = client.delete(f"/usuarios/{u.id}", headers=auth_header(rh))
        assert r.status_code == 403

    def test_id_inexistente_retorna_404(self, client, admin):
        r = client.delete("/usuarios/00000000-0000-0000-0000-000000000000",
                          headers=auth_header(admin))
        assert r.status_code == 404
