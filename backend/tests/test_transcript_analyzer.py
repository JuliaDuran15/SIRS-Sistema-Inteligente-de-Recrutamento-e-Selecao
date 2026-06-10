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
        sents = _sentencas("Tenho experiência em Python. Trabalhei por cinco anos.")
        assert len(sents) == 2

    def test_divide_por_exclamacao(self):
        # "Ótimo resultado!" tem só 16 chars e é filtrado (< 20); "Entregamos antes do prazo." fica
        sents = _sentencas("Ótimo resultado! Entregamos antes do prazo.")
        assert len(sents) >= 1

    def test_divide_por_paragrafo(self):
        sents = _sentencas("Primeiro parágrafo com conteúdo relevante.\n\nSegundo parágrafo diferente.")
        assert len(sents) == 2

    def test_filtra_sentencas_muito_curtas(self):
        # "Ok." tem menos de 20 chars → deve ser filtrada
        sents = _sentencas("Ok. Tenho bastante experiência em liderança de equipes.")
        assert all(len(s) > 20 for s in sents)

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
        assert len(r["pontos_fortes"]) >= 3
