import pygame
import os
import sys
from typing import Protocol

class AudioBackend(Protocol):
    def init(self) -> bool:
        ...
    def play(self, name: str) -> None:
        ...

class PygameAudioBackend:
    def __init__(self):
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def init(self) -> bool:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            # Load distinct sounds (prefer .ogg for Pygame/Pygbag)
            for name in ["fire_blue", "fire_red", "impact_blue", "impact_red"]:
                path = os.path.join("assets", f"{name}.ogg")
                if os.path.exists(path):
                    self.sounds[name] = pygame.mixer.Sound(path)
            print("PygameAudioBackend initialized successfully.")
            return True
        except Exception as e:
            print(f"Pygame audio init failed: {e}")
            return False

    def play(self, name: str) -> None:
        if name in self.sounds:
            self.sounds[name].play()

class MacAudioBackend:
    def __init__(self):
        self.paths: dict[str, str] = {}

    def init(self) -> bool:
        import shutil
        if not shutil.which("afplay"):
            return False
            
        for name in ["fire_blue", "fire_red", "impact_blue", "impact_red"]:
            path = os.path.join("assets", f"{name}.wav")
            if os.path.exists(path):
                self.paths[name] = path
        print("MacAudioBackend initialized successfully.")
        return True

    def play(self, name: str) -> None:
        if name in self.paths:
            import subprocess
            subprocess.Popen(
                ["afplay", self.paths[name]], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )

class WindowsAudioBackend:
    def __init__(self):
        self.paths: dict[str, str] = {}
        self.winsound = None
        
    def init(self) -> bool:
        try:
            import winsound
            self.winsound = winsound
        except ImportError:
            return False
            
        for name in ["fire_blue", "fire_red", "impact_blue", "impact_red"]:
            path = os.path.join("assets", f"{name}.wav")
            if os.path.exists(path):
                self.paths[name] = path
        print("WindowsAudioBackend initialized successfully.")
        return True

    def play(self, name: str) -> None:
        if name in self.paths and self.winsound:
            self.winsound.PlaySound(
                self.paths[name], 
                self.winsound.SND_FILENAME | self.winsound.SND_ASYNC
            )

class AudioSystem:
    """
    Deferred audio system designed to bypass the browser AudioContext lock,
    while dynamically selecting the most optimal, lowest-latency backend available
    for the current operating system.
    """
    def __init__(self):
        self.enabled = False
        self.initialized = False
        self.backend: AudioBackend | None = None

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

        if self.backend:
            self.backend.play(name)

    def _init_mixer(self) -> None:
        if sys.platform == 'emscripten':
            backend = PygameAudioBackend()
        elif sys.platform == 'darwin':
            backend = MacAudioBackend()
        elif sys.platform == 'win32':
            backend = WindowsAudioBackend()
        else:
            backend = PygameAudioBackend()
            
        if backend.init():
            self.backend = backend
            self.initialized = True
        else:
            # Fallback to Pygame if native backend failed (e.g. afplay not found)
            if not isinstance(backend, PygameAudioBackend):
                print(f"Native backend {backend.__class__.__name__} failed, falling back to PygameAudioBackend")
                fallback = PygameAudioBackend()
                if fallback.init():
                    self.backend = fallback
                    self.initialized = True
                else:
                    self.enabled = False
            else:
                self.enabled = False
