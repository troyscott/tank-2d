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
    game.state = "flight"
    game.current_tank = game.player
    game.player.angle_deg = 45
    game.player.power = 700
    game._fire(game.player)
    # simulate some frames so it flies and generates a smoke trail
    for _ in range(40):
        if getattr(game, "particles", None):
            game.particles.update(1.0 / 60.0)
        if game.flying:
            game.flying.update(1.0 / 60.0, game.wind)
            if getattr(game, "particles", None):
                game.particles.spawn_smoke_trail(game.flying.x, game.flying.y)
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/02_midflight.png")
    
    # 3. Crater
    game.flying = None
    game.terrain.apply_crater(C.SCREEN_W // 2, game.terrain.height_at(C.SCREEN_W // 2), 60.0)
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/03_crater.png")
    
    # 4. AI Aiming
    game.state = "ai_turn"
    game.current_tank = game.ai
    game.ai.angle_deg = 135
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/04_ai_aiming.png")
    
    # 5. Match End
    game.state = "match_end"
    game.player_score = 3
    game.ai_score = 1
    game.match_over_msg = "YOU WIN THE MATCH"
    game._render()
    pygame.image.save(game.screen, "docs/screenshots/05_match_end.png")
    
    print("All screenshots generated in docs/screenshots/")

if __name__ == "__main__":
    asyncio.run(main())
