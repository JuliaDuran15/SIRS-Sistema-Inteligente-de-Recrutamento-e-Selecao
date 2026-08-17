"""
Demonstração: importação via webhook + triagem em lote.

Fluxo completo:
  1. Faz login como RH para obter token JWT
  2. Importa 1 vaga + 3 candidatos com currículo via webhook (JSON)
  3. Lista as candidaturas criadas e seus status
  4. Aplica triagem em lote (aprovado_triagem + reprovado_triagem)
  5. Confirma os novos status e mostra o histórico de cada candidatura

Execute com:
    docker compose exec api python tests/demo_triagem_webhook.py
"""

import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


# ── helpers HTTP ─────────────────────────────────────────────────────────────

def _req(method: str, path: str, body=None, token: str = "", content_type: str = "application/json") -> dict:
    url  = f"{BASE}{path}"
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_erro": e.code, "_detalhe": json.loads(e.read())}


def sep(titulo: str = "") -> None:
    print(f"\n{'─' * 62}")
    if titulo:
        print(f"  {titulo}")
        print(f"{'─' * 62}")


# ── 1. login ──────────────────────────────────────────────────────────────────

sep("1 — Login como RH (ana@sirs.com)")

login_body = "username=ana%40sirs.com&password=senha123"
login_resp = _req(
    "POST", "/auth/login",
    body=login_body.encode(),
    content_type="application/x-www-form-urlencoded",
)

if "_erro" in login_resp:
    print(f"  FALHOU: {login_resp}")
    raise SystemExit(1)

token = login_resp["access_token"]
print(f"  token obtido: {token[:40]}...")


# ── 2. importar via webhook ───────────────────────────────────────────────────

sep("2 — Webhook: 1 vaga + 3 candidatos com currículo (JSON)")

VAGA_NOME = "Engenheiro de Software Backend [DEMO]"

payload = {
    "fonte": "demo_triagem",
    "vagas": [
        {
            "external_id": "demo_v99",
            "nome": VAGA_NOME,
            "requisitos_texto": (
                "Engenheiro backend com experiência em Python, FastAPI, PostgreSQL, "
                "Docker e testes automatizados. Desejável conhecimento em Redis e Celery. "
                "Perfil sênior, inglês técnico."
            ),
        }
    ],
    "candidatos": [
        {
            "external_id": "demo_c_alice",
            "nome": "Alice Drummond",
            "email": "alice.drummond.demo@email.com",
            "cidade": "São Paulo",
            "estado": "SP",
            "curriculo_texto": (
                "Engenheira de software sênior com 7 anos de experiência. "
                "Especialista em Python, FastAPI, SQLAlchemy, PostgreSQL e Docker. "
                "Liderou equipes de backend e implementou pipelines CI/CD com GitHub Actions. "
                "Redis, Celery, testes unitários e de integração. Inglês fluente."
            ),
            "vaga_external_id": "demo_v99",
        },
        {
            "external_id": "demo_c_bruno",
            "nome": "Bruno Takeda",
            "email": "bruno.takeda.demo@email.com",
            "cidade": "Curitiba",
            "estado": "PR",
            "curriculo_texto": (
                "Desenvolvedor backend pleno, 3 anos de experiência. "
                "Python, Django, PostgreSQL e Docker. "
                "Iniciando com FastAPI. Inglês intermediário."
            ),
            "vaga_external_id": "demo_v99",
        },
        {
            "external_id": "demo_c_carla",
            "nome": "Carla Mendes",
            "email": "carla.mendes.demo@email.com",
            "cidade": "Recife",
            "estado": "PE",
            "curriculo_texto": (
                "Desenvolvedora júnior, 1 ano de experiência. "
                "Python básico, HTML, CSS. Cursando Análise de Sistemas."
            ),
            "vaga_external_id": "demo_v99",
        },
    ],
}

wh = _req("POST", "/webhook/importar", body=payload)
imp = wh.get("importados", {})
print(f"  vagas criadas          : {imp.get('vagas_criadas', 0)}")
print(f"  candidatos criados     : {imp.get('candidatos_criados', 0)}")
print(f"  candidaturas criadas   : {imp.get('candidaturas_criadas', 0)}")
print(f"  currículos enfileirados: {imp.get('curriculos_processados', 0)}")
erros = wh.get("erros", [])
if erros:
    for e in erros:
        print(f"  ERRO: [{e['tipo']}] {e['identificador']} — {e['detalhe']}")


# ── 3. localizar a vaga e as candidaturas ────────────────────────────────────

sep("3 — Localizando vaga e candidaturas importadas")

