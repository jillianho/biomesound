"""
FastAPI application for Biome Sound — gut microbiome sonification engine.
"""

import io
import tempfile
import os
import uuid
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from feature_extraction import extract_features, extract_features_from_video
from inference import infer_biome_state, infer_from_frame_series, load_config
from sonification import generate_audio, generate_audio_from_series

# --- new imports to add ---
import json
import threading
import time
from sensor_inference import infer_from_sensors, classify_gut_state
from species_engine import build_bible_synth_params, SPECIES_CATALOG, compute_active_instruments
from prediction import forecast, BIOME_KEYS
from genre_engine import GENRE_CATALOG, VALID_GENRES

app = FastAPI(title="Biome Sound API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()

# In-memory store for generated audio (keyed by ID)
_audio_store: dict[str, bytes] = {}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


class FeaturesInput(BaseModel):
    features: list[dict[str, float]]


class BiomeStateInput(BaseModel):
    biome_state: dict[str, float]
    duration_seconds: float = 30.0
    seed: int | None = None
    genre: str = "classical"


# --- Endpoints ---


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """Extract visual features from an uploaded image or video."""
    ext = _get_extension(file.filename)
    contents = await file.read()

    if ext in IMAGE_EXTENSIONS:
        image = _bytes_to_image(contents)
        features = [extract_features(image)]
        return {"features": features, "frames_analyzed": 1}

    elif ext in VIDEO_EXTENSIONS:
        features = _process_video(contents, ext)
        return {"features": features, "frames_analyzed": len(features)}

    else:
        raise HTTPException(400, f"Unsupported file type: {ext}")


@app.post("/api/infer")
async def infer(data: FeaturesInput):
    """Map visual features to biome state parameters."""
    if len(data.features) == 1:
        biome_state = infer_biome_state(data.features[0], config)
        return {"biome_state": biome_state}
    else:
        biome_states = infer_from_frame_series(data.features, config)
        return {"biome_state": biome_states}


@app.get("/api/genres")
async def list_genres():
    """Return available genre presets with descriptions and tempo ranges."""
    return JSONResponse({"genres": GENRE_CATALOG, "count": len(GENRE_CATALOG)})


@app.post("/api/generate")
async def generate(data: BiomeStateInput):
    """Generate audio from biome state parameters. Returns WAV binary."""
    genre = data.genre if data.genre in VALID_GENRES else "classical"
    synth_params = build_bible_synth_params(data.biome_state, genre=genre)
    wav_bytes = generate_audio(
        data.biome_state,
        duration_seconds=data.duration_seconds,
        seed=data.seed,
        config=config,
        synth_params=synth_params,
    )
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=biome_sound.wav"},
    )


@app.post("/api/pipeline")
async def pipeline(
    file: UploadFile = File(...),
    duration_seconds: float = Query(default=30.0),
    seed: int | None = Query(default=None),
    genre: str = Query(default="classical"),
):
    """All-in-one endpoint: upload → analyze → infer → generate.
    Returns biome state + audio URL.
    """
    ext = _get_extension(file.filename)
    contents = await file.read()
    genre = genre if genre in VALID_GENRES else "classical"

    # Step 1: Feature extraction
    if ext in IMAGE_EXTENSIONS:
        image = _bytes_to_image(contents)
        features = [extract_features(image)]
    elif ext in VIDEO_EXTENSIONS:
        features = _process_video(contents, ext)
    else:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Step 2: Inference
    if len(features) == 1:
        biome_state = infer_biome_state(features[0], config)
        synth_params = build_bible_synth_params(biome_state, genre=genre)
        # Step 3: Audio generation
        wav_bytes = generate_audio(
            biome_state, duration_seconds=duration_seconds, seed=seed,
            config=config, synth_params=synth_params,
        )
        biome_response = biome_state
    else:
        biome_states = infer_from_frame_series(features, config)
        wav_bytes = generate_audio_from_series(
            biome_states, duration_seconds=duration_seconds, seed=seed, config=config
        )
        # Return the average biome state for display
        biome_response = _average_biome_states(biome_states)

    _record_observation(biome_response)

    # Store audio and return URL
    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes

    return JSONResponse({
        "biome_state": biome_response,
        "audio_url": f"/api/audio/{audio_id}",
        "features": features,
        "frames_analyzed": len(features),
    })


