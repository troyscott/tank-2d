from tanks import config as C
from tanks.terrain import Terrain


def test_heights_length_matches_width():
    t = Terrain.generate(width=C.SCREEN_W, seed=1)
    assert len(t.heights) == C.SCREEN_W


def test_heights_within_bounds():
    t = Terrain.generate(width=C.SCREEN_W, seed=1)
    assert all(C.TERRAIN_MIN_Y <= h <= C.TERRAIN_MAX_Y for h in t.heights)


def test_seed_is_deterministic():
    a = Terrain.generate(width=C.SCREEN_W, seed=42)
    b = Terrain.generate(width=C.SCREEN_W, seed=42)
    assert a.heights == b.heights


def test_different_seeds_differ():
    a = Terrain.generate(width=C.SCREEN_W, seed=1)
    b = Terrain.generate(width=C.SCREEN_W, seed=2)
    assert a.heights != b.heights


def test_height_at_clamps_out_of_range():
    t = Terrain.generate(width=C.SCREEN_W, seed=1)
    assert t.height_at(-100) == t.heights[0]
    assert t.height_at(C.SCREEN_W + 50) == t.heights[-1]
