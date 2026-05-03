import random
import math
import pygame
from dataclasses import dataclass

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    radius: float
    shrink: bool = True
    gravity: float = 0.0

class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def spawn(self, x: float, y: float, vx: float, vy: float, life: float, color: tuple[int, int, int], radius: float, shrink: bool = True, gravity: float = 0.0):
        self.particles.append(Particle(x, y, vx, vy, life, life, color, radius, shrink, gravity))

    def update(self, dt: float):
        alive = []
        for p in self.particles:
            p.x += p.vx * dt
            p.vy += p.gravity * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def render(self, surface: pygame.Surface, additive: bool = False):
        if additive:
            # For additive blending, we create a temporary surface
            # but drawing lots of circles on it might be slow if we do it per particle.
            # Pygame can do additive blending if we blit a surface with BLEND_RGBA_ADD.
            for p in self.particles:
                alpha = max(0, int(255 * (p.life / p.max_life)))
                r = p.radius * (p.life / p.max_life if p.shrink else 1.0)
                if r <= 0.5:
                    continue
                
                # To do glowing particles properly in Pygame without killing framerate:
                # We draw a circle on a small temp surface and blit it.
                size = int(r * 2) + 2
                temp = pygame.Surface((size, size), pygame.SRCALPHA)
                color_with_alpha = (p.color[0], p.color[1], p.color[2], alpha)
                pygame.draw.circle(temp, color_with_alpha, (size//2, size//2), r)
                surface.blit(temp, (int(p.x - size//2), int(p.y - size//2)), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            for p in self.particles:
                r = p.radius * (p.life / p.max_life if p.shrink else 1.0)
                if r <= 0.5:
                    continue
                pygame.draw.circle(surface, p.color, (int(p.x), int(p.y)), int(r))

    def spawn_explosion(self, x: float, y: float, count: int = 40):
        # Fire / Glow
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(50, 200)
            life = random.uniform(0.2, 0.6)
            color = random.choice([(255, 200, 50), (255, 100, 20), (255, 50, 10)])
            radius = random.uniform(4, 12)
            self.spawn(x, y, math.cos(angle)*speed, math.sin(angle)*speed, life, color, radius, shrink=True)
            
        # Debris/Dirt
        for _ in range(count):
            angle = random.uniform(0, math.pi) # upper half
            speed = random.uniform(100, 300)
            life = random.uniform(0.5, 1.5)
            color = random.choice([(96, 72, 48), (64, 48, 32), (132, 168, 84)])
            radius = random.uniform(2, 5)
            self.spawn(x, y, math.cos(angle)*speed, -math.sin(angle)*speed, life, color, radius, shrink=False, gravity=400.0)

    def spawn_smoke_trail(self, x: float, y: float):
        # Smoke
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(5, 20)
        life = random.uniform(0.5, 1.0)
        color = (150, 150, 150)
        radius = random.uniform(3, 6)
        self.spawn(x, y, math.cos(angle)*speed, math.sin(angle)*speed, life, color, radius, shrink=True, gravity=-20.0)

    def spawn_tank_smoke(self, x: float, y: float):
        # Dark smoke rising
        speed = random.uniform(10, 40)
        life = random.uniform(1.0, 2.0)
        color = (50, 50, 50)
        radius = random.uniform(4, 8)
        self.spawn(x, y + random.uniform(-5, 5), random.uniform(-10, 10), -speed, life, color, radius, shrink=True)
