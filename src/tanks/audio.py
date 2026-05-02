"""SFX loaded from disk — single-sound palette.

One sound: `impact`, played when a projectile lands (dirt or tank — same
sound either way; the HP-bar drop is the visual cue for damage). No firing
sound; the visual of the projectile leaving the barrel is the cue. No
round-end fanfare; the on-screen overlay is enough.

pygame's mixer plays OGG natively at the file's own sample rate, so no rate
mismatch and no synthesis to get wrong. Mixer init is deferred to first
`play()` so the browser AudioContext (which only unlocks on user gesture)
doesn't block startup.

Source: "25 CC0 bang/firework SFX" pack on OpenGameArt (CC0); see
src/tanks/sounds/CREDITS.txt.
"""
from pathlib import Path

import pygame

from . import config as C

_SOUND_DIR = Path(__file__).resolve().parent / "sounds"

_SOUND_FILES = {
    "impact": "impact.ogg",
}


class AudioSystem:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def _try_init(self) -> bool:
        if self.enabled:
            return True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(C.AUDIO_SAMPLE_RATE, -16, 2, C.AUDIO_BUFFER)
            pygame.mixer.set_num_channels(8)
            for name, filename in _SOUND_FILES.items():
                self.sounds[name] = pygame.mixer.Sound(str(_SOUND_DIR / filename))
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
