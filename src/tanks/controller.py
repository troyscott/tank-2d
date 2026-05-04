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
        virtual_keys: dict[str, bool],
    ) -> bool:
        """Per-frame update. Returns True if the tank fires this tick."""
        ...


class PlayerController(Controller):
    def tick(self, tank, world, dt, events, virtual_keys):
        keys = pygame.key.get_pressed()
        
        left = keys[pygame.K_LEFT] or virtual_keys.get("LEFT", False)
        right = keys[pygame.K_RIGHT] or virtual_keys.get("RIGHT", False)
        up = keys[pygame.K_UP] or virtual_keys.get("UP", False)
        down = keys[pygame.K_DOWN] or virtual_keys.get("DOWN", False)
        fire = keys[pygame.K_SPACE] or virtual_keys.get("SPACE", False)
        
        if left:
            tank.angle_deg = _clamp(
                tank.angle_deg + C.ANGLE_RATE_DEG_PER_SEC * dt, C.ANGLE_MIN, C.ANGLE_MAX
            )
        if right:
            tank.angle_deg = _clamp(
                tank.angle_deg - C.ANGLE_RATE_DEG_PER_SEC * dt, C.ANGLE_MIN, C.ANGLE_MAX
            )

        if up:
            tank.power = _clamp(
                tank.power + C.POWER_RATE_PER_SEC * dt, C.POWER_MIN, C.POWER_MAX
            )
        if down:
            tank.power = _clamp(
                tank.power - C.POWER_RATE_PER_SEC * dt, C.POWER_MIN, C.POWER_MAX
            )

        if fire:
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
        self._start_angle: float | None = None
        self._start_power: float | None = None
        self._target_angle: float | None = None
        self._target_power: float | None = None
        self._timer = 0.0
        self._fired = False
        self.turn_state = "THINKING"
        self.turn_delay_timer = 0.0

    def begin_turn(self, tank: "Tank", world: World) -> None:
        self._start_angle = tank.angle_deg
        self._start_power = tank.power
        
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
        
        self.turn_state = "THINKING"
        self.turn_delay_timer = 1.0
        self._fired = False

    def tick(self, tank: "Tank", world: World, dt: float, events: list[pygame.event.Event], virtual_keys: dict[str, bool]) -> bool:
        if self._start_angle is None or self._target_angle is None or self._target_power is None:
            return False

        if self.turn_state == "THINKING":
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self.turn_state = "AIMING"
            return False

        if self.turn_state == "AIMING":
            # Smoothly interpolate angle
            angle_diff = self._target_angle - tank.angle_deg
            if abs(angle_diff) > 0.5:
                # Move barrel at a fixed rate (e.g. 45 degrees per sec)
                move_dir = 1 if angle_diff > 0 else -1
                move_amount = 45.0 * dt
                if abs(angle_diff) < move_amount:
                    tank.angle_deg = self._target_angle
                else:
                    tank.angle_deg += move_dir * move_amount
                return False
                
            # Once angle is reached, snap power instantly and fire
            tank.angle_deg = self._target_angle
            tank.power = self._target_power
            self.turn_state = "FIRING"
            # Return true on the exact frame we snap the power and transition to firing
            return True
            
        return False

    def end_turn(self, tank: "Tank", world: World, landing_x: float | None) -> None:
        if landing_x is None or not self.cfg.memory:
            return
        opponent = next((t for t in world.tanks if t is not tank), None)
        if opponent is None:
            return
        target_x, _ = opponent.body_center()
        self.last_offset_x = landing_x - target_x
