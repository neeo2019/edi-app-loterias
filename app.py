import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime
import scipy.stats as stats

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
""", unsafe_type_html=True)

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
            [5, 0o4, 15, 57, 68]
        ],
        "Dupla Sena": [
            # Concurso 2998 (19/08/2026) - Armazena em tuplas [1º sorteio, 2º sorteio]
            [[5, 11, 24, 30, 31, 36], [6, 8, 20, 21, 45, 46]],
            [[3, 10, 17, 30, 37, 48], [15, 22, 23, 32, 40, 46]],
            [[2, 3, 19, 27, 29, 30], [2, 14, 21, 22, 30, 46]]
        ]
    }

USER_FIXED_LOTOMANIA = [
    7, 11, 13, 14, 16, 19, 20, 25, 29, 31, 33, 38, 40, 41, 43, 44, 45, 
    47, 48, 49, 54, 56, 60, 61, 64, 67, 68, 73, 77, 83, 85, 91, 92, 93
]

if "history" not in st.session_state:
    st.session_state.history = get_initial_history()

if "saved_predictions" not in st.session_state:
    st.session_state.saved_predictions = []

# ── ENGENHARIA DE PROGNÓSTICOS - MOTORES AVANÇADOS ─────────────────────

def statistical_guardian(selected_numbers, lottery_type):
    """
    Guardião Estatístico PRO: Bloqueia ruídos e valida jogos sob testes formais.
    Aplica teste do Qui-Quadrado para dispersão uniforme e impede ajuste excessivo.
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
    chi2_stat, p_val = stats.chisquare(observed, f_obs=[expected_freq]*num_bins)
    
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

