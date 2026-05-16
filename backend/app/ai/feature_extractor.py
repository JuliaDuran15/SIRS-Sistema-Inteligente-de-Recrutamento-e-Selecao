"""
Extração de features estruturadas de currículos e requisitos de vaga.

Complementa a análise semântica pura (cosine similarity) com sinais baseados
em regras: anos de experiência, nível de senioridade e overlap de habilidades.

O módulo é puramente regex + dict lookup
"""
import re
from datetime import datetime

# ── Mapeamento senioridade → nível numérico ───────────────────────────────────
_SENIORIDADE: dict[str, int] = {
    # Nível 0 — sem experiência
    'estagiário': 0, 'estagiario': 0, 'estágio': 0, 'estagio': 0,
    'trainee': 0, 'aprendiz': 0,
    # Nível 1 — júnior (0-2 anos)
    'júnior': 1, 'junior': 1,
    # Nível 2 — pleno (2-5 anos)
    'pleno': 2,
    # Nível 3 — sênior (5+ anos)
    'sênior': 3, 'senior': 3, 'especialista': 3,
    # Nível 4 — lead / staff (8+ anos)
    'tech lead': 4, 'lead': 4, 'staff': 4, 'principal': 4,
    'líder técnico': 4, 'lider tecnico': 4, 'arquiteto': 4,
    # Nível 5 — gestão
    'head': 5, 'coordenador': 5, 'gerente': 5,
    # Nível 6 — direção
    'diretor': 6, 'vp': 6, 'cto': 6,
}

# Anos típicos de experiência por nível (usados como fallback quando a vaga
# menciona senioridade mas não um número explícito de anos)
_ANOS_POR_NIVEL: dict[int, float] = {
    0: 0.0,
    1: 1.0,
    2: 3.0,
    3: 6.0,
    4: 9.0,
    5: 12.0,
    6: 15.0,
}

# ── Catálogo de habilidades técnicas (forma canônica) ────────────────────────
_HABILIDADES_TECH: frozenset[str] = frozenset({
    # Linguagens
    'python', 'java', 'javascript', 'typescript', 'go', 'golang', 'rust',
    'c++', 'c#', 'kotlin', 'swift', 'php', 'ruby', 'scala', 'r',
    'dart', 'elixir', 'haskell', 'lua', 'perl', 'groovy',
    # Web / API
    'fastapi', 'django', 'flask', 'react', 'vue', 'angular',
    'node.js', 'express', 'nestjs', 'nextjs', 'nuxt', 'svelte',
    'graphql', 'rest', 'grpc', 'fastify', 'spring', 'springboot',
    'laravel', 'rails', 'asp.net', 'blazor',
    # Dados & IA
    'spark', 'pyspark', 'airflow', 'kafka', 'dbt', 'hadoop', 'flink',
    'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
    'keras', 'huggingface', 'langchain', 'openai', 'llm',
    'mlflow', 'sagemaker', 'vertex ai', 'databricks',
    # Banco de dados
    'postgresql', 'mysql', 'mongodb', 'redis', 'sqlite',
    'elasticsearch', 'cassandra', 'dynamodb', 'oracle', 'sql server',
    'mariadb', 'neo4j', 'influxdb', 'cockroachdb', 'sql', 'nosql',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes',
    'terraform', 'ansible', 'pulumi', 'helm',
    'github actions', 'gitlab ci', 'jenkins', 'ci/cd', 'argocd',
    'linux', 'nginx', 'apache',
    # Ferramentas
    'git', 'celery', 'rabbitmq', 'jira', 'confluence',
    'power bi', 'excel', 'figma', 'tableau', 'looker', 'metabase',
    'postman', 'swagger', 'sonarqube',
    # Negócio / ERP
    'sap', 'sap fi', 'sap sd', 'sap mm', 'erp', 'crm', 'salesforce',
    'totvs', 'protheus', 'oracle erp',
    # Financeiro / Contábil
    'ifrs', 'cpc', 'gaap', 'conciliação', 'controladoria',
    'planejamento orçamentário', 'fluxo de caixa', 'demonstrações financeiras',
    # Metodologias
    'agile', 'scrum', 'kanban', 'lean', 'safe', 'xp',
})

