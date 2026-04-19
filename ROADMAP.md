# Roadmap

Este documento descreve as fases planejadas do projeto, com critérios
explícitos de "pronto" para cada uma. A intenção é que cada fase produza
**um entregável independente** — se o projeto parar no meio, o que foi feito
até ali ainda tem valor.

---

## Fase 0 — Provar que o problema existe

**Objetivo:** demonstrar empiricamente que ferramentas atuais de extração
e chunking falham em demonstrações financeiras brasileiras reais.

**Tarefas:**

- [x] Estrutura mínima de projeto Python
- [x] Extrator baseline com `pdfplumber`
- [x] Detectores automáticos de modos de falha (ver `tabelabr/src/failure_modes.py`)
- [x] Rodar em pelo menos 1 documento real (Vale 1T26)
- [ ] Rodar em pelo menos 5 documentos de empresas diferentes
- [ ] Comparar com 1 baseline mais sofisticado (Unstructured ou Docling)
- [ ] Sumarizar achados em relatório consolidado

**Critério de pronto:** existir um relatório curto (markdown) que mostra,
com números, em quantos % das tabelas o baseline falha — e em quais modos.

---

## Fase 1 — Construir o benchmark TabelaBR-50

**Objetivo:** ter um conjunto fechado de **50 perguntas numéricas** sobre
DFs brasileiras, com respostas verificáveis, para servir de avaliação
objetiva ao longo do projeto.

**Tarefas:**

- [ ] Selecionar 5–10 documentos diversos (mineração, banco, varejo, etc.)
- [ ] Para cada documento, escrever 5–10 perguntas reais ("qual a receita
      líquida do 1T26?"), com a resposta correta anotada à mão
- [ ] Validar que as perguntas são respondíveis com base no documento
- [ ] Estruturar tudo em JSON versionado no repo
- [ ] Implementar avaliador automático: roda RAG + LLM, compara resposta
      com gabarito, gera métrica

**Critério de pronto:** rodar `python scripts/02_eval_baseline.py` e obter
um número como "baseline acerta 38/50 perguntas (76%)".

---

## Fase 2 — Atacar o modo de falha dominante

**Objetivo:** propor um algoritmo focado **no problema mais frequente**
descoberto na Fase 0, e mostrar ganho mensurável vs. baseline.

**Hipótese inicial (sujeita a revisão após Fase 0):** o modo de falha
mais danoso é a **perda de contexto** (unidade, cabeçalho, nota) em chunks
de linhas de tabela. A direção de ataque é o "chunk auto-contido": cada
linha vira um chunk independente que carrega seu próprio contexto.

**Tarefas:**

- [ ] Implementar `src/self_contained_chunker.py`
- [ ] Plugar no avaliador da Fase 1
- [ ] Comparar com baseline (Recall@K, accuracy de respostas)
- [ ] Iterar nos casos onde perde

**Critério de pronto:** ganho estatisticamente significativo em pelo menos
um subgrupo de perguntas (ex: perguntas sobre tabelas).

---

## Fase 3 — Avaliação rigorosa

**Objetivo:** comparar o algoritmo proposto com **múltiplas baselines**
em condições controladas.

**Tarefas:**

- [ ] Rodar pipeline completo com:
  - Fixed-size chunking (LangChain)
  - Recursive chunking (LangChain)
  - Semantic chunking (LlamaIndex)
  - Unstructured.io (com partition_pdf)
  - Docling
  - Algoritmo proposto
- [ ] Mesmas perguntas, mesmo retriever, mesmo LLM
- [ ] Reportar com intervalos de confiança (múltiplas seeds quando aplicável)
- [ ] Análise de erro: onde cada método falha?

**Critério de pronto:** tabela de comparação publicável.

---

## Fase 4 — Comunicar

**Objetivo:** transformar o trabalho em algo que outras pessoas possam
ler, usar e criticar.

**Tarefas:**

- [ ] README do repositório no nível "esperado em um repo público maduro"
- [ ] Post técnico (Medium / dev.to / blog próprio) explicando achados
- [ ] Disponibilizar o benchmark como dataset público
- [ ] Considerar: PyPI package? Demo no Hugging Face Spaces?

**Critério de pronto:** alguém de fora consegue rodar tudo seguindo apenas
o README, e entender o que o projeto faz lendo o post.

---

## Princípios que guiam o roadmap

1. **Cada fase entrega valor sozinha.** Se parar na Fase 1, ainda assim
   o benchmark existe.
2. **Sem milestones sem critério de pronto.** "Quase pronto" não conta.
3. **Datas são otimistas — usar critérios, não calendário.** Não vamos
   fingir que dá pra cravar "Fase 2 termina em 4 semanas".
4. **Revisar a hipótese após cada fase.** A Fase 0 pode descobrir que o
   gargalo é outro; a Fase 2 pivota junto.