@app.get("/api/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Retrieve a previously generated audio file."""
    wav_bytes = _audio_store.get(audio_id)
    if wav_bytes is None:
        raise HTTPException(404, "Audio not found")
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=biome_sound.wav"},
    )


@app.get("/")
async def root():
    return {"status": "ok", "message": "Biome Sound API is running. See /docs for endpoints."}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


class InstrumentsRequest(BaseModel):
    biome_state: dict[str, float]
    h2_ppm: float | None = None
    ch4_ppm: float | None = None
    genre: str = "classical"


@app.post("/api/instruments")
async def get_instruments(data: InstrumentsRequest):
    """
    Return which instruments are active and at what amplitude for any biome state.
    Useful for the instrument-panel UI: pass any gut state, get a live instrument list.
    Also returns the full catalog so inactive instruments can be shown as dimmed.
    """
    genre = data.genre if data.genre in VALID_GENRES else "classical"
    params = build_bible_synth_params(data.biome_state, data.h2_ppm, data.ch4_ppm, genre=genre)
    active_ids = {s["id"] for s in params["active_instruments"]}

    all_instruments = []
    for sp in SPECIES_CATALOG:
        amplitude = next(
            (s["amplitude"] for s in params["active_instruments"] if s["id"] == sp["id"]),
            0.0,
        )
        all_instruments.append({
            "id":         sp["id"],
            "name":       sp["name"],
            "instrument": sp["instrument"],
            "role":       sp["role"],
            "oscillator": sp["oscillator"],
            "freq_base":  sp["freq_base"],
            "percussive": sp["percussive"],
            "sporadic":   sp["sporadic"],
            "active":     sp["id"] in active_ids,
            "amplitude":  amplitude,
        })

    return JSONResponse({
        "instruments":        all_instruments,
        "active_count":       len(active_ids),
        "tempo_bpm":          params["tempo_bpm"],
        "harmonic_richness":  params["harmonic_richness"],
        "instrument_count":   params["instrument_count"],
        "inflammation_detune": params["inflammation_detune"],
    })


@app.get("/api/species")
async def list_species():
    """Return all species in the catalog with their instrument mappings."""
    catalog = [
        {
            "id":         sp["id"],
            "name":       sp["name"],
            "role":       sp["role"],
            "instrument": sp["instrument"],
            "freq_base":  sp["freq_base"],
            "freq_range": sp["freq_range"],
            "oscillator": sp["oscillator"],
            "percussive": sp["percussive"],
            "sporadic":   sp["sporadic"],
            "activation_key":       sp["activation_key"],
            "activation_threshold": sp["activation_threshold"],
            "activation_direction": sp["activation_direction"],
        }
        for sp in SPECIES_CATALOG
    ]
    return JSONResponse({"species": catalog, "count": len(catalog)})


# --- Helpers ---


def _get_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(400, "No filename provided")
    return Path(filename).suffix.lower()


def _bytes_to_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "Could not decode image")
    return image


