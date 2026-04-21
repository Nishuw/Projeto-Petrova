"""
Fase 2 / item #1: mede o ganho da recuperação de cabeçalho via texto
da página no caso mais difícil do corpus (DRE gerencial do Itaú).

Por que um script separado do 04:
    A tabela do Itaú tem particularidades que não cabem no script da
    Vale sem poluí-lo:
      - Não tem linha de cabeçalho dentro da tabela extraída (o
        pdfplumber perde isso). O cabeçalho só existe no texto puro
        da página.
      - A linha 0 da tabela é só a unidade ("Em R$ milhões"), diferente
        do padrão Vale (título + unidade + cabeçalho em 3 linhas).
      - Isso muda os offsets de "onde começam os dados" e portanto o
        mapeamento pergunta → linha.

    Deixar um script dedicado mantém o caso simples e auditável.

Dois cenários avaliados:
    (A) Auto-contido SEM recuperação: fingimos que não temos o texto
        da página. É o que o chunker Fase 1 entregaria hoje em dia.
    (B) Auto-contido COM recuperação: passamos o texto da página e
        deixamos o chunker inferir título/unidade/headers.

    O baseline (tabela bruta) também é medido, como controle.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table as RichTable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm_client import ask  # noqa: E402
from src.self_contained_chunker import (  # noqa: E402
    extract_table_with_context,
    render_baseline_chunk,
    render_self_contained_chunks,
)


SYSTEM_PROMPT = (
    "Você é um analista financeiro. Responda à pergunta usando APENAS o "
    "contexto fornecido. Se a informação não estiver no contexto, "
    "responda 'não consta'. Seja CONCISO: a resposta ideal tem 1 a 5 "
    "palavras (um número, uma data, uma palavra-chave). Não explique."
)


# Mapeamento pergunta → linha(s) de DADOS relevante(s). Os índices são
# 0-based dentro do conjunto de linhas de dados da tabela (onde a
# linha 0 é "Produto Bancário", a 1 é "Margem Financeira Gerencial",
# a 2 é "Margem Financeira com Clientes", a 3 é "Margem Financeira com
# o Mercado", etc.). A linha da "Em R$ milhões" já é pulada pelo
# chunker auto-contido (não tem dados).
RELEVANT_DATA_ROWS: dict[str, list[int]] = {
    "q1_mfc_4t25": [2],           # Margem Financeira com Clientes
    "q2_mfc_2025": [2],
    "q3_mfm_3t25": [3],           # Margem Financeira com o Mercado
    "q4_mfm_var_aa_ano": [3],
    "q5_mfm_4t24": [3],
    # Metadados: qualquer chunk auto-contido traz a unidade e o título;
    # pegamos a 2 arbitrariamente. No baseline, a linha solta não traz
    # nada disso — é exatamente essa falha que queremos medir.
    "q6_unidade": [2],
    "q7_titulo": [2],
}


# Quantas linhas iniciais da tabela renderizada NÃO são dados. Na
# Vale são 2 (título + cabeçalho). No Itaú só 1 (a linha que traz só
# "Em R$ milhões"). Esse valor é específico do documento e por isso
# fica aqui no script, não no módulo `self_contained_chunker`.
BASELINE_NON_DATA_ROWS_PREFIX = 1


# ---------------------------------------------------------------------------
# Matcher — réplica do 04 para manter os scripts independentes
# ---------------------------------------------------------------------------


def _normalize_for_match(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"(?<=\d)\.(?=\d)", "", s)
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    s = re.sub(r"[r\$%()'\"\u2206\u2019\u00b9\u00b2\u00b3]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_correct(model_answer: str, gold_answers: list[str]) -> bool:
    norm_answer = _normalize_for_match(model_answer)
    for gold in gold_answers:
        norm_gold = _normalize_for_match(gold)
        if norm_gold and norm_gold in norm_answer:
            return True
    return False


def build_user_prompt(context: str, question: str) -> str:
    return (
        "CONTEXTO:\n"
        f"{context}\n\n"
        "PERGUNTA:\n"
        f"{question}\n\n"
        "RESPOSTA:"
    )


# ---------------------------------------------------------------------------
# Retrieval simulado
# ---------------------------------------------------------------------------


def baseline_partial_chunk(table_text: str, row_indices: list[int]) -> str:
    """Pega APENAS as linhas de dados solicitadas do baseline."""
    lines = table_text.split("\n")
    data_lines = lines[BASELINE_NON_DATA_ROWS_PREFIX:]
    picked = [data_lines[i] for i in row_indices if i < len(data_lines)]
    return "\n".join(picked)


def chunks_partial(chunks: list[str], row_indices: list[int]) -> str:
    picked = [chunks[i] for i in row_indices if i < len(chunks)]
    return "\n\n---\n\n".join(picked)


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


@dataclass
class TrialResult:
    question_id: str
    question: str
    gold_answers: list[str]
    answer_baseline: str
    correct_baseline: bool
    tokens_baseline: int
    answer_no_recovery: str
    correct_no_recovery: bool
    tokens_no_recovery: int
    answer_with_recovery: str
    correct_with_recovery: bool
    tokens_with_recovery: int


def main() -> None:
    console = Console()

    qa_path = ROOT / "data" / "processed" / "itau_4t25_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf_path = ROOT / "data" / "raw" / qa["source"]

    table, page_text = extract_table_with_context(
        str(pdf_path), qa["page"], qa["table_index"]
    )

    baseline_text = render_baseline_chunk(table)
    # Cenário (A): chunker "antigo", sem texto da página.
    chunks_no_recovery = render_self_contained_chunks(table)
    # Cenário (B): chunker com a melhoria da Fase 2 #1.
    chunks_with_recovery = render_self_contained_chunks(table, page_text=page_text)

    console.print(
        f"\n[bold cyan]Fase 2 #1[/bold cyan] — recuperação de cabeçalho "
        f"em tabela sem header extraído (Itaú DRE, pág. {qa['page']})\n"
    )
    console.print(
        f"  Chunks sem recuperação: [bold]{len(chunks_no_recovery)}[/bold]"
    )
    console.print(
        f"  Chunks com recuperação: [bold]{len(chunks_with_recovery)}[/bold]\n"
    )

    trials: list[TrialResult] = []
    for q in qa["questions"]:
        rows = RELEVANT_DATA_ROWS.get(q["id"], [])
        if not rows:
            console.print(
                f"  [yellow]pulando[/yellow] {q['id']} (sem mapeamento)"
            )
            continue

        ctx_baseline = baseline_partial_chunk(baseline_text, rows)
        ctx_no_rec = chunks_partial(chunks_no_recovery, rows)
        ctx_with_rec = chunks_partial(chunks_with_recovery, rows)

        console.print(f"  → {q['id']} ...")

        r_base = ask(
            build_user_prompt(ctx_baseline, q["question"]),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=80,
        )
        r_no = ask(
            build_user_prompt(ctx_no_rec, q["question"]),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=80,
        )
        r_with = ask(
            build_user_prompt(ctx_with_rec, q["question"]),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=80,
        )

        trials.append(
            TrialResult(
                question_id=q["id"],
                question=q["question"],
                gold_answers=q["gold_answers"],
                answer_baseline=r_base.text,
                correct_baseline=is_correct(r_base.text, q["gold_answers"]),
                tokens_baseline=r_base.prompt_tokens + r_base.completion_tokens,
                answer_no_recovery=r_no.text,
                correct_no_recovery=is_correct(r_no.text, q["gold_answers"]),
                tokens_no_recovery=r_no.prompt_tokens + r_no.completion_tokens,
                answer_with_recovery=r_with.text,
                correct_with_recovery=is_correct(r_with.text, q["gold_answers"]),
                tokens_with_recovery=r_with.prompt_tokens + r_with.completion_tokens,
            )
        )

    n = len(trials)
    correct_base = sum(1 for t in trials if t.correct_baseline)
    correct_no = sum(1 for t in trials if t.correct_no_recovery)
    correct_with = sum(1 for t in trials if t.correct_with_recovery)
    tok_base = sum(t.tokens_baseline for t in trials)
    tok_no = sum(t.tokens_no_recovery for t in trials)
    tok_with = sum(t.tokens_with_recovery for t in trials)

    view = RichTable(title="Resultados — Itaú DRE, retrieval parcial", show_lines=True)
    view.add_column("ID", overflow="fold")
    view.add_column("Baseline", overflow="fold")
    view.add_column("OK?", justify="center")
    view.add_column("Auto-contido\n(sem recup.)", overflow="fold")
    view.add_column("OK?", justify="center")
    view.add_column("Auto-contido\n(com recup.)", overflow="fold")
    view.add_column("OK?", justify="center")

    for t in trials:
        view.add_row(
            t.question_id,
            t.answer_baseline[:40],
            "[green]✓" if t.correct_baseline else "[red]✗",
            t.answer_no_recovery[:40],
            "[green]✓" if t.correct_no_recovery else "[red]✗",
            t.answer_with_recovery[:40],
            "[green]✓" if t.correct_with_recovery else "[red]✗",
        )

    console.print()
    console.print(view)

    summary = RichTable(title="Sumário", show_lines=False)
    summary.add_column("Estratégia")
    summary.add_column("Acertos", justify="right")
    summary.add_column("Precisão", justify="right")
    summary.add_column("Tokens", justify="right")
    summary.add_row("Baseline (linha solta, sem header)",
                    f"{correct_base}/{n}", f"{correct_base/n*100:.1f}%", str(tok_base))
    summary.add_row("Auto-contido SEM recuperação",
                    f"{correct_no}/{n}", f"{correct_no/n*100:.1f}%", str(tok_no))
    summary.add_row("Auto-contido COM recuperação (Fase 2 #1)",
                    f"{correct_with}/{n}", f"{correct_with/n*100:.1f}%", str(tok_with))
    console.print()
    console.print(summary)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / "eval_partial_retrieval__itau_4t25.json"
    out_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": qa["source"],
                "table_title": qa["table_title"],
                "n_questions": n,
                "baseline": {"correct": correct_base, "accuracy": correct_base / n,
                             "tokens_total": tok_base},
                "self_contained_no_recovery": {
                    "correct": correct_no, "accuracy": correct_no / n,
                    "tokens_total": tok_no},
                "self_contained_with_recovery": {
                    "correct": correct_with, "accuracy": correct_with / n,
                    "tokens_total": tok_with},
                "trials": [
                    {
                        "id": t.question_id,
                        "question": t.question,
                        "gold_answers": t.gold_answers,
                        "answer_baseline": t.answer_baseline,
                        "correct_baseline": t.correct_baseline,
                        "answer_no_recovery": t.answer_no_recovery,
                        "correct_no_recovery": t.correct_no_recovery,
                        "answer_with_recovery": t.answer_with_recovery,
                        "correct_with_recovery": t.correct_with_recovery,
                    }
                    for t in trials
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    console.print(f"\nDump JSON: [dim]{out_json}[/dim]\n")


if __name__ == "__main__":
    main()
