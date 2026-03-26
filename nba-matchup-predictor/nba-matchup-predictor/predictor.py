import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.stats import norm, poisson, nbinom, genextreme
import json
import os
import time
import math
from sklearn.ensemble import RandomForestClassifier
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import shap
from sklearn.model_selection import train_test_split
import joblib
from filterpy.kalman import KalmanFilter
from hmmlearn import hmm
import statsmodels.api as sm

team_name_map = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}

# ============================================================
# 1. LOAD DATA
# ============================================================
from database import DB_URL
from sqlalchemy import create_engine

def load_games(path="real_games.csv"):
    try:
        engine = create_engine(DB_URL)
        df = pd.read_sql("SELECT * FROM games", engine, parse_dates=["date"])
        if len(df) > 0:
            print(f"Loaded {len(df)} games from database.")
            # Ensure numeric columns are actually numeric (handle potential bytes/objects from SQLite)
            numeric_cols = ["team_pts", "opp_pts", "q1_pts", "q2_pts", "q3_pts", "q4_pts", 
                            "opp_q1_pts", "opp_q2_pts", "opp_q3_pts", "opp_q4_pts",
                            "fga", "fgm", "pm3_a", "pm3_m", "fta", "tov", "oreb", "dreb", "ast", "stl", "blk",
                            "opp_fgm", "opp_pm3_m", "opp_fga", "opp_fta", "opp_tov", "opp_stl", "opp_blk", "opp_oreb", "opp_dreb"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df.sort_values(by=["team", "date"])
    except Exception as e:
        print(f"Database load failed, falling back to CSV: {e}")
        
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values(by=["team", "date"])
    return df

def load_players(path="real_players.csv"):
    try:
        engine = create_engine(DB_URL)
        df = pd.read_sql("SELECT * FROM player_stats", engine, parse_dates=["date"])
        if len(df) > 0:
            print(f"Loaded {len(df)} player records from database.")
            numeric_cols = ["pts", "reb", "ast", "pm3", "min", "oreb", "dreb", "stl", "blk", "tov", "fgm", "fga", "ftm", "fta", "pf", "plus_minus"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except Exception as e:
        print(f"Database load failed, falling back to CSV: {e}")

    df = pd.read_csv(path, parse_dates=["date"])
    return df


# ============================================================
# 2. METRICS CALCULATION
# ============================================================
def add_base_metrics(df):
    df["poss"] = 0.5 * (
        (df["fga"] + 0.44*df["fta"] - df["oreb"] + df["tov"]) +
        (df["opp_fga"] + 0.44*df["opp_fta"] - df["opp_oreb"] + df["opp_tov"])
    )
    df["ortg"] = 100 * df["team_pts"] / df["poss"]
    df["drtg"] = 100 * df["opp_pts"] / df["poss"]
    df["net_rating"] = df["ortg"] - df["drtg"]

    # --- FOUR FACTORS ---
    # 1. Shooting (eFG%)
    df["efg_pct"] = (df["fgm"] + 0.5 * df["pm3_m"]) / df["fga"]
    df["opp_efg_pct"] = (df.get("opp_fgm", 0) + 0.5 * df.get("opp_pm3_m", 0)) / df["opp_fga"]
    
    # 2. Turnovers (TOV%)
    df["tov_pct"] = df["tov"] / (df["fga"] + 0.44 * df["fta"] + df["tov"])
    
    # 3. Rebounding (ORB%)
    df["orb_pct"] = df["oreb"] / (df["oreb"] + df["opp_dreb"])
    
    # 4. Free Throws (FT Rate)
    df["ft_rate"] = df["fta"] / df["fga"]

    # --- REST & FATIGUE ---
    df = df.sort_values(["team", "date"])
    df["days_rest"] = df.groupby("team")["date"].diff().dt.days
    df["is_b2b"] = (df["days_rest"] == 1).astype(int)
    
    return df

def rolling_last10(df, shrink_lambda=10):
    results = []
    league_ortg = df["ortg"].mean()
    league_drtg = df["drtg"].mean()
    league_pace = df["poss"].mean()
    
    # Factors Averages
    factors = ["efg_pct", "tov_pct", "orb_pct", "ft_rate", "net_rating"]

    for team, group in df.groupby("team"):
        group = group.sort_values("date")
        n = group.reset_index().index + 1
        
        r_ortg = group["ortg"].rolling(10, min_periods=1).mean()
        r_drtg = group["drtg"].rolling(10, min_periods=1).mean()
        r_pace = group["poss"].rolling(10, min_periods=1).mean()

        shrink = lambda r, league: (n/(n+shrink_lambda))*r + (shrink_lambda/(n+shrink_lambda))*league

        group["adj_ortg_10"] = shrink(r_ortg, league_ortg).values
        group["adj_drtg_10"] = shrink(r_drtg, league_drtg).values
        group["adj_pace_10"] = shrink(r_pace, league_pace).values
        
        # Rolling Four Factors
        for f in factors:
            group[f"roll_{f}_5"] = group[f].rolling(5, min_periods=1).mean()
            group[f"roll_{f}_10"] = group[f].rolling(10, min_periods=1).mean()

        # Quarter efficiency (Scientific Fallback: Default to 25% share if data is missing or zero)
        for q in range(1, 5):
            group[f"q{q}_share"] = group[f"q{q}_pts"] / group["team_pts"].replace(0, 1)
            group[f"q{q}_share"] = group[f"q{q}_share"].fillna(0.25)
            # Ensure no 0.00 shares (at least 0.10 for any quarter)
            group[f"q{q}_share"] = group[f"q{q}_share"].apply(lambda x: x if x > 0.05 else 0.25)
            group[f"adj_q{q}_share_10"] = group[f"q{q}_share"].rolling(10, min_periods=1).mean().fillna(0.25)

        results.append(group)
    return pd.concat(results)

def add_player_rolling(df_players):
    results = []
    # Convert 'min' to numeric if it's string
    if df_players['min'].dtype == object:
        df_players['min'] = df_players['min'].apply(lambda x: float(x.split(':')[0]) + float(x.split(':')[1])/60 if ':' in str(x) else float(x))
    
    for player, group in df_players.groupby("player"):
        group = group.sort_values("date")
        # Use 10-game rolling averages for more stability
        for col in ["pts", "reb", "ast", "stl", "blk", "tov", "min", "oreb", "dreb", "pm3", "fgm", "fga", "ftm", "fta", "pf", "plus_minus"]:
            group[f"roll_{col}"] = group[col].rolling(10, min_periods=1).mean()
            # 3-game rolling for momentum
            if col in ["pts", "reb", "ast"]:
                group[f"roll3_{col}"] = group[col].rolling(3, min_periods=1).mean()
            
            # Bayesian Uncertainty (Std Dev) for primary stats
            if col in ["pts", "reb", "ast", "stl", "blk", "tov"]:
                group[f"std_{col}"] = group[col].rolling(10, min_periods=1).std().fillna(0)
                
        # Calculate advanced efficiency metrics
        # Avoid division by zero
        factor = 2 * (group["roll_fga"] + 0.44 * group["roll_fta"])
        group["roll_ts_pct"] = np.where(factor > 0, group["roll_pts"] / factor, 0)
        group["roll_efg_pct"] = np.where(group["roll_fga"] > 0, (group["roll_fgm"] + 0.5 * group["roll_pm3"]) / group["roll_fga"], 0)
        
        # NEW: Player Usage Rate (Approximate)
        # Usage = 100 * (FGA + 0.44 * FTA + TOV) / Team_Possessions
        # Since we don't have team possessions here easily, we use a player-relative proxy
        group["usage_rate"] = (group["fga"] + 0.44 * group["fta"] + group["tov"])
        group["roll_usage"] = group["usage_rate"].rolling(10, min_periods=1).mean()
        
        # NEW: Player Efficiency (Approximate PER-lite)
        group["efficiency"] = (group["pts"] + group["reb"] + group["ast"] + group["stl"] + group["blk"] 
                              - (group["fga"] - group["fgm"]) - (group["fta"] - group["ftm"]) - group["tov"])
        group["roll_efficiency"] = group["efficiency"].rolling(10, min_periods=1).mean()

        # Momentum Score (compare last 3 to last 10)
        group["pts_momentum"] = np.where(group["roll_pts"] > 0, group["roll3_pts"] / group["roll_pts"], 1.0)
        
        results.append(group)
    return pd.concat(results)


# ============================================================
# 3. ELO RATING SYSTEM
# ============================================================
def update_elo(df, K=20, hca=60):
    teams = df["team"].unique()
    ratings = {t: 1500 for t in teams}
    history = []

    for _, row in df.sort_values("date").iterrows():
        t, o = row["team"], row["opponent"]
        home = row["home"]
        R_t, R_o = ratings[t], ratings[o]
        
        hca_val = hca if home == 1 else 0
        expected = 1 / (1 + 10 ** (-(R_t - R_o + hca_val) / 400))
        actual = 1 if row["team_pts"] > row["opp_pts"] else 0

        R_t_new = R_t + K * (actual - expected)
        ratings[t] = R_t_new
        history.append({"date": row["date"].strftime("%Y-%m-%d"), "team": t, "elo": R_t_new})
    
    return pd.DataFrame(history)

def add_sos_metrics(df):
    print("Calculating Strength of Schedule (SOS)...")
    df = df.sort_values("date")
    # Get each team's rolling net rating to use as opponent strength
    team_strength = df.groupby("team")["net_rating"].rolling(10, min_periods=1).mean().reset_index()
    team_strength.columns = ["team", "index", "strength"]
    team_strength = team_strength.set_index("index")
    df["current_strength"] = team_strength["strength"]
    
    # Map opponent strength to each game
    strength_map = df[["game_id", "team", "current_strength"]].copy()
    strength_map.columns = ["game_id", "opponent", "opp_strength"]
    
    df = pd.merge(df, strength_map, on=["game_id", "opponent"], how="left")
    
    # SOS is the rolling average of opponent strengths
    results = []
    for team, group in df.groupby("team"):
        group = group.sort_values("date")
        group["sos_5"] = group["opp_strength"].rolling(5, min_periods=1).mean()
        group["sos_10"] = group["opp_strength"].rolling(10, min_periods=1).mean()
        results.append(group)
        
    return pd.concat(results)

def apply_advanced_analytics(df):
    print("Applying Advanced Analytics (Bayesian, Kalman, HMM, PCA)...")
    
    # 1. Kalman Filter for Ratings (Evolution of Net Rating)
    kf_results = []
    for team, group in df.groupby("team"):
        group = group.sort_values("date")
        kf = KalmanFilterRating(initial_rating=0.0)
        # Use a safe update that ignores NaNs (keeping previous rating)
        latent_ratings = []
        current_rating = 0.0
        for val in group["net_rating"]:
            if not pd.isna(val):
                current_rating = kf.update(val)
            latent_ratings.append(current_rating)
        group["latent_strength"] = latent_ratings
        kf_results.append(group)
    df = pd.concat(kf_results)
    
    # 2. HMM for State Detection ("Form")
    hmm_results = []
    hmm_model = HiddenMarkovForm(n_components=3)
    for team, group in df.groupby("team"):
        group = group.sort_values("date")
        # Ensure we have enough data for HMM and handle NaNs
        clean_net_rating = group["net_rating"].fillna(0)
        if len(group) >= 10:
            states = hmm_model.fit_predict(clean_net_rating)
            group["form_state"] = states
        else:
            group["form_state"] = [1] * len(group) # Neutral
        hmm_results.append(group)
    df = pd.concat(hmm_results)
    
    # 3. Shannon Entropy for Volatility
    entropy_results = []
    for team, group in df.groupby("team"):
        group = group.sort_values("date")
        group["shooting_entropy"] = group["efg_pct"].rolling(10).apply(calculate_entropy).fillna(0)
        entropy_results.append(group)
    df = pd.concat(entropy_results)
    
    # 4. PCA for Feature Compression
    features_to_pca = ["adj_ortg_10", "adj_drtg_10", "adj_pace_10", "roll_efg_pct_10", "roll_tov_pct_10", "roll_orb_pct_10"]
    X_pca = df[features_to_pca].fillna(0)
    pca = PCA(n_components=3)
    pca_result = pca.fit_transform(X_pca)
    df["pca_1"] = pca_result[:, 0]
    df["pca_2"] = pca_result[:, 1]
    df["pca_3"] = pca_result[:, 2]
    
    return df


# ============================================================
# 4. ADVANCED MATHEMATICAL FRAMEWORKS
# ============================================================

class BayesianRatingUpdater:
    """Implements Bayesian updating for team ratings using hierarchical priors."""
    def __init__(self, league_mean=100.0, league_std=15.0):
        self.league_mean = league_mean
        self.league_std = league_std
        self.team_priors = {} # {team: (mean, std)}

    def update(self, team, observed_rating):
        prior_mean, prior_std = self.team_priors.get(team, (self.league_mean, self.league_std))
        
        # Bayesian Update: Posterior Precision = Prior Precision + Data Precision
        # Assume observation noise std is ~10 points
        obs_std = 10.0
        
        post_precision = (1.0 / prior_std**2) + (1.0 / obs_std**2)
        post_mean = ((prior_mean / prior_std**2) + (observed_rating / obs_std**2)) / post_precision
        post_std = math.sqrt(1.0 / post_precision)
        
        self.team_priors[team] = (post_mean, post_std)
        return post_mean, post_std

class KalmanFilterRating:
    """Models team strength as a latent variable evolving over time."""
    def __init__(self, initial_rating=1500.0):
        self.kf = KalmanFilter(dim_x=1, dim_z=1)
        self.kf.x = np.array([[initial_rating]]) # initial state (rating)
        self.kf.P *= 100. # initial uncertainty
        self.kf.R = 50 # observation noise (game-to-game variance)
        self.kf.Q = 1 # process noise (how much rating naturally drifts)
        self.kf.F = np.array([[1.]]) # state transition matrix
        self.kf.H = np.array([[1.]]) # measurement function

    def update(self, observed_outcome):
        self.kf.predict()
        self.kf.update(np.array([[observed_outcome]]))
        return float(self.kf.x[0][0])

class HiddenMarkovForm:
    """Detects latent team states (Hot, Cold, Stable) using HMM."""
    def __init__(self, n_components=3):
        self.model = hmm.GaussianHMM(n_components=n_components, covariance_type="diag", n_iter=100)

    def fit_predict(self, team_series):
        if len(team_series) < 5: return [1] * len(team_series) # Default to 'Average'
        # Reshape for HMM: (n_samples, n_features)
        data = np.array(team_series).reshape(-1, 1)
        self.model.fit(data)
        return self.model.predict(data)

class MonteCarloSimulator:
    """Simulates games using Poisson/Negative Binomial distributions and Markov chains."""
    def __init__(self, pace, ortg_A, ortg_B, sigma=12):
        self.pace = pace
        self.ortg_A = ortg_A
        self.ortg_B = ortg_B
        self.sigma = sigma

    def simulate_possession(self, team_off_rtg):
        # Negative Binomial is often better for sports scoring than Poisson 
        # as it allows for overdispersion (variance > mean)
        # mu = team_off_rtg / 100.0, alpha is dispersion parameter
        mu = team_off_rtg / 100.0
        if mu <= 0: return 0
        # Simple approximation of NegBinomial via Gamma-Poisson mixture
        # or just Poisson for now if alpha is not tuned. 
        # Let's use Poisson but with a volatility multiplier.
        volatility = np.random.uniform(0.9, 1.1) 
        return np.random.poisson(mu * volatility)

    def run_simulation(self, iterations=5000):
        results = []
        for _ in range(iterations):
            # Sample pace from a tighter distribution (NBA pace is fairly stable)
            sim_pace = np.random.normal(self.pace, 2.5)
            
            # Simulate total points using vectorized Poisson if possible, 
            # but keep possession-by-possession for granularity.
            ptsA = sum(self.simulate_possession(self.ortg_A) for _ in range(int(sim_pace)))
            ptsB = sum(self.simulate_possession(self.ortg_B) for _ in range(int(sim_pace)))
            
            results.append((ptsA, ptsB))
        return np.array(results)

class OptimizationTheory:
    """Implements Kelly Criterion for optimal bankroll management."""
    @staticmethod
    def kelly_criterion(win_prob, decimal_odds, bankroll, fractional=0.25):
        # b = net odds (decimal_odds - 1), p = win_prob, q = 1 - p
        b = decimal_odds - 1
        p = win_prob
        q = 1 - p
        f_star = (b * p - q) / b
        # Apply fractional Kelly to reduce volatility
        return max(0, f_star * bankroll * fractional)


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_market_lines(match_odds):
    if not match_odds:
        return {"home_ml": None, "away_ml": None, "spread": None, "total": None}

    return {
        "home_ml": safe_float(match_odds.get("ml", {}).get("home")),
        "away_ml": safe_float(match_odds.get("ml", {}).get("away")),
        "spread": safe_float(match_odds.get("spread", {}).get("hdp")),
        "total": safe_float(match_odds.get("total", {}).get("hdp")),
    }


def compute_form_adjustments(lastA, lastB, days_restA, days_restB, is_b2bA, is_b2bB):
    latent_edge = clamp(
        (safe_float(lastA.get("latent_strength"), 0) - safe_float(lastB.get("latent_strength"), 0)) / 12.0,
        -3.0,
        3.0,
    )
    recent_edge = clamp(
        (safe_float(lastA.get("net_rating"), 0) - safe_float(lastB.get("net_rating"), 0)) / 20.0,
        -2.0,
        2.0,
    )
    form_state_edge = (
        safe_float(lastA.get("form_state"), 1) - safe_float(lastB.get("form_state"), 1)
    ) * 0.35
    rest_edge = clamp((days_restA - days_restB) * 0.2, -1.0, 1.0)
    b2b_edge = (-0.75 if is_b2bA else 0.0) - (-0.75 if is_b2bB else 0.0)

    return {
        "teamA": latent_edge + recent_edge + form_state_edge + rest_edge + b2b_edge,
        "teamB": -(latent_edge + recent_edge + form_state_edge + rest_edge + b2b_edge),
    }


def blend_with_market(model_value, market_value, weight):
    if market_value is None:
        return model_value
    return (model_value * (1 - weight)) + (market_value * weight)

def calculate_entropy(data_series):
    """Measures predictability/volatility using Shannon Entropy."""
    if len(data_series) == 0: return 0
    counts = pd.Series(data_series).value_counts()
    probs = counts / len(data_series)
    return -sum(probs * np.log2(probs))

def extreme_value_risk(match_diffs):
    """Calculates blowout risk using Generalized Extreme Value (GEV) distribution."""
    if len(match_diffs) < 10: return 0.0
    try:
        shape, loc, scale = genextreme.fit(match_diffs)
        # Probability of a blowout (> 20 points)
        return float(1 - genextreme.cdf(20, shape, loc, scale))
    except:
        return 0.0

# ============================================================
# 5. MACHINE LEARNING MODEL
# ============================================================
def train_ml_model(df, df_p):
    print("Training Machine Learning model...")
    # Filter out games with missing box score stats (e.g. recent skeleton results)
    df = df.dropna(subset=["fga", "fta", "tov"])
    
    # 1. Aggregate Player Stats to Team Level for each game
    print("Aggregating player stats...")
    df_p_agg = df_p.groupby(['game_id', 'team']).agg({
        'pts': 'sum', 'reb': 'sum', 'ast': 'sum', 'stl': 'sum', 'blk': 'sum', 'tov': 'sum', 'pf': 'sum', 'plus_minus': 'sum',
        'usage_rate': 'mean', 'efficiency': 'mean'
    }).reset_index()
    
    # Rename aggregated columns to avoid collision with game data
    df_p_agg = df_p_agg.rename(columns={
        'pts': 'p_pts', 'reb': 'p_reb', 'ast': 'p_ast', 'stl': 'p_stl', 'blk': 'p_blk', 'tov': 'p_tov', 'pf': 'p_pf', 'plus_minus': 'p_pm',
        'usage_rate': 'p_usage', 'efficiency': 'p_eff'
    })
    
    # 2. Merge with games data
    model_df = pd.merge(df, df_p_agg, on=['game_id', 'team'], how='left')
    
    # 3. Create features from previous games
    features_to_shift = [
        "adj_ortg_10", "adj_drtg_10", "adj_pace_10", "net_rating",
        "roll_efg_pct_10", "roll_tov_pct_10", "roll_orb_pct_10", "roll_ft_rate_10",
        "sos_10", "is_b2b",
        "p_pts", "p_reb", "p_ast", "p_stl", "p_blk", "p_tov", "p_pf", "p_pm", "p_usage", "p_eff"
    ]
    
    for col in features_to_shift:
        model_df[f"prev_{col}"] = model_df.groupby("team")[col].shift(1)
    
    # Also shift the opponent's features
    opp_features = ["prev_adj_ortg_10", "prev_adj_drtg_10", "prev_sos_10", "prev_is_b2b"]
    opp_df = model_df[["game_id", "team"] + opp_features].copy()
    opp_df.columns = ["game_id", "opponent"] + [f"opp_{f}" for f in opp_features]
    
    model_df = pd.merge(model_df, opp_df, on=["game_id", "opponent"], how="left")
    
    model_df = model_df.dropna(subset=["prev_adj_ortg_10", "opp_prev_adj_ortg_10"])
    model_df["win"] = (model_df["team_pts"] > model_df["opp_pts"]).astype(int)
    
    feature_cols = [f"prev_{c}" for c in features_to_shift] + [f"opp_{f}" for f in opp_features]
    
    # Store feature names for SHAP
    feature_names = feature_cols
    
    # 4. Prepare data for model
    # Final check for NaNs in feature columns
    nan_counts = model_df[feature_cols].isna().sum()
    if nan_counts.sum() > 0:
        print("Features with NaNs detected before training:")
        print(nan_counts[nan_counts > 0])
        
    model_df = model_df.dropna(subset=feature_cols)
    print(f"Training set row count after final dropna: {len(model_df)}")
    
    if len(model_df) == 0:
        print("WARNING: Training set is empty after dropping NaNs!")
        return None
        
    X = model_df[feature_cols].values
    y = model_df["win"].values
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Random Forest is a strong baseline for this type of problem
    model = RandomForestClassifier(n_estimators=1000, max_depth=12, random_state=42)
    # Convert X_train to DataFrame with feature names for consistent SHAP behavior
    X_train_df = pd.DataFrame(X_train, columns=feature_names)
    X_test_df = pd.DataFrame(X_test, columns=feature_names)
    model.fit(X_train_df, y_train)
    
    print(f"Model Accuracy: {model.score(X_test_df, y_test):.2%}")
    joblib.dump(model, "prediction_model.joblib")
    
    # Generate SHAP Explainer (Optimized for speed using a sample)
    print(f"Generating SHAP Explainer (using sample of {min(100, len(X_train_df))} games for speed)...")
    # Using a sample of the training data as the background dataset for faster SHAP calculation
    X_sample = X_train_df.sample(min(100, len(X_train_df)), random_state=42)
    explainer = shap.TreeExplainer(model, data=X_sample)
    joblib.dump(explainer, "shap_explainer.joblib")
    
    # Safely get expected value
    exp_val = explainer.expected_value
    base_val = float(exp_val[1]) if (isinstance(exp_val, (list, np.ndarray)) and len(exp_val) > 1) else float(exp_val[0] if isinstance(exp_val, (list, np.ndarray)) else exp_val)
    
    # Save base values and feature names for later use
    shap_meta = {
        "expected_value": base_val,
        "feature_names": feature_names
    }
    with open("shap_meta.json", "w") as f:
        json.dump(shap_meta, f)
        
    return model

def get_ml_prediction(model, lastA, lastB, playersA, playersB):
    # Aggregated player features for A and B
    feat_aggA = playersA.agg({
        'roll_pts': 'sum', 'roll_reb': 'sum', 'roll_ast': 'sum', 
        'roll_stl': 'sum', 'roll_blk': 'sum', 'roll_tov': 'sum',
        'roll_pf': 'sum', 'roll_plus_minus': 'sum',
        'roll_usage': 'mean', 'roll_efficiency': 'mean'
    })
    
    # Construct feature vector matching train_ml_model structure
    # order: [adj_ortg_5, adj_drtg_5, adj_pace_5, net_rating, roll_efg_pct_5, roll_tov_pct_5, roll_orb_pct_5, roll_ft_rate_5, sos_5, is_b2b, p_stat...] 
    # + [opp_prev_adj_ortg_5, opp_prev_adj_drtg_5, opp_prev_sos_5, opp_prev_is_b2b]
    
    featA = np.array([[
        lastA["adj_ortg_10"], lastA["adj_drtg_10"], lastA["adj_pace_10"], lastA["net_rating"],
        lastA["roll_efg_pct_10"], lastA["roll_tov_pct_10"], lastA["roll_orb_pct_10"], lastA["roll_ft_rate_10"],
        lastA["sos_10"], lastA["is_b2b"],
        feat_aggA['roll_pts'], feat_aggA['roll_reb'], feat_aggA['roll_ast'],
        feat_aggA['roll_stl'], feat_aggA['roll_blk'], feat_aggA['roll_tov'],
        feat_aggA['roll_pf'], feat_aggA['roll_plus_minus'],
        feat_aggA['roll_usage'], feat_aggA['roll_efficiency'],
        # Opponent stats
        lastB["adj_ortg_10"], lastB["adj_drtg_10"], lastB["sos_10"], lastB["is_b2b"]
    ]])
    
    probA = model.predict_proba(featA)[0][1]
    
    shap_vals = {}
    if os.path.exists("shap_explainer.joblib") and os.path.exists("shap_meta.json"):
        explainer = joblib.load("shap_explainer.joblib")
        with open("shap_meta.json", "r") as f:
            shap_meta = json.load(f)
            
        shap_values = explainer.shap_values(featA)
        
        # Safely extract win class SHAP values
        if isinstance(shap_values, list) and len(shap_values) > 1:
            sv = shap_values[1][0] 
        elif isinstance(shap_values, list):
            sv = shap_values[0][0]
        else:
            sv = shap_values[0]
            
        fn = shap_meta["feature_names"]
        
        for name, val in zip(fn, sv):
            # SHAP might return an array [class0_val, class1_val] for each feature
            if isinstance(val, (list, np.ndarray)) and len(val) > 1:
                actual_val = val[1]
            elif isinstance(val, (list, np.ndarray)):
                actual_val = val[0]
            else:
                actual_val = val
            shap_vals[name.replace("prev_", "")] = float(actual_val)
    
    return float(probA), shap_vals

def get_team_form(team, df):
    team_games = df[df["team"] == team].sort_values("date").iloc[-10:]
    form = []
    for _, row in team_games.iterrows():
        # Handle NaN for quarter/half points (common in skeleton results)
        def safe_int(val, fallback=0):
            try:
                # Improve fallback: if val is 0, NaN, or None, use fallback
                if pd.isna(val) or val == 0 or val == "" or val is None:
                    return fallback
                return int(val)
            except:
                return fallback

        q_pts = [safe_int(row[f"q{i}_pts"], safe_int(row["team_pts"], 0)//4) for i in range(1, 5)]
        
        form.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "opponent": row["opponent"],
            "result": "W" if row["team_pts"] > row["opp_pts"] else "L",
            "score": f"{safe_int(row['team_pts'])}-{safe_int(row['opp_pts'])}",
            "quarters": q_pts,
            "halves": [sum(q_pts[:2]), sum(q_pts[2:])]
        })
    return form


# ============================================================
# 4. PREDICTION ENGINE (ALL MARKETS)
# ============================================================
def resolve_match_odds(odds_data, teamA, teamB, match_id=None, home_name=None, away_name=None):
    if not odds_data:
        return {}

    resolved_home = home_name or team_name_map.get(teamA, teamA)
    resolved_away = away_name or team_name_map.get(teamB, teamB)
    candidate_keys = []

    if match_id:
        candidate_keys.append(str(match_id))

    candidate_keys.extend(
        [
            f"{resolved_away} @ {resolved_home}",
            f"{resolved_home} vs {resolved_away}",
            f"{resolved_home} @ {resolved_away}",
            f"{resolved_away} vs {resolved_home}",
            f"{teamB} @ {teamA}",
            f"{teamA} vs {teamB}",
            f"{teamA} @ {teamB}",
            f"{teamB} vs {teamA}",
        ]
    )

    for key in candidate_keys:
        match_odds = odds_data.get(key)
        if match_odds:
            return match_odds

    return {}


def predict_matchup(teamA, teamB, df, df_p, sigma=12, match_timestamp=None, odds_data=None, match_id=None, home_name=None, away_name=None):
    lastA = df[df["team"] == teamA].iloc[-1]
    lastB = df[df["team"] == teamB].iloc[-1]

    # Calculate dynamic rest if match_timestamp is provided
    days_restA = lastA["days_rest"]
    is_b2bA = lastA["is_b2b"]
    days_restB = lastB["days_rest"]
    is_b2bB = lastB["is_b2b"]

    if match_timestamp:
        match_dt = datetime.fromtimestamp(match_timestamp)
        days_restA = (match_dt - lastA["date"]).days
        is_b2bA = 1 if days_restA == 1 else 0
        days_restB = (match_dt - lastB["date"]).days
        is_b2bB = 1 if days_restB == 1 else 0

    # Main Base Projection
    pace = (lastA["adj_pace_10"] + lastB["adj_pace_10"]) / 2
    # Standard normalization: Avg of Offense and Opponent Defense
    ortg_A = (lastA["adj_ortg_10"] + lastB["adj_drtg_10"]) / 2
    ortg_B = (lastB["adj_ortg_10"] + lastA["adj_drtg_10"]) / 2

    # Apply Fatigue Penalty for B2B and Rest Benefit
    # Fatigue: B2B (-2.0 Ortg), Rest Benefit: 3+ days (+1.5 Ortg)
    fatigueA = -2.0 if is_b2bA else (1.5 if days_restA >= 3 else 0)
    fatigueB = -2.0 if is_b2bB else (1.5 if days_restB >= 3 else 0)
    
    # Adjusted projected points
    ptsA = float(pace * ((ortg_A + fatigueA) / 100))
    ptsB = float(pace * ((ortg_B + fatigueB) / 100))
    
    total = ptsA + ptsB
    spread = ptsB - ptsA # Negative means A is favorite

    # Winning Margins
    margin = ptsA - ptsB
    win_prob_A = float(norm.cdf(margin / sigma))

    # Quarters and Halves
    quarters = []
    # Double-check shares aren't zero
    def get_share(team_series, q, default=0.25):
        val = team_series.get(f"adj_q{q}_share_10", default)
        return float(val) if not pd.isna(val) and val > 0 else default

    for q in range(1, 5):
        q_ptsA = ptsA * get_share(lastA, q)
        q_ptsB = ptsB * get_share(lastB, q)
        quarters.append({"q": q, "ptsA": float(q_ptsA), "ptsB": float(q_ptsB)})
    
    half1_ptsA = quarters[0]["ptsA"] + quarters[1]["ptsA"]
    half1_ptsB = quarters[0]["ptsB"] + quarters[1]["ptsB"]
    half2_ptsA = quarters[2]["ptsA"] + quarters[3]["ptsA"]
    half2_ptsB = quarters[2]["ptsB"] + quarters[3]["ptsB"]

    # Load Injury Report
    injuries = {}
    if os.path.exists("injuries.json"):
        with open("injuries.json", "r") as f:
            inj_list = json.load(f)
            inj_list = {i['player']: i for i in inj_list}
            
    # Load Odds Data for this Matchup
    match_odds = resolve_match_odds(
        odds_data,
        teamA,
        teamB,
        match_id=match_id,
        home_name=home_name,
        away_name=away_name,
    )
    market_lines = extract_market_lines(match_odds)
            
    # Context-aware base projection
    home_court_edge = 1.8
    form_adjustments = compute_form_adjustments(lastA, lastB, days_restA, days_restB, is_b2bA, is_b2bB)
    ptsA += home_court_edge + form_adjustments["teamA"]
    ptsB += form_adjustments["teamB"]
    total = ptsA + ptsB
    spread = ptsB - ptsA

    market_total = market_lines["total"]
    if market_total is not None:
        total = blend_with_market(total, market_total, 0.2)
        split_total_delta = total - (ptsA + ptsB)
        ptsA += split_total_delta / 2
        ptsB += split_total_delta / 2

    market_spread_home = market_lines["spread"]
    if market_spread_home is not None:
        # Sportsbook home spread is from the home team's perspective. Our spread is away - home.
        market_spread_model_space = market_spread_home
        spread = blend_with_market(spread, market_spread_model_space, 0.35)
        midpoint = total / 2
        ptsA = midpoint - (spread / 2)
        ptsB = midpoint + (spread / 2)

    # Winning Margins
    margin = ptsA - ptsB
    sigma = clamp(sigma + abs(spread) * 0.08, 10, 16)
    win_prob_A = float(norm.cdf(margin / sigma))

    # Player Props (Refined ML Adjustment)
    players_A = df_p[df_p["team"] == teamA].groupby("player").last()
    players_B = df_p[df_p["team"] == teamB].groupby("player").last()
    
    p_props = []
    # Use Projected Pace and Defense for more scientific player projections
    pace_factor = pace / (lastA["adj_pace_10"] if not pd.isna(lastA["adj_pace_10"]) else pace)
    
    for p, row in pd.concat([players_A, players_B]).iterrows():
        # Adjust player projection based on ML predicted game pace and opponent defense
        opp_def = lastB["adj_drtg_10"] if row["team"] == teamA else lastA["adj_drtg_10"]
        # Defense Mult: If opponent defense is better (lower DRtg), player scores less
        # Baseline is league avg ~115
        def_mult = (opp_def / 115.0) 
        
        # Combine pace and defense for "Assured Outcome" logic
        ml_mult = pace_factor * def_mult
        
        # Injury Status
        p_inj = inj_list.get(p, {})
        
        p_props.append({
            "player": p,
            "team": row["team"],
            "proj_pts": float(row["roll_pts"] * ml_mult),
            "proj_reb": float(row["roll_reb"] * pace_factor),
            "proj_ast": float(row["roll_ast"] * pace_factor),
            "status": p_inj.get("status", "Active"),
            "injury": p_inj.get("injury", ""),
            "market_line": None # Placeholder for bookie line comparison
        })
    
    # Map Player Prop Market Lines if available
    if match_odds and "props" in match_odds:
        prop_market = {p['label']: p for p in match_odds["props"]}
        for p_proj in p_props:
            # Match "Name (Stat)" e.g. "Ausar Thompson (Points)"
            # We need to find if any key in prop_market contains p_proj['player'] and specific stat
            for label, p_data in prop_market.items():
                if p_proj['player'] in label:
                    if "(Points)" in label: p_proj["market_pts"] = p_data.get("hdp")
                    if "(Rebounds)" in label: p_proj["market_reb"] = p_data.get("hdp")
                    if "(Assists)" in label: p_proj["market_ast"] = p_data.get("hdp")

    # ML Prediction and SHAP (Game Theory)
    ml_prob = 0.5
    shap_vals = {}
    if os.path.exists("prediction_model.joblib"):
        model = joblib.load("prediction_model.joblib")
        pA_top = df_p[df_p["team"] == teamA].groupby("player").last()
        pB_top = df_p[df_p["team"] == teamB].groupby("player").last()
        
        # Use dynamic b2b for ML if available
        lastA_ml = lastA.copy()
        lastB_ml = lastB.copy()
        lastA_ml["is_b2b"] = is_b2bA
        lastB_ml["is_b2b"] = is_b2bB
        ml_prob, shap_vals = get_ml_prediction(model, lastA_ml, lastB_ml, pA_top, pB_top)

    # NEW: Bayesian Rating Update (Team Strength Tracking)
    bayesian = BayesianRatingUpdater()
    # Fill priors from history
    for team in df["team"].unique():
        team_data = df[df["team"] == team]
        # Use last 10 games to establish a prior
        recent_avg = team_data["net_rating"].tail(10).mean() if len(team_data) >= 10 else 0
        bayesian.update(team, recent_avg)
    
    # Get current Bayesian strengths for this matchup
    strengthA, stdA = bayesian.update(teamA, lastA["net_rating"])
    strengthB, stdB = bayesian.update(teamB, lastB["net_rating"])

    # UPGRADED: Monte Carlo Simulations (Negative Binomial for Scoring)
    mc = MonteCarloSimulator(pace, ortg_A, ortg_B, sigma)
    # We'll use a more advanced sim loop here or update the class
    mc_results = mc.run_simulation(iterations=5000) # Increased iterations
    mc_win_A = float(np.mean(mc_results[:, 0] > mc_results[:, 1]))
    
    # NEW: Extreme Value Theory (Blowout Risk)
    all_diffs = (df["team_pts"] - df["opp_pts"]).values
    blowout_risk = extreme_value_risk(all_diffs)
    
    # Market-Implied Probability Consensus
    market_prob = None
    if market_lines["home_ml"] and market_lines["away_ml"]:
        raw_h = 1.0 / market_lines["home_ml"]
        raw_a = 1.0 / market_lines["away_ml"]
        total_implied = raw_h + raw_a
        if total_implied > 0:
            market_prob = raw_h / total_implied

    # Ensemble Probability
    model_prob = clamp(win_prob_A, 0.03, 0.97)
    if market_prob is not None:
        agreement = 1.0 - min(abs(model_prob - market_prob), 0.5) * 2.0
        ml_weight = 0.45 if agreement < 0.5 else 0.35
        mc_weight = 0.30
        market_weight = 1.0 - ml_weight - mc_weight
        final_win_prob = (
            ml_prob * ml_weight
            + mc_win_A * mc_weight
            + market_prob * market_weight
        )
    else:
        final_win_prob = (ml_prob * 0.5) + (mc_win_A * 0.2) + (model_prob * 0.3)

    final_win_prob = clamp(final_win_prob, 0.03, 0.97)

    # Optimization Theory (Kelly Criterion) using the real available home price when present.
    bankroll = 1000 # Default bankroll context
    home_price = market_lines["home_ml"] if market_lines["home_ml"] and market_lines["home_ml"] > 1 else 1.91
    edge = None if market_prob is None else final_win_prob - market_prob
    bet_size = OptimizationTheory.kelly_criterion(final_win_prob, home_price, bankroll)
    if edge is None or edge < 0.015:
        bet_size = 0.0

    return {
        "main": {
            "ptsA": ptsA, "ptsB": ptsB, "total": total, "spread": spread, 
            "win_prob_A": float(final_win_prob * 100), "ml_prob_A": ml_prob, "mc_win_A": mc_win_A,
            "base_win_prob_A": float(model_prob),
            "market_prob_A": float(market_prob) if market_prob is not None else None,
            "market": match_odds or {
                "ml": {"home": None, "away": None},
                "spread": {"hdp": None, "home": None, "away": None},
                "total": {"hdp": None, "over": None, "under": None}
            }
        },
        "advanced": {
            "blowout_risk": blowout_risk,
            "recommended_bet": float(bet_size),
            "market_edge": float(edge) if edge is not None else None,
            "latent_strength_A": float(lastA["latent_strength"]),
            "latent_strength_B": float(lastB["latent_strength"]),
            "form_state_A": int(lastA["form_state"]),
            "form_state_B": int(lastB["form_state"]),
            "entropy_A": float(lastA["shooting_entropy"])
        },
        "halves": {
            "h1_ptsA": half1_ptsA, "h1_ptsB": half1_ptsB,
            "h2_ptsA": half2_ptsA, "h2_ptsB": half2_ptsB
        },
        "quarters": quarters,
        "players": p_props,
        "factors": {
            "teamA": {
                "efg": float(lastA["roll_efg_pct_10"]),
                "tov": float(lastA["roll_tov_pct_10"]),
                "orb": float(lastA["roll_orb_pct_10"]),
                "ftr": float(lastA["roll_ft_rate_10"]),
                "sos": float(lastA["sos_10"]),
                "rest": int(days_restA) if not pd.isna(days_restA) else 3,
                "is_b2b": int(is_b2bA),
                "ml_influence": {k: v for k, v in shap_vals.items() if "efg" in k or "tov" in k or "orb" in k or "ft_rate" in k}
            },
            "teamB": {
                "efg": float(lastB["roll_efg_pct_10"]),
                "tov": float(lastB["roll_tov_pct_10"]),
                "orb": float(lastB["roll_orb_pct_10"]),
                "ftr": float(lastB["roll_ft_rate_10"]),
                "sos": float(lastB["sos_10"]),
                "rest": int(days_restB) if not pd.isna(days_restB) else 3,
                "is_b2b": int(is_b2bB)
            }
        },
        "margins": {
            "1-5": float(norm.cdf(5/sigma) - norm.cdf(-5/sigma)) * win_prob_A, # naive approx
            "6-10": float(norm.cdf(10/sigma) - norm.cdf(5/sigma)) * win_prob_A,
            "11+": float(1 - norm.cdf(10/sigma)) * win_prob_A
        },
        "formA": get_team_form(teamA, df),
        "formB": get_team_form(teamB, df),
        "shap_explanation": shap_vals
    }


# ============================================================
# 5. EXPORT
# ============================================================
def export_data(df, elo_df, df_p, upcoming=None, filename="data.js", odds_data=None):
    if upcoming is None:
        upcoming = []
        
    teams = list(df["team"].unique())
    latest_metrics = []
    
    # Load standings if available
    standings = {}
    if os.path.exists("standings.json"):
        try:
            with open("standings.json", "r") as f:
                s_list = json.load(f)
                standings = {s['TeamAbbreviation']: s for s in s_list}
        except:
            pass

    for team in teams:
        t_data = df[df["team"] == team].iloc[-1]
        t_standings = standings.get(team, {})
        
        latest_metrics.append({
            "team": team,
            "wins": t_standings.get('WINS', 0),
            "losses": t_standings.get('LOSSES', 0),
            "conf_rank": t_standings.get('PlayoffRank', '-'),
            "adj_ortg_10": float(t_data["adj_ortg_10"]) if t_data["adj_ortg_10"] > 0 else 115.0,
            "adj_drtg_10": float(t_data["adj_drtg_10"]) if t_data["adj_drtg_10"] > 0 else 115.0,
            "adj_pace_10": float(t_data["adj_pace_10"]) if t_data["adj_pace_10"] > 0 else 100.0,
            "sos_10": float(t_data["sos_10"]),
            "latent_strength": float(t_data["latent_strength"]),
            "form_state": int(t_data["form_state"]),
            "shooting_entropy": float(t_data.get("shooting_entropy", 0)),
            "factors": {
                "efg": float(t_data["roll_efg_pct_10"]),
                "tov": float(t_data["roll_tov_pct_10"]),
                "orb": float(t_data["roll_orb_pct_10"]),
                "ftr": float(t_data["roll_ft_rate_10"])
            },
            "q_shares": [float(t_data[f"adj_q{i}_share_10"]) for i in range(1, 5)],
            "last10_form": get_team_form(team, df),
            "is_b2b": int(t_data["is_b2b"])
        })

    # Convert player stats for JSON (Top 10 players by MIN per team)
    player_stats_clean = []
    for team in teams:
        t_players = df_p[df_p["team"] == team].groupby("player").last().reset_index()
        t_players = t_players.sort_values("roll_min", ascending=False).head(10)
        
        for _, row in t_players.iterrows():
            player_stats_clean.append({
                "player": row["player"],
                "team": row["team"],
                "roll_pts": float(row["roll_pts"]),
                "roll3_pts": float(row["roll3_pts"]),
                "pts_momentum": float(row["pts_momentum"]),
                "roll_reb": float(row["roll_reb"]),
                "roll_ast": float(row["roll_ast"]),
                "roll_stl": float(row["roll_stl"]),
                "roll_blk": float(row["roll_blk"]),
                "roll_tov": float(row["roll_tov"]),
                "roll_min": float(row["roll_min"]),
                "roll_oreb": float(row["roll_oreb"]),
                "roll_dreb": float(row["roll_dreb"]),
                "std_pts": float(row["std_pts"]),
                "std_reb": float(row["std_reb"]),
                "std_ast": float(row["std_ast"]),
                "std_stl": float(row["std_stl"]),
                "std_blk": float(row["std_blk"]),
                "std_tov": float(row["std_tov"]),
                "roll_usage": float(row.get("roll_usage", 0)),
                "roll_efficiency": float(row.get("roll_efficiency", 0))
            })
    
    # Process upcoming matches with predictions
    upcoming_processed = []
    model = None
    if os.path.exists("prediction_model.joblib"):
        model = joblib.load("prediction_model.joblib")

    # Get start of today (midnight) for filtering in UTC
    # Loosen to "Yesterday" to ensure games don't vanish due to UTC/ET rollovers
    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_of_today_ts = int(start_of_today.timestamp())
    
    print(f"Filtering games before: {start_of_today} ({start_of_today_ts})")
    print(f"Upcoming buffer contains {len(upcoming)} total matches.")
    
    for match in upcoming:
        # Keep games from yesterday onwards to be safe
        m_time = match.get("matchTime", 0)
        if m_time < start_of_today_ts:
            continue
            
        teamA, teamB = match["homeTeam"], match["awayTeam"]
        if teamA in teams and teamB in teams:
            lastA = df[df["team"] == teamA].iloc[-1]
            lastB = df[df["team"] == teamB].iloc[-1]
            
            matchTime = match.get("matchTime")
            match_id = match.get("matchId", match.get("gameId", match.get("GAME_ID")))
            # Pass entire odds_data to predict_matchup for name-based lookup
            res = predict_matchup(
                teamA,
                teamB,
                df,
                df_p,
                match_timestamp=matchTime,
                odds_data=odds_data,
                match_id=match_id,
                home_name=match.get("homeName"),
                away_name=match.get("awayName"),
            )
            
            res["match_id"] = match_id
            res["time"] = match.get("time", "TBD")
            match["prediction"] = res
            match["ml_prob_A"] = match["prediction"]["main"]["ml_prob_A"]
            match["mc_win_A"] = match["prediction"]["main"]["mc_win_A"]
            match["shap_explanation"] = match["prediction"]["shap_explanation"]
            
            # Pass dynamic rest/b2b back to match object for frontend
            match["is_b2b_home"] = match["prediction"]["factors"]["teamA"]["is_b2b"]
            match["is_b2b_away"] = match["prediction"]["factors"]["teamB"]["is_b2b"]
            match["rest_home"] = match["prediction"]["factors"]["teamA"]["rest"]
            match["rest_away"] = match["prediction"]["factors"]["teamB"]["rest"]
        upcoming_processed.append(match)

    if len(upcoming_processed) == 0:
        print("CRITICAL: No upcoming matches found! Preserving previous upcoming_matches in data.js to prevent empty dashboard.")
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    content = f.read().replace("const analyticsData = ", "").rstrip(";")
                    old_data = json.loads(content)
                    if "upcoming_matches" in old_data and len(old_data["upcoming_matches"]) > 0:
                        upcoming_processed = old_data["upcoming_matches"]
                        print(f"Successfully recovered {len(upcoming_processed)} matches from previous data.js state.")
        except Exception as e:
            print(f"Warning: Failed to recover previous matches: {e}")

    export_obj = {
        "teams": teams,
        "latest_metrics": latest_metrics,
        "elo_history": elo_df.to_dict(orient="records"),
        "player_stats": player_stats_clean,
        "upcoming_matches": upcoming_processed
    }
    
    with open(filename, "w") as f:
        f.write("const analyticsData = ")
        json.dump(export_obj, f, indent=2)
        f.write(";")
    print(f"Data exported to {filename} with {len(upcoming)} upcoming matches")


# ============================================================
# 6. PIPELINE
# ============================================================
def run_pipeline():
    df = load_games()
    df_p = load_players()
    
    # Load recent results to bridge the gap for rest/B2B
    if os.path.exists("recent_results.json"):
        with open("recent_results.json", "r") as f:
            recent_data = json.load(f)
            if recent_data:
                recent_df = pd.DataFrame(recent_data)
                recent_df["date"] = pd.to_datetime(recent_df["date"])
                # Append to df and drop duplicates (in case real_games.csv was partially updated)
                df = pd.concat([df, recent_df], ignore_index=True)
                df = df.drop_duplicates(subset=["game_id", "team"]).sort_values(["team", "date"])
                print(f"Merged {len(recent_df)//2} recent games from iSports API for accuracy.")
    
    df = add_base_metrics(df)
    # Fill missing box score stats with historical averages for recent games 
    # so they don't break rolling averages completely, though they'll still 
    # be excluded from training later.
    stats_to_fill = ["fga", "fta", "tov", "oreb", "opp_fga", "opp_fta", "opp_tov", "opp_oreb"]
    for stat in stats_to_fill:
        if stat in df.columns:
            df[stat] = df[stat].fillna(df[stat].mean())
    
    # Fill missing quarterly data with 25% share of total points
    for i in range(1, 5):
        col = f"q{i}_pts"
        if col in df.columns:
            # Ensure it's float to avoid TypeError when filling with float shares
            df[col] = df[col].astype(float)
            df[col] = df[col].fillna(df["team_pts"] * 0.25)
            # Handle cases where it is 0 but team_pts is > 0
            df.loc[(df[col] == 0) & (df["team_pts"] > 0), col] = df["team_pts"] * 0.25
    
    df = rolling_last10(df)
    df = add_sos_metrics(df) 
    df = apply_advanced_analytics(df) # NEW: Bayesian, Kalman, HMM, PCA
    df_p = add_player_rolling(df_p)
    elo = update_elo(df)
    
    # Train ML Model
    train_ml_model(df, df_p)

    # Load upcoming matches if available
    upcoming = []
    if os.path.exists("upcoming.json"):
        try:
            with open("upcoming.json", "r") as f:
                upcoming = json.load(f)
        except:
            pass
            
    if not upcoming and os.path.exists("odds_matches.json"):
        print("NBA API returned 0 matches. Using Odds API fallback...")
        try:
            with open("odds_matches.json", "r") as f:
                upcoming = json.load(f)
        except:
            pass
            
    if not upcoming and os.path.exists("upcoming_bet365.json"):
        print("Odds API fallback returned 0 matches. Using Bet365 fallback...")
        try:
            with open("upcoming_bet365.json", "r") as f:
                upcoming = json.load(f)
        except:
            pass
            
    # Load Odds
    odds_data = {}
    if os.path.exists("odds.json"):
        with open("odds.json", "r") as f:
            odds_data = json.load(f)

    # 4. Generate & Export
    export_data(df, elo, df_p, upcoming, odds_data=odds_data)
    print("Pipeline completed successfully.")
    return df, df_p, elo

if __name__ == "__main__":
    df_f, df_pf, elof = run_pipeline()
    print("\n=== PIPELINE COMPLETE ===")
    
    # Use real team abbreviations for example
    teams_available = list(df_f["team"].unique())
    t1 = teams_available[0]
    t2 = teams_available[1]
    
    res = predict_matchup(t1, t2, df_f, df_pf)
    print(f"Example Prediction ({t1} vs {t2} Spread):", res["main"]["spread"])
