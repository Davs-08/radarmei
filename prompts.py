SYSTEM_PROMPT_ANALISTA = """
Você é um Analista Sênior de Licitações e Captação de Oportunidades Públicas atuando como funcionário dedicado da empresa do usuário.
Sua missão é analisar editais, dispensas eletrônicas, avisos de contratação ou trechos de Termo de Referência e gerar um RELATÓRIO TÉCNICO objetivo, prático e confiável para subsidiar a decisão de participação da empresa.

Regras obrigatórias:
1. Baseie-se estritamente no texto fornecido e no perfil da empresa informado. Não invente prazos, valores, exigências técnicas ou documentos que não estejam no texto; quando algo não constar, escreva explicitamente "Não informado no texto".
2. Avalie com franqueza se a oportunidade faz sentido para a empresa (aderência ALTA, MÉDIA ou BAIXA) e aponte riscos reais (logística/frete, margem, prazo, exigências técnicas, documentação ou ambiguidade do edital).
3. Lembre sempre que a análise apoia a triagem e preparação, não substituindo a leitura integral do edital oficial nem orientação jurídica ou contábil.
4. Responda EXCLUSIVAMENTE com um objeto JSON válido contendo exatamente estas chaves:
   - "titulo_comercial": string curta e clara
   - "resumo_executivo": string traduzindo o objeto e o contexto da contratação
   - "aderencia_empresa": "ALTA" | "MÉDIA" | "BAIXA"
   - "justificativa_aderencia": string objetiva explicando o match ou desalinhamento com a empresa
   - "escopo_e_exigencias": lista de strings com itens do escopo, prazos, local/entrega ou lacunas do texto
   - "matriz_riscos": lista de strings com riscos operacionais, financeiros ou documentais identificados
   - "checklist_participacao": lista de strings com ações práticas e documentos a conferir antes de lançar proposta
   - "recomendacao_decisao": "PARTICIPAR" | "AVALIAR COM RESSALVAS" | "DESCARTAR"
   - "parecer_financeiro_e_acao": string com leitura de viabilidade/margem e próximo passo imediato
"""

EXEMPLOS_OPORTUNIDADES = {
    "Dispensa — Material de Escritório e TI": (
        "Órgão: Prefeitura Municipal — Dispensa Eletrônica | Valor estimado: R$ 18.500,00 | "
        "Prazo de entrega: até 5 dias úteis após ordem de fornecimento. "
        "Objeto: Aquisição de resmas de papel A4, toners, mouses USB, teclados e cabos de rede "
        "para atendimento das secretarias municipais."
    ),
    "Serviço — Manutenção de Climatização": (
        "Órgão: Secretaria Estadual de Saúde — Dispensa Eletrônica | Valor estimado: R$ 29.400,00 | "
        "Vigência: 6 meses. Objeto: Manutenção preventiva e corretiva em aparelhos de ar-condicionado "
        "split e piso-teto, limpeza de filtros e emissão de relatório técnico mensal."
    ),
    "Pregão — Fornecimento de Lanches / Coffee Break": (
        "Órgão: Instituto Federal — Pregão Eletrônico | Valor estimado: R$ 64.000,00 | "
        "Objeto: Fornecimento parcelado de kits de lanche e coffee break para eventos institucionais "
        "com montagem no local e exigência de alvará sanitário vigente."
    ),
}


def montar_prompt_usuario(
    texto_oportunidade: str,
    perfil_empresa: dict | None = None,
) -> str:
    perfil = perfil_empresa or {}
    ramo = perfil.get("ramo") or "Não especificado"
    uf = perfil.get("uf") or "Não especificada"
    porte = perfil.get("porte") or "MEI / Pequena Empresa"
    margem_min = perfil.get("margem_minima_pct")
    margem_txt = f"{margem_min:.0f}%" if isinstance(margem_min, (int, float)) else "Não informada"

    return (
        "=== PERFIL DA EMPRESA CLIENTE ===\n"
        f"- Porte / Enquadramento: {porte}\n"
        f"- Ramo / Atuação / Palavras-chave: {ramo}\n"
        f"- UF / Região de atuação: {uf}\n"
        f"- Margem líquida mínima desejada: {margem_txt}\n\n"
        "=== DADOS DA OPORTUNIDADE / EDITAL / TRECHO ===\n"
        f"{texto_oportunidade.strip()}\n\n"
        "Gere o relatório técnico estruturado em JSON conforme as instruções do sistema."
    )
