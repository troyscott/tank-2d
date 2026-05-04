import math
import random
from dataclasses import dataclass

from . import config as C


@dataclass(frozen=True)
class DifficultyCfg:
    angle_sigma_deg: float
    power_sigma_frac: float
    wind_aware: bool
    memory: bool


DIFFICULTY: dict[str, DifficultyCfg] = {
    "easy": DifficultyCfg(
        angle_sigma_deg=15.0, power_sigma_frac=0.20, wind_aware=False, memory=False
    ),
    "medium": DifficultyCfg(
        angle_sigma_deg=5.0, power_sigma_frac=0.08, wind_aware=False, memory=True
    ),
    "hard": DifficultyCfg(
        angle_sigma_deg=1.0, power_sigma_frac=0.02, wind_aware=True, memory=True
    ),
}


def solve_angle(
    horiz_dist: float,
    dy: float,
    v: float,
    g: float = C.GRAVITY,
    prefer_high: bool = False,
) -> float | None:
    """Solve launch angle (radians, above horizontal in shooter's facing direction).

    horiz_dist: positive horizontal distance to target.
    dy: vertical offset, pygame coords (positive = target is below shooter).
    v: launch speed.
    g: gravity (positive, pulls down).
    Returns angle in radians, or None if target is unreachable at this speed.
    """
    if horiz_dist <= 0 or v <= 0 or g <= 0:
        return None
    H = horiz_dist
    discriminant = v**4 - (g * H) ** 2 + 2 * g * v**2 * dy
    if discriminant < 0:
        return None
    s = math.sqrt(discriminant)
    u = (v * v + (s if prefer_high else -s)) / (g * H)
    return math.atan(u)


def pick_power(horiz_dist: float, dy: float, g: float = C.GRAVITY) -> float:
    """Choose a launch power that comfortably reaches a target at this distance."""
    H = max(horiz_dist, 1.0)
    v_min_flat = math.sqrt(g * H)  # minimum v to reach H on flat ground at 45°
    return max(C.POWER_MIN, min(C.POWER_MAX, v_min_flat * 1.2))


def plan_shot(
    shooter_xy: tuple[float, float],
    target_xy: tuple[float, float],
    gravity: float,
    wind: float,
    cfg: DifficultyCfg,
    last_offset_x: float,
    rng: random.Random,
    facing: int,
) -> tuple[float, float]:
    """Pick the (angle_deg, power) the AI will fire with.

    Returns angle in degrees in the game's [0, 180] convention (0 = horizontal in
    shooter's facing direction; 90 = straight up; 180 = horizontal opposite).
    """
    sx, _sy = shooter_xy
    tx, ty = target_xy
    if cfg.memory:
        tx -= 0.6 * last_offset_x

    horiz = abs(tx - sx)
    dy = ty - shooter_xy[1]

    v = pick_power(horiz, dy, gravity)
    angle_rad = solve_angle(horiz, dy, v, gravity, prefer_high=False)
    if angle_rad is None:
        angle_rad = math.radians(45.0)  # max-range fallback for flat ground

    if cfg.wind_aware:
        angle_rad -= facing * wind * 0.0015

    angle_rad += math.radians(rng.gauss(0.0, cfg.angle_sigma_deg))
    v *= 1.0 + rng.gauss(0.0, cfg.power_sigma_frac)

    angle_deg = math.degrees(angle_rad)
    angle_deg = max(C.ANGLE_MIN, min(C.ANGLE_MAX, angle_deg))
    v = max(C.POWER_MIN, min(C.POWER_MAX, v))
    return (angle_deg, v)
