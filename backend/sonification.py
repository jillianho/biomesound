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
) -> bytes:
    """Generate a WAV audio file from a biome state dict. Returns WAV bytes."""
    if config is None:
        config = load_config()

    rng = np.random.default_rng(seed)

    sr = config.get("sample_rate", 44100)
    son_config = config["sonification"]
    scales = config["scales"]

    params = _derive_musical_params(biome_state, son_config)
    scale = _choose_scale(biome_state, scales)
    freqs = [note_to_freq(n) for n in scale]

    n_samples = int(sr * duration_seconds)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False)

    audio = np.zeros(n_samples, dtype=np.float64)

    # Layer 1: Additive synthesis — tonal voices
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
    audio = _apply_envelope(audio, sr, attack=2.0, release=3.0)

    if params["distortion_amount"] > 0.05:
        audio = _soft_clip(audio, params["distortion_amount"])

    audio = _allpass_reverb(audio, sr, params["reverb_decay"])

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


def _allpass_reverb(audio: np.ndarray, sr: int, decay: float) -> np.ndarray:
    """Multi-tap comb + allpass reverb for richer spatial effect.

    Healthy (low decay) = tight, defined space.
    Eroded integrity (high decay) = cavernous, washed out.
    """
    # Multiple comb filters with prime delay times (ms)
    comb_delays_ms = [29, 37, 43, 53]
    feedback = min(0.75, decay / 4.0)
    wet = min(0.45, decay / 5.0)

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