vagas = _req("GET", "/vagas/", token=token)
vaga  = next((v for v in vagas if v["nome"] == VAGA_NOME), None)
if not vaga:
    print("  Vaga não encontrada. Verifique o seed ou a importação.")
    raise SystemExit(1)

vaga_id = vaga["id"]
print(f"  vaga id : {vaga_id}")
print(f"  vaga    : {vaga['nome']}")

emails_demo = {
    "alice.drummond.demo@email.com",
    "bruno.takeda.demo@email.com",
    "carla.mendes.demo@email.com",
}

def _buscar_cands():
    todos = _req("GET", f"/candidaturas/?vaga_id={vaga_id}", token=token)
    return [c for c in todos if c.get("candidato", {}).get("email") in emails_demo]

cands_demo = _buscar_cands()
if not cands_demo:
    print("  Candidaturas ainda não aparecem — aguardando 2s e tentando novamente...")
    time.sleep(2)
    cands_demo = _buscar_cands()

print(f"\n  {'Nome':<22} {'Email':<36} {'Status'}")
print(f"  {'─'*22} {'─'*36} {'─'*22}")
for c in cands_demo:
    print(f"  {c['candidato']['nome']:<22} {c['candidato']['email']:<36} {c.get('status','')}")


# ── 4. aguardar processamento (status sai de aguardando/processando) ──────────

sep("4 — Aguardando processamento dos currículos pelo Celery")

pendentes = {"novo", "aguardando_processamento", "processando_curriculo"}
tentativas = 0
while tentativas < 10:
    cands_demo  = _buscar_cands()
    ainda_proc  = [c for c in cands_demo if c.get("status") in pendentes]
    processados = [c for c in cands_demo if c.get("status") not in pendentes]
    print(f"  tentativa {tentativas+1}: {len(processados)}/3 processados", end="\r")
    if not ainda_proc:
        break
    time.sleep(3)
    tentativas += 1

print()
print(f"\n  {'Nome':<22} {'Status':<26} {'Score currículo'}")
print(f"  {'─'*22} {'─'*26} {'─'*15}")
for c in cands_demo:
    score = (c.get("curriculo") or {}).get("score_curriculo")
    score_str = f"{score:.1f}" if score is not None else "—"
    print(f"  {c['candidato']['nome']:<22} {c.get('status',''):<26} {score_str}")


# ── 5. triagem em lote ────────────────────────────────────────────────────────

sep("5 — Triagem em lote")

# filtra só os que estão em triagem_pendente
em_triagem   = [c for c in cands_demo if c.get("status") == "triagem_pendente"]
ids_triagem  = [c["id"] for c in em_triagem]

if not ids_triagem:
    print("  Nenhuma candidatura em triagem_pendente ainda.")
    print("  (Se o worker Celery não estiver processando, inicie-o com: docker compose restart worker)")
else:
    # Aprovados: top 2 por score; reprovado: pior score
    ordenados  = sorted(em_triagem, key=lambda c: (c.get("curriculo") or {}).get("score_curriculo") or 0, reverse=True)
    ids_aprovar   = [c["id"] for c in ordenados[:2]]
    ids_reprovar  = [c["id"] for c in ordenados[2:]]

    if ids_aprovar:
        r = _req("POST", "/candidaturas/triagem-em-lote", token=token, body={
            "candidatura_ids": ids_aprovar,
            "novo_status": "aprovado_triagem",
        })
        print(f"  aprovados  : {r.get('atualizadas', 0)} candidatura(s)  |  erros: {len(r.get('erros', []))}")

    if ids_reprovar:
        r = _req("POST", "/candidaturas/triagem-em-lote", token=token, body={
            "candidatura_ids": ids_reprovar,
            "novo_status": "reprovado_triagem",
        })
        print(f"  reprovados : {r.get('atualizadas', 0)} candidatura(s)  |  erros: {len(r.get('erros', []))}")


# ── 6. resultado final + histórico ────────────────────────────────────────────

sep("6 — Status e histórico após triagem")

cands_demo = _buscar_cands()

for c in cands_demo:
    print(f"\n  {c['candidato']['nome']} — {c.get('status')}")
    # busca histórico via endpoint de detalhe da candidatura
    det = _req("GET", f"/candidaturas/{c['id']}", token=token)
    for h in (det.get("historico") or []):
        if "para" in h:
            print(f"    → {h.get('de','?'):28}  →  {h.get('para','?'):28}  ({h.get('ator','?')})")


# ── fim ───────────────────────────────────────────────────────────────────────

sep()
print("  Fluxo concluído.")
print(f"  Verifique em: http://localhost:3000")
print(f"  Vaga: {VAGA_NOME}")
print(f"{'─' * 62}\n")
