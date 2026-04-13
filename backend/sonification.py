"""
Sonification engine: converts biome state parameters into audio.

Synthesis layers:
  1. Additive synthesis — tonal voices (sine partials per "genus")
  2. Sub-bass drone — Firmicutes foundation
  3. Granular synthesis — texture/surface layer
  4. FM synthesis — inflammation/dysbiosis timbres
  5. Band-pass filtered noise — moisture/surface textures
  6. Reverb + distortion as spatial/timbral effects
"""

import json
import io
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt
from pathlib import Path
from typing import Optional


# Note name to frequency mapping
_NOTE_FREQS: dict[str, float] = {}


def _init_note_freqs():
    """Build a lookup of note names to frequencies."""
    chromatic = [
        ["C"], ["C#", "Db"], ["D"], ["D#", "Eb"], ["E"], ["F"],
        ["F#", "Gb"], ["G"], ["G#", "Ab"], ["A"], ["A#", "Bb"], ["B"],
    ]
    for octave in range(0, 9):
        for i, names in enumerate(chromatic):
            midi = 12 + octave * 12 + i  # C0 = MIDI 12
            freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
            for name in names:
                _NOTE_FREQS[f"{name}{octave}"] = freq


_init_note_freqs()


def note_to_freq(note: str) -> float:
    """Convert a note name like 'C3' to frequency in Hz."""
    if note in _NOTE_FREQS:
        return _NOTE_FREQS[note]
    raise ValueError(f"Unknown note: {note}")


def load_config(config_path: Optional[str] = None) -> dict:
    if config_path is None:
        config_path = str(Path(__file__).parent / "mapping_config.json")
    with open(config_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_audio(
    biome_state: dict[str, float],
    duration_seconds: float = 30.0,
    seed: Optional[int] = None,
    config: Optional[dict] = None,
    synth_params: Optional[dict] = None,
) -> bytes:
    """Generate a WAV audio file from a biome state dict. Returns WAV bytes.

    Args:
        biome_state:      Normalised gut microbiome parameters (all 0–1).
        duration_seconds: Length of audio clip in seconds.
        seed:             RNG seed for reproducibility.
        config:           Sonification config dict (loads from JSON if None).
        synth_params:     Optional dict from species_engine.build_bible_synth_params().
                          When provided, Layer 1 is replaced with per-species voices
                          and tempo_bpm is overridden by the CH4-derived value.
    """
    if config is None:
        config = load_config()

    rng = np.random.default_rng(seed)

    sr = config.get("sample_rate", 44100)
    son_config = config["sonification"]
    scales = config["scales"]

    params = _derive_musical_params(biome_state, son_config)
    scale = _choose_scale(biome_state, scales)
    freqs = [note_to_freq(n) for n in scale]

    # Genre scale override (industrial fixed / jazz health-dependent)
    if synth_params:
        scale_override = synth_params.get("genre_scale_override")
        if scale_override:
            freqs = [note_to_freq(n) for n in scale_override]
        # Expose resolved freqs to species voice layer for walking bass etc.
        synth_params = {**synth_params, "genre_scale_freqs": freqs}

    # Override tempo from species engine when available
    if synth_params and "tempo_bpm" in synth_params:
        params["tempo_bpm"] = synth_params["tempo_bpm"]

    n_samples = int(sr * duration_seconds)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False)

    audio = np.zeros(n_samples, dtype=np.float64)

    # Layer 1: Per-species voices (Bible mode) or additive synthesis (legacy)
    active_instruments = synth_params.get("active_instruments") if synth_params else None
    if active_instruments:
        audio += _species_voice_layer(t, active_instruments, synth_params, sr, rng)
    else:
        audio += _additive_layer(t, freqs, params, sr, duration_seconds, rng)

    # Layer 2: Sub-bass drone (Firmicutes)
    audio += _bass_drone(t, freqs[0], params)

    # Layer 3: Granular synthesis — texture layer
    audio += _granular_layer(t, freqs, params, sr, rng)

    # Layer 4: FM synthesis — inflammation timbres
    audio += _fm_layer(t, freqs, params, sr, biome_state)

    # Layer 5: Band-pass filtered noise — surface/moisture
    audio += _bandpass_noise_layer(n_samples, params, sr, rng, biome_state)

    # --- Post-processing ---

    # Genre low-pass filter (lo-fi 8 kHz, ambient 5.5 kHz)
    genre_filter = synth_params.get("genre_filter_cutoff") if synth_params else None
    if genre_filter and genre_filter < sr / 2 - 100:
        sos_lp = butter(4, genre_filter, btype="low", fs=sr, output="sos")
        audio = sosfilt(sos_lp, audio)

    # Vinyl crackle for lo-fi / tape wobble genres
    if synth_params and synth_params.get("genre_tape_wobble"):
        crackle = rng.standard_normal(n_samples) * 0.003
        sos_c = butter(2, 5000, btype="low", fs=sr, output="sos")
        audio += sosfilt(sos_c, crackle)

    # Genre-driven attack / release envelope
    attack_s  = synth_params.get("genre_attack_s",  2.0) if synth_params else 2.0
    release_s = synth_params.get("genre_release_s", 3.0) if synth_params else 3.0
    audio = _apply_envelope(audio, sr, attack=attack_s, release=release_s)

    # Distortion scaled by genre multiplier
    dist_mult = synth_params.get("genre_distortion_mult", 1.0) if synth_params else 1.0
    eff_distortion = min(2.0, params["distortion_amount"] * dist_mult)
    if eff_distortion > 0.05:
        audio = _soft_clip(audio, eff_distortion)

    # EDM sidechain pumping
    if synth_params and synth_params.get("genre_sidechain"):
        audio = _apply_sidechain(audio, sr, params["tempo_bpm"])

    # Reverb with optional genre wet override
    reverb_wet = synth_params.get("genre_reverb_wet") if synth_params else None
    audio = _allpass_reverb(audio, sr, params["reverb_decay"], reverb_wet_override=reverb_wet)

    audio *= params["amplitude"]

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


