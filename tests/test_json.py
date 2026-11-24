from llm import analisar_oportunidade


def test_retorno_json_valido_em_modo_mock(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "1")
    resultado = analisar_oportunidade("Dispensa para aquisição de água mineral.")

    dados = resultado["dados"]
    assert isinstance(dados, dict)
    for chave in [
        "titulo_comercial",
        "categoria_negocio",
        "resumo_simples",
        "compatibilidade_mei",
        "motivo_compatibilidade",
        "prazo_ou_entrega",
        "checklist_inicial",
        "alerta_risco",
    ]:
        assert chave in dados
    assert isinstance(dados["checklist_inicial"], list)
    assert resultado["uso"]["modo"] == "MOCK"
