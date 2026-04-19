"""
Avaliador: baseline (tabela inteira) vs. chunk auto-contido.

Pergunta-chave que esse script responde:
    "Reformatar uma tabela para que cada linha vire um chunk
     auto-suficiente melhora a precisão de respostas do LLM,
     ou o LLM já é bom o bastante com a tabela bruta?"

Como mede:
    1. Carrega N perguntas com gabarito sobre UMA tabela específica.
    2. Para cada pergunta, monta DUAS conversas com o LLM:
       (a) "BASELINE": o contexto é a tabela renderizada como texto.
       (b) "AUTO-CONTAINED": o contexto são os chunks reestruturados.
    3. Recebe a resposta de cada uma e compara com o gabarito usando
       um matcher tolerante (normaliza vírgula/ponto, espaços, etc.).
    4. Relata a precisão lado a lado e o custo em tokens.

Decisão de design importante:
    Para a estratégia auto-contida, mando TODOS os chunks juntos no
    prompt (concatenados). Não é uma simulação realista de um RAG
    completo (que teria um retriever filtrando), mas isola a variável
    "qualidade da reestruturação" da variável "qualidade da
    recuperação". É o que queremos medir nesta etapa do estudo.

    Em uma fase posterior, com retriever real, se o auto-contido
    perder em tokens mas ganhar em retrieval recall, ainda compensa.
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
# Matcher de respostas
# ---------------------------------------------------------------------------


def _normalize_for_match(s: str) -> str:
    """Normaliza string para comparação tolerante.

    - Remove acentos (case "metricas" vs "métricas").
    - Lowercase.
    - Remove pontuação irrelevante e símbolos (R$, %, parênteses, etc.).
    - Padroniza separador decimal: vírgula vira ponto.
    - Remove separador de milhar (ponto entre dígitos).
    - Colapsa espaços.

    A ordem importa: separador de milhar precisa ser tratado ANTES da
    troca vírgula→ponto, senão "69.675" (sessenta e nove mil) vira
    "69.675" (sessenta e nove vírgula seiscentos e setenta e cinco).
    """
    if not s:
        return ""

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()

    # Remove ponto SOMENTE quando entre dígitos (separador de milhar BR).
    s = re.sub(r"(?<=\d)\.(?=\d)", "", s)

    # Vírgula entre dígitos vira ponto (separador decimal BR → padrão).
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)

    # Remove símbolos que não mudam o significado em respostas curtas.
    s = re.sub(r"[r\$%()'\"\u2206\u2019\u00b9\u00b2\u00b3]", " ", s)

    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_correct(model_answer: str, gold_answers: list[str]) -> bool:
    """Devolve True se a resposta do modelo bate com algum gabarito.

    A regra é: o gabarito normalizado precisa estar contido na resposta
    normalizada. Ou seja, se o modelo diz "A produção foi 69675 mil
    toneladas", o gabarito "69675" passa. Mas se o modelo diz só "70
    mil", não passa.
    """
    norm_answer = _normalize_for_match(model_answer)
    for gold in gold_answers:
        norm_gold = _normalize_for_match(gold)
        if norm_gold and norm_gold in norm_answer:
            return True
    return False


# ---------------------------------------------------------------------------
# Construção dos prompts
# ---------------------------------------------------------------------------


def build_user_prompt(context: str, question: str) -> str:
    """Template comum para baseline e auto-contido — mesma estrutura para
    isolar a variável (somente o `context` muda entre as duas)."""
    return (
        "CONTEXTO:\n"
        f"{context}\n\n"
        "PERGUNTA:\n"
        f"{question}\n\n"
        "RESPOSTA:"
    )


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
    answer_self_contained: str
    correct_self_contained: bool
    tokens_self_contained: int


def run_trial(
    question_id: str,
    question: str,
    gold_answers: list[str],
    context_baseline: str,
    context_self_contained: str,
) -> TrialResult:
    r1 = ask(
        build_user_prompt(context_baseline, question),
        system_prompt=SYSTEM_PROMPT,
        max_tokens=80,
    )
    r2 = ask(
        build_user_prompt(context_self_contained, question),
        system_prompt=SYSTEM_PROMPT,
        max_tokens=80,
    )
    return TrialResult(
        question_id=question_id,
        question=question,
        gold_answers=gold_answers,
        answer_baseline=r1.text,
        correct_baseline=is_correct(r1.text, gold_answers),
        tokens_baseline=r1.prompt_tokens + r1.completion_tokens,
        answer_self_contained=r2.text,
        correct_self_contained=is_correct(r2.text, gold_answers),
        tokens_self_contained=r2.prompt_tokens + r2.completion_tokens,
    )


def main() -> None:
    console = Console()

    qa_path = ROOT / "data" / "processed" / "vale_1t26_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))

    pdf_path = ROOT / "data" / "raw" / qa["source"]
    table = extract_specific_table(str(pdf_path), qa["page"], qa["table_index"])

    context_baseline = render_baseline_chunk(table)
    chunks = render_self_contained_chunks(table)
    context_self_contained = "\n\n---\n\n".join(chunks)

    console.print(f"\n[bold cyan]Avaliando[/bold cyan] tabela '{qa['table_title']}' "
                  f"de {qa['source']} (pág. {qa['page']})")
    console.print(f"  Perguntas: [bold]{len(qa['questions'])}[/bold]")
    console.print(f"  Chunks auto-contidos gerados: [bold]{len(chunks)}[/bold]")
    console.print()

    trials: list[TrialResult] = []
    for q in qa["questions"]:
        console.print(f"  → {q['id']} ...")
        trials.append(
            run_trial(
                q["id"],
                q["question"],
                q["gold_answers"],
                context_baseline,
                context_self_contained,
            )
        )

    n = len(trials)
    correct_b = sum(1 for t in trials if t.correct_baseline)
    correct_s = sum(1 for t in trials if t.correct_self_contained)
    tok_b = sum(t.tokens_baseline for t in trials)
    tok_s = sum(t.tokens_self_contained for t in trials)

    table_view = RichTable(title="Resultados por pergunta", show_lines=True)
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

    summary = RichTable(title="Sumário", show_lines=False)
    summary.add_column("Estratégia")
    summary.add_column("Acertos", justify="right")
    summary.add_column("Precisão", justify="right")
    summary.add_column("Tokens totais", justify="right")
    summary.add_row("Baseline (tabela inteira)",
                    f"{correct_b}/{n}", f"{correct_b/n*100:.1f}%", str(tok_b))
    summary.add_row("Auto-contido (linha-a-linha)",
                    f"{correct_s}/{n}", f"{correct_s/n*100:.1f}%", str(tok_s))
    console.print()
    console.print(summary)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / "eval_chunkers__vale_1t26.json"
    out_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": qa["source"],
                "table_title": qa["table_title"],
                "n_questions": n,
                "baseline": {
                    "correct": correct_b,
                    "accuracy": correct_b / n,
                    "tokens_total": tok_b,
                },
                "self_contained": {
                    "correct": correct_s,
                    "accuracy": correct_s / n,
                    "tokens_total": tok_s,
                    "n_chunks": len(chunks),
                },
                "trials": [
                    {
                        "id": t.question_id,
                        "question": t.question,
                        "gold_answers": t.gold_answers,
                        "answer_baseline": t.answer_baseline,
                        "correct_baseline": t.correct_baseline,
                        "tokens_baseline": t.tokens_baseline,
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
