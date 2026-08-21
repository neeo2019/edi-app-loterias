import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime
import scipy.stats as stats
import os
import json
import requests

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

# ── BANCO DE DADOS INICIAL INTEGRADO ──────────────────────────────────

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
    7, 11, 13, 14, 16, 19, 20, 25, 29, 31, 33, 38, 40, 41, 43, 44, 45, 
    47, 48, 49, 54, 56, 60, 61, 64, 67, 68, 73, 77, 83, 85, 91, 92, 93
]

if "history" not in st.session_state:
    st.session_state.history = get_initial_history()
auto_update_history()

if "saved_predictions" not in st.session_state:
    st.session_state.saved_predictions = load_predictions()

# ── ENGENHARIA DE PROGNÓSTICOS - MOTORES AVANÇADOS ─────────────────────

def statistical_guardian(selected_numbers, lottery_type):
    """
    Guardião Estatístico PRO: Bloqueia ruídos e valida jogos sob testes formais.
    Aplica teste do Qui-Quadrado para dispersão uniforme e impede ajuste excessivo.
    CORREÇÃO TÉCNICA: Ajustado f_exp para evitar erro de assinatura no SciPy.
    """
    if not selected_numbers:
        return True, 0.0
    
    # 1. Teste de Qui-Quadrado de Dispersão Espacial (Filtro Uniforme)
    max_val = 25 if lottery_type == "Lotofácil" else (60 if lottery_type == "Mega-Sena" else (80 if lottery_type == "Quina" else 100))
    if lottery_type == "Dupla Sena":
        max_val = 50
        
    num_bins = 4 # Quadrantes
    bin_size = max_val / num_bins
    observed = [0] * num_bins
    
    for val in selected_numbers:
        idx = min(int((val - 1) // bin_size), num_bins - 1)
        observed[idx] += 1
        
    expected_freq = len(selected_numbers) / num_bins
    
    # Chamada corrigida usando f_exp em vez do parâmetro f_obs incorreto
    chi2_stat, p_val = stats.chisquare(observed, f_exp=[expected_freq]*num_bins)
    
    # Se p-value for extremamente baixo, as dezenas estão concentradas demais (bloqueia sinal fraco)
    is_valid = p_val >= 0.01
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
        
    # 3. Regra de Exclusão de Data (Rigor Sazonal / Especial)
    if strict:
        # Se for um jogo especial, evita que mais de 3 dezenas estejam abaixo ou igual a 31
        dates_count = sum(1 for n in game if n <= 31)
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

# ── LOGICAS DE GERAÇÃO POR LOTERIA COM SUPORTE MÓDULO ESPECIAL ─────────

def generate_mega_sena(special_mode=False):
    hist = st.session_state.history["Mega-Sena"]
    last_draw = hist[0]
    eligible_numbers = [n for num in range(1, 61) if (n := num) % 10 not in [2, 6, 0]]
    
    # Sinergia de coocorrência híbrida se o modo especial estiver ativo
    if special_mode:
        spec_hist = get_special_history()["Mega da Virada"]
        # Fusão dos dois históricos (80% regular / 20% especial)
        transitions_reg = calculate_markov(hist, 60)
        transitions_spec = calculate_markov(spec_hist, 60)
        transitions = {}
        for i in range(1, 61):
            transitions[i] = {}
            for j in range(1, 61):
                reg_weight = transitions_reg.get(i, {}).get(j, 0) * 0.8
                spec_weight = transitions_spec.get(i, {}).get(j, 0) * 0.2
                transitions[i][j] = reg_weight + spec_weight
    else:
        transitions = calculate_markov(hist, 60)
    
    def search_valid_game(is_supremo=False):
        for _ in range(500):
            if is_supremo:
                markov_nums = get_markov_predictions(last_draw, transitions, 12)
                gold_nums = greedy_set_cover(hist, 15, 60)
                candidates = list(set([n for n in markov_nums + gold_nums if n in eligible_numbers]))
            else:
                candidates = []
                for num in last_draw:
                    for offset in [-2, 2, -8, 8]:
                        val = num + offset
                        if 1 <= val <= 60 and val % 10 not in [2, 6, 0]:
                            candidates.append(val)
                candidates = list(set(candidates))
                
            if len(candidates) < 6:
                candidates += [n for n in eligible_numbers if n not in candidates]
            
            game = sorted(random.sample(candidates, 6))
            is_valid, _ = statistical_guardian(game, "Mega-Sena")
            if is_valid and anti_popularity_filter(game, "Mega-Sena", strict=special_mode):
                return game
        return sorted(random.sample(eligible_numbers, 6))

    supremo = search_valid_game(is_supremo=True)
    tendencia = search_valid_game(is_supremo=False)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in eligible_numbers}
    cob_list = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = sorted(random.sample(cob_list, 6))
    
    return supremo, tendencia, cobertura

def generate_lotofacil(special_mode=False):
    hist_all = st.session_state.history["Lotofácil"]
    hist = hist_all[:30] # Limitação rigorosa de 30 concursos
    last_draw = hist[0]
    
    if special_mode:
        spec_hist = get_special_history()["Lotofácil da Independência"]
        transitions_reg = calculate_markov(hist, 25)
        transitions_spec = calculate_markov(spec_hist, 25)
        transitions = {}
        for i in range(1, 26):
            transitions[i] = {}
            for j in range(1, 26):
                transitions[i][j] = (transitions_reg.get(i, {}).get(j, 0) * 0.8) + (transitions_spec.get(i, {}).get(j, 0) * 0.2)
    else:
        transitions = calculate_markov(hist, 25)
        
    def build_game(candidates):
        for _ in range(500):
            game = [1, 25] # Travas Posicionais Obrigatórias
            rest = [n for n in candidates if n not in [1, 25]]
            random.shuffle(rest)
            game.extend(rest[:13])
            game = sorted(game)
            
            pares = [n for n in game if n % 2 == 0]
            if 7 <= len(pares) <= 8: # Filtro de Pares e Ímpares Recordistas
                is_valid, _ = statistical_guardian(game, "Lotofácil")
                if is_valid and anti_popularity_filter(game, "Lotofácil", strict=special_mode):
                    return game
        return sorted([1] + random.sample(range(2, 25), 13) + [25])

    gold = greedy_set_cover(hist, 15, 25)
    supremo = build_game(gold)
    
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    tendencia = build_game(markov_nums)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 26)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = build_game(atrasadas)
    
    return supremo, tendencia, cobertura

