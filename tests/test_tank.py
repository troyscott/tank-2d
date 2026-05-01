from tanks import config as C
from tanks.tank import Tank


def test_starts_alive_with_full_hp():
    t = Tank(x=0, color=(0, 0, 0))
    assert t.hp == C.TANK_HP
    assert t.alive


def test_take_damage_reduces_hp():
    t = Tank(x=0, color=(0, 0, 0))
    t.take_damage(30)
    assert t.hp == C.TANK_HP - 30
    assert t.alive


def test_take_damage_clamps_at_zero():
    t = Tank(x=0, color=(0, 0, 0))
    t.take_damage(C.TANK_HP + 50)
    assert t.hp == 0
    assert not t.alive


def test_take_damage_truncates_fractional():
    t = Tank(x=0, color=(0, 0, 0))
    t.take_damage(12.7)
    assert t.hp == C.TANK_HP - 12


def test_body_center_above_seat():
    t = Tank(x=100, color=(0, 0, 0), y=300)
    cx, cy = t.body_center()
    assert cx == 100.0
    assert cy == 300.0 - C.TANK_BODY_H / 2
