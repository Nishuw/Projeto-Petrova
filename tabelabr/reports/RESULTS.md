# Resultados experimentais — algoritmo de chunking auto-contido

Documento vivo. Cada seção corresponde a uma fase de experimentação,
com hipótese, método, dados crus e a leitura honesta do resultado
(inclusive quando ele refuta a hipótese inicial).

---

## Fase 0 — A dor existe?

**Pergunta:** o problema de extração de tabelas em DFs brasileiras é
real e mensurável, ou é uma percepção sem evidência?

**Método:** rodar o `pdfplumber` (parser de tabelas open-source mais
popular em Python) em quatro releases trimestrais reais e classificar
cada tabela extraída segundo cinco modos de falha pré-definidos
(`MISSING_HEADER`, `TINY_TABLE`, `MIXED_COLUMN`, `SPARSE_ROWS`,
`UNIT_AMBIGUITY`). Os detectores estão em `src/failure_modes.py`.

**Corpus (4 documentos, 96 tabelas):**

| Documento | Setor | Tabelas | Com falhas | % falhas |
|---|---|---:|---:|---:|
| `Produção e vendas da Vale no 1T26.pdf` | Mineração | 18 | 18 | 100.0% |
| `Relatório de Produção e Vendas 1T25.pdf` | Mineração | 19 | 19 | 100.0% |
| `call_4t25_port.pdf` (Itaú) | Bancos | 25 | 23 | 92.0% |
| `MGLU_ER_4T25_POR.pdf` (Magalu) | Varejo | 34 | 27 | 79.4% |
| **TOTAL** | — | **96** | **87** | **90.6%** |

**Modos de falha agregados:**

| Código | Ocorrências |
|---|---:|
| `MISSING_HEADER` | 74 |
| `TINY_TABLE` | 42 |
| `SPARSE_ROWS` | 28 |
| `MIXED_COLUMN` | 19 |

**Leitura:**
- O problema é generalizado (90.6% das tabelas) e atravessa setores.
- Cada setor tem um padrão dominante: Itaú estoura em `TINY_TABLE`
  (releases densos com muitos pseudo-blocos), Vale 1T25 em
  `MIXED_COLUMN` (layout antigo), Magalu é o "menos pior" porque
  seu vocabulário casa bem com os detectores.
- Conclusão: **uma solução one-size-fits-all não resolve.** O
  algoritmo precisa adaptar-se ao perfil do documento.

Reproduzir: `python scripts/02_baseline_batch.py`. Saída em
`reports/_consolidated__pdfplumber.md`.

---

## Fase 1, experimento 03 — chunk auto-contido sob contexto cheio

**Hipótese inicial (forte):** transformar uma tabela em chunks
auto-contidos (um por linha de dados, cada um carregando título,
unidade e cabeçalhos de coluna) **sempre** melhora a precisão de um
LLM ao responder perguntas sobre os dados.

