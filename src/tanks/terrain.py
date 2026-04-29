import random
from dataclasses import dataclass

import pygame

from . import config as C


def _midpoint_displacement(width: int, roughness: float, rng: random.Random) -> list[int]:
    n = 1
    while n + 1 < width:
        n *= 2
    size = n + 1

    base = float(C.TERRAIN_BASE_Y)
    disp = float(C.TERRAIN_MAX_DISP)
    heights = [0.0] * size
    heights[0] = base + rng.uniform(-disp, disp)
    heights[-1] = base + rng.uniform(-disp, disp)

    step = n
    while step > 1:
        half = step // 2
        for i in range(half, size, step):
            avg = (heights[i - half] + heights[i + half]) * 0.5
            heights[i] = avg + rng.uniform(-disp, disp)
        disp *= roughness
        step = half

    out = []
    for i in range(width):
        y = heights[i]
        if y < C.TERRAIN_MIN_Y:
            y = C.TERRAIN_MIN_Y
        elif y > C.TERRAIN_MAX_Y:
            y = C.TERRAIN_MAX_Y
        out.append(int(y))
    return out


@dataclass
class Terrain:
    heights: list[int]

    @classmethod
    def generate(cls, width: int = C.SCREEN_W, seed: int | None = None) -> "Terrain":
        rng = random.Random(seed)
        return cls(_midpoint_displacement(width, C.TERRAIN_ROUGHNESS, rng))

    def height_at(self, x: int) -> int:
        if x < 0:
            x = 0
        elif x >= len(self.heights):
            x = len(self.heights) - 1
        return self.heights[x]

    def apply_crater(self, cx: int, cy: float, r: float) -> None:
        r2 = r * r
        x_lo = max(0, int(cx - r))
        x_hi = min(len(self.heights), int(cx + r) + 1)
        max_y = C.SCREEN_H - 4
        for x in range(x_lo, x_hi):
            dx = x - cx
            d2 = dx * dx
            if d2 > r2:
                continue
            depth = cy + (r2 - d2) ** 0.5
            new_h = int(depth)
            if new_h > max_y:
                new_h = max_y
            if new_h > self.heights[x]:
                self.heights[x] = new_h

    def render(self, surface: pygame.Surface) -> None:
        w = len(self.heights)
        h = surface.get_height()
        body = [(0, h)]
        body.extend((x, self.heights[x]) for x in range(w))
        body.append((w - 1, h))
        pygame.draw.polygon(surface, C.TERRAIN_COLOR, body)

        top = [(x, self.heights[x]) for x in range(w)]
        pygame.draw.lines(surface, C.TERRAIN_TOP_COLOR, False, top, 2)
