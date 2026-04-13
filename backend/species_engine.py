"""
species_engine.py
Maps individual bacterial species to unique instruments per the Microbiome Sound Bible.

Provides:
  - SPECIES_CATALOG: 14 species with instrument/synthesis metadata
  - compute_active_instruments(biome_state, h2_ppm, ch4_ppm)
  - build_bible_synth_params(biome_state, h2_ppm, ch4_ppm)
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Species catalog
# ---------------------------------------------------------------------------
# Fields:
#   id                   — unique snake_case identifier
#   name                 — display name
#   role                 — "good" | "bad" | "archaea"
#   instrument           — human-readable instrument name
#   freq_base            — fundamental frequency in Hz
#   freq_range           — [lo, hi] Hz; sweep range for dynamic voices
#   oscillator           — "sine" | "triangle" | "sawtooth" | "square" | "noise"
#   vibrato              — {"rate": Hz, "depth": fraction of freq} or None
#   percussive           — True → rhythmic hits synced to tempo (R. bromii)
#   sporadic             — True → occasional random bursts (C. difficile, F. nucleatum)
#   detune               — Hz offset for bad-bacteria dissonance
#   activation_key       — biome_state key driving on/off
#                          special values:
#                            "compound_dpiger" → motility ≤ 0.3 AND inflammation ≥ 0.3
#   activation_threshold — numeric threshold for activation
#   activation_direction — "high" (value ≥ threshold) | "low" (value ≤ threshold)
#   amplitude_key        — biome_state key driving voice amplitude
#   amplitude_invert     — if True, amplitude = 1 − value (for "low is loud" cases)

SPECIES_CATALOG: list[dict] = [
    # ── Good bacteria ──────────────────────────────────────────────────────
    {
        "id":                   "f_prausnitzii",
        "name":                 "F. prausnitzii",
        "role":                 "good",
        "instrument":           "First Violin",
        "freq_base":            293.0,
        "freq_range":           [293.0, 370.0],
        "oscillator":           "sine",
        "vibrato":              {"rate": 5.5, "depth": 0.006},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "mucosal_integrity",
        "activation_threshold": 0.40,
        "activation_direction": "high",
        "amplitude_key":        "mucosal_integrity",
        "amplitude_invert":     False,
    },
    {
        "id":                   "b_longum",
        "name":                 "B. longum",
        "role":                 "good",
        "instrument":           "Piano",
        "freq_base":            261.0,
        "freq_range":           [261.0, 523.0],
        "oscillator":           "triangle",
        "vibrato":              None,
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "firmicutes_dominance",
        "activation_threshold": 0.35,
        "activation_direction": "high",
        "amplitude_key":        "firmicutes_dominance",
        "amplitude_invert":     False,
    },
    {
        "id":                   "l_rhamnosus",
        "name":                 "L. rhamnosus",
        "role":                 "good",
        "instrument":           "Acoustic Guitar",
        "freq_base":            196.0,
        "freq_range":           [196.0, 392.0],
        "oscillator":           "triangle",
        "vibrato":              {"rate": 3.5, "depth": 0.003},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "firmicutes_dominance",
        "activation_threshold": 0.30,
        "activation_direction": "high",
        "amplitude_key":        "diversity_index",
        "amplitude_invert":     False,
    },
    {
        "id":                   "a_muciniphila",
        "name":                 "A. muciniphila",
        "role":                 "good",
        "instrument":           "Trumpet",
        "freq_base":            523.0,
        "freq_range":           [523.0, 1047.0],
        "oscillator":           "square",
        "vibrato":              {"rate": 6.0, "depth": 0.004},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "mucosal_integrity",
        "activation_threshold": 0.50,
        "activation_direction": "high",
        "amplitude_key":        "mucosal_integrity",
        "amplitude_invert":     False,
    },
    {
        "id":                   "r_intestinalis",
        "name":                 "R. intestinalis",
        "role":                 "good",
        "instrument":           "Accordion",
        "freq_base":            392.0,
        "freq_range":           [392.0, 523.0],
        "oscillator":           "sawtooth",
        "vibrato":              {"rate": 4.0, "depth": 0.005},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "diversity_index",
        "activation_threshold": 0.45,
        "activation_direction": "high",
        "amplitude_key":        "diversity_index",
        "amplitude_invert":     False,
    },
    {
        "id":                   "b_thetaiotaomicron",
        "name":                 "B. thetaiotaomicron",
        "role":                 "good",
        "instrument":           "Cello",
        "freq_base":            130.0,
        "freq_range":           [65.0, 261.0],
        "oscillator":           "sine",
        "vibrato":              {"rate": 4.5, "depth": 0.005},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "bacteroidetes_dominance",
        "activation_threshold": 0.35,
        "activation_direction": "high",
        "amplitude_key":        "bacteroidetes_dominance",
        "amplitude_invert":     False,
    },
    {
        "id":                   "r_bromii",
        "name":                 "R. bromii",
        "role":                 "good",
        "instrument":           "Snare Drum",
        "freq_base":            200.0,
        "freq_range":           [100.0, 400.0],
        "oscillator":           "noise",
        "vibrato":              None,
        "percussive":           True,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "metabolic_energy",
        "activation_threshold": 0.30,
        "activation_direction": "high",
        "amplitude_key":        "metabolic_energy",
        "amplitude_invert":     False,
    },
    {
        "id":                   "e_hallii",
        "name":                 "E. hallii",
        "role":                 "good",
        "instrument":           "Bass Guitar",
        "freq_base":            82.0,
        "freq_range":           [82.0, 165.0],
        "oscillator":           "sawtooth",
        "vibrato":              None,
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "firmicutes_dominance",
        "activation_threshold": 0.25,
        "activation_direction": "high",
        "amplitude_key":        "firmicutes_dominance",
        "amplitude_invert":     False,
    },
    {
        "id":                   "c_minuta",
        "name":                 "C. minuta",
        "role":                 "good",
        "instrument":           "Viola",
        "freq_base":            440.0,
        "freq_range":           [440.0, 587.0],
        "oscillator":           "sine",
        "vibrato":              {"rate": 5.0, "depth": 0.007},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "diversity_index",
        "activation_threshold": 0.75,
        "activation_direction": "high",
        "amplitude_key":        "diversity_index",
        "amplitude_invert":     False,
    },
    # ── Bad bacteria ───────────────────────────────────────────────────────
    {
        "id":                   "c_difficile",
        "name":                 "C. difficile",
        "role":                 "bad",
        "instrument":           "Alarm Bell",
        "freq_base":            2000.0,
        "freq_range":           [2000.0, 4000.0],
        "oscillator":           "square",
        "vibrato":              None,
        "percussive":           False,
        "sporadic":             True,
        "detune":               12.0,
        "activation_key":       "inflammation_score",
        "activation_threshold": 0.50,
        "activation_direction": "high",
        "amplitude_key":        "inflammation_score",
        "amplitude_invert":     False,
    },
    {
        "id":                   "h_pylori",
        "name":                 "H. pylori",
        "role":                 "bad",
        "instrument":           "Off-key Drone",
        "freq_base":            120.0,
        "freq_range":           [110.0, 135.0],
        "oscillator":           "sawtooth",
        "vibrato":              {"rate": 0.3, "depth": 0.025},
        "percussive":           False,
        "sporadic":             False,
        "detune":               8.0,
        "activation_key":       "inflammation_score",
        "activation_threshold": 0.35,
        "activation_direction": "high",
        "amplitude_key":        "inflammation_score",
        "amplitude_invert":     False,
    },
    {
        "id":                   "f_nucleatum",
        "name":                 "F. nucleatum",
        "role":                 "bad",
        "instrument":           "Static Noise Burst",
        "freq_base":            3500.0,
        "freq_range":           [2000.0, 6000.0],
        "oscillator":           "noise",
        "vibrato":              None,
        "percussive":           False,
        "sporadic":             True,
        "detune":               0.0,
        "activation_key":       "proteobacteria_bloom",
        "activation_threshold": 0.40,
        "activation_direction": "high",
        "amplitude_key":        "proteobacteria_bloom",
        "amplitude_invert":     False,
    },
    {
        "id":                   "d_piger",
        "name":                 "D. piger",
        "role":                 "bad",
        "instrument":           "Sulfur Tone",
        "freq_base":            55.0,
        "freq_range":           [40.0, 80.0],
        "oscillator":           "sawtooth",
        "vibrato":              {"rate": 0.15, "depth": 0.030},
        "percussive":           False,
        "sporadic":             False,
        "detune":               6.0,
        "activation_key":       "compound_dpiger",
        "activation_threshold": 0.30,
        "activation_direction": "low",
        "amplitude_key":        "motility_activity",
        "amplitude_invert":     True,
    },
    # ── Archaea ────────────────────────────────────────────────────────────
    {
        "id":                   "m_smithii",
        "name":                 "M. smithii",
        "role":                 "archaea",
        "instrument":           "Pipe Organ",
        "freq_base":            55.0,
        "freq_range":           [27.0, 110.0],
        "oscillator":           "sine",
        "vibrato":              {"rate": 0.5, "depth": 0.010},
        "percussive":           False,
        "sporadic":             False,
        "detune":               0.0,
        "activation_key":       "motility_activity",
        "activation_threshold": 0.30,
        "activation_direction": "low",
        "amplitude_key":        "motility_activity",
        "amplitude_invert":     True,
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_active_instruments(
    biome_state: dict,
    h2_ppm: Optional[float] = None,
    ch4_ppm: Optional[float] = None,
) -> list[dict]:
    """
    Determine which species are active given the current biome state.

    Returns a list of species dicts (copies from SPECIES_CATALOG) each
    augmented with an "amplitude" key (float 0.05–1.0).
    """
    active = []
    for sp in SPECIES_CATALOG:
        if _is_active(sp, biome_state):
            amp = _compute_amplitude(sp, biome_state)
            active.append({**sp, "amplitude": round(amp, 3)})
    return active


def build_bible_synth_params(
    biome_state: dict,
    h2_ppm: Optional[float] = None,
    ch4_ppm: Optional[float] = None,
    genre: str = "classical",
) -> dict:
    """
    Build synthesis parameter dict for sonification.generate_audio().

    Returns:
        {
          "active_instruments":  list of active species dicts with amplitude,
          "tempo_bpm":           float  — CH4-driven: high CH4 → 40-60 BPM,
          "harmonic_richness":   float  — H2-driven: 0.0–1.0,
          "instrument_count":    int    — number of active good-bacteria voices,
          "inflammation_detune": float  — Hz detuning from inflammation,
          plus genre_* keys added by apply_genre()
        }
    """
    active = compute_active_instruments(biome_state, h2_ppm, ch4_ppm)

    # CH4 → tempo: high CH4 (methanogen) = sluggish 40-60 BPM;
    #               low CH4 (motile)      = lively 120+ BPM
    if ch4_ppm is not None:
        ch4_norm = min(1.0, ch4_ppm / 8.0)          # normalise to [0, 1]
        tempo_bpm = 140.0 - ch4_norm * 95.0          # 140 → 45 BPM
    else:
        motility = biome_state.get("motility_activity", 0.5)
        tempo_bpm = 50.0 + motility * 90.0           # 50 → 140 BPM

    tempo_bpm = round(max(40.0, min(160.0, tempo_bpm)), 1)

    # H2 → harmonic richness: more fermentation gas = richer overtone spectrum
    if h2_ppm is not None:
        harmonic_richness = min(1.0, h2_ppm / 12.0)
    else:
        harmonic_richness = biome_state.get("diversity_index", 0.5)

    harmonic_richness = round(max(0.0, min(1.0, harmonic_richness)), 3)

    good_count = sum(1 for s in active if s["role"] == "good")

    inflammation = biome_state.get("inflammation_score", 0.0)
    inflammation_detune = round(inflammation * 20.0, 2)   # 0–20 Hz

    base = {
        "active_instruments":  active,
        "tempo_bpm":           tempo_bpm,
        "harmonic_richness":   harmonic_richness,
        "instrument_count":    good_count,
        "inflammation_detune": inflammation_detune,
    }

    from genre_engine import apply_genre
    return apply_genre(base, genre, biome_state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_active(sp: dict, biome_state: dict) -> bool:
    key = sp["activation_key"]
    threshold = sp["activation_threshold"]
    direction = sp["activation_direction"]

    if key == "compound_dpiger":
        # D. piger: low motility + elevated inflammation
        motility = biome_state.get("motility_activity", 0.5)
        inflammation = biome_state.get("inflammation_score", 0.0)
        return motility <= 0.30 and inflammation >= 0.30

    value = biome_state.get(key, 0.5)
    if direction == "high":
        return value >= threshold
    else:
        return value <= threshold


def _compute_amplitude(sp: dict, biome_state: dict) -> float:
    key = sp["amplitude_key"]
    value = biome_state.get(key, 0.5)
    if sp["amplitude_invert"]:
        value = 1.0 - value
    # Keep active voices audible with a minimum floor
    return max(0.05, min(1.0, value))
