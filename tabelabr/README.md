# TabelaBR

Pesquisa sobre extração e chunking de tabelas em demonstrações financeiras
brasileiras (DFs publicadas na CVM/B3) para uso em sistemas RAG.

## Pergunta de pesquisa

> Como construir um pipeline de chunking + retrieval que responda corretamente
> a perguntas numéricas sobre demonstrações financeiras de empresas brasileiras
> listadas?

## Escopo (apertado de propósito)

- **Documentos:** ITR e DFP de empresas listadas na B3 (CVM)
- **Foco:** preservação de tabelas (DRE, Balanço Patrimonial, DFC) durante a
  extração e o chunking
- **Língua:** português brasileiro
- **Métrica de sucesso:** % de respostas numéricas corretas em um benchmark
  próprio (TabelaBR-50)

## Estrutura

```
tabelabr/
  data/raw/           # PDFs originais (não versionados)
  data/processed/     # Saídas de extração
  scripts/            # Scripts de execução (numerados por etapa)
  src/                # Código reutilizável
  reports/            # Relatórios das rodadas (markdown/json)
```

## Fases

- [ ] **Fase 0** — Provar que o problema existe: rodar baselines em DFs reais
      e catalogar onde quebram.
- [ ] **Fase 1** — Construir TabelaBR-50: 50 perguntas numéricas com gabarito.
- [ ] **Fase 2** — Atacar o modo de falha dominante.
- [ ] **Fase 3** — Avaliação rigorosa vs. baselines.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Como rodar a Fase 0

1. Coloque um PDF de DF (ITR ou DFP) em `data/raw/`.
   Exemplo: baixe um ITR recente em https://www.rad.cvm.gov.br/
2. Rode:

```powershell
python scripts\01_baseline_pdfplumber.py data\raw\<seu_arquivo>.pdf
```

3. Veja o relatório gerado em `reports/`.
