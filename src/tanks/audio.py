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

    def play(self, name: str) -> None:
        if not self.enabled:
            return

        if not self.initialized:
            self._init_mixer()

        if name in self.sounds:
            self.sounds[name].play()

    def _init_mixer(self) -> None:
        try:
            pygame.mixer.init()
            self.initialized = True
            
            # Load sounds
            fire_path = os.path.join("assets", "fire.wav")
            exp_path = os.path.join("assets", "explosion.wav")
            
            if os.path.exists(fire_path):
                self.sounds["fire"] = pygame.mixer.Sound(fire_path)
            if os.path.exists(exp_path):
                self.sounds["explosion"] = pygame.mixer.Sound(exp_path)
                
            print("AudioSystem initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
            self.enabled = False # disable if it fails
