"""
Fase 0 — Baseline em lote.

Roda o extrator com `pdfplumber` em TODOS os PDFs encontrados em
`data/raw/` e produz dois artefatos consolidados:

    reports/_consolidated__pdfplumber.md     (relatório legível)
    reports/_consolidated__pdfplumber.json   (dump completo)

Por que existir, se já temos o `01_baseline_pdfplumber.py`:
    O script 01 olha um PDF por vez e é ótimo para investigar um caso.
    Aqui o foco é AGREGAR — quando se quer comparar o comportamento da
    baseline em vários documentos diferentes (Vale, Itaú, Petrobras...),
    é o relatório consolidado que sustenta a discussão. "Em N de M
    documentos, o modo de falha X aparece em Y% das tabelas" é o tipo
    de afirmação que justifica decisão de pesquisa.

Uso:
    python scripts/02_baseline_batch.py
    # ou explicitando o diretório:
    python scripts/02_baseline_batch.py data/raw
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber
from rich.console import Console
from rich.table import Table as RichTable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.failure_modes import detect_all  # noqa: E402

console = Console()


# ---------------------------------------------------------------------------
# Extração (igual ao script 01, mas isolada para reuso interno)
# ---------------------------------------------------------------------------


def extract_one_pdf(pdf_path: Path) -> list[dict]:
    """Extrai todas as tabelas de um PDF e roda detectores em cada uma.

    Mesma estrutura do script 01 — duplicado aqui em vez de importado
    para manter os scripts independentes uns dos outros (cada script
    pode ser lido isoladamente sem ter que abrir três arquivos).
    """
    out: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables() or []
            except Exception as e:
                console.print(
                    f"[red]Erro extraindo página {page_num} de "
                    f"{pdf_path.name}: {e}[/red]"
                )
                tables = []

            for t_idx, table in enumerate(tables):
                rows = len(table)
                cols = max((len(r) for r in table), default=0)
                failures = detect_all(table)

                out.append(
                    {
                        "page": page_num,
                        "table_index": t_idx,
                        "rows": rows,
                        "cols": cols,
                        "failures": [
                            {
                                "code": f.code,
                                "description": f.description,
                                "severity": f.severity,
                            }
                            for f in failures
                        ],
                    }
                )

    return out


# ---------------------------------------------------------------------------
# Agregação por documento e geral
# ---------------------------------------------------------------------------


def per_doc_stats(results: list[dict]) -> dict:
    """Estatísticas resumidas para um único documento."""
    total = len(results)
    if total == 0:
        return {
            "total_tables": 0,
            "tables_with_failures": 0,
            "pct_with_failures": 0.0,
            "by_code": {},
        }

    by_code: dict[str, int] = {}
    for r in results:
        for f in r["failures"]:
            by_code[f["code"]] = by_code.get(f["code"], 0) + 1

    with_failures = sum(1 for r in results if r["failures"])

    return {
        "total_tables": total,
        "tables_with_failures": with_failures,
        "pct_with_failures": round(with_failures / total * 100, 1),
        "by_code": by_code,
    }


# ---------------------------------------------------------------------------
# Relatório consolidado
# ---------------------------------------------------------------------------


def build_consolidated_report(per_doc: dict[str, dict]) -> str:
    """Markdown com a visão agregada + tabela por documento.

    A primeira tabela é o "headline" — o número que vai na conclusão.
    A segunda é o detalhamento por documento. A terceira é a
    decomposição por código de falha.
    """
    lines: list[str] = []
    lines.append("# Relatório consolidado — Baseline pdfplumber")
    lines.append("")
    lines.append(f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Documentos analisados: **{len(per_doc)}**")
    lines.append("")

    if not per_doc:
        lines.append("Nenhum PDF encontrado em `data/raw/`.")
        return "\n".join(lines)

    # Agregação geral
    total_tables_all = sum(s["total_tables"] for s in per_doc.values())
    total_with_fail = sum(s["tables_with_failures"] for s in per_doc.values())
    pct_overall = (
        round(total_with_fail / total_tables_all * 100, 1)
        if total_tables_all
        else 0.0
    )

    by_code_all: dict[str, int] = {}
    for s in per_doc.values():
        for code, n in s["by_code"].items():
            by_code_all[code] = by_code_all.get(code, 0) + n

    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Total de tabelas extraídas: **{total_tables_all}**")
    lines.append(
        f"- Tabelas com pelo menos 1 modo de falha detectado: "
        f"**{total_with_fail}** ({pct_overall}%)"
    )
    lines.append("")

    lines.append("## Por documento")
    lines.append("")
    lines.append("| Documento | Tabelas | Com falhas | % |")
    lines.append("|---|---:|---:|---:|")
    for name in sorted(per_doc):
        s = per_doc[name]
        lines.append(
            f"| `{name}` | {s['total_tables']} | "
            f"{s['tables_with_failures']} | {s['pct_with_failures']}% |"
        )
    lines.append("")

    lines.append("## Por código de falha (agregado)")
    lines.append("")
    lines.append("| Código | Ocorrências |")
    lines.append("|---|---:|")
    for code, n in sorted(by_code_all.items(), key=lambda x: -x[1]):
        lines.append(f"| `{code}` | {n} |")
    lines.append("")

    lines.append("## Por código de falha (por documento)")
    lines.append("")
    all_codes = sorted(by_code_all.keys())
    if all_codes:
        header = "| Documento | " + " | ".join(f"`{c}`" for c in all_codes) + " |"
        sep = "|---|" + "---:|" * len(all_codes)
        lines.append(header)
        lines.append(sep)
        for name in sorted(per_doc):
            s = per_doc[name]
            row = [f"`{name}`"]
            for c in all_codes:
                row.append(str(s["by_code"].get(c, 0)))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Saída no terminal
# ---------------------------------------------------------------------------


def print_summary_terminal(per_doc: dict[str, dict]) -> None:
    if not per_doc:
        console.print("[yellow]Nenhum PDF em data/raw/.[/yellow]")
        return

    rich_t = RichTable(title="Baseline por documento")
    rich_t.add_column("Documento", overflow="fold")
    rich_t.add_column("Tabelas", justify="right")
    rich_t.add_column("Com falhas", justify="right")
    rich_t.add_column("%", justify="right")

    for name in sorted(per_doc):
        s = per_doc[name]
        rich_t.add_row(
            name,
            str(s["total_tables"]),
            str(s["tables_with_failures"]),
            f"{s['pct_with_failures']}%",
        )
    console.print(rich_t)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw"
    raw_dir = raw_dir.resolve()

    if not raw_dir.exists():
        console.print(f"[red]Diretório não encontrado: {raw_dir}[/red]")
        return 2

    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        console.print(f"[yellow]Nenhum PDF encontrado em {raw_dir}[/yellow]")
        console.print(
            "Coloque PDFs de demonstrações financeiras em `data/raw/` e rode de novo."
        )
        return 0

    console.print(f"Encontrados [bold]{len(pdfs)}[/bold] PDF(s) em {raw_dir}")

    per_doc: dict[str, dict] = {}
    for p in pdfs:
        console.print(f"  → processando [cyan]{p.name}[/cyan] ...")
        try:
            results = extract_one_pdf(p)
        except Exception as e:
            console.print(f"[red]    falhou: {e}[/red]")
            continue
        per_doc[p.name] = per_doc_stats(results)

    print_summary_terminal(per_doc)

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    md_out = reports_dir / "_consolidated__pdfplumber.md"
    json_out = reports_dir / "_consolidated__pdfplumber.json"

    md_out.write_text(build_consolidated_report(per_doc), encoding="utf-8")
    json_out.write_text(
        json.dumps(per_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"\nRelatório markdown: [cyan]{md_out}[/cyan]")
    console.print(f"Dump JSON:          [cyan]{json_out}[/cyan]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
