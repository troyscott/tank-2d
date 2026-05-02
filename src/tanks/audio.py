"""Procedurally synthesized SFX.

numpy is imported lazily because pygbag/pyodide installs wheels asynchronously
and may not have numpy ready when this module is first imported. Deferring
means the requirement only kicks in when a synth actually runs (i.e. when
AudioSystem is constructed). Browser bring-up with `enable_audio=False`
therefore never touches numpy.
"""
import pygame

from . import config as C

SR = C.AUDIO_SAMPLE_RATE


def _np():
    import numpy as np  # noqa: PLC0415
    return np


def _to_stereo_int16(mono_float):
    np = _np()
    clipped = np.clip(mono_float, -1.0, 1.0)
    int16 = (clipped * 32767).astype(np.int16)
    stereo = np.column_stack([int16, int16])
    return np.ascontiguousarray(stereo)


def _synth_fire():
    np = _np()
    duration = 0.18
    n = int(SR * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    pitch = np.linspace(160.0, 55.0, n)
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    tone = np.sin(phase)
    rng = np.random.default_rng(1)
    noise = rng.uniform(-1.0, 1.0, n) * 0.45
    env = np.exp(-t * 11.0)
    return (tone * 0.55 + noise) * env * 0.75


def _synth_explosion():
    np = _np()
    duration = 0.45
    n = int(SR * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    rng = np.random.default_rng(2)
    noise = rng.uniform(-1.0, 1.0, n)
    # crude low-pass via running mean
    k = 9
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    rumble = np.sin(2 * np.pi * 75.0 * t) * 0.35
    attack = np.minimum(t / 0.015, 1.0)
    decay = np.exp(-t * 4.0)
    env = attack * decay
    return (noise * 0.85 + rumble) * env * 0.95


def _synth_hit():
    np = _np()
    duration = 0.22
    n = int(SR * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    metallic = (
        np.sin(2 * np.pi * 520.0 * t)
        + 0.55 * np.sin(2 * np.pi * 1040.0 * t)
        + 0.30 * np.sin(2 * np.pi * 1560.0 * t)
    )
    env = np.exp(-t * 17.0)
    return metallic * env * 0.45


def _synth_tick():
    np = _np()
    duration = 0.04
    n = int(SR * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    tone = np.sin(2 * np.pi * 1100.0 * t)
    env = np.exp(-t * 70.0)
    return tone * env * 0.22


def _synth_round_win():
    np = _np()
    notes = [523.0, 659.0, 784.0, 1046.0]  # C5, E5, G5, C6
    note_dur = 0.13
    note_n = int(SR * note_dur)
    duration = note_dur * len(notes)
    n = int(SR * duration)
    sig = np.zeros(n)
    for i, freq in enumerate(notes):
        start = i * note_n
        end = min(start + note_n, n)
        seg_n = end - start
        t_seg = np.linspace(0.0, seg_n / SR, seg_n, endpoint=False)
        env = np.exp(-t_seg * 4.0)
        sig[start:end] += np.sin(2 * np.pi * freq * t_seg) * env
    return sig * 0.42


_SYNTHS = {
    "fire": _synth_fire,
    "explosion": _synth_explosion,
    "hit": _synth_hit,
    "tick": _synth_tick,
    "round_win": _synth_round_win,
}


class AudioSystem:
    """Holds procedurally synthesized sounds and a mixer channel pool.

    Numpy synthesis runs eagerly when constructed (no mixer needed). pygame
    `Sound` creation is deferred until the first successful mixer init —
    important in the browser, where the audio context only comes alive after
    a user gesture. Once mixer init succeeds, all sounds are built and `play`
    works for the rest of the session.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._raw = {
            name: _to_stereo_int16(synth()) for name, synth in _SYNTHS.items()
        }
        self.sounds = {}
        # NOTE: don't call _try_init() here. In the browser pygame.mixer.init()
        # can block on the AudioContext indefinitely; we wait until play() is
        # called, which can only happen after a user gesture has unlocked it.

    def _try_init(self) -> bool:
        if self.enabled:
            return True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(C.AUDIO_SAMPLE_RATE, -16, 2, C.AUDIO_BUFFER)
            pygame.mixer.set_num_channels(8)
            for name, samples in self._raw.items():
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
