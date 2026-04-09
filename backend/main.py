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
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
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

app = FastAPI(title="Biome Sound API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8049",
        "https://frontend-lemon-five-25.vercel.app",
        "https://frontend-hd4op2veb-raza-jafris-projects.vercel.app",
        "https://frontend-cuyibpx6q-raza-jafris-projects.vercel.app",
    ],
    allow_origin_regex=r"https://frontend-.*-raza-jafris-projects\.vercel\.app",
    allow_credentials=True,
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


@app.post("/api/generate")
async def generate(data: BiomeStateInput):
    """Generate audio from biome state parameters. Returns WAV binary."""
    wav_bytes = generate_audio(
        data.biome_state,
        duration_seconds=data.duration_seconds,
        seed=data.seed,
        config=config,
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
):
    """All-in-one endpoint: upload → analyze → infer → generate.
    Returns biome state + audio URL.
    """
    ext = _get_extension(file.filename)
    contents = await file.read()

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
        # Step 3: Audio generation
        wav_bytes = generate_audio(
            biome_state, duration_seconds=duration_seconds, seed=seed, config=config
        )
        biome_response = biome_state
    else:
        biome_states = infer_from_frame_series(features, config)
        wav_bytes = generate_audio_from_series(
            biome_states, duration_seconds=duration_seconds, seed=seed, config=config
        )
        # Return the average biome state for display
        biome_response = _average_biome_states(biome_states)

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}


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


class SensorInput(BaseModel):
    ph: float
    h2_ppm: float = 3.5       # default if sensor not present
    ch4_ppm: float = 0.8      # default if sensor not present
    temp_c: float = 37.0      # default if sensor not present


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

    # Generate a short (8-second) audio clip for real-time playback
    # Short duration = fast generation = near-real-time response
    wav_bytes = generate_audio(
        biome_state,
        duration_seconds=8.0,
        config=config,
    )

    audio_id = str(uuid.uuid4())
    _audio_store[audio_id] = wav_bytes

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
    }

    # Store for dashboard polling
    with _state_lock:
        _current_gut_state.update(payload)

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
