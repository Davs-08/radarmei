from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from buscador import buscar_oportunidades_multiportal
from llm import AnaliseLicitacao, _limpar_json_bruto, analisar_oportunidade


def test_limpar_json_bruto_remove_cercas_tres_crases():
    bruto = '```json\n{"titulo_comercial": "Teste"}\n```'
    assert _limpar_json_bruto(bruto) == '{"titulo_comercial": "Teste"}'


def test_schema_pydantic_valida_e_rejeita_enum_invalido():
    payload_valido = {
        "titulo_comercial": "Dispensa Eletrônica — Material de TI",
        "aderencia_empresa": "Alta",
        "recomendacao_decisao": "Participar",
        "resumo_executivo": "Aquisição de suprimentos de informática com entrega rápida.",
        "justificativa_aderencia": "Compatível com o ramo e porte informados.",
        "escopo_e_exigencias": ["Entrega em 5 dias úteis: Não informado no texto quanto ao local exato."],
        "matriz_riscos": ["Risco: Atraso na entrega. | Mitigação: Confirmar estoque antes do lance."],
        "checklist_participacao": ["Ler o edital oficial na íntegra"],
        "parecer_financeiro_e_acao": "Simular margem líquida antes de enviar proposta.",
    }
    modelo = AnaliseLicitacao.model_validate(payload_valido)
    assert modelo.aderencia_empresa == "Alta"

    payload_invalido = dict(payload_valido, aderencia_empresa="Altíssima")
    with pytest.raises(ValidationError):
        AnaliseLicitacao.model_validate(payload_invalido)


def test_retorno_relatorio_tecnico_valido_em_modo_mock(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "1")
    resultado = analisar_oportunidade(
        "Dispensa para aquisição de notebooks e periféricos.",
        perfil_empresa={"ramo": "informatica", "uf": "PE", "porte": "MEI", "margem_minima_pct": 20},
    )

    dados = resultado["dados"]
    assert isinstance(dados, dict)
    for chave in [
        "titulo_comercial",
        "resumo_executivo",
        "aderencia_empresa",
        "justificativa_aderencia",
        "escopo_e_exigencias",
        "matriz_riscos",
        "checklist_participacao",
        "recomendacao_decisao",
        "parecer_financeiro_e_acao",
    ]:
        assert chave in dados
    assert isinstance(dados["escopo_e_exigencias"], list)
    assert isinstance(dados["matriz_riscos"], list)
    assert isinstance(dados["checklist_participacao"], list)
    assert resultado["uso"]["modo"].lower() == "mock"
    assert json.loads(resultado["json_bruto"])["titulo_comercial"] == dados["titulo_comercial"]


def test_buscador_multiportal_retorna_lista_e_flag_exemplo():
    itens, logs, usou_exemplo = buscar_oportunidades_multiportal(uf="PE", palavra_chave="informatica")
    assert isinstance(itens, list)
    assert isinstance(logs, list)
    assert isinstance(usou_exemplo, bool)
    assert len(itens) > 0