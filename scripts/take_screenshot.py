import os
import pygame
import asyncio

os.environ["SDL_VIDEODRIVER"] = "dummy"

from src.tanks.game import Game
from src.tanks import config as C
from src.tanks.projectile import Projectile

async def main():
    os.makedirs("docs/screenshots", exist_ok=True)
    
    # 1 & 0. Menu / Cover
    game1 = Game(seed=42)
    game1.state = "menu"
    game1._render()
    pygame.image.save(game1.screen, "docs/screenshots/01_menu.png")
    pygame.image.save(game1.screen, "docs/screenshots/00_cover.png")
    
    # 2. Midflight
    game2 = Game(seed=42)
    game2.state = "flight"
    game2.current_tank = game2.player
    game2.player.angle_deg = 45
    game2.player.power = 700
    game2._fire(game2.player)
    for _ in range(40):
        if getattr(game2, "particles", None):
            game2.particles.update(1.0 / 60.0)
        if game2.flying:
            game2.flying.update(1.0 / 60.0, game2.wind)
            if getattr(game2, "particles", None):
                game2.particles.spawn_smoke_trail(game2.flying.x, game2.flying.y)
    game2._render()
    pygame.image.save(game2.screen, "docs/screenshots/02_midflight.png")
    
    # 3. Crater
    game3 = Game(seed=42)
    game3.state = "player_turn"
    game3.terrain.apply_crater(C.SCREEN_W // 2, game3.terrain.height_at(C.SCREEN_W // 2), 60.0)
    for t in game3.tanks:
        t.seat(game3.terrain)
    game3._render()
    pygame.image.save(game3.screen, "docs/screenshots/03_crater.png")
    
    # 4. AI Aiming
    game4 = Game(seed=42)
    game4.state = "ai_turn"
    game4.current_tank = game4.ai
    game4.ai.angle_deg = 135
    game4._render()
    pygame.image.save(game4.screen, "docs/screenshots/04_ai_aiming.png")
    
    # 5. Match End
    game5 = Game(seed=42)
    game5.state = "match_end"
    game5.player_score = 3
    game5.ai_score = 1
    game5.match_over_msg = "YOU WIN THE MATCH"
    game5._render()
    pygame.image.save(game5.screen, "docs/screenshots/05_match_end.png")
    
    print("All screenshots generated in docs/screenshots/")

if __name__ == "__main__":
    asyncio.run(main())