# ── Aliases → forma canônica ──────────────────────────────────────────────────
# Normaliza variações de escrita para a skill canônica do catálogo acima.
_ALIASES: dict[str, str] = {
    # Python
    'python3': 'python', 'python 3': 'python',
    # JavaScript / TypeScript
    'js': 'javascript', 'es6': 'javascript', 'es2015': 'javascript',
    'ts': 'typescript',
    # Node
    'node': 'node.js', 'nodejs': 'node.js', 'node js': 'node.js',
    # React
    'react.js': 'react', 'reactjs': 'react', 'react native': 'react',
    # Next.js
    'next.js': 'nextjs', 'next js': 'nextjs',
    # Vue / Angular
    'vue.js': 'vue', 'vuejs': 'vue',
    'angularjs': 'angular', 'angular.js': 'angular',
    # Spring
    'spring boot': 'springboot', 'spring framework': 'spring',
    # Kubernetes
    'k8s': 'kubernetes',
    # PostgreSQL
    'postgres': 'postgresql', 'pgsql': 'postgresql',
    # SQL Server
    'mssql': 'sql server', 'ms sql': 'sql server', 't-sql': 'sql server',
    # AWS serviços (normalizar para aws)
    'ec2': 'aws', 's3': 'aws', 'lambda': 'aws', 'rds': 'aws',
    'eks': 'aws', 'ecs': 'aws',
    # GCP
    'google cloud': 'gcp', 'google cloud platform': 'gcp', 'bigquery': 'gcp',
    # Azure
    'microsoft azure': 'azure', 'azure devops': 'azure',
    # CI/CD
    'continuous integration': 'ci/cd', 'continuous delivery': 'ci/cd',
    'devops': 'ci/cd',
    # Scikit-learn
    'sklearn': 'scikit-learn',
    # LLM / IA generativa
    'gpt': 'openai', 'chatgpt': 'openai', 'openai api': 'openai',
    'transformers': 'huggingface',
    # Negócio
    'power automate': 'erp',  # automação de processos
    'sharepoint': 'erp',
}


# ─────────────────────────────────────────────────────────────────────────────
# Funções públicas
# ─────────────────────────────────────────────────────────────────────────────

def extrair_features_curriculo(
    texto: str,
    formacao: list | None = None,
) -> dict:
    """
    Extrai features estruturadas de um texto de currículo.

    Returns dict com:
      anos_experiencia  — float: anos estimados de experiência profissional
      nivel_senioridade — int:   0=estágio … 6=direção
      habilidades       — set:   skills técnicas identificadas
      nivel_educacao    — int:   0=sem … 5=doutorado
    """
    habilidades = _extrair_habilidades(texto)
    return {
        "anos_experiencia"  : _extrair_anos_curriculo(texto),
        "nivel_senioridade" : _extrair_nivel(texto),
        "habilidades"       : habilidades,
        "proficiencia_skills": _extrair_proficiencia(texto, habilidades),
        "nivel_educacao"    : _extrair_educacao(texto, formacao or []),
    }


def extrair_features_vaga(
    texto: str,
    termos_mercado: list | None = None,
) -> dict:
    """
    Extrai features estruturadas de um texto de requisitos de vaga.
    termos_mercado: lista de dicts {"termo": str, "frequencia": int} do ranking_mercado.
    """
    habilidades = _extrair_habilidades(texto)

    # Enriquece com termos do ranking de mercado (já validados externamente)
    if termos_mercado:
        for item in termos_mercado:
            termo = (item.get("termo", "") if isinstance(item, dict) else str(item)).lower().strip()
            if termo and len(termo) >= 2:
                habilidades.add(termo)

    return {
        "anos_minimos"    : _extrair_anos_minimos_vaga(texto),
        "nivel_esperado"  : _extrair_nivel(texto),
        "habilidades"     : habilidades,
    }


