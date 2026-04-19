"""
Protótipo do "chunk auto-contido" para tabelas de DFs brasileiras.

Hipótese central:
    O chunk default produzido pelo `pdfplumber` (uma tabela inteira virando
    um pedaço de texto) carrega informação ESTRUTURAL implícita que se
    perde quando o RAG quebra/recupera só uma parte. Em particular:

      - O título da tabela ("Resumo da produção") aparece UMA vez no topo;
        se o chunk pega só linhas do meio, o LLM não sabe do que se trata.
      - A unidade ("Mil toneladas métricas") idem — vai pro topo e some.
      - Notas de rodapé com superíndice (¹, ²) ficam órfãs.
      - Colunas vazias-fantasmas (artefato de extração) consomem tokens
        sem agregar nada.
      - Cabeçalhos de coluna (períodos: 1T26, 1T25, ∆ a/a) só aparecem
        uma vez; cada CÉLULA numérica precisaria carregar essa
        contextualização para ser respondível isoladamente.

Solução:
    Transformar a tabela em uma LISTA de chunks, um por linha de dados,
    onde cada chunk é AUTO-SUFICIENTE: traz consigo o título, a unidade,
    o nome do item e o cabeçalho associado a cada valor numérico.

Não-objetivos do protótipo:
    - Detectar e resolver notas de rodapé (planejado, mas em iteração
      futura; por ora as marcações ficam "soltas" no texto do chunk).
    - Tratar tabelas multi-página (cada uma é tratada isoladamente).
    - Ser genérico para QUALQUER tabela: a heurística aqui foi calibrada
      para o padrão observado em releases CVM/B3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pdfplumber


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


# Tabela como o pdfplumber devolve: lista de linhas, cada linha lista de
# células (string ou None).
Row = list[str | None]
Table = list[Row]


@dataclass
class TableContext:
    """Contexto extraído do topo de uma tabela.

    Mantenho separado da tabela "limpa" porque esses metadados são o que
    cada chunk auto-contido precisa carregar. Em vez de tentar descobrir
    de novo a cada linha, descubro UMA vez e injeto.
    """

    title: str | None  # ex: "Resumo da produção"
    unit: str | None   # ex: "Mil toneladas métricas"
    column_headers: list[str]  # ex: ["", "1T26", "1T25", "∆ a/a", ...]


# ---------------------------------------------------------------------------
# Limpeza estrutural
# ---------------------------------------------------------------------------


def _is_blank(cell: str | None) -> bool:
    return cell is None or not cell.strip()


def _strip_phantom_columns(table: Table) -> Table:
    """Remove colunas inteiramente vazias.

    O `pdfplumber` adiciona com frequência uma coluna fantasma à esquerda
    (e às vezes à direita) cheia de None / "". Essas colunas inflam o
    chunk com tokens inúteis e confundem o LLM. Removo qualquer coluna
    onde TODAS as células são vazias.
    """
    if not table:
        return table

    n_cols = max((len(r) for r in table), default=0)
    keep = []
    for c in range(n_cols):
        col_values = [(row[c] if c < len(row) else None) for row in table]
        if not all(_is_blank(v) for v in col_values):
            keep.append(c)

    cleaned: Table = []
    for row in table:
        cleaned.append([(row[c] if c < len(row) else None) for c in keep])
    return cleaned


def _normalize_cell(cell: str | None) -> str:
    """Normaliza uma célula para representação textual.

    Colapso espaços múltiplos e quebras de linha — o pdfplumber às vezes
    devolve "abc\ndef" para uma célula que visualmente era contínua, e
    isso confunde a leitura tanto humana quanto do LLM.
    """
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", cell).strip()


# ---------------------------------------------------------------------------
# Detecção de contexto da tabela
# ---------------------------------------------------------------------------


# Pistas de que uma célula é uma indicação de unidade.
_UNIT_HINTS_RE = re.compile(
    r"(R\$\s*mil|R\$\s*milh[oõ]es|em milhares|em milh[oõ]es|"
    r"mil toneladas|milhares de toneladas|US\$/t|toneladas m[ée]tricas|"
    r"%|onças? troy)",
    re.IGNORECASE,
)

# Pistas de que uma célula é um cabeçalho de coluna de período.
_PERIOD_HINTS_RE = re.compile(
    r"(\d{1,2}T\d{2}|31/\d{2}/\d{4}|\d{2}/\d{4}|"
    r"a/a|t/t|guidance|controlador|consolidad)",
    re.IGNORECASE,
)


def _row_has_period_hints(row: Row) -> bool:
    """`True` se a linha contém alguma marca de cabeçalho de período."""
    return any(c and _PERIOD_HINTS_RE.search(c) for c in row)


def _row_has_unit_hint(row: Row) -> bool:
    return any(c and _UNIT_HINTS_RE.search(c) for c in row)


def detect_context(table: Table) -> TableContext:
    """Identifica título, unidade e cabeçalho de colunas.

    Heurística (calibrada nos PDFs do estudo, página 1 da Vale):

      1. As primeiras N linhas (até 4) são candidatas a "topo da tabela".
      2. A linha com pistas de período (1T26, ∆ a/a, etc.) é a linha de
         CABEÇALHO de colunas. Tudo acima dela é título/unidade.
      3. Se sobra UMA linha acima, é o título.
      4. Se sobram DUAS, a primeira é título e a segunda é unidade.
         (Esse é o padrão Vale: "Resumo da produção" / "Mil toneladas...")

    Quando a heurística não bate (ex: tabela sem título explícito),
    devolvo o que conseguir e deixo nulo o resto. O chunker downstream
    sabe lidar com nulos.
    """
    title: str | None = None
    unit: str | None = None
    column_headers: list[str] = []

    if not table:
        return TableContext(None, None, [])

    # Olha até as 4 primeiras linhas em busca da linha de cabeçalho.
    header_idx = -1
    for i, row in enumerate(table[:4]):
        if _row_has_period_hints(row):
            header_idx = i
            break

    if header_idx == -1:
        # Sem cabeçalho de período identificado — devolvo só os non-blanks
        # como "fallback" (a primeira linha não-vazia vira título).
        for row in table[:3]:
            non_blank = [_normalize_cell(c) for c in row if not _is_blank(c)]
            if non_blank:
                title = " ".join(non_blank)
                break
        return TableContext(title, unit, column_headers)

    column_headers = [_normalize_cell(c) for c in table[header_idx]]

    # Caso especial muito comum em DFs brasileiras: a célula 0 da linha
    # de cabeçalho NÃO é um título de coluna — é a UNIDADE da tabela
    # (ex: "Mil toneladas métricas", "R$ mil"). Se for o caso, promovo
    # para `unit` e zero a célula no header (a coluna 0 vira a coluna
    # do "nome do item", que dispensa cabeçalho).
    if column_headers and _UNIT_HINTS_RE.search(column_headers[0] or ""):
        unit = column_headers[0]
        column_headers[0] = ""

    # Linhas acima do cabeçalho carregam título e/ou unidade.
    above = [row for row in table[:header_idx] if any(not _is_blank(c) for c in row)]

    if len(above) == 1:
        cells = [_normalize_cell(c) for c in above[0] if not _is_blank(c)]
        merged = " ".join(cells)
        if _UNIT_HINTS_RE.search(merged):
            unit = merged
        else:
            title = merged
    elif len(above) >= 2:
        # Padrão Vale: linha 0 = título, linha 1 = unidade.
        first = " ".join(_normalize_cell(c) for c in above[0] if not _is_blank(c))
        second = " ".join(_normalize_cell(c) for c in above[1] if not _is_blank(c))
        title = first
        unit = second if _UNIT_HINTS_RE.search(second) else None
        # Se a segunda linha não parece unidade, é provavelmente parte do
        # título (multi-linha) — concatenamos.
        if unit is None:
            title = f"{first} {second}".strip()

    return TableContext(title=title, unit=unit, column_headers=column_headers)


# ---------------------------------------------------------------------------
# Chunkers
# ---------------------------------------------------------------------------


def render_baseline_chunk(table: Table) -> str:
    """Renderiza a tabela como um único chunk (estilo "tabela markdown bruta").

    Esse é o "estado da arte ingênuo" que a maioria dos pipelines RAG faz
    hoje quando topa com uma tabela: serializa para texto e manda inteira
    como um chunk. É o que vamos comparar contra.

    Mantenho colunas fantasmas REMOVIDAS aqui também, senão a comparação
    seria injusta — qualquer ganho do chunker novo poderia ser atribuído
    só à limpeza, não à reestruturação.
    """
    cleaned = _strip_phantom_columns(table)
    lines = []
    for row in cleaned:
        cells = [_normalize_cell(c) or "—" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def render_self_contained_chunks(table: Table) -> list[str]:
    """Gera um chunk auto-contido por linha de DADOS da tabela.

    Cada chunk segue o template:

        Tabela: <título>
        Unidade: <unidade>
        Item: <nome da linha>
        <Cabeçalho 1>: <valor 1>
        <Cabeçalho 2>: <valor 2>
        ...

    Linhas que não têm dados (separadores, subtítulos, totais sem valor)
    são puladas. Linhas que TÊM valor mas onde TODAS as colunas
    numéricas são vazias também são puladas (não há fato a recuperar).
    """
    cleaned = _strip_phantom_columns(table)
    if not cleaned:
        return []

    ctx = detect_context(cleaned)

    # Identifica a linha de cabeçalho dentro da tabela limpa.
    header_idx = -1
    for i, row in enumerate(cleaned[:4]):
        if _row_has_period_hints(row):
            header_idx = i
            break

    data_start = header_idx + 1 if header_idx >= 0 else 0
    data_rows = cleaned[data_start:]

    if not ctx.column_headers:
        # Sem cabeçalho explícito, geramos chave genérica "Coluna N".
        max_cols = max((len(r) for r in data_rows), default=0)
        ctx.column_headers = [f"Coluna {i}" for i in range(max_cols)]

    chunks: list[str] = []
    for row in data_rows:
        cells = [_normalize_cell(c) for c in row]
        if not any(cells):
            continue

        # Convenção: a primeira coluna não-vazia é o NOME do item da linha.
        # As demais são pares (cabeçalho, valor).
        item_name = ""
        first_idx = -1
        for i, c in enumerate(cells):
            if c:
                item_name = c
                first_idx = i
                break

        if first_idx == -1:
            continue

        # Pares (cabeçalho, valor) ignorando a coluna do nome do item.
        pairs: list[tuple[str, str]] = []
        for i, val in enumerate(cells):
            if i == first_idx:
                continue
            header = (
                ctx.column_headers[i]
                if i < len(ctx.column_headers)
                else f"Coluna {i}"
            )
            if not header and not val:
                continue
            pairs.append((header or f"Coluna {i}", val or "(não informado)"))

        # Se todos os "valores" são vazios/sem informação, é uma linha de
        # subtítulo ou separador — pula.
        if all(v == "(não informado)" or not v.strip() for _, v in pairs):
            continue

        lines = []
        if ctx.title:
            lines.append(f"Tabela: {ctx.title}")
        if ctx.unit:
            lines.append(f"Unidade: {ctx.unit}")
        lines.append(f"Item: {item_name}")
        for header, val in pairs:
            lines.append(f"{header}: {val}")

        chunks.append("\n".join(lines))

    return chunks


# ---------------------------------------------------------------------------
# Conveniência: extrair UMA tabela específica de um PDF
# ---------------------------------------------------------------------------


def extract_specific_table(
    pdf_path: str, page_num: int, table_index: int
) -> Table:
    """Extrai a `table_index`-ésima tabela da página `page_num` (1-indexed).

    Útil para o avaliador: queremos sempre comparar EXATAMENTE a mesma
    tabela em ambas as estratégias.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        tables = page.extract_tables() or []
        if table_index >= len(tables):
            raise IndexError(
                f"Página {page_num} tem {len(tables)} tabelas; "
                f"índice {table_index} fora do alcance."
            )
        return tables[table_index]