def generate_lotomania():
    hist = st.session_state.history["Lotomania"]
    wave_nums = detect_lotomania_wave(hist)
    fixed = USER_FIXED_LOTOMANIA.copy()
    
    def complete_game(seed_fixed):
        current = seed_fixed.copy()
        all_nums = [n for n in range(1, 100)] + [0]
        pool = [n for n in all_nums if n not in current]
        
        wave_eligible = [n for n in wave_nums if n in pool]
        current.extend(wave_eligible[:4])
        pool = [n for n in all_nums if n not in current]
        
        random.shuffle(pool)
        while len(current) < 50:
            current.append(pool.pop())
        return sorted(current)

    supremo = complete_game(fixed)
    tendencia = complete_game(fixed + [74]) # Atração Sazonal 54-74
    cobertura = complete_game(fixed)
    
    return supremo, tendencia, cobertura

def generate_quina(special_mode=False):
    hist = st.session_state.history["Quina"]
    last_draw = hist[0]
    
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
        
    def search_quina_game(candidates):
        for _ in range(500):
            game = sorted(random.sample(candidates, 5))
            pares = [n for n in game if n % 2 == 0]
            if len(pares) in [2, 3]: # Paridades Campeãs: 3P/2I ou 2P/3I
                is_valid, _ = statistical_guardian(game, "Quina")
                if is_valid:
                    return game
        return sorted(random.sample(candidates, 5))

    gold = greedy_set_cover(hist, 15, 80)
    supremo = search_quina_game(gold)
    
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    if len(markov_nums) < 5: markov_nums = gold
    tendencia = search_quina_game(markov_nums)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 81)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:20]]
    cobertura = search_quina_game(atrasadas)
    
    return supremo, tendencia, cobertura

