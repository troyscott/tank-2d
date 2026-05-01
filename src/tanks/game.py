import random

import pygame

from . import config as C
from .projectile import Projectile, damage_at
from .tank import Tank
from .terrain import Terrain

STATE_PLAYING = "playing"
STATE_ROUND_OVER = "round_over"


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
        self.big_font = pygame.font.SysFont(None, C.ROUND_OVER_FONT_SIZE)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=seed)
        self.player = Tank(x=C.PLAYER_X, color=C.PLAYER_COLOR, facing=+1)
        self.ai = Tank(x=C.AI_X, color=C.AI_COLOR, facing=-1)
        for t in (self.player, self.ai):
            t.seat(self.terrain)
        self.flying: Projectile | None = None
        self.state = STATE_PLAYING
        self.round_over_msg = ""
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
                elif self.state == STATE_PLAYING:
                    if event.key == pygame.K_SPACE and self.flying is None:
                        self._fire(self.player)
                elif self.state == STATE_ROUND_OVER:
                    if event.key == pygame.K_r:
                        self._reset_round()

    def _update(self, dt: float) -> None:
        if self.state == STATE_ROUND_OVER:
            return
        if self.flying is None:
            self._read_aim_keys(self.player, dt)
        else:
            self.flying.update(dt)
            if self.flying.hit_terrain(self.terrain):
                self._on_impact(self.flying.x, self.flying.y)
                self.flying = None
            elif self.flying.off_screen(C.SCREEN_W, C.SCREEN_H):
                self.flying = None

    def _on_impact(self, x: float, y: float) -> None:
        self.terrain.apply_crater(int(x), y, C.EXPLOSION_RADIUS)
        impact = (x, y)
        for t in (self.player, self.ai):
            if not t.alive:
                continue
            dmg = damage_at(impact, t.body_center())
            if dmg > 0:
                t.take_damage(dmg)
        for t in (self.player, self.ai):
            t.seat(self.terrain)
        print(
            f"BOOM at ({int(x)},{int(y)})  "
            f"player_hp={self.player.hp} ai_hp={self.ai.hp}"
        )
        if not self.player.alive or not self.ai.alive:
            self._enter_round_over()

    def _enter_round_over(self) -> None:
        if not self.player.alive and not self.ai.alive:
            self.round_over_msg = "DRAW"
        elif not self.player.alive:
            self.round_over_msg = "AI WINS"
        else:
            self.round_over_msg = "PLAYER WINS"
        self.state = STATE_ROUND_OVER

    def _reset_round(self) -> None:
        self.terrain = Terrain.generate(
            C.SCREEN_W, seed=random.randint(0, 1_000_000)
        )
        for t in (self.player, self.ai):
            t.hp = C.TANK_HP
            t.seat(self.terrain)
        self.flying = None
        self.state = STATE_PLAYING
        self.round_over_msg = ""

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
        if self.state == STATE_ROUND_OVER:
            self._render_round_over()
        pygame.display.flip()

    def _render_hud(self) -> None:
        if self.state == STATE_ROUND_OVER:
            return
        status = "FIRING" if self.flying is not None else "READY"
        line = (
            f"ANGLE {self.player.angle_deg:5.1f}    "
            f"POWER {self.player.power:5.0f}    "
            f"{status}"
        )
        color = C.HUD_DIM_COLOR if self.flying is not None else C.HUD_COLOR
        surf = self.font.render(line, True, color)
        self.screen.blit(surf, (10, 8))

    def _render_round_over(self) -> None:
        msg = f"ROUND OVER — {self.round_over_msg}"
        sub = "press R to play again, ESC to quit"
        surf = self.big_font.render(msg, True, C.ROUND_OVER_COLOR)
        rect = surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 18))
        self.screen.blit(surf, rect)
        sub_surf = self.font.render(sub, True, C.HUD_DIM_COLOR)
        sub_rect = sub_surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 18))
        self.screen.blit(sub_surf, sub_rect)
