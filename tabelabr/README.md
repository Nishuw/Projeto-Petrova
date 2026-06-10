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
├── .env.example             Template para a chave da NVIDIA Build
├── data/
│   ├── raw/                 PDFs originais (não versionados)
│   └── processed/           Conjuntos de pergunta+gabarito (versionados)
├── reports/                 Relatórios gerados pelos scripts
│   ├── RESULTS.md           Síntese narrativa dos experimentos
│   └── ...                  Saídas brutas (markdown e JSON) de cada run
├── scripts/                 Pontos de entrada, numerados por ordem
│   ├── 01_baseline_pdfplumber.py            Baseline em 1 PDF
│   ├── 02_baseline_batch.py                 Baseline em todos os PDFs de data/raw/
│   ├── 03_eval_chunkers.py                  Experimento: contexto cheio (Vale)
│   ├── 04_eval_partial_retrieval.py         Experimento: retrieval parcial (Vale)
│   ├── 05_eval_partial_retrieval_itau.py    Fase 2 #1: recuperação de cabeçalho (Itaú)
│   └── 06_eval_normalization_itau.py        Fase 2 #2: normalização numérica (Itaú)
└── src/                     Módulos reutilizáveis
    ├── failure_modes.py            Detectores de modos de falha
    ├── self_contained_chunker.py   O algoritmo proposto
    └── llm_client.py               Cliente LLM (NVIDIA NIM)
```

---

## Setup

Pré-requisitos: **Python 3.11+** e uma chave de API da
[NVIDIA Build](https://build.nvidia.com/) (gratuita).

```powershell
# A partir da raiz do repositório
cd tabelabr
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# edite .env e cole sua NVIDIA_API_KEY
```

No Linux / macOS:

```bash
cd tabelabr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edite .env e cole sua NVIDIA_API_KEY
```

> O arquivo `.env` está no `.gitignore`. **Nunca commit chaves de API.**

---

## Uso

### 1. Coloque PDFs de DFs reais em `data/raw/`

Os PDFs **não são versionados** — baixe-os das fontes públicas:

- Vale: <https://vale.com/pt/investidores>
- Itaú: <https://www.itau.com.br/relacoes-com-investidores/release-de-resultados>
- CVM: <https://www.rad.cvm.gov.br/>

Os experimentos (scripts 03–06) esperam estes nomes exatos em `data/raw/`:

| Arquivo | Documento | Usado por |
|---|---|---|
| `Produção e vendas da Vale no 1T26.pdf` | Vale, release 1T26 | scripts 03 e 04 |
| `call_4t25_port.pdf` | Itaú, release 4T25 | scripts 05 e 06 |
| `Relatório de Produção e Vendas 1T25.pdf` | Vale, release 1T25 | Fase 0 (script 02) |
| `MGLU_ER_4T25_POR.pdf` | Magalu, release 4T25 | Fase 0 (script 02) |

### 2. Diagnóstico do problema (Fase 0)

```powershell
python scripts\02_baseline_batch.py
```

Roda o `pdfplumber` em todos os PDFs de `data/raw/`, classifica as
tabelas por modo de falha e gera `reports/_consolidated__pdfplumber.md`.

### 3. Reproduzir os experimentos do algoritmo (Fases 1 e 2)

```powershell
python scripts\03_eval_chunkers.py                 # Fase 1: contexto cheio (Vale)
python scripts\04_eval_partial_retrieval.py        # Fase 1: retrieval parcial (Vale)
python scripts\05_eval_partial_retrieval_itau.py   # Fase 2 #1: recuperação de cabeçalho (Itaú)
python scripts\06_eval_normalization_itau.py       # Fase 2 #2: normalização numérica (Itaú)
```

A leitura completa dos resultados está em
[`reports/RESULTS.md`](./reports/RESULTS.md).

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
| 07 | `07_baseline_unstructured.py` | Diagnóstico usando Unstructured.io para comparar com `pdfplumber` |
| 08 | `08_build_tabelabr50.py` | Consolida o benchmark TabelaBR-50 (50 perguntas em ≥5 documentos) |
| 09 | `09_eval_full_benchmark.py` | Roda baseline vs. auto-contido em todo o benchmark |

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
