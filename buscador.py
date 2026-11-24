from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any
from urllib.parse import quote_plus
from pypdf import PdfReader
import requests

PNCP_BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
COMPRAS_GOV_URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
QUERIDO_DIARIO_URL = "https://queridodiario.ok.org.br/api/gazettes"

ESTADOS_BRASIL: list[str] = [
    "PE", "PB", "RN", "AL", "BA", "CE", "SE", "MA", "PI",
    "SP", "RJ", "MG", "ES", "PR", "SC", "RS", "DF", "GO",
    "MT", "MS", "AM", "PA", "RO", "RR", "AC", "AP", "TO",
]

OPORTUNIDADES_EXEMPLO: list[dict[str, Any]] = [
    {
        "id": "PNCP-EX-001",
        "portal": "PNCP / Compras.gov.br",
        "orgao": "Prefeitura Municipal de Recife — Secretaria de Administração",
        "uf": "PE",
        "municipio": "Recife",
        "modalidade": "Dispensa Eletrônica",
        "valor_estimado": 18500.00,
        "encerramento": "2026-12-05",
        "objeto": (
            "Aquisição parcelada de materiais de escritório, papelaria e suprimentos "
            "de informática de consumo (toners compatíveis, mouses, teclados e cabos HDMI) "
            "com entrega em até 5 dias úteis no almoxarifado central."
        ),
        "link": "https://pncp.gov.br/app/editais",
    },
    {
        "id": "PCP-EX-002",
        "portal": "Portal de Compras Públicas",
        "orgao": "Secretaria Estadual de Saúde de Pernambuco",
        "uf": "PE",
        "municipio": "Jaboatão dos Guararapes",
        "modalidade": "Dispensa Eletrônica",
        "valor_estimado": 29400.00,
        "encerramento": "2026-12-08",
        "objeto": (
            "Contratação de serviço de manutenção preventiva e corretiva em equipamentos "
            "de climatização (split e centrais) incluindo limpeza de filtros e emissão de "
            "laudo técnico mensal pelo prazo de 6 meses."
        ),
        "link": "https://www.portaldecompraspublicas.com.br/",
    },
    {
        "id": "DOM-EX-003",
        "portal": "Diário Oficial Municipal (Querido Diário)",
        "orgao": "Município de Olinda — Secretaria de Educação",
        "uf": "PE",
        "municipio": "Olinda",
        "modalidade": "Aviso de Licitação / Cotação",
        "valor_estimado": 42000.00,
        "encerramento": "2026-12-10",
        "objeto": (
            "Fornecimento de kits de lanche / coffee break e água mineral para eventos "
            "pedagógicos e formações, com entrega fracionada conforme cronograma."
        ),
        "link": "https://queridodiario.ok.org.br/",
    },
    {
        "id": "BLL-EX-004",
        "portal": "BLL Compras",
        "orgao": "Consórcio Intermunicipal de Saúde",
        "uf": "PE",
        "municipio": "Caruaru",
        "modalidade": "Pregão Eletrônico",
        "valor_estimado": 78000.00,
        "encerramento": "2026-12-14",
        "objeto": (
            "Aquisição de equipamentos de informática (tablets corporativos, leitores de "
            "código de barras e nobreaks) com garantia mínima de 12 meses on-site."
        ),
        "link": "https://bll.org.br/",
    },
    {
        "id": "PNCP-EX-005",
        "portal": "PNCP / Compras.gov.br",
        "orgao": "Tribunal Regional do Trabalho da 6ª Região",
        "uf": "PE",
        "municipio": "Recife",
        "modalidade": "Dispensa Eletrônica",
        "valor_estimado": 22900.00,
        "encerramento": "2026-12-18",
        "objeto": (
            "Aquisição de monitores LED Full HD, hubs USB-C e suportes articulados para "
            "estações de trabalho."
        ),
        "link": "https://pncp.gov.br/app/editais",
    },
]


def _validar_url_http(url: str | None, nome_fonte: str) -> str:
    """Garante que a URL seja HTTP/HTTPS válida antes de disparar requests."""
    limpa = (url or "").strip()
    if not limpa.startswith(("http://", "https://")):
        raise ValueError(f"URL inválida para {nome_fonte}: '{limpa}'")
    return limpa


