import os
import streamlit as st
from dotenv import load_dotenv

from llm import analisar_oportunidade
from prompts import EXEMPLOS_PNCP

load_dotenv()

st.set_page_config(
    page_title="RadarMEI — IA para Licitações",
    page_icon="📡",
    layout="wide",
)

st.title("📡 RadarMEI")
st.caption("Tradutor inteligente de compras públicas e editais para Microempreendedores Individuais (MEI)")

st.info(
    "🤖 **Aviso de Transparência e Ética:** Esta aplicação utiliza Inteligência Artificial para "
    "apoiar a leitura e triagem inicial de oportunidades. Não substitui a leitura integral do edital "
    "oficial nem orientação jurídica/contábil. Evite inserir dados pessoais sensíveis."
)

if "texto_entrada" not in st.session_state:
    st.session_state["texto_entrada"] = list(EXEMPLOS_PNCP.values())[0]

st.subheader("Exemplos rápidos do PNCP")
cols = st.columns(len(EXEMPLOS_PNCP))
for idx, (rotulo, texto_exemplo) in enumerate(EXEMPLOS_PNCP.items()):
    if cols[idx].button(rotulo, use_container_width=True):
        st.session_state["texto_entrada"] = texto_exemplo
        st.rerun()

texto_usuario = st.text_area(
    "Cole aqui o objeto, descrição ou trecho do edital / dispensa eletrônica:",
    value=st.session_state["texto_entrada"],
    height=140,
)

modo_atual = (
    "Simulado (LLM_MOCK=1)"
    if os.getenv("LLM_MOCK", "1").strip() == "1"
    else f"API Real ({os.getenv('LLM_MODEL', 'gemini-3.5-flash-lite')})"
)
st.caption(f"Modo atual: **{modo_atual}**")

if st.button("Analisar oportunidade", type="primary"):
    try:
        with st.spinner("Analisando oportunidade e validando JSON..."):
            resultado = analisar_oportunidade(texto_usuario)

        dados = resultado["dados"]
        uso = resultado["uso"]

        st.divider()
        st.subheader(dados["titulo_comercial"])
        st.write(
            f"**Categoria:** {dados['categoria_negocio']} | "
            f"**Compatibilidade MEI:** {dados['compatibilidade_mei']}"
        )
        st.write(dados["resumo_simples"])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Por que essa classificação?")
            st.write(dados["motivo_compatibilidade"])
            st.markdown("### Prazo ou entrega")
            st.write(dados["prazo_ou_entrega"])

        with col2:
            st.markdown("### Checklist inicial")
            for item in dados["checklist_inicial"]:
                st.write(f"- {item}")
            st.warning(f"⚠️ **Alerta de risco:** {dados['alerta_risco']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tokens de entrada", uso.get("prompt_tokens", 0))
        c2.metric("Tokens de saída", uso.get("completion_tokens", 0))
        c3.metric("Total de tokens", uso.get("total_tokens", 0))
        c4.metric("Custo est. (USD)", f"")

        with st.expander("🧾 JSON estruturado parseado"):
            st.code(resultado["json_bruto"], language="json")

    except Exception as e:
        st.error(f"Erro ao processar análise: {e}")
