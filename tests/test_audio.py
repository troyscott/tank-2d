import numpy as np

from tanks import audio
from tanks import config as C


def test_synth_functions_return_finite_arrays():
    for name, synth in audio._SYNTHS.items():
        sig = synth()
        assert isinstance(sig, np.ndarray), f"{name} must return ndarray"
        assert sig.size > 0, f"{name} produced empty signal"
        assert np.all(np.isfinite(sig)), f"{name} produced NaN/inf"
        assert np.max(np.abs(sig)) <= 1.0 + 1e-6, f"{name} not in [-1, 1]"


def test_synth_durations_are_within_a_reasonable_range():
    sr = C.AUDIO_SAMPLE_RATE
    for name, synth in audio._SYNTHS.items():
        sig = synth()
        dur = sig.shape[0] / sr
        assert 0.02 <= dur <= 1.0, f"{name} duration {dur:.3f}s out of range"


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
