def get_concurso_dezenas(lottery_name, concurso_num):
    # 1. Tentar mapear pelo nosso histórico na sessão
    try:
        history_lengths = {
            "Mega-Sena": (3051, 12),
            "Lotofácil": (3775, 10),
            "Lotomania": (2971, 8),
            "Quina": (7109, 14),
            "Dupla Sena": (3002, 5)
        }
        base_num, base_len = history_lengths[lottery_name]
        latest_concurso = base_num + (len(st.session_state.history[lottery_name]) - base_len)
        
        idx = latest_concurso - concurso_num
        if 0 <= idx < len(st.session_state.history[lottery_name]):
            raw_draw = st.session_state.history[lottery_name][idx]
            return raw_draw, f"Histórico local (Concurso {concurso_num})"
    except Exception:
        pass
        
    # 2. Se não estiver no histórico local, buscar via API
    mapping = {
        "Mega-Sena": "megasena",
        "Lotofácil": "lotofacil",
        "Lotomania": "lotomania",
        "Quina": "quina",
        "Dupla Sena": "duplasena"
    }
    api_name = mapping.get(lottery_name)
    if api_name:
        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        # Caixa Oficial
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_name}/{concurso_num}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=6)
            if response.status_code == 200:
                data = response.json()
                if lottery_name == "Dupla Sena":
                    dezenas1_raw = data.get("listaDezenas", [])
                    dezenas2_raw = data.get("listaDezenasSegundoSorteio", [])
                    if not dezenas2_raw and "listaDezenasSegundoSorteio" not in data:
                        dezenas2_raw = data.get("listaDezenas2", [])
                    d1 = sorted([int(x) for x in dezenas1_raw if str(x).isdigit()])
                    d2 = sorted([int(x) for x in dezenas2_raw if str(x).isdigit()])
                    if d1 and d2:
                        return [d1, d2], "API Oficial Caixa"
                else:
                    dezenas_raw = data.get("listaDezenas", [])
                    dezenas = sorted([int(x) for x in dezenas_raw if str(x).isdigit()])
                    if dezenas:
                        return dezenas, "API Oficial Caixa"
        except Exception:
            pass
            
        # Fallback Heroku
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{api_name}/{concurso_num}"
        try:
            response = requests.get(url_alt, headers=HEADERS, timeout=6)
            if response.status_code == 200:
                data = response.json()
                if lottery_name == "Dupla Sena":
                    dezenas1 = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                    dezenas2 = sorted([int(x) for x in data.get("dezenasSegundoSorteio", []) if str(x).isdigit()])
                    if dezenas1 and dezenas2:
                        return [dezenas1, dezenas2], "API Fallback (Heroku)"
                else:
                    dezenas = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                    if dezenas:
                        return dezenas, "API Fallback (Heroku)"
        except Exception:
            pass
            
    return None, None

import streamlit as st
import pandas as pd
import numpy as np
import random
import json
import os
import requests
from datetime import datetime
import scipy.stats as stats
import io
from fpdf import FPDF
import itertools

