"""Procedurally synthesized SFX.

Sample rate is determined at init time by what `pygame.mixer.get_init()`
actually reports, NOT what we requested — pygame doesn't resample, and on
many platforms the mixer ignores the rate argument and comes up at its native
rate (typically 44100). Synthesizing at the wrong rate plays sounds at the
wrong speed and pitch, which can sound like multiple events for a single
play call.

Synth functions take `sr` as a parameter and are only invoked after the
mixer is up. numpy is imported lazily so module import doesn't require it
(pygbag/pyodide installs wheels asynchronously).
"""
import pygame

from . import config as C


def _np():
    import numpy as np  # noqa: PLC0415
    return np


def _to_stereo_int16(mono_float):
    np = _np()
    clipped = np.clip(mono_float, -1.0, 1.0)
    int16 = (clipped * 32767).astype(np.int16)
    stereo = np.column_stack([int16, int16])
    return np.ascontiguousarray(stereo)


def _synth_fire(sr: int):
    """Tank firing — single bass thump, pure sine sweep."""
    np = _np()
    duration = 0.15
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    pitch = np.linspace(180.0, 60.0, n)
    phase = 2 * np.pi * np.cumsum(pitch) / sr
    return np.sin(phase) * np.exp(-t * 12.0) * 0.7


def _synth_explosion(sr: int):
    """Projectile in dirt — short, bright noise burst."""
    np = _np()
    duration = 0.15
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    rng = np.random.default_rng(2)
    noise = rng.uniform(-1.0, 1.0, n)
    body = np.convolve(noise, np.ones(5) / 5, mode="same")
    env = np.minimum(t / 0.002, 1.0) * np.exp(-t * 16.0)
    return body * env * 0.75


def _synth_hit(sr: int):
    """Projectile on tank — single deep thud. Same shape as `explosion`,
    just darker (heavier low-pass) and slightly longer/louder.
    """
    np = _np()
    duration = 0.18
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    rng = np.random.default_rng(3)
    noise = rng.uniform(-1.0, 1.0, n)
    body = np.convolve(noise, np.ones(20) / 20, mode="same")
    env = np.minimum(t / 0.002, 1.0) * np.exp(-t * 11.0)
    return body * env * 0.95


_SYNTHS = {
    "fire": _synth_fire,
    "explosion": _synth_explosion,
    "hit": _synth_hit,
}


class AudioSystem:
    """Holds procedurally synthesized sounds and a mixer channel pool.

    Synthesis runs once on first successful `_try_init`, using the mixer's
    actual sample rate (not what we requested). Mixer init is deferred until
    first `play()` so the browser AudioContext is unlocked by a user gesture.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.sample_rate: int | None = None
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def _try_init(self) -> bool:
        if self.enabled:
            return True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(C.AUDIO_SAMPLE_RATE, -16, 2, C.AUDIO_BUFFER)
            init_info = pygame.mixer.get_init()
            if init_info is None:
                return False
            actual_rate = init_info[0]
            self.sample_rate = actual_rate
            pygame.mixer.set_num_channels(8)
            for name, synth in _SYNTHS.items():
                samples = _to_stereo_int16(synth(actual_rate))
                self.sounds[name] = pygame.sndarray.make_sound(samples)
            self.enabled = True
            return True
        except (pygame.error, Exception):
            return False

    def play(self, name: str) -> None:
        if not self.enabled and not self._try_init():
            return
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()
