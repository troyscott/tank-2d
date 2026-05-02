# 2D Tank Artillery — Design Spec

**Genre:** Side-view turn-based artillery (Scorched Earth lineage)
**Players:** 1 human vs 1 AI bot
**Engine:** Python 3.11+ / pygame 2.5+
**v1 scope:** destructible terrain, score/round system, sound, 3 AI difficulties

---

## 1. Architecture

```
main.py                    # entry point — instantiates Game, runs loop
src/tanks/
  config.py                # all tunable constants in one place
  game.py                  # state machine, scene transitions, scoring
  terrain.py               # 1D heightmap, craters, render
  tank.py                  # Tank entity (driven by Controller)
  projectile.py            # ballistics + collision + explosion
  controller.py            # ABC: PlayerController, AIController
  ai.py                    # AI logic (3 difficulties)
  audio.py                 # pygame.mixer wrapper, channel pool
  hud.py                   # angle/power/wind indicators, score
tests/
  test_terrain.py          # heightmap mutation, crater math
  test_projectile.py       # parabolic physics (deterministic w/ seed)
  test_ai.py               # solver convergence, noise envelope
```

**Why a `Controller` ABC:** decouples Tank from input source. Same `Tank` works for player, AI, or future networked play. Makes AI testable headless.

```python
class Controller(ABC):
    def decide(self, tank: Tank, world: World) -> TurnAction: ...

@dataclass
class TurnAction:
    angle_delta: float       # -1..+1 per tick
    power_delta: float       # -1..+1 per tick
    fire: bool
```

---

## 2. State machine

```
MENU → PLAYER_TURN ⇄ PROJECTILE_FLIGHT → AI_TURN ⇄ PROJECTILE_FLIGHT
                                              ↓
                                       ROUND_END → next round / MATCH_END
```

State owns its own update/render. Transitions are explicit method calls on `Game`, not implicit flag flips.

---

## 3. Terrain model

1D heightmap: `heights: list[int]` of length `SCREEN_WIDTH`. `heights[x]` = y-coordinate of ground top at column x. Lower y = higher ground (pygame convention).

**Generation:** midpoint displacement (1D fractal). Roughness factor in config.
**Render:** single `pygame.draw.polygon` per frame — points = `[(0, H), *enumerate(heights), (W, H)]`.
**Crater:** parabolic notch `heights[x] = max(heights[x], cy + sqrt(r² - (x-cx)²))` clamped to screen.
**Tank seating:** every frame, snap tank y to `heights[tank.x]` so tanks ride the deformed terrain.

**Why heightmap not bitmap:** O(W) collision (one array lookup), trivial crater math, no surfarray gymnastics. Tradeoff: no overhangs — fine for v1.

---

## 4. Physics

Euler integration at 60 fps (dt = 1/60).

```
vx += wind * dt
vy += GRAVITY * dt
x  += vx * dt
y  += vy * dt
```

**Collision:** projectile hits terrain when `y >= heights[int(x)]`. Hits tank when within `TANK_HITBOX_RADIUS` of tank center.
**Determinism:** seed `random` once at round start. Physics has no randomness; only wind and AI noise do. → unit-testable without pygame.

---

## 5. AI design

Single solver, three difficulties via noise injection.

**Solver:** closed-form solution for projectile angle given target `(dx, dy)`, fixed power `v`, gravity `g`:

```
angle = 0.5 * atan2(v² ± sqrt(v⁴ - g(g·dx² + 2·dy·v²)), g·dx)
```

If no solution (out of range), pick max range angle and let the player escape.

| Difficulty | Angle σ | Power σ | Wind-aware | Memory |
|------------|---------|---------|------------|--------|
| Easy       | 15°     | 20%     | No         | None   |
| Medium     | 5°      | 8%      | No         | Last shot offset |
| Hard       | 1°      | 2%      | Yes        | Last shot offset |

**Memory rule:** if last shot landed at offset `Δx` from target, next shot adjusts by `−0.6·Δx` (proportional correction).

---

## 6. Config (extracted to `config.py`)

