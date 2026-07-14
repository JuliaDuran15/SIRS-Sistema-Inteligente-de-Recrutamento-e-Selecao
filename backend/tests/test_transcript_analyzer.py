"""
Testes do analisador de transcrições de entrevistas.

Cobre limpeza de artefatos, classificação, truncamento e análise end-to-end
com transcrições realistas e imperfeitas (como saem do Google Meet/Zoom).
"""
import pytest
from app.ai.transcript_analyzer import (
    _limpar,
    _sentencas,
    _classificar,
    _resumir,
    analisar_transcricao,
)


# ─── _limpar ──────────────────────────────────────────────────────────────────

class TestLimpar:
    def test_remove_timestamp_simples(self):
        assert "1:30" not in _limpar("bom dia 1:30 como vai")

    def test_remove_timestamp_com_hora(self):
        assert "1:30:45" not in _limpar("falou muito bem 1:30:45 sobre o projeto")

    def test_remove_timestamp_com_colchetes(self):
        resultado = _limpar("[00:05:12] o candidato chegou a tempo")
        assert "[" not in resultado
        assert "candidato chegou a tempo" in resultado

    def test_remove_label_falante_rh(self):
        resultado = _limpar("RH: me conta sobre sua experiência")
        assert "RH:" not in resultado
        assert "me conta" in resultado

    def test_remove_label_falante_nome_proprio(self):
        resultado = _limpar("Ana Paula: trabalhei por cinco anos na empresa")
        assert "Ana Paula:" not in resultado
        assert "trabalhei" in resultado

    def test_remove_label_com_papel_parenteses(self):
        resultado = _limpar("Ana (RH): boa tarde, pode começar")
        assert "Ana (RH):" not in resultado
        assert "boa tarde" in resultado

    def test_timestamp_seguido_de_label_multiline(self):
        """Formato real do Google Meet: timestamp + nome na mesma linha, fala na próxima."""
        transcript = "0:00:05 Ana (RH)\nBoa tarde, pode se apresentar?\n"
        resultado = _limpar(transcript)
        # timestamp e o nome na linha isolada devem sumir, conteúdo deve permanecer
        assert "0:00" not in resultado
        assert "Boa tarde" in resultado

    def test_remove_tags_html(self):
        resultado = _limpar("<b>forte</b> conhecimento em Python <i>avançado</i>")
        assert "<b>" not in resultado
        assert "<i>" not in resultado
        assert "forte" in resultado
        assert "Python" in resultado

    def test_normaliza_espacos_multiplos(self):
        resultado = _limpar("olá   como   vai")
        assert "  " not in resultado

    def test_texto_limpo_sem_artefatos_nao_muda(self):
        texto = "Tenho oito anos de experiência com Python e liderança de times."
        resultado = _limpar(texto)
        assert "experiência" in resultado
        assert "liderança" in resultado

    def test_transcript_google_meet_real(self):
        """Formato típico exportado pelo Google Meet."""
        transcript = (
            "0:00:03 Entrevistador\n"
            "Boa tarde, pode se apresentar?\n\n"
            "0:00:08 João Silva\n"
            "Claro, sou desenvolvedor sênior com dez anos de experiência."
        )
        resultado = _limpar(transcript)
        assert "0:00" not in resultado
        assert "desenvolvedor" in resultado


# ─── _sentencas ───────────────────────────────────────────────────────────────

class TestSentencas:
    def test_divide_por_ponto(self):
        sents = _sentencas("Tenho experiência em Python há mais de cinco anos. Trabalhei em empresas de tecnologia.")
        assert len(sents) == 2

    def test_divide_por_exclamacao(self):
        sents = _sentencas("Que resultado incrível e muito impactante! Entregamos o projeto antes do prazo previsto.")
        assert len(sents) >= 1

    def test_divide_por_paragrafo(self):
        sents = _sentencas("Primeiro parágrafo com conteúdo relevante e bastante detalhado.\n\nSegundo parágrafo com informação diferente.")
        assert len(sents) == 2

    def test_filtra_sentencas_muito_curtas(self):
        # "Ok." tem menos de 30 chars → deve ser filtrada
        sents = _sentencas("Ok. Tenho bastante experiência em liderança de equipes.")
        assert all(len(s) > 30 for s in sents)

    def test_texto_vazio_retorna_lista_vazia(self):
        assert _sentencas("") == []

    def test_texto_sem_pontuacao_retorna_como_sentenca(self):
        texto = "tenho cinco anos de experiência em machine learning e data science"
        sents = _sentencas(texto)
        assert len(sents) >= 1


