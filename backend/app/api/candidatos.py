# from app.ai.tasks import processar_curriculo

# @router.post("/candidatos")
# async def criar_candidato(dados: CandidatoCreate, db: Session = Depends(get_db)):

#     # 1. Salva o candidato no banco (rápido)
#     candidato = Candidato(**dados.dict())
#     db.add(candidato)
#     db.commit()

#     # 2. Enfileira o processamento no Celery (50ms)
#     tarefa = processar_curriculo.delay(
#         candidatura_id=str(candidato.id),
#         pdf_path=f"/uploads/{candidato.id}.pdf"
#     )
#     #                          ^
#     #                          .delay() envia para a fila do Redis
#     #                          não executa aqui — executa no worker

#     # 3. Responde imediatamente sem esperar o processamento
#     return {
#         "candidato_id": str(candidato.id),
#         "task_id": tarefa.id,           # ID para consultar o status depois
#         "status": "processando"
#     }