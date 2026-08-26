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

# Headers para simular um navegador real e evitar bloqueios de IP da Caixa/Cloudflare
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

SLUGS = {
    "Mega-Sena": "megasena",
    "Lotofácil": "lotofacil",
    "Quina": "quina",
    "Lotomania": "lotomania",
    "Dupla-Sena": "duplasena",
}


def obter_resultado_atualizado(nome_loteria):
    """Busca o último resultado da loteria selecionada utilizando fallback triplo para evitar falhas de atualização."""
    slug = SLUGS.get(nome_loteria, "megasena")

    # Fonte 1: API Oficial da Caixa Econômica Federal
    try:
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()

            if slug == "duplasena":
                s1 = [
                    f"{int(x):02d}"
                    for x in data.get("listaDezenas", [])
                ]
                s2 = [
                    f"{int(x):02d}"
                    for x in data.get("listaDezenasSegundoSorteio", [])
                ]
                return {
                    "concurso": data.get("numero"),
                    "data": data.get("dataApuracao"),
                    "dezenas_s1": " - ".join(s1),
                    "dezenas_s2": " - ".join(s2),
                    "is_dupla": True,
                    "fonte": "Caixa Econômica Federal (Oficial)",
                }
            else:
                dezenas = [
                    f"{int(x):02d}"
                    for x in data.get("listaDezenas", [])
                ]
                return {
                    "concurso": data.get("numero"),
                    "data": data.get("dataApuracao"),
                    "dezenas": " - ".join(dezenas),
                    "is_dupla": False,
                    "fonte": "Caixa Econômica Federal (Oficial)",
                }
    except Exception:
        pass

    # Fonte 2: API Espelho Secundária (LoteriasCaixa API)
    try:
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest"
        resp_alt = requests.get(url_alt, headers=HEADERS, timeout=8)
        if resp_alt.status_code == 200:
            data_alt = resp_alt.json()

            if slug == "duplasena":
                s1 = [
                    f"{int(x):02d}"
                    for x in data_alt.get("dezenas", [])
                ]
                s2 = [
                    f"{int(x):02d}"
                    for x in data_alt.get("dezenasSegundoSorteio", [])
                ]
                return {
                    "concurso": data_alt.get("concurso"),
                    "data": data_alt.get("data"),
                    "dezenas_s1": " - ".join(s1),
                    "dezenas_s2": " - ".join(s2),
                    "is_dupla": True,
                    "fonte": "API Alternativa (Sincronizada)",
                }
            else:
                dezenas = [
                    f"{int(x):02d}"
                    for x in data_alt.get("dezenas", [])
                ]
                return {
                    "concurso": data_alt.get("concurso"),
                    "data": data_alt.get("data"),
                    "dezenas": " - ".join(dezenas),
                    "is_dupla": False,
                    "fonte": "API Alternativa (Sincronizada)",
                }
    except Exception:
        pass

    # Fonte 3: API Espelho Terciária (Guidi Mirror API)
    try:
        url_alt2 = f"https://api.guidi.dev.br/loteria/{slug}/ultimo"
        resp_alt2 = requests.get(url_alt2, headers=HEADERS, timeout=8)
        if resp_alt2.status_code == 200:
            data_alt2 = resp_alt2.json()

            if slug == "duplasena":
                s1 = [
                    f"{int(x):02d}"
                    for x in data_alt2.get("listaDezenas", [])
                ]
                s2 = [
                    f"{int(x):02d}"
                    for x in data_alt2.get("listaDezenasSegundoSorteio", [])
                ]
                return {
                    "concurso": data_alt2.get("numero"),
                    "data": data_alt2.get("data"),
                    "dezenas_s1": " - ".join(s1),
                    "dezenas_s2": " - ".join(s2),
                    "is_dupla": True,
                    "fonte": "API Terciária (Mirror)",
                }
            else:
                dezenas = [
                    f"{int(x):02d}"
                    for x in data_alt2.get("listaDezenas", [])
                ]
                return {
                    "concurso": data_alt2.get("numero"),
                    "data": data_alt2.get("data"),
                    "dezenas": " - ".join(dezenas),
                    "is_dupla": False,
                    "fonte": "API Terciária (Mirror)",
                }
    except Exception:
        pass

    return None


# --- INTERFACE DO STREAMLIT ---
st.title("INFERÊNCIA PRO")
st.caption(
    "Motor Estatístico Avançado de Análise Probabilística e Atualização em Tempo Real"
)

loteria_selecionada = st.selectbox(
    "Selecione a Loteria:", list(SLUGS.keys()), index=0
)

st.subheader("📊 Último Resultado Registrado")

# Botão para disparo de busca manual com feedback ao usuário
if st.button("🔄 ATUALIZAR DESDE A CAIXA"):
    with st.spinner("Buscando dados atualizados nos servidores..."):
        resultado = obter_resultado_atualizado(loteria_selecionada)

    if resultado:
        st.session_state["ultimo_resultado"] = resultado
        st.success("Atualizado com sucesso!")
    else:
        st.error(
            "Não foi possível obter a atualização automática neste momento. Verifique sua conexão ou tente novamente."
        )

# Renderização dos Resultados na Interface
if "ultimo_resultado" in st.session_state:
    res = st.session_state["ultimo_resultado"]
    st.info(
        f"**Concurso #{res['concurso']}** ({res['data']}) — *{res['fonte']}*"
    )

    # Exibição adaptada dependendo do tipo de loteria
    if res.get("is_dupla"):
        st.markdown(f"**1º Sorteio:** `{res['dezenas_s1']}`")
        st.markdown(f"**2º Sorteio:** `{res['dezenas_s2']}`")
    else:
        st.markdown(f"**Dezenas Sorteadas:** `{res['dezenas']}`")

st.divider()

# Ações secundárias
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 REGENERAR PALPITES"):
        st.rerun()
