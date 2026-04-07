"""Tests for visual feature extraction module."""

import numpy as np
import cv2
import pytest

from feature_extraction import extract_features, extract_features_from_video


def _make_test_image(width=640, height=480, color=(100, 50, 50)):
    """Create a synthetic BGR image for testing."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    return img


def _make_textured_image(width=640, height=480):
    """Create an image with some texture (stripes)."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            if (x // 20) % 2 == 0:
                img[y, x] = [120, 80, 80]
            else:
                img[y, x] = [60, 40, 40]
    return img


def _make_red_image(width=640, height=480):
    """Create a predominantly red image (inflamed tissue proxy)."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # BGR: blue=0, green=30, red=200
    img[:] = [0, 30, 200]
    return img


class TestExtractFeatures:
    """Tests for the extract_features function."""

    def test_returns_all_expected_keys(self):
        img = _make_test_image()
        features = extract_features(img)

        expected_keys = {
            "dominant_hue", "saturation_mean", "value_mean",
            "color_variance", "redness_ratio",
            "texture_energy", "texture_entropy", "edge_density",
            "specular_ratio", "brightness_variance",
            "motion_magnitude", "motion_direction_variance",
        }
        assert set(features.keys()) == expected_keys

    def test_all_values_in_range(self):
        img = _make_test_image()
        features = extract_features(img)

        for key, value in features.items():
            assert 0.0 <= value <= 1.0, f"{key} = {value} is out of [0, 1]"

    def test_motion_features_zero_for_single_image(self):
        img = _make_test_image()
        features = extract_features(img)

        assert features["motion_magnitude"] == 0.0
        assert features["motion_direction_variance"] == 0.0

    def test_uniform_image_low_variance(self):
        img = _make_test_image(color=(100, 100, 100))
        features = extract_features(img)

        assert features["color_variance"] < 0.1
        assert features["brightness_variance"] < 0.05

    def test_textured_image_higher_texture_energy(self):
        uniform = _make_test_image()
        textured = _make_textured_image()

        feat_uniform = extract_features(uniform)
        feat_textured = extract_features(textured)

        assert feat_textured["edge_density"] > feat_uniform["edge_density"]

    def test_red_image_high_redness(self):
        red = _make_red_image()
        features = extract_features(red)

        assert features["redness_ratio"] > 0.3

    def test_dark_image_low_value(self):
        dark = _make_test_image(color=(10, 10, 10))
        features = extract_features(dark)

        assert features["value_mean"] < 0.15

    def test_bright_image_high_value(self):
        bright = _make_test_image(color=(230, 230, 230))
        features = extract_features(bright)

        assert features["value_mean"] > 0.7

    def test_specular_highlights(self):
        """Bright, low-saturation areas should register as specular."""
        # Create image with specular-like highlights
        img = _make_test_image(color=(100, 100, 100))
        # Add bright low-sat region (top half)
        img[:240, :] = [240, 240, 245]  # near-white in BGR
        features = extract_features(img)

        assert features["specular_ratio"] > 0.0

    def test_different_images_produce_different_features(self):
        red = _make_red_image()
        dark = _make_test_image(color=(10, 10, 10))

        f1 = extract_features(red)
        f2 = extract_features(dark)

        # They should differ on multiple features
        diffs = sum(1 for k in f1 if abs(f1[k] - f2[k]) > 0.05)
        assert diffs >= 3


class TestExtractFeaturesFromVideo:
    def test_invalid_video_raises(self):
        with pytest.raises(ValueError, match="Cannot open video"):
            extract_features_from_video("/nonexistent/video.mp4")
