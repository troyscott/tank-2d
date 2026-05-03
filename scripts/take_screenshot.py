import os
import pygame
import asyncio

os.environ["SDL_VIDEODRIVER"] = "dummy"

from src.tanks.game import Game
from src.tanks import config as C

async def main():
    game = Game(seed=42)
    game.state = "player_turn"
    
    # We need to call render once
    game._render()
    
    # Save the surface
    pygame.image.save(game.screen, "docs/screenshot.png")
    print("Screenshot saved to docs/screenshot.png")

if __name__ == "__main__":
    asyncio.run(main())
