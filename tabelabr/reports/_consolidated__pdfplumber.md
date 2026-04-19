# Relatório consolidado — Baseline pdfplumber

- Gerado em: 2026-04-19T10:19:43
- Documentos analisados: **4**

## Headline

- Total de tabelas extraídas: **96**
- Tabelas com pelo menos 1 modo de falha detectado: **87** (90.6%)

## Por documento

| Documento | Tabelas | Com falhas | % |
|---|---:|---:|---:|
| `MGLU_ER_4T25_POR.pdf` | 34 | 27 | 79.4% |
| `Produção e vendas da Vale no 1T26.pdf` | 18 | 18 | 100.0% |
| `Relatório de Produção e Vendas 1T25.pdf` | 19 | 19 | 100.0% |
| `call_4t25_port.pdf` | 25 | 23 | 92.0% |

## Por código de falha (agregado)

| Código | Ocorrências |
|---|---:|
| `MISSING_HEADER` | 74 |
| `TINY_TABLE` | 42 |
| `SPARSE_ROWS` | 28 |
| `MIXED_COLUMN` | 19 |

## Por código de falha (por documento)

| Documento | `MISSING_HEADER` | `MIXED_COLUMN` | `SPARSE_ROWS` | `TINY_TABLE` |
|---|---:|---:|---:|---:|
| `MGLU_ER_4T25_POR.pdf` | 19 | 6 | 8 | 8 |
| `Produção e vendas da Vale no 1T26.pdf` | 18 | 4 | 6 | 3 |
| `Relatório de Produção e Vendas 1T25.pdf` | 19 | 8 | 5 | 11 |
| `call_4t25_port.pdf` | 18 | 1 | 9 | 20 |
