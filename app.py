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
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    .card-oportunidade {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
        background-color: rgba(255, 255, 255, 0.02);
    }
    .card-match {
        border: 1.5px solid #22c55e;
        background-color: rgba(34, 197, 94, 0.07);
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-portal { background-color: #1e3a8a; color: #dbeafe; }
    .badge-match { background-color: #14532d; color: #dcfce7; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "oportunidades" not in st.session_state:
    st.session_state["oportunidades"] = []
if "logs_busca" not in st.session_state:
    st.session_state["logs_busca"] = []
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


def _formatar_uf(uf_sigla: str) -> str:
    return "BR — Todos os Estados" if uf_sigla == "BR" else uf_sigla


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
    st.header("⚙️ Configurações & Perfil da Empresa")
    st.caption("Ajuste aqui para filtrar pela empresa e disparar busca + alerta automático.")

    porte = st.selectbox(
        "Porte / Enquadramento",
        ["MEI", "ME (Microempresa)", "EPP (Empresa de Pequeno Porte)"],
        index=0,
    )
    ramo = st.text_input(
        "Ramo / Palavras-chave da empresa",
        value="informatica",
        placeholder="Ex: informatica, papelaria, toner",
    )
    material_exato = st.text_input(
        "Material / Item exato para alerta",
        value="",
        placeholder="Ex: papel a4, tablet, notebook",
    )
    uf = st.selectbox(
        "Estado (UF) para pesquisa",
        ESTADOS_BRASIL,
        index=0,
        format_func=_formatar_uf,
    )
    margem_minima = st.slider("Margem líquida mínima (%)", min_value=5, max_value=60, value=20, step=5)
    dias_busca = st.selectbox(
        "Janela de publicação",
        [3, 7, 15, 30],
        index=1,
        format_func=lambda d: f"Últimos {d} dias",
    )

    st.divider()
    st.subheader("🔔 Notificação & Monitoramento")
    busca_automatica = st.toggle("Buscar ao alterar configurações", value=True)
    monitoramento_continuo = st.toggle("Monitorar automaticamente em segundo plano", value=True)
    intervalo_min = st.selectbox(
        "Frequência da busca automática",
        OPCOES_INTERVALO_MIN,
        index=0,
        format_func=_formatar_intervalo,
    )
    notificar_navegador = st.checkbox("Alerta no navegador ao achar material exato", value=True)

    with st.expander("Enviar também via Telegram (opcional)"):
        tg_token = st.text_input("Bot Token", type="password", value=os.getenv("TELEGRAM_BOT_TOKEN", ""))
        tg_chat_id = st.text_input("Chat ID", value=os.getenv("TELEGRAM_CHAT_ID", ""))

    st.divider()
    modo_mock = os.getenv("LLM_MOCK", "1").strip() == "1"
    modelo_atual = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    if modo_mock:
        st.warning("🧪 Modo Simulado (`LLM_MOCK=1`) — 0 tokens")
    else:
        st.success(f"⚡ API Real Ativa (`{modelo_atual}`)")

perfil_empresa = {
    "porte": porte,
    "ramo": ramo,
    "material_exato": material_exato,
    "uf": uf,
    "margem_minima_pct": margem_minima,
}


def _disparar_varredura_e_notificacoes(forcar_notificacao: bool = False):
    st.session_state["ultimo_check_ts"] = time.time()
    with st.spinner("Varrendo portais de compras públicas e filtrando pelo perfil da empresa..."):
        itens, logs = buscar_oportunidades_multiportal(
            uf=uf,
            palavra_chave=ramo,
            material_exato=material_exato,
            dias_atras=dias_busca,
            limite_total=20,
        )
    st.session_state["oportunidades"] = itens
    st.session_state["logs_busca"] = logs

    matches_exatos = [op for op in itens if op.get("match_exato")]
    novos_matches = []
    for op in matches_exatos:
        op_id = str(op.get("id") or f"{op.get('orgao')}|{op.get('objeto')[:40]}")
        if forcar_notificacao or op_id not in st.session_state["ids_notificados"]:
            st.session_state["ids_notificados"].add(op_id)
            novos_matches.append(op)

    if novos_matches:
        st.toast(f"🎯 {len(novos_matches)} oportunidade(s) com match para '{material_exato or ramo}' em {uf}!", icon="🔔")
        if notificar_navegador:
            titulo_notif = f"RadarMEI: {len(novos_matches)} match(es) encontrado(s)"
            corpo_notif = f"{novos_matches[0].get('orgao')} — {novos_matches[0].get('objeto')[:120]}"
            components.html(
                f"""
                <script>
                if ("Notification" in window) {{
                    if (Notification.permission === "granted") {{
                        new Notification({titulo_notif!r}, {{ body: {corpo_notif!r} }});
                    }} else if (Notification.permission !== "denied") {{
                        Notification.requestPermission().then(function(perm) {{
                            if (perm === "granted") {{
                                new Notification({titulo_notif!r}, {{ body: {corpo_notif!r} }});
                            }}
                        }});
                    }}
                }}
                </script>
                """,
                height=0,
            )
        if tg_token and tg_chat_id:
            linhas_tg = [f"🔔 *RadarMEI — Match de Material ({uf})*"]
            for op in novos_matches[:5]:
                linhas_tg.append(f"• {op.get('orgao')} ({op.get('portal')}): {op.get('objeto')[:140]}")
            ok_tg, msg_tg = enviar_notificacao_telegram(tg_token, tg_chat_id, "\n".join(linhas_tg))
            st.session_state["logs_busca"].append(f"{'📲' if ok_tg else '⚠️'} {msg_tg}")


assinatura_atual = f"{porte}|{ramo}|{material_exato}|{uf}|{dias_busca}"
if busca_automatica and assinatura_atual != st.session_state["assinatura_busca"]:
    st.session_state["assinatura_busca"] = assinatura_atual
    _disparar_varredura_e_notificacoes(forcar_notificacao=False)

st.title("📡 RadarMEI — Analista Inteligente de Licitações")
st.caption("Busca automática padrão a cada 4 horas, filtro estadual/nacional pelo perfil da empresa, alerta de material exato e dossiê técnico.")
st.info("🤖 **Transparência e Ética:** Relatórios gerados por IA para triagem inicial e apoio técnico. Não substituem a leitura integral do edital oficial nem assessoria jurídica/contábil. Não insira dados pessoais sensíveis.")

aba_radar, aba_manual, aba_relatorio = st.tabs([
    "🔍 1. Radar Automático",
    "📄 2. Analisar Edital / PDF",
    "📊 3. Relatório Técnico & Viabilidade",
])


def _executar_analise(texto_completo: str, metadados: dict | None = None):
    with st.spinner("Analista de IA avaliando escopo, riscos, aderência e viabilidade..."):
        resultado = analisar_oportunidade(texto_completo, perfil_empresa=perfil_empresa)
    st.session_state["relatorio_atual"] = resultado
    st.session_state["contexto_analisado"] = metadados or {"valor_estimado": 0.0, "orgao": "Análise Direta", "portal": "Texto / PDF"}


with aba_radar:
    c_btn, c_status = st.columns([2, 3])
    with c_btn:
        if st.button("🔄 Atualizar Busca Agora", type="primary", use_container_width=True):
            st.session_state["assinatura_busca"] = assinatura_atual
            _disparar_varredura_e_notificacoes(forcar_notificacao=True)
    with c_status:
        if monitoramento_continuo:
            restante = (intervalo_min * 60) - (time.time() - st.session_state["ultimo_check_ts"])
            st.caption(f"⏱️ Busca automática ({_formatar_intervalo(intervalo_min)}) — próxima em {_formatar_tempo_restante(restante)}")
        else:
            st.caption("⏸️ Busca automática periódica pausada (padrão configurado: a cada 4 horas)")

    oportunidades = st.session_state["oportunidades"]
    matches_exatos = [op for op in oportunidades if op.get("match_exato")]
    if matches_exatos:
        alvo_txt = material_exato.strip() or ramo.strip() or "critérios da empresa"
        st.success(f"🔔 **Notificação Ativa:** Foram encontradas **{len(matches_exatos)}** oportunidade(s) compatível(is) com **{alvo_txt}** no filtro configurado.")

    if st.session_state["logs_busca"]:
        with st.expander("📡 Log da varredura e notificações", expanded=False):
            for linha in st.session_state["logs_busca"]:
                st.write(linha)

    if oportunidades:
        st.subheader(f"Oportunidades filtradas para a empresa ({len(oportunidades)})")
        for idx, op in enumerate(oportunidades):
            valor_fmt = f"R$ {op['valor_estimado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if op.get("valor_estimado") else "Não divulgado"
            eh_match = bool(op.get("match_exato"))
            classe_card = "card-oportunidade card-match" if eh_match else "card-oportunidade"
            badge_match = f'<span class="badge badge-match">🎯 MATCH EXATO ({", ".join(op.get("termos_encontrados") or [])})</span>' if eh_match else ""
            st.markdown(
                f"""
                <div class="{classe_card}">
                    {badge_match}
                    <span class="badge badge-portal">{op.get('portal', 'Portal Público')}</span>
                    <strong>{op.get('orgao')}</strong> — {op.get('municipio')}/{op.get('uf')}<br/>
                    <small>Modalidade: <b>{op.get('modalidade')}</b> | Valor estimado: <b>{valor_fmt}</b> | Encerramento: <b>{op.get('encerramento')}</b></small>
                    <p style="margin-top:0.5rem; margin-bottom:0.2rem;">{op.get('objeto')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns([2, 1])
            if b1.button(f"🧠 Gerar Relatório Técnico (#{idx+1})", key=f"btn_op_{idx}", use_container_width=True):
                texto_op = f"Portal: {op.get('portal')}\nÓrgão: {op.get('orgao')} ({op.get('municipio')}/{op.get('uf')})\nModalidade: {op.get('modalidade')}\nValor estimado: {valor_fmt}\nEncerramento: {op.get('encerramento')}\nObjeto: {op.get('objeto')}"
                try:
                    _executar_analise(texto_op, metadados=op)
                    st.success("✅ Relatório técnico pronto! Abra a aba **'📊 3. Relatório Técnico & Viabilidade'**.")
                except Exception as exc:
                    st.error(f"Erro na análise: {exc}")
            if op.get("link"):
                b2.link_button("🔗 Abrir portal", op["link"], use_container_width=True)
    else:
        st.info("Ajuste os filtros na barra lateral esquerda para iniciar a busca automática.")

    st.divider()
    st.markdown("### 🌐 Busca direta em outros portais externos")
    st.caption("Atalhos pré-filtrados com a sua palavra-chave e UF para portais que exigem consulta web direta:")
    links = gerar_links_portais_externos(material_exato or ramo, uf)
    cols_links = st.columns(4)
    for i, item_link in enumerate(links):
        cols_links[i % 4].link_button(item_link["portal"], item_link["url"], use_container_width=True)


with aba_manual:
    st.subheader("Envie o PDF do Edital / Termo de Referência ou cole o texto")
    arquivo_pdf = st.file_uploader("Upload de PDF do edital (opcional)", type=["pdf"])
    texto_pdf_extraido = ""
    if arquivo_pdf is not None:
        try:
            texto_pdf_extraido = extrair_texto_pdf(arquivo_pdf.read())
            st.success(f"PDF lido com sucesso ({len(texto_pdf_extraido)} caracteres extraídos).")
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
    texto_para_analise = st.text_area("Conteúdo do edital / dispensa para análise técnica:", value=texto_base, height=200)

    if st.button("📋 Gerar Dossiê Técnico Completo", type="primary"):
        try:
            _executar_analise(texto_para_analise, metadados={"valor_estimado": 0.0, "orgao": "Edital / PDF Enviado", "portal": "Upload / Colagem"})
            st.success("✅ Dossiê técnico gerado! Clique na aba **'📊 3. Relatório Técnico & Viabilidade'**.")
        except Exception as exc:
            st.error(f"Erro ao gerar relatório: {exc}")


with aba_relatorio:
    res = st.session_state["relatorio_atual"]
    ctx = st.session_state["contexto_analisado"] or {}
    if not res:
        st.info("Nenhuma análise gerada ainda. Selecione uma oportunidade na Aba 1 ou envie um edital na Aba 2.")
    else:
        dados = res["dados"]
        uso = res["uso"]
        st.subheader(dados["titulo_comercial"])
        st.caption(f"Origem: {ctx.get('portal', 'N/A')} | Órgão: {ctx.get('orgao', 'N/A')}")

        m1, m2, m3 = st.columns(3)
        m1.metric("Aderência à Empresa", dados["aderencia_empresa"])
        m2.metric("Recomendação", dados["recomendacao_decisao"])
        m3.metric("Margem Alvo Empresa", f"{margem_minima}%")

        st.markdown("### 📝 Resumo Executivo")
        st.write(dados["resumo_executivo"])
        st.info(f"**Diagnóstico de Aderência:** {dados['justificativa_aderencia']}")

        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.markdown("### 📌 Escopo e Exigências")
            for item in dados["escopo_e_exigencias"]:
                st.write(f"- {item}")
            st.markdown("### ✅ Checklist de Participação")
            for item in dados["checklist_participacao"]:
                st.checkbox(item, value=False, key=f"chk_{hash(item)}_{dados['titulo_comercial']}")
        with col_dir:
            st.markdown("### ⚠️ Matriz de Riscos")
            for risco in dados["matriz_riscos"]:
                st.warning(risco)
            st.markdown("### 💡 Parecer Financeiro e Próximo Passo")
            st.success(dados["parecer_financeiro_e_acao"])

        st.divider()
        st.markdown("### 🧮 Simulador Rápido de Viabilidade Financeira")
        valor_ref = float(ctx.get("valor_estimado") or 10000.0)
        s1, s2, s3, s4 = st.columns(4)
        preco_proposta = s1.number_input("Sua proposta / teto (R$)", min_value=0.0, value=valor_ref, step=100.0)
        custo_produto = s2.number_input("Custo produto/serviço (R$)", min_value=0.0, value=round(valor_ref * 0.65, 2), step=100.0)
        custo_frete = s3.number_input("Frete / logística (R$)", min_value=0.0, value=round(valor_ref * 0.08, 2), step=50.0)
        impostos_pct = s4.number_input("Impostos / taxas (%)", min_value=0.0, max_value=40.0, value=6.0, step=0.5)

        valor_impostos = preco_proposta * (impostos_pct / 100.0)
        lucro_liquido = preco_proposta - custo_produto - custo_frete - valor_impostos
        margem_real = (lucro_liquido / preco_proposta * 100.0) if preco_proposta > 0 else 0.0

        r1, r2, r3 = st.columns(3)
        r1.metric("Lucro Líquido Estimado", f"R$ {lucro_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        r2.metric("Margem Líquida Real", f"{margem_real:.1f}%", delta=f"{margem_real - margem_minima:.1f}% vs alvo")
        r3.metric("Status Viabilidade", "VIÁVEL" if margem_real >= margem_minima else "MARGEM ABAIXO DO ALVO")

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
        st.download_button("⬇️ Baixar Relatório Técnico (.md)", data=relatorio_md, file_name="relatorio_tecnico_licitacao.md", mime="text/markdown")

        st.divider()
        custo_usd = float(uso.get("custo_estimado_usd", 0.0))
        custo_brl = custo_usd * 5.80
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Tokens de entrada", uso.get("prompt_tokens", 0))
        t2.metric("Tokens de saída", uso.get("completion_tokens", 0))
        t3.metric("Total de tokens", uso.get("total_tokens", 0))
        t4.metric("Custo est. (USD / BRL)", f"${custo_usd:.5f} | R${custo_brl:.4f}")

        with st.expander("🧾 JSON estruturado validado"):
            st.code(res["json_bruto"], language="json")

if monitoramento_continuo:
    decorrido = time.time() - st.session_state["ultimo_check_ts"]
    espera = max(1, int(intervalo_min * 60 - decorrido))
    time.sleep(min(espera, 30))
    if time.time() - st.session_state["ultimo_check_ts"] >= intervalo_min * 60:
        _disparar_varredura_e_notificacoes(forcar_notificacao=False)
    st.rerun()