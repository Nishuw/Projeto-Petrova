# Relatório de baseline — `Produção e vendas da Vale no 1T26.pdf`

- Gerado em: 2026-04-19T00:49:23
- Extrator: `pdfplumber.extract_tables()` (parâmetros default)

## Sumário

- Tabelas extraídas: **18**
- Tabelas com pelo menos 1 modo de falha detectado: **18** (100.0%)

### Falhas por tipo

| Código | Ocorrências |
|---|---|
| `MISSING_HEADER` | 18 |
| `SPARSE_ROWS` | 6 |
| `MIXED_COLUMN` | 4 |
| `TINY_TABLE` | 3 |

## Tabelas com falhas (top 20)

### Pág. 1 — tabela #0 (5×3)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` • O desempenho da Vale no 1º trimestre foi marcado por mais um trimestre de forte produção e vendas, com múltiplos ativos
atingindo seus maiores níveis de produção. No minério de ferro, o ramp-up de `
- **[medium] SPARSE_ROWS**: 3/5 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | • O desempenho da Vale no 1º trimestre foi marcado por mais um trimestre de forte produção e vendas, com múltiplos ativos
atingindo seus maiores níveis de produção. No minério de ferro, o ramp-up de novos ativos sustentou o crescimento
consistente da produção, enquanto as vendas alcançaram o maior nível para um primeiro trimestre desde 2018. Em cobre e
níquel, a produção atingiu crescimento de dois dígitos, com o cobre atingindo sua melhor produção de primeiro trimestre desde
2017 e o níquel desde 2020. | ·
· | · | ·
· | • A produção de minério de ferro totalizou 69,7 Mt , 3% (2,0 Mt) maior a/a, suportado pelo recorde de produção em S11D e Brucutu,
bem como pelo contínuo ramp-up dos projetos Capanema e VGR1. A produção de pelotas alcançou 8,2 Mt, aumentando 14% (1,0 Mt)
a/a, devido o melhor desempenho das plantas de pelotização de Tubarão. As vendas de minério de ferro aumentaram 4% (2,6 Mt) a/a,
totalizando 68,7 Mt, em linha com o maior volume de produção.
• A produção de cobre totalizou 102,3 kt, 13% (11,4 kt) maior a/a, impulsionado pela produção recorde em Salobo e Sossego, assim como o
desempenho sólido das minas polimetálicas de Voisey’s Bay.
• A produção de níquel totalizou 49,3 kt, 12% (5,4 kt) maior a/a, refletindo a operação do 2º forno de Onça Puma durante todo o
trimestre e a estabilidade operacional das minas subterrâneas de Voisey’s Bay, que sustentaram um recorde de produção no primeiro
trimestre na refinaria de Long Harbour. | ·
· | · | ·
· | · | ·
```

### Pág. 1 — tabela #1 (6×8)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` Resumo da produção       |  Mil toneladas métricas 1T26 1T25 ∆ a/a 4T25 ∆ t/t Guidance 2026 |  Minério de ferro¹ 69.675 67.669 ² 3,0 % 90.403 -22,9 % `
- **[medium] MIXED_COLUMN**: Coluna 3 mistura 60% numérico com 40% texto (possível colunas mescladas)

Preview (5 primeiras linhas):

```
· | Resumo da produção | · | · | · | · | · | ·
· | Mil toneladas métricas | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t | Guidance 2026
· | Minério de ferro¹ | 69.675 | 67.669 ² | 3,0 % | 90.403 | -22,9 % | ·
· | Pelotas | 8.169 | 7.183 | 13,7 % | 8.325 | -1,9 % | ·
· | Cobre | 102,3 | 90,9 | 12,5 % | 108,1 | -5,4 % | ·
```

### Pág. 1 — tabela #2 (8×8)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` R esumo das vendas      |  Mil toneladas métricas  1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Minério de ferro  68.713 66.141 3,9 % 84.874 -19,0 %`

Preview (5 primeiras linhas):

```
· | R | esumo das vendas | · | · | · | · | ·
· | Mil toneladas métricas | · | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Minério de ferro | · | 68.713 | 66.141 | 3,9 % | 84.874 | -19,0 %
· | Finos1 | · | 59.436 | 56.762 | 4,7 % | 73.566 | -19,2 %
· | Pelotas | · | 7.699 | 7.493 | 2,7 % | 9.056 | -15,0 %
```

### Pág. 1 — tabela #3 (6×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` Resumo da realização de preço      |  US$/t 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Finos de minério de ferro (CFR/FOB, wmt) 95,8 90,8 5,5 % 95,4 0,4 %`

Preview (5 primeiras linhas):

