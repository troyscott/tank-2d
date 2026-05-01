import numpy as np
import pygame

from . import config as C

SR = C.AUDIO_SAMPLE_RATE


def _to_stereo_int16(mono_float: np.ndarray) -> np.ndarray:
    clipped = np.clip(mono_float, -1.0, 1.0)
    int16 = (clipped * 32767).astype(np.int16)
    stereo = np.column_stack([int16, int16])
    return np.ascontiguousarray(stereo)


def _synth_fire() -> np.ndarray:
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


def _synth_explosion() -> np.ndarray:
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


def _synth_hit() -> np.ndarray:
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


def _synth_tick() -> np.ndarray:
    duration = 0.04
    n = int(SR * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    tone = np.sin(2 * np.pi * 1100.0 * t)
    env = np.exp(-t * 70.0)
    return tone * env * 0.22


def _synth_round_win() -> np.ndarray:
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


_SYNTHS: dict[str, callable] = {
    "fire": _synth_fire,
    "explosion": _synth_explosion,
    "hit": _synth_hit,
    "tick": _synth_tick,
    "round_win": _synth_round_win,
}


class AudioSystem:
    """Holds procedurally synthesized sounds and a mixer channel pool.

    Safe to construct even when no audio device is available — `play` becomes
    a no-op and nothing crashes.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(C.AUDIO_SAMPLE_RATE, -16, 2, C.AUDIO_BUFFER)
            pygame.mixer.set_num_channels(8)
            for name, synth in _SYNTHS.items():
                samples = _to_stereo_int16(synth())
                self.sounds[name] = pygame.sndarray.make_sound(samples)
            self.enabled = True
        except (pygame.error, Exception):
            self.enabled = False

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()
