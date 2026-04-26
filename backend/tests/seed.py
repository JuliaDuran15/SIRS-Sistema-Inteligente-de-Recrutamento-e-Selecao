"""
Script de pré-população do banco para testes.
Rode com:
  docker compose exec api python tests/seed.py
"""

import sys
import os
sys.path.insert(0, "/app")

from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.db.base import Base  # isso já importa todos os models
from app.db.session import SessionLocal
from app.models.usuario import Usuario, PapelUsuario
from app.models.candidato import Candidato
from app.models.vaga import Vaga
from app.models.curriculo import Curriculo
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.entrevista import Entrevista  # ← estava faltando
from app.ai.resume_parser import vetorizar_texto
from passlib.context import CryptContext
from datetime import date
from app.core.auth import hash_senha
from app.core.config import settings


pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,   # ← evita recarregar do banco após commit
)
db = SessionLocal()

def limpar():
    """Apaga tudo na ordem certa para não violar foreign keys."""
    db.query(Entrevista).delete()    # ← primeiro
    db.query(Curriculo).delete()     # ← segundo
    db.query(Candidatura).delete()
    db.query(Candidato).delete()
    db.query(Vaga).delete()
    db.query(Usuario).delete()
    db.commit()
    print("Banco limpo.")


def criar_usuarios():
    usuarios = [
        Usuario(
            nome       = "Ana Paula — RH",
            email      = "ana@sirs.com",
            senha_hash = hash_senha("senha123"),
            papel      = PapelUsuario.RH,
        ),
        Usuario(
            nome       = "Carlos — Gestor Técnico",
            email      = "carlos@sirs.com",
            senha_hash = hash_senha("senha123"),
            papel      = PapelUsuario.GESTOR,
        ),
        Usuario(
            nome       = "Administrador",
            email      = settings.ADMIN_EMAIL,
            senha_hash = hash_senha(settings.ADMIN_SENHA),
            papel      = PapelUsuario.ADMIN,
        ),
    ]
    db.add_all(usuarios)
    db.commit()
    print(f"{len(usuarios)} usuários criados.")
    return usuarios


def criar_vagas():
    requisitos = [
        {
            "nome": "Desenvolvedor Python Sênior",
            "requisitos_texto": (
                "Buscamos desenvolvedor Python sênior com experiência em "
                "FastAPI, SQLAlchemy, PostgreSQL e Docker. Desejável conhecimento "
                "em AWS, Redis e Celery. Perfil comunicativo, proativo e com "
                "capacidade de liderança técnica. Inglês intermediário."
            ),
        },
        {
            "nome": "Advogado Tributarista",
            "requisitos_texto": (
                "Vaga para advogado com sólida experiência em direito tributário, "
                "planejamento fiscal, IRPJ, CSLL, PIS e COFINS. OAB ativa obrigatória. "
                "Experiência em contencioso administrativo e judicial. "
                "Inglês intermediário para leitura de documentos. "
                "Perfil analítico, atenção aos detalhes e boa comunicação escrita."
            ),
        },
        {
            "nome": "Analista de RH — Recrutamento e Seleção",
            "requisitos_texto": (
                "Profissional de RH com experiência em recrutamento e seleção, "
                "aplicação de testes psicológicos, entrevistas por competências "
                "e onboarding. Conhecimento em eSocial, CLT e sistemas ATS. "
                "Habilidade com People Analytics e Excel avançado. "
                "Perfil empático, organizado e com boa comunicação interpessoal."
            ),
        },
        {
            "nome": "Engenheiro Civil — Obras",
            "requisitos_texto": (
                "Engenheiro civil para gestão de obras residenciais e comerciais. "
                "Experiência com AutoCAD, MS Project e orçamento de obras com SINAPI. "
                "Conhecimento em NR-18, gestão de equipes em campo e laudos técnicos. "
                "CREA ativo. Perfil liderança, organização e resolução de problemas."
            ),
        },
    ]

    vagas = []
    for r in requisitos:
        vaga = Vaga(
            nome             = r["nome"],
            requisitos_texto = r["requisitos_texto"],
            vetor_vaga       = vetorizar_texto(r["requisitos_texto"]),
        )
        vagas.append(vaga)

    db.add_all(vagas)
    db.commit()
    print(f"{len(vagas)} vagas criadas com vetores.")
    return vagas