# ─── _classificar ─────────────────────────────────────────────────────────────

class TestClassificar:
    # Casos positivos — PT
    def test_lideranca_e_forte(self):
        assert _classificar("exerci liderança de um time de dez pessoas") == "forte"

    def test_desenvolveu_entregou_e_forte(self):
        assert _classificar("desenvolvi e entreguei o projeto no prazo com ótimos resultados") == "forte"

    def test_fluente_idioma_e_forte(self):
        assert _classificar("sou fluente em inglês e espanhol avançado") == "forte"

    def test_certificado_e_forte(self):
        assert _classificar("sou certificado AWS e tenho especialização em cloud") == "forte"

    # Casos positivos — EN (termos técnicos em PT/BR)
    def test_led_team_e_forte(self):
        assert _classificar("I led the backend team and delivered the project successfully") == "forte"

    def test_improved_e_forte(self):
        assert _classificar("improved system performance by 40 percent using caching") == "forte"

    # Casos negativos — PT
    def test_nao_tenho_experiencia_e_fraco(self):
        assert _classificar("não tenho experiência com Kubernetes ainda") == "fraco"

    def test_basico_e_fraco(self):
        assert _classificar("meu conhecimento em cloud é básico ainda") == "fraco"

    def test_aprendi_recentemente_e_fraco(self):
        assert _classificar("aprendi recentemente sobre microsserviços e ainda estou estudando") == "fraco"

    def test_preciso_melhorar_e_fraco(self):
        # "comunicação" é forte, mas "preciso melhorar" + "básico" garantem maioria fraca
        assert _classificar("sei que preciso melhorar minhas habilidades de gestão de tempo básico") == "fraco"

    def test_dificuldade_e_fraco(self):
        assert _classificar("tive dificuldades para trabalhar com prazos muito curtos") == "fraco"

    # Casos negativos — EN
    def test_never_e_fraco(self):
        assert _classificar("I never worked with distributed systems before") == "fraco"

    def test_limited_e_fraco(self):
        assert _classificar("my experience with DevOps is quite limited") == "fraco"

    # Neutro
    def test_apresentacao_basica_e_neutro(self):
        assert _classificar("meu nome é Carlos e trabalho na área de tecnologia há algum tempo") == "neutro"

    def test_descricao_empresa_e_neutro(self):
        assert _classificar("a empresa onde trabalhei tem sede em São Paulo e atua no setor financeiro") == "neutro"

    # Ambiguidade — prevalece quem tem mais matches
    def test_mais_fortes_que_fracos_e_forte(self):
        # 3 fortes vs 1 fraco
        sent = "liderança, autonomia e excelente comunicação, porém limitado em devops"
        assert _classificar(sent) == "forte"

    def test_mais_fracos_que_fortes_e_fraco(self):
        sent = "não tenho experiência e básico e nunca usei, mas sou proativo"
        assert _classificar(sent) == "fraco"


# ─── _resumir ─────────────────────────────────────────────────────────────────

class TestResumir:
    def test_sentenca_curta_nao_e_truncada(self):
        s = "Liderança e comunicação clara."
        assert _resumir(s) == s.rstrip(".")

    def test_sentenca_longa_e_truncada(self):
        s = "Desenvolvi e implementei uma solução de microsserviços altamente escalável."
        resultado = _resumir(s, max_len=30)
        assert len(resultado) <= 34  # margem de palavra
        assert resultado.endswith("…")

    def test_truncamento_respeita_borda_de_palavra(self):
        s = "Tenho experiência com Python Django e Flask no backend."
        resultado = _resumir(s, max_len=25)
        # não pode terminar no meio de uma palavra
        assert " " not in resultado.rstrip("…").split("…")[0][-1:]

    def test_remove_pontuacao_final(self):
        assert not _resumir("Boa comunicação,").endswith(",")
        assert not _resumir("Boa comunicação.").endswith(".")

    def test_sentenca_exatamente_no_limite(self):
        s = "A" * 55
        resultado = _resumir(s, max_len=55)
        assert len(resultado) <= 55


