import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT

load_dotenv()

PRECO_ENTRADA_POR_1M = float(os.getenv("LLM_PRICE_INPUT_1M", "0.10"))
PRECO_SAIDA_POR_1M = float(os.getenv("LLM_PRICE_OUTPUT_1M", "0.40"))


class AnaliseLicitacao(BaseModel):
    titulo_comercial: str
    categoria_negocio: str
    resumo_simples: str
    compatibilidade_mei: str = Field(description="ALTA, MEDIA ou BAIXA")
    motivo_compatibilidade: str
    prazo_ou_entrega: str
    checklist_inicial: list[str]
    alerta_risco: str


def _limpar_json(texto: str) -> str:
    limpo = texto.strip()
    if limpo.startswith("`"):
        linhas = limpo.splitlines()
        if linhas and linhas[0].startswith("`"):
            linhas = linhas[1:]
        if linhas and linhas[-1].strip() == "`":
            linhas = linhas[:-1]
        limpo = "\n".join(linhas).strip()
    return limpo


def calcular_custo_usd(prompt_tokens: int, completion_tokens: int) -> float:
    custo_entrada = (prompt_tokens / 1_000_000) * PRECO_ENTRADA_POR_1M
    custo_saida = (completion_tokens / 1_000_000) * PRECO_SAIDA_POR_1M
    return round(custo_entrada + custo_saida, 6)


def analisar_oportunidade(texto_edital: str) -> dict:
    if not texto_edital or not texto_edital.strip():
        raise ValueError("O texto da oportunidade/edital não pode estar vazio.")

    mock_mode = os.getenv("LLM_MOCK", "1").strip() == "1"

    if mock_mode:
        dados_mock = {
            "titulo_comercial": "Fornecimento de kits de lanche e café para eventos",
            "categoria_negocio": "Alimentação / Panificação / Eventos",
            "resumo_simples": (
                "A administração quer contratar lanches e café sob demanda para treinamentos "
                "e reuniões internas, seguindo as quantidades pedidas no Termo de Referência."
            ),
            "compatibilidade_mei": "ALTA",
            "motivo_compatibilidade": (
                "Atividade muito comum para pequenos negócios de alimentação local, com "
                "possibilidade de atender por demanda."
            ),
            "prazo_ou_entrega": "Sob demanda / conforme ordem de fornecimento",
            "checklist_inicial": [
                "Conferir itens e exigências sanitárias no Termo de Referência",
                "Separar certidões fiscais e comprovante de regularidade do MEI",
                "Calcular custo de insumos, embalagem e entrega",
            ],
            "alerta_risco": (
                "Modo simulado (LLM_MOCK=1) ativo. Valide sempre o edital oficial e prazos "
                "de entrega antes de apresentar proposta."
            ),
        }
        validado = AnaliseLicitacao(**dados_mock)
        return {
            "dados": validado.model_dump(),
            "json_bruto": json.dumps(validado.model_dump(), ensure_ascii=False, indent=2),
            "uso": {
                "modo": "MOCK",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "custo_estimado_usd": 0.0,
            },
        }

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")

    if not api_key:
        raise RuntimeError("LLM_API_KEY não configurada no arquivo .env.")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *FEW_SHOT_EXAMPLES,
        {"role": "user", "content": texto_edital.strip()},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=700,
    )

    conteudo = response.choices[0].message.content or ""
    json_str = _limpar_json(conteudo)

    try:
        parsed = json.loads(json_str)
        validado = AnaliseLicitacao(**parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Falha ao validar JSON retornado pelo modelo: {exc}\nResposta: {conteudo}") from exc

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

    return {
        "dados": validado.model_dump(),
        "json_bruto": json.dumps(validado.model_dump(), ensure_ascii=False, indent=2),
        "uso": {
            "modo": "REAL",
            "modelo": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "custo_estimado_usd": calcular_custo_usd(prompt_tokens, completion_tokens),
        },
    }
