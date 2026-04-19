"""
Experimento crítico: o que acontece quando o retriever entrega
APENAS UM PEDAÇO da tabela ao LLM?

Por que esse experimento existe:
    O experimento anterior (03) mostrou empate entre baseline e
    auto-contido quando o LLM recebia a tabela INTEIRA. Mas em um
    sistema RAG real isso quase nunca acontece — o retriever filtra
    e devolve só os top-K chunks mais relevantes. Se o chunking
    quebra mal a tabela, o chunk recuperado vem MUTILADO de contexto:

      - Sem o título da tabela
      - Sem a unidade
      - Sem o cabeçalho de colunas (números soltos sem saber se é
        1T26 ou 1T25)
      - Sem o nome do item (números soltos sem saber se é minério
        ou pelotas)

    A tese central deste estudo é que o BASELINE colapsa nesse
    cenário e o AUTO-CONTIDO se mantém. Esse script mede.

Como simulamos retrieval parcial:
    BASELINE: pegamos UMA linha do meio da tabela renderizada como
        baseline ("Pelotas | 8.169 | 7.183 | 13,7% | ...") — sem
        título, sem cabeçalho, sem unidade.
    AUTO-CONTIDO: pegamos o chunk auto-contido CORRESPONDENTE
        (ex: o chunk do item "Pelotas") — que por construção
        carrega título, unidade e cabeçalhos.

    Em ambos os casos o LLM recebe APENAS o chunk relacionado ao
    item perguntado. Para perguntas de raciocínio comparativo
    (que envolvem dois itens), passamos os dois chunks
    correspondentes — mantendo a paridade.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table as RichTable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm_client import ask  # noqa: E402
from src.self_contained_chunker import (  # noqa: E402
    extract_specific_table,
    render_baseline_chunk,
    render_self_contained_chunks,
)


SYSTEM_PROMPT = (
    "Você é um analista financeiro. Responda à pergunta usando APENAS o "
    "contexto fornecido. Se a informação não estiver no contexto, "
    "responda 'não consta'. Seja CONCISO: a resposta ideal tem 1 a 5 "
    "palavras (um número, uma data, uma palavra-chave). Não explique."
)


# ---------------------------------------------------------------------------
# Mapeamento pergunta → linha(s) relevante(s) da tabela
# ---------------------------------------------------------------------------

# Indica, por pergunta, QUAL linha da tabela o "retriever ideal" deveria
# devolver. Os índices são 0-based dentro do conjunto DE DADOS (após o
# header). A tabela "Resumo da produção" da Vale tem 4 linhas de dados:
#   0 = Minério de ferro
#   1 = Pelotas
#   2 = Cobre
#   3 = Níquel
#
# Para perguntas de metadado (q5, q6) e raciocínio (q7), o mapeamento é
# diferente — explicado caso a caso abaixo.
RELEVANT_ROWS: dict[str, list[int]] = {
    "q1_minerio_ferro_1t26": [0],
    "q2_pelotas_variacao_aa": [1],
    "q3_cobre_4t25": [2],
    "q4_niquel_var_tt": [3],
    # Metadados: o retriever real "acertaria" qualquer linha (todas
    # carregam o título e a unidade no auto-contido). Pegamos a 0
    # arbitrariamente para forçar o BASELINE a depender do cabeçalho
    # implícito que NÃO está na linha 0 (ele está na linha do header,
    # acima dela, e não vem no chunk solto).
    "q5_unidade_minerio": [0],
    "q6_titulo_tabela": [0],
    # Comparativo: precisa das DUAS linhas (4T25 vs 1T26 de pelotas).
    # Como ambas são sobre o mesmo item, na prática é a linha 1 sozinha.
    "q7_pelotas_4t25_vs_1t26": [1],
}


# ---------------------------------------------------------------------------
# "Retrieval" simulado
# ---------------------------------------------------------------------------


def baseline_partial_chunk(table_text: str, row_indices: list[int]) -> str:
    """Pega APENAS as linhas de dados solicitadas do baseline.

    O baseline de `render_baseline_chunk` produz uma string com N
    linhas separadas por '\\n'. As 2 primeiras são título + cabeçalho,
    as demais são dados. Aqui simulamos um retriever que devolveu só
    a(s) linha(s) de dado pedida(s) — sem o cabeçalho, sem o título.
    """
    lines = table_text.split("\n")
    # Pula 2 linhas: a do título da tabela e a do cabeçalho de colunas.
    data_lines = lines[2:]
    picked = [data_lines[i] for i in row_indices if i < len(data_lines)]
    return "\n".join(picked)


def self_contained_partial_chunk(
    chunks: list[str], row_indices: list[int]
) -> str:
    """Pega APENAS os chunks auto-contidos solicitados.

    Por construção cada chunk auto-contido já carrega título, unidade
    e cabeçalhos — então o retriever parcial não destrói o significado.
    """
    picked = [chunks[i] for i in row_indices if i < len(chunks)]
    return "\n\n---\n\n".join(picked)


# ---------------------------------------------------------------------------
# Reaproveita o matcher do experimento 03
# ---------------------------------------------------------------------------

# Em vez de duplicar, importo do script 03 — mas como scripts/ não é
# um pacote, replico inline a função aqui (decisão deliberada: scripts
# devem rodar de forma independente, sem virar mini-bibliotecas
# acopladas entre si).

import re  # noqa: E402
import unicodedata  # noqa: E402


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


@dataclass
class TrialResult:
    question_id: str
    question: str
    gold_answers: list[str]
    context_baseline: str
    answer_baseline: str
    correct_baseline: bool
    tokens_baseline: int
    context_self_contained: str
    answer_self_contained: str
    correct_self_contained: bool
    tokens_self_contained: int


def main() -> None:
    console = Console()

    qa_path = ROOT / "data" / "processed" / "vale_1t26_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf_path = ROOT / "data" / "raw" / qa["source"]

    table = extract_specific_table(str(pdf_path), qa["page"], qa["table_index"])
    full_baseline = render_baseline_chunk(table)
    full_chunks = render_self_contained_chunks(table)

    console.print(f"\n[bold cyan]Retrieval parcial[/bold cyan] — "
                  f"tabela '{qa['table_title']}'")
    console.print(f"  Cenário: o retriever entrega ao LLM apenas a(s) "
                  f"linha(s)/chunk(s) que casam com a pergunta.\n")

    trials: list[TrialResult] = []
    for q in qa["questions"]:
        rows = RELEVANT_ROWS.get(q["id"], [])
        if not rows:
            console.print(f"  [yellow]pulando[/yellow] {q['id']} "
                          f"(sem mapeamento de linha relevante)")
            continue

        ctx_b = baseline_partial_chunk(full_baseline, rows)
        ctx_s = self_contained_partial_chunk(full_chunks, rows)

        console.print(f"  → {q['id']} ...")
        rb = ask(build_user_prompt(ctx_b, q["question"]),
                 system_prompt=SYSTEM_PROMPT, max_tokens=80)
        rs = ask(build_user_prompt(ctx_s, q["question"]),
                 system_prompt=SYSTEM_PROMPT, max_tokens=80)

        trials.append(
            TrialResult(
                question_id=q["id"],
                question=q["question"],
                gold_answers=q["gold_answers"],
                context_baseline=ctx_b,
                answer_baseline=rb.text,
                correct_baseline=is_correct(rb.text, q["gold_answers"]),
                tokens_baseline=rb.prompt_tokens + rb.completion_tokens,
                context_self_contained=ctx_s,
                answer_self_contained=rs.text,
                correct_self_contained=is_correct(rs.text, q["gold_answers"]),
                tokens_self_contained=rs.prompt_tokens + rs.completion_tokens,
            )
        )

    n = len(trials)
    correct_b = sum(1 for t in trials if t.correct_baseline)
    correct_s = sum(1 for t in trials if t.correct_self_contained)
    tok_b = sum(t.tokens_baseline for t in trials)
    tok_s = sum(t.tokens_self_contained for t in trials)

    table_view = RichTable(title="Resultados — retrieval parcial", show_lines=True)
    table_view.add_column("ID", overflow="fold")
    table_view.add_column("Resposta baseline", overflow="fold")
    table_view.add_column("OK?", justify="center")
    table_view.add_column("Resposta auto-contido", overflow="fold")
    table_view.add_column("OK?", justify="center")

    for t in trials:
        table_view.add_row(
            t.question_id,
            t.answer_baseline[:60],
            "[green]✓" if t.correct_baseline else "[red]✗",
            t.answer_self_contained[:60],
            "[green]✓" if t.correct_self_contained else "[red]✗",
        )

    console.print()
    console.print(table_view)

    summary = RichTable(title="Sumário — retrieval parcial", show_lines=False)
    summary.add_column("Estratégia")
    summary.add_column("Acertos", justify="right")
    summary.add_column("Precisão", justify="right")
    summary.add_column("Tokens totais", justify="right")
    summary.add_row("Baseline (linha solta sem cabeçalho)",
                    f"{correct_b}/{n}", f"{correct_b/n*100:.1f}%", str(tok_b))
    summary.add_row("Auto-contido (chunk com contexto)",
                    f"{correct_s}/{n}", f"{correct_s/n*100:.1f}%", str(tok_s))
    console.print()
    console.print(summary)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / "eval_partial_retrieval__vale_1t26.json"
    out_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": qa["source"],
                "table_title": qa["table_title"],
                "n_questions": n,
                "baseline": {"correct": correct_b, "accuracy": correct_b / n,
                             "tokens_total": tok_b},
                "self_contained": {"correct": correct_s, "accuracy": correct_s / n,
                                   "tokens_total": tok_s},
                "trials": [
                    {
                        "id": t.question_id,
                        "question": t.question,
                        "gold_answers": t.gold_answers,
                        "context_baseline": t.context_baseline,
                        "answer_baseline": t.answer_baseline,
                        "correct_baseline": t.correct_baseline,
                        "tokens_baseline": t.tokens_baseline,
                        "context_self_contained": t.context_self_contained,
                        "answer_self_contained": t.answer_self_contained,
                        "correct_self_contained": t.correct_self_contained,
                        "tokens_self_contained": t.tokens_self_contained,
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
