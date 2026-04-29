import math

import pytest

from tanks import config as C
from tanks.projectile import Projectile, damage_at
from tanks.terrain import Terrain


def test_no_force_is_linear():
    p = Projectile(x=0.0, y=0.0, vx=120.0, vy=0.0)
    for _ in range(60):
        p.update(dt=1 / 60, gravity=0.0, wind=0.0)
    assert p.x == pytest.approx(120.0)
    assert p.y == pytest.approx(0.0)


def test_gravity_pulls_down():
    p = Projectile(x=0.0, y=0.0, vx=0.0, vy=-200.0)
    # Apex at t = vy0 / g = 200 / 400 = 0.5s
    for _ in range(30):
        p.update(dt=1 / 60, gravity=400.0, wind=0.0)
    # vy ≈ 0 at apex; allow one Euler step of slack
    assert abs(p.vy) < 7
    # y should be roughly negative (above start) at apex
    assert p.y < 0


def test_wind_alters_horizontal():
    a = Projectile(x=0.0, y=0.0, vx=100.0, vy=0.0)
    b = Projectile(x=0.0, y=0.0, vx=100.0, vy=0.0)
    for _ in range(60):
        a.update(dt=1 / 60, gravity=0.0, wind=0.0)
        b.update(dt=1 / 60, gravity=0.0, wind=50.0)
    assert b.x > a.x


def test_fired_from_straight_up():
    p = Projectile.fired_from(100, 200, angle_deg=90.0, power=400.0, facing=+1)
    assert p.vx == pytest.approx(0.0, abs=1e-9)
    assert p.vy == pytest.approx(-400.0)


def test_fired_from_45_facing_right():
    p = Projectile.fired_from(0, 0, angle_deg=45.0, power=400.0, facing=+1)
    expected = 400.0 * math.cos(math.radians(45.0))
    assert p.vx == pytest.approx(expected)
    assert p.vy == pytest.approx(-expected)


def test_fired_from_facing_left_is_mirrored():
    right = Projectile.fired_from(0, 0, angle_deg=45.0, power=400.0, facing=+1)
    left = Projectile.fired_from(0, 0, angle_deg=45.0, power=400.0, facing=-1)
    assert left.vx == pytest.approx(-right.vx)
    assert left.vy == pytest.approx(right.vy)


def test_deterministic():
    a = Projectile(x=10.0, y=20.0, vx=100.0, vy=-200.0)
    b = Projectile(x=10.0, y=20.0, vx=100.0, vy=-200.0)
    for _ in range(100):
        a.update(dt=1 / 60, gravity=400.0, wind=20.0)
        b.update(dt=1 / 60, gravity=400.0, wind=20.0)
    assert (a.x, a.y, a.vx, a.vy) == (b.x, b.y, b.vx, b.vy)


def test_hit_terrain_when_y_below_height():
    terrain = Terrain(heights=[300] * C.SCREEN_W)
    above = Projectile(x=100.0, y=200.0, vx=0.0, vy=0.0)
    on = Projectile(x=100.0, y=300.0, vx=0.0, vy=0.0)
    below = Projectile(x=100.0, y=400.0, vx=0.0, vy=0.0)
    assert not above.hit_terrain(terrain)
    assert on.hit_terrain(terrain)
    assert below.hit_terrain(terrain)


def test_hit_terrain_off_side_is_false():
    terrain = Terrain(heights=[100] * C.SCREEN_W)
    p = Projectile(x=-5.0, y=999.0, vx=0.0, vy=0.0)
    assert not p.hit_terrain(terrain)


def test_off_screen_detects_bottom_and_sides():
    p_left = Projectile(x=-200.0, y=100.0, vx=0.0, vy=0.0)
    p_right = Projectile(x=C.SCREEN_W + 200.0, y=100.0, vx=0.0, vy=0.0)
    p_bottom = Projectile(x=500.0, y=C.SCREEN_H + 200.0, vx=0.0, vy=0.0)
    p_in = Projectile(x=500.0, y=100.0, vx=0.0, vy=0.0)
    assert p_left.off_screen(C.SCREEN_W, C.SCREEN_H)
    assert p_right.off_screen(C.SCREEN_W, C.SCREEN_H)
    assert p_bottom.off_screen(C.SCREEN_W, C.SCREEN_H)
    assert not p_in.off_screen(C.SCREEN_W, C.SCREEN_H)


def test_damage_at_max_at_center():
    d = damage_at((100, 100), (100, 100), radius=35.0, max_damage=60.0)
    assert d == pytest.approx(60.0)


def test_damage_at_zero_at_or_beyond_radius():
    assert damage_at((0, 0), (35, 0), radius=35.0, max_damage=60.0) == 0.0
    assert damage_at((0, 0), (50, 0), radius=35.0, max_damage=60.0) == 0.0


def test_damage_at_linear_falloff():
    # halfway out → half damage
    d = damage_at((0, 0), (17.5, 0), radius=35.0, max_damage=60.0)
    assert d == pytest.approx(30.0)


def test_damage_at_uses_2d_distance():
    # 3-4-5 triangle: dist=5, radius=10, frac=0.5, max=60 → 30
    d = damage_at((0, 0), (3, 4), radius=10.0, max_damage=60.0)
    assert d == pytest.approx(30.0)