```
· | Resumo da realização de preço | · | · | · | · | ·
· | US$/t | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Finos de minério de ferro (CFR/FOB, wmt) | 95,8 | 90,8 | 5,5 % | 95,4 | 0,4 %
· | Pelotas de minério de ferro (CFR/FOB, wmt) | 133,8 | 140,8 | -5,0 % | 131,4 | 1,8 %
· | Cobre¹² | 13.143 | 8.891 | 47,8 % | 11.003 | 19,4 %
```

### Pág. 1 — tabela #4 (5×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` Prêmio all-in do minério de ferro      |  US$/t 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Prêmio all-in - Total1 6,2 4,8 29,2 % 3,6 72,2 %`
- **[medium] MIXED_COLUMN**: Coluna 2 mistura 75% numérico com 25% texto (possível colunas mescladas)
- **[medium] MIXED_COLUMN**: Coluna 3 mistura 75% numérico com 25% texto (possível colunas mescladas)
- **[medium] MIXED_COLUMN**: Coluna 5 mistura 75% numérico com 25% texto (possível colunas mescladas)

Preview (5 primeiras linhas):

```
· | Prêmio all-in do minério de ferro | · | · | · | · | ·
· | US$/t | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Prêmio all-in - Total1 | 6,2 | 4,8 | 29,2 % | 3,6 | 72,2 %
· | Qualidade e prêmio de finos | 4,1 | 1,7 | 141,2 % | 2,5 | 64,0 %
· | Contribuição do negócio de pelotas2 | 2,1 | 3,1 | -32,3 % | 1,1 | 90,9 %
```

### Pág. 2 — tabela #0 (2×2)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `  |  `
- **[medium] SPARSE_ROWS**: 2/2 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | ·
· | ·
```

### Pág. 2 — tabela #1 (2×2)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `  |  `
- **[medium] SPARSE_ROWS**: 2/2 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | ·
· | ·
```

### Pág. 2 — tabela #2 (2×2)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `  |  `
- **[medium] SPARSE_ROWS**: 2/2 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | ·
· | ·
```

### Pág. 4 — tabela #0 (1×2)

- **[high] TINY_TABLE**: Tabela suspeita de fragmento (rows=1, cols=2)
- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `Anexos `

Preview (5 primeiras linhas):

```
Anexos | ·
```

### Pág. 4 — tabela #1 (30×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` Mil toneladas métricas 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Sistema Norte 33.173 34.420 -3,6 % 44.776 -25,9 % |  Serra Norte e Serra Leste 13.319 15.049 -11,5 % 22.629 -41,1 %`

Preview (5 primeiras linhas):

```
· | Mil toneladas métricas | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Sistema Norte | 33.173 | 34.420 | -3,6 % | 44.776 | -25,9 %
· | Serra Norte e Serra Leste | 13.319 | 15.049 | -11,5 % | 22.629 | -41,1 %
· | S11D | 19.854 | 19.371 | 2,5 % | 22.147 | -10,4 %
· | Sistema Sudeste | 19.194 | 16.105 | 19,2 % | 23.864 | -19,6 %
```

### Pág. 4 — tabela #2 (14×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` Mil toneladas métricas 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Sistema Norte 72 370 -80,5 % — n.a. |  São Luis¹ 72 370 -80,5 % — n.a.`

Preview (5 primeiras linhas):

```
· | Mil toneladas métricas | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Sistema Norte | 72 | 370 | -80,5 % | — | n.a.
· | São Luis¹ | 72 | 370 | -80,5 % | — | n.a.
· | Sistema Sudeste | 5.029 | 3.722 | 35,1 % | 4.892 | 2,8 %
· | Itabrasco (Tubarão 3) | 846 | 754 | 12,2 % | 382 | 121,5 %
```

### Pág. 5 — tabela #0 (1×2)

- **[high] TINY_TABLE**: Tabela suspeita de fragmento (rows=1, cols=2)
- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `Anexos `

Preview (5 primeiras linhas):

```
Anexos | ·
```

### Pág. 5 — tabela #1 (13×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` milhares de toneladas métricas 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Brasil 81,8 68,3 19,8 % 81,5 0,4 % |  Salobo 52,8 52,3 1,0 % 62,9 -16,1 %`

Preview (5 primeiras linhas):

```
· | milhares de toneladas métricas | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Brasil | 81,8 | 68,3 | 19,8 % | 81,5 | 0,4 %
· | Salobo | 52,8 | 52,3 | 1,0 % | 62,9 | -16,1 %
· | Sossego | 29,0 | 16,0 | 81,3 % | 18,6 | 55,9 %
· | Canadá | 20,4 | 22,6 | -9,7 % | 26,7 | -23,6 %
```

### Pág. 5 — tabela #2 (19×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — ` milhares de toneladas métricas 1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Produto acabado por origem      |  Canadá 22,3 20,0 11,5 % 17,0 31,2 %`

Preview (5 primeiras linhas):

```
· | milhares de toneladas métricas | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Produto acabado por origem | · | · | · | · | ·
· | Canadá | 22,3 | 20,0 | 11,5 % | 17,0 | 31,2 %
· | Sudbury | 10,6 | 9,9 | 7,1 % | 8,2 | 29,3 %
· | Thompson | 1,2 | 3,6 | -66,7 % | 1,4 | -14,3 %
```

### Pág. 5 — tabela #3 (6×7)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `  1T26 1T25 ∆ a/a 4T25 ∆ t/t |  Cobalto (toneladas métricas) 888 739 20,2 % 724 22,7 % |  Platina (milhares de onças troy) 21 24 -12,5 % 25 -16,0 %`

Preview (5 primeiras linhas):

```
· | · | 1T26 | 1T25 | ∆ a/a | 4T25 | ∆ t/t
· | Cobalto (toneladas métricas) | 888 | 739 | 20,2 % | 724 | 22,7 %
· | Platina (milhares de onças troy) | 21 | 24 | -12,5 % | 25 | -16,0 %
· | Paládio (milhares de onças troy) | 23 | 27 | -14,8 % | 31 | -25,8 %
· | Ouro (milhares de onças troy)1 | 121 | 115 | 5,2 % | 146 | -17,1 %
```

### Pág. 6 — tabela #0 (1×2)

- **[high] TINY_TABLE**: Tabela suspeita de fragmento (rows=1, cols=2)
- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `Anexos `

Preview (5 primeiras linhas):

```
Anexos | ·
```

### Pág. 6 — tabela #1 (32×6)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `  1T 2T 3T 4T    |  Operações de cobre     |  Salobo    `
- **[medium] SPARSE_ROWS**: 12/32 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | · | 1T 2T 3T 4T | · | · | ·
· | Operações de cobre | · | · | · | ·
· | Salobo | · | · | · | ·
· | Salobo I & II | · | 2 semanas | · | ·
· | Salobo III | · | · | 2 semanas | ·
```

