# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Comandos essenciais

```bash
# Subir todos os serviços (API, worker Celery, PostgreSQL, Redis, frontend)
docker compose up -d

# Logs em tempo real
docker compose logs -f api worker

# Aplicar migrações (necessário após qualquer mudança de schema)
docker compose exec api alembic upgrade head

# Criar nova migração
docker compose exec api alembic revision --autogenerate -m "descricao"

# Seed completo do banco (limpa e repopula)
docker compose exec api python tests/seed_full.py

# Reiniciar worker Celery (obrigatório após alterar tasks.py ou módulos de IA)
docker compose restart worker
```

### Testes

```bash
# Todos os testes
docker compose exec api pytest tests/ -v

# Um arquivo específico
docker compose exec api pytest tests/test_candidaturas.py -v

# Um teste específico
docker compose exec api pytest tests/test_feature_extractor.py::TestBonusEstrutural::test_zero_overlap -v

# Testes de IA com embedding real (lentos ~30s)
docker compose exec api pytest tests/test_ai_curriculo.py tests/test_novos_curriculos.py -m slow -s -v

# Relatório completo de scoring (imprime breakdown de cada CV)
docker compose exec api pytest tests/test_novos_curriculos.py::TestPipelineNovos::test_relatorio_completo -m slow -s

# Testes do reranker
docker compose exec api pytest tests/test_reranker.py -v
```

O banco de testes (`sirs_test_db`) usa isolamento por **savepoint** por teste — não requer recriação do banco entre runs. Celery tasks e o modelo de embedding são mockados nos testes de API para velocidade.

---

## Arquitetura

### Serviços (docker-compose)

| Serviço | Porta | Função |
|---|---|---|
| `api` | 8000 | FastAPI + Uvicorn, auto-migrações no boot |
| `worker` | — | Celery worker, processa CVs e mercado em background |
| `db` | 5432 | PostgreSQL 16 + pgvector (vetores 384d) |
| `redis` | 6379 | Broker + result backend do Celery |
| `frontend` | 3000 | React 18 + Vite, proxy `/api/*` → api:8000 |

### Pipeline de processamento de currículo

Quando um PDF é enviado ou texto chega via webhook:

1. **API** (`candidaturas.py`) salva o arquivo e dispara `processar_curriculo.delay()` via Celery
2. **Celery task** (`tasks.py`) chama:
   - `resume_parser.parsear_curriculo()` → extrai texto, gera `vetor_embedding` + `vetor_secao_exp` + `vetor_secao_skills`
   - `matching_engine.calcular_score_rh_multi_secao()` → `score_rh` (usa seções quando disponíveis)
   - `market_analyzer.obter_vetor_mercado()` → `score_mercado`
   - `feature_extractor.extrair_features_curriculo()` + `extrair_features_vaga()` → bônus estrutural
   - `matching_engine.gerar_explicacao()` → XAI salvo no `candidatura.historico`
3. Candidatura avança para `TRIAGEM_PENDENTE`

### Fórmula de scoring

```
score_rh (com seções):
  0.60 × sim(vetor_exp_section, vetor_vaga)
+ 0.40 × sim(vetor_cv_completo, vetor_vaga)
+ bonus_estrutural × 0.6

score_curriculo = clamp(score_rh × peso_rh + score_mercado × peso_mercado, 0, 1) × 100

score_total = (score_curriculo/100 × peso_curriculo)
            + (score_entrevista_rh/10 × peso_entrevista_rh)
            + (score_entrevista_tec/10 × peso_entrevista_tec)
```

`score_rerank` (cross-encoder, sob demanda) não é persistido — retornado só na resposta do endpoint.

### Máquina de estados das candidaturas

Transições válidas definidas em `candidaturas.py:TRANSICOES`. Cada transição é registrada em `candidatura.historico` (JSONB) com `{de, para, ator, em}`.

**Armadilha crítica do SQLAlchemy — mutação de JSONB:** Para que o SQLAlchemy detecte mudança num campo JSONB, é obrigatório criar um novo objeto list/dict:

```python
# ERRADO — SQLAlchemy não detecta a mudança, não persiste
historico = candidatura.historico or []
historico.append({...})
candidatura.historico = historico  # mesma referência

# CORRETO
historico = list(candidatura.historico or [])  # nova referência
historico.append({...})
candidatura.historico = historico
```

O mesmo vale para qualquer campo JSONB mutado in-place (`ranking_mercado`, `gestores_ids`, etc.).

### Controle de acesso (RBAC)

