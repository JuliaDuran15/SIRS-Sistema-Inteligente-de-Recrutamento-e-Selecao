# SIRS — Guia de Teste Manual da Interface

Base URL: `http://localhost:3000`  
Execute na ordem — cada bloco depende do anterior.

> **Pré-requisito:** banco populado com `docker compose exec api python tests/seed_full.py`

---

## Logins disponíveis (após seed)

| Email | Senha | Papel |
|---|---|---|
| `admin@sirs.com` | `admin123` | Admin |
| `ana@sirs.com` | `senha123` | RH |
| `bruno@sirs.com` | `senha123` | RH |
| `carlos@sirs.com` | `senha123` | Gestor técnico |
| `daniela@sirs.com` | `senha123` | Gestor técnico |
| `eduardo@sirs.com` | `senha123` | Gestor técnico |

---

## 0. Login

Caminho: `http://localhost:3000/login`

```
Email : admin@sirs.com
Senha : admin123
```

---

## 1. Usuários — Administração › Usuários

Caminho: `http://localhost:3000/admin`

Criar dois usuários de teste adicionais:

**Usuário RH**
```
Nome  : Joana Ferreira
Email : joana.ferreira@empresa.com
Senha : senha123
Papel : RH
```

**Usuário Gestor**
```
Nome  : Pedro Alves
Email : pedro.alves@empresa.com
Senha : senha123
Papel : Gestor técnico
```

---

## 2. Vagas — Nova Vaga

Caminho: `http://localhost:3000/vagas` → botão "Nova Vaga"

### Vaga 1 — Tecnologia

```
Nome: Desenvolvedor Python Pleno

Requisitos:
  Desenvolvedor Python com 3 anos de experiência em FastAPI,
  SQLAlchemy e PostgreSQL. Conhecimento em Docker, CI/CD e
  boas práticas de API REST. Inglês para leitura técnica.

Gestor: Pedro Alves

Pesos (padrão):
  Requisitos RH  : 60%
  Mercado        : 40%
  Currículo      : 50%
  Entrev. RH     : 25%
  Entrev. Tec.   : 25%
```

### Vaga 2 — Marketing

```
Nome: Analista de Marketing Digital Pleno

Requisitos:
  Analista de marketing digital com experiência em Google Ads,
  Meta Ads, SEO, Google Analytics 4 e RD Station. Gestão de
  redes sociais, copywriting e criação de conteúdo. Growth
  hacking é diferencial.

Gestor: Pedro Alves
```

### Vaga 3 — Financeiro

```
Nome: Analista Financeiro Sênior

Requisitos:
  Analista financeiro sênior com experiência em controladoria,
  IFRS, planejamento orçamentário e fluxo de caixa. SAP FI,
  Power BI e Excel avançado. CRC preferencial.

Gestor: Pedro Alves
```

---

## 3. Candidatos — Novo Candidato

Caminho: `http://localhost:3000/candidatos` → botão "Novo Candidato"

O campo "Vaga" cria a candidatura automaticamente.

| Nome | Email | Cidade | Vaga |
|---|---|---|---|
| Carlos Mendes | carlos.mendes@email.com | São Paulo | Desenvolvedor Python Pleno |
| Beatriz Souza | beatriz.souza@email.com | Campinas | Desenvolvedor Python Pleno |
| Renata Lima | renata.lima@email.com | São Paulo | Analista de Marketing Digital Pleno |
| Marcos Oliveira | marcos.oliveira@email.com | Rio de Janeiro | Analista Financeiro Sênior |

---

## 4. Currículos — Upload PDF

Caminho: candidatura → seção "Currículo" → arrastar PDF  
OU: abrir a vaga → "Candidaturas" → linha do candidato

> A interface aceita apenas PDF. Gere um pelo navegador (Ctrl+P → Salvar como PDF) com o texto abaixo.

### Carlos Mendes
```
Desenvolvedor Python sênior com 5 anos de experiência.
FastAPI, SQLAlchemy, PostgreSQL, Docker. CI/CD com GitHub
Actions. Liderou migração de monolito para microsserviços.
Inglês intermediário. USP — Ciência da Computação, 2018.
```