def generate_audio_from_series(
    biome_series: list[dict[str, float]],
    duration_seconds: float = 60.0,
    seed: Optional[int] = None,
    config: Optional[dict] = None,
) -> bytes:
    """Generate audio from a time-series of biome states (video input).

    Instead of generating separate segments and cross-fading, this interpolates
    biome parameters over time and renders a single continuous composition.
    """
    if not biome_series:
        raise ValueError("Empty biome series")

    if len(biome_series) == 1:
        return generate_audio(biome_series[0], duration_seconds, seed, config)

    if config is None:
        config = load_config()

    rng = np.random.default_rng(seed)
    sr = config.get("sample_rate", 44100)
    n_samples = int(sr * duration_seconds)
    n_states = len(biome_series)

    # Build interpolated biome parameters for each sample
    keys = list(biome_series[0].keys())
    # Create time-varying biome state by linear interpolation
    state_times = np.linspace(0, 1, n_states)
    sample_times = np.linspace(0, 1, n_samples)

    interpolated_values: dict[str, np.ndarray] = {}
    for key in keys:
        values = [s[key] for s in biome_series]
        interpolated_values[key] = np.interp(sample_times, state_times, values)

    # Render in overlapping windows with smooth crossfade
    window_count = max(2, min(n_states, 8))
    window_samples = n_samples // window_count
    overlap_samples = int(window_samples * 0.25)

    audio = np.zeros(n_samples, dtype=np.float64)

    for w in range(window_count):
        center = int((w + 0.5) * n_samples / window_count)
        start = max(0, center - window_samples // 2)
        end = min(n_samples, center + window_samples // 2)
        mid_idx = (start + end) // 2

        # Sample the biome state at this window's center
        window_state = {k: float(interpolated_values[k][mid_idx]) for k in keys}
        window_duration = (end - start) / sr

        window_audio_bytes = generate_audio(
            window_state, window_duration,
            seed=(seed + w if seed is not None else None),
            config=config,
        )
        seg_buf = io.BytesIO(window_audio_bytes)
        seg_data, _ = sf.read(seg_buf)

        seg_len = end - start
        seg_data = seg_data[:seg_len]

        # Hann-like window for smooth crossfade
        window_env = np.ones(len(seg_data))
        fade = min(overlap_samples, len(seg_data) // 2)
        if fade > 0:
            window_env[:fade] = np.linspace(0, 1, fade)
            window_env[-fade:] = np.linspace(1, 0, fade)

        audio[start:start + len(seg_data)] += seg_data * window_env

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Musical parameter derivation
# ---------------------------------------------------------------------------


def _derive_musical_params(biome_state: dict[str, float], son_config: dict) -> dict:
    """Map biome state to concrete musical parameters using sonification config."""
    params = {}
    for biome_key, mapping in son_config.items():
        value = biome_state.get(biome_key, 0.5)
        target = mapping["target"]
        lo, hi = mapping["range"]
        curve = mapping.get("curve", "linear")

        if curve == "exponential":
            mapped = lo + (hi - lo) * (value ** 2)
        elif curve == "inverse":
            mapped = hi - (hi - lo) * value
        else:
            mapped = lo + (hi - lo) * value

        params[target] = mapped

    return params


def _choose_scale(biome_state: dict[str, float], scales: dict) -> list[str]:
    """Choose musical scale based on overall biome health."""
    inflammation = biome_state.get("inflammation_score", 0.0)
    diversity = biome_state.get("diversity_index", 0.5)
    integrity = biome_state.get("mucosal_integrity", 0.5)

    health_score = diversity * 0.4 + integrity * 0.4 + (1 - inflammation) * 0.2

    if health_score > 0.6:
        return scales["healthy"]
    elif health_score < 0.3:
        return scales["atrophic"]
    else:
        return scales["dysbiotic"]


# ---------------------------------------------------------------------------
# Synthesis layers
# ---------------------------------------------------------------------------


def _additive_layer(
    t: np.ndarray, freqs: list[float], params: dict,
    sr: int, duration: float, rng: np.random.Generator,
) -> np.ndarray:
    """Additive synthesis with multiple sine voices and slow LFO modulation."""
    voice_count = max(1, int(params.get("voice_count", 3)))
    voice_count = min(voice_count, len(freqs))

    audio = np.zeros_like(t)

    for i in range(voice_count):
        freq = freqs[i % len(freqs)]
        # Slow LFO per voice — organic micro-detuning
        lfo_rate = 0.04 + i * 0.017 + rng.uniform(-0.005, 0.005)
        lfo_depth = 0.003 * freq
        freq_mod = freq + lfo_depth * np.sin(2 * np.pi * lfo_rate * t)

        # Phase accumulation for smooth FM
        phase = np.cumsum(2 * np.pi * freq_mod / sr)
        voice = np.sin(phase)

        # Harmonics (Bacteroidetes = tonal clarity)
        mid_weight = params.get("mid_harmonic_weight", 0.3)
        if mid_weight > 0.2:
            voice += mid_weight * 0.5 * np.sin(2 * phase)
            voice += mid_weight * 0.25 * np.sin(3 * phase)
            voice += mid_weight * 0.1 * np.sin(5 * phase)

        # Staggered entry with fade
        entry_delay = i * duration / (voice_count * 2)
        entry_sample = int(entry_delay * sr)
        voice[:entry_sample] = 0
        fade_len = min(int(2 * sr), len(voice) - entry_sample)
        if fade_len > 0 and entry_sample < len(voice):
            voice[entry_sample:entry_sample + fade_len] *= np.linspace(0, 1, fade_len)

        # Subtle amplitude tremolo
        tremolo_rate = 0.1 + i * 0.03
        tremolo = 0.9 + 0.1 * np.sin(2 * np.pi * tremolo_rate * t)
        voice *= tremolo

        audio += voice / voice_count

    return audio * 0.5


def _bass_drone(
    t: np.ndarray, root_freq: float, params: dict,
) -> np.ndarray:
    """Low-frequency sustained drone for Firmicutes foundation."""
    bass_weight = params.get("bass_weight", 0.3)
    if bass_weight < 0.1:
        return np.zeros_like(t)

    freq = root_freq / 2
    # Slow breathing LFO
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * t)
    drone = np.sin(2 * np.pi * freq * t) * lfo
    # Sub-harmonic for weight
    drone += 0.3 * np.sin(2 * np.pi * freq / 2 * t)
    # Slight pitch wobble
    drone += 0.15 * np.sin(2 * np.pi * (freq * 1.002) * t) * lfo

    return drone * bass_weight * 0.35


def _granular_layer(
    t: np.ndarray, freqs: list[float], params: dict,
    sr: int, rng: np.random.Generator,
) -> np.ndarray:
    """Granular synthesis layer — short grains of tonal material.

    Driven by diversity (more grains) and metabolic energy (grain density).
    Creates shimmering, evolving texture.
    """
    voice_count = max(1, int(params.get("voice_count", 3)))
    amplitude = params.get("amplitude", 0.5)
    tempo = params.get("tempo_bpm", 80)

    # Higher tempo & voice count = more grains
    grains_per_second = 2 + voice_count * 0.5 + (tempo - 40) / 120 * 3
    grain_duration_ms = rng.uniform(30, 120)  # ms
    grain_samples = int(grain_duration_ms * sr / 1000)

    n_samples = len(t)
    audio = np.zeros(n_samples, dtype=np.float64)
    duration = n_samples / sr

    n_grains = int(grains_per_second * duration)
    if n_grains < 1:
        return audio

    for _ in range(n_grains):
        # Random position
        pos = rng.integers(0, max(1, n_samples - grain_samples))
        # Random frequency from scale
        freq = rng.choice(freqs)
        # Optionally transpose up 1-2 octaves for shimmer
        octave_shift = rng.choice([1, 2, 4], p=[0.5, 0.35, 0.15])
        freq *= octave_shift

        grain_len = min(grain_samples, n_samples - pos)
        gt = np.arange(grain_len) / sr

        # Grain: sine with Hann window envelope
        grain = np.sin(2 * np.pi * freq * gt)
        window = np.hanning(grain_len)
        grain *= window

        # Random amplitude variation
        grain *= rng.uniform(0.02, 0.08) * amplitude

        audio[pos:pos + grain_len] += grain

    return audio


def _fm_layer(
    t: np.ndarray, freqs: list[float], params: dict,
    sr: int, biome_state: dict[str, float],
) -> np.ndarray:
    """FM synthesis layer for inflammation/dysbiosis timbres.

    Higher inflammation → more modulation depth → harsher, metallic timbre.
    Proteobacteria bloom → dissonant modulator ratios.
    """
    inflammation = biome_state.get("inflammation_score", 0.0)
    proteobacteria = biome_state.get("proteobacteria_bloom", 0.0)

    # Only activate when there's significant inflammation or dysbiosis
    intensity = max(inflammation, proteobacteria)
    if intensity < 0.15:
        return np.zeros_like(t)

    audio = np.zeros_like(t)
    carrier_freq = freqs[0] * 2  # one octave above root

    # Modulator ratio — consonant for mild, dissonant for severe
    if proteobacteria > 0.5:
        # Dissonant: non-integer ratios
        mod_ratios = [1.414, 2.718, 3.141]
    elif inflammation > 0.5:
        # Metallic: near-integer
        mod_ratios = [2.01, 3.99, 5.03]
    else:
        # Mild: clean integer ratios
        mod_ratios = [2.0, 3.0]

    mod_depth = intensity * carrier_freq * 1.5  # modulation index scales with intensity

    for ratio in mod_ratios:
        mod_freq = carrier_freq * ratio
        # Modulator
        modulator = mod_depth * np.sin(2 * np.pi * mod_freq * t)
        # Carrier with FM
        phase = np.cumsum(2 * np.pi * (carrier_freq + modulator) / sr)
        fm_voice = np.sin(phase)

        # Slow swell envelope
        swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)
        fm_voice *= swell

        audio += fm_voice / len(mod_ratios)

    # Scale by intensity — subtle at low, prominent at high
    return audio * intensity * 0.25


def _bandpass_noise_layer(
    n_samples: int, params: dict, sr: int,
    rng: np.random.Generator, biome_state: dict[str, float],
) -> np.ndarray:
    """Band-pass filtered noise for surface/moisture textures.

    Driven by specular_ratio (moisture) and proteobacteria_bloom (dysbiosis noise).
    Low mucosal integrity → wider bandwidth (more chaotic).
    """
    dissonance = params.get("dissonance_amount", 0.0)
    integrity = biome_state.get("mucosal_integrity", 0.5)

    if dissonance < 0.05 and integrity > 0.8:
        return np.zeros(n_samples, dtype=np.float64)

    noise = rng.standard_normal(n_samples)

    # Center frequency: low integrity → lower rumble, high dissonance → higher hiss
    center_hz = 200 + dissonance * 2000 + (1 - integrity) * 500
    # Bandwidth: low integrity → wider
    bandwidth = 100 + (1 - integrity) * 800

    low = max(20, center_hz - bandwidth / 2)
    high = min(sr / 2 - 1, center_hz + bandwidth / 2)

    if low >= high:
        return np.zeros(n_samples, dtype=np.float64)

    sos = butter(4, [low, high], btype="band", fs=sr, output="sos")
    filtered = sosfilt(sos, noise)

    # Slow amplitude modulation — breathing quality
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * np.arange(n_samples) / sr)
    filtered *= mod

    # Scale: more prominent when things are unhealthy
    level = max(dissonance, 1 - integrity) * 0.12

    return filtered * level


