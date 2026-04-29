import math
from dataclasses import dataclass

import pygame

from . import config as C
from .terrain import Terrain


@dataclass
class Tank:
    x: int
    color: tuple[int, int, int]
    angle_deg: float = C.DEFAULT_ANGLE_DEG
    power: float = C.DEFAULT_POWER
    facing: int = 1  # +1 barrel points right, -1 points left
    y: int = 0
    hp: int = C.TANK_HP

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: float) -> None:
        self.hp = max(0, self.hp - int(amount))

    def seat(self, terrain: Terrain) -> None:
        self.y = terrain.height_at(self.x)

    def body_center(self) -> tuple[float, float]:
        return (float(self.x), float(self.y) - C.TANK_BODY_H / 2)

    def barrel_pivot(self) -> tuple[float, float]:
        body_top = self.y - C.TANK_BODY_H
        turret_top = body_top - C.TANK_TURRET_H
        return (float(self.x), turret_top + C.TANK_TURRET_H / 2)

    def barrel_tip(self) -> tuple[float, float]:
        px, py = self.barrel_pivot()
        rad = math.radians(self.angle_deg)
        return (
            px + self.facing * C.TANK_BARREL_LEN * math.cos(rad),
            py - C.TANK_BARREL_LEN * math.sin(rad),
        )

    def render(self, surface: pygame.Surface) -> None:
        color = self.color if self.alive else C.TANK_DEAD_COLOR
        bx, by = self.x, self.y
        body = pygame.Rect(0, 0, C.TANK_BODY_W, C.TANK_BODY_H)
        body.midbottom = (bx, by)
        pygame.draw.rect(surface, color, body)

        turret = pygame.Rect(0, 0, C.TANK_TURRET_W, C.TANK_TURRET_H)
        turret.midbottom = (bx, body.top)
        pygame.draw.rect(surface, color, turret)

        pivot = self.barrel_pivot()
        tip = self.barrel_tip()
        pygame.draw.line(surface, color, pivot, tip, C.TANK_BARREL_W)

        if self.alive:
            self._render_hp_bar(surface)

    def _render_hp_bar(self, surface: pygame.Surface) -> None:
        body_top = self.y - C.TANK_BODY_H
        turret_top = body_top - C.TANK_TURRET_H
        bar_y = turret_top - C.HP_BAR_Y_OFFSET
        bx = self.x - C.HP_BAR_W // 2
        bg = pygame.Rect(bx, bar_y, C.HP_BAR_W, C.HP_BAR_H)
        pygame.draw.rect(surface, C.HP_BAR_BG_COLOR, bg)
        frac = self.hp / C.TANK_HP
        fg_w = max(0, int(C.HP_BAR_W * frac))
        if fg_w > 0:
            r = int(255 * (1.0 - frac))
            g = int(255 * frac)
            fg = pygame.Rect(bx, bar_y, fg_w, C.HP_BAR_H)
            pygame.draw.rect(surface, (r, g, 60), fg)
