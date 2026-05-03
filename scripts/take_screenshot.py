import os
import pygame
import asyncio

os.environ["SDL_VIDEODRIVER"] = "dummy"

from src.tanks.game import Game
from src.tanks import config as C
from src.tanks.projectile import Projectile

async def main():
    os.makedirs("docs/screenshots", exist_ok=True)
    
    game = Game(seed=42)
    
    # 1. Menu
    game.state = "menu"
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/01_menu.png")
    
    # 0. Cover (just the menu again for now, maybe hide text?)
    pygame.image.save(game.screen, "docs/screenshots/00_cover.png")
    
    # 2. Midflight
    game.state = "player_turn"
    game.player.angle_deg = 45
    game.flying = Projectile(x=game.player.x + 20, y=game.player.y - 40, vx=100, vy=-100)
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/02_midflight.png")
    
    # 3. Crater
    game.flying = None
    game.terrain.apply_crater(C.SCREEN_W // 2, game.terrain.height_at(C.SCREEN_W // 2), 60.0)
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/03_crater.png")
    
    # 4. AI Aiming
    game.state = "ai_turn"
    game.ai.angle_deg = 135
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/04_ai_aiming.png")
    
    # 5. Match End
    game.state = "match_over"
    game.p1_wins = 3
    game.p2_wins = 1
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/05_match_end.png")
    
    print("All screenshots generated in docs/screenshots/")

if __name__ == "__main__":
    asyncio.run(main())
