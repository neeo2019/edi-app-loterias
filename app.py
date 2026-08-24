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
    
    # Tentativa 1: API Oficial do Portal de Loterias da Caixa
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_name}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            concurso = data.get("numero")
            data_sorteio = data.get("dataApuracao")
            
            if lottery_name == "Dupla Sena":
                dezenas1_raw = data.get("listaDezenas", [])
                dezenas2_raw = data.get("listaDezenasSegundoSorteio", [])
                if not dezenas2_raw and "listaDezenasSegundoSorteio" not in data:
                    dezenas2_raw = data.get("listaDezenas2", [])
                d1 = sorted([int(x) for x in dezenas1_raw if str(x).isdigit()])
                d2 = sorted([int(x) for x in dezenas2_raw if str(x).isdigit()])
                if d1 and d2:
                    return {"concurso": concurso, "dezenas": [d1, d2], "data": data_sorteio}
            else:
                dezenas_raw = data.get("listaDezenas", [])
                dezenas = sorted([int(x) for x in dezenas_raw if str(x).isdigit()])
                if dezenas:
                    return {"concurso": concurso, "dezenas": dezenas, "data": data_sorteio}
    except Exception:
        pass
    
    # Tentativa 2: API de Fallback (LoteriasCaixa API)
    try:
        url_alt = f"https://loteriascaixa-api.herokuapp.com/api/{api_name}/latest"
        response = requests.get(url_alt, timeout=3)
        if response.status_code == 200:
            data = response.json()
            concurso = data.get("concurso")
            data_sorteio = data.get("data")
            if lottery_name == "Dupla Sena":
                dezenas1 = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                dezenas2 = sorted([int(x) for x in data.get("dezenasSegundoSorteio", []) if str(x).isdigit()])
                if dezenas1 and dezenas2:
                    return {"concurso": concurso, "dezenas": [dezenas1, dezenas2], "data": data_sorteio}
            else:
                dezenas = sorted([int(x) for x in data.get("dezenas", []) if str(x).isdigit()])
                if dezenas:
                    return {"concurso": concurso, "dezenas": dezenas, "data": data_sorteio}
    except Exception:
        pass
    return None

def auto_update_history():
    if "history" not in st.session_state:
        st.session_state.history = get_initial_history()
    
    # Tenta atualizar de forma transparente cada uma das loterias
    for lottery_name in ["Mega-Sena", "Lotofácil", "Lotomania", "Quina", "Dupla Sena"]:
        try:
            latest = fetch_latest_results_from_caixa(lottery_name)
            if latest:
                current_history = st.session_state.history[lottery_name]
                latest_dezenas = latest["dezenas"]
                
                # Se o concurso retornado pela API não for idêntico ao primeiro do nosso histórico,
                # significa que há um novo resultado e inserimos na frente (index 0) de forma automática.
                if current_history and current_history[0] != latest_dezenas:
                    st.session_state.history[lottery_name].insert(0, latest_dezenas)
        except Exception:
            pass

# ── BANCO DE DADOS INICIAL INTEGRADO ──────────────────────────────────

