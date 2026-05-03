import pygame
import os

class AudioSystem:
    """
    Deferred audio system designed to bypass the browser AudioContext lock.
    Initialization and sound loading only occur upon the first play() call,
    which is guaranteed to happen after a user gesture.
    """
    def __init__(self):
        self.enabled = False
        self.initialized = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def toggle(self) -> None:
        self.enabled = not self.enabled
        # Eagerly initialize the mixer right when toggled so the 
        # initialization latency happens on the menu, not during a shot!
        if self.enabled and not self.initialized:
            self._init_mixer()

    def play(self, name: str) -> None:
        if not self.enabled:
            return

        if not self.initialized:
            self._init_mixer()

        if name in self.sounds:
            self.sounds[name].play()

    def _init_mixer(self) -> None:
        import sys
        if sys.platform == 'emscripten':
            try:
                pygame.mixer.SoundPatch()
            except Exception:
                pass

        try:
            # Setting a low buffer (512 instead of the default which can be 4096+)
            # is critical for preventing audio latency / out-of-sync sound effects.
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.initialized = True
            
            # Load sounds (using .ogg which is heavily preferred by pygame and pygbag)
            fire_path = os.path.join("assets", "fire.ogg")
            exp_path = os.path.join("assets", "explosion.ogg")
            
            if os.path.exists(fire_path):
                self.sounds["fire"] = pygame.mixer.Sound(fire_path)
            if os.path.exists(exp_path):
                self.sounds["explosion"] = pygame.mixer.Sound(exp_path)
                
            print("AudioSystem initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
            self.enabled = False # disable if it fails