def _process_video(contents: bytes, ext: str) -> list[dict[str, float]]:
    """Write video to temp file and extract features."""
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        features = extract_features_from_video(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not features:
        raise HTTPException(400, "Could not extract any frames from video")
    return features


def _average_biome_states(states: list[dict[str, float]]) -> dict[str, float]:
    """Average multiple biome states for display."""
    keys = states[0].keys()
    return {k: sum(s[k] for s in states) / len(states) for k in keys}

# In-memory current gut state (updated by sensor bridge)
_current_gut_state: dict = {}
_state_lock = threading.Lock()

# Observation history for trajectory forecasting
_observation_history: list[dict] = []
_obs_lock = threading.Lock()


def _record_observation(biome_state: dict) -> None:
    """Thread-safe append to observation history. Capped at 500 entries."""
    with _obs_lock:
        _observation_history.append({
            "timestamp": time.time(),
            "biome_state": dict(biome_state),
        })
        if len(_observation_history) > 500:
            del _observation_history[0]


class SensorInput(BaseModel):
    ph: float
    h2_ppm: float = 3.5       # default if sensor not present
    ch4_ppm: float = 0.8      # default if sensor not present
    temp_c: float = 37.0      # default if sensor not present
    genre: str = "classical"


@app.post("/api/sensor")
async def sensor_input(data: SensorInput):
    """
    Receive raw sensor readings from the Arduino bridge (or demo simulator).
    Runs inference, generates a short audio clip, stores state for dashboard polling.

    Returns: biome_state + audio URL + gut score + mood label
    """
    biome_state = infer_from_sensors(
        ph=data.ph,
        h2_ppm=data.h2_ppm,
        ch4_ppm=data.ch4_ppm,
        temp_c=data.temp_c,
    )
    classification = classify_gut_state(biome_state)
    genre = data.genre if data.genre in VALID_GENRES else "classical"
    synth_params = build_bible_synth_params(
        biome_state, h2_ppm=data.h2_ppm, ch4_ppm=data.ch4_ppm, genre=genre
    )

    # Generate a short (8-second) audio clip for real-time playback
    # Short duration = fast generation = near-real-time response
    wav_bytes = generate_audio(
        biome_state,
        duration_seconds=8.0,
        config=config,
        synth_params=synth_params,
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes

    # Serialise active_instruments for JSON (drop numpy-unfriendly fields)
    active_instruments = [
        {"id": s["id"], "name": s["name"], "instrument": s["instrument"],
         "role": s["role"], "amplitude": s["amplitude"]}
        for s in synth_params["active_instruments"]
    ]

    payload = {
        "ph": round(data.ph, 2),
        "h2": round(data.h2_ppm, 2),
        "ch4": round(data.ch4_ppm, 2),
        "temp": round(data.temp_c, 2),
        "biome": biome_state,
        "state": classification["state"],
        "mood": classification["mood"],
        "score": classification["score"],
        "audio_url": f"/api/audio/{audio_id}",
        "active_instruments": active_instruments,
        "tempo_bpm": synth_params["tempo_bpm"],
        "harmonic_richness": synth_params["harmonic_richness"],
    }

    # Store for dashboard polling and trajectory history
    with _state_lock:
        _current_gut_state.update(payload)
    _record_observation(biome_state)

    return JSONResponse(payload)


@app.get("/api/sensor/state")
async def get_current_state():
    """
    Dashboard polls this endpoint every 500ms to get the latest gut state.
    Returns the last processed sensor reading.
    """
    with _state_lock:
        if not _current_gut_state:
            return JSONResponse({"status": "waiting"}, status_code=204)
        return JSONResponse(_current_gut_state)


@app.post("/api/sensor/batch")
async def sensor_batch(readings: list[SensorInput]):
    """
    Process a batch of sensor readings (e.g. from a full capsule transit).
    Returns time-series biome states + a longer evolving audio composition.
    """
    biome_series = [
        infer_from_sensors(r.ph, r.h2_ppm, r.ch4_ppm, r.temp_c)
        for r in readings
    ]

    wav_bytes = generate_audio_from_series(
        biome_series,
        duration_seconds=min(60.0, len(readings) * 2.0),
        config=config,
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes

    avg_state = _average_biome_states(biome_series)
    classification = classify_gut_state(avg_state)

    return JSONResponse({
        "biome_series": biome_series,
        "avg_biome": avg_state,
        "state": classification["state"],
        "mood": classification["mood"],
        "score": classification["score"],
        "audio_url": f"/api/audio/{audio_id}",
        "frames": len(biome_series),
    })


# ---------------------------------------------------------------------------
# Questionnaire — dietary / lifestyle inputs (Tier 3)
# ---------------------------------------------------------------------------

class QuestionnaireInput(BaseModel):
    fiber_servings: float = 3.0       # 0–10+ servings per day
    alcohol_units: float = 0.0        # 0–10+ standard units
    exercise_minutes: float = 30.0    # 0–120+ minutes per day
    stress_level: float = 3.0         # 1–10 subjective scale
    sleep_hours: float = 7.0          # 0–12 hours
    duration_seconds: float = 30.0
    seed: int | None = None
    genre: str = "classical"


def _estimate_biomarkers(q: QuestionnaireInput) -> dict:
    """
    Estimate pH / H₂ / CH₄ / temperature from dietary/lifestyle inputs.
    Based on Microbiome Sound Bible Tier 3 heuristics.
    """
    # H₂: fiber drives fermentation → hydrogen production
    h2_ppm = min(30.0, q.fiber_servings * 4.0)

    # CH₄: low fiber → methanogens dominate (inverse relationship)
    ch4_ppm = max(0.5, 8.0 - q.fiber_servings * 0.8)

    # Exercise bonus: >30 min → 1.2x H₂
    if q.exercise_minutes > 30:
        h2_ppm *= 1.2

    # Alcohol shutdown: >4 units → H₂ drops to near zero, pH rises
    if q.alcohol_units > 4:
        shutdown_factor = min(1.0, (q.alcohol_units - 4) / 4)  # ramps 4→8 units
        h2_ppm *= (1.0 - shutdown_factor * 0.9)   # drops to ~10% at 8 units
        ch4_ppm *= (1.0 - shutdown_factor * 0.5)   # also suppressed

    # pH: healthy fiber-driven fermentation lowers pH; alcohol raises it
    ph = 6.5  # baseline
    ph -= min(0.8, q.fiber_servings * 0.1)       # fiber lowers pH
    ph += min(1.5, q.alcohol_units * 0.2)         # alcohol raises pH
    # Poor sleep slightly raises pH
    if q.sleep_hours < 6:
        ph += (6 - q.sleep_hours) * 0.1

    # Temperature: stress → slightly elevated temp
    temp_c = 37.0
    if q.stress_level > 5:
        temp_c += (q.stress_level - 5) * 0.1      # up to +0.5°C at stress=10
    # Poor sleep also slightly raises temp
    if q.sleep_hours < 5:
        temp_c += (5 - q.sleep_hours) * 0.05

    return {
        "ph": round(max(4.0, min(9.0, ph)), 2),
        "h2_ppm": round(max(0.0, h2_ppm), 2),
        "ch4_ppm": round(max(0.0, ch4_ppm), 2),
        "temp_c": round(max(35.0, min(39.5, temp_c)), 2),
    }


@app.post("/api/questionnaire")
async def questionnaire(data: QuestionnaireInput):
    """
    Accept dietary/lifestyle inputs and generate music without hardware.
    Estimates biomarkers from fiber, alcohol, exercise, stress, sleep,
    then feeds into sensor inference for biome state + audio generation.
    """
    genre = data.genre if data.genre in VALID_GENRES else "classical"
    biomarkers = _estimate_biomarkers(data)

    biome_state = infer_from_sensors(
        ph=biomarkers["ph"],
        h2_ppm=biomarkers["h2_ppm"],
        ch4_ppm=biomarkers["ch4_ppm"],
        temp_c=biomarkers["temp_c"],
    )
    classification = classify_gut_state(biome_state)
    synth_params = build_bible_synth_params(
        biome_state,
        h2_ppm=biomarkers["h2_ppm"],
        ch4_ppm=biomarkers["ch4_ppm"],
        genre=genre,
    )

    wav_bytes = generate_audio(
        biome_state,
        duration_seconds=data.duration_seconds,
        seed=data.seed,
        config=config,
        synth_params=synth_params,
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes
    _record_observation(biome_state)

    active_instruments = [
        {"id": s["id"], "name": s["name"], "instrument": s["instrument"],
         "role": s["role"], "amplitude": s["amplitude"]}
        for s in synth_params["active_instruments"]
    ]

    return JSONResponse({
        "biome_state":          biome_state,
        "estimated_biomarkers": biomarkers,
        "state":                classification["state"],
        "mood":                 classification["mood"],
        "score":                classification["score"],
        "audio_url":            f"/api/audio/{audio_id}",
        "active_instruments":   active_instruments,
    })


# ---------------------------------------------------------------------------
# Comprehensive multi-channel analysis
# ---------------------------------------------------------------------------

_CHANNEL_WEIGHTS = {"visual": 1.2, "ph_temp": 1.0, "breath_gas": 0.8}
_CHANNEL_BASE_CONF = {"visual": 0.85, "ph_temp": 0.80, "breath_gas": 0.70}

_BIOME_PARAMS = [
    "diversity_index", "inflammation_score", "firmicutes_dominance",
    "bacteroidetes_dominance", "proteobacteria_bloom", "motility_activity",
    "mucosal_integrity", "metabolic_energy",
]


def _fuse_channel_states(
    channel_states: dict[str, dict],
    channels_used: list[str],
) -> dict[str, float]:
    """Weighted average fusion of multiple channel biome states."""
    if len(channels_used) == 1:
        return dict(channel_states[channels_used[0]])
    total_w = sum(_CHANNEL_WEIGHTS[ch] for ch in channels_used)
    return {
        p: round(
            sum(channel_states[ch].get(p, 0.5) * _CHANNEL_WEIGHTS[ch] for ch in channels_used) / total_w,
            4,
        )
        for p in _BIOME_PARAMS
    }


def _detect_disagreements(
    channel_states: dict[str, dict],
    channels_used: list[str],
) -> tuple[list[dict], float]:
    """Find cross-channel disagreements. Returns (list, total penalty)."""
    out: list[dict] = []
    penalty = 0.0
    for p in _BIOME_PARAMS:
        for i, ca in enumerate(channels_used):
            for cb in channels_used[i + 1:]:
                va = channel_states[ca].get(p, 0.5)
                vb = channel_states[cb].get(p, 0.5)
                delta = abs(va - vb)
                if delta > 0.2:
                    if delta > 0.6:
                        sev, pen = "high", 0.20
                    elif delta > 0.4:
                        sev, pen = "moderate", 0.10
                    else:
                        sev, pen = "low", 0.05
                    penalty += pen
                    out.append({
                        "parameter": p, "channel_a": ca, "channel_b": cb,
                        "value_a": round(va, 3), "value_b": round(vb, 3),
                        "delta": round(delta, 3), "severity": sev,
                    })
    return out, penalty


@app.post("/api/comprehensive")
async def comprehensive_analysis(
    file: UploadFile | None = File(default=None),
    ph: float | None = Form(default=None),
    temp_c: float | None = Form(default=None),
    h2_ppm: float | None = Form(default=None),
    ch4_ppm: float | None = Form(default=None),
    duration_seconds: float = Form(default=30.0),
    seed: int | None = Form(default=None),
    genre: str = Form(default="classical"),
):
    """
    Comprehensive multi-channel gut sound report.

    Fuses any combination of three input channels:
      1. VISUAL — image/video upload
      2. pH+TEMP — capsule sensor (pH + temperature)
      3. BREATH GAS — breath analyzer (H₂ + CH₄)

    Returns fused biome state, per-channel states, disagreements,
    confidence score, audio URL, and classification.
    """
    genre = genre if genre in VALID_GENRES else "classical"

    channel_states: dict[str, dict] = {}
    channels_used: list[str] = []
    missing_channels: list[str] = []

    # ── Channel 1: Visual ──────────────────────────────────────────
    has_file = file is not None and file.filename
    if has_file:
        ext = _get_extension(file.filename)
        contents = await file.read()
        if ext in IMAGE_EXTENSIONS:
            image = _bytes_to_image(contents)
            features = [extract_features(image)]
        elif ext in VIDEO_EXTENSIONS:
            features = _process_video(contents, ext)
        else:
            raise HTTPException(400, f"Unsupported file type: {ext}")

        if len(features) == 1:
            channel_states["visual"] = infer_biome_state(features[0], config)
        else:
            states_list = infer_from_frame_series(features, config)
            channel_states["visual"] = _average_biome_states(states_list)
        channels_used.append("visual")
    else:
        missing_channels.append("visual")

    # ── Channel 2: pH + Temperature capsule ────────────────────────
    has_ph_temp = ph is not None and temp_c is not None
    if has_ph_temp:
        # Use real gas values when breath channel also provided, else defaults
        eff_h2 = h2_ppm if h2_ppm is not None else 3.5
        eff_ch4 = ch4_ppm if ch4_ppm is not None else 0.8
        channel_states["ph_temp"] = infer_from_sensors(
            ph=ph, h2_ppm=eff_h2, ch4_ppm=eff_ch4, temp_c=temp_c,
        )
        channels_used.append("ph_temp")
    else:
        missing_channels.append("ph_temp")

    # ── Channel 3: Breath gas analyzer ─────────────────────────────
    has_breath = h2_ppm is not None or ch4_ppm is not None
    if has_breath:
        # Use real pH/temp when capsule channel also provided, else neutral defaults
        eff_ph = ph if ph is not None else 7.0
        eff_temp = temp_c if temp_c is not None else 37.0
        channel_states["breath_gas"] = infer_from_sensors(
            ph=eff_ph,
            h2_ppm=h2_ppm if h2_ppm is not None else 3.5,
            ch4_ppm=ch4_ppm if ch4_ppm is not None else 0.8,
            temp_c=eff_temp,
        )
        channels_used.append("breath_gas")
    else:
        missing_channels.append("breath_gas")

    if not channels_used:
        raise HTTPException(400, "At least one input channel must be provided")

    # ── Fusion ─────────────────────────────────────────────────────
    fused = _fuse_channel_states(channel_states, channels_used)

    # ── Confidence scoring ─────────────────────────────────────────
    base_conf = sum(_CHANNEL_BASE_CONF[ch] for ch in channels_used) / len(channels_used)
    corroboration = min(0.10, (len(channels_used) - 1) * 0.05)
    disagreements, penalty = _detect_disagreements(channel_states, channels_used)
    overall_confidence = round(max(0.0, min(1.0, base_conf + corroboration - penalty)), 3)

    # ── Audio generation ───────────────────────────────────────────
    synth_params = build_bible_synth_params(
        fused,
        h2_ppm=h2_ppm if h2_ppm is not None else None,
        ch4_ppm=ch4_ppm if ch4_ppm is not None else None,
        genre=genre,
    )
    wav_bytes = generate_audio(
        fused, duration_seconds=duration_seconds, seed=seed,
        config=config, synth_params=synth_params,
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes
    _record_observation(fused)

    # ── Classification ─────────────────────────────────────────────
    classification = classify_gut_state(fused)
    active_instruments = [
        {"id": s["id"], "name": s["name"], "instrument": s["instrument"],
         "role": s["role"], "amplitude": s["amplitude"]}
        for s in synth_params["active_instruments"]
    ]

    return JSONResponse({
        "fused_biome_state":  fused,
        "channel_states":     channel_states,
        "channels_used":      channels_used,
        "missing_channels":   missing_channels,
        "channels_count":     len(channels_used),
        "overall_confidence": overall_confidence,
        "disagreements":      disagreements,
        "active_instruments": active_instruments,
        "audio_url":          f"/api/audio/{audio_id}",
        "gut_score":          classification["score"],
        "state":              classification["state"],
        "mood":               classification["mood"],
    })


# ---------------------------------------------------------------------------
# Trajectory forecasting
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    horizon_seconds: float = 86_400.0
    n_steps: int = 48
    events: list[dict] = []
    observations: list[dict] | None = None   # overrides history if provided
    genre: str = "classical"


def _instrument_trajectory(predictions: dict, t_steps: list[float]) -> dict:
    """
    For each prediction step, compute which instruments would be active.
    Returns {species_id: [amplitude, ...]} for frontend timeline animation.
    """
    n = len(t_steps)
    trajectories: dict[str, list[float]] = {sp["id"]: [0.0] * n for sp in SPECIES_CATALOG}

    for i in range(n):
        state = {k: predictions[k]["mean"][i] for k in BIOME_KEYS}
        for sp in compute_active_instruments(state):
            trajectories[sp["id"]][i] = sp["amplitude"]

    return trajectories


@app.post("/api/predict")
async def predict(data: PredictRequest):
    """
    Forecast gut biome state trajectory.

    Uses Gaussian Process regression on observation history (or provided
    observations) and overlays physiological event response curves.

    Returns predicted mean ± 95% CI per biome parameter, per-step confidence,
    and an instrument_trajectory showing which species play at each step.
    """
    obs = data.observations
    if obs is None:
        with _obs_lock:
            obs = list(_observation_history)

    result = forecast(
        observations=obs,
        horizon_seconds=data.horizon_seconds,
        n_steps=data.n_steps,
        events=data.events,
        t_now=time.time() if obs and "timestamp" in obs[0] else 0.0,
    )

    result["instrument_trajectory"] = _instrument_trajectory(
        result["predictions"], result["t_steps"]
    )
    return JSONResponse(result)


@app.post("/api/predict/audio")
async def predict_audio(data: PredictRequest):
    """
    Same as /api/predict but also generates audio from the predicted trajectory
    so users can hear where their gut is heading.

    Audio duration is scaled: horizon ≤ 1h → 15s, ≤ 24h → 45s, else 60s.
    """
    obs = data.observations
    if obs is None:
        with _obs_lock:
            obs = list(_observation_history)

    result = forecast(
        observations=obs,
        horizon_seconds=data.horizon_seconds,
        n_steps=data.n_steps,
        events=data.events,
        t_now=time.time() if obs and "timestamp" in obs[0] else 0.0,
    )

    # Build biome state series from predicted means
    biome_series = [
        {k: result["predictions"][k]["mean"][i] for k in BIOME_KEYS}
        for i in range(len(result["t_steps"]))
    ]

    # Scale audio length to horizon
    h = data.horizon_seconds
    audio_dur = 15.0 if h <= 3_600 else (45.0 if h <= 86_400 else 60.0)
    pred_genre = data.genre if data.genre in VALID_GENRES else "classical"

    # Render each predicted step with species engine + genre
    pred_synth_series = [
        build_bible_synth_params(bs, genre=pred_genre) for bs in biome_series
    ]
    # Use the first step's synth_params to drive a single generation
    wav_bytes = generate_audio(
        biome_series[len(biome_series) // 2],
        duration_seconds=audio_dur,
        config=config,
        synth_params=pred_synth_series[len(pred_synth_series) // 2],
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes

    result["audio_url"] = f"/api/audio/{audio_id}"
    result["instrument_trajectory"] = _instrument_trajectory(
        result["predictions"], result["t_steps"]
    )
    return JSONResponse(result)


@app.get("/api/predict/history")
async def get_predict_history():
    """Return current observation history used for forecasting."""
    with _obs_lock:
        history = list(_observation_history)
    return JSONResponse({"observations": history, "count": len(history)})


@app.delete("/api/predict/history")
async def clear_predict_history():
    """Clear observation history."""
    with _obs_lock:
        _observation_history.clear()
    return JSONResponse({"status": "cleared", "count": 0})