# ─── analisar_transcricao — end-to-end ───────────────────────────────────────

class TestAnalisarTranscricao:

    # ── Caso básico ───────────────────────────────────────────────────────────

    def test_retorna_chaves_esperadas(self):
        resultado = analisar_transcricao("Tenho dez anos de experiência em liderança técnica.")
        assert set(resultado.keys()) == {"pontos_fortes", "pontos_fracos", "anotacoes"}

    def test_listas_sao_listas(self):
        r = analisar_transcricao("Experiência sólida em Python e entrega de resultados.")
        assert isinstance(r["pontos_fortes"], list)
        assert isinstance(r["pontos_fracos"], list)

    def test_texto_vazio_retorna_estrutura_vazia(self):
        r = analisar_transcricao("   ")
        assert r["pontos_fortes"] == []
        assert r["pontos_fracos"] == []
        assert r["anotacoes"] == ""

    def test_texto_muito_curto_sem_crash(self):
        r = analisar_transcricao("Ok.")
        assert isinstance(r, dict)

    # ── Transcrição com pontos fortes claros ──────────────────────────────────

    def test_detecta_pontos_fortes_sênior(self):
        transcript = """
        Entrevistador: fale sobre sua trajetória.
        Candidato: trabalhei por oito anos liderando times de engenharia.
        Entregamos produtos para mais de dois milhões de usuários.
        Tenho domínio de Python, Go e arquitetura de microsserviços.
        Fui reconhecido como principal entregador de valor em dois anos consecutivos.
        Sou certificado em AWS e tenho experiência sólida com Kubernetes.
        A comunicação e colaboração com o time eram sempre destacadas pelos meus gestores.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) >= 2

    # ── Transcrição com fraquezas claras ──────────────────────────────────────

    def test_detecta_pontos_fracos(self):
        transcript = """
        Não tenho experiência com gerenciamento de infraestrutura em cloud.
        Meu conhecimento em Kubernetes é básico, aprendi recentemente no curso.
        Ainda estou aprendendo sobre DevOps e tenho dificuldades com CI/CD.
        Nunca trabalhei com times distribuídos globalmente.
        Preciso melhorar minha comunicação em inglês técnico.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fracos"]) >= 2

    # ── Transcrição mista (realista) ──────────────────────────────────────────

    def test_transcript_entrevista_rh_realista(self):
        """
        Transcrição típica exportada do Google Meet com artefatos:
        timestamps, labels de falante, fala repetida, interrupções.
        """
        transcript = """
        0:00:05 Ana (RH)
        Boa tarde João, obrigada por vir. Pode se apresentar brevemente?

        0:00:10 João
        Claro, boa tarde. Sou engenheiro de software, atuo há seis anos na área.
        Trabalhei principalmente com backend em Python e Go.
        Liderando equipes pequenas nos últimos três anos.

        0:01:20 Ana (RH)
        Que projeto você mais se orgulha?

        0:01:25 João
        Desenvolvemos um sistema de pagamentos que processa mais de cem mil transações por dia.
        Implementei a arquitetura do zero e entregamos três semanas antes do prazo.
        O impacto foi uma redução de 40% no custo operacional da empresa.

        0:02:40 Ana (RH)
        E alguma fraqueza que você reconhece?

        0:02:45 João
        Honestamente, não tenho muita experiência com mobile development.
        E meu conhecimento em infraestrutura de cloud é ainda básico.
        Mas estou estudando AWS atualmente.

        0:03:30 Ana (RH)
        Ótimo, e como você lida com conflitos no time?

        0:03:35 João
        Prefiro comunicação direta. Quando há conflito resolvo de forma colaborativa.
        Tive situações difíceis antes mas sempre conseguimos chegar num consenso.
        Autonomia e iniciativa são valores que priorizo no time.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) >= 1
        assert len(r["pontos_fracos"]) >= 1
        assert len(r["anotacoes"]) > 0
        # timestamps não devem vazar para o output
        assert "0:00" not in r["anotacoes"]
        assert "0:01" not in r["anotacoes"]

    def test_transcript_tecnica_com_codigo_e_jargao(self):
        """Entrevista técnica com muitos termos em inglês."""
        transcript = """
        Entrevistador: descreva sua experiência com sistemas distribuídos.

        Candidato: tenho forte experiência com event-driven architecture.
        Implementei sistemas usando Kafka e Redis para streaming de dados.
        Liderando o design de uma solução de alta disponibilidade para e-commerce.
        O sistema achieved 99.9% uptime e improved latency by 30%.

        Entrevistador: e pontos a desenvolver?

        Candidato: não tenho experiência prática com machine learning ainda.
        Meu conhecimento em ML é ainda superficial, tenho só o básico de teoria.
        Também nunca trabalhei com infraestrutura on-premise, só cloud.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) >= 1
        assert len(r["pontos_fracos"]) >= 1

    # ── Transcrição com muito ruído ───────────────────────────────────────────

    def test_transcript_com_muito_ruido_nao_quebra(self):
        """Transcrição automática com erros de reconhecimento de fala."""
        transcript = """
        [00:01:10] [inaudível]
        eh então como eu disse trabalhei durante cinco anos entregando projetos de grande porte.
        [00:01:18] [ruído de fundo]
        implementei solução de alta disponibilidade com liderança técnica reconhecida pelo time.
        [00:01:30] [sobreposição]
        não tenho muita experiência com testes automatizados ainda. preciso melhorar nisso básico.
        """
        r = analisar_transcricao(transcript)
        assert isinstance(r["pontos_fortes"], list)
        assert isinstance(r["pontos_fracos"], list)
        # marcadores de ruído não devem aparecer no output
        assert "inaudível" not in str(r)
        assert "ruído" not in str(r)

    def test_transcript_zoom_com_header(self):
        """Formato de exportação do Zoom com cabeçalho."""
        transcript = """
        <html><body>
        <b>Transcrição da reunião</b><br>
        <i>Data: 2024-05-10</i>

        Recrutador: 00:00:05
        Pode começar se apresentando.

        Candidata: 00:00:08
        Sim, claro. Sou gestora de projetos com doze anos de mercado.
        Coordenei times multidisciplinares e entreguei projetos com orçamento acima de R$10 milhões.
        Tenho certificação PMP e especialização em metodologias ágeis.
        Sou reconhecida por minha excelente comunicação e proatividade.

        Recrutador: 00:01:00
        Algum ponto de melhoria?

        Candidata: 00:01:05
        Tenho dificuldades com ferramentas técnicas como programação.
        Nunca aprendi a codar de verdade, falta esse conhecimento técnico mais profundo.
        </body></html>
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) >= 1
        assert len(r["pontos_fracos"]) >= 1
        # tags HTML não devem vazar
        assert "<" not in r["anotacoes"]
        assert "<" not in " ".join(r["pontos_fortes"])

    # ── Limites e edge cases ──────────────────────────────────────────────────

    def test_max_por_categoria_e_respeitado(self):
        """Garante que não retorna mais itens que max_por_categoria."""
        # Muitas frases fortes
        transcript = " ".join([
            "Implementei um sistema complexo de alta disponibilidade.",
            "Desenvolvi e entreguei cinco projetos críticos no prazo.",
            "Liderando equipes de engenharia com excelentes resultados.",
            "Sou certificado e especialista em arquitetura de software.",
            "Melhorei a performance do sistema em 60% com autonomia total.",
            "Criei a cultura de entrega e alcancei metas agressivas de crescimento.",
        ])
        r = analisar_transcricao(transcript, max_por_categoria=3)
        assert len(r["pontos_fortes"]) <= 3
        assert len(r["pontos_fracos"]) <= 3

    def test_sem_duplicatas_em_pontos_fortes(self):
        """Mesmo com texto repetido, não deve duplicar itens na lista."""
        transcript = (
            "Tenho liderança técnica forte e domínio de arquitetura. " * 5
        )
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) == len(set(r["pontos_fortes"]))

    def test_anotacoes_nao_vazias_para_transcript_substancial(self):
        """Transcrição com conteúdo neutro real deve gerar anotações."""
        transcript = """
        Me formei em Ciência da Computação em 2018 pela Universidade Federal.
        Trabalhei em startups e empresas de médio porte ao longo da carreira.
        Atualmente busco uma oportunidade em engenharia de dados ou backend.
        Prefiro trabalho remoto mas tenho flexibilidade para modelo híbrido.
        """
        r = analisar_transcricao(transcript)
        assert len(r["anotacoes"]) > 10

    def test_transcript_apenas_em_ingles(self):
        """Transcrição totalmente em inglês deve funcionar."""
        transcript = """
        Interviewer: Tell me about your background.
        Candidate: I have led engineering teams for five years delivering excellent results.
        I implemented microservices architecture and improved system performance significantly.
        I am certified in AWS and have strong expertise in distributed systems.
        My weakness is that I have limited experience with mobile development.
        I never worked with React Native before and my frontend skills are quite basic.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fortes"]) >= 1
        assert len(r["pontos_fracos"]) >= 1

    def test_transcript_candidato_junior(self):
        """Candidato júnior — mais fraquezas que pontos fortes esperado."""
        transcript = """
        Entrevistador: me fala sobre sua experiência.

        Candidato: sou recém-formado, ainda não tenho muita experiência profissional.
        Fiz estágio por seis meses e aprendi bastante, mas sei que é pouco.
        Meu conhecimento em banco de dados é básico ainda, só MySQL introdutório.
        Nunca trabalhei com sistemas em produção de verdade, só projetos acadêmicos.
        Tenho dificuldades com estimativas de prazo e gerenciamento de prioridades.
        Mas sou muito proativo e tenho iniciativa para aprender coisas novas.
        """
        r = analisar_transcricao(transcript)
        assert len(r["pontos_fracos"]) >= 2

    def test_transcript_candidato_senior_poucos_fracos(self):
        """Candidato sênior experiente — poucos ou nenhum ponto fraco declarado."""
        transcript = """
        Tenho quinze anos de experiência em desenvolvimento de software.
        Liderando arquiteturas de sistemas críticos com mais de um milhão de usuários.
        Desenvolvi plataformas de pagamento que processam bilhões em transações.
        Implementei práticas de engenharia que melhoraram a eficiência do time em 50%.
        Tenho domínio avançado de cloud, microsserviços e arquiteturas event-driven.
        Fui mentor de dezenas de engenheiros júnior e sênior ao longo da carreira.
        Reconhecido por entregar resultados excepcionais com autonomia total.
        """
        r = analisar_transcricao(transcript)

        print("\n── Resultado da análise ──────────────────────────────")
        print("PONTOS FORTES:")
        for i, p in enumerate(r["pontos_fortes"], 1):
            print(f"  {i}. {p}")
        print("PONTOS FRACOS:")
        for i, p in enumerate(r["pontos_fracos"], 1):
            print(f"  {i}. {p}")
        print(f"ANOTAÇÕES: {r['anotacoes'] or '(nenhuma)'}")
        print("─────────────────────────────────────────────────────")

        assert len(r["pontos_fortes"]) >= 3

    def test_entrevista_longa_e_complexa_com_typos(self):
        """
        Transcrição longa e realista: Google Meet, typos, sobreposições, misto PT/EN.
        Só imprime o resultado — sem assertions rígidas de contagem.
        """
        transcript = """
        0:00:03 Ana (RH)
        Boa tarde Pedro, tudo bem? Obrigada por aceitar essa conversa hoje.
        Pode começar se aprsentando brevemente pra gente?

        0:00:12 Pedro Alves
        Claro, boa tarde Ana! Então, meu nome é Pedro, sou engnheiro de sofware
        com quaze dez anos de expriência no mercado. Comecei na área de QA,
        migrei pra backend e nos últimos quatro anos tô trabalhando com arquitetura
        de sistemas distribuídos. Atualmente sou tech lead num time de oito pessoas.

        0:01:05 Ana (RH)
        Ótimo! E qual foi o projeto que você considera mais desafiador da sua carreira?

        0:01:11 Pedro Alves
        [sobreposição] com certeza foi quando eu liderou— liderei, desculpa —
        a migração de um monolito legado pra microsserviços na empresa anterior.
        A gente tinha um sistema com mais de quinze anos de dívida técnica,
        e eu coordenei um time de doze engenheiros durante oito meses.
        Implementei a estratégia de strangler fig pattern pra não derrubar produção.
        Entrgamos com 98% de uptime durante toda a migração, foi bem puxado [risos].
        O impacto foi reduzir o tempo de deploy de quatro horas pra oito minutos.
        Melhorei também os processos de code review e implmentei cultura de testes,
        o que aumentou a cobertura de 12% pra 78% em seis meses.

        0:02:40 Ana (RH)
        Impressionante! E no seu papel de tech lead, como você lida com conflitos técnicos
        dentro do time?

        0:02:48 Pedro Alves
        Eu acredito muito em comunicação clara e tomada de decisão baseada em dados.
        Quando surge um conflito de abordagem técnica, eu facilito uma sessão de
        arquitetura onde cada pessoa apresenta os trade-offs da sua solução.
        Tenho autonomia pra tomar a decisão final, mas prefiro construir consenso.
        Já tive situações bem tensas, como quando dois sêniores discordavam sobre
        usar Kafka versus RabbitMQ. Conduzi um spike de três dias, medimos tudo,
        e chegamos num consenso baseado em evidências. Isso fortaleceu a confiança do time.

        0:03:55 Ana (RH)
        Muito bom. E quais são as suas principais fraquezas ou pontos de desenvolvimento?

        0:04:02 Pedro Alves
        Olha, vou ser honesto. Tenho dificuldades com a parte de gestão de pessoas
        no sentido de dar feedback negativo — não sei exatamente como fazer isso
        de forma que não desmotive a pessoa, ainda tô aprendendo isso.
        Também não tenho muita experiência com a parte de negócios e produto,
        eu sempre fui muito técnico. E front-end é basico pra mim, nunca trabalhei
        seriamente com React ou Vue, fica difícil quando preciso ajudar o time frontend.
        [inaudível] ah, e gestão de orçamento também é algo que preciso melhorar,
        nunca tive essa responsabilidade diretamente.

        0:05:10 Ana (RH)
        Entendido, obrigada pela honestidade. Como você se mantém atualizado
        tecnicamente? O mercado muda muito rápido.

        0:05:18 Pedro Alves
        Tenho uma rotina bem estruturada pra isso. Todo dia leio o Hacker News
        e alguns newsletters técnicos. Contribuo com projetos open source nos finais
        de semana — tenho um repositório com quase dois mil stars no GitHub.
        Fiz certificação em Kubernetes no ano passado e tô estudando IA aplicada
        a sistemas de recomendação. Também sou reconhecido internamente por organizar
        tech talks mensais onde o time apresenta novidades e aprendizados.
        Acredito muito em mentorar pessoas mais juniores, isso me faz crescer também.

        0:06:20 Ana (RH)
        Perfeito Pedro. Última pergunta: por que você quer sair da empresa atual?

        0:06:25 Pedro Alves
        A empresa é ótima, não tenho nada negativo a falar. Mas cheguei num ponto
        onde sinto que já alcançei tudo que podia alcançar lá. Quero um ambiente
        com desafios maiores, produto com escala global e um time que me desafie
        tecnicamente. Vi que aqui vocês trabalham com problemas complexos de
        distribuição de dados em larga escala, e é exatamente onde quero desenvolver
        minha especialização nos próximos anos.
        """

        r = analisar_transcricao(transcript)

        print("\n══ TRANSCRIÇÃO (entrada) ══════════════════════════════════")
        for linha in transcript.strip().splitlines():
            print(linha)
        print("\n══ RESULTADO DA ANÁLISE ═══════════════════════════════════")
        print("PONTOS FORTES:")
        for i, p in enumerate(r["pontos_fortes"], 1):
            print(f"  {i}. {p}")
        if not r["pontos_fortes"]:
            print("  (nenhum detectado)")
        print("PONTOS FRACOS:")
        for i, p in enumerate(r["pontos_fracos"], 1):
            print(f"  {i}. {p}")
        if not r["pontos_fracos"]:
            print("  (nenhum detectado)")
        print(f"ANOTAÇÕES: {r['anotacoes'] or '(nenhuma)'}")
        print("══════════════════════════════════════════════════════════")

        assert len(r["pontos_fortes"]) >= 2, f"esperava >= 2 fortes, encontrou: {r['pontos_fortes']}"
        assert len(r["pontos_fracos"]) >= 1, f"esperava >= 1 fraco, encontrou: {r['pontos_fracos']}"
        assert "0:0" not in str(r), "timestamp vazou para o output"
        assert "Ana" not in " ".join(r["pontos_fortes"] + r["pontos_fracos"])


