import os
import random
import requests
import streamlit as st

# Configuração da página no Streamlit
st.set_page_config(
    page_title="INFERÊNCIA PRO - Análise Lotérica",
    page_icon="📊",
    layout="wide",
)

# Headers universais para simular navegador desktop real e ignorar bloqueios Cloudflare/Caixa
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

# Mapeamento de Slugs para todas as APIs
SLUGS = {
    "Mega-Sena": {"caixa": "megasena", "api2": "megasena", "api3": "megasena"},
    "Lotofácil": {"caixa": "lotofacil", "api2": "lotofacil", "api3": "lotofacil"},
    "Quina": {"caixa": "quina", "api2": "quina", "api3": "quina"},
    "Lotomania": {"caixa": "lotomania", "api2": "lotomania", "api3": "lotomania"},
    "Dupla-Sena": {
        "caixa": "duplasena",
        "api2": "duplasena",
        "api3": "duplasena",
    },
}


def extrair_dezenas(lista_dezenas):
    """Auxiliar para formatar e ordenar dezenas com dois dígitos."""
    try:
        return [f"{int(x):02d}" for x in lista_dezenas]
    except Exception:
        return [str(x).zfill(2) for x in lista_dezenas]


def obter_resultado_atualizado(nome_loteria):
    """Busca o resultado atualizado via API Oficial da Caixa com redundância em APIS espelho."""
    slug_info = SLUGS.get(nome_loteria, SLUGS["Mega-Sena"])
    slug = slug_info["caixa"]

    # -------------------------------------------------------------
    # ROTA 1: API Oficial da Caixa Econômica Federal
    # -------------------------------------------------------------
    try:
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}"
        resp = requests.get(url, headers=HEADERS, timeout=7)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("numero"):
                if slug == "duplasena":
                    s1 = extrair_dezenas(data.get("listaDezenas", []))
                    s2 = extrair_dezenas(
                        data.get("listaDezenasSegundoSorteio", [])
                    )
                    return {
                        "concurso": data.get("numero"),
                        "data": data.get("dataApuracao"),
                        "dezenas_s1": " - ".join(s1),
                        "dezenas_s2": " - ".join(s2),
                        "is_dupla": True,
                        "fonte": "Caixa Econômica Federal (Oficial)",
                    }
                else:
                    dezenas = extrair_dezenas(data.get("listaDezenas", []))
                    return {
                        "concurso": data.get("numero"),
                        "data": data.get("dataApuracao"),
                        "dezenas": " - ".join(dezenas),
                        "is_dupla": False,
                        "fonte": "Caixa Econômica Federal (Oficial)",
                    }
    except Exception:
        pass

    # -------------------------------------------------------------
    # ROTA 2: API Espelho Secundária (LoteriasCaixa API)
    # -------------------------------------------------------------
    try:
        url_alt = (
            f"https://loteriascaixa-api.herokuapp.com/api/{slug_info['api2']}/latest"
        )
        resp_alt = requests.get(url_alt, headers=HEADERS, timeout=7)
        if resp_alt.status_code == 200:
            data_alt = resp_alt.json()
            if data_alt.get("concurso"):
                if slug == "duplasena":
                    s1 = extrair_dezenas(data_alt.get("dezenas", []))
                    s2 = extrair_dezenas(
                        data_alt.get("dezenasSegundoSorteio", [])
                    )
                    return {
                        "concurso": data_alt.get("concurso"),
                        "data": data_alt.get("data"),
                        "dezenas_s1": " - ".join(s1),
                        "dezenas_s2": " - ".join(s2),
                        "is_dupla": True,
                        "fonte": "Servidor Espelho (Sincronizado)",
                    }
                else:
                    dezenas = extrair_dezenas(data_alt.get("dezenas", []))
                    return {
                        "concurso": data_alt.get("concurso"),
                        "data": data_alt.get("data"),
                        "dezenas": " - ".join(dezenas),
                        "is_dupla": False,
                        "fonte": "Servidor Espelho (Sincronizado)",
                    }
    except Exception:
        pass

    # -------------------------------------------------------------
    # ROTA 3: API Espelho Terciária (Guidi API)
    # -------------------------------------------------------------
    try:
        url_alt2 = (
            f"https://api.guidi.dev.br/loteria/{slug_info['api3']}/ultimo"
        )
        resp_alt2 = requests.get(url_alt2, headers=HEADERS, timeout=7)
        if resp_alt2.status_code == 200:
            data_alt2 = resp_alt2.json()
            if data_alt2.get("numero"):
                if slug == "duplasena":
                    s1 = extrair_dezenas(data_alt2.get("listaDezenas", []))
                    s2 = extrair_dezenas(
                        data_alt2.get("listaDezenasSegundoSorteio", [])
                    )
                    return {
                        "concurso": data_alt2.get("numero"),
                        "data": data_alt2.get("data"),
                        "dezenas_s1": " - ".join(s1),
                        "dezenas_s2": " - ".join(s2),
                        "is_dupla": True,
                        "fonte": "Servidor Terciário (Backup)",
                    }
                else:
                    dezenas = extrair_dezenas(data_alt2.get("listaDezenas", []))
                    return {
                        "concurso": data_alt2.get("numero"),
                        "data": data_alt2.get("data"),
                        "dezenas": " - ".join(dezenas),
                        "is_dupla": False,
                        "fonte": "Servidor Terciário (Backup)",
                    }
    except Exception:
        pass

    return None


# --- INTERFACE PRINCIPAL STREAMLIT ---
st.title("INFERÊNCIA PRO")
st.caption(
    "Motor Estatístico Avançado de Análise Probabilística e Atualização em Tempo Real"
)

# Seleção da Loteria
loteria_selecionada = st.selectbox(
    "Selecione a Loteria:", list(SLUGS.keys()), index=3  # Padrão: Lotomania
)

st.subheader("📊 Último Resultado Registrado")

# Limpa o cache se o usuário mudar de loteria no selectbox
if (
    "loteria_atual" not in st.session_state
    or st.session_state["loteria_atual"] != loteria_selecionada
):
    st.session_state["loteria_atual"] = loteria_selecionada
    if "ultimo_resultado" in st.session_state:
        del st.session_state["ultimo_resultado"]

# Botão de Atualização com Validação Estrita
if st.button("🔄 ATUALIZAR DESDE A CAIXA"):
    with st.spinner(f"Buscando último concurso da {loteria_selecionada}..."):
        resultado = obter_resultado_atualizado(loteria_selecionada)

    if resultado:
        st.session_state["ultimo_resultado"] = resultado
        st.success(
            f"Concurso #{resultado['concurso']} atualizado com sucesso!"
        )
    else:
        st.error(
            "Falha ao conectar com a Caixa e servidores secundários. Tente novamente em alguns instantes."
        )

# Renderização dos Dados Atualizados
if "ultimo_resultado" in st.session_state:
    res = st.session_state["ultimo_resultado"]
    st.info(
        f"**Concurso #{res['concurso']}** ({res['data']}) — *{res['fonte']}*"
    )

    if res.get("is_dupla"):
        st.markdown(f"**1º Sorteio:** `{res['dezenas_s1']}`")
        st.markdown(f"**2º Sorteio:** `{res['dezenas_s2']}`")
    else:
        st.markdown(f"**Dezenas Sorteadas:** `{res['dezenas']}`")
else:
    st.warning(
        "Clique no botão acima para buscar o concurso mais recente registrado na Caixa."
    )

st.divider()

# Ações secundárias
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 REGENERAR PALPITES"):
        st.rerun()