def calcular_bonus_estrutural(
    features_curriculo: dict,
    features_vaga: dict,
) -> float:
    """
    Retorna um bônus/penalidade entre -0.25 e +0.25 baseado em:
      - Adequação de anos de experiência ao requisito
      - Alinhamento de nível de senioridade
      - Overlap de habilidades técnicas

    O intervalo pequeno garante que o sinal estrutural complemente
    (e não substitua) a similaridade semântica.
    """
    bonus = 0.0

    anos_cand  = features_curriculo.get("anos_experiencia", 0.0)
    anos_req   = features_vaga.get("anos_minimos", 0.0)
    nivel_cand = features_curriculo.get("nivel_senioridade", 0)
    nivel_req  = features_vaga.get("nivel_esperado", 0)

    # Inferir anos mínimos a partir do nível esperado quando não declarado
    if anos_req == 0.0 and nivel_req > 0:
        anos_req = _ANOS_POR_NIVEL.get(nivel_req, 0.0)

    # ── 3. Overlap de habilidades calculado antes — condiciona componentes ───────
    hab_req  = features_vaga.get("habilidades", set())
    hab_cand = features_curriculo.get("habilidades", set())
    profic   = features_curriculo.get("proficiencia_skills", {})
    overlap  = 0.0
    if hab_req and hab_cand:
        skills_comuns = hab_req & hab_cand
        if skills_comuns:
            if profic:
                peso_total = sum(profic.get(s, 1.0) for s in skills_comuns)
                overlap = peso_total / len(hab_req)
            else:
                overlap = len(skills_comuns) / len(hab_req)
            bonus += overlap * 0.08
        else:
            bonus -= 0.15          # candidato tem skills mas nenhuma é relevante

    # ── 1. Experiência (±0.08, escalada pelo overlap para evitar premiar exp irrelevante) ──
    if anos_req > 0 and anos_cand > 0:
        ratio = anos_cand / anos_req
        # Escala o bônus positivo pelo overlap: exp irrelevante vale menos
        escala = max(overlap, 0.3) if hab_req else 1.0
        if ratio >= 1.0:
            bonus += 0.08 * escala
        elif ratio >= 0.7:
            bonus += 0.03 * escala
        elif ratio < 0.35:
            bonus -= 0.10          # penalidade por anos insuficientes não é escalada

    # ── 2. Senioridade (penalidade proporcional ao gap) ───────────────────────
    if nivel_req > 0 and nivel_cand > 0:
        diff = nivel_cand - nivel_req
        if diff == 0:
            bonus += 0.07          # nível exato
        elif diff == 1:
            bonus += 0.03          # um nível acima: levemente favorável
        elif diff > 1:
            bonus -= 0.01          # muito acima: possível overqualification
        elif diff == -1:
            bonus -= 0.05          # um nível abaixo
        elif diff == -2:
            bonus -= 0.10          # dois níveis abaixo
        else:
            bonus -= 0.15          # três+ níveis abaixo: mismatch severo

    return max(-0.25, min(0.25, bonus))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _extrair_anos_curriculo(texto: str) -> float:
    """
    Estima anos de experiência profissional acumulada a partir do texto do currículo.

    Estratégia em ordem de prioridade:
      1. Declaração explícita ("X anos de experiência")
      2. Soma de intervalos de emprego detectados (yyyy–yyyy, mm/yyyy–mm/yyyy, etc.)
      3. Fallback conservador via menor ano encontrado no texto
    """
    texto_lower = texto.lower()
    ano_atual   = datetime.now().year

    # ── 1. Declaração explícita ──────────────────────────────────────────────
    padroes_explicitos = [
        r'(\d{1,2})\s+anos?\s+de\s+experi[eê]ncia',
        r'experi[eê]ncia\s+de\s+(\d{1,2})\s+anos?',
        r'(\d{1,2})\s+anos?\s+de\s+mercado',
        r'(\d{1,2})\s+anos?\s+de\s+atua[cç][aã]o',
        r'(\d{1,2})\+?\s*years?\s+of\s+experience',
        r'h[áa]\s+(\d{1,2})\s+anos?\s+trabalh',
    ]
    valores_explicitos: list[float] = []
    for p in padroes_explicitos:
        for m in re.findall(p, texto_lower):
            try:
                v = int(m)
                if 1 <= v <= 45:
                    valores_explicitos.append(float(v))
            except (ValueError, TypeError):
                pass
    if valores_explicitos:
        return max(valores_explicitos)

    # ── 2. Soma de intervalos de emprego ─────────────────────────────────────
    # Restringe a busca à seção "experiência" quando detectável —
    # evita somar anos de formação ou de outras seções não profissionais.
    from app.ai.section_extractor import extrair_secoes
    secoes = extrair_secoes(texto)
    secao_exp = secoes.get("experiencia", "").strip()
    texto_busca = (secao_exp if secao_exp else texto).lower()

    # Detecta padrões como:
    #   2018–2022 | 2019 - 2023 | 01/2018 - 12/2022
    #   2020 – presente | 2021 - atual | 2022 - current
    _FIM_ABERTOS = {'presente', 'atual', 'current', 'now', 'hoje'}

    # Padrão: (mm/)yyyy – (mm/)yyyy ou (mm/)yyyy – presente
    _PAD_INTERVALO = re.compile(
        r'(?:(?:\d{1,2})[/\-])?'           # mês/dia opcional
        r'((?:19|20)\d{2})'                  # ano início
        r'\s*[–\-—]\s*'                      # separador
        r'(?:'
            r'(?:(?:\d{1,2})[/\-])?((?:19|20)\d{2})'   # ano fim numérico
            r'|(' + '|'.join(_FIM_ABERTOS) + r')'        # ou "atual/presente"
        r')',
        re.IGNORECASE,
    )

    intervalos: list[tuple[int, int]] = []
    for m in _PAD_INTERVALO.finditer(texto_busca):
        inicio = int(m.group(1))
        if m.group(2):
            fim = int(m.group(2))
        else:
            fim = ano_atual   # "presente" / "atual"

        if 1980 <= inicio <= ano_atual and inicio <= fim <= ano_atual + 1:
            intervalos.append((inicio, fim))

    # Padrão adicional: "desde 2018", "since 2019", "a partir de 2020"
    _PAD_DESDE = re.compile(
        r'(?:desde|since|a\s+partir\s+de)\s+((?:19|20)\d{2})',
        re.IGNORECASE,
    )
    for m in _PAD_DESDE.finditer(texto_busca):
        inicio = int(m.group(1))
        if 1980 <= inicio <= ano_atual:
            intervalos.append((inicio, ano_atual))

    if intervalos:
        total = _somar_intervalos_sem_sobreposicao(intervalos)
        if total > 0:
            return round(total, 1)

    # ── 3. Fallback conservador ───────────────────────────────────────────────
    # Usa o menor ano encontrado na seção de experiência (ou texto completo),
    # divide por 1.4 para ser conservador.
    anos_texto = [int(y) for y in re.findall(r'\b(20\d{2}|19[89]\d)\b', texto_busca)]
    anos_validos = [a for a in anos_texto if 1990 <= a <= ano_atual]
    if len(anos_validos) >= 2:
        span = ano_atual - min(anos_validos)
        return round(span / 1.4, 1)

    return 0.0