# ─── Novos testes — iteração 2 ────────────────────────────────────────────────

class TestLimparNomeSemColon:
    """Labels de falante em linha isolada sem dois-pontos (Google Meet / Zoom)."""

    def test_nome_simples_removido(self):
        resultado = _limpar("Entrevistador\nFale sobre sua trajetória profissional.")
        assert "Entrevistador" not in resultado
        assert "trajetória" in resultado

    def test_nome_composto_apos_timestamp_removido(self):
        resultado = _limpar("0:00:08 João Silva\nClaro, sou desenvolvedor sênior.")
        assert "João Silva" not in resultado
        assert "desenvolvedor sênior" in resultado

    def test_nome_com_papel_sem_colon_removido(self):
        """'Ana (RH)' em linha isolada sem dois-pontos — removido pelo passo 3."""
        resultado = _limpar("0:00:05 Ana (RH)\nBoa tarde, pode começar?")
        assert not resultado.lstrip().startswith("Ana (RH)")
        assert "Boa tarde" in resultado

    def test_nome_em_dialogo_nao_removido(self):
        """Nome dentro de uma frase de diálogo é conteúdo legítimo, não label."""
        resultado = _limpar("Boa tarde João, obrigada por vir.")
        assert "João" in resultado

    def test_multiplos_falantes_removidos(self):
        transcript = (
            "Entrevistador\n"
            "Fale sobre sua experiência em liderança de times.\n\n"
            "Candidato\n"
            "Liderei equipes por cinco anos entregando resultados excelentes.\n"
        )
        resultado = _limpar(transcript)
        assert "Entrevistador" not in resultado
        assert "Candidato" not in resultado
        assert "Liderei" in resultado

    def test_nome_nao_prefixado_na_sentenca_seguinte(self):
        """Nome do falante não deve aparecer como prefixo na sentença que segue."""
        resultado = _limpar("0:01:20 Maria\nImplementei o sistema de pagamentos do zero.")
        for trecho in resultado.split("."):
            assert not trecho.strip().startswith("Maria")

    def test_transcript_google_meet_nomes_removidos(self):
        """Formato real exportado pelo Google Meet — nomes não devem vazar."""
        transcript = (
            "0:00:03 Entrevistador\n"
            "Boa tarde, pode se apresentar?\n\n"
            "0:00:08 João Silva\n"
            "Claro, sou desenvolvedor sênior com dez anos de experiência."
        )
        resultado = _limpar(transcript)
        assert "Entrevistador" not in resultado
        assert "João Silva" not in resultado
        assert "desenvolvedor sênior" in resultado