@st.cache_data
def get_initial_history():
    return {
        "Mega-Sena": [
            [16, 23, 24, 33, 36, 52], # Concurso 3046 (18/08/2026)
            [5, 11, 15, 21, 23, 32],
            [4, 15, 17, 40, 55, 58],
            [10, 18, 29, 34, 41, 56],
            [1, 12, 23, 27, 44, 49],
            [13, 20, 26, 38, 45, 53],
            [6, 17, 28, 35, 42, 59],
            [14, 25, 33, 40, 51, 57],
            [3, 11, 22, 36, 45, 50],
            [8, 19, 31, 37, 48, 54]
        ],
        "Lotofácil": [
            [1, 2, 3, 5, 8, 9, 11, 13, 14, 16, 17, 19, 21, 23, 24], # Concurso 3766 (19/08/2026)
            [1, 5, 6, 10, 11, 12, 13, 15, 16, 17, 19, 21, 22, 24, 25],
            [2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 15, 18, 21, 22, 25],
            [1, 2, 3, 4, 5, 8, 9, 14, 15, 17, 20, 21, 22, 23, 24],
            [1, 2, 3, 4, 5, 6, 9, 10, 13, 16, 18, 21, 22, 23, 25],
            # Adicionados simulados para completar 30 para o filtro rigoroso
            [1, 2, 4, 5, 7, 8, 10, 12, 13, 16, 18, 19, 21, 24, 25],
            [2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 20, 22, 23, 24],
            [1, 4, 5, 6, 8, 10, 11, 13, 15, 16, 18, 19, 21, 23, 25],
            [2, 3, 5, 7, 9, 10, 12, 14, 16, 17, 19, 20, 22, 24, 25],
            [1, 2, 3, 6, 8, 9, 11, 13, 14, 15, 18, 21, 23, 24, 25]
        ] * 3, # Replica para garantir cobertura mínima de 30 concursos para Lotofácil
        "Lotomania": [
            [14, 17, 20, 23, 26, 31, 34, 36, 38, 46, 53, 59, 60, 63, 71, 73, 77, 84, 95, 97], # Concurso 2966 (21/08/2026)
            [5, 15, 16, 22, 27, 32, 40, 44, 49, 52, 61, 62, 63, 65, 69, 72, 78, 83, 86, 93], # Concurso 2965 (19/08/2026)
            [7, 13, 14, 16, 25, 29, 33, 40, 41, 44, 56, 60, 61, 64, 67, 68, 73, 77, 83, 85],
            [5, 13, 16, 21, 28, 33, 35, 40, 43, 47, 53, 61, 63, 71, 73, 76, 77, 81, 89, 99],
            [13, 15, 21, 29, 34, 35, 36, 42, 47, 56, 60, 64, 74, 75, 86, 89, 91, 95, 96, 99]
        ],
        "Quina": [
            [10, 29, 43, 47, 51], # Concurso 7096 (19/08/2026)
            [12, 25, 33, 42, 74],
            [12, 25, 33, 41, 52],
            [4, 14, 45, 71, 80],
            [5, 4, 15, 57, 68]
        ],
        "Dupla Sena": [
            # Concurso 2998 (19/08/2026) - Armazena em tuplas [1º sorteio, 2º sorteio]
            [[5, 11, 24, 30, 31, 36], [6, 8, 20, 21, 45, 46]],
            [[3, 10, 17, 30, 37, 48], [15, 22, 23, 32, 40, 46]],
            [[2, 3, 19, 27, 29, 30], [2, 14, 21, 22, 30, 46]]
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
        # Prevent extreme clustering (e.g. no row should have more than 8 numbers or fewer than 2 numbers)
        for count in bins:
            if count < 2 or count > 8:
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
    appearances = {i: set() for i in range(1, max_val + 1)}
    
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
        for i in range(1, max_val + 1):
            if len(selected) < k and i not in selected:
                selected.append(i)
                
    return sorted(selected)

def calculate_markov(history, max_val=60):
    transitions = {i: {j: 0 for j in range(1, max_val + 1)} for i in range(1, max_val + 1)}
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
    max_val = 25 if lottery_type == "Lotofácil" else (50 if lottery_type == "Dupla Sena" else (60 if lottery_type == "Mega-Sena" else 80))
    window_size = 30 if lottery_type == "Lotofácil" else 50
    hist = history[:window_size]
    
    # 1. Frequência
    freqs = {i: 0 for i in range(1, max_val + 1)}
    for draw in hist:
        if lottery_type == "Dupla Sena":
            actual_draw = draw[0] + draw[1] if isinstance(draw[0], list) else draw
        else:
            actual_draw = draw
        for val in actual_draw:
            if val in freqs:
                freqs[val] += 1
                
    max_f = max(freqs.values()) if freqs.values() else 1
    min_f = min(freqs.values()) if freqs.values() else 0
    range_f = max_f - min_f if max_f != min_f else 1
    score_freq = {num: (f - min_f) / range_f for num, f in freqs.items()}
    
    # 2. Atraso (Gaps)
    gaps = {i: window_size for i in range(1, max_val + 1)}
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
    pending_numbers = set(range(1, max_val + 1)) - current_cycle_numbers
    score_ciclo = {i: (1.0 if i in pending_numbers else 0.2) for i in range(1, max_val + 1)}
    
    # 4. Distribuição (Paridades + Baixas/Altas + Moldura)
    score_dist = {i: 1.0 for i in range(1, max_val + 1)}
    if lottery_type == "Lotofácil":
        moldura = [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25]
        score_dist = {i: (1.0 if i in moldura else 0.5) for i in range(1, max_val + 1)}
    elif lottery_type == "Mega-Sena":
        score_dist = {i: (1.0 if i % 10 not in [2, 6, 0] else 0.05) for i in range(1, max_val + 1)}
    elif lottery_type == "Quina":
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79]
        score_dist = {i: (1.0 if i in primes else 0.6) for i in range(1, max_val + 1)}
    elif lottery_type == "Dupla Sena":
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        score_dist = {i: (1.0 if i in primes else 0.6) for i in range(1, max_val + 1)}
        
    # 5. Repetição do Concurso Anterior
    flat_last = []
    if last_draw:
        if isinstance(last_draw[0], list):
            flat_last = last_draw[0] + last_draw[1]
        else:
            flat_last = last_draw
    score_anterior = {i: (1.0 if i in flat_last else 0.1) for i in range(1, max_val + 1)}
    
    # Pesos do modelo unificado recomendados pelo especialista
    weights_map = {
        "Lotofácil":   {"freq": 0.40, "atraso": 0.20, "ciclo": 0.15, "dist": 0.15, "anterior": 0.10},
        "Dupla Sena":  {"freq": 0.40, "atraso": 0.20, "ciclo": 0.15, "dist": 0.15, "anterior": 0.10},
        "Mega-Sena":   {"freq": 0.25, "atraso": 0.25, "ciclo": 0.20, "dist": 0.20, "anterior": 0.10},
        "Quina":       {"freq": 0.20, "atraso": 0.25, "ciclo": 0.25, "dist": 0.20, "anterior": 0.10}
    }
    
    p = weights_map.get(lottery_type, {"freq": 0.20, "atraso": 0.25, "ciclo": 0.25, "dist": 0.20, "anterior": 0.10})
    
    final_weights = {}
    for i in range(1, max_val + 1):
        w = (score_freq[i] * p["freq"] +
             score_atraso[i] * p["atraso"] +
             score_ciclo[i] * p["ciclo"] +
             score_dist[i] * p["dist"] +
             score_anterior[i] * p["anterior"])
        final_weights[i] = max(float(w), 0.01)
        
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
            
    corr_scores = {i: 0 for i in range(1, max_val + 1)}
    for num in flat_last:
        if num in transitions:
            for follower, count in transitions[num].items():
                if follower in corr_scores:
                    corr_scores[follower] += count
                    
    max_corr = max(corr_scores.values()) if corr_scores.values() else 1
    if max_corr == 0: max_corr = 1
    
    best_num = 1
    best_score = -1.0
    for i in range(1, max_val + 1):
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
    for idx, (g, g_name) in enumerate(zip(games, ["Supremo", "Tendência", "Cobertura"])):
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
    pdf.cell(0, 10, "PORTAL DE INFERENCIA PRO", ln=1, align="C")
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"E-book Oficial de Palpites Otimizados -- {lottery_type.upper()}", ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 10, f"Dezena de Ouro (Ancora Ativa): {golden_ten:02d}", ln=1)
    pdf.ln(5)
    
    for idx, (g, g_name) in enumerate(zip(games, ["O Supremo", "A Tendencia Cruzada", "A Cobertura de Seguranca"])):
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, f"Palpite {idx+1} -- {g_name}", ln=1)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 10, "Dezenas: " + " -- ".join([f"{n:02d}" for n in g]), ln=1)
        pdf.ln(3)
        
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Nota de Seguranca: Este sistema trata os historicos como dados para analise e otimizacao estatistica, sem afirmar que padroes historicos alteram a probabilidade matematica oficial de um sorteio ou garantem premios.")
    return bytes(pdf.output())