### Pág. 7 — tabela #0 (20×9)

- **[high] MISSING_HEADER**: Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas (possível quebra entre páginas ou falso positivo de extração) — `         |       Relações com
Investidores   |         `
- **[medium] SPARSE_ROWS**: 20/20 linhas com densidade < 30% (possível perda de células)

Preview (5 primeiras linhas):

```
· | · | · | · | · | · | · | · | ·
· | · | · | · | · | · | Relações com
Investidores | · | ·
· | · | · | · | · | · | · | · | ·
· | Este comunicado pode incluir declarações sobre as expectativas atuais da
Vale sobre eventos ou resultados futuros (estimativas e projeções),
incluindo em especial expectativas de produção e vendas de minério de
ferro, níquel e cobre nas páginas 1, 2, 3 e 4. Muitas dessas estimativas e
projeções podem ser identificadas por meio do uso de palavras com
perspectivas futuras como “antecipar", “acreditar", “poder“, “esperar",
“dever“, "planejar", “pretender“, "estimar“, “fará” e "potencial", entre
outras. Todas as estimativas e projeções envolvem vários riscos e
incertezas. A Vale não pode garantir que tais declarações venham a ser
corretas. Tais riscos e incertezas incluem, entre outros, fatores
relacionados a: (a) países onde a Vale opera, especialmente Brasil e
Canadá; (b) economia global; (c) mercado de capitais; (d) negócio de
minérios e metais e sua dependência à produção industrial global, que é
cíclica por natureza; e (e) elevado grau de competição global nos mercados
onde a Vale opera. A Vale cautela que os resultados atuais podem
diferenciar materialmente dos planos, objetivos, expectativas, estimativas
e intenções expressadas nesta apresentação. A Vale não assume nenhuma
obrigação de atualizar publicamente ou revisar nenhuma estimativa e
projeção, seja como resultado de informações novas ou eventos futuros
ou por qualquer outra razão. Para obter informações adicionais sobre
fatores que podem originar resultados diferentes daqueles estimados
pela Vale, favor consultar os relatórios arquivados pela Vale na U.S.
Securities and Exchange Commission (SEC), na Comissão de Valores
Mobiliários (CVM) e, em particular, os fatores discutidos nas seções
“Estimativas e Projeções” e “Fatores de Risco” no Relatório Anual - Form
20-F da Vale. | · | · | · | · | Vale.RI@vale.com | · | ·
· | · | · | · | · | · | · | · | ·
```
