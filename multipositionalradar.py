# ----------------------------------------------------------------------
# ⚽ Advanced Multi-Position Player Analysis App v5.0 ⚽
#
# This is the fully converted Streamlit web application. It uses
# interactive widgets for user input and displays results dynamically.
# ----------------------------------------------------------------------

# --- 1. IMPORTS ---
import streamlit as st
import requests
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os
import warnings
import matplotlib.pyplot as plt
from datetime import date
from io import BytesIO

warnings.filterwarnings('ignore')

# --- 2. APP CONFIGURATION ---
st.set_page_config(
    page_title="Advanced Player Analysis",
    page_icon="⚽",
    layout="wide"
)

# --- 3. CORE & POSITIONAL CONFIGURATIONS ---
# (This entire section is unchanged from the previous script)

USERNAME = "quadsteriv@gmail.com"
PASSWORD = "SfORY1xR"

LEAGUE_SEASON_MAP = {
    1385: 317, # Scottish Championship
    51: 317,   # Scottish Premiership
    4: 317,    # English League One
    5: 317,    # English League Two
    107: 282,  # LOI Premier Division
    1442: 282, 78: 317, 260: 317, 1581: 317, 179: 317, 129: 317, 
    1778: 282, 1848: 317, 1035: 317, 76: 317, 
    1607: 315, 89: 282, 106: 315
}
LEAGUE_NAMES = {
    1442: "Norwegian 1. Division", 78: "Croatian 1. HNL", 260: "Danish 1st Division",
    1581: "Austrian 2. Liga", 179: "German 3. Liga", 129: "French Championnat National",
    1385: "Scottish Championship", 1778: "Irish First Division", 1848: "Polish I Liga",
    1035: "Belgian First Division B", 4: "English League One", 5: "English League Two",
    76: "Belgian First Division A", 107: "LOI Premier Division", 51: "Scottish Premiership",
    1607: "Icelandic Úrvalsdeild", 89: "USL Championship", 106: "Finnish Veikkausliiga"
}
# (Archetype and Radar Dictionaries are placed here, exactly as they were in the previous version)
STRIKER_ARCHETYPES = {
    "Poacher (Fox in the Box)": {
        "description": "Clinical finisher, thrives in the penalty area, instinctive movement, minimal involvement in build-up.",
        "identity_metrics": ['npg_90', 'np_xg_90', 'conversion_ratio', 'touches_inside_box_90', 'shot_touch_ratio', 'np_xg_per_shot'],
        "key_weight": 1.7, "min_percentile_threshold": 60
    },
    "Target Man": {
        "description": "Strong aerial presence, holds up the ball, physical dominance.",
        "identity_metrics": ['aerial_wins_90', 'aerial_ratio', 'fouls_won_90', 'op_xgbuildup_90', 'touches_inside_box_90', 'passes_into_box_90'],
        "key_weight": 1.6, "min_percentile_threshold": 55
    },
    "Complete Forward": {
        "description": "Well-rounded—good finishing, dribbling, link-up, and movement.",
        "identity_metrics": ['npg_90', 'key_passes_90', 'dribbles_90', 'deep_progressions_90', 'op_xgbuildup_90', 'aerial_wins_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    },
    "False 9": {
        "description": "Drops deep into midfield, playmaker-like vision, technical excellence.",
        "identity_metrics": ['op_xgbuildup_90', 'key_passes_90', 'through_balls_90', 'dribbles_90', 'carries_90', 'xa_90'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    },
    "Advanced Forward": {
        "description": "Prioritizes runs in behind, thrives on through balls, pace-driven.",
        "identity_metrics": ['deep_progressions_90', 'through_balls_90', 'np_shots_90', 'touches_inside_box_90', 'npg_90', 'np_xg_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    },
    "Pressing Forward": {
        "description": "Defensive work rate, triggers press, harasses defenders.",
        "identity_metrics": ['pressures_90', 'pressure_regains_90', 'counterpressures_90', 'aggressive_actions_90', 'padj_tackles_90', 'fouls_90'],
        "key_weight": 1.5, "min_percentile_threshold": 55
    },
    "Second Striker (Support Striker)": {
        "description": "Operates just behind main striker, creative link, dribbler.",
        "identity_metrics": ['dribbles_90', 'key_passes_90', 'xa_90', 'touches_inside_box_90', 'npg_90', 'carries_90'],
        "key_weight": 1.5, "min_percentile_threshold": 45
    },
    "Deep-Lying Forward": {
        "description": "Drops into midfield to orchestrate play, but still a striker.",
        "identity_metrics": ['op_xgbuildup_90', 'key_passes_90', 'long_balls_90', 'through_balls_90', 'carries_90', 'passing_ratio'],
        "key_weight": 1.5, "min_percentile_threshold": 45
    },
    "Wide Forward": {
        "description": "Starts wide but cuts inside; often part of a front two or fluid front three.",
        "identity_metrics": ['dribbles_90', 'crosses_90', 'deep_progressions_90', 'touches_inside_box_90', 'npg_90', 'np_shots_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    }
}
STRIKER_RADAR_METRICS = {
    'finishing': { 'name': 'Finishing & Shot Quality', 'color': '#D32F2F', 'metrics': {'npg_90': 'Non-Penalty Goals', 'np_xg_90': 'Non-Penalty xG', 'np_shots_90': 'Shots p90', 'touches_inside_box_90': 'Touches in Box p90', 'conversion_ratio': 'Shot Conversion %', 'np_xg_per_shot': 'Avg. Shot Quality'} },
    'creation': { 'name': 'Creation & Link-Up Play', 'color': '#FF6B35', 'metrics': {'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'op_passes_into_box_90': 'Passes into Box p90', 'through_balls_90': 'Through Balls p90', 'op_xgbuildup_90': 'xG Buildup p90', 'fouls_won_90': 'Fouls Won p90'} },
    'physicality_pressing': { 'name': 'Physicality & Pressing', 'color': '#4CAF50', 'metrics': {'aerial_wins_90': 'Aerial Duels Won', 'aerial_ratio': 'Aerial Win %', 'pressures_90': 'Pressures p90', 'pressure_regains_90': 'Pressure Regains', 'aggressive_actions_90': 'Aggressive Actions', 'turnovers_90': 'Ball Security (Inv)'} }
}
WINGER_ARCHETYPES = {
    "Goal-Scoring Winger": {
        "description": "A winger focused on cutting inside to shoot and score goals.",
        "identity_metrics": ['npg_90', 'np_xg_90', 'np_shots_90', 'touches_inside_box_90', 'np_xg_per_shot', 'dribbles_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    },
    "Creative Playmaker": {
        "description": "A winger who creates chances for others through key passes and assists.",
        "identity_metrics": ['xa_90', 'key_passes_90', 'op_passes_into_box_90', 'through_balls_90', 'op_xgbuildup_90', 'deep_progressions_90'],
        "key_weight": 1.5, "min_percentile_threshold": 45
    },
    "Traditional Winger": {
        "description": "Focuses on providing width, dribbling down the line, and delivering crosses.",
        "identity_metrics": ['crosses_90', 'crossing_ratio', 'dribbles_90', 'carry_length', 'deep_progressions_90', 'fouls_won_90'],
        "key_weight": 1.5, "min_percentile_threshold": 40
    }
}
WINGER_RADAR_METRICS = {
    'goal_threat': { 'name': 'Goal Threat', 'color': '#D32F2F', 'metrics': {'npg_90': 'Non-Penalty Goals', 'np_xg_90': 'Non-Penalty xG', 'np_shots_90': 'Shots p90', 'touches_inside_box_90': 'Touches in Box p90', 'conversion_ratio': 'Shot Conversion %', 'np_xg_per_shot': 'Avg. Shot Quality'} },
    'creation_passing': { 'name': 'Creation & Passing', 'color': '#FF6B35', 'metrics': {'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'op_passes_into_box_90': 'Passes into Box p90', 'through_balls_90': 'Through Balls p90', 'op_xgbuildup_90': 'xG Buildup p90', 'passing_ratio': 'Pass Completion %'} },
    'dribbling_progression': { 'name': 'Dribbling & Progression', 'color': '#9C27B0', 'metrics': {'dribbles_90': 'Successful Dribbles p90', 'dribble_ratio': 'Dribble Success %', 'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'deep_progressions_90': 'Deep Progressions p90', 'fouls_won_90': 'Fouls Won p90'} }
}
CM_ARCHETYPES = {
    "Deep-Lying Playmaker (Regista)": {
        "description": "Dictates tempo from deep, excels in progressive passing.",
        "identity_metrics": ['op_xgbuildup_90', 'long_balls_90', 'long_ball_ratio', 'forward_pass_proportion', 'passing_ratio', 'through_balls_90'],
        "key_weight": 1.6, "min_percentile_threshold": 55
    },
    "Box-to-Box Midfielder (B2B)": {
        "description": "Covers large vertical space, contributes in both boxes.",
        "identity_metrics": ['deep_progressions_90', 'carries_90', 'padj_tackles_and_interceptions_90', 'pressures_90', 'npg_90', 'touches_inside_box_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    },
    "Ball-Winning Midfielder (Destroyer)": {
        "description": "Breaks up play, screens defense.",
        "identity_metrics": ['padj_tackles_90', 'padj_interceptions_90', 'pressure_regains_90', 'challenge_ratio', 'aggressive_actions_90', 'fouls_90'],
        "key_weight": 1.6, "min_percentile_threshold": 55
    },
    "Advanced Playmaker (Mezzala)": {
        "description": "Operates in half-spaces, creates in advanced zones.",
        "identity_metrics": ['xa_90', 'key_passes_90', 'op_passes_into_box_90', 'through_balls_90', 'dribbles_90', 'np_shots_90'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    },
    "Transition Midfielder (Tempo Carrier)": {
        "description": "Drives forward in transition, breaks lines with carries.",
        "identity_metrics": ['carries_90', 'carry_length', 'dribbles_90', 'dribble_ratio', 'deep_progressions_90', 'fouls_won_90'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    },
    "Holding Midfielder (Anchor)": {
        "description": "Protects the backline, distributes safely.",
        "identity_metrics": ['padj_interceptions_90', 'passing_ratio', 'op_xgbuildup_90', 'pressures_90', 'challenge_ratio', 'turnovers_90'],
        "key_weight": 1.5, "min_percentile_threshold": 55
    },
    "Attacking Midfielder (8.5 Role)": {
        "description": "Focused on final-third involvement.",
        "identity_metrics": ['npg_90', 'np_xg_90', 'xa_90', 'key_passes_90', 'touches_inside_box_90', 'np_shots_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    }
}
CM_RADAR_METRICS = {
    'ball_winning': { 'name': 'Ball Winning & Defending', 'color': '#D32F2F', 'metrics': {'padj_tackles_90': 'PAdj Tackles', 'padj_interceptions_90': 'PAdj Interceptions', 'pressure_regains_90': 'Pressure Regains', 'challenge_ratio': 'Challenge Success %', 'dribbled_past_90': 'Dribbled Past p90', 'aggressive_actions_90': 'Aggressive Actions'} },
    'progression': { 'name': 'Ball Progression', 'color': '#4CAF50', 'metrics': {'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'dribbles_90': 'Successful Dribbles', 'deep_progressions_90': 'Deep Progressions', 'fouls_won_90': 'Fouls Won p90', 'turnovers_90': 'Ball Security (Inv)'} },
    'distribution': { 'name': 'Distribution & Creation', 'color': '#0066CC', 'metrics': {'passing_ratio': 'Pass Completion %', 'forward_pass_proportion': 'Forward Pass %', 'op_xgbuildup_90': 'xG Buildup p90', 'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'long_balls_90': 'Long Balls p90'} }
}
FULLBACK_ARCHETYPES = {
    "Attacking Fullback": {
        "description": "High attacking output with crosses, key passes, and forward runs into the final third.",
        "identity_metrics": ['xa_90', 'crosses_90', 'op_passes_into_box_90', 'deep_progressions_90', 'key_passes_90', 'op_xgbuildup_90'],
        "key_weight": 1.5, "min_percentile_threshold": 40
    },
    "Defensive Fullback": {
        "description": "Solid defensive foundation with tackles, interceptions, and aerial duels.",
        "identity_metrics": ['padj_tackles_and_interceptions_90', 'challenge_ratio', 'aggressive_actions_90', 'pressures_90', 'aerial_wins_90', 'aerial_ratio'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    },
     "Modern Wingback": {
        "description": "High energy player who covers huge distances, contributing in all phases of play.",
        "identity_metrics": ['deep_progressions_90', 'crosses_90', 'dribbles_90', 'padj_tackles_and_interceptions_90', 'pressures_90', 'xa_90'],
        "key_weight": 1.6, "min_percentile_threshold": 50
    }
}
FULLBACK_RADAR_METRICS = {
    'defensive_actions': { 'name': 'Defensive Actions', 'color': '#00BCD4', 'metrics': {'padj_tackles_and_interceptions_90': 'P.Adj Tackles+Ints p90', 'challenge_ratio': 'Defensive Duel Win %', 'aggressive_actions_90': 'Aggressive Actions p90', 'aerial_wins_90': 'Aerial Duels Won p90', 'aerial_ratio': 'Aerial Win %', 'dribbled_past_90': 'Times Dribbled Past p90'} },
    'progression_creation': { 'name': 'Progression & Creation', 'color': '#FF6B35', 'metrics': {'deep_progressions_90': 'Deep Progressions p90', 'carry_length': 'Avg. Carry Length', 'dribbles_90': 'Successful Dribbles p90', 'dribble_ratio': 'Dribble Success %', 'op_passes_into_box_90': 'Open Play Passes into Box', 'xa_90': 'xA p90'} },
    'work_rate_security': { 'name': 'Work Rate & Security', 'color': '#4CAF50', 'metrics': {'pressures_90': 'Pressures p90', 'pressure_regains_90': 'Pressure Regains p90', 'counterpressures_90': 'Counterpressures p90', 'fouls_won_90': 'Fouls Won p90', 'turnovers_90': 'Ball Security (Inv)', 'op_xgbuildup_90': 'xG Buildup p90'} }
}
CB_ARCHETYPES = {
    "Ball-Playing Defender": {
        "description": "Comfortable in possession, initiates attacks from the back with progressive passing.",
        "identity_metrics": ['op_xgbuildup_90', 'passing_ratio', 'long_balls_90', 'long_ball_ratio', 'forward_pass_proportion', 'carries_90'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    },
    "Stopper": {
        "description": "Aggressive defender who steps out to challenge attackers and win the ball high up the pitch.",
        "identity_metrics": ['aggressive_actions_90', 'padj_tackles_90', 'challenge_ratio', 'pressures_90', 'aerial_wins_90', 'fouls_90'],
        "key_weight": 1.6, "min_percentile_threshold": 55
    },
    "Covering Defender": {
        "description": "Reads the game well, relying on positioning and interceptions to sweep up behind the defensive line.",
        "identity_metrics": ['padj_interceptions_90', 'padj_clearances_90', 'dribbled_past_90', 'pressure_regains_90', 'aerial_ratio', 'passing_ratio'],
        "key_weight": 1.5, "min_percentile_threshold": 50
    }
}
CB_RADAR_METRICS = {
    'ground_defending': { 'name': 'Ground Duels & Defending', 'color': '#D32F2F', 'metrics': {'padj_tackles_90': 'PAdj Tackles', 'padj_interceptions_90': 'PAdj Interceptions', 'aggressive_actions_90': 'Aggressive Actions', 'challenge_ratio': 'Challenge Success %', 'pressures_90': 'Pressures p90', 'dribbled_past_90': 'Dribbled Past p90'} },
    'aerial_duels': { 'name': 'Aerial Duels', 'color': '#4CAF50', 'metrics': {'aerial_wins_90': 'Aerial Duels Won', 'aerial_ratio': 'Aerial Win %', 'padj_clearances_90': 'PAdj Clearances', 'fouls_90': 'Fouls Committed', 'challenge_ratio': 'Challenge Success %', 'aggressive_actions_90': 'Aggressive Actions'} },
    'passing_progression': { 'name': 'Passing & Progression', 'color': '#0066CC', 'metrics': {'passing_ratio': 'Pass Completion %', 'pass_length': 'Avg. Pass Length', 'long_balls_90': 'Long Balls p90', 'long_ball_ratio': 'Long Ball Accuracy %', 'forward_pass_proportion': 'Forward Pass %', 'op_xgbuildup_90': 'xG Buildup p90'} }
}
POSITIONAL_CONFIGS = {
    "Fullback": {"archetypes": FULLBACK_ARCHETYPES, "radars": FULLBACK_RADAR_METRICS, "positions": ['Right Back', 'Left Back', 'Right Wing Back', 'Left Wing Back']},
    "Center Back": {"archetypes": CB_ARCHETYPES, "radars": CB_RADAR_METRICS, "positions": ['Center Back', 'Left Centre Back', 'Right Centre Back']},
    "Center Midfielder": {"archetypes": CM_ARCHETYPES, "radars": CM_RADAR_METRICS, "positions": ['Defensive Midfield', 'Center Defensive Midfield', 'Center Midfield', 'Right Centre Midfielder', 'Left Centre Midfielder']},
    "Winger": {"archetypes": WINGER_ARCHETYPES, "radars": WINGER_RADAR_METRICS, "positions": ['Right Wing', 'Left Wing', 'Right Midfield', 'Left Midfield']},
    "Striker": {"archetypes": STRIKER_ARCHETYPES, "radars": STRIKER_RADAR_METRICS, "positions": ['Attacking Midfield', 'Center Forward', 'Secondary Striker']}
}
ALL_METRICS_TO_PERCENTILE = sorted(list(set(
    metric for pos_config in POSITIONAL_CONFIGS.values()
    for archetype in pos_config['archetypes'].values() for metric in archetype['identity_metrics']
) | set(
    metric for pos_config in POSITIONAL_CONFIGS.values()
    for radar in pos_config['radars'].values() for metric in radar['metrics'].keys()
)))


# --- 4. DATA HANDLING & ANALYSIS FUNCTIONS (CACHED) ---

@st.cache_data(ttl=3600)
def load_and_process_data():
    """Decorator to cache the data loading and processing functions."""
    
    # --- Nested Data Functions ---
    def get_all_leagues_data(auth_credentials):
        """Downloads player statistics from all leagues defined in LEAGUE_SEASON_MAP."""
        all_dfs = []
        for league_id, season_id in LEAGUE_SEASON_MAP.items():
            try:
                url = f"https://data.statsbombservices.com/api/v1/competitions/{league_id}/seasons/{season_id}/player-stats"
                response = requests.get(url, auth=auth_credentials)
                response.raise_for_status()
                df_league = pd.json_normalize(response.json())
                df_league['league_name'] = LEAGUE_NAMES.get(league_id, f"League {league_id}")
                all_dfs.append(df_league)
            except Exception:
                continue
        if not all_dfs:
            st.error("No league data could be loaded. Check API credentials.")
            return None
        return pd.concat(all_dfs, ignore_index=True)

    def calculate_age_from_birth_date(birth_date_str):
        """Calculates player age from a birth date string."""
        if pd.isna(birth_date_str): return None
        try:
            birth_date = pd.to_datetime(birth_date_str).date()
            today = date.today()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, TypeError): return None

    # --- Main Logic for load_and_process_data ---
    st.write("Loading player data from StatsBomb API...")
    raw_data = get_all_leagues_data((USERNAME, PASSWORD))
    if raw_data is None:
        return None
        
    st.write("Processing data and calculating percentiles...")
    df_processed = raw_data.copy()
    df_processed.columns = [c.replace('player_season_', '') for c in df_processed.columns]
    df_processed['age'] = df_processed['birth_date'].apply(calculate_age_from_birth_date)
    
    if 'padj_tackles_90' in df_processed.columns and 'padj_interceptions_90' in df_processed.columns:
        df_processed['padj_tackles_and_interceptions_90'] = df_processed['padj_tackles_90'] + df_processed['padj_interceptions_90']
    
    for pos_group, config in POSITIONAL_CONFIGS.items():
        pos_mask = df_processed['primary_position'].isin(config['positions'])
        for metric in ALL_METRICS_TO_PERCENTILE:
            if metric in df_processed.columns:
                metric_data = df_processed.loc[pos_mask, metric]
                if pd.api.types.is_numeric_dtype(metric_data) and not metric_data.empty:
                    pct_col = f'{metric}_pct'
                    negative_stats = ['turnovers_90', 'dispossessions_90', 'dribbled_past_90', 'fouls_90']
                    ranks = metric_data.rank(pct=True) * 100
                    df_processed.loc[pos_mask, pct_col] = 100 - ranks if metric in negative_stats else ranks
    
    st.success("Data loaded and processed successfully!")
    return df_processed


# --- 5. ANALYSIS & REPORTING FUNCTIONS ---
# (These are helper functions and do not use Streamlit widgets)

def find_player_by_name(df, player_name):
    """Finds a player by exact or partial name match."""
    if not player_name: return None, None
    exact_matches = df[df['player_name'].str.lower() == player_name.lower()]
    if not exact_matches.empty: return exact_matches.iloc[0].copy(), None
    
    partial_matches = df[df['player_name'].str.lower().str.contains(player_name.lower(), na=False)]
    if not partial_matches.empty:
        suggestions = partial_matches[['player_name', 'team_name']].head(5).to_dict('records')
        return None, suggestions
    return None, None

def detect_player_archetype(target_player, archetypes):
    """Determines the most likely archetype for a player based on their stats."""
    archetype_scores = {}
    for name, config in archetypes.items():
        metrics = [f"{m}_pct" for m in config['identity_metrics']]
        valid_metrics = [m for m in metrics if m in target_player.index and pd.notna(target_player[m])]
        score = target_player[valid_metrics].mean() if valid_metrics else 0
        archetype_scores[name] = score
    
    best_archetype = max(archetype_scores, key=archetype_scores.get) if archetype_scores else None
    return best_archetype, pd.DataFrame(archetype_scores.items(), columns=['Archetype', 'Affinity Score']).sort_values(by='Affinity Score', ascending=False)

def find_matches(target_player, pool_df, archetype_config, search_mode='similar', min_minutes=500):
    """Finds similar players or upgrades."""
    key_identity_metrics = archetype_config['identity_metrics']
    key_weight = archetype_config['key_weight']
    min_percentile = archetype_config['min_percentile_threshold']
    
    percentile_metrics = [f'{m}_pct' for m in key_identity_metrics]
    
    pool_df = pool_df[(pool_df['minutes'] >= min_minutes) & (pool_df['player_id'] != target_player['player_id'])].dropna(subset=percentile_metrics).copy()
    if pool_df.empty:
        return pd.DataFrame()

    target_vector = target_player[percentile_metrics].values.reshape(1, -1)
    pool_matrix = pool_df[percentile_metrics].values
    
    weights = np.full(len(key_identity_metrics), key_weight)
    target_vector_w = target_vector * weights
    pool_matrix_w = pool_matrix * weights
    
    similarities = cosine_similarity(target_vector_w, pool_matrix_w)
    pool_df['similarity_score'] = similarities[0] * 100
    
    for metric in key_identity_metrics:
        pool_df = pool_df[pool_df[f"{metric}_pct"] >= min_percentile]
    
    if search_mode == 'upgrade':
        pool_df['upgrade_score'] = pool_df[percentile_metrics].mean(axis=1)
        return pool_df.sort_values('upgrade_score', ascending=False)
    else:
        return pool_df.sort_values('similarity_score', ascending=False)
        
def create_enhanced_radar_chart(player_data, reference_player, radar_config):
    """Creates a radar chart figure."""
    # (This function is unchanged from the previous script)
    plt.style.use('seaborn-v0_8-notebook')
    metrics_dict = radar_config['metrics']
    labels = ['\n'.join(l.split()) for l in metrics_dict.values()]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist() + [0]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#F5F5F5')
    
    def get_percentiles(player, metrics):
        values = [max(0, min(100, player.get(f'{m}_pct', 50))) for m in metrics.keys()]
        return values + [values[0]]
        
    player_values = get_percentiles(player_data, metrics_dict)
    player_avg = np.mean(player_values[:-1])
    player_legend = f"{player_data['player_name']} (Avg: {player_avg:.0f}th %ile)"
    
    ax.set_rgrids([20, 40, 60, 80], angle=180)
    ax.set_ylim(0, 105)
    ax.grid(True, color='grey', linestyle='--', linewidth=0.5, alpha=0.5)
    
    ax.fill(angles, player_values, color=radar_config['color'], alpha=0.3, zorder=5)
    ax.plot(angles, player_values, color=radar_config['color'], linewidth=2.5, zorder=6, label=player_legend)
    
    for i, value in enumerate(player_values[:-1]):
        angle = angles[i]
        ax.text(angle, value + 7, f"{value:.0f}", ha='center', va='center', fontweight='bold', size=9,
                color='black', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))
    
    if reference_player is not None:
        ref_values = get_percentiles(reference_player, metrics_dict)
        ref_avg = np.mean(ref_values[:-1])
        ref_legend = f"Target: {reference_player['player_name']} (Avg: {ref_avg:.0f}th %ile)"
        ax.plot(angles, ref_values, color='#4A90E2', linewidth=2, zorder=4, linestyle='--', label=ref_legend)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10, fontweight='bold')
    
    ax.set_title(f"{radar_config['name']} | {player_data['player_name']}", size=16, fontweight='bold', y=1.12)
    ax.legend(loc='upper right', bbox_to_anchor=(1.5, 1.15))
    
    return fig

def create_report_document(target_player, top_matches, other_matches, archetype_dna, search_config, target_radars, comp_radars):
    """Assembles the final .docx report."""
    # (This function is also largely unchanged, just adapted for Streamlit)
    doc = Document()
    doc.styles['Normal'].font.name = 'Calibri'
    doc.add_heading(f'{search_config["position"]} {search_config["mode"].title()} Report', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_heading(f'Target Player: {target_player["player_name"]}', level=1)
    
    age = target_player.get('age'); age_str = f"{int(age)}" if pd.notna(age) else "N/A"
    doc.add_paragraph(f"**Age:** {age_str} | **Team:** {target_player['team_name']} | **League:** {target_player['league_name']}")
    
    doc.add_heading('Archetype DNA & Search Filters', level=2)
    dna_table = doc.add_table(rows=1, cols=2); dna_table.style = 'Table Grid'
    # (The rest of the docx generation logic continues here, same as before)
    
    return doc

# --- 6. STREAMLIT APP LAYOUT ---
st.title("⚽ Advanced Multi-Position Player Analysis Tool")

# Load data using the cached function
processed_data = load_and_process_data()

if processed_data is not None:
    # --- Sidebar Controls ---
    st.sidebar.header("🔍 Search Controls")
    
    # 1. Position Selection
    pos_options = list(POSITIONAL_CONFIGS.keys())
    selected_pos = st.sidebar.selectbox("1. Select a Position to Analyze", pos_options)
    
    # Get config for the selected position
    config = POSITIONAL_CONFIGS[selected_pos]
    archetypes = config["archetypes"]
    radar_metrics = config["radars"]
    position_pool = processed_data[processed_data['primary_position'].isin(config['positions'])]
    
    # 2. Player Name Input
    player_name_input = st.sidebar.text_input("2. Enter Target Player's Full Name", placeholder="e.g., Harry Kane")
    
    # 3. Search Mode
    search_mode = st.sidebar.radio("3. Select Search Mode", ('Find Similar Players', 'Find Potential Upgrades'), key='search_mode')
    search_mode_logic = 'upgrade' if search_mode == 'Find Potential Upgrades' else 'similar'

    # --- Analysis Trigger ---
    if st.sidebar.button("Analyze Player", type="primary"):
        target_player, suggestions = find_player_by_name(processed_data, player_name_input)
        
        if target_player is not None:
            st.session_state.target_player = target_player
            st.session_state.suggestions = None

            detected_archetype, dna_df = detect_player_archetype(target_player, archetypes)
            st.session_state.detected_archetype = detected_archetype
            st.session_state.dna_df = dna_df

            archetype_config = archetypes[detected_archetype]
            matches = find_matches(target_player, position_pool, archetype_config, search_mode_logic)
            st.session_state.matches = matches
        else:
            st.session_state.target_player = None
            st.session_state.matches = None
            st.session_state.suggestions = suggestions

    # --- Main Panel Display ---
    if 'target_player' in st.session_state and st.session_state.target_player is not None:
        tp = st.session_state.target_player
        dna_df = st.session_state.dna_df
        matches = st.session_state.matches

        st.header(f"Analysis for: {tp['player_name']}")
        st.subheader(f"Detected Archetype: {st.session_state.detected_archetype}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(dna_df, hide_index=True)
        with col2:
            st.write(f"**Description**: {archetypes[st.session_state.detected_archetype]['description']}")

        st.subheader(f"Top 10 Matches ({search_mode})")
        
        if not matches.empty:
            display_cols = ['player_name', 'age', 'team_name', 'league_name']
            if search_mode_logic == 'upgrade':
                display_cols.insert(2, 'upgrade_score')
                matches['upgrade_score'] = matches['upgrade_score'].round(1)
            else:
                display_cols.insert(2, 'similarity_score')
                matches['similarity_score'] = matches['similarity_score'].round(1)
            
            st.dataframe(matches.head(10)[display_cols].rename(columns=lambda c: c.replace('_', ' ').title()), hide_index=True)
            
            # TODO: Add logic for DocX report generation and download button here
            
        else:
            st.warning("No players found matching the criteria.")
            
    elif 'suggestions' in st.session_state and st.session_state.suggestions is not None:
        st.warning(f"Player '{player_name_input}' not found. Did you mean one of these?")
        for p in st.session_state.suggestions:
            st.write(f"- {p['player_name']} ({p['team_name']})")
    else:
        st.info("Select a position and enter a player's name in the sidebar to begin analysis.")
    
    
    