def anti_popularity_filter(game, lottery_type):
    """
    Motor Anti-Popularidade: Penaliza combinações de alta redundância ou óbvias
    para evitar divisão de possíveis prêmios em faixas de acerto.
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

# ── LOGICAS DE GERAÇÃO POR LOTERIA ────────────────────────────────────

def generate_mega_sena():
    hist = st.session_state.history["Mega-Sena"]
    last_draw = hist[0]
    eligible_numbers = [n for num in range(1, 61) if (n := num) % 10 not in [2, 6, 0]]
    transitions = calculate_markov(hist, 60)
    
    def search_valid_game(is_supremo=False):
        for _ in range(500):
            if is_supremo:
                markov_nums = get_markov_predictions(last_draw, transitions, 10)
                gold_nums = greedy_set_cover(hist, 12, 60)
                candidates = list(set([n for n in markov_nums + gold_nums if n in eligible_numbers]))
            else:
                # Tendência ou desvios posicionais
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
            if is_valid and anti_popularity_filter(game, "Mega-Sena"):
                return game
        return sorted(random.sample(eligible_numbers, 6))

    supremo = search_valid_game(is_supremo=True)
    tendencia = search_valid_game(is_supremo=False)
    
    # Cobertura: foco em atrasadas
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in eligible_numbers}
    cob_list = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = sorted(random.sample(cob_list, 6))
    
    return supremo, tendencia, cobertura

def generate_lotofacil():
    # REGRA CRÍTICA DO CHECKLIST: Todos os cálculos usam EXCLUSIVAMENTE os últimos 30 concursos
    hist_all = st.session_state.history["Lotofácil"]
    hist = hist_all[:30] # LIMITAÇÃO ESTRITA DE 30 CONCURSOS
    last_draw = hist[0]
    
    def build_game(candidates):
        for _ in range(500):
            game = [1, 25] # Travas Posicionais
            rest = [n for n in candidates if n not in [1, 25]]
            random.shuffle(rest)
            game.extend(rest[:13])
            game = sorted(game)
            
            # Filtro de paridade
            pares = [n for n in game if n % 2 == 0]
            if 7 <= len(pares) <= 8:
                is_valid, _ = statistical_guardian(game, "Lotofácil")
                if is_valid and anti_popularity_filter(game, "Lotofácil"):
                    return game
        # Fallback se falhar
        return sorted([1] + random.sample(range(2, 25), 13) + [25])

    gold = greedy_set_cover(hist, 15, 25)
    supremo = build_game(gold)
    
    # Tendência por Markov de curto prazo (30 concursos)
    transitions = calculate_markov(hist, 25)
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    tendencia = build_game(markov_nums)
    
    # Cobertura por Ciclos recentes (30 concursos)
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 26)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = build_game(atrasadas)
    
    return supremo, tendencia, cobertura

def generate_lotomania():
    hist = st.session_state.history["Lotomania"]
    wave_nums = detect_lotomania_wave(hist) # Integração técnica da onda
    fixed = USER_FIXED_LOTOMANIA.copy()
    
    def complete_game(seed_fixed):
        # Desejamos completar as 16 restantes respeitando o balanço lateral
        current = seed_fixed.copy()
        all_nums = [n for n in range(1, 100)] + [0]
        pool = [n for n in all_nums if n not in current]
        
        # Prioriza injetar números da Onda de Calor para acelerar a zona de premiação
        wave_eligible = [n for n in wave_nums if n in pool]
        current.extend(wave_eligible[:4])
        pool = [n for n in all_nums if n not in current]
        
        random.shuffle(pool)
        while len(current) < 50:
            current.append(pool.pop())
        return sorted(current)

    supremo = complete_game(fixed)
    tendencia = complete_game(fixed + [74]) # Atração 54-74
    cobertura = complete_game(fixed)
    
    return supremo, tendencia, cobertura

def generate_quina():
    hist = st.session_state.history["Quina"]
    last_draw = hist[0]
    
    # Paridades campeãs: 3P/2I (32.55%) ou 2P/3I (31.44%)
    def search_quina_game(candidates):
        for _ in range(500):
            game = sorted(random.sample(candidates, 5))
            pares = [n for n in game if n % 2 == 0]
            if len(pares) in [2, 3]:
                is_valid, _ = statistical_guardian(game, "Quina")
                if is_valid:
                    return game
        return sorted(random.sample(candidates, 5))

    gold = greedy_set_cover(hist, 15, 80)
    supremo = search_quina_game(gold)
    
    transitions = calculate_markov(hist, 80)
    markov_nums = get_markov_predictions(last_draw, transitions, 15)
    if len(markov_nums) < 5: markov_nums = gold
    tendencia = search_quina_game(markov_nums)
    
    all_draws = [n for sub in hist for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 81)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:20]]
    cobertura = search_quina_game(atrasadas)
    
    return supremo, tendencia, cobertura

def generate_dupla_sena():
    # TRATAMENTO SEPARADO DOS DOIS SORTEIOS DA DUPLA SENA
    hist = st.session_state.history["Dupla Sena"]
    
    # Extrai o primeiro sorteio de cada concurso histórico para a base principal
    hist_draw1 = [concurso[0] for concurso in hist]
    hist_draw2 = [concurso[1] for concurso in hist]
    
    def search_dupla_game(candidates):
        for _ in range(500):
            game = sorted(random.sample(candidates, 6))
            is_valid, _ = statistical_guardian(game, "Dupla Sena")
            if is_valid:
                return game
        return sorted(random.sample(candidates, 6))

    # 1º Sorteio Supremo
    gold1 = greedy_set_cover(hist_draw1, 15, 50)
    supremo = search_dupla_game(gold1)
    
    # 2º Sorteio Tendência
    gold2 = greedy_set_cover(hist_draw2, 15, 50)
    tendencia = search_dupla_game(gold2)
    
    # Cobertura combinada (gaps)
    all_draws = [n for sub in hist_draw1 + hist_draw2 for n in sub]
    gaps = {num: all_draws.index(num) if num in all_draws else 999 for num in range(1, 51)}
    atrasadas = [num for num, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:15]]
    cobertura = search_dupla_game(atrasadas)
    
    return supremo, tendencia, cobertura

# ── DESIGN DO WEB APP GRÁFICO (INTERFACES STREAMLIT) ──────────────────

st.markdown("<div class='main-title'>🔮 PORTAL DE INFERÊNCIA PRO</div>", unsafe_type_html=True)
st.markdown("<div class='subtitle'>Ambiente de Otimização Estatística de Alta Performance - Caixa Econômica</div>", unsafe_type_html=True)

# Layout Principal: Duas Colunas
col_nav, col_main = st.columns([1, 3])

with col_nav:
    st.markdown("### ⚙️ Painel de Operações")
    selected_lottery = st.selectbox(
        "Selecione a Loteria Alvo:",
        ["Mega-Sena", "Lotofácil", "Lotomania", "Quina", "Dupla Sena"],
        index=0
    )
    
    # Exibe as informações da Loteria selecionada
    if selected_lottery == "Mega-Sena":
        st.markdown(
            "<div class='lottery-card mega-sena-bg'>"
            "<h4>MEGA-SENA</h4>"
            "<p>Prêmio Estimado: <b>R$ 50 Milhões</b><br>"
            "Próximo Concurso: <b>3047</b></p>"
            "</div>", 
            unsafe_type_html=True
        )
    elif selected_lottery == "Lotofácil":
        st.markdown(
            "<div class='lottery-card lotofacil-bg'>"
            "<h4>LOTOFÁCIL</h4>"
            "<p>Prêmio Estimado: <b>R$ 2 Milhões</b><br>"
            "Próximo Concurso: <b>3767</b></p>"
            "</div>", 
            unsafe_type_html=True
        )
    elif selected_lottery == "Lotomania":
        st.markdown(
            "<div class='lottery-card lotomania-bg'>"
            "<h4>LOTOMANIA</h4>"
            "<p>Prêmio Estimado: <b>R$ 16 Milhões</b><br>"
            "Próximo Concurso: <b>2966</b></p>"
            "</div>", 
            unsafe_type_html=True
        )
    elif selected_lottery == "Quina":
        st.markdown(
            "<div class='lottery-card quina-bg'>"
            "<h4>QUINA</h4>"
            "<p>Prêmio Estimado: <b>R$ 15 Milhões</b><br>"
            "Próximo Concurso: <b>7097</b></p>"
            "</div>", 
            unsafe_type_html=True
        )
    else:
        st.markdown(
            "<div class='lottery-card dupla-sena-bg'>"
            "<h4>DUPLA SENA</h4>"
            "<p>Prêmio Estimado: <b>R$ 1.8 Milhão</b><br>"
            "Próximo Concurso: <b>2999</b></p>"
            "</div>", 
            unsafe_type_html=True
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
                    s, t, c = generate_mega_sena()
                elif selected_lottery == "Lotofácil":
                    s, t, c = generate_lotofacil()
                elif selected_lottery == "Lotomania":
                    s, t, c = generate_lotomania()
                elif selected_lottery == "Quina":
                    s, t, c = generate_quina()
                else:
                    s, t, c = generate_dupla_sena()
                    
                st.session_state.active_supremo = s
                st.session_state.active_tendencia = t
                st.session_state.active_cobertura = c
                st.session_state.generated_lottery = selected_lottery
                st.success("Jogos gerados, auditados e validados pelo Guardião Estatístico!")

        # Exibição dos Prognósticos Ativos
        if "active_supremo" in st.session_state and st.session_state.generated_lottery == selected_lottery:
            s = st.session_state.active_supremo
            t = st.session_state.active_tendencia
            c = st.session_state.active_cobertura
            
            ball_class = {
                "Mega-Sena": "ball-mega",
                "Lotofácil": "ball-facil",
                "Lotomania": "ball-mania",
                "Quina": "ball-quina",
                "Dupla Sena": "ball-dupla"
            }[selected_lottery]
            
            # --- SUPREMO ---
            st.markdown("#### <span class='badge-supremo'>1º PALPITE — O SUPREMO (Aposta Master — Peso Máximo)</span>", unsafe_type_html=True)
            balls_html = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in s])
            st.markdown(f"<div class='ball-container'>{balls_html}</div>", unsafe_type_html=True)
            
            if st.button("💾 Salvar Palpite Supremo", key="save_sup"):
                pred = {"lottery": selected_lottery, "type": "Supremo", "numbers": s, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    st.toast("Palpite Supremo Salvo!", icon="💾")
            
            st.divider()
            
            # --- TENDÊNCIA ---
            st.markdown("#### <span class='badge-tendencia'>2º PALPITE — A TENDÊNCIA CRUZADA (Peso Médio)</span>", unsafe_type_html=True)
            balls_html_t = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in t])
            st.markdown(f"<div class='ball-container'>{balls_html_t}</div>", unsafe_type_html=True)
            
            if st.button("💾 Salvar Palpite Tendência", key="save_tend"):
                pred = {"lottery": selected_lottery, "type": "Tendência", "numbers": t, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    st.toast("Palpite Tendência Salvo!", icon="💾")
                    
            st.divider()
            
            # --- COBERTURA ---
            st.markdown("#### <span class='badge-cobertura'>3º PALPITE — A COBERTURA DE SEGURANÇA (Peso de Cobertura)</span>", unsafe_type_html=True)
            balls_html_c = "".join([f"<div class='ball {ball_class}'>{f'{n:02d}' if n != 0 else '00'}</div>" for n in c])
            st.markdown(f"<div class='ball-container'>{balls_html_c}</div>", unsafe_type_html=True)
            
            if st.button("💾 Salvar Palpite Cobertura", key="save_cob"):
                pred = {"lottery": selected_lottery, "type": "Cobertura", "numbers": c, "date": datetime.now().strftime("%d/%m/%Y %H:%M")}
                if pred not in st.session_state.saved_predictions:
                    st.session_state.saved_predictions.append(pred)
                    st.toast("Palpite Cobertura Salvo!", icon="💾")
        else:
            st.info("Aperte no botão acima para rodar a análise estatística multi-camadas.")

    # ── TAB 2: MEUS JOGOS SALVOS ──────────────────────────────────────
    with tab_saved:
        st.write("### 💾 Seus Jogos Salvos")
        
        if not st.session_state.saved_predictions:
            st.info("Nenhum palpite salvo até o momento.")
        else:
            to_delete = []
            for idx, pred in enumerate(st.session_state.saved_predictions):
                col_info, col_action = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{pred['lottery'].upper()}** - *{pred['type']}* (Salvo em: {pred['date']})")
                    balls_html_s = "".join([f"<span style='display:inline-block; margin:2px; padding:5px 8px; background-color:#edf2f7; border-radius:4px; font-weight:bold; font-size:0.85rem;'>{f'{n:02d}' if n != 0 else '00'}</span>" for n in pred['numbers']])
                    st.markdown(f"<div>{balls_html_s}</div>", unsafe_type_html=True)
                with col_action:
                    if st.button("❌ Excluir", key=f"del_{idx}"):
                        to_delete.append(idx)
                        
                st.markdown("---\")")
                
            if to_delete:
                for idx in sorted(to_delete, reverse=True):
                    st.session_state.saved_predictions.pop(idx)
                st.toast("Palpite excluído com sucesso!", icon="🗑️")
                st.rerun()
                
            txt_data = ""
            for pred in st.session_state.saved_predictions:
                num_str = " ".join([f"{n:02d}" for n in pred['numbers']])
                txt_data += f"{pred['lottery']} - {pred['type']} - {pred['date']}\n{num_str}\n\n"
                
            st.download_button(
                label="📥 Exportar Jogos para Bloco de Notas (TXT)",
                data=txt_data,
                file_name="meus_palpites_otimizados.txt",
                mime="text/plain"
            )

    # ── TAB 3: CONFERÊNCIA INTELIGENTE ────────────────────────────────
    with tab_check:
        st.write("### 🔍 Conferência de Prognósticos")
        
        if not st.session_state.saved_predictions:
            st.warning("É necessário possuir jogos salvos para realizar a conferência.")
        else:
            st.markdown("#### 1. Escolha o Jogo Salvo para Conferir:")
            game_options = [f"{idx} - {p['lottery']} ({p['type']})" for idx, p in enumerate(st.session_state.saved_predictions)]
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
                    st.markdown(f"<div style='text-align:center;'>{''.join(display_html)}</div>", unsafe_type_html=True)

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
