import pygame

from . import config as C
from .projectile import Projectile
from .tank import Tank
from .terrain import Terrain


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class Game:
    def __init__(self, seed: int | None = None) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Tank Game")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, C.HUD_FONT_SIZE)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=seed)
        self.player = Tank(x=C.PLAYER_X, color=C.PLAYER_COLOR, facing=+1)
        self.ai = Tank(x=C.AI_X, color=C.AI_COLOR, facing=-1)
        for t in (self.player, self.ai):
            t.seat(self.terrain)
        self.flying: Projectile | None = None
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE and self.flying is None:
                    self._fire(self.player)

    def _update(self, dt: float) -> None:
        if self.flying is None:
            self._read_aim_keys(self.player, dt)
        else:
            self.flying.update(dt)
            if self.flying.hit_terrain(self.terrain):
                print("BOOM")
                self.flying = None
            elif self.flying.off_screen(C.SCREEN_W, C.SCREEN_H):
                self.flying = None

    def _read_aim_keys(self, tank: Tank, dt: float) -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            tank.angle_deg = _clamp(
                tank.angle_deg + C.ANGLE_RATE_DEG_PER_SEC * dt, C.ANGLE_MIN, C.ANGLE_MAX
            )
        if keys[pygame.K_RIGHT]:
            tank.angle_deg = _clamp(
                tank.angle_deg - C.ANGLE_RATE_DEG_PER_SEC * dt, C.ANGLE_MIN, C.ANGLE_MAX
            )
        if keys[pygame.K_UP]:
            tank.power = _clamp(
                tank.power + C.POWER_RATE_PER_SEC * dt, C.POWER_MIN, C.POWER_MAX
            )
        if keys[pygame.K_DOWN]:
            tank.power = _clamp(
                tank.power - C.POWER_RATE_PER_SEC * dt, C.POWER_MIN, C.POWER_MAX
            )

    def _fire(self, tank: Tank) -> None:
        tip_x, tip_y = tank.barrel_tip()
        self.flying = Projectile.fired_from(
            tip_x, tip_y, tank.angle_deg, tank.power, tank.facing
        )

    def _render(self) -> None:
        self.screen.fill(C.SKY_COLOR)
        self.terrain.render(self.screen)
        self.player.render(self.screen)
        self.ai.render(self.screen)
        if self.flying is not None:
            self.flying.render(self.screen)
        self._render_hud()
        pygame.display.flip()

    def _render_hud(self) -> None:
        status = "FIRING" if self.flying is not None else "READY"
        line = (
            f"ANGLE {self.player.angle_deg:5.1f}    "
            f"POWER {self.player.power:5.0f}    "
            f"{status}"
        )
        color = C.HUD_DIM_COLOR if self.flying is not None else C.HUD_COLOR
        surf = self.font.render(line, True, color)
        self.screen.blit(surf, (10, 8))
