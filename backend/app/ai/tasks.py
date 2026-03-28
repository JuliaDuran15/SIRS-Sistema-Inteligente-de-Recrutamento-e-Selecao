from app.core.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def processar_curriculo(self, candidatura_id: str, pdf_path: str):
    """
    Executada pelo worker em background.
    Será preenchida na sprint do motor de IA.
    """
    try:
        print(f"Processando candidatura {candidatura_id}...")
        # Sprint 3: Resume Parser + Matching Engine aqui
        return {"status": "ok", "candidatura_id": candidatura_id}
    except Exception as exc:
        raise self.retry(exc=exc)