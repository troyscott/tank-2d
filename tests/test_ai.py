import math
import random

import pytest

from tanks import config as C
from tanks.ai import DIFFICULTY, DifficultyCfg, plan_shot, solve_angle
from tanks.projectile import Projectile


def _simulate(angle_rad: float, v: float, g: float, max_x: float, dt: float = 1 / 240) -> Projectile:
    p = Projectile(0.0, 0.0, v * math.cos(angle_rad), -v * math.sin(angle_rad))
    while p.x < max_x and p.y < 5000:
        p.update(dt=dt, gravity=g, wind=0.0)
        if p.y > 5000:
            break
    return p


def test_solve_angle_unreachable_returns_none():
    # A very far target with a weak velocity: out of range
    assert solve_angle(horiz_dist=10_000, dy=0.0, v=100.0, g=400.0) is None


def test_solve_angle_low_arc_lands_near_target():
    H, dy, v, g = 500.0, 0.0, 500.0, 400.0
    ang = solve_angle(H, dy, v, g, prefer_high=False)
    assert ang is not None
    assert 0 < ang < math.radians(45.0) + 0.1  # low arc is shallow

    p = _simulate(ang, v, g, max_x=H)
    assert abs(p.x - H) < 5
    assert abs(p.y - dy) < 5


def test_solve_angle_high_arc_lobs_higher_than_low():
    H, dy, v, g = 500.0, 0.0, 500.0, 400.0
    ang_low = solve_angle(H, dy, v, g, prefer_high=False)
    ang_high = solve_angle(H, dy, v, g, prefer_high=True)
    assert ang_low is not None and ang_high is not None
    assert ang_high > ang_low

    p = _simulate(ang_high, v, g, max_x=H)
    assert abs(p.x - H) < 5
    assert abs(p.y - dy) < 5


def test_solve_angle_target_below_extends_reachable_range():
    # Speed just shy of flat-ground max range (v_min_flat = sqrt(g·H) = 400):
    H, v, g = 400.0, 350.0, 400.0
    assert solve_angle(H, dy=0.0, v=v, g=g) is None
    # ...but the same speed *can* reach a target below the shooter at the same H.
    assert solve_angle(H, dy=300.0, v=v, g=g) is not None


def test_difficulty_table_matches_spec():
    assert DIFFICULTY["easy"].angle_sigma_deg == 15.0
    assert DIFFICULTY["medium"].angle_sigma_deg == 5.0
    assert DIFFICULTY["hard"].angle_sigma_deg == 1.0
    assert DIFFICULTY["easy"].memory is False
    assert DIFFICULTY["medium"].memory is True
    assert DIFFICULTY["hard"].memory is True
    assert DIFFICULTY["hard"].wind_aware is True


def test_plan_shot_zero_noise_is_deterministic():
    cfg = DifficultyCfg(angle_sigma_deg=0, power_sigma_frac=0, wind_aware=False, memory=False)
    a1, p1 = plan_shot(
        shooter_xy=(100, 300), target_xy=(700, 300),
        gravity=400.0, wind=0.0, cfg=cfg, last_offset_x=0.0,
        rng=random.Random(1),
    )
    a2, p2 = plan_shot(
        shooter_xy=(100, 300), target_xy=(700, 300),
        gravity=400.0, wind=0.0, cfg=cfg, last_offset_x=0.0,
        rng=random.Random(99),
    )
    assert a1 == pytest.approx(a2)
    assert p1 == pytest.approx(p2)


def test_plan_shot_memory_changes_aim_when_offset_nonzero():
    cfg_mem = DifficultyCfg(angle_sigma_deg=0, power_sigma_frac=0, wind_aware=False, memory=True)
    cfg_nomem = DifficultyCfg(angle_sigma_deg=0, power_sigma_frac=0, wind_aware=False, memory=False)
    args = dict(
        shooter_xy=(100, 300), target_xy=(700, 300),
        gravity=400.0, wind=0.0, last_offset_x=80.0,
    )
    a_mem, _ = plan_shot(cfg=cfg_mem, rng=random.Random(1), **args)
    a_nomem, _ = plan_shot(cfg=cfg_nomem, rng=random.Random(1), **args)
    assert a_mem != a_nomem


def test_plan_shot_easy_noise_envelope_wider_than_hard():
    args = dict(
        shooter_xy=(100, 300), target_xy=(700, 300),
        gravity=400.0, wind=0.0, last_offset_x=0.0,
    )
    rng = random.Random(0)
    easy_angles = [
        plan_shot(cfg=DIFFICULTY["easy"], rng=rng, **args)[0] for _ in range(200)
    ]
    rng = random.Random(0)
    hard_angles = [
        plan_shot(cfg=DIFFICULTY["hard"], rng=rng, **args)[0] for _ in range(200)
    ]

    def stddev(xs):
        m = sum(xs) / len(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    assert stddev(easy_angles) > stddev(hard_angles) * 3


def test_plan_shot_clamps_to_legal_ranges():
    cfg = DifficultyCfg(angle_sigma_deg=200, power_sigma_frac=5.0, wind_aware=False, memory=False)
    rng = random.Random(0)
    for _ in range(50):
        ang, pw = plan_shot(
            shooter_xy=(100, 300), target_xy=(700, 300),
            gravity=400.0, wind=0.0, cfg=cfg, last_offset_x=0.0, rng=rng,
        )
        assert C.ANGLE_MIN <= ang <= C.ANGLE_MAX
        assert C.POWER_MIN <= pw <= C.POWER_MAX
