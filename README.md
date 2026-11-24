# 📡 RadarMEI — IA para Tradução e Triagem de Compras Públicas

Projeto desenvolvido por **Davi Monteiro** para apoiar **Microempreendedores Individuais (MEI)** e pequenos negócios locais na leitura, triagem inicial e análise de viabilidade de oportunidades de compras públicas (como dispensas eletrônicas, cotações e editais do PNCP, Compras.gov.br e Diários Oficiais).

- **Autor:** Davi Monteiro
- **Repositório:** [https://github.com/Davs-08/radarmei](https://github.com/Davs-08/radarmei)
- **Vídeo Demonstração (até 2 min):** `[INSIRA_AQUI_O_LINK_DO_VIDEO_DEMO]`

---

## 1. Problema, Público-Alvo e Impacto Local
Órgãos públicos publicam diariamente oportunidades de compra e contratação com linguagem burocrática e técnica. Muitos MEIs e pequenos empreendedores locais deixam de participar — ou correm riscos operacionais e financeiros (como prazos curtos, frete não calculado ou exigências fora do escopo) — por dificuldade de interpretar rapidamente o que está sendo pedido.

O **RadarMEI** realiza a busca multi-portal (PNCP, Compras.gov.br e Diários Oficiais via Querido Diário), permite colar textos ou enviar PDFs de editais, separa rigorosamente `system` e `user` prompt na chamada à LLM com blindagem contra *prompt injection*, devolve um **JSON estruturado e validado com Pydantic** em linguagem simples, gera um checklist prático, simula a margem líquida real e exibe a telemetria de tokens e custo estimado.

---

## 2. Arquitetura do Projeto
- `app.py`: Interface web em Streamlit com radar multi-portal, análise de texto/PDF, relatório técnico, simulador de viabilidade financeira e telemetria de tokens/custo.
- `llm.py`: Integração com API compatível com OpenAI (`gemini-3.5-flash-lite` por padrão, `temperature=0.2`, `LLM_MAX_TOKENS=1800`), validação estrita via `AnaliseLicitacao` (Pydantic), tentativa automática de reparo em caso de falha/truncamento e modo simulado (`LLM_MOCK=1`).
- `prompts.py`: Engenharia de prompt com separação `SYSTEM_PROMPT` / `montar_user_prompt`, exemplo *few-shot* completo, delimitadores de texto não confiável (`<<<INICIO_TEXTO_NAO_CONFIAVEL>>>`) e instrução explícita anti-alucinação (`"Não informado no texto"`).
- `buscador.py`: Consulta ao PNCP, Compras.gov.br e Querido Diário, normalização de acentos, detecção de match exato, fallback transparente para dados de exemplo (`usou_exemplo=True`) e extração de texto de PDF (`pypdf`, limite de 8.000 caracteres).
- `exemplos/`: Três exemplos de oportunidades/editais em `.txt` para demonstração e validação.
- `tests/`: Testes automatizados com `pytest` cobrindo schema Pydantic, modo mock, sanitização de JSON, match de materiais e fallback do buscador.

---

## 3. Como Rodar Localmente

1. Clone o repositório e acesse a pasta do projeto:
   ```bash
   git clone [https://github.com/Davs-08/radarmei.git](https://github.com/Davs-08/radarmei.git)
   cd radarmei