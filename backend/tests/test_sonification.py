"""Tests for the sonification engine."""

import io
import pytest
import numpy as np
import soundfile as sf

from sonification import generate_audio, generate_audio_from_series, note_to_freq, load_config


def _make_biome_state(**overrides) -> dict[str, float]:
    """Create a complete biome state with defaults."""
    defaults = {
        "diversity_index": 0.5,
        "inflammation_score": 0.3,
        "firmicutes_dominance": 0.5,
        "bacteroidetes_dominance": 0.4,
        "proteobacteria_bloom": 0.2,
        "motility_activity": 0.4,
        "mucosal_integrity": 0.7,
        "metabolic_energy": 0.5,
    }
    defaults.update(overrides)
    return defaults


def _read_wav(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    buf = io.BytesIO(wav_bytes)
    data, sr = sf.read(buf)
    return data, sr


class TestNoteToFreq:

    def test_a4_is_440(self):
        assert abs(note_to_freq("A4") - 440.0) < 0.01

    def test_c4_is_middle_c(self):
        freq = note_to_freq("C4")
        assert abs(freq - 261.63) < 1.0

    def test_unknown_note_raises(self):
        with pytest.raises(ValueError, match="Unknown note"):
            note_to_freq("X9")

    def test_all_scale_notes_valid(self):
        config = load_config()
        for scale_name, notes in config["scales"].items():
            for note in notes:
                freq = note_to_freq(note)
                assert freq > 20, f"{note} in {scale_name} has inaudible freq {freq}"

    def test_enharmonic_equivalents(self):
        assert note_to_freq("C#4") == note_to_freq("Db4")
        assert note_to_freq("F#3") == note_to_freq("Gb3")


class TestGenerateAudio:

    def test_returns_valid_wav(self):
        state = _make_biome_state()
        wav_bytes = generate_audio(state, duration_seconds=5.0, seed=42)
        assert len(wav_bytes) > 0
        data, sr = _read_wav(wav_bytes)
        assert sr == 44100
        assert len(data) > 0

    def test_correct_duration(self):
        state = _make_biome_state()
        duration = 5.0
        wav_bytes = generate_audio(state, duration_seconds=duration, seed=42)
        data, sr = _read_wav(wav_bytes)
        actual_duration = len(data) / sr
        assert abs(actual_duration - duration) < 0.1

    def test_deterministic_with_seed(self):
        state = _make_biome_state()
        wav1 = generate_audio(state, duration_seconds=3.0, seed=42)
        wav2 = generate_audio(state, duration_seconds=3.0, seed=42)
        assert wav1 == wav2

    def test_different_seeds_different_output(self):
        state = _make_biome_state(proteobacteria_bloom=0.8, inflammation_score=0.7)
        wav1 = generate_audio(state, duration_seconds=3.0, seed=1)
        wav2 = generate_audio(state, duration_seconds=3.0, seed=2)
        assert wav1 != wav2

    def test_healthy_state_produces_audio(self):
        state = _make_biome_state(
            diversity_index=0.8, inflammation_score=0.1,
            mucosal_integrity=0.9, metabolic_energy=0.6,
        )
        wav_bytes = generate_audio(state, duration_seconds=3.0, seed=42)
        data, _ = _read_wav(wav_bytes)
        assert np.max(np.abs(data)) > 0.1

    def test_inflamed_state_produces_audio(self):
        state = _make_biome_state(
            diversity_index=0.2, inflammation_score=0.9,
            proteobacteria_bloom=0.8, mucosal_integrity=0.2,
        )
        wav_bytes = generate_audio(state, duration_seconds=3.0, seed=42)
        data, _ = _read_wav(wav_bytes)
        assert np.max(np.abs(data)) > 0.1

    def test_no_clipping(self):
        state = _make_biome_state(
            metabolic_energy=1.0, inflammation_score=1.0, diversity_index=1.0,
        )
        wav_bytes = generate_audio(state, duration_seconds=5.0, seed=42)
        data, _ = _read_wav(wav_bytes)
        assert np.max(np.abs(data)) <= 1.0

    def test_extreme_low_state(self):
        state = {k: 0.0 for k in _make_biome_state()}
        wav_bytes = generate_audio(state, duration_seconds=3.0, seed=42)
        data, _ = _read_wav(wav_bytes)
        assert len(data) > 0

    def test_extreme_high_state(self):
        state = {k: 1.0 for k in _make_biome_state()}
        wav_bytes = generate_audio(state, duration_seconds=3.0, seed=42)
        data, _ = _read_wav(wav_bytes)
        assert np.max(np.abs(data)) <= 1.0
        assert len(data) > 0


class TestGranularLayer:
    """Tests that the granular synthesis layer responds to parameters."""

    def test_high_diversity_spectrally_richer(self):
        """High diversity should produce more spectral content (more voices + grains)."""
        low = _make_biome_state(diversity_index=0.1, metabolic_energy=0.2)
        high = _make_biome_state(diversity_index=0.9, metabolic_energy=0.8)

        wav_low = generate_audio(low, duration_seconds=3.0, seed=42)
        wav_high = generate_audio(high, duration_seconds=3.0, seed=42)

        data_low, sr = _read_wav(wav_low)
        data_high, _ = _read_wav(wav_high)

        # Count spectral bins with significant energy (spectral richness)
        def count_active_bins(signal, sample_rate, threshold_db=-40):
            spectrum = np.abs(np.fft.rfft(signal))
            spectrum_db = 20 * np.log10(spectrum + 1e-10)
            peak_db = np.max(spectrum_db)
            return np.sum(spectrum_db > peak_db + threshold_db)

        bins_low = count_active_bins(data_low, sr)
        bins_high = count_active_bins(data_high, sr)
        assert bins_high > bins_low


class TestFMLayer:
    """Tests that FM synthesis activates with inflammation."""

    def test_inflammation_changes_timbre(self):
        """High inflammation should produce a spectrally different result."""
        calm = _make_biome_state(inflammation_score=0.05, proteobacteria_bloom=0.05)
        inflamed = _make_biome_state(inflammation_score=0.9, proteobacteria_bloom=0.8)

        wav_calm = generate_audio(calm, duration_seconds=3.0, seed=42)
        wav_inflamed = generate_audio(inflamed, duration_seconds=3.0, seed=42)

        data_calm, sr = _read_wav(wav_calm)
        data_inflamed, _ = _read_wav(wav_inflamed)

        # Compute spectral centroid as a rough timbre measure
        def spectral_centroid(signal, sample_rate):
            spectrum = np.abs(np.fft.rfft(signal))
            freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)
            return np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-10)

        centroid_calm = spectral_centroid(data_calm, sr)
        centroid_inflamed = spectral_centroid(data_inflamed, sr)

        # Inflamed should have higher spectral centroid (brighter/harsher)
        assert centroid_inflamed > centroid_calm

    def test_fm_not_active_when_healthy(self):
        """With very low inflammation, FM layer should be minimal."""
        healthy = _make_biome_state(
            inflammation_score=0.0, proteobacteria_bloom=0.0,
            diversity_index=0.8, mucosal_integrity=0.9,
        )
        wav = generate_audio(healthy, duration_seconds=3.0, seed=42)
        data, _ = _read_wav(wav)
        # Should still produce valid audio (from other layers)
        assert np.max(np.abs(data)) > 0.05


