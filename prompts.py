SYSTEM_PROMPT = """
Você é o RadarMEI, um assistente de IA especializado em traduzir descrições de compras públicas
(como dispensas eletrônicas e editais do PNCP) para linguagem simples e prática voltada a
Microempreendedores Individuais (MEI) e pequenos negócios locais.

Regras obrigatórias:
1. Responda EXCLUSIVAMENTE com um objeto JSON válido. Não use blocos markdown `json nem texto fora do JSON.
2. Traduza termos burocráticos e técnicos para linguagem clara, direta e acolhedora.
3. Avalie a compatibilidade com o perfil MEI considerando complexidade, escopo e possíveis riscos operacionais
   (ex.: frete, prazo curto, exigências técnicas ou documentais).
4. Nunca invente valores ou prazos que não estejam no texto; se não houver informação clara, use "Não informado no texto".
5. Inclua sempre um alerta prático de risco e lembrete de conferência do edital oficial.

Formato exato do JSON de saída:
{
  "titulo_comercial": "string",
  "categoria_negocio": "string",
  "resumo_simples": "string",
  "compatibilidade_mei": "ALTA | MEDIA | BAIXA",
  "motivo_compatibilidade": "string",
  "prazo_ou_entrega": "string",
  "checklist_inicial": ["string"],
  "alerta_risco": "string"
}
"""

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": (
            "Contratação direta para aquisição de garrafões de água mineral natural "
            "de 20 litros (sem vasilhame), entrega parcelada semanalmente na sede "
            "administrativa municipal, valor estimado R$ 6.800,00."
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{"titulo_comercial": "Entrega semanal de água mineral (20L) para a prefeitura", '
            '"categoria_negocio": "Água e Bebidas / Distribuição Local", '
            '"resumo_simples": "O órgão quer comprar água mineral em galões de 20L com entrega '
            'toda semana, sem precisar fornecer os galões vazios.", '
            '"compatibilidade_mei": "ALTA", '
            '"motivo_compatibilidade": "Demanda recorrente de baixo valor e operação simples para '
            'quem já atua com entregas locais.", '
            '"prazo_ou_entrega": "Entrega parcelada semanalmente na sede administrativa", '
            '"checklist_inicial": ["Verificar CND Federal, Estadual e Municipal", '
            '"Confirmar capacidade de entrega semanal no endereço indicado", '
            '"Calcular custo de deslocamento e margem no valor estimado"], '
            '"alerta_risco": "Atenção ao custo de rota semanal para não perder margem com combustível '
            'e sempre confira o edital/aviso oficial antes de enviar lance."}'
        ),
    },
]

EXEMPLOS_PNCP = {
    "Compra de lanches / coffee break": (
        "Dispensa eletrônica visando o fornecimento eventual e parcelado de kits de lanche "
        "e coffee break para eventos de capacitação de servidores públicos, contendo salgados "
        "assados, sucos naturais e café coado, conforme Termo de Referência."
    ),
    "Manutenção de climatização": (
        "Contratação de serviço especializado de manutenção preventiva e corretiva em aparelhos "
        "de ar-condicionado tipo split, incluindo limpeza de filtros e verificação de carga de gás, "
        "em unidades administrativas municipais."
    ),
    "Material de escritório e papelaria": (
        "Aquisição de materiais de expediente e papelaria, tais como resmas de papel A4, canetas "
        "esferográficas, pastas arquivo e toners compatíveis, com entrega única em até 10 dias "
        "corridos após emissão da ordem de fornecimento."
    ),
}