**Método:** uma tabela alvo (Vale 1T26, página 1, "Resumo da
produção"), 7 perguntas com gabarito (`data/processed/vale_1t26_qa.json`)
e duas estratégias de chunking. Em ambas, o LLM (Llama-3.3-70b via
NVIDIA NIM, `temperature=0`) recebe TODO o contexto (a tabela inteira)
junto com a pergunta. O matcher é tolerante a vírgula/ponto, espaços
e símbolos.

**Resultado:**

| Estratégia | Acertos | Precisão | Tokens |
|---|---:|---:|---:|
| Baseline (tabela inteira renderizada) | 6/7 | 85.7% | 2371 |
| Auto-contido (linhas separadas, cada uma com contexto) | 6/7 | 85.7% | 3386 (+43%) |

**Leitura honesta:**
- A hipótese inicial **foi refutada nesse cenário.** Quando o LLM
  recebe a tabela inteira, o baseline já é ótimo — o auto-contido só
  adiciona tokens redundantes (repete título e unidade em todo chunk).
- A única pergunta que ambos erraram (q7, comparação 4T25 vs 1T26 de
  pelotas) é um erro de RACIOCÍNIO do modelo, não de chunking — não
  conta como falha do método.
- **Esse resultado é importante:** evita a tentação de embarcar em
  um algoritmo elaborado sem provar que ele agrega.

Reproduzir: `python scripts/03_eval_chunkers.py`. Saída em
`reports/eval_chunkers__vale_1t26.json`.

---

## Fase 1, experimento 04 — chunk auto-contido sob retrieval parcial

**Hipótese refinada (após o experimento 03):** o ganho do chunk
auto-contido aparece **somente** quando o retriever de um RAG real
entrega ao LLM apenas um pedaço da tabela — cenário em que o
contexto implícito (título, cabeçalhos) some no baseline e
sobrevive no auto-contido.

**Método:** mesma tabela, mesmas 7 perguntas. Para cada pergunta,
simulamos o retriever entregando ao LLM **apenas** a(s) linha(s)
relevante(s). No baseline isso significa uma string como
`"Pelotas | 8.169 | 7.183 | 13,7 % | 8.325 | -1,9 % | —"` — sem
título, sem unidade, sem nome de coluna. No auto-contido significa
o chunk correspondente, que por construção carrega tudo.

**Resultado:**

| Estratégia | Acertos | Precisão | Tokens |
|---|---:|---:|---:|
| Baseline (linha solta sem cabeçalho) | **0/7** | **0.0%** | 1308 |
| Auto-contido (chunk com contexto) | **6/7** | **85.7%** | 1651 (+26%) |

Detalhe pergunta a pergunta:

| ID | Pergunta (resumo) | Resp. baseline | OK? | Resp. auto-contido | OK? |
|---|---|---|:-:|---|:-:|
| q1 | minério ferro 1T26 | "Não consta" | ✗ | "69.675" | ✓ |
| q2 | var. a/a pelotas | "-1,9 %" (errou coluna) | ✗ | "13,7%" | ✓ |
| q3 | cobre 4T25 | "não consta" | ✗ | "108,1" | ✓ |
| q4 | var. t/t níquel | "12,3 %" (errou coluna) | ✗ | "6,7%" | ✓ |
| q5 | unidade do minério | "Não consta" | ✗ | "Mil toneladas métricas" | ✓ |
| q6 | título da tabela | "Minério de ferro" (confundiu nome do item) | ✗ | "Resumo da produção" | ✓ |
| q7 | pelotas 4T25 vs 1T26 | "menor" | ✗ | "menor" | ✗ |

**Leitura:**
- Δ = **+85.7 pontos percentuais** de precisão.
- Custo: +26% em tokens (de 1308 para 1651).
- O baseline não apenas falha em "não consta" — em vários casos
  ele **chuta a coluna errada** (q2, q4) ou **confunde o nome do
  item com o título** (q6). Esses erros são piores que omissão
  porque o usuário recebe um número plausível-mas-errado.
- O único erro persistente do auto-contido (q7) é o mesmo erro do
  experimento 03: erro de raciocínio do modelo, não do chunking.
- A hipótese refinada se confirma: **o chunk auto-contido é
  uma ferramenta para o cenário em que o RAG precisa quebrar o
  contexto, não para o cenário ideal.**

Reproduzir: `python scripts/04_eval_partial_retrieval.py`. Saída em
`reports/eval_partial_retrieval__vale_1t26.json`.

---

## Síntese e tese atual

Combinando 03 + 04, o algoritmo de **chunking auto-contido**:

1. Não prejudica o caso em que o LLM já recebe contexto completo
   (empata em precisão, custa +43% tokens nesse cenário).
2. Salva o caso em que o retriever entrega contexto mutilado
   (vai de 0.0% para 85.7% de precisão, custa +26% tokens).

Como em RAG real o cenário (2) é a regra e (1) é a exceção, a tese
fica: **vale a pena pagar +26% em tokens de armazenamento/embedding
para evitar quedas catastróficas de precisão sob retrieval parcial.**

---

## Fase 2, item #1 — recuperação de cabeçalho via texto da página

**Motivação:** a recon em uma tabela real do Itaú (DRE gerencial,
`call_4t25_port.pdf` pág. 21) mostrou que o `pdfplumber.extract_tables()`
frequentemente **devolve a tabela sem a linha de cabeçalho**. Ela
existe no PDF, aparece no `page.extract_text()` puro
(`"Em R$ milhões 4T25 3T25 ' 4T24 ' 2025 2024 '"`) mas não é
reconhecida como linha da tabela estruturada. Sem isso o chunker
auto-contido produz `"Coluna 1: 30.930"` em vez de `"4T25: 30.930"`,
o que destrói praticamente toda a proposta de valor dele em tabelas
grandes.

Esse é o modo de falha `MISSING_HEADER` da Fase 0 — **74 de 96 tabelas
do corpus** sofrem dele.

**Método:** um segundo caso de teste (`data/processed/itau_4t25_qa.json`,
7 perguntas sobre o DRE do Itaú, deliberadamente em linhas onde a
extração numérica saiu limpa — para isolar o efeito do cabeçalho).
Três estratégias sob retrieval parcial:

1. Baseline (linha solta, como antes).
2. Auto-contido SEM recuperação de cabeçalho — comportamento da Fase 1.
3. Auto-contido COM recuperação — nova função
   `recover_header_from_page_text` que busca no texto da página a
   linha candidata (maior pontuação em tokens de período/∆) e
   tokeniza. Inclui tratamento do artefato `\uf044` que o pdfplumber
   devolve no lugar do `∆` em PDFs com fontes customizadas.

**Resultado:**

| Estratégia | Acertos | Precisão | Tokens |
|---|---:|---:|---:|
| Baseline | 0/7 | 0.0% | 1381 |
| Auto-contido SEM recuperação | 1/7 | 14.3% | 1663 |
| **Auto-contido COM recuperação (Fase 2 #1)** | **5/7** | **71.4%** | **1642** |

Detalhe pergunta a pergunta:

| ID | Pergunta (resumo) | Sem recuperação | Com recuperação |
|---|---|---|---|
| q1 | MFC 4T25 → 30.930 | "28.484" (chutou coluna errada) ✗ | "30.930" ✓ |
| q2 | MFC 2025 → 121.128 | "não consta" ✗ | "121.128" ✓ |
| q3 | MFM 3T25 → 902 | "904" (coluna errada) ✗ | "902" ✓ |
| q4 | MFM var a/a 2025 → -25,8% | "não consta" ✗ | "-25,8%" ✓ |
| q5 | MFM 4T24 → 904 | "904" ✓ (acaso) | "904" ✓ |
| q6 | unidade → "R$ milhões" | "Reais" ✗ | "Reais" ✗ |
| q7 | título → "Resultados" | "Margem Financeira" ✗ | "Margem Financeira" ✗ |

**Leitura:**
- Δ = **+57 pontos percentuais** (14.3% → 71.4%) mantendo retrieval parcial.
- Custo: **praticamente zero** (de 1663 para 1642 tokens — até ficou
  um pouco menor, porque "4T25" é mais curto que "Coluna 1").
- Os 2 erros remanescentes NÃO são falha da recuperação de cabeçalho:
  - q6: o LLM respondeu "Reais" (omitiu "milhões"). Falha de instrução
    ou de matcher, não de chunking.
  - q7: o LLM confundiu `Tabela: Resultados` com `Item: Margem
    Financeira...`. Sinaliza que o rótulo "Tabela:" no template do
    chunk é ambíguo — vai ser ajustado em iteração posterior (trocar
    "Tabela:" por "Título da tabela:" ou similar).
- Os ganhos dos itens q1–q4 são **puramente atribuíveis à recuperação
  do cabeçalho** — sem ele, o LLM ou dizia "não consta" ou chutava uma
  coluna adjacente, o que é pior (número errado parecendo certo).

Reproduzir: `python scripts/05_eval_partial_retrieval_itau.py`. Saída
em `reports/eval_partial_retrieval__itau_4t25.json`.

---

## Fase 2, item #2 — normalização numérica

**Motivação:** mesmo com o cabeçalho recuperado (item #1), as linhas
em que o `pdfplumber` quebrou o número continuavam respondendo errado.
Duas patologias específicas dominam o Itaú:

1. **Espaços falsos dentro do número.** Quando o layout aperta uma
   coluna, o parser insere um espaço entre o primeiro dígito e o
   resto: `"47.560"` vira `"4 7.560"`, `"184.393"` vira `"1 84.393"`,
   `"5.167"` vira `"5 .167"`. O LLM não sabe se deve pegar o primeiro
   token, o segundo, ou concatenar — em geral chuta o segundo (o
   "mais bonito") e responde errado.
2. **Sinais contábeis em parênteses.** Despesas e custos em DFs vêm
   como `"(9.397)"` em vez de `"-9.397"`. Convenção padrão do
   mercado, mas confunde matchers automáticos.

**Método:** novo caso de teste
(`data/processed/itau_4t25_dirty_qa.json`, 7 perguntas em linhas
SUJAS — 4 com espaço falso, 3 com parênteses) e três cenários sob
retrieval parcial. A normalização é controlada por flag
`normalize_numbers` em `render_self_contained_chunks`, então dá pra
medir o efeito ISOLADO sobre o estado da arte da Fase 2 #1.

**Resultado:**

| Estratégia | Acertos | Precisão | Tokens |
|---|---:|---:|---:|
| Baseline (linha solta, sem header) | 1/7 | 14.3% | 1476 |
| Auto-contido — só Fase 2 #1 | 4/7 | 57.1% | 1744 |
| **Auto-contido — Fase 2 #1 + #2** | **7/7** | **100.0%** | **1702** |

Detalhe pergunta a pergunta:

| ID | Patologia | Resp. só #1 | Resp. #1 + #2 |
|---|---|---|---|
| q1_produto_bancario_4t25 → 47.560 | espaço falso `"4 7.560"` | "4.560" ✗ | "47.560" ✓ |
| q2_produto_bancario_2025 → 184.393 | espaço falso `"1 84.393"` | "84.393" ✗ | "184.393" ✓ |
| q3_mfg_2024 → 112.445 | espaço falso `"1 12.445"` | "12.445" ✗ | "112.445" ✓ |
| q4_rps_4t24 → 11.697 | espaço falso `"1 1.697"` | "11.697" ✓ | "11.697" ✓ |
| q5_custo_credito_4t25 → 9.397 | parênteses `"(9.397)"` | "9.397" ✓ | "9.397" ✓ |
| q6_custo_credito_2024 → 34.493 | parênteses `"( 34.493)"` | "34.493" ✓ | "34.493" ✓ |
| q7_despesas_tributarias_4t25 → 2.619 | parênteses `"( 2.619)"` | "2.619" ✓ | "2.619" ✓ |

**Leitura:**
- Δ marginal de #2 sobre #1: **+42.9 pontos percentuais** (57.1% → 100%).
- Custo: **−2.4% em tokens** — converter `"( 34.493)"` em `"-34.493"`
  é, literalmente, 4 caracteres a menos. A normalização é
  praticamente "grátis".
- **Insight não-trivial:** as 3 perguntas de parênteses (q5, q6, q7)
  já passavam SEM normalização. O Llama-3.3-70b reconhece a convenção
  contábil e reporta o número limpo mesmo recebendo `"(9.397)"`. Em
  outras palavras: para LLMs frontier o sinal contábil é menos
  perigoso do que parece. **A patologia que realmente derruba o
  pipeline é o espaço falso dentro do número** — onde sem
  normalização o modelo não tem como adivinhar o token certo.
- Os 3 acertos novos atribuíveis a #2 (q1, q2, q3) compõem 100% do
  ganho desta fase — isolamento experimental limpo.

Reproduzir: `python scripts/06_eval_normalization_itau.py`. Saída em
`reports/eval_normalization__itau_4t25.json`.

---

## Próximos passos planejados

1. **Fase 2 #3:** detector automático "vale chunkar?" — filtro
   anti-`TINY_TABLE` para evitar poluir o vector store com
   pseudo-tabelas (cabeçalhos de seção, blocos com 1–2 células,
   artefatos de borda).
2. **Fase 2 #4:** anexar notas de rodapé ao chunk do item que as
   referencia (`Receitas de Operações de Seguros¹` → o chunk dela
   também traz a nota ¹).
3. Ajuste fino do template do chunk (trocar "Tabela:" por
   "Título da tabela:" para resolver o q7 do Itaú original; repetir
   o ∆ com sufixo explícito "∆ t/t" quando puder inferir).
4. Generalizar para tabelas com sub-cabeçalhos hierárquicos
   (Controladora × Consolidado).
5. Replicar em Magalu e Vale 1T25 para ter 4 casos de teste.
6. Comparar contra `Unstructured.io` e `Docling` em vez de só
   `pdfplumber` baseline.
