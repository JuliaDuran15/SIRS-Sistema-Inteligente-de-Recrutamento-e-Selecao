# Como o sistema avalia candidatos

Uma explicação sem jargão técnico.

---

## O que acontece quando um currículo entra no sistema

Quando um candidato envia o currículo, o sistema passa por quatro etapas automáticas antes de exibir qualquer nota:

### 1. Leitura do currículo

O sistema lê o PDF e divide o texto em partes: experiência profissional, habilidades técnicas, formação e resumo. Cada parte é analisada separadamente — assim, a experiência do candidato é comparada com a experiência exigida pela vaga, e não misturada com o restante do texto.

### 2. Nota da vaga (score RH)

Responde à pergunta: **"esse candidato tem o que a vaga pede?"**

- A seção de experiência do CV é comparada diretamente com os requisitos da vaga (peso maior).
- O CV completo também é comparado para capturar o perfil geral (peso menor).
- Além disso, o sistema verifica anos de experiência, nível de senioridade e skills em comum com a vaga — e ajusta a nota para cima ou para baixo (até ±15%).

### 3. Nota de mercado (score mercado)

Responde à pergunta: **"esse candidato tem as skills que o mercado está pedindo para esse tipo de cargo?"**

O sistema busca dados reais de vagas abertas no mercado (via LinkedIn/Kaggle ou API Adzuna) quando a vaga é criada, identifica as habilidades mais exigidas e compara com o perfil do candidato.

Esse score é independente da vaga específica — mede o quanto o candidato está atualizado com as tendências do mercado.

### 4. Nota curricular (score final do currículo)

Combina as duas notas anteriores numa única, de 0 a 100:

```
nota_curriculo = (nota_vaga × peso_rh) + (nota_mercado × peso_mercado)
```

Os pesos padrão são 60% vaga e 40% mercado, mas podem ser ajustados por vaga. Se o analista não quiser levar o mercado em conta, basta zerar o peso de mercado — ele não interfere em nenhuma outra parte do cálculo.

---

## Depois das entrevistas

Quando as entrevistas são registradas, o sistema calcula uma nota consolidada:

```
nota_final = nota_curriculo (50%) + entrevista RH (25%) + entrevista técnica (25%)
```

Os pesos também são configuráveis por vaga.

---

## Reordenar com IA (botão)

O botão "Reordenar (IA)" na tela da vaga aplica um modelo mais preciso sobre os top-20 candidatos. Ao contrário do scoring automático — que compara vetores salvos no banco (rápido, feito uma vez) — esse modelo lê o par vaga + CV junto, como um recrutador leria, e produz uma ordenação mais fina.

É um botão e não automático porque é mais custoso e só faz sentido quando o analista quer uma segunda opinião sobre os finalistas.

---

## O que a nota **não** substitui

As notas são um auxílio para triagem inicial e priorização — não uma decisão final. Um candidato com nota 62 pode ser mais adequado do que um com 78 dependendo de contexto, cultura e cargo. O sistema foi desenhado para reduzir o tempo de triagem, não para substituir o julgamento humano.