def _somar_intervalos_sem_sobreposicao(intervalos: list[tuple[int, int]]) -> float:
    """
    Soma durações de intervalos eliminando sobreposições.
    Ex: [(2015,2018),(2017,2020),(2020,2023)] → 8 anos (não 11).
    """
    if not intervalos:
        return 0.0
    ordenados = sorted(intervalos)
    merged: list[tuple[int, int]] = [ordenados[0]]
    for inicio, fim in ordenados[1:]:
        prev_inicio, prev_fim = merged[-1]
        if inicio <= prev_fim:                 # sobreposição ou adjacente
            merged[-1] = (prev_inicio, max(prev_fim, fim))
        else:
            merged.append((inicio, fim))
    return float(sum(fim - inicio for inicio, fim in merged))


def _extrair_anos_minimos_vaga(texto: str) -> float:
    """Extrai anos mínimos de experiência exigidos pela vaga."""
    padroes = [
        r'(\d{1,2})\+?\s+anos?\s+de\s+experi[eê]ncia',
        r'm[íi]nimo\s+de?\s+(\d{1,2})\s+anos?',
        r'(\d{1,2})\s+anos?\s+ou\s+mais',
        r'(\d{1,2})\+\s*anos?',
    ]
    for p in padroes:
        m = re.search(p, texto.lower())
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                pass
    return 0.0


def _extrair_nivel(texto: str) -> int:
    """Extrai nível de senioridade mencionado no texto (currículo ou vaga)."""
    texto_lower = texto.lower()
    nivel_max = 0
    # Verifica frases multi-palavra primeiro (mais específicas)
    for keyword in sorted(_SENIORIDADE, key=len, reverse=True):
        if keyword in texto_lower:
            nivel_max = max(nivel_max, _SENIORIDADE[keyword])
    return nivel_max


# ── Modificadores de proficiência ────────────────────────────────────────────
_PROF_BAIXO: frozenset[str] = frozenset({
    'básico', 'básica', 'básicos', 'básicas',
    'iniciante', 'iniciantes', 'noções', 'noção',
    'conhecimento básico', 'conhecimentos básicos',
    'rudimentar', 'elementar', 'superficial',
    'beginner', 'basic', 'introductory',
    'pouco', 'um pouco',
})
_PROF_ALTO: frozenset[str] = frozenset({
    'avançado', 'avançada', 'sólido', 'sólida', 'profundo', 'profunda',
    'expert', 'especialista', 'extenso', 'amplo', 'domínio',
    'advanced', 'proficient', 'expert',
})

