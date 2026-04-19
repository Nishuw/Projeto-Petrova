"""
Fase 0 — Baseline com pdfplumber.

Pega um PDF de DF brasileira (ITR/DFP/release de resultados) e:
  1. Extrai todas as tabelas página a página com pdfplumber.
  2. Roda detectores de modos de falha em cada tabela.
  3. Gera um relatório markdown em reports/ e um JSON com tudo bruto.

Uso:
    python scripts/01_baseline_pdfplumber.py data/raw/<arquivo>.pdf

Não pretende ser bom — pretende ser HONESTO sobre onde a baseline atual quebra.
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

from src.failure_modes import detect_all, summarize  # noqa: E402

console = Console()


def extract_tables(pdf_path: Path) -> list[dict]:
    """Extrai todas as tabelas do PDF, anotando página e índice."""
    out: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables() or []
            except Exception as e:
                console.print(
                    f"[red]Erro extraindo página {page_num}: {e}[/red]"
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
                                "evidence": f.evidence,
                            }
                            for f in failures
                        ],
                        "preview": table[:5],
                    }
                )
    return out


def build_report(pdf_path: Path, results: list[dict]) -> str:
    total_tables = len(results)
    if total_tables == 0:
        return f"# Relatório: {pdf_path.name}\n\nNenhuma tabela detectada.\n"

    all_failures = [f for r in results for f in r["failures"]]
    by_code: dict[str, int] = {}
    for f in all_failures:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1

    tables_with_issues = sum(1 for r in results if r["failures"])
    pct_problem = tables_with_issues / total_tables * 100

    lines: list[str] = []
    lines.append(f"# Relatório de baseline — `{pdf_path.name}`")
    lines.append("")
    lines.append(f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("- Extrator: `pdfplumber.extract_tables()` (parâmetros default)")
    lines.append("")
    lines.append("## Sumário")
    lines.append("")
    lines.append(f"- Tabelas extraídas: **{total_tables}**")
    lines.append(
        f"- Tabelas com pelo menos 1 modo de falha detectado: "
        f"**{tables_with_issues}** ({pct_problem:.1f}%)"
    )
    lines.append("")
    lines.append("### Falhas por tipo")
    lines.append("")
    lines.append("| Código | Ocorrências |")
    lines.append("|---|---|")
    for code, n in sorted(by_code.items(), key=lambda x: -x[1]):
        lines.append(f"| `{code}` | {n} |")
    lines.append("")
    lines.append("## Tabelas com falhas (top 20)")
    lines.append("")
    shown = 0
    for r in results:
        if not r["failures"]:
            continue
        if shown >= 20:
            break
        shown += 1
        lines.append(
            f"### Pág. {r['page']} — tabela #{r['table_index']} "
            f"({r['rows']}×{r['cols']})"
        )
        lines.append("")
        for f in r["failures"]:
            ev = f" — `{f['evidence']}`" if f["evidence"] else ""
            lines.append(f"- **[{f['severity']}] {f['code']}**: {f['description']}{ev}")
        lines.append("")
        lines.append("Preview (5 primeiras linhas):")
        lines.append("")
        lines.append("```")
        for row in r["preview"]:
            lines.append(" | ".join((c or "·") for c in row))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def print_summary(pdf_path: Path, results: list[dict]) -> None:
    total = len(results)
    all_failures = [f for r in results for f in r["failures"]]
    by_code: dict[str, int] = {}
    for f in all_failures:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1

    console.rule(f"[bold]Resultado para {pdf_path.name}[/bold]")
    console.print(f"Tabelas extraídas: [bold]{total}[/bold]")
    console.print(
        f"Tabelas com falhas detectadas: "
        f"[bold]{sum(1 for r in results if r['failures'])}[/bold]"
    )
    if not by_code:
        console.print("[green]Nenhum modo de falha detectado.[/green]")
        return
    rich_t = RichTable(title="Falhas por tipo")
    rich_t.add_column("Código")
    rich_t.add_column("Ocorrências", justify="right")
    for code, n in sorted(by_code.items(), key=lambda x: -x[1]):
        rich_t.add_row(code, str(n))
    console.print(rich_t)


def main() -> int:
    if len(sys.argv) < 2:
        console.print(
            "[red]Uso: python scripts/01_baseline_pdfplumber.py <caminho.pdf>[/red]"
        )
        return 2

    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        console.print(f"[red]Arquivo não encontrado: {pdf_path}[/red]")
        return 2

    console.print(f"Lendo [bold]{pdf_path.name}[/bold] ...")
    results = extract_tables(pdf_path)
    print_summary(pdf_path, results)

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    stem = pdf_path.stem

    json_out = reports_dir / f"{stem}__pdfplumber.json"
    md_out = reports_dir / f"{stem}__pdfplumber.md"
    json_out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_out.write_text(build_report(pdf_path, results), encoding="utf-8")

    console.print(f"\nRelatório markdown: [cyan]{md_out}[/cyan]")
    console.print(f"Dump JSON:          [cyan]{json_out}[/cyan]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
