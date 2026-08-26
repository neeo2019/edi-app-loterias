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

# Headers para simular um navegador real e evitar bloqueios de IP da Caixa
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
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
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "concurso": data.get("numero"),
                "data": data.get("dataApuracao"),
                "dezenas": [
                    f"{int(x):02d}" for x in data.get("listaDezenas", [])
                ],
                "fonte": "Caixa Econômica Federal (Oficial)",
            }
    except Exception:
        pass

    # Fonte 2: API Espelho Secundária (Heroku Mirror)
    try:
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest"
        resp_alt = requests.get(url_alt, timeout=6)
        if resp_alt.status_code == 200:
            data_alt = resp_alt.json()
            return {
                "concurso": data_alt.get("concurso"),
                "data": data_alt.get("data"),
                "dezenas": [
                    f"{int(x):02d}" for x in data_alt.get("dezenas", [])
                ],
                "fonte": "API Alternativa (Sincronizada)",
            }
    except Exception:
        pass

    # Fonte 3: API Espelho Terciária (Guidi Mirror)
    try:
        url_alt2 = f"https://api.guidi.dev.br/loteria/{slug}/ultimo"
        resp_alt2 = requests.get(url_alt2, timeout=6)
        if resp_alt2.status_code == 200:
            data_alt2 = resp_alt2.json()
            return {
                "concurso": data_alt2.get("numero"),
                "data": data_alt2.get("data"),
                "dezenas": [
                    f"{int(x):02d}" for x in data_alt2.get("listaDezenas", [])
                ],
                "fonte": "API Terciária (Mirror)",
            }
    except Exception:
        pass

    return None


# Interface Streamlit
st.title("INFERÊNCIA PRO")
st.caption(
    "Motor Estatístico Avançado de Análise Probabilística e Atualização em Tempo Real"
)

loteria_selecionada = st.selectbox(
    "Selecione a Loteria:", list(SLUGS.keys()), index=0
)

st.subheader("📊 Último Resultado Registrado")

# Botão de atualização manual
if st.button("🔄 ATUALIZAR DESDE A CAIXA"):
    resultado = obter_resultado_atualizado(loteria_selecionada)
    if resultado:
        st.session_state["ultimo_resultado"] = resultado
        st.success("Atualizado com sucesso!")
    else:
        st.error(
            "Não foi possível conectar às APIs de loterias no momento. Tente novamente."
        )

# Exibição do resultado obtido
if "ultimo_resultado" in st.session_state:
    res = st.session_state["ultimo_resultado"]
    st.info(
        f"**Concurso #{res['concurso']}** ({res['data']}) — *{res['fonte']}*"
    )
    dezenas_formatadas = " - ".join(res["dezenas"])
    st.markdown(f"**Dezenas Sorteadas:** `{dezenas_formatadas}`")

st.divider()

# Ações secundárias
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 REGENERAR PALPITES"):
        st.experimental_rerun()