# Configuração da página - adaptada para dispositivos móveis Android e telas pequenas
st.set_page_config(
    page_title="Loterias Caixa - Inteligência Estatística PRO",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização profissional personalizada (Cores da Caixa e design limpo)
st.markdown("""
<style>
    /* Estilos globais e fontes */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Roboto', sans-serif;
        background-color: #f7f9fc;
    }
    
    /* Títulos e Headers */
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1A365D;
        text-align: center;
        margin-bottom: 5px;
    }
    .subtitle {
        font-size: 1rem;
        color: #4A5568;
        text-align: center;
        margin-bottom: 25px;
    }
    
    /* Cartões de Loterias */
    .lottery-card {
        padding: 15px;
        border-radius: 12px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .mega-sena-bg { background: linear-gradient(135deg, #209853 0%, #17723E 100%); }
    .lotofacil-bg { background: linear-gradient(135deg, #930053 0%, #6E003C 100%); }
    .lotomania-bg { background: linear-gradient(135deg, #F5921E 0%, #D47913 100%); }
    .quina-bg { background: linear-gradient(135deg, #2F5496 0%, #1B365D 100%); }
    .dupla-sena-bg { background: linear-gradient(135deg, #A80000 0%, #7A0000 100%); }
    
    /* Dezenas Sorteadas (Círculos) */
    .ball-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin: 15px 0;
    }
    .ball {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.95rem;
        color: #2D3748;
        background: #FFFFFF;
        box-shadow: inset 0 -3px 0.15rem rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #E2E8F0;
    }
    .ball-mega { border-top: 3px solid #209853; }
    .ball-facil { border-top: 3px solid #930053; }
    .ball-mania { border-top: 3px solid #F5921E; }
    .ball-quina { border-top: 3px solid #2F5496; }
    .ball-dupla { border-top: 3px solid #A80000; }
    
    /* Tabs e Botões */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 700;
        transition: all 0.2s;
    }
    
    /* Badges de Hierarquia */
    .badge-supremo {
        background-color: #E2E8F0;
        color: #2D3748;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        border-left: 4px solid #3182CE;
    }
    .badge-tendencia {
        background-color: #E2E8F0;
        color: #2D3748;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        border-left: 4px solid #DD6B20;
    }
    .badge-cobertura {
        background-color: #E2E8F0;
        color: #2D3748;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        border-left: 4px solid #4A5568;
    }
</style>
""", unsafe_allow_html=True)

# ── PERSISTÊNCIA E SINCRONIZAÇÃO AUTOMÁTICA COM A CAIXA ─────────────────

def load_predictions():
    if os.path.exists("saved_predictions.json"):
        try:
            with open("saved_predictions.json", "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_predictions(preds):
    try:
        with open("saved_predictions.json", "w") as f:
            json.dump(preds, f)
    except Exception:
        pass

@st.cache_data(ttl=120)  # Cache de 2 minutos para evitar excesso de requisições
def fetch_latest_results_from_caixa(lottery_name):
    mapping = {
        "Mega-Sena": "megasena",
        "Lotofácil": "lotofacil",
        "Lotomania": "lotomania",
        "Quina": "quina",
        "Dupla Sena": "duplasena"
    }
    api_name = mapping.get(lottery_name)
    if not api_name:
        return None
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    # Tentativa 1: API Oficial do Portal de Loterias da Caixa
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_name}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        if response.status_code == 200:
            data = response.json()
            concurso = data.get("numero")
            data_sorteio = data.get("dataApuracao")
            
            valor_estimado = data.get("valorEstimadoProximoConcurso")
            valor_formatted = None
            if valor_estimado:
                try:
                    val = float(valor_estimado)
                    if val >= 1_000_000:
                        valor_formatted = f"R$ {val / 1_000_000:.1f} Milhão" if val < 2_000_000 else f"R$ {val / 1_000_000:.1f} Milhões"
                        valor_formatted = valor_formatted.replace(".0", "")
                    else:
                        valor_formatted = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except Exception:
                    pass
            
            if lottery_name == "Dupla Sena":
                dezenas1_raw = data.get("listaDezenas", [])
                dezenas2_raw = data.get("listaDezenasSegundoSorteio", [])
                if not dezenas2_raw and "listaDezenasSegundoSorteio" not in data:
                    dezenas2_raw = data.get("listaDezenas2", [])
                d1 = sorted([int(x) for x in dezenas1_raw if str(x).isdigit()])
                d2 = sorted([int(x) for x in dezenas2_raw if str(x).isdigit()])
                if d1 and d2:
                    return {"concurso": concurso, "dezenas": [d1, d2], "data": data_sorteio, "valor": valor_formatted, "fonte": "Caixa Oficial"}
            else:
                dezenas_raw = data.get("listaDezenas", [])
                dezenas = sorted([int(x) for x in dezenas_raw if str(x).isdigit()])
                if dezenas:
                    return {"concurso": concurso, "dezenas": dezenas, "data": data_sorteio, "valor": valor_formatted, "fonte": "Caixa Oficial"}
    except Exception:
        pass
    
    # Tentativa 2: API de Fallback (LoteriasCaixa Heroku API)
    try:
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{api_name}/latest"
        response = requests.get(url_alt, headers=HEADERS, timeout=6)
        if response.status_code == 200:
            data = response.json()
            concurso = data.get("concurso")
            data_sorteio = data.get("data")
            
            valor_estimado = data.get("valorEstimadoProximoConcurso")
            valor_formatted = None
            if valor_estimado:
                try:
                    val = float(valor_estimado)
                    if val >= 1_000_000:
                        valor_formatted = f"R$ {val / 1_000_000:.1f} Milhão" if val < 2_000_000 else f"R$ {val / 1_000_000:.1f} Milhões"
                        valor_formatted = valor_formatted.replace(".0", "")
                    else:
                        valor_formatted = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except Exception:
                    pass
            
            if lottery_name == "Dupla Sena":
                dezenas1 = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                dezenas2 = sorted([int(x) for x in data.get("dezenasSegundoSorteio", []) if str(x).isdigit()])
                if dezenas1 and dezenas2:
                    return {"concurso": concurso, "dezenas": [dezenas1, dezenas2], "data": data_sorteio, "valor": valor_formatted, "fonte": "Mirror Heroku"}
            else:
                dezenas = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                if dezenas:
                    return {"concurso": concurso, "dezenas": dezenas, "data": data_sorteio, "valor": valor_formatted, "fonte": "Mirror Heroku"}
    except Exception:
        pass

    # Tentativa 3: API Terciária de Backup (Guidi Mirror API)
    try:
        url_alt2 = f"https://api.guidi.dev.br/loteria/{api_name}/ultimo"
        response = requests.get(url_alt2, headers=HEADERS, timeout=6)
        if response.status_code == 200:
            data = response.json()
            concurso = data.get("numero")
            data_sorteio = data.get("data")
            
            if lottery_name == "Dupla Sena":
                dezenas1_raw = data.get("listaDezenas", [])
                dezenas2_raw = data.get("listaDezenasSegundoSorteio", [])
                d1 = sorted([int(x) for x in dezenas1_raw if str(x).isdigit()])
                d2 = sorted([int(x) for x in dezenas2_raw if str(x).isdigit()])
                if d1 and d2:
                    return {"concurso": concurso, "dezenas": [d1, d2], "data": data_sorteio, "valor": None, "fonte": "Mirror Guidi"}
            else:
                dezenas_raw = data.get("listaDezenas", [])
                dezenas = sorted([int(x) for x in dezenas_raw if str(x).isdigit()])
                if dezenas:
                    return {"concurso": concurso, "dezenas": dezenas, "data": data_sorteio, "valor": None, "fonte": "Mirror Guidi"}
    except Exception:
        pass
        
    return None

def auto_update_history():
    if "history" not in st.session_state:
        st.session_state.history = get_initial_history()
    
    if "latest_info" not in st.session_state:
        st.session_state.latest_info = {
            "Mega-Sena": {"concurso": 3051, "valor": "R$ 58 Milhões", "data": "30/08/2026"},
            "Lotofácil": {"concurso": 3775, "valor": "R$ 2 Milhões", "data": "30/08/2026"},
            "Lotomania": {"concurso": 2971, "valor": "R$ 16 Milhões", "data": "02/09/2026"},
            "Quina": {"concurso": 7109, "valor": "R$ 15 Milhões", "data": "03/09/2026"},
            "Dupla Sena": {"concurso": 3002, "valor": "R$ 1.8 Milhão", "data": "28/08/2026"}
        }
        
    history_lengths = {
        "Mega-Sena": (3051, 12),
        "Lotofácil": (3775, 10),
        "Lotomania": (2971, 8),
        "Quina": (7109, 14),
        "Dupla Sena": (3002, 5)
    }
    
    # Tenta atualizar de forma transparente cada uma das loterias
    for lottery_name in ["Mega-Sena", "Lotofácil", "Lotomania", "Quina", "Dupla Sena"]:
        try:
            latest = fetch_latest_results_from_caixa(lottery_name)
            if latest:
                current_history = st.session_state.history[lottery_name]
                latest_dezenas = latest["dezenas"]
                latest_concurso = latest["concurso"]
                
                base_num, base_len = history_lengths[lottery_name]
                current_latest_concurso = base_num + (len(current_history) - base_len)
                
                if latest_concurso > current_latest_concurso:
                    # Genuinamente novo concurso, inserimos sequencialmente para evitar furos na base
                    start_c = current_latest_concurso + 1
                    end_c = latest_concurso
                    if end_c - start_c > 15:
                        start_c = end_c - 15
                    for c_num in range(start_c, end_c + 1):
                        temp_latest = base_num + (len(st.session_state.history[lottery_name]) - base_len)
                        if c_num > temp_latest:
                            if c_num == latest_concurso:
                                st.session_state.history[lottery_name].insert(0, latest_dezenas)
                            else:
                                draw_data, _ = get_concurso_dezenas(lottery_name, c_num)
                                if draw_data:
                                    st.session_state.history[lottery_name].insert(0, draw_data)
                                else:
                                    break
                elif latest_concurso == current_latest_concurso:
                    # Se for o mesmo concurso, apenas atualizamos para corrigir possíveis desvios/erros locais
                    st.session_state.history[lottery_name][0] = latest_dezenas
                
                # Atualiza os dados do último concurso sorteado e prêmio dinâmico
                st.session_state.latest_info[lottery_name] = {
                    "concurso": latest["concurso"],
                    "valor": latest.get("valor") or st.session_state.latest_info[lottery_name]["valor"],
                    "data": latest.get("data") or st.session_state.latest_info[lottery_name]["data"]
                }
        except Exception:
            pass

# ── BANCO DE DADOS INICIAL INTEGRADO ──────────────────────────────────

@st.cache_data
def get_initial_history():
    return {
        "Mega-Sena": [
            [11, 15, 20, 21, 38, 48], # Concurso 3051 (30/08/2026)
            [11, 14, 30, 38, 49, 55], # Concurso 3050 (27/08/2026)
            [6, 13, 36, 43, 53, 55],  # Concurso 3049 (25/08/2026)
            [2, 6, 27, 39, 44, 50],   # Concurso 3048 (23/08/2026)
            [4, 18, 22, 26, 31, 58],  # Concurso 3047 (20/08/2026)
            [16, 23, 24, 33, 36, 52], # Concurso 3046 (18/08/2026)
            [23, 29, 33, 42, 43, 57], # Concurso 3045 (16/08/2026)
            [4, 15, 17, 40, 55, 58],  # Concurso 3044 (13/08/2026)
            [10, 11, 16, 37, 42, 53], # Concurso 3043 (11/08/2026)
            [2, 5, 10, 35, 40, 53],   # Concurso 3042 (09/08/2026)
            [16, 21, 24, 31, 43, 54], # Concurso 3041 (06/08/2026)
            [3, 16, 24, 30, 49, 54]    # Concurso 3040 (04/08/2026)
        ],
        "Lotofácil": [
            [1, 4, 5, 6, 8, 10, 11, 12, 13, 15, 17, 18, 19, 23, 25], # Concurso 3775 (30/08/2026)
            [1, 3, 4, 5, 6, 7, 9, 12, 14, 15, 16, 18, 19, 23, 24], # Concurso 3774 (28/08/2026)
            [3, 4, 7, 9, 11, 13, 14, 15, 17, 18, 20, 21, 22, 24, 25], # Concurso 3773 (27/08/2026)
            [3, 5, 6, 7, 8, 9, 11, 12, 14, 15, 18, 20, 21, 23, 25], # Concurso 3772 (26/08/2026)
            [2, 3, 4, 5, 9, 10, 11, 12, 15, 16, 17, 18, 21, 23, 25], # Concurso 3771 (25/08/2026)
            [1, 2, 4, 7, 8, 12, 13, 15, 16, 17, 18, 19, 23, 24, 25], # Concurso 3770 (24/08/2026)
            [1, 2, 3, 4, 5, 9, 10, 11, 15, 16, 17, 21, 23, 24, 25], # Concurso 3769 (23/08/2026)
            [2, 3, 4, 5, 6, 7, 10, 11, 12, 14, 15, 17, 20, 23, 24], # Concurso 3768 (21/08/2026)
            [2, 4, 6, 7, 9, 10, 11, 13, 14, 15, 16, 20, 21, 22, 23], # Concurso 3767 (20/08/2026)
            [1, 2, 3, 5, 8, 9, 11, 13, 14, 16, 17, 19, 21, 23, 24]  # Concurso 3766 (19/08/2026)
        ],
        "Lotomania": [
            [1, 2, 3, 6, 7, 18, 19, 20, 22, 25, 46, 49, 51, 63, 65, 68, 69, 86, 88, 92], # Concurso 2971 (02/09/2026)
            [7, 11, 15, 16, 17, 19, 28, 32, 37, 39, 44, 66, 70, 72, 80, 82, 85, 87, 92, 96], # Concurso 2970 (31/08/2026)
            [0, 13, 15, 21, 25, 38, 40, 47, 55, 56, 57, 58, 62, 68, 70, 75, 84, 86, 90, 99], # Concurso 2969 (28/08/2026)
            [0, 2, 5, 13, 16, 19, 30, 35, 38, 43, 44, 48, 56, 60, 63, 65, 74, 76, 92, 95], # Concurso 2968 (26/08/2026)
            [4, 7, 10, 18, 27, 29, 38, 41, 44, 56, 57, 67, 75, 81, 85, 90, 91, 94, 96, 98], # Concurso 2967 (25/08/2026)
            [14, 17, 20, 23, 26, 31, 34, 36, 38, 46, 53, 59, 60, 63, 71, 73, 77, 84, 95, 97], # Concurso 2966 (21/08/2026)
            [5, 15, 16, 22, 27, 32, 40, 44, 49, 52, 61, 62, 63, 65, 69, 72, 78, 83, 86, 93], # Concurso 2965 (19/08/2026)
            [7, 13, 14, 16, 25, 29, 33, 40, 41, 44, 56, 60, 61, 64, 67, 68, 73, 77, 83, 85]  # Concurso 2964 (17/08/2026)
        ],
        "Quina": [
            [27, 30, 61, 66, 70], # Concurso 7109 (03/09/2026)
            [4, 28, 29, 30, 67],  # Concurso 7108 (02/09/2026)
            [33, 36, 49, 61, 71], # Concurso 7107 (01/09/2026)
            [18, 23, 34, 49, 69], # Concurso 7106 (31/08/2026)
            [2, 33, 41, 48, 78],  # Concurso 7105 (30/08/2026)  # Concurso 7105 (30/08/2026)
            [7, 51, 61, 66, 75],  # Concurso 7104 (28/08/2026)
            [20, 25, 26, 59, 68], # Concurso 7103 (27/08/2026)
            [11, 14, 38, 43, 77], # Concurso 7102 (26/08/2026)
            [32, 48, 52, 62, 68], # Concurso 7101 (25/08/2026)
            [27, 34, 36, 48, 76], # Concurso 7100 (24/08/2026)
            [27, 33, 35, 42, 59], # Concurso 7099 (23/08/2026)
            [4, 17, 21, 38, 47],  # Concurso 7098 (21/08/2026)
            [14, 16, 65, 71, 76], # Concurso 7097 (20/08/2026)
            [10, 29, 43, 47, 51]  # Concurso 7096 (19/08/2026)
        ],
        "Dupla Sena": [
            [[6, 19, 22, 27, 41, 46], [7, 11, 12, 13, 25, 28]], # Concurso 3002 (28/08/2026)
            [[5, 8, 10, 22, 43, 48], [1, 14, 25, 33, 40, 47]], # Concurso 3001 (26/08/2026)
            [[13, 14, 17, 39, 42, 46], [2, 6, 10, 15, 32, 40]], # Concurso 3000 (25/08/2026)
            [[1, 10, 12, 37, 39, 44], [3, 15, 21, 28, 42, 49]], # Concurso 2999 (21/08/2026)
            [[5, 11, 24, 30, 31, 36], [6, 8, 20, 21, 45, 46]]  # Concurso 2998 (19/08/2026)
        ]
    }

# ── RESULTADOS HISTÓRICOS DE LOTERIAS ESPECIAIS (BANCO DE DADOS FIXO) ──

@st.cache_data
def get_special_history():
    return {
        "Mega da Virada": [
            [10, 14, 16, 30, 46, 50],
            [4, 5, 10, 34, 58, 59],
            [12, 15, 23, 32, 33, 46],
            [2, 18, 31, 42, 51, 56],
            [3, 35, 38, 40, 57, 58],
            [10, 25, 31, 37, 38, 57],
            [1, 15, 23, 27, 33, 52]
        ],
        "Lotofácil da Independência": [
            [1, 3, 5, 7, 8, 9, 10, 11, 12, 15, 16, 17, 20, 22, 24],
            [1, 2, 3, 5, 6, 8, 12, 13, 15, 16, 18, 20, 21, 22, 25],
            [1, 3, 4, 7, 8, 10, 11, 12, 15, 16, 17, 18, 20, 21, 22],
            [1, 2, 4, 6, 7, 9, 10, 13, 14, 16, 18, 20, 21, 23, 25],
            [1, 3, 5, 6, 9, 10, 11, 12, 13, 17, 18, 20, 21, 22, 25]
        ],
        "Quina de São João": [
            [1, 15, 22, 43, 50],
            [7, 12, 42, 51, 74],
            [14, 26, 32, 55, 69],
            [2, 17, 34, 49, 79],
            [13, 23, 39, 61, 75]
        ],
        "Dupla Sena de Páscoa": [
            [[3, 15, 23, 32, 33, 45], [4, 8, 12, 21, 30, 48]],
            [[1, 11, 20, 23, 35, 49], [2, 14, 25, 33, 39, 45]],
            [[10, 14, 18, 19, 35, 42], [5, 11, 16, 17, 30, 48]]
        ]
    }

USER_FIXED_LOTOMANIA = [
    7, 11, 13, 14, 16, 19, 20, 25, 29, 31, 33, 38, 40, 41, 44, 47, 49,
    56, 59, 60, 61, 63, 64, 67, 68, 73, 77, 83, 84, 85, 91, 93, 95, 97
]

USER_FIXED_MEGA_SENA = [
    5, 12, 23, 33, 44, 51, 8, 15, 27, 30, 38, 47, 54, 58, 2, 18, 25, 35, 49, 60
]

USER_FIXED_QUINA = [
    15, 38, 54, 7, 29, 41, 62, 73, 4, 19, 25, 33, 47, 58, 67, 71, 2, 11, 22, 44
]

USER_FIXED_DUPLA_SENA = [
    33, 38, 44, 16, 29, 42, 14, 19, 25, 47, 11, 23, 31, 41, 4, 7, 17, 32, 43, 45
]

if "history" not in st.session_state:
    st.session_state.history = get_initial_history()
auto_update_history()

if "saved_predictions" not in st.session_state:
    st.session_state.saved_predictions = load_predictions()


# ── ENGENHARIA DE PROGNÓSTICOS - MOTORES AVANÇADOS ─────────────────────

def advanced_mathematical_filters(selected_numbers, lottery_type):
    """
    Filtros Matemáticos Avançados:
    1. Filtro de Espaçamento Delta (Dave Muse's Delta System)
    2. Filtro de Modelos de Linha Gianella (Renato Gianella's Geometry of Chance)
    """
    if not selected_numbers:
        return True
    
    nums = sorted(selected_numbers)
    n = len(nums)
    
    # 1. FILTRO DE ESPAÇAMENTO DELTA (Para Mega-Sena, Dupla Sena, Quina)
    if lottery_type in ["Mega-Sena", "Dupla Sena", "Quina"]:
        deltas = []
        deltas.append(nums[0])
        for i in range(1, n):
            deltas.append(nums[i] - nums[i-1])
            
        max_delta = max(deltas)
        mean_delta = np.mean(deltas)
        
        # Guard rails based on Delta Lotto System
        if max_delta > 28:
            return False
        if mean_delta < 3.0 or mean_delta > 15.0:
            return False
            
        # Pelo menos 4 deltas <= 15 (Mega/Dupla) ou 3 deltas <= 15 (Quina)
        required_small = 4 if n == 6 else 3
        if sum(1 for d in deltas if d <= 15) < required_small:
            return False

    # 2. FILTRO DE MODELOS DE LINHA GIANELLA (The Geometry of Chance)
    if lottery_type in ["Mega-Sena", "Dupla Sena"]:
        # Bins of 10
        bins = [0] * 6 if lottery_type == "Mega-Sena" else [0] * 5
        for val in nums:
            bin_idx = min(int((val - 1) // 10), len(bins) - 1)
            bins[bin_idx] += 1
        t = tuple(sorted(bins, reverse=True))
        
        # Golden templates (91% of historical draws)
        if lottery_type == "Mega-Sena":
            valid_templates = {
                (2, 2, 1, 1, 0, 0),
                (2, 1, 1, 1, 1, 0),
                (3, 1, 1, 1, 0, 0),
                (3, 2, 1, 0, 0, 0)
            }
        else: # Dupla Sena
            valid_templates = {
                (2, 2, 1, 1, 0),
                (2, 1, 1, 1, 1),
                (3, 1, 1, 1, 0),
                (3, 2, 1, 0, 0)
            }
        if t not in valid_templates:
            return False
            
    elif lottery_type == "Lotofácil":
        # Bins of 5 (lines of 5)
        bins = [0] * 5
        for val in nums:
            bin_idx = min(int((val - 1) // 5), 4)
            bins[bin_idx] += 1
        t = tuple(sorted(bins, reverse=True))
        # Top line templates (covering over 90% of draws)
        valid_templates = {
            (4, 4, 3, 2, 2),
            (4, 3, 3, 3, 2),
            (5, 3, 3, 2, 2),
            (5, 4, 2, 2, 2),
            (3, 3, 3, 3, 3)
        }
        if t not in valid_templates:
            return False
            
    elif lottery_type == "Quina":
        # Bins of 10 (8 bins)
        bins = [0] * 8
        for val in nums:
            bin_idx = min(int((val - 1) // 10), 7)
            bins[bin_idx] += 1
        t = tuple(sorted(bins, reverse=True))
        max_in_bin = t[0]
        covered_bins = sum(1 for x in t if x > 0)
        if max_in_bin > 3 or covered_bins < 3:
            return False
            
    elif lottery_type == "Lotomania":
        # Bins of 10 (10 bins)
        bins = [0] * 10
        for val in nums:
            bin_idx = min(int((val - 1) // 10), 9)
            bins[bin_idx] += 1
        # Prevent extreme clustering (e.g. no row should have more than 7 numbers)
        # Ajustado após estudo avançado das linhas horizontais (linhas/bins de 10)
        for count in bins:
            if count > 7:
                return False
                
    return True


def statistical_guardian(selected_numbers, lottery_type):
    """
    Guardião Estatístico PRO: Bloqueia ruídos e valida jogos sob testes formais.
    Aplica teste do Qui-Quadrado para dispersão uniforme e impede ajuste excessivo.
    CORREÇÃO TÉCNICA: Ajustado f_exp para evitar erro de assinatura no SciPy.
    """
    if not selected_numbers:
        return True, 0.0
    
    # 1. Teste de Qui-Quadrado de Dispersão Espacial (Filtro Uniforme com Quadrantes de Taufic Darhal)
    observed = [0, 0, 0, 0]
    for val in selected_numbers:
        if lottery_type == "Lotofácil":
            if 1 <= val <= 7: observed[0] += 1
            elif 8 <= val <= 13: observed[1] += 1
            elif 14 <= val <= 19: observed[2] += 1
            elif 20 <= val <= 25: observed[3] += 1
        elif lottery_type == "Lotomania":
            v = 0 if val == 0 else val
            if 0 <= v <= 24: observed[0] += 1
            elif 25 <= v <= 49: observed[1] += 1
            elif 50 <= v <= 74: observed[2] += 1
            elif 75 <= v <= 99: observed[3] += 1
        elif lottery_type == "Mega-Sena":
            if 1 <= val <= 15: observed[0] += 1
            elif 16 <= val <= 30: observed[1] += 1
            elif 31 <= val <= 45: observed[2] += 1
            elif 46 <= val <= 60: observed[3] += 1
        elif lottery_type == "Quina":
            if 1 <= val <= 20: observed[0] += 1
            elif 21 <= val <= 40: observed[1] += 1
            elif 41 <= val <= 60: observed[2] += 1
            elif 61 <= val <= 80: observed[3] += 1
        elif lottery_type == "Dupla Sena":
            if 1 <= val <= 12: observed[0] += 1
            elif 13 <= val <= 25: observed[1] += 1
            elif 26 <= val <= 38: observed[2] += 1
            elif 39 <= val <= 50: observed[3] += 1
            
    expected_freq = len(selected_numbers) / 4
    
    chi2_stat, p_val = stats.chisquare(observed, f_exp=[expected_freq]*4)
    
    # Se p-value for extremamente baixo, as dezenas estão concentradas demais (bloqueia sinal fraco)
    is_valid = p_val >= 0.01
    if is_valid:
        is_valid = advanced_mathematical_filters(selected_numbers, lottery_type)
    return is_valid, p_val

def detect_lotomania_wave(history):
    """
    Técnica Específica: Onda da Lotomania.
    Detecta início de onda, controla duração (max 3 concursos) e valida potencial.
    """
    if len(history) < 3:
        return []
    
    flat_draws = [n for sub in history[:3] for n in sub]
    freq = pd.Series(flat_draws).value_counts()
    
    # Números que apareceram seguidamente nos últimos 2-3 concursos entram na "onda de calor"
    wave_numbers = [int(num) for num, count in freq.items() if count >= 2]
    return wave_numbers[:10]

def anti_popularity_filter(game, lottery_type, strict=False):
    """
    Motor Anti-Popularidade: Penaliza combinações de alta redundância ou óbvias
    para evitar divisão de possíveis prêmios em faixas de acerto.
    Em loterias especiais (strict=True), o motor é 300% mais severo.
    """
    # 1. Penalização de Consecutivos Extremos
    consecutives = 0
    for i in range(len(game)-1):
        if game[i+1] - game[i] == 1:
            consecutives += 1
            
    # Se tiver mais que 3 números em sequência direta, penaliza
    if consecutives > 3:
        return False
        
    # 2. Penalização de Somatórios Extremos (Fora da curva de Gauss)
    soma = sum(game)
    if lottery_type == "Mega-Sena" and not (150 <= soma <= 210):
        return False
    if lottery_type == "Lotofácil" and not (160 <= soma <= 220):
        return False
        
    # 3. Filtro de Sorteios Especiais: Sem acúmulo excessivo de datas (números <= 31)
    if strict:
        dates_count = len([n for n in game if n <= 31])
        if lottery_type == "Mega-Sena" and dates_count > 3:
            return False
        if lottery_type == "Lotofácil" and dates_count > 10:
            return False
            
    return True

# ── GERADORES E FECHAMENTOS POR MODALIDADE ───────────────────────────

def greedy_set_cover(history, k=15, max_val=25):
    selected = []
    uncovered = set(range(len(history)))
    is_lotomania = (max_val == 100)
    eligible = list(range(100)) if is_lotomania else list(range(1, max_val + 1))
    appearances = {i: set() for i in eligible}
    
    for idx, draw in enumerate(history):
        # Desempacota se for Dupla Sena
        actual_draw = draw[0] if isinstance(draw[0], list) else draw
        for val in actual_draw:
            if val in appearances:
                appearances[val].add(idx)
                
    while len(selected) < k and uncovered:
        best_val = None
        best_covered = set()
        for val, idxs in appearances.items():
            if val in selected:
                continue
            covered = idxs.intersection(uncovered)
            if len(covered) > len(best_covered):
                best_covered = covered
                best_val = val
        if best_val is None:
            flat = [num for sub in history for num in (sub[0] if isinstance(sub[0], list) else sub)]
            counts = pd.Series(flat).value_counts()
            for val in counts.index:
                if val not in selected and len(selected) < k:
                    selected.append(int(val))
            break
        selected.append(best_val)
        uncovered = uncovered - best_covered
        
    # Garantia de preenchimento caso a amostragem seja muito pequena para cobrir k candidatos
    if len(selected) < k:
        flat = [num for sub in history for num in (sub[0] if isinstance(sub[0], list) else sub)]
        counts = pd.Series(flat).value_counts()
        for val in counts.index:
            if val not in selected and len(selected) < k:
                selected.append(int(val))
        # Se ainda assim faltar números, completa sequencialmente
        for i in eligible:
            if len(selected) < k and i not in selected:
                selected.append(i)
                
    return sorted(selected)

def calculate_markov(history, max_val=60):
    is_lotomania = (max_val == 100)
    eligible = list(range(100)) if is_lotomania else list(range(1, max_val + 1))
    transitions = {i: {j: 0 for j in eligible} for i in eligible}
    for idx in range(len(history) - 1):
        curr_draw = history[idx][0] if isinstance(history[idx][0], list) else history[idx]
        next_draw = history[idx + 1][0] if isinstance(history[idx + 1][0], list) else history[idx + 1]
        for num_curr in curr_draw:
            if num_curr in transitions:
                for num_next in next_draw:
                    if num_next in transitions[num_curr]:
                        transitions[num_curr][num_next] += 1
    return transitions

def get_markov_predictions(last_draw, transitions, k=5):
    scores = {}
    for num in last_draw:
        if num in transitions:
            for follower, count in transitions[num].items():
                scores[follower] = scores.get(follower, 0) + count
    sorted_followers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [num for num, score in sorted_followers[:k]]


def get_unified_weights(lottery_type, history, last_draw):
    max_val = 25 if lottery_type == "Lotofácil" else (50 if lottery_type == "Dupla Sena" else (60 if lottery_type == "Mega-Sena" else (100 if lottery_type == "Lotomania" else 80)))
    window_size = 30 if lottery_type == "Lotofácil" else 50
    hist = history[:window_size]
    
    # ── MOTORES TEMPORAIS DE MULTI-ESCALA PERSONALIZADOS ──
    # Particularidades temporais por Loteria para redefinir pesos e mitigar ruídos
    if lottery_type == "Lotofácil":
        windows = [10, 30]
        weights_win = [0.60, 0.40] # 60% peso no curtíssimo prazo, 40% no longo recente
    elif lottery_type == "Lotomania":
        windows = [30, 50]
        weights_win = [0.60, 0.40]
    elif lottery_type == "Mega-Sena":
        windows = [30, 50, 100]
        weights_win = [0.40, 0.35, 0.25] # 40% curto, 35% médio, 25% longo prazo
    else: # Quina / Dupla Sena
        windows = [30, 50]
        weights_win = [0.50, 0.50]
        
    eligible_numbers = list(range(100)) if lottery_type == "Lotomania" else list(range(1, max_val + 1))
        
    score_freq = {i: 0.0 for i in eligible_numbers}
    for win_size, win_w in zip(windows, weights_win):
        # Escala dinâmica adaptada ao tamanho do histórico na memória do app
        w_size = min(win_size, len(history))
        hist_subset = history[:w_size]
        
        freqs_win = {i: 0 for i in eligible_numbers}
        for draw in hist_subset:
            if lottery_type == "Dupla Sena":
                actual_draw = draw[0] + draw[1] if isinstance(draw[0], list) else draw
            else:
                actual_draw = draw
            for val in actual_draw:
                if val in freqs_win:
                    freqs_win[val] += 1
                    
        max_f = max(freqs_win.values()) if freqs_win.values() else 1
        min_f = min(freqs_win.values()) if freqs_win.values() else 0
        range_f = max_f - min_f if max_f != min_f else 1
        
        for num in eligible_numbers:
            norm_f = (freqs_win[num] - min_f) / range_f
            score_freq[num] += norm_f * win_w
            
    # 2. Atraso (Gaps)
    gaps = {i: window_size for i in eligible_numbers}
    for idx, draw in enumerate(hist):
        if lottery_type == "Dupla Sena":
            actual_draw = draw[0] + draw[1] if isinstance(draw[0], list) else draw
        else:
            actual_draw = draw
        for val in actual_draw:
            if val in gaps and gaps[val] == window_size:
                gaps[val] = idx
                
    max_g = max(gaps.values()) if gaps.values() else 1
    min_g = min(gaps.values()) if gaps.values() else 0
    range_g = max_g - min_g if max_g != min_g else 1
    score_atraso = {num: (g - min_g) / range_g for num, g in gaps.items()}
    
    # 3. Ciclo das Dezenas
    current_cycle_numbers = set()
    for draw in history:
        actual_draw = draw[0] + draw[1] if lottery_type == "Dupla Sena" and isinstance(draw[0], list) else draw
        current_cycle_numbers.update(actual_draw)
        if len(current_cycle_numbers) == max_val:
            break
    pending_numbers = set(eligible_numbers) - current_cycle_numbers
    score_ciclo = {i: (1.0 if i in pending_numbers else 0.2) for i in eligible_numbers}
    
    # 4. Distribuição (Paridades + Baixas/Altas + Moldura)
    score_dist = {i: 1.0 for i in eligible_numbers}
    if lottery_type == "Lotofácil":
        moldura = [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25]
        score_dist = {i: (1.0 if i in moldura else 0.5) for i in eligible_numbers}
    elif lottery_type == "Mega-Sena":
        score_dist = {i: (1.0 if i % 10 not in [2, 6, 0] else 0.05) for i in eligible_numbers}
    elif lottery_type == "Quina":
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79]
        score_dist = {i: (1.0 if i in primes else 0.6) for i in eligible_numbers}
    elif lottery_type == "Dupla Sena":
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        score_dist = {i: (1.0 if i in primes else 0.6) for i in eligible_numbers}
        
    # 5. Repetição do Concurso Anterior
    flat_last = []
    if last_draw:
        if isinstance(last_draw[0], list):
            flat_last = last_draw[0] + last_draw[1]
        else:
            flat_last = last_draw
    score_anterior = {i: (1.0 if i in flat_last else 0.1) for i in eligible_numbers}
    
    # Pesos do modelo unificado recomendados pelo especialista
    weights_map = {
        "Lotofácil":   {"freq": 0.40, "atraso": 0.20, "ciclo": 0.15, "dist": 0.15, "anterior": 0.10},
        "Dupla Sena":  {"freq": 0.40, "atraso": 0.20, "ciclo": 0.15, "dist": 0.15, "anterior": 0.10},
        "Mega-Sena":   {"freq": 0.25, "atraso": 0.25, "ciclo": 0.20, "dist": 0.20, "anterior": 0.10},
        "Quina":       {"freq": 0.20, "atraso": 0.25, "ciclo": 0.25, "dist": 0.20, "anterior": 0.10}
    }
    
    p = weights_map.get(lottery_type, {"freq": 0.20, "atraso": 0.25, "ciclo": 0.25, "dist": 0.20, "anterior": 0.10})
    
    final_weights = {}
    for i in eligible_numbers:
        w = (score_freq[i] * p["freq"] +
             score_atraso[i] * p["atraso"] +
             score_ciclo[i] * p["ciclo"] +
             score_dist[i] * p["dist"] +
             score_anterior[i] * p["anterior"])
        final_weights[i] = max(float(w), 0.01)
        
    # 6. Sinergia de Transição de Frequência + Cadeia de Markov (Evolução Gular Cruzada para TODAS as Loterias)
    if len(history) >= 11:
        f_curr = {i: 0 for i in eligible_numbers}
        for draw in history[0:10]:
            actual_draw = draw[0] + draw[1] if lottery_type == "Dupla Sena" and isinstance(draw[0], list) else draw
            for num in actual_draw:
                if num in f_curr: f_curr[num] += 1
                
        f_prev = {i: 0 for i in eligible_numbers}
        for draw in history[1:11]:
            actual_draw = draw[0] + draw[1] if lottery_type == "Dupla Sena" and isinstance(draw[0], list) else draw
            for num in actual_draw:
                if num in f_prev: f_prev[num] += 1
                
        last_d = history[0][0] + history[0][1] if lottery_type == "Dupla Sena" and isinstance(history[0][0], list) else history[0]
        prev_d = history[1][0] + history[1][1] if lottery_type == "Dupla Sena" and isinstance(history[1][0], list) else history[1]
        
        for i in eligible_numbers:
            curr_freq = f_curr.get(i, 0)
            prev_freq = f_prev.get(i, 0)
            
            st_prev = i in prev_d
            st_curr = i in last_d
            
            if st_prev and st_curr:
                m_state = "S to S"
            elif st_prev and not st_curr:
                m_state = "S to N"
            elif not st_prev and st_curr:
                m_state = "N to S"
            else:
                m_state = "N to N"
                
            # Aplicar multiplicadores baseados na tabela de inclusão e exclusão de Gular
            multiplier = 1.0
            
            # Padrão de Inclusão Excelente (Descida mas com retorno sequencial)
            if prev_freq > curr_freq and m_state == "N to S":
                multiplier = 1.45
            # Padrão de Inclusão Forte (Crescimento contínuo com S to S)
            elif prev_freq < curr_freq and m_state == "S to S":
                multiplier = 1.30
            # Padrão de Boa Inclusão (Estabilidade do fluxo com N to N ou N to S)
            elif prev_freq > curr_freq and m_state == "N to N":
                multiplier = 1.15
            # Padrões de Exclusão ou Resfriamento severo
            elif prev_freq < curr_freq and m_state == "S to N":
                multiplier = 0.55 # Evita dezenas em queda brusca simulada
                
            final_weights[i] = max(final_weights[i] * multiplier, 0.01)
            
    return final_weights


def calculate_dezena_de_ouro(lottery_type, history, last_draw):
    """
    Calcula a Dezena de Ouro: a dezena com maior combinação de frequência,
    baixo atraso e forte correlação condicional com as dezenas do último concurso.
    """
    max_val = 25 if lottery_type == "Lotofácil" else (50 if lottery_type == "Dupla Sena" else (60 if lottery_type == "Mega-Sena" else (80 if lottery_type == "Quina" else 100)))
    all_weights = get_unified_weights(lottery_type, history, last_draw)
    
    transitions = calculate_markov(history, max_val)
    flat_last = []
    if last_draw:
        if isinstance(last_draw[0], list):
            flat_last = last_draw[0] + last_draw[1]
        else:
            flat_last = last_draw
            
    eligible_numbers = list(range(100)) if lottery_type == "Lotomania" else list(range(1, max_val + 1))
    corr_scores = {i: 0 for i in eligible_numbers}
    for num in flat_last:
        if num in transitions:
            for follower, count in transitions[num].items():
                if follower in corr_scores:
                    corr_scores[follower] += count
                    
    max_corr = max(corr_scores.values()) if corr_scores.values() else 1
    if max_corr == 0: max_corr = 1
    
    best_num = 1 if lottery_type != "Lotomania" else 0
    best_score = -1.0
    for i in eligible_numbers:
        w = all_weights.get(i, 0.0)
        c = corr_scores.get(i, 0) / max_corr
        score = w * 0.6 + c * 0.4
        if score > best_score:
            best_score = score
            best_num = i
    return best_num

def get_xlsx_download_data(games, golden_ten, lottery_type):
    buffer = io.BytesIO()
    rows = []
    names = ["Supremo", "Tendência", "Cobertura", "Jogo 4 Extra", "Jogo 5 Extra"]
    for idx, g in enumerate(games):
        g_name = names[idx] if idx < len(names) else f"Jogo {idx+1}"
        rows.append({
            "Loteria": lottery_type,
            "Tipo de Palpite": g_name,
            "Dezenas": " ".join([f"{n:02d}" for n in g]),
            "Dezena de Ouro": f"{golden_ten:02d}"
        })
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Palpites')
    return buffer.getvalue()

def get_pdf_download_data(games, golden_ten, lottery_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "PORTAL DE INFERENCIA PRO", 0, 1, "C")
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"E-book Oficial de Palpites Otimizados -- {lottery_type.upper()}", 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 10, f"Dezena de Ouro (Ancora Ativa): {golden_ten:02d}", 0, 1)
    pdf.ln(5)
    
    names = ["O Supremo", "A Tendencia Cruzada", "A Cobertura de Seguranca", "Jogo Extra 4", "Jogo Extra 5"]
    for idx, g in enumerate(games):
        g_name = names[idx] if idx < len(names) else f"Jogo Extra {idx+1}"
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, f"Palpite {idx+1} -- {g_name}", 0, 1)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 10, "Dezenas: " + " -- ".join([f"{n:02d}" for n in g]), 0, 1)
        pdf.ln(3)
        
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Nota de Seguranca: Este sistema trata os historicos como dados para analise e otimizacao estatistica, sem afirmar que padroes historicos alteram a probabilidade matematica oficial de um sorteio ou garantem premios.")
    
    try:
        out = pdf.output(dest="S")
    except Exception:
        out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


# ── LOGICAS DE GERAÇÃO POR LOTERIA ────────────────────────────────────

# ── ALGORITMO DE SUPER-COBERTURA DE ALTA COBERTURA (MÉTODO CARLOS LOTERIA) ──

@st.cache_data
def find_best_combinations_numpy(history, k=20, top_n=10):
    """
    Algoritmo de altíssima performance usando álgebra linear vetorial (NumPy)
    para encontrar os subconjuntos de K dezenas que mais obtiveram 15 acertos
    na história da Lotofácil [Carlos Loteria].
    """
    num_draws = len(history)
    if num_draws == 0:
        return []
        
    # Converte histórico para matriz binária (num_draws, 25)
    draws_matrix = np.zeros((num_draws, 25), dtype=np.int8)
    for idx, draw in enumerate(history):
        for num in draw:
            if 1 <= num <= 25:
                draws_matrix[idx, num - 1] = 1
                
    # Gera todas as combinações de K dezenas (K em {20, 21, 22, 23})
    comb_list = list(itertools.combinations(range(25), k))
    num_combs = len(comb_list)
    
    # Converte combinações para matriz binária (num_combs, 25)
    combs_matrix = np.zeros((num_combs, 25), dtype=np.int8)
    for idx, comb in enumerate(comb_list):
        for pos in comb:
            combs_matrix[idx, pos] = 1
            
    # Produto Escalar Vetorial para calcular sobreposições instantâneas
    # overlap[i, j] é a quantidade de dezenas sorteadas que a combinação i acertou no sorteio j
    overlap = np.dot(combs_matrix, draws_matrix.T)
    
    # Identifica concursos que obtiveram exatamente 15 acertos
    hits_15 = (overlap == 15)
    hits_count = np.sum(hits_15, axis=1) # shape (num_combs,)
    
    # Ordena combinações por maior quantidade de acertos de 15 pontos
    top_indices = np.argsort(hits_count)[::-1][:top_n]
    
    results = []
    for rank, idx in enumerate(top_indices):
        comb_dezenas = [pos + 1 for pos in comb_list[idx]]
        comb_hits = int(hits_count[idx])
        
        # Calcula atraso atual (gap) e maior seca (max gap)
        match_draws_indices = np.where(hits_15[idx])[0]
        
        if len(match_draws_indices) > 0:
            atraso_atual = int(match_draws_indices[0])
            gaps = []
            gaps.append(int(match_draws_indices[0]))
            for i in range(1, len(match_draws_indices)):
                gaps.append(int(match_draws_indices[i] - match_draws_indices[i-1] - 1))
            gaps.append(int(num_draws - match_draws_indices[-1] - 1))
            max_atraso_historico = max(gaps)
        else:
            atraso_atual = num_draws
            max_atraso_historico = num_draws
            
        results.append({
            "ranking": rank + 1,
            "dezenas": comb_dezenas,
            "hits_15": comb_hits,
            "atraso_atual": atraso_atual,
            "max_atraso_historico": max_atraso_historico
        })
        
    return results



# ── SISTEMA DE OTIMIZAÇÃO MULTIOBJETIVO E DIVERSIFICAÇÃO MONTE CARLO (EDI v19) ──

def evaluate_game_score(game, lottery_type, all_weights):
    """
    Avaliação Adaptativa Multi-Objetivo (MOMC):
    1. Score de Consenso de Pesos (Markov + Frequência + Ciclo + Atraso)
    2. Entropia Espacial (Qui-Quadrado p-value)
    3. Distribuição de Paridades (Proporções Históricas de Elite)
    4. Guard Rails de Espaçamento (Dave Muse's Delta Lotto System)
    5. Geometria Espacial de Renato Gianella (Modelos de Linhas/Colunas)
    6. Geometria de Grelha Dinâmica (Linhas Horizontais e Verticais do Volante)
    7. Filtro de Miolo Central de Alta Densidade (Mega-Sena 21-40) - Incluindo Simetrias Ocultas
    8. Filtro da Cruz de Ouro (Lotofácil Diagonais Principais)
    9. Filtro da Cruz de Segurança (Lotomania Borda vs Centro)
    10. Filtro de Moldura Preditiva (Quina Extremos do Volante)
    11. Filtro de Simetria Lateral (Dupla Sena Esquerda vs Direita)
    12. Penalização de Consecutivos Extremos
    """
    if not game:
        return 0.0
        
    nums_sorted = sorted(game)
    n = len(nums_sorted)
    
    # 1. Consenso Ponderado (Atração Geral das Dezenas)
    base_score = sum(all_weights.get(x, 1.0) for x in nums_sorted)
    
    # 2. Entropia por Dispersão Espacial (Qui-Quadrado de Gauss)
    is_valid_guardian, p_val = statistical_guardian(nums_sorted, lottery_type)
    if is_valid_guardian:
        entropy_bonus = p_val * 4.0 # Favorece dispersão uniforme e natural
    else:
        entropy_bonus = -15.0 # Penaliza aglomerações e dezenas viciadas
        
    # 3. Equilíbrio de Paridades (Pares vs Ímpares)
    n_even = sum(1 for x in nums_sorted if x % 2 == 0)
    n_odd = n - n_even
    paridade_bonus = 0.0
    
    if lottery_type == "Lotofácil":
        if (n_even == 7 and n_odd == 8) or (n_even == 8 and n_odd == 7):
            paridade_bonus = 8.0 # Padrão recordista isolado (cobertura ideal)
        elif (n_even == 6 and n_odd == 9) or (n_even == 9 and n_odd == 6):
            paridade_bonus = 3.0
        else:
            paridade_bonus = -5.0
    elif lottery_type in ["Mega-Sena", "Dupla Sena"]:
        if n_even == 3 and n_odd == 3:
            paridade_bonus = 8.0 # Simetria perfeita de Gauss
        elif (n_even == 4 and n_odd == 2) or (n_even == 2 and n_odd == 4):
            paridade_bonus = 4.0
        else:
            paridade_bonus = -6.0
    elif lottery_type == "Quina":
        if (n_even == 3 and n_odd == 2) or (n_even == 2 and n_odd == 3):
            paridade_bonus = 6.0
        else:
            paridade_bonus = -4.0
    elif lottery_type == "Lotomania":
        if 22 <= n_even <= 28:
            paridade_bonus = 15.0 # Equilíbrio ideal de 50 dezenas
        elif 20 <= n_even <= 30:
            paridade_bonus = 5.0
        else:
            paridade_bonus = -15.0
            
    # 4. Spacing de Dave Muse (Sistema de Loterias Delta)
    delta_bonus = 0.0
    if lottery_type in ["Mega-Sena", "Dupla Sena", "Quina"]:
        deltas = [nums_sorted[0]]
        for idx in range(1, n):
            deltas.append(nums_sorted[idx] - nums_sorted[idx-1])
        max_delta = max(deltas)
        mean_delta = np.mean(deltas)
        
        if max_delta <= 24 and (4.0 <= mean_delta <= 12.0):
            delta_bonus = 5.0
        elif max_delta > 28 or mean_delta < 3.0 or mean_delta > 15.0:
            delta_bonus = -12.0
            
    # 5. Geometria de Grelha Avançada (Distribuição por Linhas e Colunas do Volante - Todas as Loterias)
    geometry_bonus = 0.0
    
    if lottery_type == "Mega-Sena":
        # 6 linhas de 10 dezenas e 10 colunas de 6 dezenas
        rows = [0] * 6
        cols = [0] * 10
        for val in nums_sorted:
            r_idx = min(int((val - 1) // 10), 5)
            c_idx = int((val - 1) % 10)
            rows[r_idx] += 1
            cols[c_idx] += 1
        
        row_template = tuple(sorted(rows, reverse=True))
        col_template = tuple(sorted(cols, reverse=True))
        
        # Padrões Recordistas da Mega-Sena: Linhas (36% e 15.5%) e Colunas (20.8% e 18.9%)
        valid_row_templates = {(2, 2, 1, 1, 0, 0), (3, 1, 1, 1, 0, 0)}
        valid_col_templates = {(2, 2, 1, 1, 0, 0, 0, 0, 0, 0), (1, 1, 1, 1, 1, 1, 0, 0, 0, 0)}
        
        if row_template in valid_row_templates:
            geometry_bonus += 8.0
        else:
            if row_template[0] > 3:
                geometry_bonus -= 8.0 # Penaliza aglomeração excessiva de linha
                
        if col_template in valid_col_templates:
            geometry_bonus += 8.0
        else:
            if col_template[0] > 2:
                geometry_bonus -= 8.0 # Penaliza aglomeração excessiva de coluna
                
        # 7. Filtro de Miolo Central de Alta Densidade (Mega-Sena 21-40) - Com Sinergias Ocultas
        # O miolo central (linhas 3 e 4) comporta 20 números. Estatisticamente, mais de 75% dos sorteios possuem de 1 a 3 números ali.
        miolo_nums = [x for x in nums_sorted if 21 <= x <= 40]
        miolo_count = len(miolo_nums)
        if miolo_count == 2:
            geometry_bonus += 12.0 # Proporção áurea perfeita (2 números)
            # Padrão invisível de paridade do miolo (1 Par e 1 Ímpar)
            m_evens = sum(1 for x in miolo_nums if x % 2 == 0)
            if m_evens == 1:
                geometry_bonus += 6.0 # Bônus para Simetria de Paridade do Miolo
            # Padrão invisível de soma do miolo (ideal entre 45 e 85)
            m_sum = sum(miolo_nums)
            if 45 <= m_sum <= 85:
                geometry_bonus += 6.0 # Bônus de soma centralizada do miolo
        elif miolo_count in [1, 3]:
            geometry_bonus += 6.0  # Cobertura secundária estável
        else:
            geometry_bonus -= 12.0 # Penaliza 0 ou 4+ dezenas do miolo

    elif lottery_type == "Lotofácil":
        # 5 linhas de 5 dezenas e 5 colunas de 5 dezenas
        rows = [0] * 5
        cols = [0] * 5
        for val in nums_sorted:
            r_idx = min(int((val - 1) // 5), 4)
            c_idx = int((val - 1) % 5)
            rows[r_idx] += 1
            cols[c_idx] += 1
            
        row_template = tuple(sorted(rows, reverse=True))
        col_template = tuple(sorted(cols, reverse=True))
        
        # Padrões Recordistas da Lotofácil (Linhas e Colunas > 90% das ocorrências)
        valid_row_templates = {(4, 4, 3, 2, 2), (4, 3, 3, 3, 2), (5, 3, 3, 2, 2), (5, 4, 2, 2, 2), (3, 3, 3, 3, 3)}
        valid_col_templates = {(4, 4, 3, 2, 2), (4, 3, 3, 3, 2), (5, 3, 3, 2, 2), (5, 4, 2, 2, 2), (3, 3, 3, 3, 3)}
        
        if row_template in valid_row_templates:
            geometry_bonus += 8.0
        else:
            geometry_bonus -= 6.0
            
        if col_template in valid_col_templates:
            geometry_bonus += 8.0
        else:
            geometry_bonus -= 6.0
            
        # 8. Filtro da Cruz de Ouro (Diagonais Principais da Lotofácil)
        # Estatisticamente, a Lotofácil distribui de 5 a 7 dezenas nas diagonais do volante 5x5
        diagonals = {1, 5, 7, 9, 13, 17, 19, 21, 25}
        diag_count = sum(1 for x in nums_sorted if x in diagonals)
        if 5 <= diag_count <= 7:
            geometry_bonus += 6.0 # Cobertura ideal na Cruz de Ouro
        else:
            geometry_bonus -= 4.0

    elif lottery_type == "Quina":
        # 8 linhas de 10 dezenas e 10 colunas de 8 dezenas
        rows = [0] * 8
        cols = [0] * 10
        for val in nums_sorted:
            r_idx = min(int((val - 1) // 10), 7)
            c_idx = int((val - 1) % 10)
            rows[r_idx] += 1
            cols[c_idx] += 1
            
        row_template = tuple(sorted(rows, reverse=True))
        col_template = tuple(sorted(cols, reverse=True))
        
        # Padrões Recordistas da Quina (Linhas e Colunas que evitam aglomerações e garantem cobertura)
        valid_row_templates = {(1, 1, 1, 1, 1, 0, 0, 0), (2, 2, 1, 0, 0, 0, 0, 0), (2, 1, 1, 1, 0, 0, 0, 0)}
        valid_col_templates = {(1, 1, 1, 1, 1, 0, 0, 0, 0, 0), (2, 2, 1, 0, 0, 0, 0, 0, 0, 0), (2, 1, 1, 1, 0, 0, 0, 0, 0, 0)}
        
        if row_template in valid_row_templates:
            geometry_bonus += 10.0
        else:
            if row_template[0] > 3:
                geometry_bonus -= 8.0
                
        if col_template in valid_col_templates:
            geometry_bonus += 10.0
        else:
            if col_template[0] > 2:
                geometry_bonus -= 8.0
                
        # 10. Filtro de Moldura Preditiva (Quina Extremos do Volante)
        # Estatisticamente, a Quina distribui de 1 a 3 dezenas na borda externa do volante de 80 números
        moldura_count = 0
        for val in nums_sorted:
            r = (val - 1) // 10
            c = (val - 1) % 10
            if r == 0 or r == 7 or c == 0 or c == 9:
                moldura_count += 1
        if 1 <= moldura_count <= 3:
            geometry_bonus += 6.0 # Equilíbrio perfeito na borda da Quina
        else:
            geometry_bonus -= 4.0

    elif lottery_type == "Dupla Sena":
        # 5 linhas de 10 dezenas e 10 colunas de 5 dezenas
        rows = [0] * 5
        cols = [0] * 10
        for val in nums_sorted:
            r_idx = min(int((val - 1) // 10), 4)
            c_idx = int((val - 1) % 10)
            rows[r_idx] += 1
            cols[c_idx] += 1
            
        row_template = tuple(sorted(rows, reverse=True))
        col_template = tuple(sorted(cols, reverse=True))
        
        # Padrões de Linha e Coluna da Dupla Sena
        valid_row_templates = {(3, 2, 1, 0, 0), (2, 1, 1, 1, 1), (2, 2, 2, 0, 0), (2, 2, 1, 1, 0)}
        valid_col_templates = {(1, 1, 1, 1, 1, 1, 0, 0, 0, 0), (2, 2, 1, 1, 0, 0, 0, 0, 0, 0), (2, 1, 1, 1, 1, 0, 0, 0, 0, 0)}
        
        if row_template in valid_row_templates:
            geometry_bonus += 10.0
        else:
            if row_template[0] > 3:
                geometry_bonus -= 8.0
                
        if col_template in valid_col_templates:
            geometry_bonus += 10.0
        else:
            if col_template[0] > 2:
                geometry_bonus -= 8.0
                
        # 11. Filtro de Simetria Lateral (Dupla Sena Esquerda vs Direita)
        # No máximo 4 dezenas de um único lado (esquerda colunas 1-5; direita colunas 6-10)
        left_half = sum(1 for val in nums_sorted if (val - 1) % 10 < 5)
        if 2 <= left_half <= 4:
            geometry_bonus += 6.0 # Simetria lateral de alta dispersão
        else:
            geometry_bonus -= 6.0

    elif lottery_type == "Lotomania":
        # Mapeador de Geometria de Grelha Avançado (Distribuições nas Linhas e Colunas do Volante)
        v_nums = [100 if x == 0 else x for x in nums_sorted]
        rows = [0] * 10
        cols = [0] * 10
        for val in v_nums:
            r_idx = (val - 1) // 10
            c_idx = (val - 1) % 10
            rows[r_idx] += 1
            cols[c_idx] += 1
        
        row_template = tuple(sorted(rows, reverse=True))
        col_template = tuple(sorted(cols, reverse=True))
        
        # Padrões Recordistas das Linhas Horizontais (Frequência acumulada > 60%) [Passage 237]
        valid_row_templates = {
            (4, 3, 3, 3, 2, 2, 1, 1, 1, 0),
            (4, 3, 3, 2, 2, 2, 1, 1, 1, 1),
            (3, 3, 3, 2, 2, 2, 2, 1, 1, 1),
            (3, 3, 2, 2, 2, 2, 2, 2, 1, 1),
            (4, 3, 2, 2, 2, 2, 2, 2, 1, 0),
            (4, 3, 3, 3, 3, 2, 1, 1, 0, 0),
            (4, 4, 3, 2, 2, 2, 1, 1, 1, 0),
            (4, 4, 2, 2, 2, 2, 2, 1, 1, 0)
        }
        
        # Padrões Recordistas das Colunas Verticais (Frequência acumulada > 60%) [Passage 240]
        valid_col_templates = {
            (4, 3, 3, 2, 2, 2, 1, 1, 1, 1),
            (4, 3, 3, 3, 2, 2, 1, 1, 1, 0),
            (3, 3, 3, 2, 2, 2, 2, 1, 1, 1),
            (3, 3, 2, 2, 2, 2, 2, 2, 1, 1),
            (4, 3, 2, 2, 2, 2, 2, 2, 1, 0),
            (4, 3, 3, 3, 3, 2, 1, 1, 0, 0),
            (4, 4, 3, 2, 2, 2, 1, 1, 1, 0),
            (4, 4, 2, 2, 2, 2, 2, 1, 1, 0)
        }
        
        grid_bonus = 0.0
        if row_template in valid_row_templates:
            grid_bonus += 12.0
        else:
            if row_template[0] > 6:
                grid_bonus -= 10.0  # Penaliza severamente concentrações excessivas (mais de 6 dezenas por linha)
                
        if col_template in valid_col_templates:
            grid_bonus += 12.0
        else:
            if col_template[0] > 6:
                grid_bonus -= 10.0  # Penaliza severamente concentrações excessivas em colunas
                
        # 9. Filtro da Cruz de Segurança (Lotomania Borda vs Centro)
        # Das 50 dezenas sorteadas, a proporção ideal na borda extrema (linhas 1, 10 e colunas 1, 10) deve estar entre 20 e 30
        border_count = 0
        for val in nums_sorted:
            v = 100 if val == 0 else val
            r = (v - 1) // 10
            c = (v - 1) % 10
            is_border = (r == 0 or r == 9 or c == 0 or c == 9)
            if is_border:
                border_count += 1
        if 20 <= border_count <= 30:
            grid_bonus += 8.0 # Bônus de equilíbrio de borda/centro
        else:
            grid_bonus -= 6.0
            
        geometry_bonus = grid_bonus
            
    # 12. Consecutivos Extremos (Gargalos de Sequências do Cartão)
    consecutive_penalty = 0.0
    consecutives = sum(1 for idx in range(n - 1) if nums_sorted[idx+1] - nums_sorted[idx] == 1)
    if lottery_type == "Lotofácil" and consecutives > 4:
        consecutive_penalty = -10.0
    elif lottery_type in ["Mega-Sena", "Dupla Sena", "Quina"] and consecutives > 2:
        consecutive_penalty = -15.0
    elif lottery_type == "Lotomania" and consecutives > 12:
        consecutive_penalty = -12.0
        
    return float(base_score + entropy_bonus + paridade_bonus + delta_bonus + geometry_bonus + consecutive_penalty)


def generate_mega_sena(special_mode=False):
    hist = st.session_state.history["Mega-Sena"]
    last_draw = hist[0]
    eligible_numbers = [n for num in range(1, 61) if (n := num) % 10 not in [2, 6, 0]]
    
    dezena_de_ouro = calculate_dezena_de_ouro("Mega-Sena", hist, last_draw)
    
    all_weights = get_unified_weights("Mega-Sena", hist, last_draw)
    for num in USER_FIXED_MEGA_SENA:
        if num in all_weights:
            all_weights[num] *= 2.5 # EXTREME REFINEMENT: Boost favored numbers from 1.5x to 2.5x!
            
    if special_mode:
        spec_hist = get_special_history()["Mega da Virada"]
        transitions_reg = calculate_markov(hist, 60)
        transitions_spec = calculate_markov(spec_hist, 60)
        transitions = {}
        for i in range(1, 61):
            transitions[i] = {}
            for j in range(1, 61):
                transitions[i][j] = (transitions_reg.get(i, {}).get(j, 0) * 0.8) + (transitions_spec.get(i, {}).get(j, 0) * 0.2)
    else:
        transitions = calculate_markov(hist, 60)
        
    def complete_mega_game(seed_nums, avoid_games=[]):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
            
        candidate_pool = []
        for _ in range(150):
            current = list(dict.fromkeys(seed_nums))
            if len(current) >= 6:
                pool = current.copy()
                current = []
                if dezena_de_ouro not in current and dezena_de_ouro in pool:
                    current.append(dezena_de_ouro)
                    pool.remove(dezena_de_ouro)
                while len(current) < 6:
                    weights = [all_weights.get(n, 2.0) for n in pool]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(pool, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
            else:
                pool = [n for n in range(1, 61) if (n in USER_FIXED_MEGA_SENA) or (n % 10 not in [2, 6, 0])]
                pool = [n for n in pool if n not in current]
                if dezena_de_ouro not in current:
                    current.append(dezena_de_ouro)
                if dezena_de_ouro in pool:
                    pool.remove(dezena_de_ouro)
                    
                while len(current) < 6:
                    candidates = pool
                    weights = [all_weights.get(n, 2.0) for n in candidates]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(candidates, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
                    
            game = sorted(current)
            candidate_pool.append(game)
            
        # Score candidates
        scored_candidates = []
        for g in candidate_pool:
            score = evaluate_game_score(g, "Mega-Sena", all_weights)
            
            # Anti-popularity check
            if not anti_popularity_filter(g, "Mega-Sena", strict=special_mode):
                score -= 10.0
                
            # Diversity check
            for prev_game in avoid_games:
                overlap = len(set(g).intersection(set(prev_game)))
                if overlap > 2:
                    score -= (overlap - 2) * 15.0 # Heavy penalization for overlap > 2
                    
            scored_candidates.append((score, g))
            
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    markov_nums = get_markov_predictions(last_draw, transitions, 10)
    if special_mode:
        spec_hist = get_special_history()["Mega da Virada"]
        gold_nums = greedy_set_cover(hist + spec_hist, 12, 60) # EXTREME REFINEMENT: Long-term seasonal cover for Virada!
    else:
        gold_nums = greedy_set_cover(hist, 12, 60)
        
    # EXTREME REFINEMENT: Supremo blends favored list with top coverage & transitions!
    candidates_seed = list(set(USER_FIXED_MEGA_SENA + markov_nums + gold_nums))
    supremo = complete_mega_game(candidates_seed, avoid_games=[])
    
    # EXTREME REFINEMENT: Tendência seeds from computed offsets + markov predictions
    candidates_seed_t = []
    for num in last_draw:
        for offset in [-2, 2, -8, 8]:
            val = num + offset
            if 1 <= val <= 60:
                candidates_seed_t.append(val)
    candidates_seed_t = list(set(candidates_seed_t + markov_nums))
    tendencia = complete_mega_game(candidates_seed_t, avoid_games=[supremo])
    
    # EXTREME REFINEMENT: Cobertura blends most delayed + favored lists
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in eligible_numbers}
    cob_list = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = complete_mega_game(cob_list + USER_FIXED_MEGA_SENA, avoid_games=[supremo, tendencia])
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_lotofacil(special_mode=False, tribo_mode=False):
    hist_all = st.session_state.history["Lotofácil"]
    hist = hist_all[:30] # REGRA ESTREITA DE 30 CONCURSOS
    last_draw = hist[0]

    if tribo_mode and not special_mode:
        # ── EXTREME REFINEMENT: TRIBO DA SORTE (DUPLO ESPELHO COMPLEMENTAR - 5 FIXAS) ──
        # 1. Obter co-ocorrência (Duques Amigos) nos últimos 30 concursos
        co_occurrence = {i: {j: 0 for j in range(1, 26)} for i in range(1, 26)}
        for draw in hist:
            for u in draw:
                for v in draw:
                    if u != v:
                        co_occurrence[u][v] += 1
                        
        # 2. Obter pesos das dezenas e selecionar as top 10 mais quentes
        all_weights = get_unified_weights("Lotofácil", hist, last_draw)
        ranked_dezenas = sorted(range(1, 26), key=lambda x: all_weights.get(x, 1.0), reverse=True)
        top_10 = ranked_dezenas[:10]
        
        # 3. Escolher as 5 dezenas fixas (de elite) com maior co-ocorrência mútua entre as top 10
        best_sum = -1
        best_five = []
        for comb in itertools.combinations(top_10, 5):
            curr_sum = 0
            for u in comb:
                for v in comb:
                    if u < v:
                        curr_sum += co_occurrence[u][v]
            if curr_sum > best_sum:
                best_sum = curr_sum
                best_five = list(comb)
                
        fixed_nums = sorted(best_five)
        variable_nums = sorted([n for n in range(1, 26) if n not in fixed_nums])
        
        # 4. Partição Complementar Otimizada via Monte Carlo (500 iterações)
        best_part_score = -999999
        best_Game_A, best_Game_B = [], []
        
        for _ in range(500):
            set_A = sorted(random.sample(variable_nums, 10))
            set_B = sorted([n for n in variable_nums if n not in set_A])
            
            Game_A = sorted(fixed_nums + set_A)
            Game_B = sorted(fixed_nums + set_B)
            
            score_A = evaluate_game_score(Game_A, "Lotofácil", all_weights)
            score_B = evaluate_game_score(Game_B, "Lotofácil", all_weights)
            
            if not anti_popularity_filter(Game_A, "Lotofácil", strict=False):
                score_A -= 15.0
            if not anti_popularity_filter(Game_B, "Lotofácil", strict=False):
                score_B -= 15.0
                
            # Pontuação da partição penalizando assimetrias para que ambos os jogos sejam excelentes
            part_score = score_A + score_B - abs(score_A - score_B) * 0.5
            
            if part_score > best_part_score:
                best_part_score = part_score
                best_Game_A = Game_A
                best_Game_B = Game_B
                
        # 5. Jogo 3: Cobertura por Max Verossimilhança (5 Fixas + 10 de maior peso estatístico)
        sorted_vars = sorted(variable_nums, key=lambda x: all_weights.get(x, 1.0), reverse=True)
        best_vars_10 = sorted_vars[:10]
        Game_C = sorted(fixed_nums + best_vars_10)
        
        # Salva o estado da partição na sessão para renderização na interface
        st.session_state.tribo_fixed_nums = fixed_nums
        st.session_state.tribo_set_a = sorted(list(set(best_Game_A) - set(fixed_nums)))
        st.session_state.tribo_set_b = sorted(list(set(best_Game_B) - set(fixed_nums)))
        
        # Ouro é a dezena mais central do grupo fixo
        dezena_de_ouro = fixed_nums[2]
        
        return best_Game_A, best_Game_B, Game_C, dezena_de_ouro

    
    if special_mode:
        # ── EXTREME REFINEMENT: LOTOFÁCIL DA INDEPENDÊNCIA (8-STEP ANÁLISE COMBINADA) ──
        hist_ind = get_special_history()["Lotofácil da Independência"]
        
        # Etapa 1: Análise da Independência
        freq_total_ind = {i: sum(1 for game in hist_ind if i in game) for i in range(1, 26)}
        freq_rec_ind = {i: sum(1 for game in hist_ind[:3] if i in game) for i in range(1, 26)}
        atraso_ind = {}
        for i in range(1, 26):
            delay = 999
            for idx, game in enumerate(hist_ind):
                if i in game:
                    delay = idx
                    break
            atraso_ind[i] = delay
            
        tab1_rows = []
        for i in range(1, 26):
            tab1_rows.append({
                "Dezena": f"{i:02d}",
                "Frequência Total": freq_total_ind[i],
                "Frequência Recente (3)": freq_rec_ind[i],
                "Atraso (Concursos)": atraso_ind[i] if atraso_ind[i] != 999 else "Nunca"
            })
        tab1_df = pd.DataFrame(tab1_rows)
        st.session_state.independencia_tab1 = tab1_df
        
        # Etapa 2: Análise da Lotofácil Normal
        freq_30_norm = {i: sum(1 for game in hist if i in game) for i in range(1, 26)}
        freq_20_norm = {i: sum(1 for game in hist[:20] if i in game) for i in range(1, 26)}
        freq_10_norm = {i: sum(1 for game in hist[:10] if i in game) for i in range(1, 26)}
        freq_5_norm = {i: sum(1 for game in hist[:5] if i in game) for i in range(1, 26)}
        atraso_norm = {}
        for i in range(1, 26):
            delay = 999
            for idx, game in enumerate(hist):
                if i in game:
                    delay = idx
                    break
            atraso_norm[i] = delay
            
        tab2_rows = []
        for i in range(1, 26):
            tab2_rows.append({
                "Dezena": f"{i:02d}",
                "Freq. 30": freq_30_norm[i],
                "Freq. 20": freq_20_norm[i],
                "Freq. 10": freq_10_norm[i],
                "Freq. Recente (5)": freq_5_norm[i],
                "Atraso (Concursos)": atraso_norm[i] if atraso_norm[i] != 999 else "Nunca"
            })
        tab2_df = pd.DataFrame(tab2_rows)
        st.session_state.independencia_tab2 = tab2_df
        
        # Etapa 3: Cruzamento de Dados (Pontuação de 0 a 10)
        scores = {}
        for i in range(1, 26):
            score_A = (freq_total_ind[i] / 5.0) * 10.0
            score_B = (freq_rec_ind[i] / 3.0) * 10.0
            score_C = 10.0 if atraso_ind[i] == 0 else (7.0 if atraso_ind[i] == 1 else (5.0 if atraso_ind[i] == 2 else (3.0 if atraso_ind[i] == 3 else 0.0)))
            score_D = (freq_30_norm[i] / 30.0) * 10.0
            score_E = (freq_5_norm[i] / 5.0) * 10.0
            score_F = max(0.0, 10.0 - atraso_norm[i]) if atraso_norm[i] != 999 else 0.0
            
            total_score = (score_A * 3 + score_B * 2 + score_C * 1 + score_D * 2 + score_E * 1 + score_F * 1) / 10.0
            scores[i] = total_score
            
        # Etapa 4: Análise de Padrões Comportamentais
        reps_ind = []
        for idx in range(len(hist_ind) - 1):
            reps_ind.append(len(set(hist_ind[idx]).intersection(set(hist_ind[idx+1]))))
        mean_rep_ind = np.mean(reps_ind) if reps_ind else 9.0
        
        mean_rep_norm_ind = len(set(hist[0]).intersection(set(hist_ind[0])))
        tendencia_rep = set(hist[0]).intersection(set(hist_ind[0]))
        tendencia_aus = set(range(1, 26)) - (set(hist[0]).union(set(hist_ind[0])))
        
        adjusted_scores = {}
        for i in range(1, 26):
            base_s = scores[i]
            if i in tendencia_rep:
                base_s += 0.5
            elif i in tendencia_aus:
                base_s -= 0.5
            adjusted_scores[i] = min(10.0, max(0.0, base_s))
            
        sorted_dezenas_with_scores = sorted(adjusted_scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
        ranking = [int(x[0]) for x in sorted_dezenas_with_scores]
        st.session_state.independencia_ranking = ranking
        
        tab3_rows = []
        for rank_idx, (num, score) in enumerate(sorted_dezenas_with_scores):
            tab3_rows.append({
                "Ranking": rank_idx + 1,
                "Dezena": f"{num:02d}",
                "Pontuação Final": round(score, 2),
                "Classificação": "Forte (Elite)" if rank_idx < 10 else ("Intermediária" if rank_idx < 18 else "Fraca (Resfriamento)")
            })
        tab3_df = pd.DataFrame(tab3_rows)
        st.session_state.independencia_scores = tab3_df
        
        top_10 = ranking[:10]
        intermediarias = ranking[10:18]
        fracas = ranking[18:]
        
        st.session_state.ind_fixed_135 = top_10[:7]
        st.session_state.ind_fixed_24 = top_10[:8]
        st.session_state.ind_variables_pool = sorted(intermediarias)
        
        fixed_135 = top_10[:7]
        fixed_24 = top_10[:8]
        
        games = []
        all_weights = get_unified_weights("Lotofácil", hist, last_draw)
        
        for game_idx, num_fixed in enumerate([7, 8, 7, 8, 7]):
            current_fixed = fixed_135 if num_fixed == 7 else fixed_24
            num_vars = 15 - num_fixed
            eligible_vars = [n for n in range(1, 26) if n not in current_fixed]
            
            candidate_pool = []
            for _ in range(100):
                w_vars = [adjusted_scores[n] + 0.1 for n in eligible_vars]
                total_w = sum(w_vars)
                probs = [w / total_w for w in w_vars]
                
                chosen_vars = [int(n) for n in np.random.choice(eligible_vars, size=num_vars, replace=False, p=probs)]
                game = sorted([int(n) for n in list(current_fixed) + chosen_vars])
                candidate_pool.append(game)
                
            scored_candidates = []
            for g in candidate_pool:
                score = evaluate_game_score(g, "Lotofácil", all_weights)
                if not anti_popularity_filter(g, "Lotofácil", strict=True):
                    score -= 10.0
                scored_candidates.append((score, g))
                
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            best_game = scored_candidates[0][1]
            games.append(best_game)
            
        st.session_state.independencia_games = games
        dezena_de_ouro = ranking[0]
        
        supremo = games[0]
        tendencia = games[1]
        cobertura = games[2]
        
        return supremo, tendencia, cobertura, dezena_de_ouro
    
    # 1. Calcular a Dezena de Ouro (maior score clássico)
    dezena_de_ouro = calculate_dezena_de_ouro("Lotofácil", hist, last_draw)
    
    # 2. Executar Análise de Gular (Zonas de Transição de 10 concursos + Cadeias de Markov)
    if len(hist_all) >= 11:
        f_curr = {i: 0 for i in range(1, 26)}
        for draw in hist_all[0:10]:
            for num in draw:
                if num in f_curr: f_curr[num] += 1
                
        f_prev = {i: 0 for i in range(1, 26)}
        for draw in hist_all[1:11]:
            for num in draw:
                if num in f_prev: f_prev[num] += 1
                
        was_in_1 = set(hist_all[1])
        is_in_0 = set(hist_all[0])
    else:
        f_curr = {i: 5 for i in range(1, 26)}
        f_prev = {i: 5 for i in range(1, 26)}
        was_in_1 = set(last_draw)
        is_in_0 = set(last_draw)
        
    gular_scores = {}
    
    for num in range(1, 26):
        curr_freq = f_curr.get(num, 5)
        prev_freq = f_prev.get(num, 5)
        
        st_prev = num in was_in_1
        st_curr = num in is_in_0
        
        if st_prev and st_curr:
            m_state = "S to S"
        elif st_prev and not st_curr:
            m_state = "S to N"
        elif not st_prev and st_curr:
            m_state = "N to S"
        else:
            m_state = "N to N"
            
        # Padrão de temperatura geral
        if curr_freq >= 7:
            score = 73.8
        elif curr_freq in [5, 6]:
            score = 52.3
        else:
            score = 45.0
            
        # Padrões específicos de Gular
        if prev_freq == 8 and curr_freq == 7 and m_state == "N to S":
            score = 90.0 # Inclusão Muito Forte (90%)
        elif prev_freq == 6 and curr_freq == 7 and m_state == "S to S":
            score = 78.6 # Inclusão Forte (78.6%)
        elif prev_freq == 5 and curr_freq == 6 and m_state == "S to S":
            score = 71.4 # Inclusão Forte (71.4%)
        elif prev_freq == 6 and curr_freq == 5 and m_state == "N to S":
            score = 71.4 # Inclusão Forte (71.4%)
        elif prev_freq == 5 and curr_freq == 4 and m_state == "N to N":
            score = 66.7 # Boa Inclusão (66.7%)
        elif prev_freq == 7 and curr_freq == 6 and m_state == "N to S":
            score = 61.5 # Inclusão Moderada (61.5%)
        # Exclusões
        elif prev_freq == 3 and curr_freq == 4 and m_state == "S to N":
            score = 20.0 # Exclusão Muito Forte (80% ausência)
        elif prev_freq == 5 and curr_freq == 6 and m_state == "S to N":
            score = 37.5 # Candidata à Exclusão (62.5% ausência)
        elif prev_freq == 9 and curr_freq == 8 and m_state == "N to S":
            score = 33.3 # Exclusão Experimental (66.7% ausência)
            
        if num == dezena_de_ouro:
            score += 15.0 # Força a Dezena de Ouro clássica a ter privilégio de âncora
            
        gular_scores[num] = score

    # 3. Divisão dos Pools de Repetição
    pool_rep = [n for n in last_draw]
    pool_aus = [n for n in range(1, 26) if n not in last_draw]
    
    pool_rep = sorted(pool_rep, key=lambda n: gular_scores[n], reverse=True)
    pool_aus = sorted(pool_aus, key=lambda n: gular_scores[n], reverse=True)
    
    # 4. Seleção das 11 Fixas e 8 Variáveis do Sistema Steiner de Leandro Gular
    fixed_rep = pool_rep[:8]
    fixed_aus = pool_aus[:3]
    fixed_nums = sorted(fixed_rep + fixed_aus)
    
    var_rep = pool_rep[8:11]
    var_aus = pool_aus[3:8]
    variable_nums = sorted(var_rep + var_aus)
    
    st.session_state.gular_fixed_nums = fixed_nums
    st.session_state.gular_variable_nums = variable_nums
    st.session_state.gular_excluded_nums = sorted([n for n in range(1, 26) if n not in fixed_nums and n not in variable_nums])
    
    # 5. Executar o Desdobramento de Steiner (14 jogos de 15 dezenas)
    STEINER_BLOCKS = [
        [0, 2, 5, 6], [1, 3, 6, 7], [2, 3, 4, 7], [0, 1, 2, 3],
        [0, 1, 4, 7], [3, 4, 5, 6], [0, 2, 6, 7], [0, 1, 3, 5],
        [1, 2, 4, 5], [0, 3, 4, 6], [1, 5, 6, 7], [2, 3, 5, 7],
        [1, 2, 4, 6], [0, 4, 5, 7]
    ]
    
    games = []
    for block in STEINER_BLOCKS:
        g_vars = [variable_nums[idx] for idx in block]
        game = sorted(fixed_nums + g_vars)
        games.append(game)
        
    # 6. Refinar e filtrar os 14 jogos pelo Motor de Otimização Multiobjetivo
    scored_games = []
    all_weights = get_unified_weights("Lotofácil", hist, last_draw)
    
    for g in games:
        score = evaluate_game_score(g, "Lotofácil", all_weights)
        
        # Anti-popularity check
        if not anti_popularity_filter(g, "Lotofácil", strict=special_mode):
            score -= 10.0
            
        scored_games.append((score, g))
        
    # Sort games by multi-objective score descending
    scored_games.sort(key=lambda x: x[0], reverse=True)
    
    # Select Supremo (absolute best of desdobramento)
    supremo = scored_games[0][1]
    
    # Select Tendência with portfolio diversity (at most 10 overlap with Supremo)
    tendencia = None
    for idx in range(1, len(scored_games)):
        g = scored_games[idx][1]
        overlap = len(set(g).intersection(set(supremo)))
        if overlap <= 12:
            tendencia = g
            break
    if tendencia is None:
        tendencia = scored_games[1][1] # fallback to next best
        
    # Select Cobertura with portfolio diversity (at most 10 overlap with both)
    cobertura = None
    for idx in range(1, len(scored_games)):
        g = scored_games[idx][1]
        if g == tendencia:
            continue
        overlap_s = len(set(g).intersection(set(supremo)))
        overlap_t = len(set(g).intersection(set(tendencia)))
        if overlap_s <= 10 and overlap_t <= 10:
            cobertura = g
            break
    if cobertura is None:
        # fallback to first distinct game available
        for idx in range(1, len(scored_games)):
            g = scored_games[idx][1]
            if g != supremo and g != tendencia:
                cobertura = g
                break
                
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_lotomania():
    hist = st.session_state.history["Lotomania"]
    wave_nums = detect_lotomania_wave(hist)
    fixed = USER_FIXED_LOTOMANIA.copy()
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Lotomania", hist, last_draw)
    
    all_weights = {i: 5.0 for i in range(100)}
    user_weights = {
        16: 18, 41: 17, 61: 16, 14: 15, 25: 15, 83: 15,
        11: 14, 20: 14, 44: 14, 77: 14, 13: 13, 29: 13,
        38: 13, 47: 13, 63: 13, 73: 13, 91: 13, 19: 12,
        33: 12, 40: 12, 49: 12, 60: 12, 64: 12, 67: 12,
        68: 12, 85: 12, 7: 11, 31: 11, 56: 11, 59: 11,
        84: 11, 93: 11, 95: 11, 97: 11
    }
    for num, w in user_weights.items():
        all_weights[num] = float(w)
        
    for num in wave_nums:
        if num in all_weights:
            all_weights[num] *= 1.2
            
    def complete_game(seed_fixed, avoid_games=[]):
        if dezena_de_ouro not in seed_fixed:
            seed_fixed = list(seed_fixed) + [dezena_de_ouro]
            
        candidate_pool = []
        for _ in range(100):
            current = list(dict.fromkeys(seed_fixed))
            all_nums = [n for n in range(1, 100)] + [0]
            pool = [n for n in all_nums if n not in current]
            
            wave_eligible = [n for n in wave_nums if n in pool]
            current.extend(wave_eligible[:4])
            pool = [n for n in all_nums if n not in current]
            
            if dezena_de_ouro not in current:
                current.append(dezena_de_ouro)
            
            while len(current) < 50:
                candidates = pool
                weights = [all_weights.get(n, 5.0) for n in candidates]
                total_w = sum(weights)
                probs = [w / total_w for w in weights]
                chosen = np.random.choice(candidates, p=probs)
                current.append(int(chosen))
                pool.remove(chosen)
                
            game = sorted(current)
            candidate_pool.append(game)
            
        scored_candidates = []
        for g in candidate_pool:
            score = evaluate_game_score(g, "Lotomania", all_weights)
            
            # Diversity check
            for prev_game in avoid_games:
                overlap = len(set(g).intersection(set(prev_game)))
                if overlap > 38:
                    score -= (overlap - 38) * 8.0 # Heavy penalization for sharing too many dezenas
                    
            scored_candidates.append((score, g))
            
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    supremo = complete_game(fixed, avoid_games=[])
    tendencia = complete_game(fixed, avoid_games=[supremo])
    cobertura = complete_game(fixed, avoid_games=[supremo, tendencia])
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_quina(special_mode=False):
    hist = st.session_state.history["Quina"]
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Quina", hist, last_draw)
    
    all_weights = get_unified_weights("Quina", hist, last_draw)
    for num in USER_FIXED_QUINA:
        if num in all_weights:
            all_weights[num] *= 2.5 # EXTREME REFINEMENT: Boost favored numbers to 2.5x!
            
    if special_mode:
        spec_hist = get_special_history()["Quina de São João"]
        transitions_reg = calculate_markov(hist, 80)
        transitions_spec = calculate_markov(spec_hist, 80)
        transitions = {}
        for i in range(1, 81):
            transitions[i] = {}
            for j in range(1, 81):
                transitions[i][j] = (transitions_reg.get(i, {}).get(j, 0) * 0.8) + (transitions_spec.get(i, {}).get(j, 0) * 0.2)
    else:
        transitions = calculate_markov(hist, 80)
        
    def complete_quina_game(seed_nums, avoid_games=[]):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
            
        candidate_pool = []
        for _ in range(150):
            current = list(dict.fromkeys(seed_nums))
            if len(current) >= 5:
                pool = current.copy()
                current = []
                if dezena_de_ouro not in current and dezena_de_ouro in pool:
                    current.append(dezena_de_ouro)
                    pool.remove(dezena_de_ouro)
                while len(current) < 5:
                    weights = [all_weights.get(n, 2.0) for n in pool]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(pool, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
            else:
                pool = [n for n in range(1, 81) if n not in current]
                if dezena_de_ouro not in current:
                    current.append(dezena_de_ouro)
                if dezena_de_ouro in pool:
                    pool.remove(dezena_de_ouro)
                while len(current) < 5:
                    candidates = pool
                    weights = [all_weights.get(n, 2.0) for n in candidates]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(candidates, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
                    
            game = sorted(current)
            candidate_pool.append(game)
            
        scored_candidates = []
        for g in candidate_pool:
            score = evaluate_game_score(g, "Quina", all_weights)
            
            # Diversity check
            for prev_game in avoid_games:
                overlap = len(set(g).intersection(set(prev_game)))
                if overlap > 1:
                    score -= (overlap - 1) * 20.0 # Strict quina diversity: overlap > 1 is heavily penalized
                    
            scored_candidates.append((score, g))
            
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    if special_mode:
        spec_hist = get_special_history()["Quina de São João"]
        gold_nums = greedy_set_cover(hist + spec_hist, 12, 80) # EXTREME REFINEMENT: Long-term seasonal cover for São João!
    else:
        gold_nums = greedy_set_cover(hist, 12, 80)
        
    # EXTREME REFINEMENT: Supremo blends favored list with top coverage & transitions!
    candidates_seed = list(set(USER_FIXED_QUINA + markov_nums + gold_nums))
    supremo = complete_quina_game(candidates_seed, avoid_games=[])
    
    # EXTREME REFINEMENT: Tendência seeds from transitions + favored list
    tendencia = complete_quina_game(markov_nums + USER_FIXED_QUINA, avoid_games=[supremo])
    
    # EXTREME REFINEMENT: Cobertura blends most delayed + favored lists
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 81)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:20]]
    cobertura = complete_quina_game(atrasadas + USER_FIXED_QUINA, avoid_games=[supremo, tendencia])
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_dupla_sena(special_mode=False):
    hist = st.session_state.history["Dupla Sena"]
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Dupla Sena", hist, last_draw)
    
    all_weights = get_unified_weights("Dupla Sena", hist, last_draw)
    for num in USER_FIXED_DUPLA_SENA:
        if num in all_weights:
            all_weights[num] *= 2.5 # EXTREME REFINEMENT: Boost favored numbers to 2.5x!

    hist_draw1 = [concurso[0] for concurso in hist]
    hist_draw2 = [concurso[1] for concurso in hist]
    
    if special_mode:
        spec_hist = get_special_history()["Dupla Sena de Páscoa"]
        spec_draw1 = [c[0] for c in spec_hist]
        spec_draw2 = [c[1] for c in spec_hist]
        
        gold1_reg = greedy_set_cover(hist_draw1, 15, 50)
        gold1_spec = greedy_set_cover(spec_draw1, 10, 50)
        gold1 = list(set(gold1_reg + gold1_spec))[:18]
        
        gold2_reg = greedy_set_cover(hist_draw2, 15, 50)
        gold2_spec = greedy_set_cover(spec_draw2, 10, 50)
        gold2 = list(set(gold2_reg + gold2_spec))[:18]
    else:
        gold1 = greedy_set_cover(hist_draw1, 15, 50)
        gold2 = greedy_set_cover(hist_draw2, 15, 50)
        
    def complete_dupla_game(seed_nums, avoid_games=[]):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
            
        candidate_pool = []
        for _ in range(150):
            current = list(dict.fromkeys(seed_nums))
            if len(current) >= 6:
                pool = current.copy()
                current = []
                if dezena_de_ouro not in current and dezena_de_ouro in pool:
                    current.append(dezena_de_ouro)
                    pool.remove(dezena_de_ouro)
                while len(current) < 6:
                    weights = [all_weights.get(n, 2.0) for n in pool]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(pool, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
            else:
                pool = [n for n in range(1, 51) if n not in current]
                if dezena_de_ouro not in current:
                    current.append(dezena_de_ouro)
                if dezena_de_ouro in pool:
                    pool.remove(dezena_de_ouro)
                while len(current) < 6:
                    candidates = pool
                    weights = [all_weights.get(n, 2.0) for n in candidates]
                    total_w = sum(weights)
                    probs = [w / total_w for w in weights]
                    chosen = np.random.choice(candidates, p=probs)
                    current.append(int(chosen))
                    pool.remove(chosen)
                
            game = sorted(current)
            candidate_pool.append(game)
            
        scored_candidates = []
        for g in candidate_pool:
            score = evaluate_game_score(g, "Dupla Sena", all_weights)
            
            # Diversity check
            for prev_game in avoid_games:
                overlap = len(set(g).intersection(set(prev_game)))
                if overlap > 2:
                    score -= (overlap - 2) * 15.0 # Overlap > 2 is heavily penalized
                    
            scored_candidates.append((score, g))
            
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    # EXTREME REFINEMENT: Supremo blends favored list with top coverage!
    supremo = complete_dupla_game(USER_FIXED_DUPLA_SENA.copy() + gold1, avoid_games=[])
    
    # EXTREME REFINEMENT: Tendência seeds from transitions + favored list
    tendencia = complete_dupla_game(gold2 + USER_FIXED_DUPLA_SENA.copy(), avoid_games=[supremo])
    
    # EXTREME REFINEMENT: Cobertura blends most delayed + favored lists
    all_draws = [n for sub in hist_draw1 + hist_draw2 for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 51)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = complete_dupla_game(atrasadas + USER_FIXED_DUPLA_SENA.copy(), avoid_games=[supremo, tendencia])
    
    return supremo, tendencia, cobertura, dezena_de_ouro

# ── DESIGN DO WEB APP GRÁFICO (INTERFACES STREAMLIT) ──────────────────

st.markdown("<div class='main-title'>🔮 PORTAL DE INFERÊNCIA PRO v20</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Ambiente de Otimização Estatística de Alta Performance - CEF</div>", unsafe_allow_html=True)

# Layout Principal: Duas Colunas
col_nav, col_main = st.columns([1, 3])

with col_nav:
    st.markdown("### ⚙️ Painel de Operações")
    selected_lottery = st.selectbox(
        "Selecione a Loteria Alvo:",
        ["Mega-Sena", "Lotofácil", "Lotomania", "Quina", "Dupla Sena"],
        index=0
    )
    
    # Interruptor para Modo Especial Sazonal (Sinergia Híbrida 80/20 e Anti-Popularidade Extremo)
    support_specials = selected_lottery in ["Mega-Sena", "Lotofácil", "Quina", "Dupla Sena"]
    special_mode = False
    if support_specials:
        special_label = {
            "Mega-Sena": "Mega da Virada 🎅",
            "Lotofácil": "Lotofácil da Independência 🇧🇷",
            "Quina": "Quina de São João 🔥",
            "Dupla Sena": "Dupla Sena de Páscoa 🐰"
        }[selected_lottery]
        special_mode = st.toggle(f"🔮 Ativar Modo {special_label}", value=False)
    
    # Determinar os números dos concursos de forma dinâmica e robusta
    history_lengths = {
        "Mega-Sena": (3051, 12),
        "Lotofácil": (3775, 10),
        "Lotomania": (2971, 8),
        "Quina": (7109, 14),
        "Dupla Sena": (3002, 5)
    }

    base_num, base_len = history_lengths[selected_lottery]
    latest_concurso = base_num + (len(st.session_state.history[selected_lottery]) - base_len)
    proximo_concurso = latest_concurso + 1

    # Se a info da API tiver um concurso maior, usa ela
    if "latest_info" in st.session_state and selected_lottery in st.session_state.latest_info:
        api_concurso = st.session_state.latest_info[selected_lottery]["concurso"]
        if api_concurso > latest_concurso:
            latest_concurso = api_concurso
            proximo_concurso = latest_concurso + 1

    # Obter o prêmio estimado da API se disponível, senão usar os valores base de mercado atuais
    base_prizes = {
        "Mega-Sena": "R$ 58 Milhões",
        "Lotofácil": "R$ 2 Milhões",
        "Lotomania": "R$ 16 Milhões",
        "Quina": "R$ 15 Milhões",
        "Dupla Sena": "R$ 1.8 Milhão"
    }
    premio_estimado = base_prizes[selected_lottery]

    if "latest_info" in st.session_state and selected_lottery in st.session_state.latest_info:
        api_valor = st.session_state.latest_info[selected_lottery]["valor"]
        if api_valor:
            premio_estimado = api_valor

    # Exibe as informações da Loteria selecionada
    lot_classes = {
        "Mega-Sena": "mega-sena-bg",
        "Lotofácil": "lotofacil-bg",
        "Lotomania": "lotomania-bg",
        "Quina": "quina-bg",
        "Dupla Sena": "dupla-sena-bg"
    }
    card_class = lot_classes[selected_lottery]

    st.markdown(
        f"<div class='lottery-card {card_class}'>"
        f"<h4>{selected_lottery.upper()}</h4>"
        f"<p>Prêmio Estimado: <b>{premio_estimado}</b><br>"
        f"Próximo Concurso: <b>{proximo_concurso}</b></p>"
        f"</div>", 
        unsafe_allow_html=True
    )
        
    st.info("💡 Este sistema trata históricos como dados estatísticos puros, buscando máxima eficiência de dispersão e cobertura sem alterar as probabilidades matemáticas teóricas.")
    if selected_lottery == "Lotofácil" and not special_mode:
        st.radio(
            "📍 Estratégia de Geração:",
            ["Gular & Steiner (19 Dezenas / 14 Desdobramentos)", "Tribo da Sorte (Estratégia Espelho / 2 Jogos de Elite)"],
            index=0,
            key="lf_generation_mode_radio"
        )

# Abas na Coluna Principal
with col_main:
    if selected_lottery == "Lotofácil":
        tab_generator, tab_saved, tab_check, tab_learning, tab_cobertura = st.tabs([
            "🎰 Gerar Palpites", 
            "💾 Meus Jogos Salvos", 
            "🔍 Conferência de Resultados",
            "🧠 Treinar Algoritmo (Ciclos)",
            "📈 Super-Cobertura (20-23 Dezenas)"
        ])
    else:
        tab_generator, tab_saved, tab_check, tab_learning = st.tabs([
            "🎰 Gerar Palpites", 
            "💾 Meus Jogos Salvos", 
            "🔍 Conferência de Resultados",
            "🧠 Treinar Algoritmo (Ciclos)"
        ])
    
    # ── TAB 1: GERADOR DE PROGNÓSTICOS ────────────────────────────────
    with tab_generator:
        st.write("### Prognósticos Otimizados por Hierarquia de Força Estatística")
        if selected_lottery == "Lotofácil" and not special_mode:
            # Calcular dados em tempo real para a Matriz de Análise
            hist_all_m = st.session_state.history["Lotofácil"]
            hist_m = hist_all_m[:30]
            
            co_occurrence_m = {i: {j: 0 for j in range(1, 26)} for i in range(1, 26)}
            for draw in hist_m:
                for u in draw:
                    for v in draw:
                        if u != v:
                            co_occurrence_m[u][v] += 1
            
            duques_m = []
            for u in range(1, 26):
                for v in range(u + 1, 26):
                    duques_m.append(((u, v), co_occurrence_m[u][v]))
            duques_m.sort(key=lambda x: x[1], reverse=True)
            top_duques_str = "  |  ".join([f"🍀 **{u:02d} e {v:02d}** ({count}x)" for (u, v), count in duques_m[:3]])
            
            # Ciclo de Ausentes
            curr_cycle_m = set()
            for draw in hist_m:
                curr_cycle_m.update(draw)
                if len(curr_cycle_m) == 25:
                    break
            missing_cycle_m = sorted(list(set(range(1, 26)) - curr_cycle_m))
            missing_str = " — ".join([f"**{n:02d}**" for n in missing_cycle_m]) if missing_cycle_m else "Ciclo fechado!"
            
            with st.expander("📊 MATRIZ DE ANÁLISE DE TODOS OS CONCURSOS (Tribo da Sorte)", expanded=True):
                st.markdown(f"""
                <div style='background-color:#111524; border:1px solid #2d3748; border-radius:12px; padding:15px; margin-bottom:10px;'>
                    <h5 style='color:#E2E8F0; margin-top:0;'>📊 Matriz de Estudos & Logística Reversa (Janela de 30 Concursos)</h5>
                    <ul style='color:#CBD5E0; font-size:0.85rem; padding-left:20px; line-height:1.6;'>
                        <li><b>👥 Dezenas Amigas (Duques de maior Co-ocorrência):</b> {top_duques_str}</li>
                        <li><b>⏳ Ciclo das Ausentes (Pendentes para Fechar):</b> {missing_str}</li>
                        <li><b>📈 Comportamento de Linhas (Frequência Média em 30 sorteios):</b>
                            <ul style='padding-left:15px; margin-top:4px;'>
                                <li>L1 (01-05): <b>{np.mean([sum(1 for x in d if 1<=x<=5) for d in hist_m]):.2f}</b> dezenas/concurso</li>
                                <li>L2 (06-10): <b>{np.mean([sum(1 for x in d if 6<=x<=10) for d in hist_m]):.2f}</b> dezenas/concurso</li>
                                <li>L3 (11-15): <b>{np.mean([sum(1 for x in d if 11<=x<=15) for d in hist_m]):.2f}</b> dezenas/concurso</li>
                                <li>L4 (16-20): <b>{np.mean([sum(1 for x in d if 16<=x<=20) for d in hist_m]):.2f}</b> dezenas/concurso</li>
                                <li>L5 (21-25): <b>{np.mean([sum(1 for x in d if 21<=x<=25) for d in hist_m]):.2f}</b> dezenas/concurso</li>
                            </ul>
                        </li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        # Botões de Geração e Regeneração Dinâmica
        col_gen1, col_gen2 = st.columns(2)
        with col_gen1:
            gerar_clicked = st.button("🚀 Executar Afunilamento e Gerar Prognósticos")
        with col_gen2:
            regenerar_clicked = st.button("🔄 Regenerar Palpites Dinamicamente")
            
        if gerar_clicked or regenerar_clicked:
            with st.spinner("Processando Cadeias de Markov, Onda de Calor e Guardião Estatístico..."):
                if selected_lottery == "Mega-Sena":
                    s, t, c, g_ten = generate_mega_sena(special_mode)
                elif selected_lottery == "Lotofácil":
                    is_tribo = (st.session_state.get("lf_generation_mode_radio") == "Tribo da Sorte (Estratégia Espelho / 2 Jogos de Elite)") if not special_mode else False
                    s, t, c, g_ten = generate_lotofacil(special_mode, tribo_mode=is_tribo)
                elif selected_lottery == "Lotomania":
                    s, t, c, g_ten = generate_lotomania()
                elif selected_lottery == "Quina":
                    s, t, c, g_ten = generate_quina(special_mode)
                else:
                    s, t, c, g_ten = generate_dupla_sena(special_mode)
                    
                st.session_state.active_supremo = s
                st.session_state.active_tendencia = t
                st.session_state.active_cobertura = c
                st.session_state.active_g_ten = g_ten
                st.session_state.generated_lottery = selected_lottery
                st.session_state.is_special_app = special_mode
                st.success("Jogos gerados, auditados e validados pelo Guardião Estatístico com a Dezena de Ouro como âncora!")

        # Exibição dos Prognósticos Ativos
        if "active_supremo" in st.session_state and st.session_state.generated_lottery == selected_lottery:
            s = st.session_state.active_supremo
            t = st.session_state.active_tendencia
            c = st.session_state.active_cobertura
            g_ten = st.session_state.active_g_ten
            is_spec = st.session_state.get("is_special_app", False)
            
            ball_class = {
                "Mega-Sena": "ball-mega",
                "Lotofácil": "ball-facil",
                "Lotomania": "ball-mania",
                "Quina": "ball-quina",
                "Dupla Sena": "ball-dupla"
            }[selected_lottery]
            
            # --- DEZENA DE OURO DESTAQUE ---
            st.markdown(f"""
            <div style='background-color:#FEFCBF; border:2px solid #ECC94B; border-radius:10px; padding:10px; text-align:center; margin-bottom:15px;'>
                <h4 style='color:#744210; margin:0;'>⭐ DEZENA DE OURO ANCADA: <span style='font-size:1.4rem; font-weight:bold;'>{g_ten:02d}</span></h4>
                <p style='color:#744210; margin:0; font-size:0.9rem;'>Esta dezena âncora está presente em todos os 3 palpites abaixo!</p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- MATRIZ COMBINATÓRIA SINALIZADA E ADAPTADA ---
            if selected_lottery == "Lotofácil" and not is_spec:
                is_tribo = (st.session_state.get("lf_generation_mode_radio") == "Tribo da Sorte (Estratégia Espelho / 2 Jogos de Elite)")
                if is_tribo and "tribo_fixed_nums" in st.session_state:
                    st.markdown(f"""
                    <div style='background-color:#1c142c; border:1px solid #4A3E70; border-radius:12px; padding:15px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);'>
                        <h4 style='color:#E2E8F0; margin-top:0; font-size:1.1rem;'>🧬 Estratégia Tribo da Sorte — Duplo Espelho Complementar</h4>
                        <p style='color:#A0AEC0; font-size:0.85rem; margin-bottom:12px;'>O volante de 25 foi reduzido usando <b>5 Dezenas Fixas de Elite</b> (com base nas maiores co-ocorrências/"Dezenas Amigas"). As outras 20 dezenas foram divididas em dois grupos complementares (Set A e Set B) e otimizadas via Monte Carlo!</p>
                        <div style='margin-bottom:10px;'>
                            <b>📌 5 Dezenas Fixas de Elite (Âncoras Amigas):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#D69E2E; color:black; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.tribo_fixed_nums])}
                        </div>
                        <div style='margin-bottom:10px;'>
                            <b>🔄 Set A (10 Dezenas Dinâmicas do Espelho A):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#3182CE; color:white; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.tribo_set_a])}
                        </div>
                        <div style='margin-bottom:10px;'>
                            <b>🔄 Set B (10 Dezenas Dinâmicas do Espelho B - Complementares):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#319795; color:white; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.tribo_set_b])}
                        </div>
                        <div style='margin-top:12px; font-size:0.8rem; color:#A0AEC0; font-style:italic;'>
                            *Garantia Matemática: Acertando as 5 Dezenas Fixas, você tem a garantia matemática de colocar pelo menos um cartão na zona de premiação (11 a 15 pontos) se a distribuição dos 10 acertos dinâmicos não for exatamente de 5/5!
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif "gular_fixed_nums" in st.session_state:
                    st.markdown(f"""
                    <div style='background-color:#F7FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:15px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        <h4 style='color:#2D3748; margin-top:0; font-size:1.1rem;'>🧬 Matriz Combinatória Steiner de Leandro Gular (19 Dezenas)</h4>
                        <p style='color:#4A5568; font-size:0.85rem; margin-bottom:12px;'>O volante de 25 foi reduzido para 19 dezenas de elite, cruzando as <b>Zonas de Transição de 10 concursos</b> com as <b>Cadeias de Markov</b> para atingir a zona de premiação!</p>
                        <div style='margin-bottom:10px;'>
                            <b>📌 11 Dezenas Fixas (Esqueleto de Ouro):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#2B6CB0; color:white; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.gular_fixed_nums])}
                        </div>
                        <div style='margin-bottom:10px;'>
                            <b>🔄 8 Dezenas Variáveis (Fechamento Steiner 14 Jogos):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#319795; color:white; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.gular_variable_nums])}
                        </div>
                        <div style='margin-bottom:10px;'>
                            <b>❌ 6 Dezenas Excluídas (Sinais de Baixa Assertividade):</b><br>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:3px 8px; background-color:#FEB2B2; color:#9B2C2C; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in st.session_state.gular_excluded_nums])}
                        </div>
                        <div style='margin-top:12px; font-size:0.8rem; color:#718096; font-style:italic;'>
                            *Esta estrutura trava o corredor de repetidas em exatamente [8 a 11 dezenas repetidas] em cada um dos 14 desdobramentos de Steiner. Os 3 melhores jogos estatísticos filtrados pelo Guardião PRO são exibidos abaixo!
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            is_tribo = (selected_lottery == "Lotofácil" and st.session_state.get("lf_generation_mode_radio") == "Tribo da Sorte (Estratégia Espelho / 2 Jogos de Elite)") if not is_spec else False
            
            # --- SUPREMO ---
            if is_tribo:
                st.markdown(f"#### <span class='badge-supremo' style='border-left-color: #805AD5;'>1º PALPITE — TRIBO ESPELHO A (Espelho Complementar A)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"#### <span class='badge-supremo'>1º PALPITE — O SUPREMO (Aposta Master — {'Especial Sazonal' if is_spec else 'Peso Máximo'})</span>", unsafe_allow_html=True)
            
            # Highlight golden ten in Supremo list
            balls_html = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in s])
            st.markdown(f"<div class='ball-container'>{balls_html}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Supremo", key="save_sup"):
                save_type = "Supremo"
                if is_spec:
                    save_type = "Supremo (Especial)"
                elif is_tribo:
                    save_type = "Tribo Espelho A"
                pred = {"lottery": selected_lottery, "type": save_type, "numbers": s, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Supremo Salvo!", icon="💾")
            
            st.divider()
            
            # --- TENDÊNCIA ---
            if is_tribo:
                st.markdown(f"#### <span class='badge-tendencia' style='border-left-color: #3182CE;'>2º PALPITE — TRIBO ESPELHO B (Espelho Complementar B)</span>", unsafe_allow_html=True)
            else:
                st.markdown("#### <span class='badge-tendencia'>2º PALPITE — A TENDÊNCIA CRUZADA (Peso Médio)</span>", unsafe_allow_html=True)
            balls_html_t = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in t])
            st.markdown(f"<div class='ball-container'>{balls_html_t}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Tendência", key="save_tend"):
                save_type_t = "Tendência"
                if is_tribo:
                    save_type_t = "Tribo Espelho B"
                pred = {"lottery": selected_lottery, "type": save_type_t, "numbers": t, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Tendência Salvo!", icon="💾")
                    
            st.divider()
            
            # --- COBERTURA ---
            if is_tribo:
                st.markdown(f"#### <span class='badge-cobertura' style='border-left-color: #319795;'>3º PALPITE — TRIBO COBERTURA (Max Verossimilhança)</span>", unsafe_allow_html=True)
            else:
                st.markdown("#### <span class='badge-cobertura'>3º PALPITE — A COBERTURA DE SEGURANÇA (Peso de Cobertura)</span>", unsafe_allow_html=True)
            balls_html_c = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in c])
            st.markdown(f"<div class='ball-container'>{balls_html_c}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Cobertura", key="save_cob"):
                save_type_c = "Cobertura"
                if is_tribo:
                    save_type_c = "Tribo Cobertura"
                pred = {"lottery": selected_lottery, "type": save_type_c, "numbers": c, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Cobertura Salvo!", icon="💾")
            
            st.divider()
            
            if selected_lottery == "Lotofácil" and is_spec and "independencia_games" in st.session_state:
                g4 = st.session_state.independencia_games[3]
                g5 = st.session_state.independencia_games[4]
                
                # --- JOGO 4 ---
                st.markdown(f"#### <span class='badge-tendencia' style='border-left-color:#805AD5;'>4º PALPITE — JOGO EXTRA 4 (Peso Auxiliar)</span>", unsafe_allow_html=True)
                balls_html_g4 = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in g4])
                st.markdown(f"<div class='ball-container'>{balls_html_g4}</div>", unsafe_allow_html=True)
                
                if st.button("💾 Salvar Palpite Jogo 4", key="save_g4"):
                    pred = {"lottery": selected_lottery, "type": "Jogo 4 (Independência)", "numbers": g4, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                    if pred not in st.session_state.saved_predictions:
                        st.session_state.saved_predictions.append(pred)
                        save_predictions(st.session_state.saved_predictions)
                        st.toast("Palpite Jogo 4 Salvo!", icon="💾")
                        
                st.divider()
                
                # --- JOGO 5 ---
                st.markdown(f"#### <span class='badge-cobertura' style='border-left-color:#319795;'>5º PALPITE — JOGO EXTRA 5 (Peso Auxiliar)</span>", unsafe_allow_html=True)
                balls_html_g5 = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in g5])
                st.markdown(f"<div class='ball-container'>{balls_html_g5}</div>", unsafe_allow_html=True)
                
                if st.button("💾 Salvar Palpite Jogo 5", key="save_g5"):
                    pred = {"lottery": selected_lottery, "type": "Jogo 5 (Independência)", "numbers": g5, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                    if pred not in st.session_state.saved_predictions:
                        st.session_state.saved_predictions.append(pred)
                        save_predictions(st.session_state.saved_predictions)
                        st.toast("Palpite Jogo 5 Salvo!", icon="💾")
                        
                st.divider()
                
                if st.button("💾 Salvar os 5 Palpites da Independência", key="save_all_5"):
                    saved_count = 0
                    types_all = ["Jogo 1 (Independência)", "Jogo 2 (Independência)", "Jogo 3 (Independência)", "Jogo 4 (Independência)", "Jogo 5 (Independência)"]
                    for idx, g_p in enumerate(st.session_state.independencia_games):
                        pred = {"lottery": selected_lottery, "type": types_all[idx], "numbers": g_p, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                        if pred not in st.session_state.saved_predictions:
                            st.session_state.saved_predictions.append(pred)
                            saved_count += 1
                    if saved_count > 0:
                        save_predictions(st.session_state.saved_predictions)
                        st.toast(f"✅ {saved_count} palpites salvos com sucesso!", icon="💾")
                        st.rerun()
                
                st.divider()
                
            if selected_lottery == "Lotofácil" and is_spec and "independencia_tab1" in st.session_state:
                st.markdown("### 📊 Relatório Analítico da Lotofácil da Independência (Etapa 8)")
                
                st.write("#### 1. Frequência Total e Atraso — Lotofácil da Independência (Etapa 1)")
                st.dataframe(st.session_state.independencia_tab1)
                
                st.write("#### 2. Frequência Total e Atraso — Lotofácil Normal (Etapa 2)")
                st.dataframe(st.session_state.independencia_tab2)
                
                st.write("#### 3. Tabela de Pontuação Final das 25 Dezenas (Etapa 3)")
                st.dataframe(st.session_state.independencia_scores)
                
                st.write("#### 4. Ranking Final das Dezenas Mais Fortes (Etapa 3 & 4)")
                st.write(" — ".join([f"**{idx+1}º** ({num:02d})" for idx, num in enumerate(st.session_state.independencia_ranking)]))
                
                st.write("#### 5. Dezenas Fixas Selecionadas (Etapa 5)")
                st.write(f"📌 **Fixas Jogos 1, 3, 5 (7 dezenas):** " + " — ".join([f"{num:02d}" for num in st.session_state.ind_fixed_135]))
                st.write(f"📌 **Fixas Jogos 2, 4 (8 dezenas):** " + " — ".join([f"{num:02d}" for num in st.session_state.ind_fixed_24]))
                
                st.write("#### 6. Pool de Dezenas Variáveis Selecionadas (Etapa 5)")
                st.write(" — ".join([f"{num:02d}" for num in st.session_state.ind_variables_pool]))
                st.divider()
            
            # --- EXPORTAÇÃO E DOWNLOADS ---
            st.markdown("### 📥 Exportar Resultados Deste Lote")
            col_exp1, col_gen_xlsx, col_gen_pdf = st.columns(3)
            
            games_to_export = [s, t, c]
            if selected_lottery == "Lotofácil" and is_spec and "independencia_games" in st.session_state:
                games_to_export = st.session_state.independencia_games
                
            with col_exp1:
                txt_palpites = f"PALPITES OTIMIZADOS -- {selected_lottery.upper()}\n\n"
                txt_palpites += f"Dezena de Ouro (Ancora): {g_ten:02d}\n\n"
                names_export = ["1o Palpite - Supremo", "2o Palpite - Tendencia", "3o Palpite - Cobertura", "4o Palpite", "5o Palpite"]
                for idx, g in enumerate(games_to_export):
                    g_name = names_export[idx] if idx < len(names_export) else f"Jogo {idx+1}"
                    txt_palpites += f"{g_name}: {' '.join([f'{n:02d}' for n in g])}\n"
                st.download_button(
                    label="📋 Copiar / Baixar como Texto (TXT)",
                    data=txt_palpites,
                    file_name=f"palpites_{selected_lottery.lower()}.txt",
                    mime="text/plain"
                )
                
            with col_gen_xlsx:
                xlsx_data = get_xlsx_download_data(games_to_export, g_ten, selected_lottery)
                st.download_button(
                    label=" Excel Planilha (XLSX)",
                    data=xlsx_data,
                    file_name=f"palpites_{selected_lottery.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            with col_gen_pdf:
                pdf_data = get_pdf_download_data(games_to_export, g_ten, selected_lottery)
                st.download_button(
                    label="📕 Baixar E-book (PDF)",
                    data=pdf_data,
                    file_name=f"ebook_palpites_{selected_lottery.lower()}.pdf",
                    mime="application/pdf"
                )
            
            # --- VISUAL GRAPHS ---
            st.markdown("### 📊 Distribuição por Quadrantes de Taufic Darhal")
            # Count Supremo numbers in each quadrant
            q_counts = [0, 0, 0, 0]
            for n in s:
                if selected_lottery == "Lotofácil":
                    if 1 <= n <= 7: q_counts[0] += 1
                    elif 8 <= n <= 13: q_counts[1] += 1
                    elif 14 <= n <= 19: q_counts[2] += 1
                    elif 20 <= n <= 25: q_counts[3] += 1
                elif selected_lottery == "Lotomania":
                    v = 0 if n == 0 else n
                    if 0 <= v <= 24: q_counts[0] += 1
                    elif 25 <= v <= 49: q_counts[1] += 1
                    elif 50 <= v <= 74: q_counts[2] += 1
                    elif 75 <= v <= 99: q_counts[3] += 1
                elif selected_lottery == "Mega-Sena":
                    if 1 <= n <= 15: q_counts[0] += 1
                    elif 16 <= n <= 30: q_counts[1] += 1
                    elif 31 <= n <= 45: q_counts[2] += 1
                    elif 46 <= n <= 60: q_counts[3] += 1
                elif selected_lottery == "Quina":
                    if 1 <= n <= 20: q_counts[0] += 1
                    elif 21 <= n <= 40: q_counts[1] += 1
                    elif 41 <= n <= 60: q_counts[2] += 1
                    elif 61 <= n <= 80: q_counts[3] += 1
                elif selected_lottery == "Dupla Sena":
                    if 1 <= n <= 12: q_counts[0] += 1
                    elif 13 <= n <= 25: q_counts[1] += 1
                    elif 26 <= n <= 38: q_counts[2] += 1
                    elif 39 <= n <= 50: q_counts[3] += 1
            
            chart_df = pd.DataFrame({
                "Quadrantes (Método Darhal)": ["Q1", "Q2", "Q3", "Q4"],
                "Quantidade de Dezenas (Palpite Supremo)": q_counts
            })
            st.bar_chart(chart_df.set_index("Quadrantes (Método Darhal)"))
            
            # --- TABELA CONDICIONAL SE X ──> ENTÃO Y ---
            st.markdown("### 📊 Tabela de Padrão Condicional Aplicada (Último Sorteio)")
            hist = st.session_state.history[selected_lottery]
            last_draw = hist[0]
            last_draw_flat = last_draw[0] + last_draw[1] if selected_lottery == "Dupla Sena" and isinstance(last_draw[0], list) else last_draw
            
            max_val_m = 25 if selected_lottery == "Lotofácil" else (50 if selected_lottery == "Dupla Sena" else (60 if selected_lottery == "Mega-Sena" else (80 if selected_lottery == "Quina" else 100)))
            transitions = calculate_markov(hist, max_val_m)
            
            cond_data = []
            for x in last_draw_flat:
                if x in transitions:
                    sorted_y = sorted(transitions[x].items(), key=lambda item: item[1], reverse=True)[:3]
                    followers_str = " — ".join([f"{y:02d} ({count}x)" for y, count in sorted_y if count > 0])
                    if not followers_str:
                        followers_str = "Sem histórico"
                    cond_data.append({"Dezena Anterior (X)": f"{x:02d}", "Seguidores Mais Prováveis (Y) (Frequência)": followers_str})
                    
            st.table(pd.DataFrame(cond_data))
            
        else:
            st.info("Aperte no botão acima para rodar a análise estatística multi-camadas e ver os palpites.")

    # ── TAB 2: MEUS JOGOS SALVOS ──────────────────────────────────────
    with tab_saved:
        st.write("### 💾 Seus Jogos Salvos")
        
        # ── SEÇÃO DE SEGURANÇA E BACKUP (ANTI-PERDA STREAMLIT CLOUD) ──
        st.markdown("""
        <div style='background-color:#EBF8FF; border:1px solid #BEE3F8; border-radius:10px; padding:12px; margin-bottom:15px;'>
            <h5 style='color:#2B6CB0; margin:0;'>🛡️ Backup e Restauração Contra Perda de Dados</h5>
            <p style='color:#2D3748; margin:5px 0 10px 0; font-size:0.85rem;'>Como servidores em nuvem (Streamlit Cloud) são reiniciados periodicamente, os seus jogos salvos podem ser limpos da memória temporária do servidor. Para garantir persistência total, baixe o arquivo de backup abaixo e faça o upload quando reabrir o app!</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_bak1, col_bak2 = st.columns(2)
        with col_bak1:
            all_preds_json = json.dumps(st.session_state.saved_predictions, ensure_ascii=False, indent=2)
            st.download_button(
                label="📤 Baixar Backup Completo de Segurança (JSON)",
                data=all_preds_json,
                file_name="backup_loterias_pro.json",
                mime="application/json"
            )
        with col_bak2:
            uploaded_bak = st.file_uploader("📥 Restaurar Backup Salvo (JSON):", type=["json"], key="upload_bak_v21")
            if uploaded_bak is not None:
                try:
                    imported_list = json.load(uploaded_bak)
                    if isinstance(imported_list, list):
                        added_count = 0
                        for pred in imported_list:
                            if isinstance(pred, dict) and "lottery" in pred and "numbers" in pred:
                                if pred not in st.session_state.saved_predictions:
                                    st.session_state.saved_predictions.append(pred)
                                    added_count += 1
                        if added_count > 0:
                            save_predictions(st.session_state.saved_predictions)
                            st.success(f"✅ {added_count} jogos restaurados com sucesso!")
                            st.rerun()
                        else:
                            st.info("Nenhum jogo novo ou formato diferente detectado.")
                    else:
                        st.error("Arquivo de backup inválido.")
                except Exception as e:
                    st.error(f"Erro ao processar backup: {e}")
        
        # ── MOTOR DE CORREÇÃO AUTOMÁTICA DE CONCURSO ESPECÍFICO (OPCIONAL) ──
        st.write("### 🔍 Correção e Validação Automática de Desempenho")
        st.markdown("Insira o número de um concurso específico para validar os acertos e acompanhar o desempenho dos seus jogos salvos de forma automatizada e em tempo real:")
        
        c_check_num = st.number_input("Digite o número do concurso para conferência:", min_value=0, value=0, step=1, key="concurso_checker_saved_games_v24")
        
        compare_draw = None
        compare_concurso_num = None
        if c_check_num > 0:
            target_draw, source_api = get_concurso_dezenas(selected_lottery, c_check_num)
            if target_draw:
                if selected_lottery == "Dupla Sena":
                    s1_str = " — ".join([f"{n:02d}" for n in target_draw[0]])
                    s2_str = " — ".join([f"{n:02d}" for n in target_draw[1]])
                    st.success(f"✅ Concurso #{c_check_num} localizado com sucesso via {source_api}!\n\n* **1º Sorteio:** {s1_str}\n* **2º Sorteio:** {s2_str}")
                else:
                    draw_str = " — ".join([f"{n:02d}" for n in target_draw])
                    st.success(f"✅ Concurso #{c_check_num} localizado com sucesso via {source_api}! Dezenas: **{draw_str}**")
                compare_draw = target_draw
                compare_concurso_num = c_check_num
            else:
                st.warning(f"⚠️ Concurso #{c_check_num} não encontrado no histórico local nem nas APIs de consulta da Caixa.")
                
        if compare_draw:
            st.info("💡 **Acompanhamento de Desempenho:** Deseja fixar o concurso de referência para esses jogos permanentemente?")
            if st.button("🔄 Sincronizar Concursos de Referência dos Jogos Salvos", key="sync_ref_concursos_v25"):
                for p_saved in st.session_state.saved_predictions:
                    if p_saved["lottery"] == selected_lottery:
                        p_saved["ref"] = compare_concurso_num
                save_predictions(st.session_state.saved_predictions)
                st.toast(f"✅ Todos os jogos salvos de {selected_lottery} foram vinculados ao Concurso #{compare_concurso_num}!", icon="🔄")
                st.rerun()
                
        # Filtro de Contexto por Loteria Ativa
        filtered_preds = [(idx, pred) for idx, pred in enumerate(st.session_state.saved_predictions) if pred["lottery"] == selected_lottery]
        
        if not filtered_preds:
            st.info(f"Nenhum palpite salvo para {selected_lottery} até o momento.")
        else:
            to_delete = []
            for idx_orig, pred in filtered_preds:
                col_info, col_action = st.columns([4, 1])
                with col_info:
                    p_g_ten = pred.get("g_ten", 1)
                    st.markdown(f"**{pred['lottery'].upper()}** - *{pred['type']}* (Salvo em: {pred['date']}) -- ⭐ Dezena de Ouro: **{p_g_ten:02d}**")
                    
                    if compare_draw:
                        dezenas_jogo = set(pred['numbers'])
                        if selected_lottery == "Dupla Sena":
                            dezenas_sorteadas_1 = set(compare_draw[0])
                            dezenas_sorteadas_2 = set(compare_draw[1])
                            acertos_1 = len(dezenas_jogo.intersection(dezenas_sorteadas_1))
                            acertos_2 = len(dezenas_jogo.intersection(dezenas_sorteadas_2))
                            st.markdown(f"🎯 **Desempenho no Concurso #{compare_concurso_num}:** {acertos_1} acertos (1º Sorteio) | {acertos_2} acertos (2º Sorteio)")
                            
                            balls_html_s = ""
                            for n in pred['numbers']:
                                if n in dezenas_sorteadas_1 or n in dezenas_sorteadas_2:
                                    bg_color = "#C6F6D5"
                                    border_color = "#38A169"
                                    text_color = "#22543D"
                                else:
                                    bg_color = "#FEFCBF" if n == p_g_ten else "#EDF2F7"
                                    border_color = "#ECC94B" if n == p_g_ten else "#CBD5E0"
                                    text_color = "#2D3748"
                                balls_html_s += f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:{bg_color}; border:1px solid {border_color}; border-radius:4px; font-weight:bold; font-size:0.85rem; color:{text_color};'>{n:02d}</span>"
                        else:
                            dezenas_sorteadas = set(compare_draw)
                            acertos = len(dezenas_jogo.intersection(dezenas_sorteadas))
                            st.markdown(f"🎯 **Desempenho no Concurso #{compare_concurso_num}:** **{acertos} acertos!**")
                            
                            balls_html_s = ""
                            for n in pred['numbers']:
                                if n in dezenas_sorteadas:
                                    bg_color = "#C6F6D5"
                                    border_color = "#38A169"
                                    text_color = "#22543D"
                                else:
                                    bg_color = "#FEFCBF" if n == p_g_ten else "#EDF2F7"
                                    border_color = "#ECC94B" if n == p_g_ten else "#CBD5E0"
                                    text_color = "#2D3748"
                                balls_html_s += f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:{bg_color}; border:1px solid {border_color}; border-radius:4px; font-weight:bold; font-size:0.85rem; color:{text_color};'>{n:02d}</span>"
                    else:
                        balls_html_s = "".join([f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:#FEFCBF; border:1px solid #ECC94B; border-radius:4px; font-weight:bold; font-size:0.85rem;'>{f'{n:02d}' if n != 0 else '00'}</span>" if n == p_g_ten else f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:#edf2f7; border-radius:4px; font-weight:bold; font-size:0.85rem;'>{f'{n:02d}' if n != 0 else '00'}</span>" for n in pred['numbers']])
                    
                    st.markdown(f"<div>{balls_html_s}</div>", unsafe_allow_html=True)
                with col_action:
                    if st.button("❌ Excluir", key=f"del_{idx_orig}"):
                        to_delete.append(idx_orig)
                        
                st.markdown("---")
                
            if to_delete:
                for idx_to_del in sorted(to_delete, reverse=True):
                    st.session_state.saved_predictions.pop(idx_to_del)
                save_predictions(st.session_state.saved_predictions)
                st.toast("Palpite excluído com sucesso!", icon="🗑️")
                st.rerun()
                
            # Exportador focado na Loteria Ativa
            txt_data = ""
            for _, pred in filtered_preds:
                num_str = " ".join([f"{n:02d}" for n in pred['numbers']])
                txt_data += f"{pred['lottery']} - {pred['type']} - {pred['date']} (Dezena de Ouro: {pred.get('g_ten', 1):02d})\n{num_str}\n\n"
                
            st.download_button(
                label=f"📥 Exportar Jogos de {selected_lottery} para Bloco de Notas (TXT)",
                data=txt_data,
                file_name=f"meus_palpites_{selected_lottery.lower()}_otimizados.txt",
                mime="text/plain"
            )

    # ── TAB 3: CONFERÊNCIA INTELIGENTE ────────────────────────────────
    with tab_check:
        st.write("### 🔍 Conferência de Prognósticos")
        
        # Filtro de Contexto por Loteria Ativa para Conferência
        filtered_preds_check = [(idx, pred) for idx, pred in enumerate(st.session_state.saved_predictions) if pred["lottery"] == selected_lottery]
        
        if not filtered_preds_check:
            st.warning(f"É necessário possuir jogos salvos de {selected_lottery} para realizar a conferência.")
        else:
            st.markdown("#### 1. Escolha o Jogo Salvo para Conferir:")
            game_options = [f"{idx} - {p['lottery']} ({p['type']})" for idx, p in filtered_preds_check]
            selected_game_idx_str = st.selectbox("Selecione o palpite:", game_options)
            selected_game_idx_orig = int(selected_game_idx_str.split(" - ")[0])
            target_prediction = st.session_state.saved_predictions[selected_game_idx_orig]
            
            st.markdown("#### 2. Insira as Dezenas Sorteadas para Conferir:")
            check_mode = st.radio("Método de entrada do sorteio:", ["Último concurso oficial da base", "Digitar dezenas manualmente"])
            
            if check_mode == "Último concurso oficial da base":
                target_lottery = target_prediction['lottery']
                raw_draw = st.session_state.history[target_lottery][0]
                real_draw = raw_draw[0] if isinstance(raw_draw[0], list) else raw_draw
                st.info(f"Conferindo contra o Concurso mais recente de **{target_lottery}** na base: " + " — ".join([f"{n:02d}" for n in real_draw]))
            else:
                input_str = st.text_input("Digite as dezenas separadas por espaço (ex: 05 11 24 33 46):")
                if input_str:
                    try:
                        real_draw = [int(x) for x in input_str.split()]
                    except ValueError:
                        st.error("Por favor, digite apenas números inteiros válidos.")
                        real_draw = []
                else:
                    real_draw = []
                    
            if st.button("🎯 Conferir Acertos"):
                if not real_draw:
                    st.warning("Por favor, insira ou selecione dezenas válidas.")
                else:
                    p_nums = set(target_prediction['numbers'])
                    r_nums = set(real_draw)
                    hits = p_nums.intersection(r_nums)
                    
                    st.markdown(f"### 🎉 Resultado: {len(hits)} acertos!")
                    
                    display_html = []
                    for num in target_prediction['numbers']:
                        if num in hits:
                            display_html.append(f"<span style='display:inline-block; margin:4px; padding:8px 12px; background-color:#c6f6d5; border:3px solid #38a169; border-radius:50%; font-weight:bold; color:#22543d; font-size:1.1rem;'>{num:02d}</span>")
                        else:
                            display_html.append(f"<span style='display:inline-block; margin:4px; padding:8px 12px; background-color:#edf2f7; border:1px solid #cbd5e0; border-radius:50%; font-weight:bold; color:#718096; font-size:1.1rem;'>{num:02d}</span>")
                    st.markdown(f"<div style='text-align:center;'>{''.join(display_html)}</div>", unsafe_allow_html=True)

    # ── TAB 4: TREINAMENTO E CICLOS ───────────────────────────────────
    with tab_learning:
        st.write("### 🧠 Treinar Sistema e Atualizar Métricas")
        st.write("Insira os novos resultados oficiais para reajustar a **Cadeia de Markov** e recalcular as **Dezenas de Ouro**.")
        
        st.markdown("#### Adicionar Novo Concurso:")
        lot_to_train = st.selectbox("Selecione a Loteria para alimentar:", ["Mega-Sena", "Lotofácil", "Lotomania", "Quina", "Dupla Sena"])
        
        # Dupla Sena exige 2 sorteios na entrada
        if lot_to_train == "Dupla Sena":
            new_draw_str1 = st.text_input("Digite as 6 dezenas do 1º Sorteio (separadas por espaço):", key="train_input_d1")
            new_draw_str2 = st.text_input("Digite as 6 dezenas do 2º Sorteio (separadas por espaço):", key="train_input_d2")
            
            if st.button("🧠 Alimentar Inteligência Estatística Dupla"):
                try:
                    d1 = sorted([int(x) for x in new_draw_str1.split()])
                    d2 = sorted([int(x) for x in new_draw_str2.split()])
                    if len(d1) != 6 or len(d2) != 6:
                        st.error("Cada sorteio da Dupla Sena deve conter exatamente 6 dezenas.")
                    else:
                        st.session_state.history["Dupla Sena"].insert(0, [d1, d2])
                        st.success("Concurso da Dupla Sena adicionado de forma segregada e treinado com sucesso!")
                except ValueError:
                    st.error("Por favor, insira números válidos.")
        else:
            new_draw_str = st.text_input("Digite as dezenas do novo concurso (separadas por espaço):", key="train_input")
            
            if st.button("🧠 Alimentar Inteligência Estatística"):
                if new_draw_str:
                    try:
                        new_draw = sorted([int(x) for x in new_draw_str.split()])
                        req_len = 6 if lot_to_train == "Mega-Sena" else (15 if lot_to_train == "Lotofácil" else (5 if lot_to_train == "Quina" else 20))
                        if len(new_draw) != req_len:
                            st.error(f"Erro: O sorteio para a {lot_to_train} deve conter exatamente {req_len} dezenas.")
                        else:
                            st.session_state.history[lot_to_train].insert(0, new_draw)
                            st.success(f"Concurso adicionado com sucesso! A base agora conta com {len(st.session_state.history[lot_to_train])} concursos sequenciais.")
                    except ValueError:
                        st.error("Por favor, digite dezenas válidas.")
                else:
                    st.warning("Por favor, digite as dezenas antes de treinar.")
                
        # Exibe histórico atual
        st.markdown("#### Histórico de Concursos na Memória de Treino:")
        df_history = []
        for idx, draw in enumerate(st.session_state.history[lot_to_train]):
            if lot_to_train == "Dupla Sena":
                draw_repr = f"1º Sorteio: {draw[0]} | 2º Sorteio: {draw[1]}"
            else:
                draw_repr = " — ".join([f"{n:02d}" for n in draw])
            df_history.append({"Posição": f"Concurso {idx+1}", "Dezenas": draw_repr})
        st.table(pd.DataFrame(df_history))


    # ── TAB 5: SUPER-COBERTURA COMBINATÓRIA (CARLOS LOTERIA) ───────────
    if selected_lottery == "Lotofácil":
        with tab_cobertura:
            st.write("### 📈 Super-Cobertura Histórica de Alta Densidade")
            st.markdown("""
            Este módulo implementa a técnica de **Super-Cobertura Histórica de Alta Densidade (Gerador 20-23)** [Carlos Loteria].
            O algoritmo executa uma varredura matemática completa em todo o histórico de concursos na memória para encontrar
            os grupos de **20, 21, 22 ou 23 dezenas** que mais vezes obtiveram **15 pontos (cobertura máxima)** na Lotofácil.
            
            O sistema calcula e exibe de forma instantânea:
            * **🏆 Hits (15 acertos):** Total de concursos em que o grupo de dezenas já pontuou com 15 pontos.
            * **⏳ Atraso Atual (Gap):** Quantidade de sorteios consecutivos de atraso desde a última ocorrência de 15 pontos do grupo.
            * **🏜️ Maior Seca (Max Gap):** O pior atraso histórico de sorteios acumulados sem pontuar.
            
            *Esta ferramenta de elite é ideal para apostadores de **Lotinha** ou para selecionar os melhores grupos para realizar desdobramentos de alta cobertura financeira!*
            """)
            
            k_val = st.radio(
                "Selecione o tamanho do grupo para fazer a varredura:",
                options=[20, 21, 22, 23],
                format_func=lambda x: f"Grupo de {x} Dezenas (Varredura de {25 if x==25 else (53130 if x==20 else (12650 if x==21 else (2300 if x==22 else 300))):,} combinatórias)",
                horizontal=True,
                key="carlos_loteria_k"
            )
            
            col_cov_b1, col_cov_b2 = st.columns([2, 1])
            with col_cov_b1:
                executar_clicked = st.button("🔍 Executar Varredura de Alta Performance Vetorial", key="run_carlos_loteria")
            with col_cov_b2:
                limpar_cov = st.button("🗑️ Limpar Varredura", key="clear_carlos_loteria")
                
            if limpar_cov:
                if "top_cobertura_combs" in st.session_state:
                    del st.session_state.top_cobertura_combs
                st.rerun()
                
            if executar_clicked:
                with st.spinner("Analisando combinações vetoriais via Álgebra Linear NumPy..."):
                    history_lf = st.session_state.history["Lotofácil"]
                    top_combs = find_best_combinations_numpy(history_lf, k=k_val, top_n=10)
                    st.session_state.top_cobertura_combs = top_combs
                    st.session_state.active_k_val = k_val
                    st.success("Varredura concluída com sucesso em milissegundos!")
                    
            if "top_cobertura_combs" in st.session_state and st.session_state.get("active_k_val") == k_val:
                combs = st.session_state.top_cobertura_combs
                st.markdown(f"#### 🏆 Top 10 Grupos de {k_val} Dezenas — Maior Cobertura de 15 Pontos")
                
                for idx, item in enumerate(combs):
                    st.markdown(f"""
                    <div style='background-color:#1A2234; border:1px solid #2D3A52; border-radius:12px; padding:15px; margin-bottom:12px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>
                            <span style='color:#F59E0B; font-weight:bold; font-size:1.05rem;'>🥇 {idx+1}º Lugar — Cobertura: {item['hits_15']}x (15 acertos)</span>
                            <span style='background-color:#0D9488; color:white; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:bold;'>MOMC Elite</span>
                        </div>
                        <div style='margin-bottom:12px; display:flex; flex-wrap:wrap; gap:4px;'>
                            {' '.join([f'<span style="display:inline-block; margin:2px; padding:4px 8px; background-color:#2B364E; color:white; border-radius:4px; font-weight:bold; font-size:0.85rem;">{n:02d}</span>' for n in item['dezenas']])}
                        </div>
                        <div style='font-size:0.85rem; color:#94A3B8;'>
                            ⏳ <b>Atraso Atual (Gap):</b> {item['atraso_atual']} concursos | 🏜️ <b>Maior Seca Histórica (Max Gap):</b> {item['max_atraso_historico']} concursos
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Desdobrador Integrado
                st.markdown("---")
                st.write("### ⚡ Desdobrador de Elite Carlos Loteria")
                st.markdown("Selecione um dos 10 grupos de maior cobertura acima para desdobrar em **3 palpites cirúrgicos de 15 dezenas** altamente otimizados:")
                
                comb_options = [f"{i+1}º Lugar (Cobertura: {item['hits_15']}x, Gap: {item['atraso_atual']})" for i, item in enumerate(combs)]
                selected_comb_str = st.selectbox("Selecione o grupo para desdobrar:", comb_options, key="selectbox_carlos")
                selected_idx = comb_options.index(selected_comb_str)
                target_comb = combs[selected_idx]["dezenas"]
                
                if st.button("⚡ Gerar 3 Jogos de Elite Desdobrados", key="desdobrar_carlos"):
                    with st.spinner("Desdobrando grupo com otimização multiobjetivo e Guardião Estatístico..."):
                        # Obter os pesos unificados apenas para as dezenas do grupo selecionado
                        all_weights = get_unified_weights("Lotofácil", st.session_state.history["Lotofácil"], st.session_state.history["Lotofácil"][0])
                        
                        # Realiza simulação de Monte Carlo para encontrar as melhores combinações dentro do subset
                        scored_candidates = []
                        for _ in range(150):
                            g = sorted(random.sample(target_comb, 15))
                            is_valid, _ = statistical_guardian(g, "Lotofácil")
                            score = evaluate_game_score(g, "Lotofácil", all_weights)
                            if not is_valid:
                                score -= 20.0
                            scored_candidates.append((score, g))
                        scored_candidates.sort(key=lambda x: x[0], reverse=True)
                        
                        s_game = scored_candidates[0][1]
                        
                        # Localizar Tendência com diversificação de portfólio
                        t_game = None
                        for score, g in scored_candidates[1:]:
                            if len(set(g).intersection(set(s_game))) <= 12:
                                t_game = g
                                break
                        if t_game is None:
                            t_game = scored_candidates[1][1]
                            
                        # Localizar Cobertura com diversificação de portfólio
                        c_game = None
                        for score, g in scored_candidates[1:]:
                            if g == t_game:
                                continue
                            if len(set(g).intersection(set(s_game))) <= 12 and len(set(g).intersection(set(t_game))) <= 12:
                                c_game = g
                                break
                        if c_game is None:
                            for score, g in scored_candidates[1:]:
                                if g != s_game and g != t_game:
                                    c_game = g
                                    break
                                    
                        st.session_state.active_supremo = s_game
                        st.session_state.active_tendencia = t_game
                        st.session_state.active_cobertura = c_game
                        st.session_state.active_g_ten = calculate_dezena_de_ouro("Lotofácil", st.session_state.history["Lotofácil"], st.session_state.history["Lotofácil"][0])
                        st.session_state.generated_lottery = "Lotofácil"
                        st.session_state.is_special_app = False
                        
                        st.success("3 Palpites de Elite desdobrados e carregados com sucesso na Aba 🎰 Gerar Palpites!")
                        st.toast("Seus palpites de elite de alta cobertura foram gerados!", icon="🎰")
                        st.rerun()
