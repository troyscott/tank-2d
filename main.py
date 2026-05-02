# /// script
# dependencies = ["numpy"]
# ///
"""Tank Game entry point.

Includes browser-friendly defenses:
- "loading..." paint so a visitor sees Python actually started.
- numpy-availability poll: pygbag/pyodide fetches numpy *before* running our
  script, but installation can finish slightly after — block up to ~3 seconds
  before importing anything that touches numpy.
- try/except that paints uncaught exceptions onto the canvas. Browsers hide
  Python stdout, so without this, a crash looks like a silent grey screen.
"""
import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def _wait_for_numpy(max_attempts: int = 30, delay: float = 0.1) -> None:
    for _ in range(max_attempts):
        try:
            import numpy  # noqa: F401, PLC0415
            return
        except ModuleNotFoundError:
            await asyncio.sleep(delay)


async def main() -> None:
    import pygame  # noqa: PLC0415

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((1024, 640))
    font = pygame.font.Font(None, 22)

    # Boot indicator — proves Python is running, and gives the browser a
    # chance to render before heavy init runs.
    screen.fill((20, 24, 40))
    surf = font.render("loading...", True, (220, 220, 220))
    screen.blit(surf, (16, 18))
    pygame.display.flip()
    await asyncio.sleep(0)

    try:
        await _wait_for_numpy()
        from tanks.game import Game  # noqa: PLC0415
        await Game().run()
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc().splitlines()
        screen.fill((60, 10, 10))
        y = 18
        for line in [f"EXCEPTION: {exc}", ""] + tb[-22:]:
            surf = font.render(line[:140], True, (255, 220, 220))
            screen.blit(surf, (16, y))
            y += 24
        pygame.display.flip()
        while True:
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