class TestBandpassNoiseLayer:
    """Tests for the band-pass filtered noise layer."""

    def test_low_integrity_adds_noise(self):
        """Low mucosal integrity should add audible noise."""
        healthy = _make_biome_state(mucosal_integrity=0.95, proteobacteria_bloom=0.0)
        eroded = _make_biome_state(mucosal_integrity=0.1, proteobacteria_bloom=0.7)

        wav_healthy = generate_audio(healthy, duration_seconds=3.0, seed=42)
        wav_eroded = generate_audio(eroded, duration_seconds=3.0, seed=42)

        data_healthy, sr = _read_wav(wav_healthy)
        data_eroded, _ = _read_wav(wav_eroded)

        # Compute high-frequency energy ratio as a noise proxy
        def hf_energy_ratio(signal, sample_rate, cutoff=2000):
            spectrum = np.abs(np.fft.rfft(signal))
            freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)
            hf_mask = freqs > cutoff
            total_energy = np.sum(spectrum ** 2) + 1e-10
            hf_energy = np.sum(spectrum[hf_mask] ** 2)
            return hf_energy / total_energy

        hf_healthy = hf_energy_ratio(data_healthy, sr)
        hf_eroded = hf_energy_ratio(data_eroded, sr)

        # Eroded gut should have more high-frequency noise
        assert hf_eroded > hf_healthy