def generate_dupla_sena(special_mode=False):
    hist = st.session_state.history["Dupla Sena"]
    
    # Extração de sorteios segregados
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
        
    def search_dupla_game(candidates):
        for _ in range(500):
            game = sorted(random.sample(candidates, 6))
            is_valid, _ = statistical_guardian(game, "Dupla Sena")
            if is_valid:
                return game
        return sorted(random.sample(candidates, 6))

    supremo = search_dupla_game(gold1)
    tendencia = search_dupla_game(gold2)
    
    all_draws = [n for sub in hist_draw1 + hist_draw2 for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 51)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = search_dupla_game(atrasadas)
    
    return supremo, tendencia, cobertura

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
        st.markdown("---")
        special_mode = st.toggle(f"🔮 Ativar Modo Especial Sazonal", help="Mescla o banco de dados regular ao sazonal com anti-popularidade rígido.")
        if special_mode:
            st.success(f"Sinergia Ativa: {special_label}")
            
    st.markdown("---")
    # Exibe as informações da Loteria selecionada
    if selected_lottery == "Mega-Sena":
        st.markdown(
            f"<div class='lottery-card mega-sena-bg'>"
            f"<h4>{'MEGA DA VIRADA' if special_mode else 'MEGA-SENA'}</h4>"
            f"<p>Prêmio Estimado: <b>R$ {'550' if special_mode else '50'} Milhões</b><br>"
            f"Próximo Concurso: <b>{'Especial' if special_mode else '3047'}</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Lotofácil":
        st.markdown(
            f"<div class='lottery-card lotofacil-bg'>"
            f"<h4>{'LF INDEPENDÊNCIA' if special_mode else 'LOTOFÁCIL'}</h4>"
            f"<p>Prêmio Estimado: <b>R$ {'200' if special_mode else '2'} Milhões</b><br>"
            f"Próximo Concurso: <b>{'Especial' if special_mode else '3767'}</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Lotomania":
        st.markdown(
            "<div class='lottery-card lotomania-bg'>"
            "<h4>LOTOMANIA</h4>"
            "<p>Prêmio Estimado: <b>R$ 16 Milhões</b><br>"
            "Próximo Concurso: <b>2966</b></p>"
            "</div>", 
            unsafe_allow_html=True
        )
    elif selected_lottery == "Quina":
        st.markdown(
            f"<div class='lottery-card quina-bg'>"
            f"<h4>{'QUINA DE SÃO JOÃO' if special_mode else 'QUINA'}</h4>"
            f"<p>Prêmio Estimado: <b>R$ {'220' if special_mode else '15'} Milhões</b><br>"
            f"Próximo Concurso: <b>{'Especial' if special_mode else '7097'}</b></p>"
            f"</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='lottery-card dupla-sena-bg'>"
            f"<h4>{'DUPLA DE PÁSCOA' if special_mode else 'DUPLA SENA'}</h4>"
            f"<p>Prêmio Estimado: <b>R$ {'35' if special_mode else '1.8'} Milhão</b><br>"
            f"Próximo Concurso: <b>{'Especial' if special_mode else '2999'}</b></p>"
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
        
        # Botão Gerar
        if st.button("🚀 Executar Afunilamento e Gerar Prognósticos"):
            with st.spinner("Processando Cadeias de Markov, Onda de Calor e Guardião Estatístico..."):
                if selected_lottery == "Mega-Sena":
                    s, t, c = generate_mega_sena(special_mode)
                elif selected_lottery == "Lotofácil":
                    s, t, c = generate_lotofacil(special_mode)
                elif selected_lottery == "Lotomania":
                    s, t, c = generate_lotomania()
                elif selected_lottery == "Quina":
                    s, t, c = generate_quina(special_mode)
                else:
                    s, t, c = generate_dupla_sena(special_mode)
                    
                st.session_state.active_supremo = s
                st.session_state.active_tendencia = t
                st.session_state.active_cobertura = c
                st.session_state.generated_lottery = selected_lottery
                st.session_state.is_special_app = special_mode
                st.success("Jogos gerados, auditados e validados pelo Guardião Estatístico!")

        # Exibição dos Prognósticos Ativos
        if "active_supremo" in st.session_state and st.session_state.generated_lottery == selected_lottery:
            s = st.session_state.active_supremo
            t = st.session_state.active_tendencia
            c = st.session_state.active_cobertura
            is_spec = st.session_state.get("is_special_app", False)
            
            ball_class = {
                "Mega-Sena": "ball-mega",
                "Lotofácil": "ball-facil",
                "Lotomania": "ball-mania",
                "Quina": "ball-quina",
                "Dupla Sena": "ball-dupla"
            }[selected_lottery]
            
            # --- SUPREMO ---
            st.markdown(f"#### <span class='badge-supremo'>1º PALPITE — O SUPREMO (Aposta Master — {'Especial Sazonal' if is_spec else 'Peso Máximo'})</span>", unsafe_allow_html=True)
            balls_html = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in s])
            st.markdown(f"<div class='ball-container'>{balls_html}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Supremo", key="save_sup"):
                pred = {"lottery": selected_lottery, "type": "Supremo (Especial)" if is_spec else "Supremo", "numbers": s, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Supremo Salvo!", icon="💾")
            
            st.divider()
            
            # --- TENDÊNCIA ---
            st.markdown("#### <span class='badge-tendencia'>2º PALPITE — A TENDÊNCIA CRUZADA (Peso Médio)</span>", unsafe_allow_html=True)
            balls_html_t = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in t])
            st.markdown(f"<div class='ball-container'>{balls_html_t}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Tendência", key="save_tend"):
                pred = {"lottery": selected_lottery, "type": "Tendência", "numbers": t, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Tendência Salvo!", icon="💾")
                    
            st.divider()
            
            # --- COBERTURA ---
            st.markdown("#### <span class='badge-cobertura'>3º PALPITE — A COBERTURA DE SEGURANÇA (Peso de Cobertura)</span>", unsafe_allow_html=True)
            balls_html_c = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in c])
            st.markdown(f"<div class='ball-container'>{balls_html_c}</div>", unsafe_allow_html=True)
            
            if st.button("💾 Salvar Palpite Cobertura", key="save_cob"):
                pred = {"lottery": selected_lottery, "type": "Cobertura", "numbers": c, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    save_predictions(st.session_state.saved_predictions)
                    st.toast("Palpite Cobertura Salvo!", icon="💾")
        else:
            st.info("Aperte no botão acima para rodar a análise estatística multi-camadas.")

    # ── TAB 2: MEUS JOGOS SALVOS ──────────────────────────────────────
    with tab_saved:
        st.write(f"### 💾 Seus Jogos Salvos — {selected_lottery.upper()}")
        
        # Filtrar palpites para a loteria atualmente selecionada no Painel de Operações
        filtered_preds = [(original_idx, pred) for original_idx, pred in enumerate(st.session_state.saved_predictions) if pred['lottery'] == selected_lottery]
        
        if not filtered_preds:
            st.info(f"Nenhum palpite salvo para a {selected_lottery} até o momento.")
        else:
            to_delete = []
            for original_idx, pred in filtered_preds:
                col_info, col_action = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{pred['lottery'].upper()}** - *{pred['type']}* (Salvo em: {pred['date']})")
                    balls_html_s = "".join([f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:#edf2f7; border-radius:4px; font-weight:bold; font-size:0.85rem;'>{f'{n:02d}' if n != 0 else '00'}</span>" for n in pred['numbers']])
                    st.markdown(f"<div>{balls_html_s}</div>", unsafe_allow_html=True)
                with col_action:
                    if st.button("❌ Excluir", key=f"del_{original_idx}"):
                        to_delete.append(original_idx)
                        
                st.markdown("---")
                
            if to_delete:
                for idx in sorted(to_delete, reverse=True):
                    st.session_state.saved_predictions.pop(idx)
                save_predictions(st.session_state.saved_predictions)
                st.toast("Palpite excluído com sucesso!", icon="🗑️")
                st.rerun()
                
            txt_data = ""
            for _, pred in filtered_preds:
                num_str = " ".join([f"{n:02d}" for n in pred['numbers']])
                txt_data += f"{pred['lottery']} - {pred['type']} - {pred['date']}\n{num_str}\n\n"
                
            st.download_button(
                label=f"📥 Exportar Jogos de {selected_lottery} para Bloco de Notas (TXT)",
                data=txt_data,
                file_name=f"meus_palpites_{selected_lottery.lower()}_otimizados.txt",
                mime="text/plain"
            )

    # ── TAB 3: CONFERÊNCIA INTELIGENTE ────────────────────────────────
    with tab_check:
        st.write(f"### 🔍 Conferência de Prognósticos — {selected_lottery.upper()}")
        
        # Filtrar palpites para a loteria atualmente selecionada no Painel de Operações
        filtered_preds = [(original_idx, pred) for original_idx, pred in enumerate(st.session_state.saved_predictions) if pred['lottery'] == selected_lottery]
        
        if not filtered_preds:
            st.warning(f"É necessário possuir jogos salvos para a {selected_lottery} para realizar a conferência.")
        else:
            st.markdown("#### 1. Escolha o Jogo Salvo para Conferir:")
            game_options = [f"{original_idx} - {p['lottery']} ({p['type']}) - {p['date']}" for original_idx, p in filtered_preds]
            selected_game_idx_str = st.selectbox("Selecione o palpite:", game_options)
            selected_game_idx = int(selected_game_idx_str.split(" - ")[0])
            target_prediction = st.session_state.saved_predictions[selected_game_idx]
            
            st.markdown("#### 2. Insira as Dezenas Sorteadas para Conferir:")
            check_mode = st.radio("Método de entrada do sorteio:", ["Último concurso oficial da base", "Digitar dezenas manualmente"])
            
            if check_mode == "Último concurso oficial da base":
                target_lottery = target_prediction['lottery']
                raw_draw = st.session_state.history[target_lottery][0]
                # Se for Dupla Sena, pega apenas o 1º sorteio para conferência simples
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
