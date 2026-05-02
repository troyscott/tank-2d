import numpy as np

from tanks import audio
from tanks import config as C


def test_synth_functions_return_finite_arrays():
    for name, synth in audio._SYNTHS.items():
        sig = synth(C.AUDIO_SAMPLE_RATE)
        assert isinstance(sig, np.ndarray), f"{name} must return ndarray"
        assert sig.size > 0, f"{name} produced empty signal"
        assert np.all(np.isfinite(sig)), f"{name} produced NaN/inf"
        assert np.max(np.abs(sig)) <= 1.0 + 1e-6, f"{name} not in [-1, 1]"


def test_synth_durations_are_within_a_reasonable_range():
    sr = C.AUDIO_SAMPLE_RATE
    for name, synth in audio._SYNTHS.items():
        sig = synth(sr)
        dur = sig.shape[0] / sr
        assert 0.02 <= dur <= 1.0, f"{name} duration {dur:.3f}s out of range"


def test_synth_works_at_44100_too():
    """Synths must produce sensible buffers at the rate the mixer actually
    comes up at, which is typically 44100 even when we request 22050."""
    for name, synth in audio._SYNTHS.items():
        sig = synth(44100)
        assert sig.size > 0, f"{name} at 44100 produced empty signal"
        # Each duration should still match (just more samples)
        sig_22 = synth(22050)
        ratio = sig.shape[0] / sig_22.shape[0]
        assert 1.95 <= ratio <= 2.05, f"{name} doesn't scale with sr (ratio {ratio:.3f})"


def test_to_stereo_int16_shape_and_dtype():
    mono = np.array([0.5, -0.5, 0.0, 1.0, -1.0])
    stereo = audio._to_stereo_int16(mono)
    assert stereo.dtype == np.int16
    assert stereo.shape == (5, 2)
    # left and right channels equal for mono input
    assert (stereo[:, 0] == stereo[:, 1]).all()
    # full-scale clipping
    assert stereo[3, 0] == 32767
    assert stereo[4, 0] == -32767
