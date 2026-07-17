"""
Seed de teste para detecção de duplicatas.

Cria dados mínimos para testar dois cenários visíveis na tela:

  CENÁRIO 1 — Aviso amarelo no card da candidatura (webhook re-submeteu)
    → Abra /candidatos → "Maria Duplicata" → veja o aviso amarelo no card

  CENÁRIO 2 — Toast vermelho ao tentar vincular via UI
    → Abra /candidatos → "João Duplicata" → tente adicionar
      "Vaga Teste Duplicata" novamente → veja o toast de erro

Não destrói dados existentes. Usa emails exclusivos com sufixo @example.com
(@example.com é reservado pela RFC 2606 para testes — sempre passa validação).

Rode com:
  docker compose exec api python tests/seed_duplicata.py
"""

import sys
sys.path.insert(0, "/app")

from datetime import datetime
from sqlalchemy.orm import sessionmaker

from app.db.session import engine, Base
import app.db.base  # noqa

from app.models.vaga        import Vaga
from app.models.candidato   import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo   import Curriculo
from app.ai.resume_parser   import vetorizar_texto
from app.db.init_extensions import criar_extensoes

criar_extensoes()
Base.metadata.create_all(engine)

db = sessionmaker(autocommit=False, autoflush=False, bind=engine,
                  expire_on_commit=False)()

VAGA_NOME = "Vaga Teste Duplicata"

# ── Remove dados anteriores deste seed (idempotente) ─────────────────────────
def limpar_anteriores():
    for email in ("maria.duplicata@example.com", "joao.duplicata@example.com"):
        c = db.query(Candidato).filter(Candidato.email == email).first()
        if c:
            for cand in db.query(Candidatura).filter(Candidatura.candidato_id == c.id).all():
                db.query(Curriculo).filter(Curriculo.candidatura_id == cand.id).delete()
                db.delete(cand)
            db.delete(c)
    vaga = db.query(Vaga).filter(Vaga.nome == VAGA_NOME).first()
    if vaga:
        db.delete(vaga)
    db.commit()


# ── Vaga ──────────────────────────────────────────────────────────────────────
def criar_vaga():
    req = (
        "Desenvolvedor backend Python com experiência em FastAPI, "
        "PostgreSQL, Docker e testes automatizados. Inglês intermediário."
    )
    vaga = Vaga(
        nome=VAGA_NOME,
        requisitos_texto=req,
        vetor_vaga=vetorizar_texto(req),
        status="aberta",
    )
    db.add(vaga)
    db.commit()
    return vaga


# ── Cenário 1: re-submissão via webhook ───────────────────────────────────────
def criar_cenario_webhook(vaga):
    """
    Maria já tem candidatura. O historico contém uma entrada
    'resubmissao_duplicata' como se o webhook tivesse detectado a duplicata.
    """
    maria = Candidato(
        nome="Maria Duplicata",
        email="maria.duplicata@example.com",
        cidade="São Paulo", estado="SP",
    )
    db.add(maria)
    db.flush()

    historico = [
        {
            "tipo"   : "resubmissao_duplicata",
            "detalhe": (
                f"Re-submissão detectada via webhook "
                f"(fonte: greenhouse). "
                "Candidatura já existia — nenhuma alteração feita."
            ),
            "em": datetime.utcnow().isoformat(),
        }
    ]
    cand = Candidatura(
        candidato_id=maria.id,
        vaga_id=vaga.id,
        status=StatusCandidatura.TRIAGEM_PENDENTE,
        historico=historico,
        origem="externo",
        fonte="greenhouse",
    )
    db.add(cand)
    db.commit()
    return maria, cand


# ── Cenário 2: duplicata via UI ───────────────────────────────────────────────
def criar_cenario_ui(vaga):
    """
    João já tem candidatura. Na tela, tente vincular a mesma vaga novamente
    → API retorna 409 → toast vermelho aparece.
    """
    joao = Candidato(
        nome="João Duplicata",
        email="joao.duplicata@example.com",
        cidade="Rio de Janeiro", estado="RJ",
    )
    db.add(joao)
    db.flush()

    cand = Candidatura(
        candidato_id=joao.id,
        vaga_id=vaga.id,
        status=StatusCandidatura.NOVO,
        historico=[],
        origem="manual",
    )
    db.add(cand)
    db.commit()
    return joao, cand


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nLimpando dados anteriores deste seed...")
    limpar_anteriores()

    print("Criando vaga de teste...")
    vaga = criar_vaga()

    print("Criando Cenário 1 (aviso no historico)...")
    maria, cand_maria = criar_cenario_webhook(vaga)

    print("Criando Cenário 2 (toast via UI)...")
    joao, cand_joao = criar_cenario_ui(vaga)

    db.close()

    print("\n" + "=" * 60)
    print("  SEED DE DUPLICATA CONCLUÍDO")
    print("=" * 60)
    print(f"\n  Vaga criada : {VAGA_NOME}")
    print(f"\n  CENÁRIO 1 — Aviso amarelo no historico")
    print(f"  Candidato   : Maria Duplicata  (maria.duplicata@example.com)")
    print( "  Como testar : Busque 'Maria' em /candidatos → abra o perfil")
    print( "                O card da candidatura mostra o aviso amarelo ⚠")
    print(f"\n  CENÁRIO 2 — Toast de erro ao duplicar via UI")
    print(f"  Candidato   : João Duplicata   (joao.duplicata@example.com)")
    print( "  Como testar : Busque 'João' em /candidatos → abra o perfil")
    print(f"                Tente vincular '{VAGA_NOME}' novamente")
    print( "                Toast vermelho aparece no canto inferior direito")
    print("\n" + "=" * 60)
