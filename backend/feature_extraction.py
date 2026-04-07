"""
Visual feature extraction from gut endoscopy images using OpenCV.
Extracts color, texture, surface, and motion features.
"""

import cv2
import numpy as np
from typing import Optional


def extract_features(image: np.ndarray) -> dict[str, float]:
    """Extract visual features from a single BGR image frame."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # Normalize channels to 0-1
    h_norm = h.astype(np.float64) / 180.0
    s_norm = s.astype(np.float64) / 255.0
    v_norm = v.astype(np.float64) / 255.0

    features = {}

    # --- Color features (HSV space) ---
    features["dominant_hue"] = _dominant_hue(h_norm)
    features["saturation_mean"] = float(np.mean(s_norm))
    features["value_mean"] = float(np.mean(v_norm))
    features["color_variance"] = _color_variance(h_norm, s_norm, v_norm)
    features["redness_ratio"] = _redness_ratio(image, hsv)

    # --- Texture features (Gabor + GLCM-inspired) ---
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    features["texture_energy"] = _texture_energy(gray)
    features["texture_entropy"] = _texture_entropy(gray)
    features["edge_density"] = _edge_density(gray)

    # --- Surface features ---
    features["specular_ratio"] = _specular_ratio(v_norm, s_norm)
    features["brightness_variance"] = float(np.std(v_norm))

    # Motion features default to 0 for single images
    features["motion_magnitude"] = 0.0
    features["motion_direction_variance"] = 0.0

    # Clamp all to [0, 1]
    for k in features:
        features[k] = float(np.clip(features[k], 0.0, 1.0))

    return features


def extract_features_from_video(
    video_path: str, fps_sample: float = 1.0
) -> list[dict[str, float]]:
    """Extract features from video frames at the given sample rate."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, int(video_fps / fps_sample))

    all_features = []
    prev_gray: Optional[np.ndarray] = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            feats = extract_features(frame)

            # Compute motion features if we have a previous frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                mag, dir_var = _compute_motion(prev_gray, gray)
                feats["motion_magnitude"] = float(np.clip(mag, 0.0, 1.0))
                feats["motion_direction_variance"] = float(np.clip(dir_var, 0.0, 1.0))
            prev_gray = gray

            all_features.append(feats)

        frame_idx += 1

    cap.release()
    return all_features


# --- Internal helpers ---


def _dominant_hue(h_norm: np.ndarray) -> float:
    """Find the dominant hue using a histogram."""
    hist, _ = np.histogram(h_norm.ravel(), bins=36, range=(0, 1))
    dominant_bin = np.argmax(hist)
    return float((dominant_bin + 0.5) / 36.0)


def _color_variance(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> float:
    """Measure color heterogeneity across all HSV channels."""
    variance = np.std(h) * 0.4 + np.std(s) * 0.3 + np.std(v) * 0.3
    return float(np.clip(variance * 3.0, 0.0, 1.0))  # scale up for sensitivity


def _redness_ratio(bgr: np.ndarray, hsv: np.ndarray) -> float:
    """Compute ratio of red/inflamed pixels.
    Red in HSV wraps around 0/180, so check both ends.
    """
    h, s, v = cv2.split(hsv)
    # Red hue ranges: 0-10 and 170-180, with decent saturation
    mask_low = (h <= 10) & (s > 50) & (v > 50)
    mask_high = (h >= 170) & (s > 50) & (v > 50)
    red_pixels = np.sum(mask_low | mask_high)
    total_pixels = h.shape[0] * h.shape[1]
    ratio = red_pixels / total_pixels
    # Scale up — endoscopy images are often mostly red-ish
    return float(np.clip(ratio * 2.0, 0.0, 1.0))


def _texture_energy(gray: np.ndarray) -> float:
    """Gabor filter bank energy as texture complexity measure."""
    energies = []
    for theta in [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]:
        for frequency in [0.1, 0.2, 0.4]:
            kernel = cv2.getGaborKernel(
                (21, 21), sigma=4.0, theta=theta, lambd=1.0 / frequency,
                gamma=0.5, psi=0
            )
            filtered = cv2.filter2D(gray, cv2.CV_64F, kernel)
            energies.append(np.mean(np.abs(filtered)))
    mean_energy = np.mean(energies)
    return float(np.clip(mean_energy / 128.0, 0.0, 1.0))


def _texture_entropy(gray: np.ndarray) -> float:
    """Entropy of grayscale histogram as disorder measure."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.ravel() / hist.sum()
    hist = hist[hist > 0]
    entropy = -np.sum(hist * np.log2(hist))
    # Max entropy for 256 bins = 8, normalize
    return float(np.clip(entropy / 8.0, 0.0, 1.0))


def _edge_density(gray: np.ndarray) -> float:
    """Fraction of edge pixels using Canny."""
    edges = cv2.Canny(gray, 50, 150)
    return float(np.mean(edges > 0))


def _specular_ratio(v_norm: np.ndarray, s_norm: np.ndarray) -> float:
    """Detect specular highlights (high brightness, low saturation) as moisture proxy."""
    specular_mask = (v_norm > 0.85) & (s_norm < 0.3)
    return float(np.mean(specular_mask))


def _compute_motion(
    prev_gray: np.ndarray, curr_gray: np.ndarray
) -> tuple[float, float]:
    """Compute optical flow magnitude and direction variance."""
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    mean_mag = np.mean(mag)
    # Normalize magnitude (typical values 0-20 pixels)
    norm_mag = np.clip(mean_mag / 10.0, 0.0, 1.0)
    # Direction variance (circular std)
    dir_var = np.std(ang) / np.pi  # normalize by pi
    return norm_mag, np.clip(dir_var, 0.0, 1.0)