class TestFalsosPositivosKeywords:
    """Palavras-chave não devem bater em substrings de outras palavras."""

    def test_forte_nao_bate_em_esforco(self):
        """'forte' como substring de 'esforço' não deve gerar falso positivo."""
        assert _classificar("foi necessário muito esforço para completar a tarefa no prazo") == "neutro"

    def test_forte_nao_bate_em_conforto(self):
        assert _classificar("trabalho com conforto em ambientes de alta pressão") == "neutro"

    def test_forte_nao_bate_em_reforco(self):
        assert _classificar("usamos reforço positivo para motivar a equipe no projeto") == "neutro"

    def test_domina_nao_bate_em_predomina(self):
        """'domina' como substring de 'predomina' não deve gerar falso positivo."""
        assert _classificar("a cultura ágil predomina na empresa onde trabalhei por anos") == "neutro"

    def test_iniciativa_bate_como_palavra_inteira(self):
        """'iniciativa' presente como palavra inteira — deve classificar como forte."""
        assert _classificar("tomei iniciativa no projeto e entreguei antes do prazo") == "forte"

    def test_fraco_nao_bate_em_texto_neutro_sem_keywords(self):
        """Texto sem nenhuma keyword não deve ser classificado como fraco."""
        assert _classificar("a empresa trabalha com atacado e varejo em todo o país") == "neutro"

    def test_nao_tenho_nada_negativo_e_neutro(self):
        """'não tenho nada negativo' cancela o sinal fraco de 'não tenho' → neutro."""
        assert _classificar("A empresa é ótima, não tenho nada negativo a falar.") == "neutro"

    def test_nao_tenho_nada_a_reclamar_e_neutro(self):
        assert _classificar("não tenho nada a reclamar da empresa anterior, foi ótimo") == "neutro"

    def test_nao_tenho_experiencia_ainda_e_fraco(self):
        """'não tenho' sem inversão de contexto continua sendo fraco."""
        assert _classificar("não tenho experiência com Kubernetes ainda") == "fraco"


