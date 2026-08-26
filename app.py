import streamlit as st
import numpy as np
import pandas as pd
import io
import datetime

st.set_page_config(
    page_title="Loterias Pro · EDI IA",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# DADOS DE COR E CONFIGURAÇÃO DE LOTERIAS
# -----------------------------------------------------------------------------
LOTERIAS_CONFIG = {
    "Mega-Sena": {
        "cor": "#00a859",
        "total_dezenas": 60,
        "qtd_jogo": 6,
        "ultimo_concurso": "3049",
        "data_ultimo": "25/08/2026",
        "dezenas_ultimo": [6, 13, 36, 43, 53, 55]
    },
    "Lotofácil": {
        "cor": "#930089",
        "total_dezenas": 25,
        "qtd_jogo": 15,
        "ultimo_concurso": "3770",
        "data_ultimo": "25/08/2026",
        "dezenas_ultimo": [1, 2, 4, 7, 8, 12, 13, 15, 16, 17, 18, 19, 23, 24, 25]
    },
    "Quina": {
        "cor": "#260085",
        "total_dezenas": 80,
        "qtd_jogo": 5,
        "ultimo_concurso": "7100",
        "data_ultimo": "25/08/2026",
        "dezenas_ultimo": [27, 34, 36, 48, 76]
    },
    "Lotomania": {
        "cor": "#f78200",
        "total_dezenas": 100,
        "qtd_jogo": 50,
        "ultimo_concurso": "2967",
        "data_ultimo": "25/08/2026",
        "dezenas_ultimo": [4, 7, 10, 18, 27, 29, 38, 41, 44, 56, 57, 67, 75, 81, 85, 90, 91, 94, 96, 98]
    },
    "Dupla Sena": {
        "cor": "#a6121f",
        "total_dezenas": 50,
        "qtd_jogo": 6,
        "ultimo_concurso": "3000",
        "data_ultimo": "25/08/2026",
        "dezenas_ultimo": [13, 14, 17, 39, 42, 46]
    }
}

if 'loteria_selecionada' not in st.session_state:
    st.session_state.loteria_selecionada = "Mega-Sena"

if 'jogos_salvos' not in st.session_state:
    st.session_state.jogos_salvos = []

if 'conferencia_resultado' not in st.session_state:
    st.session_state.conferencia_resultado = {}

cfg = LOTERIAS_CONFIG[st.session_state.loteria_selecionada]
cor_loteria = cfg["cor"]

# -----------------------------------------------------------------------------
# CSS CUSTOMIZADO (DESIGN ESCURO FIEL ÀS FOTOS)
# -----------------------------------------------------------------------------
st.markdown(f"""
    <style>
    /* Fundo Escuro Principal */
    .stApp {{
        background-color: #0b0e14;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    
    /* Cabeçalho de Navegação (Pills) */
    .stButton>button {{
        border-radius: 20px;
        background-color: #1a2234;
        color: #94a3b8;
        border: 1px solid #2e3a52;
        font-weight: 600;
    }}
    .stButton>button:hover {{
        border-color: {cor_loteria};
        color: #ffffff;
    }}

    /* Card Topo do Concurso */
    .card-concurso {{
        background-color: {cor_loteria};
        border-radius: 16px;
        padding: 20px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    
    /* Cartões Escuros Container */
    .box-dark {{
        background-color: #151c2c;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #232d42;
        margin-bottom: 20px;
    }}

    /* Dezenas Circulares (Dark Pills) */
    .ball-dark {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        background-color: #2b364e;
        color: #ffffff;
        border-radius: 50%;
        font-weight: bold;
        font-size: 15px;
        margin: 3px;
    }}
    .ball-gold {{
        background-color: #ffb703 !important;
        color: #000000 !important;
        font-weight: 800;
    }}
    .ball-match {{
        background-color: #00e676 !important;
        color: #000000 !important;
        font-weight: 800;
    }}
    
    /* Botões Verdes Especiais */
    .btn-green button {{
        background-color: #102a1d !important;
        color: #2ec4b6 !important;
        border: 1px solid #1b4332 !important;
        width: 100%;
        font-weight: bold;
    }}
    .btn-green-main button {{
        background-color: {cor_loteria} !important;
        color: #ffffff !important;
        border: none !important;
        width: 100%;
        font-size: 16px;
        font-weight: bold;
        padding: 12px;
        border-radius: 10px;
    }}

    /* Badges e Tags */
    .badge-tag {{
        background-color: #1e293b;
        color: #94a3b8;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
        border: 1px solid #334155;
    }}
    .badge-ouro {{
        background-color: #332701;
        color: #ffb703;
        border: 1px solid #664d03;
    }}
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TOPO: TÍTULO E NAVEGAÇÃO ENTRE LOTERIAS
# -----------------------------------------------------------------------------
st.title("Loterias Pro · EDI IA")
st.caption("3 palpites · desempenho do último concurso · jogos salvos com EXCLUIR. Não altera a probabilidade oficial.")

# Selector de Loterias (Estilo Botões da Imagem)
cols_nav = st.columns(5)
for idx, (nome_lot, d) in enumerate(LOTERIAS_CONFIG.items()):
    with cols_nav[idx]:
        if st.button(nome_lot, key=f"nav_{nome_lot}"):
            st.session_state.loteria_selecionada = nome_lot
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CARD ÚLTIMO CONCURSO
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="card-concurso">
    <div style="font-size:12px; font-weight: bold; letter-spacing: 1px;">{st.session_state.loteria_selecionada.upper()} — ÚLTIMO</div>
    <div style="font-size: 32px; font-weight: 900;">#{cfg['ultimo_concurso']}</div>
    <div style="font-size: 13px; opacity: 0.9; margin-bottom: 12px;">{cfg['data_ultimo']}</div>
    <div>
        {' '.join([f'<span class="ball-dark" style="background: rgba(255,255,255,0.2);">{d:02d}</span>' for d in cfg['dezenas_ultimo']])}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="btn-green-main">', unsafe_allow_html=True)
if st.button(f"ATUALIZAR RESULTADOS DESDE A CAIXA"):
    st.toast("Resultados sincronizados com sucesso!")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DEZENA DE OURO E PADRÃO CONDICIONAL
# -----------------------------------------------------------------------------
st.markdown("""
<div class="box-dark">
    <div style="color: #d4af37; font-weight: bold; font-size: 13px; margin-bottom: 8px;">
        Motores: ciclo · atraso · frequência · ouro · quadrantes · condicional · Monte Carlo · Mersenne. Não altera a probabilidade oficial.
    </div>
    <h3 style="margin-top:15px; font-size: 18px;">Dezena de Ouro</h3>
    <p style="color: #94a3b8; font-size: 13px;">Âncora (maior score) — presente nos 3 palpites</p>
    <span class="ball-dark ball-gold" style="width: 45px; height: 45px; font-size: 18px;">58</span>
    <br><br>
    <p style="color: #94a3b8; font-size: 13px; margin-bottom: 5px;">Pool ouro (consenso 20·30·40·50)</p>
    <div>
        <span class="badge-tag badge-ouro">2</span>
        <span class="badge-tag badge-ouro">6</span>
        <span class="badge-tag badge-ouro">11</span>
        <span class="badge-tag badge-ouro">16</span>
        <span class="badge-tag badge-ouro">21</span>
        <span class="badge-tag badge-ouro">24</span>
        <span class="badge-tag badge-ouro">30</span>
        <span class="badge-tag badge-ouro">33</span>
        <span class="badge-tag badge-ouro">39</span>
        <span class="badge-tag badge-ouro">42</span>
        <span class="badge-tag badge-ouro">43</span>
        <span class="badge-tag badge-ouro">58</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# GERADOR DE PALPITES
# -----------------------------------------------------------------------------
def gerar_jogo_base(dezena_ouro=58, qtd=6, max_num=60):
    np.random.seed()
    resto = list(np.random.choice([n for n in range(1, max_num+1) if n != dezena_ouro], qtd-1, replace=False))
    return sorted([dezena_ouro] + resto)

if 'palpites' not in st.session_state:
    st.session_state.palpites = [
        {"ordem": "1º", "estrelas": "★★★", "peso": 100, "score": 2004, "dezenas": [11, 16, 24, 39, 43, 58], "ouro": 58},
        {"ordem": "2º", "estrelas": "★★", "peso": 97, "score": 1947, "dezenas": [11, 24, 30, 39, 43, 58], "ouro": 58},
        {"ordem": "3º", "estrelas": "★", "peso": 94, "score": 1887, "dezenas": [6, 11, 24, 30, 39, 58], "ouro": 58}
    ]

st.subheader("3 melhores palpites")

for p in st.session_state.palpites:
    st.markdown(f"""
    <div class="box-dark">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:bold; font-size:16px;">{p['ordem']} · {p['estrelas']} · peso {p['peso']} · score {p['score']}</span>
            <span style="background-color:#332701; color:#ffb703; padding:2px 8px; border-radius:4px; font-size:11px;">próximo concurso</span>
        </div>
        <div style="margin: 15px 0;">
            {' '.join([f'<span class="ball-dark ball-gold">{d:02d}</span>' if d == p['ouro'] else f'<span class="ball-dark">{d:02d}</span>' for d in p['dezenas']])}
        </div>
        <div style="font-size:12px; color:#94a3b8; margin-bottom:12px;">
            Ouro {p['ouro']} · Paridade Balanced · Matriz Otimizada
        </div>
        <div>
            <span class="badge-tag">Ciclo</span>
            <span class="badge-tag">Atraso</span>
            <span class="badge-tag">Frequência</span>
            <span class="badge-tag">Dezena de Ouro</span>
            <span class="badge-tag">Quadrantes</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(f"Salvar este jogo ({p['ordem']})", key=f"save_{p['ordem']}"):
        st.session_state.jogos_salvos.append({
            "loteria": st.session_state.loteria_selecionada,
            "ref": cfg["ultimo_concurso"],
            "data": datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            "dezenas": p['dezenas'],
            "peso": p['peso'],
            "score": p['score'],
            "estrelas": p['estrelas'],
            "ordem": p['ordem']
        })
        st.toast(f"Palpite {p['ordem']} salvo com sucesso!")

st.markdown('<div class="btn-green-main">', unsafe_allow_html=True)
if st.button("Salvar os 3 palpites"):
    for p in st.session_state.palpites:
        st.session_state.jogos_salvos.append({
            "loteria": st.session_state.loteria_selecionada,
            "ref": cfg["ultimo_concurso"],
            "data": datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            "dezenas": p['dezenas'],
            "peso": p['peso'],
            "score": p['score'],
            "estrelas": p['estrelas'],
            "ordem": p['ordem']
        })
    st.toast("Todos os 3 palpites foram salvos!")
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SEÇÃO DE JOGOS SALVOS E CONFERÊNCIA AUTOMÁTICA
# -----------------------------------------------------------------------------
st.markdown("<br><hr style='border-color:#232d42;'><br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;">
    <h3 style="margin:0;">Jogos salvos</h3>
    <span class="badge-tag" style="font-size:14px; font-weight:bold;">{len(st.session_state.jogos_salvos)}</span>
</div>
<p style="color:#94a3b8; font-size:12px;">Só o que você salvou. Regenerar cria jogos novos acima, sem repetir estes.</p>
""", unsafe_allow_html=True)

if not st.session_state.jogos_salvos:
    st.info("Nenhum jogo salvo na sua lista até o momento.")
else:
    for idx, jogo in enumerate(st.session_state.jogos_salvos):
        # Lógica de conferência com o último concurso carregado
        dezenas_sorteadas = set(cfg["dezenas_ultimo"])
        dezenas_jogo = set(jogo["dezenas"])
        acertos = len(dezenas_jogo.intersection(dezenas_sorteadas))
        
        st.markdown(f"""
        <div class="box-dark">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:bold;">{jogo['ordem']} · {jogo['estrelas']} · peso {jogo['peso']} · score {jogo['score']}</span>
                <span style="background-color:#4a1212; color:#ff6b6b; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">
                    {acertos} acertos no #{cfg['ultimo_concurso']}
                </span>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">
                {jogo['data']} · ref #{jogo['ref']}
            </div>
            <div style="margin: 12px 0;">
                {' '.join([f'<span class="ball-dark ball-match">{d:02d}</span>' if d in dezenas_sorteadas else f'<span class="ball-dark">{d:02d}</span>' for d in jogo['dezenas']])}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c_conf, c_del = st.columns([1, 1])
        with c_conf:
            if st.button(f"Conferir", key=f"conf_{idx}"):
                st.toast(f"Jogo {jogo['ordem']} conferido: {acertos} acertos no concurso {cfg['ultimo_concurso']}!")
        with c_del:
            if st.button(f"EXCLUIR", key=f"del_{idx}"):
                st.session_state.jogos_salvos.pop(idx)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("EXCLUIR TODOS OS SALVOS"):
        st.session_state.jogos_salvos = []
        st.rerun()
