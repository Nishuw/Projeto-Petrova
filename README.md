# Projeto Petrova

Projeto de **pesquisa em algoritmos de chunking** para sistemas RAG
(Retrieval-Augmented Generation), com foco em **tabelas de relatórios
financeiros e operacionais de empresas brasileiras listadas**.

> O nome é só um codinome de trabalho. O foco é técnico.

---

## Tese

Sistemas RAG comuns quebram documentos em pedaços (*chunks*) usando
estratégias genéricas (tamanho fixo, fim de sentença, recursão por
separadores). Quando o documento contém **tabelas**, essas estratégias
destroem o contexto estrutural — título da tabela, unidade de medida,
cabeçalhos de coluna — e o pedaço recuperado pelo retriever vira uma
sequência de números sem significado para o LLM.

A tese que este repositório investiga, em uma frase:

> **Reformular cada linha de uma tabela em um chunk auto-suficiente
> (carregando título + unidade + cabeçalho de coluna em cada chunk)
> elimina o colapso de precisão que ocorre em RAGs reais quando o
> retriever entrega só uma parte da tabela.**

Esta é uma tese **empírica**: o repositório existe para testá-la com
dados reais (releases CVM/B3 de Vale, Itaú, Magalu) e medir custo
(tokens) versus benefício (precisão de resposta).

## Resultado central até agora

Em uma tabela alvo da Vale (1T26, "Resumo da produção"), com 7
perguntas de gabarito e Llama-3.3-70b como avaliador:

| Cenário | Baseline (tabela bruta) | Auto-contido | Δ acurácia | Δ tokens |
|---|---:|---:|---:|---:|
| Contexto completo (LLM recebe tabela inteira) | 85.7% | 85.7% | 0 pp | +43% |
| Retrieval parcial (LLM recebe só o chunk relevante) | **0.0%** | **85.7%** | **+85.7 pp** | +26% |

Resultados completos, com método e dados crus, em
[`tabelabr/reports/RESULTS.md`](./tabelabr/reports/RESULTS.md).

---

## Estrutura do repositório

```
.
├── README.md                       Este arquivo (visão geral)
├── ROADMAP.md                      Fases do projeto e checkpoints
├── LICENSE                         Licença MIT
├── O problema nao resolvido.md     Notas iniciais (rascunho de pesquisa)
└── tabelabr/                       Código e dados do estudo
    ├── README.md                   Guia de uso do código
    ├── requirements.txt
    ├── data/                       PDFs originais e saídas processadas
    ├── reports/                    Relatórios gerados pelos scripts
    ├── scripts/                    Scripts numerados (01_, 02_, ...)
    └── src/                        Módulos reutilizáveis
```

---

## Estado atual

| Fase | Descrição | Status |
|------|-----------|--------|
| 0 | Provar que o problema existe (rodar baselines em DF reais) | concluída — 90.6% das tabelas com falha em 4 docs |
| 1 | Protótipo do algoritmo (chunk auto-contido) e validação experimental | concluída — tese refinada confirmada |
| 2 | Generalizar o algoritmo para variações de layout (sub-cabeçalhos, notas) | em andamento |
| 3 | Benchmark TabelaBR-50 (50 perguntas com gabarito em ≥ 5 documentos) | pendente |
| 4 | Avaliação rigorosa vs. Unstructured.io e Docling | pendente |
| 5 | Documentação, post técnico, repositório público maduro | pendente |

Detalhes em [`ROADMAP.md`](./ROADMAP.md).

---

## Como começar

```powershell
# 1. Clone o repositório
git clone https://github.com/Nishuw/Projeto-Petrova.git
cd Projeto-Petrova

# 2. Setup do ambiente Python (3.11+)
cd tabelabr
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure a chave da NVIDIA Build (https://build.nvidia.com/)
copy .env.example .env
# edite .env e cole sua NVIDIA_API_KEY

# 4. Rode o baseline em todos os PDFs de data/raw/
python scripts\02_baseline_batch.py

# 5. Reproduza os experimentos do algoritmo
python scripts\03_eval_chunkers.py            # cenário com contexto cheio
python scripts\04_eval_partial_retrieval.py   # cenário de retrieval parcial
```

Os relatórios saem em `tabelabr/reports/`.

---

## Princípios de trabalho

- **Escopo apertado vence escopo amplo.** Resolver uma dor específica de um
  usuário específico em um documento específico vale mais do que uma proposta
  genérica que tenta cobrir tudo.
- **Evidência antes de algoritmo.** Antes de propor uma solução, mostrar com
  dados reais que o problema existe.
- **Métrica verificável por terceiro.** Não "qualidade do chunk"; sim
  "número correto na resposta final".
- **Cada etapa entrega valor.** O benchmark sozinho já é entregável; a análise
  de falhas sozinha já é entregável; o algoritmo é um bônus em cima disso.

---

## Licença

[MIT](./LICENSE).