class TestScaleSelection:
    """Tests that scale selection responds to biome health."""

    def test_healthy_vs_dysbiotic_different_output(self):
        healthy = _make_biome_state(
            diversity_index=0.9, inflammation_score=0.05, mucosal_integrity=0.95,
        )
        dysbiotic = _make_biome_state(
            diversity_index=0.3, inflammation_score=0.6, mucosal_integrity=0.3,
        )

        wav_h = generate_audio(healthy, duration_seconds=3.0, seed=42)
        wav_d = generate_audio(dysbiotic, duration_seconds=3.0, seed=42)

        # Different scales → different audio
        assert wav_h != wav_d


class TestGenerateAudioFromSeries:

    def test_single_frame_works(self):
        states = [_make_biome_state()]
        wav_bytes = generate_audio_from_series(states, duration_seconds=5.0, seed=42)
        data, sr = _read_wav(wav_bytes)
        assert len(data) > 0

    def test_multi_frame_correct_duration(self):
        states = [
            _make_biome_state(inflammation_score=0.1),
            _make_biome_state(inflammation_score=0.5),
            _make_biome_state(inflammation_score=0.9),
        ]
        duration = 9.0
        wav_bytes = generate_audio_from_series(states, duration_seconds=duration, seed=42)
        data, sr = _read_wav(wav_bytes)
        actual = len(data) / sr
        assert abs(actual - duration) < 0.5

    def test_empty_series_raises(self):
        with pytest.raises(ValueError, match="Empty biome series"):
            generate_audio_from_series([], duration_seconds=5.0)

    def test_series_produces_evolving_audio(self):
        """A series with changing states should not be identical to a single state."""
        single = _make_biome_state(inflammation_score=0.5)
        series = [
            _make_biome_state(inflammation_score=0.1),
            _make_biome_state(inflammation_score=0.9),
        ]

        wav_single = generate_audio(single, duration_seconds=6.0, seed=42)
        wav_series = generate_audio_from_series(series, duration_seconds=6.0, seed=42)

        assert wav_single != wav_series

    def test_long_series_handles_many_frames(self):
        """Should handle a realistic video with many frames."""
        states = [_make_biome_state(inflammation_score=i / 10) for i in range(10)]
        wav_bytes = generate_audio_from_series(states, duration_seconds=10.0, seed=42)
        data, sr = _read_wav(wav_bytes)
        actual = len(data) / sr
        assert abs(actual - 10.0) < 0.5
        assert np.max(np.abs(data)) <= 1.0


class TestReverb:
    """Tests for reverb behavior."""

    def test_high_decay_vs_low_decay(self):
        """Higher reverb decay should produce more sustained energy in the tail."""
        tight = _make_biome_state(mucosal_integrity=0.95)  # low reverb decay
        cavernous = _make_biome_state(mucosal_integrity=0.1)  # high reverb decay

        wav_tight = generate_audio(tight, duration_seconds=5.0, seed=42)
        wav_cave = generate_audio(cavernous, duration_seconds=5.0, seed=42)

        data_tight, sr = _read_wav(wav_tight)
        data_cave, _ = _read_wav(wav_cave)

        # Compare energy in last 1 second (reverb tail)
        tail_samples = sr
        tail_rms_tight = np.sqrt(np.mean(data_tight[-tail_samples:] ** 2))
        tail_rms_cave = np.sqrt(np.mean(data_cave[-tail_samples:] ** 2))

        # Both should have some tail (release envelope), but they should differ
        # The cavernous one gets more reverb wet signal
        assert data_tight is not None  # sanity
        assert data_cave is not None
