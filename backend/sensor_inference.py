"""
sensor_inference.py
Maps raw pillbot sensor readings (pH, H2, CH4, temperature) to the
biome_state dict expected by the repo's sonification engine.

All output values are floats in [0.0, 1.0] unless noted.
"""

import math


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

def infer_from_sensors(ph: float, h2_ppm: float, ch4_ppm: float, temp_c: float) -> dict:
    """
    Convert raw sensor readings to a biome_state dict.

    Args:
        ph:       Luminal pH reading (typical range 5.0 – 9.0)
        h2_ppm:   Hydrogen gas in parts per million (0 – 20+ ppm)
        ch4_ppm:  Methane gas in parts per million (0 – 10+ ppm)
        temp_c:   Luminal temperature in Celsius (35.0 – 39.0)

    Returns:
        biome_state dict compatible with the repo's sonification engine.
    """

    # --- individual sub-scores (all clamped 0–1) ---

    # Fermentation quality: peaks at pH 6.3, degrades above 7.0 or below 5.5
    fermentation_quality = _bell(ph, center=6.3, width=1.0)

    # H2 activity: 0 ppm = nothing happening, ~10 ppm = peak, plateaus above
    h2_activity = _sigmoid(h2_ppm, midpoint=5.0, steepness=0.4)

    # CH4 dominance: high CH4 + low H2 = methanogens consuming everything
    # Penalise when CH4 is high relative to H2
    ch4_ratio = ch4_ppm / (h2_ppm + 0.5)           # avoid div/zero
    methanogen_score = _sigmoid(ch4_ratio, midpoint=1.5, steepness=1.2)

    # Inflammation: rises above 37.5°C, peaks at 39°C
    inflammation_from_temp = _sigmoid(temp_c, midpoint=37.8, steepness=1.5)

    # pH disruption: any deviation from healthy zone raises inflammation
    ph_disruption = max(0.0, (ph - 7.0) / 2.0)     # 0 below 7.0, 1.0 at 9.0
    ph_disruption = min(1.0, ph_disruption)

    # Combined inflammation score
    inflammation_score = max(inflammation_from_temp, ph_disruption * 0.8)

    # Diversity: driven by H2 activity + healthy pH + low inflammation
    diversity_index = (
        h2_activity * 0.5
        + fermentation_quality * 0.35
        + (1.0 - inflammation_score) * 0.15
    )

    # Motility: fast transit = high H2 + normal-to-low pH
    #           slow transit = high CH4 + near-neutral pH
    motility_activity = (
        h2_activity * 0.6
        + fermentation_quality * 0.2
        + (1.0 - methanogen_score) * 0.2
    )

    # Mucosal integrity: degrades with inflammation and proteolytic pH
    mucosal_integrity = max(0.0, 1.0 - inflammation_score * 0.7 - ph_disruption * 0.3)

    # Metabolic energy: overall activity level
    metabolic_energy = (h2_activity * 0.5 + fermentation_quality * 0.3 + diversity_index * 0.2)

    # Phylum proxies (rough heuristics, not validated strain detection)
    # Firmicutes: healthy fermenters, associated with moderate H2 + low pH
    firmicutes_dominance = fermentation_quality * (1.0 - methanogen_score) * 0.8

    # Bacteroidetes: active in high-H2, near-neutral pH environments
    bacteroidetes_dominance = h2_activity * fermentation_quality

    # Proteobacteria bloom: high pH + low H2 + elevated temp = dysbiosis
    proteobacteria_bloom = min(1.0, ph_disruption * 0.6 + inflammation_from_temp * 0.4)

    return {
        "diversity_index":        round(_clamp(diversity_index), 3),
        "inflammation_score":     round(_clamp(inflammation_score), 3),
        "firmicutes_dominance":   round(_clamp(firmicutes_dominance), 3),
        "bacteroidetes_dominance":round(_clamp(bacteroidetes_dominance), 3),
        "proteobacteria_bloom":   round(_clamp(proteobacteria_bloom), 3),
        "motility_activity":      round(_clamp(motility_activity), 3),
        "mucosal_integrity":      round(_clamp(mucosal_integrity), 3),
        "metabolic_energy":       round(_clamp(metabolic_energy), 3),
    }


