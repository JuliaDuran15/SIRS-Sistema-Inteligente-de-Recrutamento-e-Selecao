from datetime import datetime
from app.core.celery_app import celery_app
from app.ai.resume_parser import parsear_curriculo
from app.ai.matching_engine import (
    calcular_score_rh,
    calcular_score_mercado,
    calcular_score_curriculo,
    gerar_explicacao,
)
from app.db.session import SessionLocal
from app.models.curriculo import Curriculo
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.vaga import Vaga


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def processar_curriculo(self, candidatura_id: str, caminho_pdf: str):
    db = SessionLocal()

    try:
        # 1. Busca candidatura e vaga
        candidatura = db.query(Candidatura).filter(
            Candidatura.id == candidatura_id
        ).first()

        if not candidatura:
            raise ValueError(f"Candidatura {candidatura_id} não encontrada")

        vaga = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()

        if not vaga:
            raise ValueError(f"Vaga não encontrada para candidatura {candidatura_id}")

        if not vaga.vetor_vaga:
            raise ValueError("Vaga não possui vetor — crie a vaga antes de processar currículos")

        # 2. Parseia o currículo — extrai texto e gera vetor
        resultado = parsear_curriculo(caminho_pdf)

        # 3. Calcula os scores
        score_rh      = calcular_score_rh(resultado["vetor_embedding"], vaga.vetor_vaga)
        vetor_mercado = vaga.vetor_mercado if vaga.vetor_mercado is not None else vaga.vetor_vaga
        score_mercado = calcular_score_mercado(
            resultado["vetor_embedding"],
            vetor_mercado,
        )
        score_curriculo = calcular_score_curriculo(
            score_rh, score_mercado, vaga.peso_rh, vaga.peso_mercado
        )

        # 4. Gera explicação XAI
        explicacao = gerar_explicacao(
            score_rh, score_mercado, score_curriculo,
            vaga.peso_rh, vaga.peso_mercado,
        )

        # 5. Salva no banco
        curriculo = db.query(Curriculo).filter(
            Curriculo.candidato_id == candidatura.candidato_id
        ).first()

        if not curriculo:
            curriculo = Curriculo(candidato_id=candidatura.candidato_id)
            db.add(curriculo)

        curriculo.texto_extraido   = resultado["texto_extraido"]
        curriculo.vetor_embedding  = resultado["vetor_embedding"]
        curriculo.score_rh         = round(score_rh * 100, 1)
        curriculo.score_mercado    = round(score_mercado * 100, 1)
        curriculo.score_curriculo  = score_curriculo
        curriculo.processado_em    = datetime.utcnow()

        # Salva a explicação XAI na candidatura
        candidatura.historico = (candidatura.historico or []) + [{
            "evento"    : "curriculo_processado",
            "em"        : datetime.utcnow().isoformat(),
            "explicacao": explicacao,
        }]
        candidatura.status = StatusCandidatura.TRIAGEM_PENDENTE

        db.commit()

        return {
            "status"        : "ok",
            "candidatura_id": candidatura_id,
            "score_curriculo": score_curriculo,
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def atualizar_mercado_vaga(self, vaga_id: str):
    """
    Busca dados de mercado para a vaga e atualiza vetor_mercado.
    Chamada automaticamente quando uma vaga é criada.
    Pode ser chamada manualmente via POST /vagas/{id}/analisar-mercado.
    """
    db = SessionLocal()

    try:
        from app.models.vaga import Vaga
        vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()

        if not vaga:
            raise ValueError(f"Vaga {vaga_id} não encontrada")

        # asyncio.run para rodar código async dentro da task síncrona do Celery
        resultado = asyncio.run(analisar_mercado(vaga.nome))

        vaga.vetor_mercado = resultado["vetor_mercado"]
        vaga.ranking_mercado = {
            "termos"                : resultado["termos_frequentes"],
            "total_vagas_analisadas": resultado["total_vagas_analisadas"],
            "fonte"                 : resultado["fonte"],
            "atualizado_em"         : datetime.utcnow().isoformat(),
        }

        db.commit()
        print(f"Mercado atualizado para vaga '{vaga.nome}': "
              f"{resultado['total_vagas_analisadas']} vagas analisadas")

        return {
            "status"  : "ok",
            "vaga_id" : vaga_id,
            "termos"  : len(resultado["termos_frequentes"]),
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()