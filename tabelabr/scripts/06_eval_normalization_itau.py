"""
Fase 2 / item #2: mede o ganho da NORMALIZAÇÃO NUMÉRICA isoladamente.

A hipótese é que, mesmo com o cabeçalho corretamente recuperado (item #1
da Fase 2), as linhas em que a extração do pdfplumber sofreu de:

    a) ESPAÇOS FALSOS dentro do número  ("4 7.560" em vez de "47.560")
    b) SINAIS CONTÁBEIS em parênteses    ("(9.397)" em vez de "-9.397")

ainda confundem o LLM no cenário de retrieval parcial. As perguntas
deste teste foram desenhadas para bater EXCLUSIVAMENTE em linhas com
essas patologias — é o complemento natural do `05_…`, que cobria
linhas "limpas".

Três cenários medidos:
    (A) Baseline: linha solta da tabela bruta, sem cabeçalho.
    (B) Auto-contido COM Fase 2 #1 mas SEM normalização. Header voltou,
        mas os números continuam quebrados.
    (C) Auto-contido COM Fase 2 #1 + #2 (chunker integral). Números
        normalizados.

A leitura interessante é o delta (B → C): mede o ganho marginal de
adicionar a normalização sobre o estado da arte da Fase 2 #1.
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


# Os índices abaixo são 0-based dentro das linhas de DADOS — coincidem
# entre o baseline (após pular a 1ª linha de "Em R$ milhões") e o
# chunker auto-contido. Confirmei isso listando os dois lados.
RELEVANT_DATA_ROWS: dict[str, list[int]] = {
    "q1_produto_bancario_4t25": [0],
    "q2_produto_bancario_2025": [0],
    "q3_mfg_2024": [1],         # Margem Financeira Gerencial
    "q4_rps_4t24": [4],         # Receitas de Prestação de Serviços
    "q5_custo_credito_4t25": [6],
    "q6_custo_credito_2024": [6],
    "q7_despesas_tributarias_4t25": [13],
}


# Mesma constante do script 05: na DRE do Itaú a única linha "não-dado"
# no topo do baseline é "Em R$ milhões".
BASELINE_NON_DATA_ROWS_PREFIX = 1


# ---------------------------------------------------------------------------
# Matcher — réplica do 04/05 para manter o script independente
# ---------------------------------------------------------------------------


def _normalize_for_match(s: str) -> str:
    """Reduz a string a uma forma comparável.

    Operações:
      - decompõe acentos (NFKD) e descarta os combining marks;
      - lower-case;
      - remove pontos entre dígitos ("1.234" → "1234") para neutralizar
        a diferença BR vs US no separador de milhar;
      - troca vírgula entre dígitos por ponto (decimal BR → US);
      - remove ruído tipográfico (R$, %, parênteses, aspas, ∆, ', ¹, ²);
      - colapsa espaços.
    """
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
    answer_no_norm: str
    correct_no_norm: bool
    tokens_no_norm: int
    answer_with_norm: str
    correct_with_norm: bool
    tokens_with_norm: int


def main() -> None:
    console = Console()

    qa_path = ROOT / "data" / "processed" / "itau_4t25_dirty_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf_path = ROOT / "data" / "raw" / qa["source"]

    table, page_text = extract_table_with_context(
        str(pdf_path), qa["page"], qa["table_index"]
    )

    baseline_text = render_baseline_chunk(table)
    # Cenário (B): chunker da Fase 2 #1 (header recuperado), sem #2.
    chunks_no_norm = render_self_contained_chunks(
        table, page_text=page_text, normalize_numbers=False
    )
    # Cenário (C): Fase 2 #1 + #2.
    chunks_with_norm = render_self_contained_chunks(
        table, page_text=page_text, normalize_numbers=True
    )

    console.print(
        "\n[bold cyan]Fase 2 #2[/bold cyan] — normalização numérica em "
        f"linhas com extração suja (Itaú DRE, pág. {qa['page']})\n"
    )
    console.print(
        f"  Chunks (mesmo número nos dois cenários): "
        f"[bold]{len(chunks_with_norm)}[/bold]\n"
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
        ctx_no = chunks_partial(chunks_no_norm, rows)
        ctx_with = chunks_partial(chunks_with_norm, rows)

        console.print(f"  → {q['id']} ...")

        r_base = ask(
            build_user_prompt(ctx_baseline, q["question"]),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=80,
        )
        r_no = ask(
            build_user_prompt(ctx_no, q["question"]),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=80,
        )
        r_with = ask(
            build_user_prompt(ctx_with, q["question"]),
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
                answer_no_norm=r_no.text,
                correct_no_norm=is_correct(r_no.text, q["gold_answers"]),
                tokens_no_norm=r_no.prompt_tokens + r_no.completion_tokens,
                answer_with_norm=r_with.text,
                correct_with_norm=is_correct(r_with.text, q["gold_answers"]),
                tokens_with_norm=r_with.prompt_tokens + r_with.completion_tokens,
            )
        )

    n = len(trials)
    correct_base = sum(1 for t in trials if t.correct_baseline)
    correct_no = sum(1 for t in trials if t.correct_no_norm)
    correct_with = sum(1 for t in trials if t.correct_with_norm)
    tok_base = sum(t.tokens_baseline for t in trials)
    tok_no = sum(t.tokens_no_norm for t in trials)
    tok_with = sum(t.tokens_with_norm for t in trials)

    view = RichTable(
        title="Resultados — Itaú DRE (linhas sujas), retrieval parcial",
        show_lines=True,
    )
    view.add_column("ID", overflow="fold")
    view.add_column("Baseline", overflow="fold")
    view.add_column("OK?", justify="center")
    view.add_column("Auto-c.\n#1 só", overflow="fold")
    view.add_column("OK?", justify="center")
    view.add_column("Auto-c.\n#1 + #2", overflow="fold")
    view.add_column("OK?", justify="center")

    for t in trials:
        view.add_row(
            t.question_id,
            t.answer_baseline[:30],
            "[green]✓" if t.correct_baseline else "[red]✗",
            t.answer_no_norm[:30],
            "[green]✓" if t.correct_no_norm else "[red]✗",
            t.answer_with_norm[:30],
            "[green]✓" if t.correct_with_norm else "[red]✗",
        )

    console.print()
    console.print(view)

    summary = RichTable(title="Sumário", show_lines=False)
    summary.add_column("Estratégia")
    summary.add_column("Acertos", justify="right")
    summary.add_column("Precisão", justify="right")
    summary.add_column("Tokens", justify="right")
    summary.add_row(
        "Baseline (linha solta, sem header)",
        f"{correct_base}/{n}",
        f"{correct_base/n*100:.1f}%",
        str(tok_base),
    )
    summary.add_row(
        "Auto-contido — só Fase 2 #1",
        f"{correct_no}/{n}",
        f"{correct_no/n*100:.1f}%",
        str(tok_no),
    )
    summary.add_row(
        "Auto-contido — Fase 2 #1 + #2",
        f"{correct_with}/{n}",
        f"{correct_with/n*100:.1f}%",
        str(tok_with),
    )
    console.print()
    console.print(summary)

    delta = (correct_with - correct_no) / n * 100
    tokens_delta_pct = (tok_with - tok_no) / tok_no * 100 if tok_no else 0.0
    console.print()
    console.print(
        f"[bold]Ganho marginal de #2 sobre #1[/bold]: "
        f"{delta:+.1f} p.p. de precisão, "
        f"{tokens_delta_pct:+.1f}% de tokens."
    )

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / "eval_normalization__itau_4t25.json"
    out_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": qa["source"],
                "table_title": qa["table_title"],
                "n_questions": n,
                "baseline": {
                    "correct": correct_base,
                    "accuracy": correct_base / n,
                    "tokens_total": tok_base,
                },
                "self_contained_phase2_item1_only": {
                    "correct": correct_no,
                    "accuracy": correct_no / n,
                    "tokens_total": tok_no,
                },
                "self_contained_phase2_item1_and_2": {
                    "correct": correct_with,
                    "accuracy": correct_with / n,
                    "tokens_total": tok_with,
                },
                "trials": [
                    {
                        "id": t.question_id,
                        "question": t.question,
                        "gold_answers": t.gold_answers,
                        "answer_baseline": t.answer_baseline,
                        "correct_baseline": t.correct_baseline,
                        "answer_no_norm": t.answer_no_norm,
                        "correct_no_norm": t.correct_no_norm,
                        "answer_with_norm": t.answer_with_norm,
                        "correct_with_norm": t.correct_with_norm,
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