def _formatar_erro_requisicao(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return f"HTTPError {exc.response.status_code}"
    if isinstance(exc, requests.exceptions.Timeout):
        return "Timeout"
    return type(exc).__name__


def normalizar_texto(texto: str) -> str:
    """Remove acentos e coloca em minúsculas para comparação robusta de materiais/termos."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(sem_acento.lower().split())


def _normalizar_lista_ufs(ufs: list[str] | str | None, todos_estados: bool = False) -> list[str]:
    """Retorna lista de UFs válidas (2 letras), ou [] para buscar sem filtro de UF."""
    if todos_estados:
        return []
    if isinstance(ufs, str):
        limpo = ufs.strip().upper()
        if not limpo or limpo == "BR":
            return []
        return [p.strip() for p in limpo.split(",") if len(p.strip()) == 2 and p.strip() != "BR"]
    if isinstance(ufs, (list, tuple, set)):
        out: list[str] = []
        for item in ufs:
            sigla = str(item or "").strip().upper()
            if not sigla:
                continue
            if sigla == "BR":
                return []
            if len(sigla) == 2 and sigla not in out:
                out.append(sigla)
        return out
    return ["PE"]


def extrair_termos_alvo(material_exato: str, ramo: str) -> list[str]:
    bruto = f"{material_exato or ''},{ramo or ''}"
    partes = [normalizar_texto(p) for p in bruto.replace(";", ",").split(",")]
    return [p for p in partes if p]


def verificar_match_material(item: dict[str, Any], material_exato: str, ramo: str) -> tuple[bool, list[str]]:
    alvo_exato = normalizar_texto(material_exato)
    termos_ramo = extrair_termos_alvo("", ramo)
    texto_item = normalizar_texto(
        f"{item.get('objeto', '')} {item.get('orgao', '')} {item.get('modalidade', '')}"
    )

    encontrados: list[str] = []
    if alvo_exato and alvo_exato in texto_item:
        encontrados.append(alvo_exato)

    for t in termos_ramo:
        if t and t in texto_item and t not in encontrados:
            encontrados.append(t)

    if alvo_exato:
        return (alvo_exato in encontrados), encontrados

    if termos_ramo:
        return (len(encontrados) > 0), encontrados

    return True, []


def _identificar_portal_origem(item: dict[str, Any], fonte_padrao: str) -> str:
    texto_meta = (
        f"{item.get('linkSistemaOrigem') or ''} "
        f"{item.get('sistemaOrigem') or ''} "
        f"{item.get('numeroControlePNCP') or ''}"
    ).lower()
    if "comprasnet" in texto_meta or "compras.gov" in texto_meta:
        return "Compras.gov.br (via PNCP)"
    if "portaldecompraspublicas" in texto_meta:
        return "Portal de Compras Públicas (via PNCP)"
    if "bll" in texto_meta:
        return "BLL Compras (via PNCP)"
    if "bnc" in texto_meta:
        return "BNC (via PNCP)"
    if "licitanet" in texto_meta:
        return "Licitanet (via PNCP)"
    return fonte_padrao


def _buscar_pncp_por_uf(
    uf_param: str | None, termos: list[str], dias_atras: int, limite: int
) -> list[dict[str, Any]]:
    endpoint = _validar_url_http(PNCP_BASE_URL, "PNCP")
    data_fim = datetime.now().strftime("%Y%m%d")
    data_ini = (datetime.now() - timedelta(days=max(1, dias_atras))).strftime("%Y%m%d")
    resultados: list[dict[str, Any]] = []

    for modalidade in (8, 6):
        params: dict[str, Any] = {
            "dataInicial": data_ini,
            "dataFinal": data_fim,
            "codigoModalidadeContratacao": modalidade,
            "pagina": 1,
            "tamanhoPagina": 50,
        }
        if uf_param:
            params["uf"] = uf_param

        try:
            resp = requests.get(endpoint, params=params, timeout=12)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            if resultados:
                break
            raise

        itens = resp.json().get("data") or []

        for item in itens:
            objeto = (item.get("objetoCompra") or "").strip()
            if not objeto:
                continue
            orgao = ((item.get("orgaoEntidade") or {}).get("razaoSocial")) or "Órgão Público"
            unidade = item.get("unidadeOrgao") or {}
            municipio = unidade.get("municipioNome") or ""
            uf_item = unidade.get("ufSigla") or (uf_param or "Sem UF")
            texto_busca = normalizar_texto(f"{objeto} {orgao} {municipio}")

            if termos and not any(t in texto_busca for t in termos):
                continue

            valor = item.get("valorTotalEstimado")
            encerramento = (item.get("dataEncerramentoProposta") or "")[:10] or "Não informado"
            link_origem = item.get("linkSistemaOrigem") or "https://pncp.gov.br/app/editais"

            resultados.append(
                {
                    "id": item.get("numeroControlePNCP") or f"PNCP-{uf_item}-{len(resultados)+1}",
                    "portal": _identificar_portal_origem(item, "PNCP"),
                    "orgao": orgao,
                    "uf": uf_item,
                    "municipio": municipio,
                    "modalidade": item.get("modalidadeNome") or "Licitação / Dispensa",
                    "valor_estimado": float(valor) if isinstance(valor, (int, float)) else None,
                    "encerramento": encerramento,
                    "objeto": objeto,
                    "link": link_origem,
                }
            )
            if len(resultados) >= limite:
                return resultados
    return resultados


def _buscar_pncp(
    ufs_alvo: list[str], termos: list[str], dias_atras: int, limite: int
) -> tuple[list[dict[str, Any]], str]:
    rotulo_uf = "Sem filtro de UF" if not ufs_alvo else ", ".join(ufs_alvo)
    if not ufs_alvo:
        itens = _buscar_pncp_por_uf(None, termos, dias_atras, limite)
        return itens, f"PNCP / Portais integrados ({rotulo_uf}): {len(itens)} resultado(s)"

    por_uf = max(3, limite // len(ufs_alvo) + 2)
    resultados: list[dict[str, Any]] = []
    for sigla in ufs_alvo[:6]:
        resultados.extend(_buscar_pncp_por_uf(sigla, termos, dias_atras, por_uf))
        if len(resultados) >= limite:
            break
    return resultados[:limite], f"PNCP / Portais integrados ({rotulo_uf}): {len(resultados[:limite])} resultado(s)"


def _buscar_compras_gov(
    ufs_alvo: list[str], termos: list[str], dias_atras: int, limite: int
) -> tuple[list[dict[str, Any]], str]:
    endpoint = _validar_url_http(COMPRAS_GOV_URL, "Compras.gov.br")
    data_fim = datetime.now().strftime("%Y-%m-%d")
    data_ini = (datetime.now() - timedelta(days=max(1, dias_atras))).strftime("%Y-%m-%d")
    rotulo_uf = "Sem filtro de UF" if not ufs_alvo else ", ".join(ufs_alvo)
    consultas: list[str | None] = [None] if not ufs_alvo else list(ufs_alvo[:4])
    resultados: list[dict[str, Any]] = []

    for uf_param in consultas:
        params: dict[str, Any] = {
            "pagina": 1,
            "tamanhoPagina": 40,
            "dataPublicacaoPncpInicial": data_ini,
            "dataPublicacaoPncpFinal": data_fim,
        }
        if uf_param:
            params["unidadeOrgaoUfSigla"] = uf_param

        resp = requests.get(endpoint, params=params, timeout=12)
        resp.raise_for_status()
        itens = resp.json().get("resultado") or []

        for item in itens:
            objeto = (item.get("objetoCompra") or "").strip()
            if not objeto:
                continue
            orgao = item.get("orgaoEntidadeRazaoSocial") or "Órgão Federal / Compras.gov"
            municipio = item.get("unidadeOrgaoMunicipioNome") or ""
            uf_item = item.get("unidadeOrgaoUfSigla") or (uf_param or "Sem UF")
            texto_busca = normalizar_texto(f"{objeto} {orgao} {municipio}")

            if termos and not any(t in texto_busca for t in termos):
                continue

            valor = item.get("valorTotalEstimado")
            encerramento = (item.get("dataEncerramentoPropostaPncp") or "")[:10] or "Não informado"

            resultados.append(
                {
                    "id": item.get("numeroControlePNCP") or f"CGOV-{uf_item}-{len(resultados)+1}",
                    "portal": "Compras.gov.br (Dados Abertos)",
                    "orgao": orgao,
                    "uf": uf_item,
                    "municipio": municipio,
                    "modalidade": item.get("modalidadeNome") or "Contratação Federal",
                    "valor_estimado": float(valor) if isinstance(valor, (int, float)) else None,
                    "encerramento": encerramento,
                    "objeto": objeto,
                    "link": item.get("linkSistemaOrigem") or "https://www.gov.br/compras",
                }
            )
            if len(resultados) >= limite:
                return resultados, f"Compras.gov.br ({rotulo_uf}): {len(resultados)} resultado(s)"

    return resultados, f"Compras.gov.br ({rotulo_uf}): {len(resultados)} resultado(s)"


def _buscar_querido_diario(
    ufs_alvo: list[str], termos: list[str], dias_atras: int, limite: int
) -> tuple[list[dict[str, Any]], str]:
    endpoint = _validar_url_http(QUERIDO_DIARIO_URL, "Querido Diário")
    data_fim = datetime.now().strftime("%Y-%m-%d")
    data_ini = (datetime.now() - timedelta(days=max(1, dias_atras))).strftime("%Y-%m-%d")
    rotulo_uf = "Sem filtro de UF" if not ufs_alvo else ", ".join(ufs_alvo)
    foco_termo = termos[0] if termos else "dispensa"
    query_str = f"dispensa {foco_termo}".strip() if foco_termo != "dispensa" else "dispensa"

    params: dict[str, Any] = {
        "querystring": query_str,
        "published_since": data_ini,
        "published_until": data_fim,
        "size": min(15, limite),
        "excerpt_size": 450,
    }
    resp = requests.get(endpoint, params=params, timeout=12)
    resp.raise_for_status()
    gazettes = resp.json().get("gazettes") or []
    resultados: list[dict[str, Any]] = []

    for g in gazettes:
        uf_g = (g.get("state_code") or "").upper()
        if ufs_alvo and uf_g and uf_g not in ufs_alvo:
            continue
        trechos = g.get("excerpts") or []
        resumo_trecho = " ".join(trechos).replace("\n", " ").strip()
        if not resumo_trecho:
            continue
        nome_mun = g.get("territory_name") or "Município"
        data_pub = g.get("date") or "Recente"

        resultados.append(
            {
                "id": f"DOM-{g.get('territory_id', '0')}-{data_pub}-{len(resultados)+1}",
                "portal": "Diário Oficial Municipal (Querido Diário)",
                "orgao": f"Prefeitura / Órgão Municipal de {nome_mun}",
                "uf": uf_g or "Sem UF",
                "municipio": nome_mun,
                "modalidade": "Publicação em Diário Oficial",
                "valor_estimado": None,
                "encerramento": f"Publicado em {data_pub}",
                "objeto": resumo_trecho[:500],
                "link": g.get("url") or "https://queridodiario.ok.org.br/",
            }
        )
        if len(resultados) >= limite:
            break

    return resultados, f"Diários Oficiais ({rotulo_uf}): {len(resultados)} resultado(s)"


def gerar_links_portais_externos(
    palavra_chave: str, ufs: list[str] | str = "PE", todos_estados: bool = False
) -> list[dict[str, str]]:
    q = quote_plus((palavra_chave or "dispensa").strip())
    ufs_lista = _normalizar_lista_ufs(ufs, todos_estados=todos_estados)
    if not ufs_lista:
        pncp_url = f"https://pncp.gov.br/app/editais?q={q}"
    else:
        ufs_qs = quote_plus(",".join(ufs_lista))
        pncp_url = f"https://pncp.gov.br/app/editais?q={q}&ufs={ufs_qs}"

    return [
        {"portal": "PNCP (Nacional)", "url": pncp_url},
        {"portal": "Compras.gov.br", "url": "https://www.gov.br/compras/pt-br"},
        {"portal": "Portal de Compras Públicas", "url": "https://www.portaldecompraspublicas.com.br/processos"},
        {"portal": "BLL Compras", "url": "https://bllcompras.com/Process/ProcessSearchPublic"},
        {"portal": "BNC (Bolsa Nacional)", "url": "https://bnccompras.com/Process/ProcessSearchPublic"},
        {"portal": "Licitanet", "url": "https://licitanet.com.br/processos"},
        {"portal": "BEC-SP / Compras Estaduais", "url": "https://www.bec.sp.gov.br/"},
        {"portal": "Diários Oficiais (Querido Diário)", "url": f"https://queridodiario.ok.org.br/pesquisa?q={q}"},
    ]


def buscar_oportunidades_multiportal(
    uf: list[str] | str = "PE",
    palavra_chave: str = "",
    material_exato: str = "",
    dias_atras: int = 7,
    limite_total: int = 20,
    todos_estados: bool = False,
) -> tuple[list[dict[str, Any]], list[str], bool]:
    """
    Varre fontes públicas e retorna (lista_consolidada, relatorio_fontes, usou_exemplo).
    """
    ufs_alvo = _normalizar_lista_ufs(uf, todos_estados=todos_estados)
    termos = extrair_termos_alvo(material_exato, palavra_chave)
    consolidados: list[dict[str, Any]] = []
    vistos: set[str] = set()
    logs_fontes: list[str] = []
    usou_exemplo = False

    fontes = [
        ("PNCP", lambda: _buscar_pncp(ufs_alvo, termos, dias_atras, limite=10)),
        ("Compras.gov.br", lambda: _buscar_compras_gov(ufs_alvo, termos, dias_atras, limite=8)),
        ("Diários Oficiais", lambda: _buscar_querido_diario(ufs_alvo, termos, dias_atras, limite=8)),
    ]

    for nome_fonte, fn in fontes:
        try:
            itens, msg = fn()
            logs_fontes.append(f"✅ {msg}")
            for item in itens:
                chave_dedup = f"{normalizar_texto(item['orgao'])[:30]}|{normalizar_texto(item['objeto'])[:60]}"
                if chave_dedup in vistos:
                    continue
                vistos.add(chave_dedup)
                houve_match, termos_batidos = verificar_match_material(item, material_exato, palavra_chave)
                item["match_exato"] = houve_match
                item["termos_encontrados"] = termos_batidos
                consolidados.append(item)
                if len(consolidados) >= limite_total:
                    break
        except Exception as exc:
            logs_fontes.append(f"⚠️ {nome_fonte}: indisponível no momento ({_formatar_erro_requisicao(exc)})")

    if not consolidados:
        usou_exemplo = True
        base_ex = _filtrar_exemplos(material_exato or palavra_chave, ufs_alvo)
        for item in base_ex:
            copia = dict(item)
            houve_match, termos_batidos = verificar_match_material(copia, material_exato, palavra_chave)
            copia["match_exato"] = houve_match
            copia["termos_encontrados"] = termos_batidos
            consolidados.append(copia)
        logs_fontes.append("ℹ️ Exibindo dados de exemplo para demonstração/triagem.")

    consolidados.sort(key=lambda x: (0 if x.get("match_exato") else 1))
    return consolidados[:limite_total], logs_fontes, usou_exemplo


def _filtrar_exemplos(palavra_chave: str, ufs_alvo: list[str]) -> list[dict[str, Any]]:
    termo = normalizar_texto(palavra_chave)
    filtrados = []
    for item in OPORTUNIDADES_EXEMPLO:
        if ufs_alvo and item.get("uf") and item["uf"].upper() not in ufs_alvo:
            continue
        texto = normalizar_texto(f"{item['objeto']} {item['orgao']} {item['municipio']} {item['portal']}")
        if termo and termo not in texto:
            continue
        filtrados.append(item)
    return filtrados if filtrados else OPORTUNIDADES_EXEMPLO


def enviar_notificacao_telegram(bot_token: str, chat_id: str, mensagem: str) -> tuple[bool, str]:
    token = (bot_token or "").strip()
    chat = (chat_id or "").strip()
    if not token or not chat:
        return False, "Telegram não configurado."
    try:
        url = _validar_url_http(f"https://api.telegram.org/bot{token}/sendMessage", "Telegram")
        resp = requests.post(
            url,
            json={"chat_id": chat, "text": mensagem, "disable_web_page_preview": True},
            timeout=8,
        )
        resp.raise_for_status()
        return True, "Notificação enviada ao Telegram."
    except Exception as exc:
        return False, f"Falha ao enviar Telegram ({_formatar_erro_requisicao(exc)})."


def extrair_texto_pdf(arquivo_bytes: bytes, max_caracteres: int = 8000) -> str:
    leitor = PdfReader(BytesIO(arquivo_bytes))
    partes: list[str] = []
    total = 0

    for pagina in leitor.pages:
        texto = (pagina.extract_text() or "").strip()
        if not texto:
            continue
        restante = max_caracteres - total
        if restante <= 0:
            break
        partes.append(texto[:restante])
        total += len(texto[:restante])

    return "\n\n".join(partes).strip()