_WB  = r'(?<![a-z0-9\+\#\.])'  # word-boundary esquerdo (inclui ponto)
_WB_R = r'(?![a-z0-9\+\#\.])'  # word-boundary direito  (inclui ponto)

# Mapa inverso: canonical → todas as formas pesquisáveis (inclui aliases)
_SKILL_BUSCA: dict[str, list[str]] = {s: [s] for s in _HABILIDADES_TECH}
for _alias, _canonical in _ALIASES.items():
    if _canonical in _SKILL_BUSCA:
        _SKILL_BUSCA[_canonical].append(_alias)


def _encontra_skill(texto_lower: str, patterns: list[str]) -> int:
    """Retorna a posição da primeira ocorrência de qualquer forma da skill, ou -1."""
    for p in patterns:
        m = re.search(_WB + re.escape(p) + _WB_R, texto_lower)
        if m:
            return m.start()
    return -1


def _extrair_habilidades(texto: str) -> set[str]:
    """
    Retorna o conjunto de habilidades técnicas reconhecidas no texto.
    Busca cada skill junto com seus aliases — sem modificar o texto.
    """
    texto_lower = texto.lower()
    encontradas: set[str] = set()
    for canonical, patterns in _SKILL_BUSCA.items():
        if _encontra_skill(texto_lower, patterns) >= 0:
            encontradas.add(canonical)
    return encontradas


def _extrair_proficiencia(texto: str, habilidades: set[str]) -> dict[str, float]:
    """
    Para cada skill detectada, retorna um multiplicador de proficiência (0.3–1.3).
    Examina uma janela de ±70 chars em volta de cada menção da skill.

    0.3 = mencionado como básico/iniciante
    1.0 = mencionado sem modificador (padrão)
    1.3 = mencionado como avançado/expert
    """
    texto_lower = texto.lower()
    resultado: dict[str, float] = {}
    for skill in habilidades:
        pos = _encontra_skill(texto_lower, _SKILL_BUSCA.get(skill, [skill]))
        if pos < 0:
            resultado[skill] = 1.0
            continue
        janela = texto_lower[max(0, pos - 70): pos + len(skill) + 70]
        if any(m in janela for m in _PROF_BAIXO):
            resultado[skill] = 0.3
        elif any(m in janela for m in _PROF_ALTO):
            resultado[skill] = 1.3
        else:
            resultado[skill] = 1.0
    return resultado


_INCOMPLETO = frozenset({'cursando', 'trancado', 'trancada', 'em andamento', 'interrompido', 'incompleto'})


def _extrair_educacao(texto: str, formacao: list) -> int:
    """
    Retorna nível de educação:
    0=sem / 1=técnico / 2=graduação incompleta (cursando/trancado) /
    3=graduação / 4=pós/MBA / 5=mestrado / 6=doutorado
    """
    nivel_map = {
        'tecnico': 1, 'técnico': 1, 'tecnologo': 1, 'tecnólogo': 1,
        'graduacao': 3, 'graduação': 3, 'bacharelado': 3, 'licenciatura': 3,
        'especializacao': 4, 'especialização': 4, 'mba': 4,
        'mestrado': 5, 'msc': 5,
        'doutorado': 6, 'phd': 6,
    }
    if formacao:
        nivel_max = 0
        for f in formacao:
            nivel = nivel_map.get((f.get("nivel") or "").lower(), 0)
            status = (f.get("status") or "").lower()
            # Graduação com status de cursando/trancado → incompleta
            if nivel == 3 and status in ('cursando', 'em andamento', 'trancado'):
                nivel = 2
            nivel_max = max(nivel_max, nivel)
        if nivel_max > 0:
            return nivel_max

    texto_lower = texto.lower()
    for palavra, nivel in sorted(nivel_map.items(), key=lambda x: -x[1]):
        if palavra in texto_lower:
            # Graduação com indicador de incompleto em qualquer parte do texto
            if nivel == 3 and any(inc in texto_lower for inc in _INCOMPLETO):
                return 2
            return nivel

    # Fallback: "cursando" ou "trancado" sem palavra-chave de grau → graduação incompleta
    if any(inc in texto_lower for inc in ('cursando', 'trancado', 'trancada')):
        return 2
    return 0
