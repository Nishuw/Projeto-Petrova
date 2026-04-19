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

## Próximos passos planejados

1. Generalizar o chunker para tabelas com sub-cabeçalhos de coluna
   (período-Controladora vs período-Consolidado, comum em DFs).
2. Tratar notas de rodapé (`¹`, `²`) — hoje ficam órfãs no chunk.
3. Replicar os experimentos em tabelas do Itaú e Magalu (setores
   diferentes, estruturas diferentes).
4. Medir custo de embedding adicional, não só de inferência.
5. Comparar contra `Unstructured.io` e `Docling` em vez de só
   `pdfplumber` baseline.
