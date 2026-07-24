"""
Gabarito manual de precisão da segmentação de currículos.

Para cada fixture:
  - "esperadas": seções que DEVEM ser detectadas com conteúdo relevante
  - "nao_esperadas": seções que NÃO devem aparecer (ou devem estar vazias)
  - "contem": trechos de texto que devem estar DENTRO da seção detectada

Adicionar novos casos: basta incluir mais entradas em GABARITO.
"""
import pytest
from pathlib import Path
from app.ai.section_extractor import extrair_secoes

FIXTURES = Path(__file__).parent / "fixtures"

GABARITO = [
    {
        "arquivo"     : "cv_com_cabecalhos.txt",
        "descricao"   : "CV com cabeçalhos explícitos em PT-BR",
        "esperadas"   : ["experiencia", "habilidades", "educacao", "resumo"],
        "nao_esperadas": [],
        "contem"      : {
            "experiencia" : ["Fintech Pagamentos", "microsserviços"],
            "habilidades" : ["FastAPI", "Kubernetes"],
            "educacao"    : ["USP", "Engenharia de Computação"],
            "resumo"      : ["sistemas distribuídos"],
        },
    },
    {
        "arquivo"     : "cv_sem_cabecalhos.txt",
        "descricao"   : "CV sem cabeçalhos (fallback por densidade)",
        "esperadas"   : ["experiencia", "habilidades", "educacao"],
        "nao_esperadas": [],
        "contem"      : {
            "experiencia" : ["Agência Digital", "desenvolvedor"],
            "habilidades" : ["React", "PostgreSQL"],
            "educacao"    : ["FATEC", "Análise e Desenvolvimento"],
        },
    },
    {
        "arquivo"     : "cv_em_ingles.txt",
        "descricao"   : "CV em inglês com cabeçalhos em EN",
        "esperadas"   : ["experiencia", "habilidades", "educacao", "resumo"],
        "nao_esperadas": [],
        "contem"      : {
            "experiencia" : ["GlobalTech", "Kafka"],
            "habilidades" : ["Spark", "Terraform"],
            "educacao"    : ["PUC-SP", "Bachelor"],
            "resumo"      : ["data engineer", "pipelines"],
        },
    },
]


@pytest.mark.parametrize("caso", GABARITO, ids=[c["descricao"] for c in GABARITO])
def test_secoes_detectadas(caso):
    texto  = (FIXTURES / caso["arquivo"]).read_text(encoding="utf-8")
    secoes = extrair_secoes(texto)

    for secao in caso["esperadas"]:
        assert secoes.get(secao, "").strip(), (
            f"Seção '{secao}' deveria ter sido detectada em {caso['arquivo']}"
        )

    for secao in caso.get("nao_esperadas", []):
        assert not secoes.get(secao, "").strip(), (
            f"Seção '{secao}' não deveria ter conteúdo em {caso['arquivo']}"
        )

    for secao, trechos in caso.get("contem", {}).items():
        texto_secao = secoes.get(secao, "").lower()
        for trecho in trechos:
            assert trecho.lower() in texto_secao, (
                f"Trecho '{trecho}' não encontrado na seção '{secao}' de {caso['arquivo']}\n"
                f"Conteúdo detectado: {secoes.get(secao, '')[:200]}"
            )


def test_relatorio_completo():
    """Imprime diagnóstico legível para inspeção manual — rode com -s."""
    for caso in GABARITO:
        texto  = (FIXTURES / caso["arquivo"]).read_text(encoding="utf-8")
        secoes = extrair_secoes(texto)

        print(f"\n{'='*60}")
        print(f"  {caso['descricao']}")
        print(f"{'='*60}")
        for nome, conteudo in secoes.items():
            status  = "✓" if conteudo.strip() else "✗"
            preview = conteudo[:100].replace("\n", " ") if conteudo.strip() else "NÃO DETECTADA"
            print(f"  [{status}] {nome.upper():<14} {preview}")