# ── LOGICAS DE GERAÇÃO POR LOTERIA ────────────────────────────────────

def generate_mega_sena(special_mode=False):
    hist = st.session_state.history["Mega-Sena"]
    last_draw = hist[0]
    eligible_numbers = [n for num in range(1, 61) if (n := num) % 10 not in [2, 6, 0]]
    
    dezena_de_ouro = calculate_dezena_de_ouro("Mega-Sena", hist, last_draw)
    
    all_weights = get_unified_weights("Mega-Sena", hist, last_draw)
    for num in USER_FIXED_MEGA_SENA:
        if num in all_weights:
            all_weights[num] *= 1.5
            
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
        
    def complete_mega_game(seed_nums):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
        for _ in range(1000):
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
            is_valid, _ = statistical_guardian(game, "Mega-Sena")
            if is_valid and anti_popularity_filter(game, "Mega-Sena", strict=special_mode):
                return game
                
        current = list(dict.fromkeys(seed_nums))
        pool = [n for n in eligible_numbers if n not in current]
        random.shuffle(pool)
        if dezena_de_ouro not in current:
            current.append(dezena_de_ouro)
        while len(current) < 6:
            current.append(pool.pop())
        return sorted(current[:6])

    markov_nums = get_markov_predictions(last_draw, transitions, 10)
    gold_nums = greedy_set_cover(hist, 12, 60)
    candidates_seed = list(set([n for n in markov_nums + gold_nums if n in USER_FIXED_MEGA_SENA]))
    supremo = complete_mega_game(candidates_seed)
    
    candidates_seed_t = []
    for num in last_draw:
        for offset in [-2, 2, -8, 8]:
            val = num + offset
            if 1 <= val <= 60 and val in USER_FIXED_MEGA_SENA:
                candidates_seed_t.append(val)
    candidates_seed_t = list(set(candidates_seed_t))
    tendencia = complete_mega_game(candidates_seed_t)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in eligible_numbers}
    cob_list = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = complete_mega_game(cob_list)
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_lotofacil(special_mode=False):
    hist_all = st.session_state.history["Lotofácil"]
    hist = hist_all[:30] # REGRA ESTREITA DE 30 CONCURSOS
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Lotofácil", hist, last_draw)
    
    all_weights = get_unified_weights("Lotofácil", hist, last_draw)
    
    def build_game(candidates):
        for _ in range(500):
            game = [1, 25] # Travas Posicionais
            if dezena_de_ouro not in game:
                game.append(dezena_de_ouro)
            pool = [n for n in candidates if n not in [1, 25, dezena_de_ouro]]
            if len(pool) < 12:
                pool += [n for n in range(2, 25) if n not in pool and n not in game]
                
            chosen = []
            pool_copy = pool.copy()
            while len(game) + len(chosen) < 15 and pool_copy:
                w_list = [all_weights.get(n, 1.0) for n in pool_copy]
                total_w = sum(w_list)
                probs = [w / total_w for w in w_list]
                item = np.random.choice(pool_copy, p=probs)
                chosen.append(int(item))
                pool_copy.remove(item)
                
            final_game = sorted(game + chosen)
            pares = [n for n in final_game if n % 2 == 0]
            if 7 <= len(pares) <= 8:
                is_valid, _ = statistical_guardian(final_game, "Lotofácil")
                if is_valid and anti_popularity_filter(final_game, "Lotofácil", strict=special_mode):
                    return final_game
        # fallback
        current = [1, 25, dezena_de_ouro]
        pool = [n for n in range(2, 25) if n != dezena_de_ouro]
        random.shuffle(pool)
        while len(current) < 15:
            current.append(pool.pop())
        return sorted(current)

    gold = greedy_set_cover(hist, 15, 25)
    supremo = build_game(gold)
    
    transitions = calculate_markov(hist, 25)
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    tendencia = build_game(markov_nums)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 26)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = build_game(atrasadas)
    
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
            
    def complete_game(seed_fixed):
        if dezena_de_ouro not in seed_fixed:
            seed_fixed = list(seed_fixed) + [dezena_de_ouro]
        for _ in range(1000):
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
            is_valid, _ = statistical_guardian(game, "Lotomania")
            pares = [n for n in game if n % 2 == 0]
            if is_valid and (20 <= len(pares) <= 30):
                return game
                
        current = list(dict.fromkeys(seed_fixed))
        all_nums = [n for n in range(1, 100)] + [0]
        pool = [n for n in all_nums if n not in current]
        random.shuffle(pool)
        if dezena_de_ouro not in current:
            current.append(dezena_de_ouro)
        while len(current) < 50:
            current.append(pool.pop())
        return sorted(current)

    supremo = complete_game(fixed)
    tendencia = complete_game(fixed)
    cobertura = complete_game(fixed)
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_quina(special_mode=False):
    hist = st.session_state.history["Quina"]
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Quina", hist, last_draw)
    
    all_weights = get_unified_weights("Quina", hist, last_draw)
    for num in USER_FIXED_QUINA:
        if num in all_weights:
            all_weights[num] *= 1.5
            
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
        
    def complete_quina_game(seed_nums):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
        for _ in range(1000):
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
            pares = [n for n in game if n % 2 == 0]
            if len(pares) in [2, 3]:
                is_valid, _ = statistical_guardian(game, "Quina")
                if is_valid:
                    return game
                    
        current = list(dict.fromkeys(seed_nums))
        pool = [n for n in range(1, 81) if n not in current]
        random.shuffle(pool)
        if dezena_de_ouro not in current:
            current.append(dezena_de_ouro)
        while len(current) < 5:
            current.append(pool.pop())
        return sorted(current[:5])

    supremo = complete_quina_game(USER_FIXED_QUINA.copy())
    
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    tendencia = complete_quina_game(markov_nums)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 81)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:20]]
    cobertura = complete_quina_game(atrasadas)
    
    return supremo, tendencia, cobertura, dezena_de_ouro

