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


def test_apply_crater_lowers_ground_under_blast():
    t = Terrain(heights=[200] * C.SCREEN_W)
    cx, cy, r = 500, 200, 30
    t.apply_crater(cx, cy, r)
    # At center: depth = cy + r = 230 (lower on screen)
    assert t.heights[cx] == 230
    # Symmetric falloff: at cx ± r/2, depth = cy + sqrt(r^2 - (r/2)^2)
    expected = int(cy + (r * r - (r / 2) ** 2) ** 0.5)
    assert t.heights[cx + 15] == expected
    assert t.heights[cx - 15] == expected
    # Outside the radius: untouched
    assert t.heights[cx + r + 1] == 200
    assert t.heights[cx - r - 1] == 200


def test_apply_crater_never_raises_ground():
    # Parabola entirely above the existing ground (cy + r < heights)
    t = Terrain(heights=[200] * C.SCREEN_W)
    cx, cy, r = 500, 100, 30  # cy + r = 130 < 200
    snapshot = list(t.heights)
    t.apply_crater(cx, cy, r)
    assert t.heights == snapshot


def test_apply_crater_clamps_to_screen_bottom():
    t = Terrain(heights=[100] * C.SCREEN_W)
    cx, cy, r = 500, C.SCREEN_H, 80  # would push past screen
    t.apply_crater(cx, cy, r)
    assert max(t.heights) <= C.SCREEN_H - 4


def test_apply_crater_handles_edges():
    t = Terrain(heights=[200] * C.SCREEN_W)
    t.apply_crater(2, 200, 50)  # center near left edge, radius extends past 0
    t.apply_crater(C.SCREEN_W - 3, 200, 50)  # near right edge
    # No exceptions; heights array still right length
    assert len(t.heights) == C.SCREEN_W
