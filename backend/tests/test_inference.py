"""Tests for the inference bridge module."""

import pytest

from inference import infer_biome_state, infer_from_frame_series, load_config


def _make_features(**overrides) -> dict[str, float]:
    """Create a complete feature dict with defaults and optional overrides."""
    defaults = {
        "dominant_hue": 0.5,
        "saturation_mean": 0.5,
        "value_mean": 0.5,
        "color_variance": 0.5,
        "redness_ratio": 0.5,
        "texture_energy": 0.5,
        "texture_entropy": 0.5,
        "edge_density": 0.5,
        "specular_ratio": 0.5,
        "brightness_variance": 0.5,
        "motion_magnitude": 0.0,
        "motion_direction_variance": 0.0,
    }
    defaults.update(overrides)
    return defaults


class TestInferBiomeState:

    def test_returns_all_expected_keys(self):
        features = _make_features()
        config = load_config()
        biome = infer_biome_state(features, config)

        expected_keys = {
            "diversity_index", "inflammation_score",
            "firmicutes_dominance", "bacteroidetes_dominance",
            "proteobacteria_bloom", "motility_activity",
            "mucosal_integrity", "metabolic_energy",
        }
        assert set(biome.keys()) == expected_keys

    def test_all_values_in_range(self):
        features = _make_features()
        biome = infer_biome_state(features)

        for key, value in biome.items():
            assert 0.0 <= value <= 1.0, f"{key} = {value} is out of [0, 1]"

    def test_high_redness_high_inflammation(self):
        low_red = _make_features(redness_ratio=0.1)
        high_red = _make_features(redness_ratio=0.9)

        biome_low = infer_biome_state(low_red)
        biome_high = infer_biome_state(high_red)

        assert biome_high["inflammation_score"] > biome_low["inflammation_score"]

    def test_high_texture_high_diversity(self):
        low_tex = _make_features(texture_energy=0.1, edge_density=0.1, color_variance=0.1)
        high_tex = _make_features(texture_energy=0.9, edge_density=0.9, color_variance=0.9)

        biome_low = infer_biome_state(low_tex)
        biome_high = infer_biome_state(high_tex)

        assert biome_high["diversity_index"] > biome_low["diversity_index"]

    def test_motion_affects_motility(self):
        no_motion = _make_features(motion_magnitude=0.0)
        high_motion = _make_features(motion_magnitude=0.9)

        biome_still = infer_biome_state(no_motion)
        biome_moving = infer_biome_state(high_motion)

        assert biome_moving["motility_activity"] > biome_still["motility_activity"]

    def test_high_inflammation_low_integrity(self):
        """High redness + specular should reduce mucosal integrity."""
        healthy = _make_features(redness_ratio=0.1, specular_ratio=0.1, brightness_variance=0.1)
        inflamed = _make_features(redness_ratio=0.9, specular_ratio=0.9, brightness_variance=0.9)

        biome_healthy = infer_biome_state(healthy)
        biome_inflamed = infer_biome_state(inflamed)

        assert biome_healthy["mucosal_integrity"] > biome_inflamed["mucosal_integrity"]

    def test_zero_features_valid(self):
        features = {k: 0.0 for k in _make_features()}
        biome = infer_biome_state(features)

        for v in biome.values():
            assert 0.0 <= v <= 1.0

    def test_max_features_valid(self):
        features = {k: 1.0 for k in _make_features()}
        biome = infer_biome_state(features)

        for v in biome.values():
            assert 0.0 <= v <= 1.0


class TestInferFromFrameSeries:

    def test_returns_list_of_correct_length(self):
        series = [_make_features() for _ in range(5)]
        result = infer_from_frame_series(series)
        assert len(result) == 5

    def test_each_frame_has_all_keys(self):
        series = [_make_features(), _make_features(redness_ratio=0.9)]
        result = infer_from_frame_series(series)

        for biome in result:
            assert len(biome) == 8
