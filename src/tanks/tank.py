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

    def seat(self, terrain: Terrain) -> None:
        self.y = terrain.height_at(self.x)

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
        bx, by = self.x, self.y
        body = pygame.Rect(0, 0, C.TANK_BODY_W, C.TANK_BODY_H)
        body.midbottom = (bx, by)
        pygame.draw.rect(surface, self.color, body)

        turret = pygame.Rect(0, 0, C.TANK_TURRET_W, C.TANK_TURRET_H)
        turret.midbottom = (bx, body.top)
        pygame.draw.rect(surface, self.color, turret)

        pivot = self.barrel_pivot()
        tip = self.barrel_tip()
        pygame.draw.line(surface, self.color, pivot, tip, C.TANK_BARREL_W)
