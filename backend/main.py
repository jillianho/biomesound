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

app = FastAPI(title="Biome Sound API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
