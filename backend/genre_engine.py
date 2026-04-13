"""
genre_engine.py
Musical genre presets for Biome Sound.

A genre defines HOW the synthesizer sounds — oscillator types, tempo range,
envelope timing, reverb level, and special effects like sidechain or tape wobble.
It does NOT change WHICH bacteria are active; that is determined by the biome
state in species_engine.py.

Mapping stays constant (healthy = consonant, inflamed = dissonant, high
diversity = more voices). Genre only reshapes the musical character.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Jazz scale definitions — selected by health state inside apply_genre()
# ---------------------------------------------------------------------------

JAZZ_SCALES: dict[str, list[str]] = {
    "healthy":   ["C3", "D3", "Eb3", "F3", "G3", "A3", "Bb3"],    # Dorian — warm, bluesy
    "dysbiotic": ["C3", "D3", "E3", "F3", "G3", "A3", "Bb3"],     # Mixolydian — slight tension
    "atrophic":  ["C3", "Db3", "Eb3", "F3", "G3", "Ab3", "Bb3"], # Phrygian — dark jazz
}

# ---------------------------------------------------------------------------
# Genre presets
# ---------------------------------------------------------------------------
# oscillator_map keys:
#   role-level  → "good" | "bad" | "archaea"   (lower priority)
#   per-species → species id string             (higher priority, overrides role)

GENRE_PRESETS: dict[str, dict] = {

    "classical": {
        "id":          "classical",
        "name":        "Classical / Orchestral",
        "description": "Full orchestral timbre per the Microbiome Sound Bible — "
                       "violin, cello, piano, trumpet. Slow and expressive.",
        "oscillator_map":          {},          # use species catalog defaults
        "tempo_range":             [40, 100],
        "attack_s":                2.0,
        "release_s":               3.5,
        "reverb_wet":              0.38,
        "filter_cutoff":           None,
        "distortion_mult":         1.0,
        "harmonic_richness_mult":  1.0,
        "swing":                   0.0,
        "tape_wobble":             False,
        "bad_amplify":             False,
        "sidechain":               False,
        "scale_override":          None,
        "vibrato_override":        None,
        "walking_bass":            False,
    },

    "edm": {
        "id":          "edm",
        "name":        "EDM / Electronic",
        "description": "808 kicks, sawtooth leads, sidechain-pumped bass. "
                       "Energy scales with diversity and metabolic activity.",
        "oscillator_map": {
            # role-level defaults
            "good":    "sawtooth",
            "bad":     "square",
            "archaea": "sawtooth",
            # per-species overrides
            "f_prausnitzii":     "square",     # lead synth
            "b_longum":          "square",     # pluck synth
            "b_thetaiotaomicron":"sawtooth",   # sub bass
            "e_hallii":          "sawtooth",   # bass synth
            "l_rhamnosus":       "sawtooth",   # arp synth
            "a_muciniphila":     "square",     # supersquare lead
        },
        "tempo_range":             [120, 150],
        "attack_s":                0.006,
        "release_s":               0.11,
        "reverb_wet":              0.09,
        "filter_cutoff":           None,
        "distortion_mult":         0.6,
        "harmonic_richness_mult":  1.5,
        "swing":                   0.0,
        "tape_wobble":             False,
        "bad_amplify":             False,
        "sidechain":               True,
        "scale_override":          None,
        "vibrato_override":        None,
        "walking_bass":            False,
    },

    "ambient": {
        "id":          "ambient",
        "name":        "Ambient / Meditation",
        "description": "All instruments become sine-wave pads with long attack/release "
                       "and heavy reverb. Calm regardless of gut state.",
        "oscillator_map": {
            "good":    "sine",
            "bad":     "sine",      # even pathogens become soft pads
            "archaea": "sine",
        },
        "tempo_range":             [30, 50],
        "attack_s":                4.0,
        "release_s":               7.0,
        "reverb_wet":              0.82,
        "filter_cutoff":           5500,        # soft high-end rolloff
        "distortion_mult":         0.04,        # near-zero distortion even when inflamed
        "harmonic_richness_mult":  0.22,        # clean overtone-free pads
        "swing":                   0.0,
        "tape_wobble":             False,
        "bad_amplify":             False,
        "sidechain":               False,
        "scale_override":          None,
        "vibrato_override":        {"rate": 0.24, "depth": 0.006},   # slow vibrato on all
        "walking_bass":            False,
    },

    "jazz": {
        "id":          "jazz",
        "name":        "Jazz",
        "description": "Swing feel, dorian/mixolydian scales, walking bass line, "
                       "sawtooth saxophone lead. Chord complexity tracks diversity.",
        "oscillator_map": {
            "f_prausnitzii":     "sawtooth",   # saxophone
            "a_muciniphila":     "sawtooth",   # trumpet (brassy)
            "b_thetaiotaomicron":"sine",        # upright bass
            "e_hallii":          "sine",        # walking bass
            "l_rhamnosus":       "sawtooth",   # comping chord strum
            "r_intestinalis":    "sawtooth",   # comping
        },
        "tempo_range":             [80, 130],
        "attack_s":                0.032,
        "release_s":               0.55,
        "reverb_wet":              0.20,
        "filter_cutoff":           None,
        "distortion_mult":         0.45,
        "harmonic_richness_mult":  1.1,
        "swing":                   0.33,
        "tape_wobble":             False,
        "bad_amplify":             False,
        "sidechain":               False,
        "scale_override":          None,        # computed from jazz_scales + health state
        "vibrato_override":        None,        # keep per-species vibrato
        "walking_bass":            True,
        "jazz_scales":             JAZZ_SCALES,
    },

    "lofi": {
        "id":          "lofi",
        "name":        "Lo-fi / Chill",
        "description": "Warm triangle waves, vinyl tape wobble, light swing, "
                       "8 kHz lowpass. Always mellow regardless of gut state.",
        "oscillator_map": {
            "good":    "triangle",
            "bad":     "sine",
            "archaea": "sine",
        },
        "tempo_range":             [70, 90],
        "attack_s":                0.09,
        "release_s":               1.0,
        "reverb_wet":              0.44,
        "filter_cutoff":           8000,
        "distortion_mult":         0.35,
        "harmonic_richness_mult":  0.6,
        "swing":                   0.18,
        "tape_wobble":             True,
        "bad_amplify":             False,
        "sidechain":               False,
        "scale_override":          None,
        "vibrato_override":        None,
        "walking_bass":            False,
    },

    "industrial": {
        "id":          "industrial",
        "name":        "Industrial / Dark",
        "description": "Harsh sawtooth/square, extreme distortion, fast aggressive tempo. "
                       "Pathogens get LOUDER. Always dissonant — even healthy states.",
        "oscillator_map": {
            "good":    "sawtooth",
            "bad":     "square",
            "archaea": "sawtooth",
            "m_smithii":  "sawtooth",   # pipe organ → industrial drone
            "r_bromii":   "noise",      # industrial percussion
        },
        "tempo_range":             [130, 170],
        "attack_s":                0.003,
        "release_s":               0.055,
        "reverb_wet":              0.04,
        "filter_cutoff":           None,
        "distortion_mult":         2.8,
        "harmonic_richness_mult":  1.6,
        "swing":                   0.0,
        "tape_wobble":             False,
        "bad_amplify":             True,   # pathogens get louder, not just detuned
        "sidechain":               False,
        # Phrygian dominant — always dissonant regardless of health
        "scale_override":          ["C3", "Db3", "E3", "F3", "Gb3", "Ab3", "B3"],
        "vibrato_override":        None,
        "walking_bass":            False,
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

GENRE_CATALOG: list[dict] = [
    {
        "id":          p["id"],
        "name":        p["name"],
        "description": p["description"],
        "tempo_range": p["tempo_range"],
    }
    for p in GENRE_PRESETS.values()
]

VALID_GENRES: set[str] = set(GENRE_PRESETS.keys())


def apply_genre(
    synth_params: dict,
    genre_id: str,
    biome_state: dict,
) -> dict:
    """
    Apply a genre preset to synth_params.

    Returns a new dict (does not mutate the input) with:
      - Oscillator overrides applied to active_instruments
      - Tempo clamped to genre's range
      - Harmonic richness scaled by genre multiplier
      - genre_* keys added for sonification.generate_audio() to consume

    Species activation (which instruments are active) is NOT changed.
    """
    genre = GENRE_PRESETS.get(genre_id) or GENRE_PRESETS["classical"]
    result = dict(synth_params)

    # ── Oscillator overrides ──────────────────────────────────────────────
    osc_map = genre.get("oscillator_map", {})
    new_instruments = []
    for sp in synth_params.get("active_instruments", []):
        sp_copy = dict(sp)
        # Per-species id takes precedence over role-level
        if sp["id"] in osc_map:
            sp_copy["oscillator"] = osc_map[sp["id"]]
        elif sp["role"] in osc_map:
            sp_copy["oscillator"] = osc_map[sp["role"]]
        new_instruments.append(sp_copy)
    result["active_instruments"] = new_instruments

    # ── Tempo: clamp to genre range ───────────────────────────────────────
    lo, hi = genre["tempo_range"]
    result["tempo_bpm"] = float(max(lo, min(hi, synth_params.get("tempo_bpm", 80.0))))

    # ── Harmonic richness: scale by genre multiplier ──────────────────────
    mult = genre.get("harmonic_richness_mult", 1.0)
    result["harmonic_richness"] = min(1.0, synth_params.get("harmonic_richness", 0.5) * mult)

    # ── Scale override ────────────────────────────────────────────────────
    scale_override = genre.get("scale_override")
    if scale_override is None and "jazz_scales" in genre:
        health = _health_state(biome_state)
        scale_override = genre["jazz_scales"][health]
    result["genre_scale_override"] = scale_override

    # ── Pass-through parameters consumed by sonification.generate_audio() ─
    result["genre_id"]              = genre["id"]
    result["genre_attack_s"]        = genre["attack_s"]
    result["genre_release_s"]       = genre["release_s"]
    result["genre_reverb_wet"]      = genre["reverb_wet"]
    result["genre_filter_cutoff"]   = genre.get("filter_cutoff")
    result["genre_distortion_mult"] = genre["distortion_mult"]
    result["genre_swing"]           = genre.get("swing", 0.0)
    result["genre_tape_wobble"]     = genre.get("tape_wobble", False)
    result["genre_bad_amplify"]     = genre.get("bad_amplify", False)
    result["genre_sidechain"]       = genre.get("sidechain", False)
    result["genre_vibrato_override"]= genre.get("vibrato_override")
    result["genre_walking_bass"]    = genre.get("walking_bass", False)

    return result


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _health_state(biome_state: dict) -> str:
    """Map biome_state to healthy / dysbiotic / atrophic bucket (mirrors sonification logic)."""
    inflammation = biome_state.get("inflammation_score", 0.0)
    diversity    = biome_state.get("diversity_index", 0.5)
    integrity    = biome_state.get("mucosal_integrity", 0.5)
    score = diversity * 0.4 + integrity * 0.4 + (1.0 - inflammation) * 0.2
    if score > 0.6:
        return "healthy"
    if score < 0.3:
        return "atrophic"
    return "dysbiotic"
