"""
Cliente para chamar modelos LLM via NVIDIA Build (NIM).

Por que NVIDIA Build:
    - Endpoint OpenAI-compatível (re-aproveita o SDK `openai`)
    - Acesso a vários modelos abertos (Llama, Mistral, Nemotron)
    - Tem tier gratuito generoso para experimentação
    - Sem dependência de provedores pagos para o protótipo

Como configurar:
    1. Crie conta em https://build.nvidia.com/
    2. Pegue uma chave em "API Keys"
    3. Coloque no arquivo `.env` na raiz do `tabelabr/`:
           NVIDIA_API_KEY=nvapi-...
    4. O `.env` já está no `.gitignore` — nunca vai pro repositório.

A escolha de modelo padrão (`DEFAULT_MODEL`) é deliberada:
    - llama-3.3-70b é o sweet spot atual entre qualidade e latência
    - Para o protótipo, queremos algo "decente o suficiente" para que a
      diferença entre estratégias de chunking apareça de forma evidente.
    - Trocar de modelo é trivial — só passar `model=` na chamada.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Carrega .env relativo ao diretório do tabelabr/.
# Não falha silenciosamente se o arquivo não existir — pode ser que a
# chave esteja sendo passada como variável de ambiente do sistema.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


@dataclass
class LLMResponse:
    """Resposta bruta do LLM, com o que importa para análise."""

    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


def get_client() -> OpenAI:
    """Devolve um client `openai` apontando para a NVIDIA Build.

    Levanta `RuntimeError` claro se a chave não estiver configurada —
    em vez de deixar o `openai` retornar um erro 401 confuso depois.
    """
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError(
            "NVIDIA_API_KEY não encontrada. Crie um arquivo .env em "
            "tabelabr/.env com a linha:\n"
            "    NVIDIA_API_KEY=nvapi-...\n"
            "Veja .env.example."
        )
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=key)


def ask(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> LLMResponse:
    """Faz uma pergunta de turno único ao modelo.

    `temperature=0.0` é proposital: queremos respostas determinísticas
    para o avaliador funcionar (rodar duas vezes e dar respostas
    diferentes torna o experimento ruidoso).

    `max_tokens=512` cobre respostas longas com folga, mas evita
    derrapadas em bilhete preto se o modelo decidir alucinar 4k tokens.
    """
    client = get_client()

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    choice = completion.choices[0]
    usage = completion.usage

    return LLMResponse(
        text=(choice.message.content or "").strip(),
        model=model,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )
