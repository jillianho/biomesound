"""
prediction.py
Gut state trajectory forecasting using lightweight Gaussian Process regression.

No sklearn dependency — GP implemented from scratch with numpy + math.
Designed for small time-series under 200 observations.

Architecture:
  1. SimpleGP: RBF kernel, direct Cholesky solve, auto hyperparameters
  2. event_deltas: physiological response curves for lifestyle events
  3. forecast(): main entry — fits per-parameter GPs, overlays events,
     returns predictions with uncertainty bounds and confidence scores
"""

import math
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Canonical biome state keys
# ---------------------------------------------------------------------------

BIOME_KEYS: list[str] = [
    "diversity_index",
    "inflammation_score",
    "firmicutes_dominance",
    "bacteroidetes_dominance",
    "proteobacteria_bloom",
    "motility_activity",
    "mucosal_integrity",
    "metabolic_energy",
]


# ---------------------------------------------------------------------------
# Event effect library
# ---------------------------------------------------------------------------
# Each effect: {key, delta, peak_s, decay_s}
# Response: linear onset 0 → peak_s, exponential decay beyond peak.

EVENT_EFFECTS: dict[str, list[dict]] = {
    "MEAL": [
        {"key": "firmicutes_dominance", "delta": +0.20, "peak_s": 7_200,  "decay_s": 21_600},
        {"key": "motility_activity",    "delta": +0.30, "peak_s": 3_600,  "decay_s": 10_800},
        {"key": "metabolic_energy",     "delta": +0.25, "peak_s": 3_600,  "decay_s": 14_400},
    ],
    "PROBIOTIC": [
        {"key": "diversity_index",      "delta": +0.15, "peak_s": 14_400, "decay_s": 43_200},
        {"key": "proteobacteria_bloom", "delta": -0.10, "peak_s": 14_400, "decay_s": 43_200},
    ],
    "ANTIBIOTIC": [
        {"key": "diversity_index",      "delta": -0.40, "peak_s": 7_200,  "decay_s": 43_200},
        {"key": "proteobacteria_bloom", "delta": +0.30, "peak_s": 7_200,  "decay_s": 28_800},
        {"key": "mucosal_integrity",    "delta": -0.20, "peak_s": 7_200,  "decay_s": 43_200},
    ],
    "EXERCISE": [
        {"key": "motility_activity",    "delta": +0.25, "peak_s": 1_800,  "decay_s": 7_200},
    ],
    "STRESS": [
        {"key": "inflammation_score",   "delta": +0.20, "peak_s": 3_600,  "decay_s": 14_400},
        {"key": "motility_activity",    "delta": -0.15, "peak_s": 3_600,  "decay_s": 10_800},
    ],
    "SLEEP": [
        {"key": "motility_activity",    "delta": -0.30, "peak_s": 3_600,  "decay_s": 28_800},
        {"key": "mucosal_integrity",    "delta": +0.10, "peak_s": 14_400, "decay_s": 43_200},
    ],
}


# ---------------------------------------------------------------------------
# Physiological response curve
# ---------------------------------------------------------------------------

def _event_response(dt: float, delta: float, peak_s: float, decay_s: float) -> float:
    """
    Effect magnitude at ``dt`` seconds after event onset.

    Shape:
      dt ≤ 0           → 0            (event hasn't happened)
      0 < dt ≤ peak_s  → delta × dt/peak_s          (linear onset)
      dt > peak_s      → delta × exp(-(dt-peak_s)/decay_s)  (exponential decay)
    """
    if dt <= 0.0:
        return 0.0
    if dt <= peak_s:
        return delta * (dt / peak_s)
    return delta * math.exp(-(dt - peak_s) / decay_s)


def compute_event_deltas(
    t_pred: np.ndarray,
    events: list[dict],
) -> dict[str, np.ndarray]:
    """
    Accumulate event-driven deltas at each prediction time step.

    Args:
        t_pred: Prediction timestamps (seconds from t_now=0).
                Positive values are future, negative are past.
        events: List of {type: str, offset_seconds: float} where
                offset_seconds is seconds from now (0 = immediate).

    Returns:
        {biome_key: delta_array} — same length as t_pred.
    """
    deltas: dict[str, np.ndarray] = {k: np.zeros(len(t_pred)) for k in BIOME_KEYS}

    for event in events:
        event_type = event.get("type", "").upper()
        offset_s = float(event.get("offset_seconds", 0.0))
        # event_time relative to t_now=0
        event_time = offset_s

        for eff in EVENT_EFFECTS.get(event_type, []):
            key = eff["key"]
            for i, t in enumerate(t_pred):
                dt = t - event_time
                deltas[key][i] += _event_response(dt, eff["delta"], eff["peak_s"], eff["decay_s"])

    return deltas


# ---------------------------------------------------------------------------
# Gaussian Process — RBF kernel, no sklearn
# ---------------------------------------------------------------------------

def _rbf_kernel_matrix(
    X1: np.ndarray, X2: np.ndarray,
    length_scale: float, signal_var: float,
) -> np.ndarray:
    """
    RBF (squared-exponential) kernel matrix K(X1, X2).

    k(x, x') = signal_var * exp(-||x - x'||² / (2 * l²))

    X1: (n,)  X2: (m,)  →  returns (n, m)
    """
    diff = X1[:, None] - X2[None, :]
    return signal_var * np.exp(-0.5 * diff ** 2 / (length_scale ** 2))


def _auto_length_scale(t_train: np.ndarray) -> float:
    """Heuristic length scale: 4× median inter-observation gap, min 60s."""
    if len(t_train) < 2:
        return 3_600.0
    gaps = np.diff(np.sort(t_train))
    positive_gaps = gaps[gaps > 0]
    if len(positive_gaps) == 0:
        return 3_600.0
    return max(60.0, float(np.median(positive_gaps)) * 4.0)


def _auto_signal_var(y_train: np.ndarray) -> float:
    """Heuristic signal variance: (range/2)² + small floor."""
    if len(y_train) < 2:
        return 0.05
    return max(0.01, (float(np.ptp(y_train)) / 2.0) ** 2 + 0.005)


def gp_predict(
    t_train: np.ndarray,
    y_train: np.ndarray,
    t_test: np.ndarray,
    length_scale: Optional[float] = None,
    noise_var: float = 0.004,
    signal_var: Optional[float] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Gaussian Process regression with RBF kernel.

    Returns: (mean, std) each of shape (m,) for m test points.

    With no observations, returns a uniform prior: mean=0.5, std=0.3.
    """
    n = len(t_train)
    m = len(t_test)

    if n == 0:
        return np.full(m, 0.5), np.full(m, 0.30)

    if length_scale is None:
        length_scale = _auto_length_scale(t_train)
    if signal_var is None:
        signal_var = _auto_signal_var(y_train)

    # Kernel matrices
    K_nn = _rbf_kernel_matrix(t_train, t_train, length_scale, signal_var)
    K_sn = _rbf_kernel_matrix(t_test,  t_train, length_scale, signal_var)

    # Regularised training covariance
    K_nn_r = K_nn + noise_var * np.eye(n) + 1e-9 * np.eye(n)

    # Solve with Cholesky for numerical stability
    try:
        L = np.linalg.cholesky(K_nn_r)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))
        V = np.linalg.solve(L, K_sn.T)          # (n, m)
    except np.linalg.LinAlgError:
        # Fallback: add more jitter and use LU
        K_nn_r += 1e-4 * np.eye(n)
        alpha = np.linalg.solve(K_nn_r, y_train)
        V = np.linalg.solve(K_nn_r, K_sn.T)

    mean = K_sn @ alpha

    # Diagonal of posterior variance
    k_ss_diag = np.full(m, signal_var)
    var = k_ss_diag - np.einsum("ij,ij->j", V, V)
    var = np.maximum(var, 1e-9)

    return mean, np.sqrt(var)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _horizon_confidence(
    t_pred: np.ndarray,
    t_last_obs: float,
    n_observations: int,
    decay_halflife: float = 43_200.0,   # 12 hours
) -> np.ndarray:
    """
    Per-step confidence that decays with prediction horizon and grows with data.

    base = tanh(n_obs / 5)           — saturates at ~1.0 once we have ≥15 obs
    decay = exp(-ln2 × dt / halflife) — halves every decay_halflife seconds

    Result is in [0, 1].
    """
    base = math.tanh(n_observations / 5.0)
    dt = np.maximum(0.0, t_pred - t_last_obs)
    decay = np.exp(-math.log(2) * dt / decay_halflife)
    return np.clip(base * decay, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Main forecasting entry point
# ---------------------------------------------------------------------------

def forecast(
    observations: list[dict],
    horizon_seconds: float = 86_400.0,
    n_steps: int = 48,
    events: Optional[list[dict]] = None,
    t_now: float = 0.0,
) -> dict:
    """
    Forecast gut biome parameters over a future time horizon.

    Args:
        observations:    List of {timestamp: float, biome_state: dict}.
                         timestamp is **absolute** seconds (e.g. Unix time).
                         Observations before t_now are used for conditioning.
        horizon_seconds: Prediction window from t_now (seconds).
        n_steps:         Number of evenly-spaced output steps.
        events:          List of {type: str, offset_seconds: float} lifestyle
                         events. offset_seconds is seconds from t_now.
        t_now:           Reference time in same units as observation timestamps.

    Returns:
        {
          "t_steps":         list[float]  — seconds from t_now (0 … horizon),
          "predictions":     {key: {"mean": [..], "lower": [..], "upper": [..], "std": [..]}},
          "confidence":      list[float]  — per-step overall confidence [0, 1],
          "events_applied":  list[str],
          "n_observations":  int,
        }
    """
    if events is None:
        events = []

    # Prediction grid: 0 to horizon (relative to t_now)
    t_pred = np.linspace(0.0, horizon_seconds, max(2, n_steps))

    # Convert observations to relative time
    t_train_list: list[float] = []
    y_train_raw: dict[str, list[float]] = {k: [] for k in BIOME_KEYS}

    for obs in observations:
        ts_rel = float(obs.get("timestamp", t_now)) - t_now
        bs = obs.get("biome_state", {})
        t_train_list.append(ts_rel)
        for k in BIOME_KEYS:
            y_train_raw[k].append(float(bs.get(k, 0.5)))

    t_train = np.array(t_train_list, dtype=float)
    n_obs = len(t_train)
    t_last = float(t_train.max()) if n_obs > 0 else 0.0

    # Event-driven deltas
    event_deltas = compute_event_deltas(t_pred, events)

    # Horizon confidence (used to inflate uncertainty far into the future)
    confidence = _horizon_confidence(t_pred, t_last, n_obs)

    predictions: dict[str, dict] = {}

    for k in BIOME_KEYS:
        y_arr = np.array(y_train_raw[k], dtype=float) if n_obs > 0 else np.array([])

        gp_mean, gp_std = gp_predict(t_train, y_arr, t_pred)

        # Overlay event effects
        adjusted_mean = gp_mean + event_deltas[k]
        adjusted_mean = np.clip(adjusted_mean, 0.0, 1.0)

        # Total uncertainty: GP std + horizon-decay inflation
        horizon_inflation = (1.0 - confidence) * 0.20
        total_std = np.sqrt(gp_std ** 2 + horizon_inflation ** 2)
        total_std = np.clip(total_std, 0.0, 0.50)

        lower = np.clip(adjusted_mean - 1.96 * total_std, 0.0, 1.0)
        upper = np.clip(adjusted_mean + 1.96 * total_std, 0.0, 1.0)

        predictions[k] = {
            "mean":  [round(v, 4) for v in adjusted_mean.tolist()],
            "lower": [round(v, 4) for v in lower.tolist()],
            "upper": [round(v, 4) for v in upper.tolist()],
            "std":   [round(v, 4) for v in total_std.tolist()],
        }

    return {
        "t_steps":        [round(v, 1) for v in t_pred.tolist()],
        "predictions":    predictions,
        "confidence":     [round(v, 4) for v in confidence.tolist()],
        "events_applied": [str(e.get("type", "")) for e in events],
        "n_observations": n_obs,
    }