| Constant | Default | Notes |
|----------|---------|-------|
| `SCREEN_W, SCREEN_H` | 1024, 640 | |
| `FPS` | 60 | |
| `GRAVITY` | 400 px/s² | tune for arc feel |
| `WIND_RANGE` | (-50, 50) px/s² | per-round random |
| `POWER_MIN, POWER_MAX` | 100, 800 | initial speed |
| `ANGLE_MIN, ANGLE_MAX` | 0°, 180° | 90° = straight up |
| `TANK_HP` | 100 | |
| `EXPLOSION_RADIUS` | 35 px | |
| `EXPLOSION_DAMAGE` | 60 (max, falls off linearly) | |
| `ROUNDS_TO_WIN` | 3 | best of 5 |
| `TERRAIN_ROUGHNESS` | 0.6 | midpoint displacement |

---

## 7. Audio

`pygame.mixer` with 8-channel pool. SFX are procedurally generated at startup using `numpy` + `pygame.sndarray` — no asset files. Synthesis is intentionally simple — single-component waveforms with a single envelope per sound — because layered synths read as multiple events when actually played, even when only one `play()` call fires.

Three sounds:
- `fire` — descending sine sweep (180→60 Hz), exponential decay; ~150 ms.
- `explosion` — bright noise burst (light low-pass), fast decay; ~150 ms. Played when a projectile lands in dirt with no tank in the blast radius.
- `hit` — darker noise burst (heavier low-pass than `explosion`), single envelope, slightly louder; ~180 ms. Distinct from `explosion` by tone (darker / heavier), not by layering. Played when a projectile damages a tank. *Layered versions with a metallic ring on top sounded like multiple events for a single impact — kept it single-component on purpose.*

The `explosion` and `hit` events are mutually exclusive — exactly one impact sound per impact, chosen by whether any tank took damage. (Earlier versions layered `explosion` + `hit` on tank hits, which sounded like a doubled blast.)

**Cut from earlier drafts:** `tick` (aim feedback) was noise during a state where the player is already getting visual feedback from the HUD; `round_win` (arpeggio) duplicated the on-screen "ROUND OVER" overlay. Both removed.

**Browser caveat:** `pygame.mixer.init()` can block on the locked AudioContext in pygbag — see `docs/browser-build.md` for the deferred-init pattern in `AudioSystem._try_init`.

---

## 8. Build order — vertical slices

Each slice is **independently runnable** (`python main.py`). Acceptance = manual playtest.

| # | Slice | Acceptance criteria |
|---|-------|---------------------|
| 1 | Terrain + 2 stationary tanks | Window opens, terrain renders, two tanks sit on it. Quit with ESC. |
| 2 | Aim + fire + ballistics | Player 1 (left/right adjust angle, up/down adjust power, space fires). Shell flies, hits terrain, prints "BOOM" to console. |
| 3 | Damage + craters | Hit creates crater. Tank in blast radius loses HP. HP bar renders. Tank dies → "ROUND OVER". |
| 4 | Turn loop + AI | Turns alternate. AI takes its turn (medium difficulty). Wind shown in HUD, affects shells. |
| 5 | Score + sound + polish | Best-of-5 rounds, score tracker, all 5 SFX wired, win screen, difficulty select on menu. |

---

## 9. Controls

| Key | Action |
|-----|--------|
| ← / → | Aim angle |
| ↑ / ↓ | Power |
| Space | Fire |
| 1 / 2 / 3 | (menu) Easy / Medium / Hard |
| ESC | Quit / back to menu |

---

## 10. Testing

Pytest. Pygame-free tests for: heightmap mutation (terrain.py), projectile trajectory given seeded wind (projectile.py), AI solver convergence + noise envelope (ai.py). Render and audio not tested — manual.

```bash
pytest tests/ -v          # unit tests, no display needed
python main.py            # play
```

---

## 11. Dependencies

```
pygame>=2.5
numpy>=1.26      # SFX synthesis only
pytest>=8.0      # dev only
```

No other runtime deps. Single `requirements.txt`.

---

## 12. Cadence

Step-by-step. After each slice: I deliver code, you run it, we adjust constants/feel, then proceed. Physics constants (gravity, power range, explosion radius) will need human playtesting — they cannot be tuned without feel.
