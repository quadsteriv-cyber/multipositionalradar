# ----------------------------------------------------------------------
# ⚽ Advanced Multi-Position Player Analysis App v6.6 ⚽
#
# This version introduces a dynamic, multi-player comparison tool and
# refines the player selection workflow to be more intuitive.
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

USERNAME = "quadsteriv@gmail.com"
PASSWORD = "SfORY1xR"

LEAGUE_NAMES = {
    4: "League One", 5: "League Two", 51: "Premiership", 65: "National League",
    76: "Liga", 78: "1. HNL", 89: "USL Championship", 106: "Veikkausliiga",
    107: "Premier Division", 129: "Championnat National", 166: "Premier League 2 Division One",
    179: "3. Liga", 260: "1st Division", 1035: "First Division B", 1385: "Championship",
    1442: "1. Division", 1581: "2. Liga", 1607: "Úrvalsdeild", 1778: "First Division",
    1848: "I Liga", 1865: "First League"
}

# Refined list of seasons from 2022/23 to 2025/26
COMPETITION_SEASONS = {
    4: [235, 281, 317, 318],
    5: [235, 281, 317, 318],
    51: [235, 281, 317, 318],
    65: [281, 318],
    76: [317, 318],
    78: [317, 318],
    89: [106, 107, 282, 315],
    106: [315],
    107: [106, 107, 282, 315],
    129: [317, 318],
    166: [318],
    179: [317, 318],
    260: [317, 318],
    1035: [317, 318],
    1385: [235, 281, 317, 318],
    1442: [107, 282, 315],
    1581: [317, 318],
    1607: [315],
    1778: [282, 315],
    1848: [281, 317, 318],
    1865: [318]
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
    'finishing': { 'name': 'Finishing', 'color': '#D32F2F', 'metrics': {'npg_90': 'Non-Penalty Goals', 'np_xg_90': 'Non-Penalty xG', 'np_shots_90': 'Shots p90', 'conversion_ratio': 'Shot Conversion %', 'np_xg_per_shot': 'Avg. Shot Quality'} },
    'box_presence': { 'name': 'Box Presence', 'color': '#AF1D1D', 'metrics': {'touches_inside_box_90': 'Touches in Box p90', 'passes_inside_box_90': 'Passes in Box p90', 'positive_outcome_90': 'Positive Outcomes p90'} },
    'creation': { 'name': 'Creation & Link-Up', 'color': '#FF6B35', 'metrics': {'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'op_passes_into_box_90': 'Passes into Box p90', 'through_balls_90': 'Through Balls p90', 'op_xgbuildup_90': 'xG Buildup p90'} },
    'dribbling': { 'name': 'Dribbling & Carrying', 'color': '#9C27B0', 'metrics': {'dribbles_90': 'Successful Dribbles p90', 'dribble_ratio': 'Dribble Success %', 'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'turnovers_90': 'Ball Security (Inv)'} },
    'aerial': { 'name': 'Aerial Prowess', 'color': '#607D8B', 'metrics': {'aerial_wins_90': 'Aerial Duels Won p90', 'aerial_ratio': 'Aerial Win %', 'fouls_won_90': 'Fouls Won p90'} },
    'defensive': { 'name': 'Defensive Contribution', 'color': '#4CAF50', 'metrics': {'pressures_90': 'Pressures p90', 'pressure_regains_90': 'Pressure Regains p90', 'counterpressures_90': 'Counterpressures p90', 'aggressive_actions_90': 'Aggressive Actions'} }
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
    'creation': { 'name': 'Chance Creation', 'color': '#FF6B35', 'metrics': {'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'op_passes_into_box_90': 'Passes into Box p90', 'through_balls_90': 'Through Balls p90', 'op_xgbuildup_90': 'xG Buildup p90', 'passing_ratio': 'Pass Completion %'} },
    'progression': { 'name': 'Dribbling & Progression', 'color': '#9C27B0', 'metrics': {'dribbles_90': 'Successful Dribbles p90', 'dribble_ratio': 'Dribble Success %', 'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'deep_progressions_90': 'Deep Progressions p90', 'fouls_won_90': 'Fouls Won p90'} },
    'crossing': { 'name': 'Crossing Profile', 'color': '#00BCD4', 'metrics': {'crosses_90': 'Completed Crosses p90', 'crossing_ratio': 'Cross Completion %', 'box_cross_ratio': '% of Box Passes that are Crosses'} },
    'defensive': { 'name': 'Defensive Work Rate', 'color': '#4CAF50', 'metrics': {'pressures_90': 'Pressures p90', 'pressure_regains_90': 'Pressure Regains p90', 'padj_tackles_90': 'P.Adj Tackles p90', 'padj_interceptions_90': 'P.Adj Interceptions p90'} },
    'duels': { 'name': 'Duels & Security', 'color': '#607D8B', 'metrics': {'turnovers_90': 'Ball Security (Inv)', 'dribbled_past_90': 'Times Dribbled Past p90', 'challenge_ratio': 'Defensive Duel Win %'} }
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
    'defending': { 'name': 'Defensive Actions', 'color': '#D32F2F', 'metrics': {'padj_tackles_and_interceptions_90': 'P.Adj Tackles+Ints', 'challenge_ratio': 'Defensive Duel Win %', 'dribbled_past_90': 'Times Dribbled Past p90', 'aggressive_actions_90': 'Aggressive Actions'} },
    'duels': { 'name': 'Duels & Physicality', 'color': '#AF1D1D', 'metrics': {'aerial_wins_90': 'Aerial Duels Won', 'aerial_ratio': 'Aerial Win %', 'fouls_won_90': 'Fouls Won'} },
    'passing': { 'name': 'Passing & Distribution', 'color': '#0066CC', 'metrics': {'passing_ratio': 'Pass Completion %', 'forward_pass_proportion': 'Forward Pass %', 'long_balls_90': 'Long Balls p90', 'long_ball_ratio': 'Long Ball Accuracy %'} },
    'creation': { 'name': 'Creativity & Creation', 'color': '#FF6B35', 'metrics': {'key_passes_90': 'Key Passes p90', 'xa_90': 'xA p90', 'through_balls_90': 'Through Balls p90', 'op_xgbuildup_90': 'xG Buildup p90'} },
    'progression': { 'name': 'Ball Progression', 'color': '#4CAF50', 'metrics': {'deep_progressions_90': 'Deep Progressions', 'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'dribbles_90': 'Successful Dribbles'} },
    'attacking': { 'name': 'Attacking Output', 'color': '#9C27B0', 'metrics': {'npg_90': 'Non-Penalty Goals', 'np_xg_90': 'Non-Penalty xG', 'np_shots_90': 'Shots p90', 'touches_inside_box_90': 'Touches in Box'} }
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
    'defensive_actions': { 'name': 'Defensive Actions', 'color': '#00BCD4', 'metrics': {'padj_tackles_and_interceptions_90': 'P.Adj Tackles+Ints p90', 'challenge_ratio': 'Defensive Duel Win %', 'dribbled_past_90': 'Times Dribbled Past p90'} },
    'duels': { 'name': 'Duels', 'color': '#008294', 'metrics': {'aerial_wins_90': 'Aerial Duels Won p90', 'aerial_ratio': 'Aerial Win %', 'aggressive_actions_90': 'Aggressive Actions p90'} },
    'progression_creation': { 'name': 'Progression & Creation', 'color': '#FF6B35', 'metrics': {'deep_progressions_90': 'Deep Progressions p90', 'carries_90': 'Ball Carries p90', 'dribbles_90': 'Successful Dribbles p90', 'xa_90': 'xA p90'} },
    'crossing': { 'name': 'Crossing', 'color': '#FFA735', 'metrics': {'crosses_90': 'Completed Crosses p90', 'crossing_ratio': 'Cross Completion %', 'box_cross_ratio': '% of Box Passes that are Crosses'} },
    'passing': { 'name': 'Passing & Buildup', 'color': '#9C27B0', 'metrics': {'passing_ratio': 'Pass Completion %', 'op_xgbuildup_90': 'xG Buildup p90', 'key_passes_90': 'Key Passes p90'} },
    'work_rate': { 'name': 'Work Rate & Security', 'color': '#4CAF50', 'metrics': {'pressures_90': 'Pressures p90', 'pressure_regains_90': 'Pressure Regains p90', 'turnovers_90': 'Ball Security (Inv)'} }
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
    'ground_defending': { 'name': 'Ground Duels', 'color': '#D32F2F', 'metrics': {'padj_tackles_90': 'PAdj Tackles', 'challenge_ratio': 'Challenge Success %', 'aggressive_actions_90': 'Aggressive Actions'} },
    'aerial_duels': { 'name': 'Aerial Duels & Clearances', 'color': '#4CAF50', 'metrics': {'aerial_wins_90': 'Aerial Duels Won', 'aerial_ratio': 'Aerial Win %', 'padj_clearances_90': 'PAdj Clearances'} },
    'passing_distribution': { 'name': 'Passing & Distribution', 'color': '#0066CC', 'metrics': {'passing_ratio': 'Pass Completion %', 'pass_length': 'Avg. Pass Length', 'long_balls_90': 'Long Balls p90', 'long_ball_ratio': 'Long Ball Accuracy %'} },
    'ball_progression': { 'name': 'Ball Progression', 'color': '#FFC107', 'metrics': {'carries_90': 'Ball Carries p90', 'carry_length': 'Avg. Carry Length', 'deep_progressions_90': 'Deep Progressions'} },
    'defensive_positioning': { 'name': 'Defensive Positioning', 'color': '#00BCD4', 'metrics': {'padj_interceptions_90': 'PAdj Interceptions', 'dribbled_past_90': 'Times Dribbled Past p90', 'pressure_regains_90': 'Pressure Regains'} },
    'on_ball_security': { 'name': 'On-Ball Security', 'color': '#607D8B', 'metrics': {'turnovers_90': 'Ball Security (Inv)', 'op_xgbuildup_90': 'xG Buildup p90', 'fouls_90': 'Fouls Committed'} }
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
    @st.cache_resource
    def get_all_leagues_data(_auth_credentials):
        """Downloads player statistics from all leagues defined in COMPETITION_SEASONS."""
        all_dfs = []
        for league_id, season_ids in COMPETITION_SEASONS.items():
            for season_id in season_ids:
                try:
                    url = f"https://data.statsbombservices.com/api/v1/competitions/{league_id}/seasons/{season_id}/player-stats"
                    response = requests.get(url, auth=_auth_credentials)
                    response.raise_for_status()
                    df_league = pd.json_normalize(response.json())
                    df_league['league_name'] = LEAGUE_NAMES.get(league_id, f"League {league_id}")
                    all_dfs.append(df_league)
                except Exception:
                    continue 
        if not all_dfs:
            st.error("No league data could be loaded. Check API credentials or league/season IDs.")
            return None
        return pd.concat(all_dfs, ignore_index=True)

    def calculate_age_from_birth_date(birth_date_str):
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

def find_player_by_name(df, player_name):
    if not player_name: return None, None
    exact_matches = df[df['player_name'].str.lower() == player_name.lower()]
    if not exact_matches.empty: return exact_matches.iloc[0].copy(), None
    
    partial_matches = df[df['player_name'].str.lower().str.contains(player_name.lower(), na=False)]
    if not partial_matches.empty:
        suggestions = partial_matches[['player_name', 'team_name']].head(5).to_dict('records')
        return None, suggestions
    return None, None

def detect_player_archetype(target_player, archetypes):
    archetype_scores = {}
    for name, config in archetypes.items():
        metrics = [f"{m}_pct" for m in config['identity_metrics']]
        valid_metrics = [m for m in metrics if m in target_player.index and pd.notna(target_player[m])]
        score = target_player[valid_metrics].mean() if valid_metrics else 0
        archetype_scores[name] = score
    
    best_archetype = max(archetype_scores, key=archetype_scores.get) if archetype_scores else None
    return best_archetype, pd.DataFrame(archetype_scores.items(), columns=['Archetype', 'Affinity Score']).sort_values(by='Affinity Score', ascending=False)

def find_matches(target_player, pool_df, archetype_config, search_mode='similar', min_minutes=500):
    key_identity_metrics = archetype_config['identity_metrics']
    key_weight = archetype_config['key_weight']
    min_percentile = archetype_config['min_percentile_threshold']
    
    percentile_metrics = [f'{m}_pct' for m in key_identity_metrics]
    
    pool_df = pool_df[(pool_df['minutes'] >= min_minutes) & (pool_df['player_id'] != target_player['player_id'])].dropna(subset=percentile_metrics).copy()
    if pool_df.empty:
        return pd.DataFrame()

    target_vector = target_player[percentile_metrics].fillna(50).values.reshape(1, -1)
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
    
    title = f"{radar_config['name']} | {player_data['player_name']}"
    if reference_player is not None:
        title += f"\nvs. {reference_player['player_name']}"
    
    ax.set_title(title, size=16, fontweight='bold', y=1.12)
    ax.legend(loc='upper right', bbox_to_anchor=(1.5, 1.15))
    
    return fig

# --- 6. STREAMLIT APP LAYOUT ---
st.title("⚽ Advanced Multi-Position Player Analysis Tool")

with st.spinner("Loading and processing data for all leagues... This may take a moment."):
    processed_data = load_and_process_data()

if 'analysis_run' not in st.session_state:
    st.session_state.analysis_run = False
if 'comparison_players' not in st.session_state:
    st.session_state.comparison_players = []

scouting_tab, comparison_tab = st.tabs(["Scouting Analysis", "Direct Comparison"])

with scouting_tab:
    if processed_data is not None:
        st.sidebar.header("🔍 Scouting Controls")
        
        pos_options = list(POSITIONAL_CONFIGS.keys())
        selected_pos = st.sidebar.selectbox("1. Select a Position to Analyze", pos_options, key="scout_pos")
        
        leagues_and_seasons = processed_data[['league_name', 'season_name']].drop_duplicates().sort_values(by=['league_name', 'season_name'])
        leagues = ["All Leagues"] + sorted(leagues_and_seasons['league_name'].unique())
        
        selected_league = st.sidebar.selectbox("2. Filter by League (Optional)", leagues, key="scout_league")

        if selected_league == "All Leagues":
            seasons = ["All Seasons"]
            selected_season = "All Seasons"
        else:
            seasons = ["All Seasons"] + sorted(leagues_and_seasons[leagues_and_seasons['league_name'] == selected_league]['season_name'].unique())
            selected_season = st.sidebar.selectbox("3. Filter by Season (Optional)", seasons, key="scout_season")

        filtered_pool = processed_data.copy()
        if selected_league != "All Leagues":
            filtered_pool = filtered_pool[filtered_pool['league_name'] == selected_league]
        if selected_season != "All Seasons":
            filtered_pool = filtered_pool[filtered_pool['season_name'] == selected_season]

        config = POSITIONAL_CONFIGS[selected_pos]
        archetypes = config["archetypes"]
        position_pool = filtered_pool[filtered_pool['primary_position'].isin(config['positions'])]
        
        player_name_input = st.sidebar.text_input("4. Enter Target Player's Full Name", placeholder="e.g., Harry Kane", key="scout_player")
        
        search_mode = st.sidebar.radio("5. Select Search Mode", ('Find Similar Players', 'Find Potential Upgrades'), key='scout_mode')
        search_mode_logic = 'upgrade' if search_mode == 'Find Potential Upgrades' else 'similar'

        if st.sidebar.button("Analyze Player", type="primary", key="scout_analyze"):
            st.session_state.analysis_run = True
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

        if st.session_state.analysis_run:
            if 'target_player' in st.session_state and st.session_state.target_player is not None:
                tp = st.session_state.target_player
                dna_df = st.session_state.dna_df
                matches = st.session_state.matches

                st.header(f"Analysis for: {tp['player_name']}")
                st.subheader(f"Detected Archetype: {st.session_state.detected_archetype}")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.dataframe(dna_df.reset_index(drop=True), hide_index=True)
                with col2:
                    st.write(f"**Description**: {archetypes[st.session_state.detected_archetype]['description']}")

                st.subheader(f"Top 10 Matches ({search_mode})")
                if not matches.empty:
                    display_cols = ['player_name', 'age', 'team_name', 'league_name']
                    score_col = 'upgrade_score' if search_mode_logic == 'upgrade' else 'similarity_score'
                    display_cols.insert(2, score_col)
                    
                    matches_display = matches.head(10)[display_cols].copy()
                    matches_display[score_col] = matches_display[score_col].round(1)
                    st.dataframe(matches_display.rename(columns=lambda c: c.replace('_', ' ').title()), hide_index=True)
                else:
                    st.warning("No players found matching the criteria for the selected filters.")
                    
            elif 'suggestions' in st.session_state and st.session_state.suggestions is not None:
                st.warning(f"Player '{player_name_input}' not found. Did you mean one of these?")
                for p in st.session_state.suggestions:
                    st.write(f"- {p['player_name']} ({p['team_name']})")
        else:
            st.info("Select filters and enter a player's name in the sidebar to begin analysis.")
            
with comparison_tab:
    st.header("Multi-Player Direct Comparison")

    if processed_data is not None:
        leagues_and_seasons = processed_data[['league_name', 'season_name']].drop_duplicates().sort_values(by=['league_name', 'season_name'])
        leagues = leagues_and_seasons['league_name'].unique()

        # --- NEW: Section to add players to the comparison ---
        with st.container(border=True):
            st.subheader("Add a Player to Comparison")
            
            # New League -> Player -> Season selection logic
            selected_league = st.selectbox("Select League", leagues, key="comp_league", index=None, placeholder="Choose a league")
            if selected_league:
                league_df = processed_data[processed_data['league_name'] == selected_league]
                players = sorted(league_df['player_name'].dropna().unique())
                selected_player_name = st.selectbox("Select Player", players, key="comp_player", index=None, placeholder="Choose a player")
                
                if selected_player_name:
                    player_seasons = sorted(league_df[league_df['player_name'] == selected_player_name]['season_name'].dropna().unique())
                    selected_season = st.selectbox("Select Season", player_seasons, key="comp_season")
                    
                    if st.button("Add Player", type="primary"):
                        player_instance = processed_data[
                            (processed_data['player_name'] == selected_player_name) & 
                            (processed_data['season_name'] == selected_season) &
                            (processed_data['league_name'] == selected_league)
                        ]
                        if not player_instance.empty:
                            st.session_state.comparison_players.append(player_instance.iloc[0])
                            st.rerun()

        st.divider()

        # --- NEW: Display currently selected players and allow removal ---
        st.subheader("Current Comparison")
        if not st.session_state.comparison_players:
            st.info("Add one or more players using the selection box above to start a comparison.")
        else:
            player_cols = st.columns(len(st.session_state.comparison_players))
            for i, player_data in enumerate(st.session_state.comparison_players):
                with player_cols[i]:
                    st.markdown(f"**{player_data['player_name']}**")
                    st.markdown(f"*{player_data['team_name']}*")
                    st.markdown(f"`{player_data['season_name']}`")
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.comparison_players.pop(i)
                        st.rerun()

        st.divider()
        
        # --- NEW: Display radar charts for all selected players ---
        if st.session_state.comparison_players:
            st.subheader("Radar Charts")
            
            radar_pos_options = list(POSITIONAL_CONFIGS.keys())
            selected_radar_pos = st.selectbox("Select Radar Set to Use for Comparison", radar_pos_options)
            
            radars_to_show = POSITIONAL_CONFIGS[selected_radar_pos]['radars']
            
            # Create a main column for each player in the comparison
            main_cols = st.columns(len(st.session_state.comparison_players))
            
            for i, player in enumerate(st.session_state.comparison_players):
                with main_cols[i]:
                    st.markdown(f"#### {player['player_name']}")
                    # Display all 6 radars for this player
                    for radar_name, radar_config in radars_to_show.items():
                        fig = create_enhanced_radar_chart(player, None, radar_config)
                        st.pyplot(fig, use_container_width=True)
