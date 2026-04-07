"""
Inference bridge: maps visual features to estimated biome state parameters.
Uses SMEAR-informed heuristic mappings defined in mapping_config.json.
"""

import json
from pathlib import Path
from typing import Optional


def load_config(config_path: Optional[str] = None) -> dict:
    """Load the mapping configuration."""
    if config_path is None:
        config_path = str(Path(__file__).parent / "mapping_config.json")
    with open(config_path) as f:
        return json.load(f)


def infer_biome_state(
    features: dict[str, float],
    config: Optional[dict] = None,
) -> dict[str, float]:
    """
    Map visual features to biome state parameters.

    For parameters that depend on other biome parameters (e.g., mucosal_integrity
    depends on inflammation_score), we compute in two passes.
    """
    if config is None:
        config = load_config()

    inference_config = config["inference"]

    # First pass: compute parameters that only depend on visual features
    biome_state: dict[str, float] = {}
    deferred: dict[str, dict] = {}

    for param_name, param_config in inference_config.items():
        sources = param_config["sources"]
        bias = param_config.get("bias", 0.0)

        # Check if any source references another biome parameter
        has_biome_dep = any(
            src not in features and src in inference_config
            for src in sources
        )

        if has_biome_dep:
            deferred[param_name] = param_config
        else:
            biome_state[param_name] = _compute_weighted(features, sources, bias)

    # Second pass: compute deferred parameters using already-computed biome values
    combined = {**features, **biome_state}
    for param_name, param_config in deferred.items():
        sources = param_config["sources"]
        bias = param_config.get("bias", 0.0)
        biome_state[param_name] = _compute_weighted(combined, sources, bias)

    return biome_state


def infer_from_frame_series(
    feature_series: list[dict[str, float]],
    config: Optional[dict] = None,
) -> list[dict[str, float]]:
    """Infer biome state for each frame in a time series."""
    if config is None:
        config = load_config()
    return [infer_biome_state(f, config) for f in feature_series]


def _compute_weighted(
    values: dict[str, float],
    sources: dict[str, float],
    bias: float = 0.0,
) -> float:
    """Compute weighted combination of source values.

    Negative weights in the config indicate inverse relationships
    (e.g., specular_ratio: -0.4 means higher specular = lower output).
    """
    result = bias
    for source_name, weight in sources.items():
        value = values.get(source_name, 0.0)
        result += value * weight

    return max(0.0, min(1.0, result))