# ---------------------------------------------------------------------------
# Gut state classifier — returns human-readable label + music mode
# ---------------------------------------------------------------------------

GUT_STATES = {
    "peak_diversity":   {"scale": "lydian_dominant",   "mood": "Full ensemble",       "color": "green"},
    "healthy":          {"scale": "lydian",             "mood": "Smooth fermentation", "color": "teal"},
    "fasted":           {"scale": "dorian",             "mood": "Resting baseline",    "color": "blue"},
    "methanogen":       {"scale": "phrygian",           "mood": "Heavy drone",         "color": "amber"},
    "dysbiosis":        {"scale": "phrygian_dominant",  "mood": "Dissonance",          "color": "orange"},
    "inflamed":         {"scale": "locrian",            "mood": "System alert",        "color": "red"},
}

# Musical scales (MIDI note offsets from root C3 = 48)
SCALES = {
    "lydian":            [0, 4, 7, 11, 14, 18, 21],   # C E G B D F# A
    "lydian_dominant":   [0, 4, 7, 10, 14, 18, 21],   # C E G Bb D F# A
    "dorian":            [0, 2, 3, 7, 9, 14, 15],     # C D Eb F G A Bb
    "phrygian":          [0, 1, 3, 7, 8, 10, 15],     # C Db Eb F G Ab Bb
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],      # C Db E F G Ab Bb
    "locrian":           [0, 1, 3, 5, 6, 8, 10],      # C Db Eb F Gb Ab Bb
}


def classify_gut_state(biome_state: dict) -> dict:
    """
    Given a biome_state dict, return the gut state label + musical params.
    """
    d = biome_state["diversity_index"]
    inf = biome_state["inflammation_score"]
    ch4_proxy = 1.0 - biome_state["motility_activity"]   # high ch4 → low motility
    prot = biome_state["proteobacteria_bloom"]

    if inf > 0.65:
        state = "inflamed"
    elif prot > 0.55 and d < 0.4:
        state = "dysbiosis"
    elif ch4_proxy > 0.65 and d < 0.5:
        state = "methanogen"
    elif d > 0.75 and inf < 0.2:
        state = "peak_diversity"
    elif d > 0.45 and inf < 0.35:
        state = "healthy"
    else:
        state = "fasted"

    meta = GUT_STATES[state]
    return {
        "state":  state,
        "mood":   meta["mood"],
        "scale":  SCALES[meta["scale"]],
        "color":  meta["color"],
        "score":  int(_gut_score(biome_state)),
    }


def _gut_score(b: dict) -> float:
    """Aggregate 0–100 wellness score from biome_state."""
    return (
        b["diversity_index"]     * 35
        + b["mucosal_integrity"] * 25
        + (1 - b["inflammation_score"]) * 25
        + b["metabolic_energy"]  * 15
    ) * 100 / (35 + 25 + 25 + 15)


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float, midpoint: float, steepness: float) -> float:
    return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))

def _bell(x: float, center: float, width: float) -> float:
    """Gaussian bell — peaks at 1.0 at center, falls off with width."""
    return math.exp(-((x - center) ** 2) / (2 * width ** 2))

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        ("Healthy fermentation",   6.4,  6.0, 0.8, 37.0),
        ("Peak diversity",         6.2, 12.0, 1.2, 37.0),
        ("Sugar spike / dysbiosis",7.8,  0.5, 0.3, 37.5),
        ("Inflamed",               7.9,  0.4, 0.2, 38.2),
        ("Methanogen dominant",    6.8,  1.0, 7.0, 36.9),
        ("Fasted baseline",        7.0,  0.8, 0.5, 37.0),
    ]

    for label, ph, h2, ch4, temp in test_cases:
        state = infer_from_sensors(ph, h2, ch4, temp)
        result = classify_gut_state(state)
        print(f"\n{label}")
        print(f"  Score: {result['score']}  |  Mood: {result['mood']}  |  State: {result['state']}")
        print(f"  diversity={state['diversity_index']}  inflammation={state['inflammation_score']}  motility={state['motility_activity']}")