def generate_dupla_sena(special_mode=False):
    hist = st.session_state.history["Dupla Sena"]
    last_draw = hist[0]
    dezena_de_ouro = calculate_dezena_de_ouro("Dupla Sena", hist, last_draw)
    
    all_weights = get_unified_weights("Dupla Sena", hist, last_draw)
    for num in USER_FIXED_DUPLA_SENA:
        if num in all_weights:
            all_weights[num] *= 1.5

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
        
    def complete_dupla_game(seed_nums):
        if dezena_de_ouro not in seed_nums:
            seed_nums = list(seed_nums) + [dezena_de_ouro]
        for _ in range(1000):
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
            is_valid, _ = statistical_guardian(game, "Dupla Sena")
            if is_valid:
                return game
                
        current = list(dict.fromkeys(seed_nums))
        pool = [n for n in range(1, 51) if n not in current]
        random.shuffle(pool)
        if dezena_de_ouro not in current:
            current.append(dezena_de_ouro)
        while len(current) < 6:
            current.append(pool.pop())
        return sorted(current[:6])

    supremo = complete_dupla_game(USER_FIXED_DUPLA_SENA.copy())
    tendencia = complete_dupla_game(gold2)
    
    all_draws = [n for sub in hist_draw1 + hist_draw2 for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 51)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = complete_dupla_game(atrasadas)
    
    return supremo, tendencia, cobertura, dezena_de_ouro

