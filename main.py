"""Tank Game entry point.

Browser-friendly defenses (matter for pygbag, harmless on native):
- "loading..." paint so a visitor sees Python actually started.
- try/except that paints uncaught exceptions onto the canvas. Browsers hide
  Python stdout, so without this, a crash looks like a silent grey screen.
"""
import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main() -> None:
    import pygame  # noqa: PLC0415

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((1024, 640))
    font = pygame.font.Font(None, 22)

    screen.fill((20, 24, 40))
    surf = font.render("loading...", True, (220, 220, 220))
    screen.blit(surf, (16, 18))
    pygame.display.flip()
    await asyncio.sleep(0)

    try:
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
