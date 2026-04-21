# Roadmap

Este documento descreve as fases planejadas do projeto, com critérios
explícitos de "pronto" para cada uma. A intenção é que cada fase produza
**um entregável independente** — se o projeto parar no meio, o que foi feito
até ali ainda tem valor.

---

## Fase 0 — Provar que o problema existe ✓ concluída

**Objetivo:** demonstrar empiricamente que ferramentas atuais de extração
e chunking falham em demonstrações financeiras brasileiras reais.

**Tarefas:**

- [x] Estrutura mínima de projeto Python
- [x] Extrator baseline com `pdfplumber`
- [x] Detectores automáticos de modos de falha (`tabelabr/src/failure_modes.py`)
- [x] Rodar em pelo menos 4 documentos de empresas/setores diferentes
- [x] Sumarizar achados em relatório consolidado
- [ ] (futuro, não-bloqueante) Comparar com 1 baseline mais sofisticado
      (Unstructured ou Docling)

**Resultado:** 90.6% de tabelas com pelo menos 1 modo de falha em 96 tabelas
de 4 documentos (Vale 1T26, Vale 1T25, Itaú 4T25, Magalu 4T25). Cada setor
tem um padrão dominante diferente — confirma que solução one-size-fits-all
não funciona. Detalhes em `tabelabr/reports/RESULTS.md` (Fase 0).

---

## Fase 1 — Protótipo do algoritmo e validação experimental ✓ concluída

**Objetivo:** propor um algoritmo de chunking específico para tabelas
financeiras brasileiras e medir seu impacto em precisão de respostas.

**Tarefas:**

- [x] Implementar `src/self_contained_chunker.py` (chunk auto-contido por linha)
- [x] Construir cliente LLM (`src/llm_client.py`, NVIDIA NIM /
      Llama-3.3-70b)
- [x] Definir conjunto de 7 perguntas com gabarito sobre 1 tabela alvo
- [x] Experimento 03: comparar baseline vs. auto-contido com contexto cheio
- [x] Experimento 04: comparar baseline vs. auto-contido sob retrieval parcial
- [x] Documentar resultados (incluindo a refutação da hipótese inicial)

**Resultado:**

| Cenário | Baseline | Auto-contido |
|---|---:|---:|
| Contexto cheio | 85.7% | 85.7% (custa +43% tokens, sem ganho) |
| Retrieval parcial (caso de RAG real) | 0.0% | 85.7% (+85.7 pp, custa +26% tokens) |

A hipótese inicial ("auto-contido sempre ganha") foi refutada. A hipótese
refinada ("auto-contido salva o caso de retrieval mutilado, que é o caso
real") foi confirmada de forma esmagadora. Detalhes em
`tabelabr/reports/RESULTS.md` (Fase 1).

---

## Fase 2 — Generalizar o algoritmo (em andamento)

**Objetivo:** estender o chunker para lidar com as variações de layout
observadas nos 4 documentos da Fase 0 que ele ainda não cobre bem.

**Tarefas:**

- [x] **#1 — Recuperação de cabeçalho via texto da página.** Para
      tabelas em que o `pdfplumber` extrai os dados mas perde a linha
      de header (modo `MISSING_HEADER`, 74 ocorrências no corpus).
      Resultado no DRE do Itaú: precisão sobe de 14.3% para 71.4% sob
      retrieval parcial, com custo de tokens praticamente nulo.
- [x] **#2 — Normalização numérica.** Junta espaços falsos dentro de
      números (`"4 7.560"` → `"47.560"`) e converte sinais contábeis
      (`"(9.397)"` → `"-9.397"`). Resultado no DRE do Itaú em linhas
      sujas: precisão sobe de 57.1% para **100.0%** sobre a Fase 2 #1
      sozinha, com **−2.4% de tokens**.
- [ ] **#3 — Detector "essa tabela vale a pena chunkar?"** Filtro
      anti-`TINY_TABLE` para evitar gerar chunks de cabeçalhos de
      seção, blocos de 1–2 células e artefatos de borda.
- [ ] **#4 — Notas de rodapé referenciadas por superíndice
      (`¹`, `²`)** — hoje ficam órfãs; precisam ser anexadas ao chunk
      do item que as cita.
- [ ] Tabelas com sub-cabeçalhos hierárquicos
      (ex: período-Controladora vs período-Consolidado).
- [ ] Linhas de total/subtotal — devem virar chunks distintos com flag.
- [ ] Tabelas multi-página (cabeçalho repetido na página seguinte).

**Critério de pronto:** o chunker roda sem perder informação em pelo
menos 80% das tabelas dos 4 documentos do corpus inicial.

---

## Fase 3 — Benchmark TabelaBR-50

**Objetivo:** ter um conjunto fechado de **50 perguntas numéricas** sobre
DFs brasileiras, com respostas verificáveis, para servir de avaliação
objetiva ao longo do projeto e (eventualmente) como dataset público.

**Tarefas:**

- [ ] Selecionar 5–10 documentos diversos (já temos 4; faltam 1–6)
- [ ] Para cada documento, escrever 5–10 perguntas reais com gabarito
- [ ] Validar manualmente que as respostas estão corretas
- [ ] Estruturar tudo em JSON versionado (já temos o formato, ver
      `data/processed/vale_1t26_qa.json`)
- [ ] Rodar o avaliador completo sobre as 50 perguntas

**Critério de pronto:** rodar `python scripts/05_eval_full_benchmark.py`
e obter linhas como "baseline acerta X/50; auto-contido acerta Y/50".

---

## Fase 4 — Avaliação rigorosa vs. baselines externos

**Objetivo:** comparar o algoritmo proposto com **múltiplas baselines**
da indústria em condições controladas.

**Tarefas:**

- [ ] Rodar pipeline completo com:
  - Fixed-size chunking (LangChain `CharacterTextSplitter`)
  - Recursive chunking (LangChain `RecursiveCharacterTextSplitter`)
  - Semantic chunking (LlamaIndex `SemanticSplitterNodeParser`)
  - Unstructured.io (`partition_pdf` com hi_res)
  - Docling
  - Algoritmo proposto
- [ ] Mesmas perguntas, mesmo retriever, mesmo LLM
- [ ] Reportar com intervalos de confiança (múltiplas seeds quando aplicável)
- [ ] Análise de erro qualitativa: onde cada método falha?

**Critério de pronto:** tabela de comparação publicável.

---

## Fase 5 — Comunicar

**Objetivo:** transformar o trabalho em algo que outras pessoas possam
ler, usar e criticar.

**Tarefas:**

- [ ] README no nível "esperado em um repo público maduro"
- [ ] Post técnico explicando achados
- [ ] Disponibilizar o benchmark TabelaBR-50 como dataset público
- [ ] Considerar: pacote PyPI? Demo no Hugging Face Spaces?

**Critério de pronto:** alguém de fora consegue rodar tudo seguindo
apenas o README e entender o que o projeto faz lendo o post.

---

## Princípios que guiam o roadmap

1. **Cada fase entrega valor sozinha.** Se parar na Fase 3, ainda assim
   o benchmark existe.
2. **Sem milestone sem critério de pronto.** "Quase pronto" não conta.
3. **Datas são otimistas — usar critérios, não calendário.**
4. **Revisar a hipótese após cada fase.** Aconteceu na Fase 1: a
   hipótese inicial caiu, a refinada subiu, e o algoritmo ficou mais
   defensável por causa disso.
