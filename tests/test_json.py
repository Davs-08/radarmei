from buscador import buscar_oportunidades_multiportal
from llm import analisar_oportunidade


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
    assert resultado["uso"]["modo"] == "MOCK"


def test_buscador_multiportal_retorna_lista():
    itens, logs = buscar_oportunidades_multiportal(uf="PE", palavra_chave="informatica")
    assert isinstance(itens, list)
    assert len(itens) >= 1
    assert isinstance(logs, list)
