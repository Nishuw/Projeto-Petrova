"""
Detectores de modos de falha em tabelas extraídas de DFs brasileiras.

Cada função recebe uma tabela (lista de listas de strings, como pdfplumber retorna)
e/ou contexto (página, posição) e devolve uma lista de FailureMode encontradas.

A intenção aqui não é classificar com perfeição — é dar SINAIS automáticos de que
algo provavelmente quebrou, para guiar a inspeção manual posterior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FailureMode:
    code: str
    description: str
    severity: str  # "low" | "medium" | "high"
    evidence: str = ""


_NUM_BR_RE = re.compile(r"^-?\(?\s*R?\$?\s*-?[\d\.\s]+,\d{1,4}\)?$|^-?\(?\s*[\d\.]+\)?$")
_HEADER_HINT_RE = re.compile(
    r"(controlador|consolidad|R\$\s*mil|em milhares|em milh[oõ]es|31/\d{2}/\d{4})",
    re.IGNORECASE,
)


def _is_numeric_br(cell: str) -> bool:
    if cell is None:
        return False
    s = cell.strip()
    if not s:
        return False
    return bool(_NUM_BR_RE.match(s))


def _row_density(row: list[str | None]) -> float:
    if not row:
        return 0.0
    filled = sum(1 for c in row if c and c.strip())
    return filled / len(row)


def detect_empty_or_tiny(table: list[list[str | None]]) -> list[FailureMode]:
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
    """DFs brasileiras quase sempre têm cabeçalho com 'Controladora', 'Consolidado',
    período (ex: '31/12/2024') ou 'R$ mil'. Se NENHUMA das primeiras 3 linhas tem
    esses sinais, provavelmente o cabeçalho ficou em outra página."""
    if not table:
        return []
    head = " | ".join(
        " ".join((c or "") for c in row) for row in table[:3] if row
    )
    if not _HEADER_HINT_RE.search(head):
        return [
            FailureMode(
                "MISSING_HEADER",
                "Tabela sem cabeçalho típico de DF brasileira nas 3 primeiras linhas "
                "(possível quebra entre páginas)",
                "high",
                evidence=head[:200],
            )
        ]
    return []


def detect_misaligned_numbers(table: list[list[str | None]]) -> list[FailureMode]:
    """Em DFs, colunas numéricas devem ter alta proporção de células numéricas.
    Se uma coluna mistura muito texto com números, provavelmente houve mesclagem
    indevida de colunas."""
    if not table or len(table) < 3:
        return []
    cols = max(len(r) for r in table)
    issues: list[FailureMode] = []
    for c in range(cols):
        col_cells = [
            (row[c] if c < len(row) else None) for row in table[1:]  # ignora header
        ]
        non_empty = [x for x in col_cells if x and x.strip()]
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
    """Linhas com densidade muito baixa sugerem que a extração perdeu células."""
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
    """Se a tabela tem números altos mas não menciona 'mil' ou 'milhões' em lugar
    nenhum, o leitor (humano ou LLM) pode interpretar errado a magnitude."""
    if not table:
        return []
    flat = " ".join(
        (c or "") for row in table for c in row
    ).lower()
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


ALL_DETECTORS = [
    detect_empty_or_tiny,
    detect_missing_header,
    detect_misaligned_numbers,
    detect_sparse_rows,
    detect_unit_ambiguity,
]


def detect_all(table: list[list[str | None]]) -> list[FailureMode]:
    out: list[FailureMode] = []
    for det in ALL_DETECTORS:
        out.extend(det(table))
    return out


def summarize(failures: Iterable[FailureMode]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in failures:
        counts[f.code] = counts.get(f.code, 0) + 1
    return counts
