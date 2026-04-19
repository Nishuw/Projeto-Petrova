# TabelaBR

Estudo experimental sobre **extração e chunking de tabelas em demonstrações
financeiras brasileiras** (DRE, Balanço Patrimonial, DFC, releases de
resultados publicados na CVM/B3).

Esse diretório contém todo o código, dados de saída e relatórios da pesquisa.
A motivação geral está no [README do repositório](../README.md) e o plano
em [`../ROADMAP.md`](../ROADMAP.md).

---

## Pergunta de pesquisa

> Como construir um pipeline de chunking + retrieval que responda
> corretamente a perguntas numéricas sobre demonstrações financeiras
> de empresas brasileiras listadas?

Escolha consciente: o escopo é estreito de propósito. Tabelas em PT-BR,
formato CVM/B3, perguntas com resposta numérica verificável.

---

## Estrutura

```
tabelabr/
├── README.md                Este arquivo
├── requirements.txt         Dependências Python
├── data/
│   ├── raw/                 PDFs originais (NÃO versionados — gitignorados)
│   └── processed/           Saídas intermediárias
├── reports/                 Relatórios gerados pelos scripts
├── scripts/                 Pontos de entrada numerados por etapa
│   └── 01_baseline_pdfplumber.py
└── src/                     Módulos reutilizáveis
    ├── __init__.py
    └── failure_modes.py     Detectores automáticos de problemas em tabelas
```

---

## Setup

Pré-requisitos: **Python 3.11+**.

```powershell
# A partir da raiz do repositório
cd tabelabr
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No Linux / macOS:

```bash
cd tabelabr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Uso

### 1. Coloque um PDF de demonstração financeira em `data/raw/`

Sugestões de fonte (todas públicas):

- Releases de resultados da Vale: <https://vale.com/pt/investidores>
- Releases do Itaú: <https://www.itau.com.br/relacoes-com-investidores/release-de-resultados>
- ITR/DFP oficiais na CVM: <https://www.rad.cvm.gov.br/>

### 2. Rode o baseline

```powershell
python scripts\01_baseline_pdfplumber.py "data\raw\<nome_do_arquivo>.pdf"
```

### 3. Veja a saída

- Sumário no terminal (tabela rica com falhas por tipo)
- Relatório markdown legível em `reports/<arquivo>__pdfplumber.md`
- Dump JSON com tudo em `reports/<arquivo>__pdfplumber.json`

---

## O que o baseline faz hoje

1. Abre o PDF com `pdfplumber` (parâmetros default — intencional, queremos
   ver o que a ferramenta entrega "fora da caixa").
2. Extrai todas as tabelas página a página.
3. Roda os detectores em `src/failure_modes.py` em cada tabela:
   - `EMPTY_TABLE` / `TINY_TABLE` — fragmento ou tabela vazia
   - `MISSING_HEADER` — sem cabeçalho típico de DF brasileira (sinal de
     quebra entre páginas ou de falso positivo: parágrafo virou "tabela")
   - `MIXED_COLUMN` — coluna com mistura suspeita de texto e números
   - `SPARSE_ROWS` — densidade de células baixa demais
   - `UNIT_AMBIGUITY` — números grandes sem indicação de unidade no chunk
4. Gera relatório markdown com os 20 piores casos para inspeção manual.

Os detectores são **calibrados para o domínio** (DF brasileira em
português). Eles não pretendem ser genéricos — pretendem ser um sinal
honesto de problemas em quem é o usuário-alvo do projeto.

---

## Próximos scripts (planejados)

| # | Nome | O que faz |
|---|------|-----------|
| 02 | `02_baseline_unstructured.py` | Mesma análise usando Unstructured.io |
| 03 | `03_build_benchmark.py` | Constrói TabelaBR-50 a partir dos PDFs |
| 04 | `04_eval_chunkers.py` | Avalia chunkers no benchmark |
| 05 | `05_self_contained_chunker.py` | Implementação do chunker proposto |

---

## Convenções

- Scripts em `scripts/` são **numerados por ordem de execução** e devem ser
  rodáveis a partir do diretório `tabelabr/` (eles ajustam o `sys.path`
  internamente para enxergar `src/`).
- Tudo em `src/` é **importável** e testável isoladamente.
- Relatórios em `reports/` são **versionados** (são pequenos e contam a
  história do projeto). Já os PDFs em `data/raw/` **não** são versionados.
- Comentários no código em português; docstrings também.

---

## Limitações conhecidas

- `pdfplumber` em PDFs digitalizados (scanned) não funciona — vai precisar
  de OCR antes (planejado para fase posterior).
- Os detectores são heurísticos, não classificadores treinados. Tendem a
  ter falsos positivos em documentos fora do domínio.
- O baseline atual não trata multi-página: se uma tabela atravessa páginas,
  hoje aparece como duas tabelas separadas (esse é justamente um dos
  problemas que o algoritmo final pretende atacar).
