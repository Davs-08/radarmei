# RadarMEI — IA para Traducao e Triagem de Compras Publicas

Projeto desenvolvido para apoiar **Microempreendedores Individuais (MEI)** e pequenos negocios locais na leitura e triagem inicial de oportunidades de compras publicas (como dispensas eletronicas e editais do PNCP).

## 1. Problema e Publico-Alvo
Orgaos publicos publicam diariamente oportunidades de compra e contratacao com linguagem burocratica e tecnica. Muitos MEIs e pequenos empreendedores locais deixam de participar — ou correm riscos operacionais (como prazos curtos, frete nao calculado ou exigencias fora do escopo) — por dificuldade de interpretar rapidamente o que esta sendo pedido.

O **RadarMEI** le a descricao ou trecho da oportunidade, separa system e user na chamada a LLM, devolve um **JSON estruturado e validado** em linguagem simples, classifica a compatibilidade inicial com o perfil MEI, gera um checklist pratico e exibe a telemetria de tokens e custo estimado.

## 2. Como Rodar Localmente

1. Clone o repositorio e acesse a pasta do projeto:
   git clone URL_DO_SEU_REPOSITORIO
   cd radarmei

2. Crie e ative o ambiente virtual:
   python -m venv venv
   .\venv\Scripts\Activate.ps1

3. Instale as dependencias:
   pip install -r requirements.txt

4. Configure as variaveis de ambiente (nunca commite o .env):
   Copy-Item .env.example .env

   Edite o .env preenchendo LLM_API_KEY, LLM_BASE_URL, LLM_MODEL e LLM_MOCK (1 para modo simulado sem consumo de tokens, 0 para chamada real a API).

5. Execute os testes automatizados:
   python -m pytest -p no:cacheprovider

6. Inicie a aplicacao web (Streamlit):
   streamlit run app.py

## 3. Controle de Tokens e Estimativa de Custo
- O projeto suporta LLM_MOCK=1 (0 tokens) para testes locais e LLM_MOCK=0 para consumo real via API compativel com OpenAI (gemini-3.5-flash-lite com temperature=0.2 e limite de max_tokens=700).
- Em uma execucao real tipica (cerca de 600 tokens de entrada e 220-260 tokens de saida, totalizando ~830-900 tokens), o custo estimado por analise e na ordem de fracoes de centavo de dolar (~US$ 0,00015 a US$ 0,00017 por consulta, usando precos ilustrativos de referencia por 1M de tokens).

## 4. Etica, Limitaçoes e LGPD
- Transparencia: A interface informa explicitamente que as respostas sao geradas por Inteligencia Artificial.
- Limitacoes e alucinacao: A IA pode errar ou omitir nuances de um edital completo. A ferramenta nao substitui a leitura integral do documento oficial no portal de compras publicas nem orientacao juridica ou contabil.
- Privacidade / LGPD: O sistema nao exige cadastro de dados pessoais e orienta o usuario a nao inserir dados sensiveis ou sigilosos.

## 5. Declaracao de Uso de IA
Ferramentas de Inteligencia Artificial foram utilizadas como apoio na estruturacao da arquitetura, elaboracao de prompts, escrita/refatoracao de codigo e revisao da documentacao, com validacao tecnica, testes e revisao manual do autor.

## 6. Prints / Demonstracao
Adicione aqui o print da tela do RadarMEI em execucao e/ou o link do video demo de ate 2 minutos.
