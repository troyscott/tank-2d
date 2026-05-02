import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from . import ai
from . import config as C

if TYPE_CHECKING:
    from .tank import Tank
    from .terrain import Terrain


@dataclass
class World:
    terrain: "Terrain"
    wind: float
    gravity: float
    tanks: list["Tank"]
    audio: object | None = None  # AudioSystem; left as `object` to avoid a cycle


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class Controller(ABC):
    """Drives a tank during its turn. Mutates `tank.angle_deg` / `tank.power` directly."""

    def begin_turn(self, tank: "Tank", world: World) -> None:  # noqa: B027
        return

    def end_turn(self, tank: "Tank", world: World, landing_x: float | None) -> None:  # noqa: B027
        return

    @abstractmethod
    def tick(
        self,
        tank: "Tank",
        world: World,
        dt: float,
        events: list[pygame.event.Event],
    ) -> bool:
        """Per-frame update. Returns True if the tank fires this tick."""
        ...


class PlayerController(Controller):
    def tick(self, tank, world, dt, events):
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
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                return True
        return False


class AIController(Controller):
    def __init__(
        self,
        difficulty: str = C.AI_DEFAULT_DIFFICULTY,
        rng: random.Random | None = None,
        delay: float = C.AI_TURN_DELAY,
    ) -> None:
        self.cfg = ai.DIFFICULTY[difficulty]
        self.rng = rng or random.Random()
        self.delay = delay
        self.last_offset_x = 0.0
        self._target_angle: float | None = None
        self._target_power: float | None = None
        self._timer = 0.0
        self._armed = False
        self._fired = False

    def begin_turn(self, tank, world):
        opponent = next((t for t in world.tanks if t is not tank and t.alive), None)
        if opponent is None:
            self._target_angle = tank.angle_deg
            self._target_power = tank.power
        else:
            angle_deg, power = ai.plan_shot(
                shooter_xy=(float(tank.x), float(tank.y)),
                target_xy=opponent.body_center(),
                gravity=world.gravity,
                wind=world.wind,
                cfg=self.cfg,
                last_offset_x=self.last_offset_x,
                rng=self.rng,
            )
            self._target_angle = angle_deg
            self._target_power = power
        self._timer = 0.0
        self._armed = False
        self._fired = False

    def tick(self, tank, world, dt, events):
        self._timer += dt
        # Telegraph: snap to target ~halfway through the delay so the player
        # can see what the AI is aiming at before the shot.
        if not self._armed and self._timer >= self.delay * 0.4:
            if self._target_angle is not None:
                tank.angle_deg = self._target_angle
            if self._target_power is not None:
                tank.power = self._target_power
            self._armed = True
        if self._armed and not self._fired and self._timer >= self.delay:
            self._fired = True
            return True
        return False

    def end_turn(self, tank, world, landing_x):
        if landing_x is None or not self.cfg.memory:
            return
        opponent = next((t for t in world.tanks if t is not tank), None)
        if opponent is None:
            return
        target_x, _ = opponent.body_center()
        self.last_offset_x = landing_x - target_x
