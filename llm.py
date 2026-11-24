from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from prompts import SYSTEM_PROMPT_ANALISTA, montar_prompt_usuario

load_dotenv()

PRECO_ENTRADA_POR_1M_USD = 0.10
PRECO_SAIDA_POR_1M_USD = 0.40


class RelatorioTecnicoLicitacao(BaseModel):
    titulo_comercial: str = Field(..., min_length=3)
    resumo_executivo: str = Field(..., min_length=5)
    aderencia_empresa: Literal["ALTA", "MÉDIA", "BAIXA"]
    justificativa_aderencia: str = Field(..., min_length=5)
    escopo_e_exigencias: list[str] = Field(default_factory=list)
    matriz_riscos: list[str] = Field(default_factory=list)
    checklist_participacao: list[str] = Field(default_factory=list)
    recomendacao_decisao: Literal["PARTICIPAR", "AVALIAR COM RESSALVAS", "DESCARTAR"]
    parecer_financeiro_e_acao: str = Field(..., min_length=5)


def _limpar_json_bruto(conteudo: str) -> str:
    texto = conteudo.strip()
    if texto.startswith("`"):
        texto = re.sub(r"^`(?:json)?\s*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\s*`$", "", texto)
    return texto.strip()


def _estimar_custo_usd(prompt_tokens: int, completion_tokens: int) -> float:
    custo = (prompt_tokens / 1_000_000) * PRECO_ENTRADA_POR_1M_USD + (
        completion_tokens / 1_000_000
    ) * PRECO_SAIDA_POR_1M_USD
    return round(custo, 6)


def _resposta_mock(texto_oportunidade: str, perfil_empresa: dict[str, Any] | None) -> dict[str, Any]:
    perfil = perfil_empresa or {}
    ramo = (perfil.get("ramo") or "").strip()
    resumo_curto = texto_oportunidade.strip().replace("\n", " ")[:180]
    aderencia: Literal["ALTA", "MÉDIA", "BAIXA"] = "ALTA" if ramo else "MÉDIA"

    dados = RelatorioTecnicoLicitacao(
        titulo_comercial="Análise de Oportunidade Pública (Modo Simulado)",
        resumo_executivo=f"Síntese da contratação analisada: {resumo_curto}",
        aderencia_empresa=aderencia,
        justificativa_aderencia=(
            f"Avaliação simulada considerando o ramo '{ramo or 'geral'}' e o escopo descrito no edital."
        ),
        escopo_e_exigencias=[
            "Conferir especificações técnicas, quantidades e prazos exatos no edital/TR oficial",
            "Verificar local de entrega ou execução do serviço e eventuais exigências de habilitação",
        ],
        matriz_riscos=[
            "Custos de logística/frete, impostos ou insumos acima do previsto podem corroer a margem",
            "Prazos apertados de entrega ou exigências técnicas específicas podem inviabilizar a participação",
        ],
        checklist_participacao=[
            "Validar regularidade fiscal e certidões exigidas no edital",
            "Calcular planilha de custos diretos + frete + margem mínima antes de enviar lance",
            "Confirmar enquadramento do objeto ao CNAE e capacidade operacional da empresa",
        ],
        recomendacao_decisao="AVALIAR COM RESSALVAS",
        parecer_financeiro_e_acao=(
            "Simule sua margem líquida real antes do lance e leia o edital completo. "
            "Ative LLM_MOCK=0 no .env para rodar o parecer técnico completo com o modelo real."
        ),
    )

    prompt_tokens = max(120, len(texto_oportunidade) // 3)
    completion_tokens = 240
    total_tokens = prompt_tokens + completion_tokens

    return {
        "dados": dados.model_dump(),
        "json_bruto": json.dumps(dados.model_dump(), ensure_ascii=False, indent=2),
        "uso": {
            "modo": "MOCK",
            "modelo": os.getenv("LLM_MODEL", "gemini-3.5-flash-lite"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "custo_estimado_usd": _estimar_custo_usd(prompt_tokens, completion_tokens),
        },
    }


def analisar_oportunidade(
    texto_oportunidade: str,
    perfil_empresa: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not texto_oportunidade or not texto_oportunidade.strip():
        raise ValueError("Informe a descrição da oportunidade, edital ou texto para análise.")

    modo_mock = os.getenv("LLM_MOCK", "1").strip() == "1"
    if modo_mock:
        return _resposta_mock(texto_oportunidade, perfil_empresa)

    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("LLM_API_KEY não configurada no ambiente/.env.")

    base_url = os.getenv("LLM_BASE_URL", "[https://generativelanguage.googleapis.com/v1beta/openai/](https://generativelanguage.googleapis.com/v1beta/openai/)").strip()
    modelo = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite").strip()

    client = OpenAI(api_key=api_key, base_url=base_url)
    user_prompt = montar_prompt_usuario(texto_oportunidade, perfil_empresa)

    response = client.chat.completions.create(
        model=modelo,
        temperature=0.2,
        max_tokens=950,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANALISTA},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_content = (response.choices[0].message.content or "").strip()
    limpo = _limpar_json_bruto(raw_content)

    try:
        parsed_dict = json.loads(limpo)
        validado = RelatorioTecnicoLicitacao.model_validate(parsed_dict)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Falha ao validar JSON do relatório técnico: {exc}\nSaída bruta:\n{raw_content}") from exc

    uso_api = getattr(response, "usage", None)
    prompt_tokens = int(getattr(uso_api, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(uso_api, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(uso_api, "total_tokens", prompt_tokens + completion_tokens) or 0)

    return {
        "dados": validado.model_dump(),
        "json_bruto": json.dumps(validado.model_dump(), ensure_ascii=False, indent=2),
        "uso": {
            "modo": "REAL",
            "modelo": modelo,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "custo_estimado_usd": _estimar_custo_usd(prompt_tokens, completion_tokens),
        },
    }
