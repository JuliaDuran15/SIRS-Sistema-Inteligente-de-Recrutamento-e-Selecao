"""
Demonstração do webhook de importação.

Simula um sistema externo (ATS/HRIS) enviando candidatos e vagas via HTTP POST.
Execute com:
    docker compose exec api python tests/demo_webhook.py

Ou, a partir do host (se a API estiver exposta na porta 8000):
    python tests/demo_webhook.py
"""

import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/webhook/importar"
API_KEY  = ""   # preencha se WEBHOOK_SECRET_KEY estiver configurada no .env


def _post(payload: dict | str, content_type: str = "application/json") -> dict:
    corpo = payload if isinstance(payload, bytes) else (
        payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
    )
    headers = {"Content-Type": content_type}
    if API_KEY:
        headers["X-Webhook-Key"] = API_KEY
    req = urllib.request.Request(ENDPOINT, data=corpo, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"erro_http": e.code, "detalhe": json.loads(e.read())}


def _cabecalho(titulo: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {titulo}")
    print(f"{'─' * 60}")


def _resumo(r: dict) -> None:
    imp = r.get("importados", {})
    print(f"  vagas criadas          : {imp.get('vagas_criadas', 0)}")
    print(f"  candidatos criados     : {imp.get('candidatos_criados', 0)}")
    print(f"  candidatos atualizados : {imp.get('candidatos_atualizados', 0)}")
    print(f"  candidaturas criadas   : {imp.get('candidaturas_criadas', 0)}")
    print(f"  curriculos processados : {imp.get('curriculos_processados', 0)}")
    erros = r.get("erros", [])
    if erros:
        print(f"  erros ({len(erros)}):")
        for e in erros:
            print(f"    [{e['tipo']}] {e['identificador']} — {e['detalhe']}")
    if "erro_http" in r:
        print(f"  HTTP {r['erro_http']}: {r.get('detalhe')}")


# ── Demo 1: importação via JSON ───────────────────────────────────────────────
def demo_json():
    _cabecalho("DEMO 1 — JSON: vaga + candidatos com currículo")
    payload = {
        "fonte": "greenhouse",
        "vagas": [
            {
                "external_id": "demo_v1",
                "nome": "Demo Dev Python",
                "requisitos_texto": (
                    "Desenvolvedor Python com experiência em FastAPI, SQLAlchemy, "
                    "PostgreSQL, Docker e boas práticas de API REST. "
                    "Inglês intermediário para leitura de documentação."
                ),
            }
        ],
        "candidatos": [
            {
                "external_id": "demo_c1",
                "nome": "Alice Demo",
                "email": "alice.demo@externo.com",
                "telefone": "11999990001",
                "cidade": "São Paulo",
                "estado": "SP",
                "formacao": [
                    {
                        "curso": "Ciência da Computação",
                        "instituicao": "USP",
                        "nivel": "graduacao",
                        "status": "concluido",
                        "ano_conclusao": 2020,
                    }
                ],
                "curriculo_texto": (
                    "Desenvolvedora Python com 4 anos de experiência. "
                    "Trabalhou com FastAPI, SQLAlchemy, PostgreSQL e Docker em "
                    "projetos de APIs REST. Inglês avançado."
                ),
                "vaga_external_id": "demo_v1",
            },
            {
                "external_id": "demo_c2",
                "nome": "Bruno Demo",
                "email": "bruno.demo@externo.com",
                "cidade": "Campinas",
                "estado": "SP",
                "curriculo_texto": (
                    "Backend developer com 2 anos. Python, Django, PostgreSQL. "
                    "Iniciante em FastAPI e Docker."
                ),
                "vaga_external_id": "demo_v1",
            },
        ],
    }
    resultado = _post(payload)
    _resumo(resultado)


# ── Demo 2: upsert — atualiza candidato já existente ─────────────────────────
def demo_upsert():
    _cabecalho("DEMO 2 — Upsert: atualiza candidato alice.demo@externo.com")
    payload = {
        "fonte": "linkedin",
        "candidatos": [
            {
                "nome": "Alice Demo Atualizada",
                "email": "alice.demo@externo.com",
                "telefone": "11988880001",
                "cidade": "Campinas",
                "estado": "SP",
            }
        ],
    }
    resultado = _post(payload)
    _resumo(resultado)


# ── Demo 3: XML ───────────────────────────────────────────────────────────────
def demo_xml():
    _cabecalho("DEMO 3 — XML: vaga + candidato (formato SAP/Oracle)")
    xml = """<importacao fonte="sap_hcm">
  <vagas>
    <vaga external_id="demo_xml_v1">
      <nome>Demo Analista Financeiro</nome>
      <requisitos_texto>Excel avancado, SAP FI, Power BI, IFRS, fluxo de caixa, CRC preferencial</requisitos_texto>
    </vaga>
  </vagas>
  <candidatos>
    <candidato external_id="demo_xml_c1" vaga_external_id="demo_xml_v1">
      <nome>Carla Demo XML</nome>
      <email>carla.xml@externo.com</email>
      <telefone>21988880001</telefone>
      <cidade>Rio de Janeiro</cidade>
      <estado>RJ</estado>
      <curriculo_texto>Analista financeira com 6 anos de experiencia em controladoria. SAP FI, Power BI, IFRS e planejamento orcamentario.</curriculo_texto>
      <formacao>
        <item nivel="graduacao" status="concluido" ano_conclusao="2016">
          <curso>Ciencias Contabeis</curso>
          <instituicao>FGV-RJ</instituicao>
        </item>
      </formacao>
    </candidato>
  </candidatos>
</importacao>"""
    resultado = _post(xml.encode(), content_type="application/xml")
    _resumo(resultado)


# ── Demo 4: erros parciais — email inválido não interrompe os demais ──────────
def demo_erros_parciais():
    _cabecalho("DEMO 4 — Erros parciais: 1 inválido + 2 válidos")
    payload = {
        "candidatos": [
            {"nome": "OK Um",    "email": "ok1.demo@externo.com"},
            {"nome": "Invalido", "email": "nao-e-um-email"},
            {"nome": "OK Dois",  "email": "ok2.demo@externo.com"},
        ]
    }
    resultado = _post(payload)
    _resumo(resultado)


# ── Demo 5: candidatura vinculada a vaga existente por nome ──────────────────
def demo_vaga_por_nome():
    _cabecalho("DEMO 5 — Vincula a vaga existente pelo nome")
    payload = {
        "fonte": "gupy",
        "candidatos": [
            {
                "nome": "Diego Demo",
                "email": "diego.demo@externo.com",
                "cidade": "Belo Horizonte",
                "estado": "MG",
                "curriculo_texto": "DevOps com 5 anos. Kubernetes, Terraform, AWS, CI/CD.",
                "vaga_nome": "DevOps / SRE Engineer",  # vaga já criada pelo seed
            }
        ],
    }
    resultado = _post(payload)
    _resumo(resultado)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nEnviando para: {ENDPOINT}")
    demos = {
        "1": demo_json,
        "2": demo_upsert,
        "3": demo_xml,
        "4": demo_erros_parciais,
        "5": demo_vaga_por_nome,
    }

    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "all":
        for fn in demos.values():
            fn()
    elif arg in demos:
        demos[arg]()
    else:
        print(f"Uso: python demo_webhook.py [1|2|3|4|5|all]")
        print("  1 — JSON com vaga + candidatos com currículo")
        print("  2 — Upsert de candidato existente")
        print("  3 — XML no formato SAP/Oracle")
        print("  4 — Erros parciais (email inválido não quebra os demais)")
        print("  5 — Vinculo a vaga existente pelo nome")
        sys.exit(1)

    print(f"\n{'─' * 60}")
    print("  Pronto. Verifique na interface ou via:")
    print("  curl -s -H 'Authorization: Bearer <token>'")
    print("  http://localhost:8000/candidatos/ | python -m json.tool")
    print(f"{'─' * 60}\n")