Três papéis: `RH`, `GESTOR`, `ADMIN`. Além do papel, vagas têm `rhs_autorizados` (lista de IDs). Um RH só gerencia vagas onde é criador ou está nessa lista; vagas criadas por admin são acessíveis a qualquer RH.

Guards reutilizáveis em `core/auth.py`: `QUALQUER_PAPEL`, `RH_OU_ADMIN`, `get_usuario_atual`.

### Módulos de IA (`backend/app/ai/`)

| Módulo | Responsabilidade |
|---|---|
| `resume_parser.py` | PDF → texto + vetores (embedding model singleton, lazy load) |
| `section_extractor.py` | Segmenta CV em seções; `texto_para_rerank()` para o cross-encoder |
| `feature_extractor.py` | Regex puro: anos (3 estratégias), senioridade, skills + proficiência, bônus ±0.25 |
| `matching_engine.py` | Calcula `score_rh`, `score_mercado`, `score_curriculo`, `score_total`, `gerar_explicacao()` |
| `market_analyzer.py` | Kaggle dataset + Adzuna API → vetor de mercado por cargo; filtro de EEO/benefits em `limpar_skills_desc()` |
| `reranker.py` | Cross-encoder `BAAI/bge-reranker-base` (~270MB), lazy load na 1ª chamada; normaliza logits via sigmoid |
| `tasks.py` | Tasks Celery: `processar_curriculo`, `processar_curriculo_texto`, `atualizar_mercado_vaga` |

**Armadilha — vetores numpy como booleanos:** Campos `vetor_embedding` e `vetor_vaga` são arrays numpy. Usar `if curriculo.vetor_embedding:` levanta `ValueError`. Sempre usar:
```python
if curriculo.vetor_embedding is not None and vaga.vetor_vaga is not None:
```

### Recálculo de scores

Quando pesos ou requisitos de uma vaga mudam, `_recalcular_scores_vaga()` em `vagas.py` recalcula `score_rh`, `score_mercado`, `score_curriculo` **e** `explicacao` para todos os currículos da vaga. É chamado automaticamente pelos endpoints `PATCH /vagas/{id}/pesos` e `PATCH /vagas/{id}/requisitos`.

### Frontend (`frontend/src/`)

SPA React com React Router. Navegar para a mesma rota não força remount — páginas com dados frescos (ex: Auditoria) devem ter botão de atualizar explícito ou `useEffect` com chave de navegação.

Componentes compartilhados em `components/`:
- `ExplicacaoScore.jsx` — breakdown de score (aderência, mercado, skills); usado em `VagaDetalhe` e `CandidatoDetalhe`
- `ComparacaoCandidatos.jsx` — modal de comparação lado a lado (2–3 candidatos)
- `Layout.jsx` — sidebar com link Auditoria visível apenas para admin

`api.js` centraliza todas as chamadas HTTP via axios com interceptor JWT.

### Webhook de importação

`POST /webhook/importar` aceita JSON ou XML. Autenticação via header `X-Webhook-Key` (opcional em dev, configurar `WEBHOOK_SECRET_KEY` em produção). Cada candidato roda em savepoint isolado — falhas individuais não cancelam a importação dos demais.

---

## Variáveis de ambiente relevantes

```env
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2   # mudar exige migração + reprocessamento
EMBEDDING_DIM=384
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_TOP_N=20
MARKET_ANALYZER_SOURCE=kaggle   # "kaggle" | "adzuna" | "ambos"
```

Para usar o Kaggle como fonte de mercado, colocar `backend/data/postings.csv` do [LinkedIn Job Postings dataset](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings).

---

## Estrutura de testes

| Arquivo | Foco |
|---|---|
| `test_feature_extractor.py` | Anos (3 estratégias), senioridade, skills, proficiência, bônus estrutural |
| `test_matching_engine.py` | Scores RH/mercado/multi-seção, XAI, score final |
| `test_market_analyzer.py` | Detecção de categoria, extração de skills, filtragem EEO |
| `test_ai_curriculo.py` + `test_novos_curriculos.py` | Pipeline completo com CVs reais (marcados `@pytest.mark.slow`) |
| `test_reranker.py` | Cross-encoder unidade + endpoint, logging, fallback em erro |
| `test_candidaturas.py` | Máquina de estados, triagem em lote, savepoints |
| `test_entrevistas.py` | Permissões por papel e por vaga (gestor só técnica) |
| `test_vagas.py` | CRUD, `rhs_autorizados`, recálculo de scores ao mudar pesos |
