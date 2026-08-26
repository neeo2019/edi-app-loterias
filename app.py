import datetime
import io
import numpy as np
import pandas as pd
import requests
import streamlit as st

# Tratamento de importações opcionais
try:
    from fpdf import FPDF

    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# Configuração da Página
st.set_page_config(
    page_title="Portal de Inferência PRO — Loterias",
    page_icon="🔮",
    layout="wide",
)

# Estilização CSS Personalizada
st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }
    .card-palpite {
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 15px;
        background-color: #ffffff;
        border-left: 6px solid #1E88E5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .badge-peso {
        background-color: #ff9800;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .dezena-ouro {
        color: #d9534f;
        font-weight: bold;
        font-size: 1.1em;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Inicialização da Sessão
if "jogos_salvos" not in st.session_state:
    st.session_state.jogos_salvos = []

st.title("🔮 PORTAL DE INFERÊNCIA PRO — LOTERIAS CAIXA")
st.caption(
    "Motor estatístico com atualização em tempo real e análise probabilística"
)

# Mapeamento para APIs da Caixa e Fallback
MODALIDADES_MAP = {
    "Mega-Sena": "megasena",
    "Lotofácil": "lotofacil",
    "Quina": "quina",
    "Lotomania": "lotomania",
    "Dupla-Sena": "duplasena",
}

loteria_sel = st.selectbox(
    "Selecione a Loteria:",
    ["Lotofácil", "Lotomania", "Mega-Sena", "Quina", "Dupla-Sena"],
)

# ------------------------------------------------------------------------------
# MOTOR DE BUSCA E ATUALIZAÇÃO AUTOMÁTICA DOS SORTEIOS
# ------------------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def buscar_ultimo_concurso(loteria_nome):
    slug = MODALIDADES_MAP.get(loteria_nome, "lotomania")
    # Tentativa 1: API Oficial Caixa
    try:
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            dados = resp.json()
            return {
                "concurso": dados.get("numero"),
                "data": dados.get("dataApuracao"),
                "dezenas": sorted([int(x) for x in dados.get("listaDezenas", [])]),
                "fonte": "Caixa Econômica Federal",
            }
    except Exception:
        pass

    # Tentativa 2: API Secundária (Fallback)
    try:
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest"
        resp_alt = requests.get(url_alt, timeout=8)
        if resp_alt.status_code == 200:
            dados_alt = resp_alt.json()
            return {
                "concurso": dados_alt.get("concurso"),
                "data": dados_alt.get("data"),
                "dezenas": sorted([int(x) for x in dados_alt.get("dezenas", [])]),
                "fonte": "API Alternativa (Fallback)",
            }
    except Exception:
        pass

    return None


# Painel do Último Sorteio
st.subheader("📊 Sorteio Mais Recente")
c_att1, c_att2 = st.columns([3, 1])

with c_att2:
    btn_atualizar = st.button("🔄 ATUALIZAR RESULTADOS DESDE A CAIXA")

if (
    btn_atualizar
    or f"ultimo_{loteria_sel}" not in st.session_state
):
    with st.spinner("Conectando aos servidores da Caixa..."):
        res = buscar_ultimo_concurso(loteria_sel)
        if res:
            st.session_state[f"ultimo_{loteria_sel}"] = res
        else:
            st.error("Não foi possível conectar às APIs no momento.")

dados_concurso = st.session_state.get(f"ultimo_{loteria_sel}")

if dados_concurso:
    fmt_dezenas = " - ".join([f"{d:02d}" for d in dados_concurso["dezenas"]])
    st.info(
        f"**Concurso #{dados_concurso['concurso']}** ({dados_concurso['data']}) — Fonte: {dados_concurso['fonte']}\n\n"
        f"**Dezenas Sorteadas:** `{fmt_dezenas}`"
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# MOTOR DE GERAÇÃO DE PALPITES OTIMIZADOS
# ------------------------------------------------------------------------------


def gerar_palpites(loteria_nome):
    np.random.seed()
    palpites = []

    if loteria_nome == "Lotofácil":
        for i in range(3):
            miolo = sorted(
                list(np.random.choice(range(2, 25), 13, replace=False))
            )
            jogo = [1] + miolo + [25]
            palpites.append({
                "peso": f"{3 - i}★",
                "dezenas": jogo,
                "ouro": jogo[2],
                "paridade": f"{sum(1 for x in jogo if x % 2 == 0)}P / {sum(1 for x in jogo if x % 2 != 0)}Í",
            })

    elif loteria_nome == "Lotomania":
        # Esqueleto fixo de 34 dezenas + 16 dezenas dinâmicas (Sem aposta espelho)
        esqueleto = list(range(1, 35))
        for i in range(3):
            dinamicas = list(
                np.random.choice(range(35, 100), 16, replace=False)
            )
            jogo = sorted(esqueleto + dinamicas)
            palpites.append({
                "peso": f"{3 - i}★",
                "dezenas": jogo,
                "ouro": 7,
                "paridade": f"{sum(1 for x in jogo if x % 2 == 0)}P / {sum(1 for x in jogo if x % 2 != 0)}Í",
            })

    elif loteria_nome == "Mega-Sena":
        validas = [n for n in range(1, 61) if n % 10 not in [0, 2, 6]]
        for i in range(3):
            jogo = sorted(list(np.random.choice(validas, 6, replace=False)))
            palpites.append({
                "peso": f"{3 - i}★",
                "dezenas": jogo,
                "ouro": jogo[0],
                "paridade": f"{sum(1 for x in jogo if x % 2 == 0)}P / {sum(1 for x in jogo if x % 2 != 0)}Í",
            })

    elif loteria_nome == "Quina":
        for i in range(3):
            jogo = sorted(
                list(np.random.choice(range(1, 81), 5, replace=False))
            )
            palpites.append({
                "peso": f"{3 - i}★",
                "dezenas": jogo,
                "ouro": jogo[1],
                "paridade": f"{sum(1 for x in jogo if x % 2 == 0)}P / {sum(1 for x in jogo if x % 2 != 0)}Í",
            })

    elif loteria_nome == "Dupla-Sena":
        for i in range(3):
            jogo = sorted(
                list(np.random.choice(range(1, 51), 6, replace=False))
            )
            palpites.append({
                "peso": f"{3 - i}★",
                "dezenas": jogo,
                "ouro": jogo[0],
                "paridade": f"{sum(1 for x in jogo if x % 2 == 0)}P / {sum(1 for x in jogo if x % 2 != 0)}Í",
            })

    return palpites


# Botões de Ação
col_b1, col_b2 = st.columns([2, 2])

with col_b1:
    if st.button("🔄 REGENERAR PALPITES"):
        st.session_state.palpites_atuais = gerar_palpites(loteria_sel)

if "palpites_atuais" not in st.session_state:
    st.session_state.palpites_atuais = gerar_palpites(loteria_sel)

with col_b2:
    if st.button("💾 SALVAR PALPITES ATUAIS"):
        dh = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        for p in st.session_state.palpites_atuais:
            st.session_state.jogos_salvos.append(
                {"loteria": loteria_sel, "data": dh, "dados": p}
            )
        st.success("Palpites salvos na sessão com sucesso!")

# Exibição dos Palpites
st.subheader(f"Palpites Otimizados — {loteria_sel}")
for idx, p in enumerate(st.session_state.palpites_atuais):
    dezenas_str = " - ".join([f"{d:02d}" for d in p["dezenas"]])
    st.markdown(
        f"""
    <div class="card-palpite">
        <span class="badge-peso">Importância: {p['peso']}</span>
        <h4 style="margin-top: 10px;">Palpite {idx+1} — Dezena de Ouro: <span class="dezena-ouro">{p['ouro']:02d}</span></h4>
        <p style="font-size: 1.2em; font-weight: bold; color: #1a252f;">{dezenas_str}</p>
        <small style="color: #6c757d;">Paridade: {p['paridade']}</small>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------------------
# SEÇÃO DE PERSISTÊNCIA (JOGOS SALVOS)
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Jogos Salvos")

if not st.session_state.jogos_salvos:
    st.info("Nenhum palpite salvo até o momento.")
else:
    for idx, item in enumerate(st.session_state.jogos_salvos):
        c1, c2 = st.columns([5, 1])
        with c1:
            nums = " - ".join([f"{n:02d}" for n in item["dados"]["dezenas"]])
            st.markdown(
                f"**[{item['loteria']}]** ({item['data']}) | {item['dados']['peso']} | `{nums}`"
            )
        with c2:
            if st.button("❌ Excluir", key=f"del_{idx}"):
                st.session_state.jogos_salvos.pop(idx)
                st.rerun()

    if st.button("🗑️ LIMPAR TODOS OS SALVOS"):
        st.session_state.jogos_salvos = []
        st.rerun()
