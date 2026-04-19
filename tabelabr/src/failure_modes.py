"""
Detectores de modos de falha em tabelas extraídas de demonstrações
financeiras brasileiras.

A ideia central:
    Um relatório de produção/vendas, DRE, Balanço ou DFC tem padrões
    bem específicos (datas no formato 31/12/AAAA, indicação "R$ mil",
    colunas "Controladora" / "Consolidado", valores com vírgula decimal,
    notas com superíndices, células de "n.a." ou em-dash). Quando uma
    tabela extraída por uma ferramenta como `pdfplumber` *não* exibe
    nenhum desses padrões esperados, é um sinal forte de que a extração
    quebrou — seja porque cortou o cabeçalho, seja porque é um falso
    positivo (parágrafo, título de capítulo etc.).

Cada detector é uma função pura: recebe a tabela (lista de listas como
o `pdfplumber.extract_tables()` retorna) e devolve uma lista de
`FailureMode` encontradas. O objetivo NÃO é classificar com perfeição,
e sim dar SINAIS automáticos para guiar inspeção manual e medir a taxa
de problemas no baseline.

Essa "calibração para o domínio" é proposital. Esses detectores não
seriam bons num corpus genérico — eles são bons para o usuário-alvo
do projeto (analistas/engenheiros lidando com documentos CVM/B3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# ---------------------------------------------------------------------------
# Tipo de saída
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FailureMode:
    """Um sinal de que algo provavelmente saiu errado em uma tabela.

    Atributos:
        code: identificador curto e estável (usado em sumários e gráficos).
              Mantido em UPPER_SNAKE para ficar fácil de filtrar.
        description: explicação humana do problema.
        severity: "low" | "medium" | "high". Usado para priorizar inspeção;
                  "high" significa "se isso acontecer numa tabela, o RAG
                  provavelmente vai responder errado".
        evidence: trecho curto da tabela que motivou o disparo. Útil para
                  abrir o relatório e ir direto ao ponto.
    """

    code: str
    description: str
    severity: str
    evidence: str = ""


# ---------------------------------------------------------------------------
# Regex utilitárias
# ---------------------------------------------------------------------------


# Casamento "número à brasileira": aceita
#   1.234,56     -1.234,56     (1.234,56)     R$ 1.234,56     1234
# e variações com sinal/parêntese (DFs usam parênteses para negativo).
# A forma é deliberadamente permissiva — é melhor classificar célula como
# numérica quando há dúvida do que excluir um número legítimo do cálculo.
_NUM_BR_RE = re.compile(
    r"^-?\(?\s*R?\$?\s*-?[\d\.\s]+,\d{1,4}\)?$"  # com vírgula decimal
    r"|^-?\(?\s*[\d\.]+\)?$"                     # inteiro com separador de milhar
)


# Pistas de cabeçalho típico de DF brasileira. Se NENHUMA destas aparece nas
# 3 primeiras linhas, é um sinal de quebra de página ou de falso positivo.
# Casos que motivaram cada termo:
#   "Controladora" / "Consolidado" — colunas padrão em DRE/Balanço
#   "R$ mil"                       — unidade quase universal em DFs
#   "em milhares" / "em milhões"   — unidade alternativa
#   "31/12/2024" e similares       — período comparativo é regra
_HEADER_HINT_RE = re.compile(
    r"(controlador|consolidad|R\$\s*mil|em milhares|em milh[oõ]es|31/\d{2}/\d{4})",
    re.IGNORECASE,
)


def _is_numeric_br(cell: str | None) -> bool:
    """`True` se a célula casa o padrão de número brasileiro."""
    if cell is None:
        return False
    s = cell.strip()
    if not s:
        return False
    return bool(_NUM_BR_RE.match(s))


def _row_density(row: list[str | None]) -> float:
    """Razão entre células preenchidas e total de células da linha."""
    if not row:
        return 0.0
    filled = sum(1 for c in row if c and c.strip())
    return filled / len(row)


# ---------------------------------------------------------------------------
# Detectores individuais
# ---------------------------------------------------------------------------


def detect_empty_or_tiny(table: list[list[str | None]]) -> list[FailureMode]:
    """Tabela vazia ou tão pequena que provavelmente é fragmento.

    `pdfplumber` às vezes detecta "tabelas" 1x1 ou 2x2 que na verdade são
    pedaços de moldura, títulos, ou regiões em branco. Considero qualquer
    coisa abaixo de 2 linhas ou 2 colunas como suspeita.
    """
    if not table:
        return [FailureMode("EMPTY_TABLE", "Tabela retornada vazia", "high")]

    rows = len(table)
    cols = max((len(r) for r in table), default=0)

    if rows < 2 or cols < 2:
        return [
            FailureMode(
                "TINY_TABLE",
                f"Tabela suspeita de fragmento (rows={rows}, cols={cols})",
                "high",
            )
        ]
    return []


def detect_missing_header(table: list[list[str | None]]) -> list[FailureMode]:
    """Sem cabeçalho típico de DF nas 3 primeiras linhas.

    Critério das 3 primeiras: na prática, mesmo cabeçalhos com "subtítulo"
    raramente passam de 2 linhas. Olhar 3 dá uma margem de segurança.

    Esse detector é o que mais dispara "falso positivo intencional": numa
    tabela legítima em outro domínio (ex: paper acadêmico) ele vai disparar
    sempre. Isso é desejado — queremos que ele só fique silencioso quando
    a tabela realmente "se parece" com uma DF brasileira bem extraída.
    """
    if not table:
        return []

    head = " | ".join(
        " ".join((c or "") for c in row) for row in table[:3] if row
    )

    if not _HEADER_HINT_RE.search(head):
        return [
            FailureMode(
                "MISSING_HEADER",
                "Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras "
                "linhas (possível quebra entre páginas ou falso positivo de "
                "extração)",
                "high",
                # Trunca para não inflar o relatório quando o "cabeçalho"
                # for um parágrafo enorme (acontece com falsos positivos).
                evidence=head[:200],
            )
        ]
    return []


def detect_misaligned_numbers(table: list[list[str | None]]) -> list[FailureMode]:
    """Coluna que mistura texto e número em proporção suspeita.

    Em DFs, colunas numéricas são bem regulares: ou são quase todas
    numéricas (>= 80%), ou quase todas texto (descrição). Quando uma
    coluna está entre 20% e 80% numérica, geralmente significa que o
    `pdfplumber` mesclou indevidamente duas colunas adjacentes (ex:
    "Descrição" + "1T26" viraram uma coluna só).

    Os limiares 20% / 80% são empíricos — ajustar para cima reduz falsos
    positivos mas perde casos reais. Mantenho conservador.
    """
    if not table or len(table) < 3:
        return []

    cols = max(len(r) for r in table)
    issues: list[FailureMode] = []

    # `table[1:]` ignora a primeira linha porque tipicamente é cabeçalho —
    # cabeçalho misturando "1T26" (período) e "Descrição" (texto) seria
    # um falso positivo aqui se considerássemos.
    for c in range(cols):
        col_cells = [
            (row[c] if c < len(row) else None) for row in table[1:]
        ]
        non_empty = [x for x in col_cells if x and x.strip()]

        # Menos de 3 não-vazias é amostra pequena demais para concluir nada.
        if len(non_empty) < 3:
            continue

        numeric_ratio = sum(1 for x in non_empty if _is_numeric_br(x)) / len(non_empty)
        text_ratio = 1 - numeric_ratio

        if 0.2 < numeric_ratio < 0.8:
            issues.append(
                FailureMode(
                    "MIXED_COLUMN",
                    f"Coluna {c} mistura {numeric_ratio:.0%} numérico com "
                    f"{text_ratio:.0%} texto (possível colunas mescladas)",
                    "medium",
                )
            )
    return issues


def detect_sparse_rows(table: list[list[str | None]]) -> list[FailureMode]:
    """Tabela com muitas linhas quase vazias.

    Critério: se mais de 30% das linhas têm densidade < 30%, há perda
    sistemática de células. Tipicamente acontece quando o documento usa
    células mescladas verticais que `pdfplumber` "quebra" sem repetir
    o valor.

    Nota: o segundo limiar (30% das linhas) é proposital. Tabelas com
    1 ou 2 linhas esparsas (totais, subtotais) são normais — não devem
    disparar o alerta sozinhas.
    """
    if not table:
        return []

    sparse = [i for i, row in enumerate(table) if _row_density(row) < 0.3]

    if len(sparse) > len(table) * 0.3:
        return [
            FailureMode(
                "SPARSE_ROWS",
                f"{len(sparse)}/{len(table)} linhas com densidade < 30% "
                "(possível perda de células)",
                "medium",
            )
        ]
    return []


def detect_unit_ambiguity(table: list[list[str | None]]) -> list[FailureMode]:
    """Números grandes sem indicação de unidade no chunk.

    Esse é o detector mais importante para o uso final em RAG: se um
    chunk tem um número grande (ex: "67.669") e nenhuma menção a "mil"
    ou "milhões" no texto, o LLM não tem como saber se é R$ 67 mil,
    R$ 67 milhões, ou unidades de toneladas. Resposta numérica errada
    é praticamente garantida.

    Critério para "número grande": pelo menos um valor com 2 ou mais
    separadores de milhar (ex: "1.234.567"). Números menores raramente
    geram ambiguidade prática.
    """
    if not table:
        return []

    # Achatar tudo num único string facilita a busca por palavras-chave de
    # unidade. Usar lowercase para não depender de "MIL" vs "mil".
    flat = " ".join((c or "") for row in table for c in row).lower()

    if "mil" in flat or "milh" in flat or "r$" in flat:
        return []

    has_big_numbers = False
    for row in table:
        for c in row:
            if c and re.search(r"\d{1,3}(?:\.\d{3}){2,}", c):
                has_big_numbers = True
                break
        if has_big_numbers:
            break

    if has_big_numbers:
        return [
            FailureMode(
                "UNIT_AMBIGUITY",
                "Tabela com números grandes mas sem indicação de unidade "
                "(R$ mil / milhões) no chunk extraído",
                "high",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


# Lista mantida explícita (em vez de auto-descoberta) para que adicionar
# detector novo seja uma decisão consciente — incluindo decidir a ordem
# em que aparecem nos relatórios.
ALL_DETECTORS = [
    detect_empty_or_tiny,
    detect_missing_header,
    detect_misaligned_numbers,
    detect_sparse_rows,
    detect_unit_ambiguity,
]


def detect_all(table: list[list[str | None]]) -> list[FailureMode]:
    """Roda todos os detectores e devolve todas as falhas encontradas."""
    out: list[FailureMode] = []
    for det in ALL_DETECTORS:
        out.extend(det(table))
    return out


def summarize(failures: Iterable[FailureMode]) -> dict[str, int]:
    """Conta ocorrências por código. Útil para sumários e gráficos."""
    counts: dict[str, int] = {}
    for f in failures:
        counts[f.code] = counts.get(f.code, 0) + 1
    return counts