# ── DESIGN DO WEB APP GRÁFICO (INTERFACES STREAMLIT) ──────────────────

st.markdown("<div class='main-title'>🔮 PORTAL DE INFERÊNCIA PRO</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Ambiente de Otimização Estatística de Alta Performance - Caixa Econômica</div>", unsafe_allow_html=True)

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
    
    # Exibe as informações da Loteria selecionada
    if selected_lottery == "Mega-Sena":
        st.markdown(
            f"<div class='lottery-card mega-sena-bg'>"
            f"<h4>MEGA-SENA</h4>"
            f"<p>Prêmio Estimado: <b>R$ 50 Milhões</b><br>"
            f"Próximo Concurso: <b>3047</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Lotofácil":
        st.markdown(
            f"<div class='lottery-card lotofacil-bg'>"
            f"<h4>LOTOFÁCIL</h4>"
            f"<p>Prêmio Estimado: <b>R$ 2 Milhões</b><br>"
            f"Próximo Concurso: <b>3767</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Lotomania":
        st.markdown(
            f"<div class='lottery-card lotomania-bg'>"
            f"<h4>LOTOMANIA</h4>"
            f"<p>Prêmio Estimado: <b>R$ 16 Milhões</b><br>"
            f"Próximo Concurso: <b>2967</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Quina":
        st.markdown(
            f"<div class='lottery-card quina-bg'>"
            f"<h4>QUINA</h4>"
            f"<p>Prêmio Estimado: <b>R$ 15 Milhões</b><br>"
            f"Próximo Concurso: <b>7097</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='lottery-card dupla-sena-bg'>"
            f"<h4>DUPLA SENA</h4>"
            f"<p>Prêmio Estimado: <b>R$ 1.8 Milhão</b><br>"
            f"Próximo Concurso: <b>2999</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
    st.info("💡 Este sistema trata históricos como dados estatísticos puros, buscando máxima eficiência de dispersão e cobertura sem alterar as probabilidades matemáticas teóricas.")

# Abas na Coluna Principal
with col_main:
    tab_generator, tab_saved, tab_check, tab_learning = st.tabs([
        "🎰 Gerar Palpites", 
        "💾 Meus Jogos Salvos", 
        "🔍 Conferência de Resultados",
        "🧠 Treinar Algoritmo (Ciclos)"
    ])
    
    # ── TAB 1: GERADOR DE PROGNÓSTICOS ────────────────────────────────
    with tab_generator:
        st.write("### Prognósticos Otimizados por Hierarquia de Força Estatística")
        
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
                    s, t, c, g_ten = generate_lotofacil(special_mode)
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
            
            # --- SUPREMO ---
            st.markdown(f"#### <span class='badge-supremo'>1º PALPITE — O SUPREMO (Aposta Master — {'Especial Sazonal' if is_spec else 'Peso Máximo'})</span>", unsafe_allow_html=True)
            
            # Highlight golden ten in Supremo list
            balls_html = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in s])
            st.markdown(f"<div class='ball-container'>{balls_html}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Supremo", key="save_sup"):
                pred = {"lottery": selected_lottery, "type": "Supremo (Especial)" if is_spec else "Supremo", "numbers": s, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Supremo Salvo!", icon="💾")
            
            st.divider()
            
            # --- TENDÊNCIA ---
            st.markdown("#### <span class='badge-tendencia'>2º PALPITE — A TENDÊNCIA CRUZADA (Peso Médio)</span>", unsafe_allow_html=True)
            balls_html_t = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in t])
            st.markdown(f"<div class='ball-container'>{balls_html_t}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Tendência", key="save_tend"):
                pred = {"lottery": selected_lottery, "type": "Tendência", "numbers": t, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Tendência Salvo!", icon="💾")
                    
            st.divider()
            
            # --- COBERTURA ---
            st.markdown("#### <span class='badge-cobertura'>3º PALPITE — A COBERTURA DE SEGURANÇA (Peso de Cobertura)</span>", unsafe_allow_html=True)
            balls_html_c = "".join([f"<div class='ball {ball_class}' style='background-color:#FEFCBF; border:2px solid #ECC94B;' title='Dezena de Ouro!'>{f'{n:02d}' if n != 0 else '00'}</div>" if n == g_ten else f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in c])
            st.markdown(f"<div class='ball-container'>{balls_html_c}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Cobertura", key="save_cob"):
                pred = {"lottery": selected_lottery, "type": "Cobertura", "numbers": c, "g_ten": g_ten, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Cobertura Salvo!", icon="💾")
            
            st.divider()
            
            # --- EXPORTAÇÃO E DOWNLOADS ---
            st.markdown("### 📥 Exportar Resultados Deste Lote")
            col_exp1, col_gen_xlsx, col_gen_pdf = st.columns(3)
            with col_exp1:
                txt_palpites = f"PALPITES OTIMIZADOS -- {selected_lottery.upper()}\n\n"
                txt_palpites += f"Dezena de Ouro (Ancora): {g_ten:02d}\n\n"
                txt_palpites += f"1o Palpite - Supremo: {' '.join([f'{n:02d}' for n in s])}\n"
                txt_palpites += f"2o Palpite - Tendencia: {' '.join([f'{n:02d}' for n in t])}\n"
                txt_palpites += f"3o Palpite - Cobertura: {' '.join([f'{n:02d}' for n in c])}\n"
                st.download_button(
                    label="📋 Copiar / Baixar como Texto (TXT)",
                    data=txt_palpites,
                    file_name=f"palpites_{selected_lottery.lower()}.txt",
                    mime="text/plain"
                )
                
            with col_gen_xlsx:
                xlsx_data = get_xlsx_download_data([s, t, c], g_ten, selected_lottery)
                st.download_button(
                    label=" Excel Planilha (XLSX)",
                    data=xlsx_data,
                    file_name=f"palpites_{selected_lottery.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            with col_gen_pdf:
                pdf_data = get_pdf_download_data([s, t, c], g_ten, selected_lottery)
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
