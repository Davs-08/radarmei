import html
import json
import os
import time
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from buscador import (
    ESTADOS_BRASIL,
    buscar_oportunidades_multiportal,
    enviar_notificacao_telegram,
    extrair_texto_pdf,
    gerar_links_portais_externos,
)
from llm import analisar_oportunidade
from prompts import EXEMPLOS_OPORTUNIDADES

load_dotenv()

st.set_page_config(
    page_title="RadarMEI — Analista de Licitações com IA",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --hig-font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, sans-serif;
        --hig-secondary: #86868B;
        --hig-border: rgba(120, 120, 128, 0.18);
        --hig-surface: rgba(255, 255, 255, 0.72);
        --hig-surface-dark: rgba(28, 28, 30, 0.68);
        --hig-accent: #007AFF;
        --hig-green: #34C759;
    }

    html, body, [class*="css"] {
        font-family: var(--hig-font) !important;
        -webkit-font-smoothing: antialiased;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1180px;
    }

    section[data-testid="stSidebar"] {
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-right: 1px solid var(--hig-border);
    }

    .hig-hero {
        background: var(--hig-surface);
        backdrop-filter: blur(18px) saturate(160%);
        -webkit-backdrop-filter: blur(18px) saturate(160%);
        border: 1px solid var(--hig-border);
        border-radius: 20px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.1rem;
    }

    @media (prefers-color-scheme: dark) {
        .hig-hero {
            background: var(--hig-surface-dark);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }
    }

    .hig-title {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }

    .hig-subtitle {
        color: var(--hig-secondary);
        font-size: 0.96rem;
        font-weight: 400;
        margin: 0;
        line-height: 1.45;
    }

    .card-oportunidade {
        border: 1px solid var(--hig-border);
        border-radius: 18px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 0.8rem;
        background: var(--hig-surface);
        backdrop-filter: blur(14px) saturate(150%);
        -webkit-backdrop-filter: blur(14px) saturate(150%);
        box-shadow: 0 6px 22px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    @media (prefers-color-scheme: dark) {
        .card-oportunidade {
            background: var(--hig-surface-dark);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
        }
    }

    .card-match {
        border: 1px solid rgba(52, 199, 89, 0.55);
        box-shadow: 0 8px 26px rgba(52, 199, 89, 0.08);
    }

    .card-meta {
        color: var(--hig-secondary);
        font-size: 0.84rem;
        margin-top: 0.35rem;
        line-height: 1.4;
    }

    .card-objeto {
        font-size: 0.95rem;
        line-height: 1.5;
        margin-top: 0.65rem;
        margin-bottom: 0.1rem;
    }

    .badge {
        display: inline-block;
        padding: 0.22rem 0.72rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        margin-right: 0.4rem;
        margin-bottom: 0.25rem;
    }

    .badge-portal {
        background-color: rgba(0, 122, 255, 0.12);
        color: #007AFF;
        border: 1px solid rgba(0, 122, 255, 0.22);
    }

    .badge-match {
        background-color: rgba(52, 199, 89, 0.14);
        color: #1e8e3e;
        border: 1px solid rgba(52, 199, 89, 0.32);
    }

    @media (prefers-color-scheme: dark) {
        .badge-portal {
            background-color: rgba(10, 132, 255, 0.2);
            color: #64D2FF;
        }
        .badge-match {
            background-color: rgba(52, 199, 89, 0.2);
            color: #6EE787;
        }
    }

    /* Botões estilo pílula inspirados no iOS/macOS */
    div.stButton > button,
    div.stLinkButton > a,
    div.stDownloadButton > button {
        border-radius: 999px !important;
        font-weight: 500 !important;
        padding: 0.45rem 1.05rem !important;
        border: 1px solid var(--hig-border) !important;
        transition: all 0.15s ease !important;
    }

    div.stButton > button[kind="primary"] {
        background-color: var(--hig-accent) !important;
        border-color: var(--hig-accent) !important;
        color: #FFFFFF !important;
    }

    div[data-testid="stMetric"] {
        background: var(--hig-surface);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid var(--hig-border);
        border-radius: 16px;
        padding: 0.85rem 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
    }

    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background: var(--hig-surface-dark);
        }
    }

    @media (max-width: 768px) {
        .hig-title {
            font-size: 1.42rem;
        }
        .card-oportunidade {
            border-radius: 16px;
            padding: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "oportunidades" not in st.session_state:
    st.session_state["oportunidades"] = []
if "logs_busca" not in st.session_state:
    st.session_state["logs_busca"] = []
if "usou_exemplo" not in st.session_state:
    st.session_state["usou_exemplo"] = False
if "assinatura_busca" not in st.session_state:
    st.session_state["assinatura_busca"] = ""
if "ids_notificados" not in st.session_state:
    st.session_state["ids_notificados"] = set()
if "ultimo_check_ts" not in st.session_state:
    st.session_state["ultimo_check_ts"] = time.time()
if "relatorio_atual" not in st.session_state:
    st.session_state["relatorio_atual"] = None
if "contexto_analisado" not in st.session_state:
    st.session_state["contexto_analisado"] = None

OPCOES_INTERVALO_MIN = [240, 60, 30, 15, 5]


def _formatar_intervalo(minutos: int) -> str:
    if minutos == 240:
        return "A cada 4 horas (Padrão)"
    if minutos % 60 == 0:
        return f"A cada {minutos // 60}h"
    return f"A cada {minutos} min"


def _formatar_tempo_restante(segundos: int) -> str:
    seg = max(0, int(segundos))
    horas = seg // 3600
    mins = (seg % 3600) // 60
    r_seg = seg % 60
    if horas > 0:
        return f"{horas}h {mins:02d}m {r_seg:02d}s"
    return f"{mins:02d}m {r_seg:02d}s"


with st.sidebar:
    st.header("Perfil & Filtros")
    st.caption("Configure a empresa e clique em Atualizar Busca Agora.")

    porte = st.selectbox(
        "Porte / Enquadramento",
        ["MEI", "ME (Microempresa)", "EPP (Empresa de Pequeno Porte)"],
        index=0,
    )
    ramo = st.text_input(
        "Ramo / Palavras-chave",
        value="informatica",
        placeholder="Ex: informatica, papelaria, toner",
    )
    material_exato = st.text_input(
        "Material / Item exato para alerta",
        value="",
        placeholder="Ex: papel a4, tablet, notebook",
    )

    todos_estados = st.checkbox("Sem filtro de UF (todos os estados)", value=False)
    ufs_selecionadas = st.multiselect(
        "Estados (UF)",
        options=ESTADOS_BRASIL,
        default=["PE"],
        disabled=todos_estados,
        placeholder="Escolha um ou mais estados",
    )

    margem_minima = st.slider("Margem líquida mínima (%)", min_value=5, max_value=60, value=20, step=5)
    dias_busca = st.selectbox(
        "Janela de publicação",
        [3, 7, 15, 30],
        index=1,
        format_func=lambda d: f"Últimos {d} dias",
    )

    st.divider()
    st.subheader("Alertas & Frequência")
    busca_automatica = st.toggle("Buscar ao alterar configurações", value=False)
    monitoramento_continuo = st.toggle("Monitorar em segundo plano", value=False)
    intervalo_min = st.selectbox(
        "Frequência da busca automática",
        OPCOES_INTERVALO_MIN,
        index=0,
        format_func=_formatar_intervalo,
    )
    notificar_navegador = st.checkbox("Alerta no navegador ao achar match", value=True)

    with st.expander("Telegram (opcional)"):
        tg_token = st.text_input("Bot Token", type="password", value=os.getenv("TELEGRAM_BOT_TOKEN", ""))
        tg_chat_id = st.text_input("Chat ID", value=os.getenv("TELEGRAM_CHAT_ID", ""))

    st.divider()
    modo_mock = os.getenv("LLM_MOCK", "1").strip() == "1"
    modelo_atual = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    if modo_mock:
        st.caption("🧪 Modo simulado ativo (`LLM_MOCK=1`) · 0 tokens")
    else:
        st.caption(f"⚡ API ativa · `{modelo_atual}`")

ufs_efetivas = [] if todos_estados else (ufs_selecionadas or ["PE"])
rotulo_ufs = "Sem filtro de UF" if todos_estados else ", ".join(ufs_efetivas)

perfil_empresa = {
    "porte": porte,
    "ramo": ramo,
    "material_exato": material_exato,
    "ufs": ufs_efetivas,
    "uf": rotulo_ufs,
    "margem_minima_pct": margem_minima,
}


def _disparar_varredura_e_notificacoes(forcar_notificacao: bool = False):
    st.session_state["ultimo_check_ts"] = time.time()
    with st.spinner("Consultando fontes públicas e aplicando filtros..."):
        itens, logs, usou_ex = buscar_oportunidades_multiportal(
            uf=ufs_efetivas,
            palavra_chave=ramo,
            material_exato=material_exato,
            dias_atras=dias_busca,
            limite_total=20,
            todos_estados=todos_estados,
        )
    st.session_state["oportunidades"] = itens
    st.session_state["logs_busca"] = logs
    st.session_state["usou_exemplo"] = usou_ex

    matches_exatos = [op for op in itens if op.get("match_exato")]
    novos_matches = []
    for op in matches_exatos:
        op_id = str(op.get("id") or f"{op.get('orgao')}|{op.get('objeto')[:40]}")
        if forcar_notificacao or op_id not in st.session_state["ids_notificados"]:
            st.session_state["ids_notificados"].add(op_id)
            novos_matches.append(op)

    if novos_matches:
        st.toast(
            f"🎯 {len(novos_matches)} oportunidade(s) com match para '{material_exato or ramo}' ({rotulo_ufs}).",
            icon="🔔",
        )
        if notificar_navegador:
            titulo_js = json.dumps(f"RadarMEI: {len(novos_matches)} match(es) encontrado(s)")
            corpo_js = json.dumps(f"{novos_matches[0].get('orgao', '')} — {novos_matches[0].get('objeto', '')[:120]}")
            components.html(
                f"""
                <script>
                if ("Notification" in window) {{
                    if (Notification.permission === "granted") {{
                        new Notification({titulo_js}, {{ body: {corpo_js} }});
                    }} else if (Notification.permission !== "denied") {{
                        Notification.requestPermission().then(function(perm) {{
                            if (perm === "granted") {{
                                new Notification({titulo_js}, {{ body: {corpo_js} }});
                            }}
                        }});
                    }}
                }}
                </script>
                """,
                height=0,
            )
        if tg_token and tg_chat_id:
            linhas_tg = [f"🔔 *RadarMEI — Match de Material ({rotulo_ufs})*"]
            for op in novos_matches[:5]:
                linhas_tg.append(f"• {op.get('orgao')} ({op.get('portal')}): {op.get('objeto')[:140]}")
            ok_tg, msg_tg = enviar_notificacao_telegram(tg_token, tg_chat_id, "\n".join(linhas_tg))
            st.session_state["logs_busca"].append(f"{'📲' if ok_tg else '⚠️'} {msg_tg}")


assinatura_atual = f"{porte}|{ramo}|{material_exato}|{todos_estados}|{','.join(ufs_efetivas)}|{dias_busca}"
if busca_automatica and assinatura_atual != st.session_state["assinatura_busca"]:
    st.session_state["assinatura_busca"] = assinatura_atual
    _disparar_varredura_e_notificacoes(forcar_notificacao=False)

st.markdown(
    """
    <div class="hig-hero">
        <h1 class="hig-title">RadarMEI</h1>
        <p class="hig-subtitle">Triagem inteligente de compras públicas, análise estruturada de editais e simulação de margem para MEIs.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Transparência e Ética: relatórios gerados por IA para triagem inicial; não substituem a leitura integral do edital oficial "
    "nem assessoria jurídica ou contábil. Não insira dados pessoais sensíveis."
)

aba_radar, aba_manual, aba_relatorio = st.tabs([
    "Radar de Oportunidades",
    "Analisar Edital / PDF",
    "Relatório & Viabilidade",
])


def _executar_analise(texto_completo: str, metadados: dict | None = None):
    with st.spinner("Avaliando escopo, aderência, riscos e viabilidade..."):
        resultado = analisar_oportunidade(texto_completo, perfil_empresa=perfil_empresa)
    st.session_state["relatorio_atual"] = resultado
    st.session_state["contexto_analisado"] = metadados or {
        "valor_estimado": 0.0,
        "orgao": "Análise Direta",
        "portal": "Texto / PDF",
    }


with aba_radar:
    c_btn, c_status = st.columns([2, 3])
    with c_btn:
        if st.button("Atualizar Busca Agora", type="primary", use_container_width=True):
            st.session_state["assinatura_busca"] = assinatura_atual
            _disparar_varredura_e_notificacoes(forcar_notificacao=True)
    with c_status:
        if monitoramento_continuo:
            restante = (intervalo_min * 60) - (time.time() - st.session_state["ultimo_check_ts"])
            st.caption(f"Monitoramento ativo ({_formatar_intervalo(intervalo_min)}) · próxima em {_formatar_tempo_restante(restante)}")
        else:
            st.caption(f"Monitoramento contínuo desligado · padrão: {_formatar_intervalo(intervalo_min)}")

    if st.session_state["usou_exemplo"]:
        st.warning(
            "**Dados de exemplo:** As fontes externas não retornaram itens agora ou ficaram indisponíveis; "
            "os cartões exibidos abaixo são oportunidades fictícias de exemplo para demonstração."
        )

    oportunidades = st.session_state["oportunidades"]
    matches_exatos = [op for op in oportunidades if op.get("match_exato")]
    if matches_exatos:
        alvo_txt = material_exato.strip() or ramo.strip() or "critérios da empresa"
        st.success(
            f"**{len(matches_exatos)}** oportunidade(s) compatível(is) com "
            f"**{html.escape(alvo_txt)}** ({html.escape(rotulo_ufs)})."
        )

    if st.session_state["logs_busca"]:
        with st.expander("Log da varredura e notificações", expanded=False):
            for linha in st.session_state["logs_busca"]:
                st.write(linha)

    if oportunidades:
        st.subheader(f"Oportunidades ({len(oportunidades)})")
        for idx, op in enumerate(oportunidades):
            valor_fmt = (
                f"R$ {op['valor_estimado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if op.get("valor_estimado")
                else "Não divulgado"
            )
            eh_match = bool(op.get("match_exato"))
            classe_card = "card-oportunidade card-match" if eh_match else "card-oportunidade"
            termos_esc = ", ".join(html.escape(t) for t in (op.get("termos_encontrados") or []))
            badge_match = f'<span class="badge badge-match">Match · {termos_esc}</span>' if eh_match else ""

            portal_esc = html.escape(str(op.get("portal") or "Portal Público"))
            orgao_esc = html.escape(str(op.get("orgao") or ""))
            mun_esc = html.escape(str(op.get("municipio") or ""))
            uf_esc = html.escape(str(op.get("uf") or ""))
            mod_esc = html.escape(str(op.get("modalidade") or ""))
            val_esc = html.escape(valor_fmt)
            enc_esc = html.escape(str(op.get("encerramento") or ""))
            obj_esc = html.escape(str(op.get("objeto") or ""))
            local_txt = f"{mun_esc}/{uf_esc}" if mun_esc else uf_esc

            st.markdown(
                f"""
                <div class="{classe_card}">
                    {badge_match}
                    <span class="badge badge-portal">{portal_esc}</span>
                    <div style="font-weight: 600; font-size: 1.02rem; margin-top: 0.25rem;">
                        {orgao_esc} <span style="color: var(--hig-secondary); font-weight: 400;">· {local_txt}</span>
                    </div>
                    <div class="card-meta">
                        {mod_esc} · Estimado: <b>{val_esc}</b> · Encerramento: <b>{enc_esc}</b>
                    </div>
                    <p class="card-objeto">{obj_esc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns([2, 1])
            if b1.button(f"Gerar Relatório Técnico (#{idx+1})", key=f"btn_op_{idx}", use_container_width=True):
                texto_op = (
                    f"Portal: {op.get('portal')}\n"
                    f"Órgão: {op.get('orgao')} ({local_txt})\n"
                    f"Modalidade: {op.get('modalidade')}\n"
                    f"Valor estimado: {valor_fmt}\n"
                    f"Encerramento: {op.get('encerramento')}\n"
                    f"Objeto: {op.get('objeto')}"
                )
                try:
                    _executar_analise(texto_op, metadados=op)
                    st.success("Relatório pronto. Abra a aba **Relatório & Viabilidade**.")
                except Exception as exc:
                    st.error(f"Erro na análise: {exc}")
            link_url = str(op.get("link") or "")
            if link_url.startswith(("https://", "http://")):
                b2.link_button("Abrir portal", link_url, use_container_width=True)
    else:
        st.caption("Ajuste os filtros na barra lateral e clique em **Atualizar Busca Agora**.")

    st.divider()
    st.subheader("Portais externos")
    st.caption("Atalhos diretos com palavra-chave e estados selecionados:")
    links = gerar_links_portais_externos(material_exato or ramo, ufs_efetivas, todos_estados=todos_estados)
    cols_links = st.columns(4)
    for i, item_link in enumerate(links):
        cols_links[i % 4].link_button(item_link["portal"], item_link["url"], use_container_width=True)


with aba_manual:
    st.subheader("Edital / Termo de Referência (PDF ou Texto)")
    st.caption("Extração de PDF limitada a 8.000 caracteres. Não insira dados pessoais sensíveis.")
    arquivo_pdf = st.file_uploader("Upload de PDF do edital (opcional)", type=["pdf"])
    texto_pdf_extraido = ""
    if arquivo_pdf is not None:
        try:
            texto_pdf_extraido = extrair_texto_pdf(arquivo_pdf.read(), max_caracteres=8000)
            st.success(f"PDF lido ({len(texto_pdf_extraido)} caracteres extraídos).")
        except Exception as exc:
            st.error(f"Não foi possível ler o PDF: {exc}")

    ex_cols = st.columns(len(EXEMPLOS_OPORTUNIDADES))
    if "texto_manual" not in st.session_state:
        st.session_state["texto_manual"] = list(EXEMPLOS_OPORTUNIDADES.values())[0]
    for i, (rotulo, texto_ex) in enumerate(EXEMPLOS_OPORTUNIDADES.items()):
        if ex_cols[i].button(rotulo, use_container_width=True):
            st.session_state["texto_manual"] = texto_ex
            st.rerun()

    texto_base = texto_pdf_extraido if texto_pdf_extraido else st.session_state["texto_manual"]
    texto_para_analise = st.text_area("Conteúdo do edital / dispensa:", value=texto_base, height=200)

    if st.button("Gerar Dossiê Técnico Completo", type="primary"):
        try:
            _executar_analise(
                texto_para_analise,
                metadados={"valor_estimado": 0.0, "orgao": "Edital / PDF Enviado", "portal": "Upload / Colagem"},
            )
            st.success("Dossiê gerado. Abra a aba **Relatório & Viabilidade**.")
        except Exception as exc:
            st.error(f"Erro ao gerar relatório: {exc}")


with aba_relatorio:
    res = st.session_state["relatorio_atual"]
    ctx = st.session_state["contexto_analisado"] or {}
    if not res:
        st.caption("Nenhuma análise gerada ainda. Selecione uma oportunidade ou envie um edital.")
    else:
        dados = res["dados"]
        uso = res["uso"]
        st.subheader(dados["titulo_comercial"])
        st.caption(f"Origem: {ctx.get('portal', 'N/A')} · Órgão: {ctx.get('orgao', 'N/A')}")

        m1, m2, m3 = st.columns(3)
        m1.metric("Aderência", dados["aderencia_empresa"])
        m2.metric("Recomendação", dados["recomendacao_decisao"])
        m3.metric("Margem Alvo", f"{margem_minima}%")

        st.markdown("### Resumo Executivo")
        st.write(dados["resumo_executivo"])
        st.info(f"**Aderência:** {dados['justificativa_aderencia']}")

        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.markdown("### Escopo e Exigências")
            for item in dados["escopo_e_exigencias"]:
                st.write(f"- {item}")
            st.markdown("### Checklist")
            for idx_chk, item in enumerate(dados["checklist_participacao"]):
                st.checkbox(item, value=False, key=f"chk_{idx_chk}_{dados['titulo_comercial']}")
        with col_dir:
            st.markdown("### Matriz de Riscos")
            for risco in dados["matriz_riscos"]:
                st.warning(risco)
            st.markdown("### Parecer Financeiro e Próximo Passo")
            st.success(dados["parecer_financeiro_e_acao"])

        st.divider()
        st.markdown("### Simulador de Viabilidade Financeira")
        valor_ref = float(ctx.get("valor_estimado") or 10000.0)
        s1, s2, s3, s4 = st.columns(4)
        preco_proposta = s1.number_input("Proposta / teto (R$)", min_value=0.0, value=valor_ref, step=100.0)
        custo_produto = s2.number_input("Custo item/serviço (R$)", min_value=0.0, value=round(valor_ref * 0.65, 2), step=100.0)
        custo_frete = s3.number_input("Frete / logística (R$)", min_value=0.0, value=round(valor_ref * 0.08, 2), step=50.0)
        impostos_pct = s4.number_input("Impostos / taxas (%)", min_value=0.0, max_value=40.0, value=6.0, step=0.5)

        valor_impostos = preco_proposta * (impostos_pct / 100.0)
        lucro_liquido = preco_proposta - custo_produto - custo_frete - valor_impostos
        margem_real = (lucro_liquido / preco_proposta * 100.0) if preco_proposta > 0 else 0.0

        r1, r2, r3 = st.columns(3)
        r1.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        r2.metric("Margem Real", f"{margem_real:.1f}%", delta=f"{margem_real - margem_minima:.1f}% vs alvo")
        r3.metric("Viabilidade", "VIÁVEL" if margem_real >= margem_minima else "ABAIXO DO ALVO")

        relatorio_md = (
            f"# Relatório Técnico — {dados['titulo_comercial']}\n\n"
            f"- **Aderência:** {dados['aderencia_empresa']}\n"
            f"- **Recomendação:** {dados['recomendacao_decisao']}\n\n"
            f"## Resumo Executivo\n{dados['resumo_executivo']}\n\n"
            f"## Justificativa de Aderência\n{dados['justificativa_aderencia']}\n\n"
            f"## Escopo e Exigências\n" + "\n".join(f"- {x}" for x in dados["escopo_e_exigencias"]) + "\n\n"
            f"## Matriz de Riscos\n" + "\n".join(f"- {x}" for x in dados["matriz_riscos"]) + "\n\n"
            f"## Checklist de Participação\n" + "\n".join(f"- [ ] {x}" for x in dados["checklist_participacao"]) + "\n\n"
            f"## Parecer Financeiro e Próximo Passo\n{dados['parecer_financeiro_e_acao']}\n"
        )
        st.download_button(
            "Baixar Relatório (.md)",
            data=relatorio_md,
            file_name="relatorio_tecnico_licitacao.md",
            mime="text/markdown",
        )

        st.divider()
        custo_usd = float(uso.get("custo_estimado_usd", 0.0))
        custo_brl = custo_usd * 5.80
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Tokens entrada", uso.get("prompt_tokens", 0))
        t2.metric("Tokens saída", uso.get("completion_tokens", 0))
        t3.metric("Total tokens", uso.get("total_tokens", 0))
        t4.metric("Custo est. (USD / BRL)", f"${custo_usd:.5f} | R${custo_brl:.4f}")

        with st.expander("JSON estruturado validado"):
            st.code(res["json_bruto"], language="json")

if monitoramento_continuo:
    decorrido = time.time() - st.session_state["ultimo_check_ts"]
    espera = max(1, int(intervalo_min * 60 - decorrido))
    time.sleep(min(espera, 30))
    if time.time() - st.session_state["ultimo_check_ts"] >= intervalo_min * 60:
        _disparar_varredura_e_notificacoes(forcar_notificacao=False)
    st.rerun()