# ---------------------------------------------------------------------------
# Species-based synthesis (Bible mode)
# ---------------------------------------------------------------------------


def _render_oscillator(
    t: np.ndarray, freq: float, oscillator: str,
    sr: int, rng: np.random.Generator,
) -> np.ndarray:
    """Render a single oscillator waveform at the given frequency."""
    if oscillator == "triangle":
        phase = (freq * t) % 1.0
        return 2.0 * np.abs(2.0 * phase - 1.0) - 1.0
    elif oscillator == "sawtooth":
        phase = (freq * t) % 1.0
        return 2.0 * phase - 1.0
    elif oscillator == "square":
        return np.sign(np.sin(2.0 * np.pi * freq * t))
    elif oscillator == "noise":
        return rng.standard_normal(len(t))
    else:  # "sine" default
        return np.sin(2.0 * np.pi * freq * t)


def _percussive_hits(
    t: np.ndarray, tempo_bpm: float, sr: int,
    rng: np.random.Generator, swing: float = 0.0,
) -> np.ndarray:
    """Rhythmic snare-style hits on 8th-note grid (R. bromii).

    swing: 0.0 = straight, 0.33 = jazz triplet feel (delays every other 8th note).
    """
    n = len(t)
    audio = np.zeros(n, dtype=np.float64)
    hit_dur = int(0.055 * sr)   # ~55 ms per hit
    beat_period = 60.0 / tempo_bpm
    eighth_period = beat_period / 2.0
    swing_offset = eighth_period * swing * 0.5  # delay odd 8th notes

    pos_sec = 0.0
    duration = n / sr
    note_idx = 0
    while pos_sec < duration:
        # Apply swing: delay every other 8th note
        onset = pos_sec + (swing_offset if (note_idx % 2 == 1) else 0.0)
        idx = int(onset * sr)
        if idx >= n:
            break
        hit_len = min(hit_dur, n - idx)
        noise = rng.standard_normal(hit_len)
        env = np.exp(-np.arange(hit_len) / (hit_len * 0.12))
        audio[idx:idx + hit_len] += noise * env
        pos_sec += eighth_period
        note_idx += 1

    # Bandpass filter for snare character (200–8000 Hz)
    sos = butter(4, [200, 8000], btype="band", fs=sr, output="sos")
    return sosfilt(sos, audio)


