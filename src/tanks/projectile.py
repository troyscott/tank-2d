import math
from dataclasses import dataclass

import pygame

from . import config as C
from .terrain import Terrain


def damage_at(
    impact: tuple[float, float],
    target: tuple[float, float],
    radius: float = C.EXPLOSION_RADIUS,
    max_damage: float = C.EXPLOSION_DAMAGE,
) -> float:
    dist = math.hypot(target[0] - impact[0], target[1] - impact[1])
    if dist >= radius:
        return 0.0
    return max_damage * (1.0 - dist / radius)


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float

    @classmethod
    def fired_from(
        cls, tip_x: float, tip_y: float, angle_deg: float, power: float, facing: int
    ) -> "Projectile":
        rad = math.radians(angle_deg)
        vx = facing * power * math.cos(rad)
        vy = -power * math.sin(rad)
        return cls(tip_x, tip_y, vx, vy)

    def update(self, dt: float, gravity: float = C.GRAVITY, wind: float = 0.0) -> None:
        self.vx += wind * dt
        self.vy += gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def hit_terrain(self, terrain: Terrain) -> bool:
        ix = int(self.x)
        if ix < 0 or ix >= len(terrain.heights):
            return False
        return self.y >= terrain.heights[ix]

    def off_screen(self, width: int, height: int, margin: int = 50) -> bool:
        return (
            self.x < -margin
            or self.x > width + margin
            or self.y > height + margin
        )

import functools

@functools.lru_cache(maxsize=1)
def _get_projectile_glow(radius: int, r: int, g: int, b: int) -> pygame.Surface:
    glow_size = radius * 4
    glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (r, g, b, 100), (glow_size, glow_size), glow_size)
    return glow

    def render(self, surface: pygame.Surface) -> None:
        # Additive glow
        radius = C.PROJECTILE_RADIUS
        glow = _get_projectile_glow(radius, C.PROJECTILE_COLOR[0], C.PROJECTILE_COLOR[1], C.PROJECTILE_COLOR[2])
        glow_size = radius * 4
        surface.blit(glow, (int(self.x - glow_size), int(self.y - glow_size)), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Core
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (int(self.x), int(self.y)),
            radius,
        )
