"""Audio isolation test.

Plays each SFX three times in a row with 1-second pauses between, so you can
count events per play call without the game obscuring anything.

Run: .venv/bin/python scripts/audio_test.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame  # noqa: E402

from tanks.audio import AudioSystem  # noqa: E402

pygame.init()
audio = AudioSystem()
# Force mixer init now (since there's no user gesture path here)
audio._try_init()
print(f"audio enabled: {audio.enabled}")
print(f"mixer init: {pygame.mixer.get_init()}  (rate, format, channels)")
print(f"num channels: {pygame.mixer.get_num_channels()}")
print()

for name in ("impact",):
    print(f"\n--- {name} (3 plays, 1s apart) ---")
    for i in range(3):
        print(f"  play {i + 1}")
        audio.play(name)
        time.sleep(1.0)

print("\ndone. count the events you heard per play.")
print("expected: 3 events total (impact ×3).")
pygame.mixer.quit()
pygame.quit()