def _sporadic_burst(
    t: np.ndarray, freq_range: list[float], oscillator: str,
    sr: int, rng: np.random.Generator,
) -> np.ndarray:
    """Occasional random bursts (C. difficile alarm, F. nucleatum static)."""
    n = len(t)
    audio = np.zeros(n, dtype=np.float64)
    duration = n / sr

    n_bursts = rng.integers(2, max(3, int(duration / 8)))
    burst_dur = int(0.20 * sr)  # 200 ms burst

    for _ in range(n_bursts):
        pos = rng.integers(0, max(1, n - burst_dur))
        burst_len = min(burst_dur, n - pos)
        bt = np.arange(burst_len) / sr
        f = rng.uniform(freq_range[0], freq_range[1])

        if oscillator == "noise":
            burst = rng.standard_normal(burst_len)
        elif oscillator == "square":
            burst = np.sign(np.sin(2.0 * np.pi * f * bt))
        else:
            burst = np.sin(2.0 * np.pi * f * bt)

        env = np.hanning(burst_len)
        audio[pos:pos + burst_len] += burst * env

    return audio


def _species_voice_layer(
    t: np.ndarray, active_instruments: list, synth_params: dict,
    sr: int, rng: np.random.Generator,
) -> np.ndarray:
    """Render per-species instrument voices from the Microbiome Sound Bible.

    Replaces the generic additive layer when synth_params are provided.
    Each species has its own oscillator type, frequency, vibrato, and envelope.
    Genre parameters (oscillator overrides, tape wobble, vibrato override, etc.)
    are read from synth_params and applied here.
    """
    n_samples = len(t)
    audio = np.zeros(n_samples, dtype=np.float64)

    if not active_instruments:
        return audio

    tempo_bpm        = synth_params.get("tempo_bpm", 80.0)
    harmonic_richness = synth_params.get("harmonic_richness", 0.5)
    inflammation_detune = synth_params.get("inflammation_detune", 0.0)

    # Genre-specific parameters
    genre_id         = synth_params.get("genre_id", "classical")
    bad_amplify      = synth_params.get("genre_bad_amplify", False)
    tape_wobble      = synth_params.get("genre_tape_wobble", False)
    vibrato_override = synth_params.get("genre_vibrato_override")
    scale_freqs      = synth_params.get("genre_scale_freqs", [])
    swing            = synth_params.get("genre_swing", 0.0)
    walking_bass     = synth_params.get("genre_walking_bass", False)

    # Build bass freqs for jazz walking bass from resolved scale
    bass_freqs = [f / 4.0 for f in scale_freqs] if scale_freqs else [82.0, 110.0, 130.0, 165.0]

    # Scale overall level so many voices don't overwhelm
    n_active = max(1, len(active_instruments))
    level = 0.5 / (n_active ** 0.55)

    for sp in active_instruments:
        amplitude = sp["amplitude"]
        freq      = sp["freq_base"]
        oscillator = sp["oscillator"]
        vibrato    = sp.get("vibrato")
        detune     = sp.get("detune", 0.0)
        role       = sp["role"]

        # Bad bacteria: amplify instead of detune in industrial, else add detune
        if role == "bad":
            if bad_amplify:
                amplitude = min(1.0, amplitude * 1.8)
                detune = 0.0
            else:
                detune += inflammation_detune * 0.5

        voice = np.zeros(n_samples, dtype=np.float64)

        if sp["percussive"]:
            # R. bromii: rhythm hits; EDM gets 808 kick instead of snare
            if genre_id == "edm":
                voice = _edm_kick(t, tempo_bpm, sr, rng)
            else:
                voice = _percussive_hits(t, tempo_bpm, sr, rng, swing=swing)

        elif sp["sporadic"]:
            # C. difficile / F. nucleatum: infrequent alarm bursts
            voice = _sporadic_burst(t, sp["freq_range"], oscillator, sr, rng)

        elif walking_bass and sp["id"] in ("b_thetaiotaomicron", "e_hallii"):
            # Jazz walking bass line for upright/bass guitar voices
            voice = _walking_bass_line(t, bass_freqs, tempo_bpm, sr, rng, swing=swing)

        else:
            eff_freq = freq + detune

            # Build per-sample frequency array for phase accumulation
            # (enables vibrato + tape wobble on all oscillator types)
            effective_vibrato = vibrato_override if vibrato_override else vibrato
            freq_arr = np.full(n_samples, float(eff_freq))

            if effective_vibrato:
                vib_depth = effective_vibrato["depth"] * eff_freq
                freq_arr = freq_arr + vib_depth * np.sin(
                    2.0 * np.pi * effective_vibrato["rate"] * t
                )

            if tape_wobble:
                wobble_rate  = 0.033 + rng.uniform(-0.008, 0.008)
                wobble_depth = eff_freq * (2.0 ** (5.0 / 1200.0) - 1.0)  # ±5 cents
                freq_arr = freq_arr + wobble_depth * np.sin(
                    2.0 * np.pi * wobble_rate * t + rng.uniform(0.0, 2.0 * np.pi)
                )

            # Phase accumulation — works uniformly for all waveforms
            phase = np.cumsum(2.0 * np.pi * freq_arr / sr)

            if oscillator == "sawtooth":
                voice = 2.0 * ((phase / (2.0 * np.pi)) % 1.0) - 1.0
            elif oscillator == "triangle":
                p = (phase / (2.0 * np.pi)) % 1.0
                voice = 2.0 * np.abs(2.0 * p - 1.0) - 1.0
            elif oscillator == "square":
                voice = np.sign(np.sin(phase))
            elif oscillator == "noise":
                voice = rng.standard_normal(n_samples)
            else:  # sine
                voice = np.sin(phase)

            # Add overtones driven by harmonic_richness
            if oscillator in ("sine", "triangle") and harmonic_richness > 0.2:
                voice += harmonic_richness * 0.4 * np.sin(2.0 * phase)
                if harmonic_richness > 0.5:
                    voice += harmonic_richness * 0.2 * np.sin(3.0 * phase)

            # M. smithii pipe organ: extra sub-harmonics for depth
            if sp["id"] == "m_smithii":
                voice += 0.7 * np.sin(2.0 * phase)
                voice += 0.5 * np.sin(4.0 * phase)
                voice += 0.3 * np.sin(6.0 * phase)

            # Organic tremolo (skip for ambient — vibrato_override handles it)
            if not vibrato_override:
                trem_rate = 0.07 + rng.uniform(0.0, 0.04)
                voice *= 0.85 + 0.15 * np.sin(2.0 * np.pi * trem_rate * t)

        # Per-voice fade in/out envelope
        fade = min(int(1.5 * sr), n_samples // 4)
        if fade > 0:
            env = np.ones(n_samples)
            env[:fade]  = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
            voice *= env

        audio += voice * amplitude * level

    return audio


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _apply_envelope(
    audio: np.ndarray, sr: int, attack: float = 2.0, release: float = 3.0,
) -> np.ndarray:
    """Apply attack/release amplitude envelope."""
    n = len(audio)
    attack_samples = min(int(attack * sr), n // 2)
    release_samples = min(int(release * sr), n // 2)

    envelope = np.ones(n)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if release_samples > 0:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)

    return audio * envelope


def _soft_clip(audio: np.ndarray, amount: float) -> np.ndarray:
    """Soft clipping distortion — warm saturation."""
    drive = 1.0 + amount * 5.0
    return np.tanh(audio * drive) / np.tanh(drive)


def _allpass_reverb(
    audio: np.ndarray, sr: int, decay: float,
    reverb_wet_override: Optional[float] = None,
) -> np.ndarray:
    """Multi-tap comb + allpass reverb for richer spatial effect.

    Healthy (low decay) = tight, defined space.
    Eroded integrity (high decay) = cavernous, washed out.
    reverb_wet_override: if set, overrides the computed wet level (0.0–1.0).
    """
    # Multiple comb filters with prime delay times (ms)
    comb_delays_ms = [29, 37, 43, 53]
    feedback = min(0.75, decay / 4.0)
    wet = reverb_wet_override if reverb_wet_override is not None else min(0.45, decay / 5.0)

    n = len(audio)
    reverb_out = np.zeros(n, dtype=np.float64)

    for delay_ms in comb_delays_ms:
        delay_samples = int(sr * delay_ms / 1000)
        buf = np.zeros(n, dtype=np.float64)
        for i in range(delay_samples, n):
            buf[i] = audio[i] + buf[i - delay_samples] * feedback
        reverb_out += buf

    reverb_out /= len(comb_delays_ms)

    # Single allpass filter for diffusion
    ap_delay = int(sr * 5 / 1000)  # 5ms
    ap_gain = 0.5
    allpass = np.zeros(n, dtype=np.float64)
    for i in range(ap_delay, n):
        allpass[i] = -ap_gain * reverb_out[i] + reverb_out[i - ap_delay] + ap_gain * allpass[i - ap_delay]

    return audio * (1 - wet) + allpass * wet


# ---------------------------------------------------------------------------
# Genre-specific synthesis helpers
# ---------------------------------------------------------------------------


def _edm_kick(
    t: np.ndarray, tempo_bpm: float, sr: int, rng: np.random.Generator,
) -> np.ndarray:
    """808-style kick drum: pitch drops 225 → 45 Hz with exponential decay."""
    n = len(t)
    audio = np.zeros(n, dtype=np.float64)
    beat_samples = int(sr * 60.0 / tempo_bpm)
    kick_dur = int(0.35 * sr)

    for kick_pos in range(0, n, beat_samples):
        k_len = min(kick_dur, n - kick_pos)
        if k_len < 2:
            break
        kt = np.arange(k_len) / sr
        freq_env = 45.0 + 180.0 * np.exp(-kt * 28.0)
        phase = np.cumsum(2.0 * np.pi * freq_env / sr)
        audio[kick_pos:kick_pos + k_len] += np.sin(phase) * np.exp(-kt * 10.0)

    return audio


def _walking_bass_line(
    t: np.ndarray, bass_freqs: list[float], tempo_bpm: float,
    sr: int, rng: np.random.Generator, swing: float = 0.0,
) -> np.ndarray:
    """Jazz quarter-note walking bass through scale tones with upright-bass envelope."""
    n = len(t)
    audio = np.zeros(n, dtype=np.float64)
    beat_samples = int(sr * 60.0 / tempo_bpm)
    n_freqs = len(bass_freqs)
    walk_pattern = [0, 4 % n_freqs, 2 % n_freqs, 6 % n_freqs]

    note_idx = 0
    pos = 0
    swing_offset = int(beat_samples * swing * 0.3)

    while pos < n:
        onset = pos + (swing_offset if (note_idx % 2 == 1) else 0)
        end   = min(onset + beat_samples, n)
        seg_len = end - onset
        if seg_len < 2:
            break

        gt   = np.arange(seg_len) / sr
        freq = bass_freqs[walk_pattern[note_idx % len(walk_pattern)] % n_freqs]
        voice = np.sin(2.0 * np.pi * freq * gt) * np.exp(-gt * 4.5)

        if onset < n:
            audio[onset:end] += voice[:end - onset]

        pos += beat_samples
        note_idx += 1

    return audio


def _apply_sidechain(
    audio: np.ndarray, sr: int, tempo_bpm: float,
) -> np.ndarray:
    """EDM sidechain compression: dip to 0.1 on each kick beat, recover over 90 ms."""
    beat_samples = int(sr * 60.0 / tempo_bpm)
    n = len(audio)
    envelope = np.ones(n, dtype=np.float64)
    recover = int(0.09 * sr)

    for kick_pos in range(0, n, beat_samples):
        r = min(recover, n - kick_pos)
        if r > 0:
            envelope[kick_pos:kick_pos + r] = 0.1 + 0.9 * (np.arange(r) / r)

    return audio * envelope