### Beatriz Souza
```
Desenvolvedora backend com 1 ano. Python, Django, SQLite.
Conhecimento básico em Docker. Sem experiência com FastAPI.
```

### Renata Lima
```
Analista de marketing digital pleno. Google Analytics,
Google Ads, Meta Ads, RD Station, SEO on-page, gestão de
redes sociais. 6 anos de experiência. Pós em Marketing
Digital — ESPM, 2021.
```

### Marcos Oliveira
```
Analista financeiro com 8 anos. Controladoria, IFRS, SAP FI,
Power BI, Excel avançado, planejamento orçamentário e fluxo
de caixa. CRC ativo. Pós em Controladoria — FGV-SP, 2017.
```

---

## 5. Triagem — após processamento (~5 s)

Caminho: abrir candidatura → botão "Aprovar" ou "Reprovar"

| Candidato | Ação |
|---|---|
| Carlos Mendes | Aprovar → agendar entrevista RH |
| Beatriz Souza | Reprovar (score baixo esperado) |
| Renata Lima | Aprovar |
| Marcos Oliveira | Aprovar |

---

## 6. Entrevista RH — agendar e registrar resultado

Caminho: candidatura aprovada → "Agendar Entrevista RH"

**Data/hora:** 2026-07-10 às 14:00

**Resultado — Carlos Mendes:**
```
Score       : 8.5
Anotações   : Candidato comunicativo, boa profundidade técnica
              em Python e FastAPI. Apresentou cases reais de
              arquitetura de microsserviços. Inglês ok.
Pontos fortes: comunicação clara | experiência com APIs REST | proativo
Pontos fracos: pouca experiência com Kubernetes
```

---

## 7. Entrevista Técnica — agendar como Gestor

Login como gestor: `pedro.alves@empresa.com / senha123`

**Data/hora:** 2026-07-15 às 10:00

**Resultado — Carlos Mendes:**
```
Score       : 9.0
Anotações   : Excelente domínio de SQLAlchemy e modelagem
              relacional. Resolveu corretamente o desafio de
              query complexa com joins. Conhece boas práticas
              de indexação.
Pontos fortes: SQLAlchemy avançado | resolução de problemas | raciocínio lógico
Pontos fracos: nunca trabalhou com sistemas de alta escala
```

---

## 8. Dashboard — verificar cards de resumo

Caminho: `http://localhost:3000/dashboard`

- Passe o mouse nos cards **Candidaturas ativas**, **Decisões pendentes**, **Contratados**, **Entrevistas agendadas** e **Banco de talentos** para ver o preview hover
- Clique em qualquer card para fixar o popover aberto (ponto colorido aparece no canto)
- Clique fora ou no × para fechar

---

## 9. Vagas do seed — testar skills especiais

As vagas do seed incluem casos especialmente preparados para testar detecção de skills:

### Nutricionista Clínica (vaga 10)
Login como `daniela@sirs.com`. Verificar que:
- **Beatriz Nogueira** (contratada) tem skills: `dietpro`, `avaliação nutricional`, `nutrição clínica`, `crn`
- **Camila Nascimento** tem `nutrição hospitalar`, `avanutri`
- **Renato Cavalcante** tem nível júnior, skills básicas

### Professora de Idiomas — Inglês e Espanhol (vaga 11)
Login como `daniela@sirs.com` ou `eduardo@sirs.com`. Verificar que:
- **Sofia Andrade** (contratada) tem skills: `celta`, `moodle`, `ielts`, `toefl`
- **Pedro Yamamoto** tem `celta`, `moodle`, sem espanhol
- **Marie Dupont** tem `dalf`, `moodle`, domínio do francês

---

## Limitações conhecidas da interface

| # | Limitação | Alternativa |
|---|---|---|
| 1 | Currículo em texto — sem campo na UI | `curl -X POST .../candidaturas/{id}/curriculo/texto -d '{"texto": "..."}'` |
| 2 | Formação do candidato — sem campo na UI | curl `PATCH /candidatos/{id}` com campo `formacao` |
| 3 | Webhook JSON/XML — sem UI | `docker compose exec api python tests/demo_webhook.py` |
