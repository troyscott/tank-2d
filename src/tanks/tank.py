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
        bw, bh = C.TANK_BODY_W, C.TANK_BODY_H
        tw, th = C.TANK_TURRET_W, C.TANK_TURRET_H
        
        # 1. Treads (Dark gray pill shape at the bottom)
        tread_h = int(bh * 0.5)
        tread_y = by - tread_h
        tread_rect = pygame.Rect(bx - bw//2, tread_y, bw, tread_h)
        pygame.draw.rect(surface, (30, 30, 30), tread_rect, border_radius=tread_h//2)
        
        # Wheels inside treads
        wheel_r = tread_h // 2 - 2
        if wheel_r > 0:
            num_wheels = bw // (wheel_r * 2 + 2)
            start_x = bx - bw//2 + wheel_r + 4
            for i in range(num_wheels):
                wx = start_x + i * (wheel_r * 2 + 2)
                pygame.draw.circle(surface, (70, 70, 70), (int(wx), tread_y + tread_h//2), wheel_r)
                pygame.draw.circle(surface, (20, 20, 20), (int(wx), tread_y + tread_h//2), wheel_r//2)

        # 2. Hull (Sloped armor)
        hull_h = bh - tread_h
        hull_y = tread_y - hull_h
        slope = 6
        hull_pts = [
            (bx - bw//2 + slope, hull_y),            # top left
            (bx + bw//2 - slope, hull_y),            # top right
            (bx + bw//2, tread_y),                   # bottom right
            (bx - bw//2, tread_y)                    # bottom left
        ]
        pygame.draw.polygon(surface, color, hull_pts)
        # Highlight and shadow
        pygame.draw.line(surface, (255, 255, 255), hull_pts[0], hull_pts[1], 2)
        pygame.draw.line(surface, (0, 0, 0), hull_pts[2], hull_pts[3], 2)
        
        # 3. Turret (Angled dome)
        turret_y = hull_y - th
        turret_pts = [
            (bx - tw//2 + 4, turret_y),              # top left
            (bx + tw//2 - 4, turret_y),              # top right
            (bx + tw//2 + 2, hull_y),                # bottom right
            (bx - tw//2 - 2, hull_y)                 # bottom left
        ]
        pygame.draw.polygon(surface, color, turret_pts)
        pygame.draw.line(surface, (255, 255, 255), turret_pts[0], turret_pts[1], 2)

        # 4. Barrel
        pivot = self.barrel_pivot()
        tip = self.barrel_tip()
        pygame.draw.line(surface, (80, 80, 80), pivot, tip, C.TANK_BARREL_W)
        pygame.draw.line(surface, (150, 150, 150), pivot, tip, max(1, C.TANK_BARREL_W - 2))
        
        # Muzzle brake
        rad = math.radians(self.angle_deg)
        mb_dx = self.facing * 4 * math.cos(rad)
        mb_dy = -4 * math.sin(rad)
        pygame.draw.line(surface, (40, 40, 40), 
                         (tip[0] - mb_dx, tip[1] - mb_dy), 
                         (tip[0] + mb_dx, tip[1] + mb_dy), C.TANK_BARREL_W + 4)

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