class TestOutputSemArtefatos:
    """analisar_transcricao não deve retornar artefatos de transcrição no output."""

    def test_speaker_labels_nao_vazam_google_meet(self):
        transcript = (
            "0:00:03 Recrutadora (RH)\n"
            "Me fale sobre seus pontos fortes principais.\n\n"
            "0:00:08 Candidato\n"
            "Tenho liderança técnica sólida e domínio avançado de arquitetura.\n"
            "Desenvolvi sistemas escaláveis com excelente entrega de resultado.\n"
        )
        r = analisar_transcricao(transcript)
        saida = " ".join(r["pontos_fortes"] + r["pontos_fracos"] + [r["anotacoes"]])
        assert "Recrutadora" not in saida
        assert "Candidato" not in saida
        assert "0:00" not in saida

    def test_timestamps_nao_vazam_para_saida(self):
        import re as _re
        transcript = (
            "1:30:45 falei sobre liderança de equipes nos projetos anteriores.\n"
            "2:15 desenvolvi e entregamos sistemas de alta disponibilidade.\n"
        )
        r = analisar_transcricao(transcript)
        saida = " ".join(r["pontos_fortes"] + r["pontos_fracos"] + [r["anotacoes"]])
        assert not _re.search(r'\d+:\d{2}', saida), f"timestamp vazou: {saida!r}"

    def test_anotacoes_e_sentenca_unica_nao_join(self):
        """anotacoes deve ser a melhor sentença neutra, não um join de várias."""
        transcript = """
        Me formei em Ciência da Computação em 2015 e comecei minha carreira em startups.
        Trabalhei em quatro empresas diferentes ao longo de dez anos de carreira.
        Atualmente busco posição de liderança técnica em empresa de produto digital.
        Prefiro ambientes colaborativos onde posso contribuir e crescer profissionalmente.
        Tenho interesse especial em projetos de alto impacto e inovação tecnológica.
        """
        r = analisar_transcricao(transcript)
        # join de 3 frases do exemplo ultrapassaria facilmente 200 chars
        assert len(r["anotacoes"]) <= 201

    def test_anotacoes_respeita_max_len_200(self):
        """Sentença neutra longa deve ser truncada a 200 chars com '…'."""
        palavras = " e ".join([f"item{i}" for i in range(60)])
        long_sent = f"Trabalhei com {palavras} ao longo de toda minha carreira."
        r = analisar_transcricao(long_sent)
        assert len(r["anotacoes"]) <= 201

    def test_html_nao_vaza_para_campos(self):
        transcript = """
        <div>Entrevistador: fale sobre você.</div>
        <p>Tenho liderança técnica e domínio avançado em arquitetura de sistemas.</p>
        <p>Desenvolvi plataformas de pagamento com excelente desempenho e entrega.</p>
        """
        r = analisar_transcricao(transcript)
        saida = " ".join(r["pontos_fortes"] + r["pontos_fracos"] + [r["anotacoes"]])
        assert "<" not in saida
        assert ">" not in saida
