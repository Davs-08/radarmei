from __future__ import annotations

import json
import os
import re
from typing import Any, Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from prompts import SYSTEM_PROMPT, montar_user_prompt

load_dotenv()

DEFAULT_BASE_URL = "[https://generativelanguage.googleapis.com/v1beta/openai/](https://generativelanguage.googleapis.com/v1beta/openai/)"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


class AnaliseLicitacao(BaseModel):
    titulo_comercial: str = Field(min_length=3, max_length=180)
    aderencia_empresa: Literal["Alta", "Média", "Baixa"]
    recomendacao_decisao: Literal["Participar", "Avaliar com ressalvas", "Não participar"]
    resumo_executivo: str = Field(min_length=15)
    justificativa_aderencia: str = Field(min_length=10)
    escopo_e_exigencias: list[str] = Field(min_length=1)
    matriz_riscos: list[str] = Field(min_length=1)
    checklist_participacao: list[str] = Field(min_length=1)
    parecer_financeiro_e_acao: str = Field(min_length=10)


def _limpar_json_bruto(conteudo: str) -> str:
    """Remove cercas de código Markdown (```json ... ```) quando presentes."""
    texto = (conteudo or "").strip()
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", texto, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
    if texto.endswith("```"):
        texto = re.sub(r"\s*```$", "", texto)
    return texto.strip()


def _estimar_custo_usd(prompt_tokens: int, completion_tokens: int) -> float:
    custo_entrada_por_1m = float(os.getenv("LLM_INPUT_COST_PER_1M_USD", "0.10"))
    custo_saida_por_1m = float(os.getenv("LLM_OUTPUT_COST_PER_1M_USD", "0.40"))
    return (prompt_tokens / 1_000_000.0) * custo_entrada_por_1m + (
        completion_tokens / 1_000_000.0
    ) * custo_saida_por_1m


def _resposta_mock(texto_edital: str, perfil_empresa: dict[str, Any] | None = None) -> dict[str, Any]:
    perfil = perfil_empresa or {}
    porte = perfil.get("porte") or "MEI"
    ramo = perfil.get("ramo") or "Não informado no texto"
    uf = perfil.get("uf") or "Não informado no texto"
    resumo_curto = " ".join((texto_edital or "").split())[:160] or "Não informado no texto"

    dados = AnaliseLicitacao(
        titulo_comercial=f"Análise de Oportunidade ({porte} — {uf})",
        aderencia_empresa="Alta",
        recomendacao_decisao="Participar",
        resumo_executivo=f"Extrato avaliado: {resumo_curto}",
        justificativa_aderencia=(
            f"Análise simulada para perfil {porte}, ramo '{ramo}' e UF '{uf}'. "
            "Campos ausentes no extrato são marcados como 'Não informado no texto'."
        ),
        escopo_e_exigencias=[
            "Verificar especificações completas, prazos e local de entrega: Não informado no texto em detalhes.",
            "Documentação fiscal e regularidade exigida: Não informado no texto.",
        ],
        matriz_riscos=[
            "Risco: Informações incompletas no extrato inicial gerarem erro de precificação. | Mitigação: Baixar o edital completo e confirmar itens antes de enviar lance.",
            "Risco: Prazo de entrega ou frete impactar a margem líquida. | Mitigação: Simular custos de produto, frete e impostos no simulador.",
        ],
        checklist_participacao=[
            "Ler o edital e o termo de referência oficiais na íntegra",
            "Confirmar margem líquida mínima no simulador financeiro",
            "Preparar documentos de habilitação e proposta",
        ],
        parecer_financeiro_e_acao=(
            "Modo de simulação ativo (LLM_MOCK=1): valide custos reais de fornecedor, frete e "
            "tributos antes da decisão final."
        ),
    )
    json_str = json.dumps(dados.model_dump(), ensure_ascii=False, indent=2)
    return {
        "dados": dados.model_dump(),
        "json_bruto": json_str,
        "uso": {
            "prompt_tokens": 120,
            "completion_tokens": 180,
            "total_tokens": 300,
            "custo_estimado_usd": _estimar_custo_usd(120, 180),
            "modo": "mock",
        },
    }


def _criar_cliente() -> OpenAI:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "Chave de API não configurada. Defina GEMINI_API_KEY (ou OPENAI_API_KEY) no ambiente ou ative LLM_MOCK=1."
        )
    base_url = (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).strip()
    if not base_url.startswith(("http://", "https://")):
        base_url = DEFAULT_BASE_URL
    return OpenAI(api_key=api_key, base_url=base_url)


def analisar_oportunidade(
    texto_edital: str, perfil_empresa: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Analisa o texto de uma licitação/dispensa e retorna relatório validado por Pydantic."""
    modo_mock = os.getenv("LLM_MOCK", "1").strip() == "1"
    if modo_mock:
        return _resposta_mock(texto_edital, perfil_empresa=perfil_empresa)

    client = _criar_cliente()
    modelo = (os.getenv("LLM_MODEL") or DEFAULT_MODEL).strip()
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1800"))
    user_prompt = montar_user_prompt(texto_edital, perfil_empresa=perfil_empresa)

    prompt_tokens_total = 0
    completion_tokens_total = 0
    ultimo_erro: str = ""
    mensagem_usuario_atual = user_prompt

    for tentativa in range(2):
        response = client.chat.completions.create(
            model=modelo,
            temperature=0.2,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": mensagem_usuario_atual},
            ],
        )

        usage = getattr(response, "usage", None)
        p_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        c_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        prompt_tokens_total += p_tok
        completion_tokens_total += c_tok

        escolha = response.choices[0] if response.choices else None
        finish_reason = getattr(escolha, "finish_reason", None) if escolha else None
        raw_content = ((getattr(escolha.message, "content", "") if escolha and escolha.message else "") or "").strip()
        limpo = _limpar_json_bruto(raw_content)

        if finish_reason == "length":
            ultimo_erro = "A resposta do modelo atingiu o limite de tokens e foi cortada antes de concluir o JSON."
        else:
            try:
                parsed_dict = json.loads(limpo)
                validado = AnaliseLicitacao.model_validate(parsed_dict)
                total_tok = prompt_tokens_total + completion_tokens_total
                return {
                    "dados": validado.model_dump(),
                    "json_bruto": json.dumps(validado.model_dump(), ensure_ascii=False, indent=2),
                    "uso": {
                        "prompt_tokens": prompt_tokens_total,
                        "completion_tokens": completion_tokens_total,
                        "total_tokens": total_tok,
                        "custo_estimado_usd": _estimar_custo_usd(
                            prompt_tokens_total, completion_tokens_total
                        ),
                        "modo": "api",
                        "tentativas": tentativa + 1,
                    },
                }
            except (json.JSONDecodeError, ValidationError) as exc:
                ultimo_erro = f"Falha ao estruturar/validar a resposta do modelo ({type(exc).__name__})."

        if tentativa == 0:
            mensagem_usuario_atual = (
                f"{user_prompt}\n\n"
                "ATENÇÃO: A tentativa anterior falhou por formato/tamanho. Retorne um JSON COMPLETO "
                "e conciso obedecendo exatamente ao schema obrigatório, sem truncar campos."
            )

    raise RuntimeError(
        f"Não foi possível gerar um relatório válido após tentativa automática: {ultimo_erro}"
    )