def criar_candidatos():
    candidatos = [
        Candidato(
            nome            = "Julia Souza",
            email           = "julia@email.com",
            telefone        = "11999990001",
            origem          = "manual",
            data_nascimento = date(1995, 3, 15),
            cidade          = "São Paulo",
            estado          = "SP",
            formacao        = [
                {
                    "curso"       : "Ciência da Computação",
                    "instituicao" : "USP",
                    "nivel"       : "graduacao",
                    "status"      : "concluido",
                    "ano_conclusao": 2017,
                }
            ],
        ),
        Candidato(
            nome            = "Pedro Almeida",
            email           = "pedro@email.com",
            telefone        = "11999990002",
            origem          = "externo",
            data_nascimento = date(1990, 7, 22),
            cidade          = "Campinas",
            estado          = "SP",
            formacao        = [
                {
                    "curso"       : "Direito",
                    "instituicao" : "PUC-SP",
                    "nivel"       : "graduacao",
                    "status"      : "concluido",
                    "ano_conclusao": 2015,
                },
                {
                    "curso"       : "Direito Tributário",
                    "instituicao" : "FGV",
                    "nivel"       : "especializacao",
                    "status"      : "concluido",
                    "ano_conclusao": 2018,
                },
            ],
        ),
        Candidato(
            nome            = "Mariana Costa",
            email           = "mariana@email.com",
            telefone        = "11999990003",
            origem          = "manual",
            data_nascimento = date(1998, 11, 5),
            cidade          = "Rio de Janeiro",
            estado          = "RJ",
            formacao        = [
                {
                    "curso"       : "Gestão de Recursos Humanos",
                    "instituicao" : "SENAC",
                    "nivel"       : "tecnologo",
                    "status"      : "concluido",
                    "ano_conclusao": 2020,
                }
            ],
        ),
        Candidato(
            nome            = "Rafael Ferreira",
            email           = "rafael@email.com",
            telefone        = "11999990004",
            origem          = "manual",
            data_nascimento = date(1993, 5, 30),
            cidade          = "Belo Horizonte",
            estado          = "MG",
            formacao        = [
                {
                    "curso"       : "Engenharia Civil",
                    "instituicao" : "UFMG",
                    "nivel"       : "graduacao",
                    "status"      : "concluido",
                    "ano_conclusao": 2016,
                }
            ],
        ),
    ]

    db.add_all(candidatos)
    db.commit()
    print(f"{len(candidatos)} candidatos criados.")
    return candidatos


def criar_candidaturas(vagas, candidatos):
    """
    Vincula cada candidato à vaga mais adequada ao seu perfil.
    """
    vinculos = [
        (candidatos[0], vagas[0]),  # Julia → Dev Python
        (candidatos[1], vagas[1]),  # Pedro → Advogado Tributarista
        (candidatos[2], vagas[2]),  # Mariana → Analista RH
        (candidatos[3], vagas[3]),  # Rafael → Engenheiro Civil
        # Candidato extra na vaga errada — para testar score baixo
        (candidatos[0], vagas[1]),  # Julia (dev) → Advogado (deve ter score baixo)
    ]

    candidaturas = []
    for candidato, vaga in vinculos:
        c = Candidatura(
            candidato_id = candidato.id,
            vaga_id      = vaga.id,
            status       = StatusCandidatura.TRIAGEM_PENDENTE,
            historico    = [],
        )
        candidaturas.append(c)

    db.add_all(candidaturas)
    db.commit()
    print(f"{len(candidaturas)} candidaturas criadas.")
    return candidaturas


def mostrar_resumo(vagas, candidatos, candidaturas):
    print("\n" + "="*50)
    print("BANCO POPULADO — RESUMO")
    print("="*50)

    print("\nUsuários:")
    print("  ana@sirs.com    → RH")
    print("  carlos@sirs.com → Gestor")
    print("  admin@sirs.com  → Admin")

    print("\nVagas criadas:")
    for v in vagas:
        print(f"  {v.nome}")

    print("\nCandidatos criados:")
    for c in candidatos:
        print(f"  {c.nome} — {c.email}")

    print("\nCandidaturas criadas:")
    vinculos = [
        ("Julia Souza",    "Desenvolvedor Python Sênior"),
        ("Pedro Almeida",  "Advogado Tributarista"),
        ("Mariana Costa",  "Analista de RH"),
        ("Rafael Ferreira","Engenheiro Civil"),
        ("Julia Souza",    "Advogado Tributarista"),
    ]
    for candidato, vaga in vinculos:
        print(f"  {candidato:20} → {vaga}")

    print("\nAcesse: http://localhost:8000/docs")
    print("="*50)

def criar_usuarios():
    usuarios = [
        Usuario(
            nome       = "Ana Paula — RH",
            email      = "ana@sirs.com",
            senha_hash = hash_senha("senha123"),
            papel      = PapelUsuario.RH,
        ),
        Usuario(
            nome       = "Carlos — Gestor Técnico",
            email      = "carlos@sirs.com",
            senha_hash = hash_senha("senha123"),
            papel      = PapelUsuario.GESTOR,
        ),
        Usuario(
            nome       = "Admin",
            email      = "admin@sirs.com",
            senha_hash = hash_senha("senha123"),
            papel      = PapelUsuario.ADMIN,
        ),
    ]
    db.add_all(usuarios)
    db.commit()
    print(f"{len(usuarios)} usuários criados.")
    return usuarios

if __name__ == "__main__":
    print("Iniciando seed do banco...")
    limpar()
    usuarios    = criar_usuarios()
    vagas       = criar_vagas()
    candidatos  = criar_candidatos()
    candidaturas = criar_candidaturas(vagas, candidatos)
    mostrar_resumo(vagas, candidatos, candidaturas)
    db.close()