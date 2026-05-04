import random
import pygame

from . import config as C
from .controller import AIController, PlayerController, World
from .projectile import Projectile, damage_at
from .tank import Tank
from .terrain import Terrain
from .particles import ParticleSystem
from .audio import AudioSystem
from .input import Intent


def round_outcome(player_alive: bool, ai_alive: bool) -> tuple[str, int, int]:
    """Decide round outcome from final HP states. Returns (msg, p_delta, ai_delta)."""
    if not player_alive and not ai_alive:
        return ("DRAW", 0, 0)
    if not player_alive:
        return ("AI WINS", 0, 1)
    if not ai_alive:
        return ("PLAYER WINS", 1, 0)
    return ("ONGOING", 0, 0)


def is_match_over(
    player_score: int, ai_score: int, threshold: int = C.ROUNDS_TO_WIN
) -> bool:
    return player_score >= threshold or ai_score >= threshold


class Game:
    def __init__(
        self,
        seed: int | None = None,
        ai_difficulty: str = C.AI_DEFAULT_DIFFICULTY,
        skip_menu: bool = False,
    ) -> None:
        self.rng = random.Random(seed)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=seed)
        self.player = Tank(x=C.PLAYER_X, color=C.PLAYER_COLOR, facing=+1)
        self.ai = Tank(x=C.AI_X, color=C.AI_COLOR, facing=-1)
        self.tanks: list[Tank] = [self.player, self.ai]
        for t in self.tanks:
            self.terrain.flatten_under(t.x, C.TANK_BODY_W + 10)
            t.seat(self.terrain)

        self.player_ctrl = PlayerController()
        self.ai_ctrl = AIController(
            difficulty=ai_difficulty,
            rng=random.Random(self.rng.randint(0, 1_000_000)),
        )
        self.difficulty = ai_difficulty

        self.player_score = 0
        self.ai_score = 0
        self.wind = self._roll_wind()
        self.flying: Projectile | None = None
        self.current_tank: Tank = self.player
        self.next_tank: Tank | None = None
        self.round_over_msg = ""
        self.match_over_msg = ""

        self._impact_timer = 0.0
        self._impact_landing_x: float | None = None
        self._impact_dying = False

        self.particles = ParticleSystem()
        self.audio = AudioSystem()
        self.shake_timer = 0.0
        self.shake_amount = 0.0

        if skip_menu:
            self.start_match(ai_difficulty)
        else:
            self.state = "menu"

    def _controller_for(self, tank: Tank):
        return self.player_ctrl if tank is self.player else self.ai_ctrl

    def _world(self) -> World:
        return World(
            terrain=self.terrain,
            wind=self.wind,
            gravity=C.GRAVITY,
            tanks=self.tanks,
        )

    def _roll_wind(self) -> float:
        lo, hi = C.WIND_RANGE
        return self.rng.uniform(lo, hi)

    def start_match(self, difficulty: str) -> None:
        self.difficulty = difficulty
        self.player_score = 0
        self.ai_score = 0
        self.ai_ctrl = AIController(
            difficulty=difficulty,
            rng=random.Random(self.rng.randint(0, 1_000_000)),
        )
        self.start_round()

    def start_round(self) -> None:
        new_seed = self.rng.randint(0, 1_000_000)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=new_seed)
        for t in self.tanks:
            t.hp = C.TANK_HP
            self.terrain.flatten_under(t.x, C.TANK_BODY_W + 10)
            t.seat(self.terrain)
        self.wind = self._roll_wind()
        self.flying = None
        self.current_tank = self.player
        self.next_tank = None
        self.state = "player_turn"
        self.round_over_msg = ""
        self.ai_ctrl.last_offset_x = 0.0
        self._controller_for(self.current_tank).begin_turn(
            self.current_tank, self._world()
        )

    def handle_intent(self, intent: Intent) -> bool:
        """Process an intent, returning False if the game should quit."""
        if intent.action == "QUIT":
            return False
        elif intent.action == "TOGGLE_AUDIO":
            self.audio.toggle()
        elif intent.action == "START_MATCH":
            if intent.payload:
                self.start_match(intent.payload)
        elif intent.action == "START_ROUND":
            self.start_round()
        elif intent.action == "GOTO_MENU":
            self.state = "menu"
        return True

    def update(
        self,
        dt: float,
        virtual_keys: dict[str, bool],
        frame_events: list[pygame.event.Event],
    ) -> None:
        self.particles.update(dt)

        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_amount *= 0.9

        for t in self.tanks:
            if t.alive and t.hp < C.TANK_HP * 0.5:
                if self.rng.random() < 0.2:
                    cx, cy = t.body_center()
                    self.particles.spawn_tank_smoke(cx, cy)

        if self.state in ("player_turn", "ai_turn"):
            ctrl = self._controller_for(self.current_tank)
            fired = ctrl.tick(
                self.current_tank, self._world(), dt, frame_events, virtual_keys
            )
            if fired:
                self._fire(self.current_tank)
                self.next_tank = self._other(self.current_tank)
                self.state = "flight"
        elif self.state == "flight" and self.flying is not None:
            self.flying.update(dt, gravity=C.GRAVITY, wind=self.wind)
            self.particles.spawn_smoke_trail(self.flying.x, self.flying.y)
            if self.flying.hit_terrain(self.terrain):
                self._on_impact(self.flying.x, self.flying.y)
            elif self.flying.off_screen(C.SCREEN_W, C.SCREEN_H):
                # Off-screen miss: no impact sound, no settle period
                self._end_flight(landing_x=None)
        elif self.state == "impact":
            self._impact_timer -= dt
            if self._impact_timer <= 0.0:
                if self._impact_dying:
                    self._controller_for(self.current_tank).end_turn(
                        self.current_tank, self._world(), self._impact_landing_x
                    )
                    self.flying = None
                    self._enter_round_over()
                else:
                    self._end_flight(landing_x=self._impact_landing_x)

    def _other(self, tank: Tank) -> Tank:
        return self.ai if tank is self.player else self.player

    def _fire(self, tank: Tank) -> None:
        tip_x, tip_y = tank.barrel_tip()
        self.flying = Projectile.fired_from(
            tip_x, tip_y, tank.angle_deg, tank.power, tank.facing
        )
        if tank is self.player:
            self.audio.play("fire_blue")
        else:
            self.audio.play("fire_red")

    def _on_impact(self, x: float, y: float) -> None:
        self.terrain.apply_crater(int(x), y, C.EXPLOSION_RADIUS)
        self.particles.spawn_explosion(x, y)
        if self.current_tank is self.player:
            self.audio.play("impact_blue")
        else:
            self.audio.play("impact_red")
        self.shake_timer = 0.5
        self.shake_amount = 15.0
        impact = (x, y)
        for t in self.tanks:
            if not t.alive:
                continue
            dmg = damage_at(impact, t.body_center())
            if dmg > 0:
                t.take_damage(dmg)
        for t in self.tanks:
            t.seat(self.terrain)
        print(
            f"BOOM at ({int(x)},{int(y)})  wind={self.wind:+.0f}  "
            f"player_hp={self.player.hp} ai_hp={self.ai.hp}"
        )

        self._impact_landing_x = x
        self._impact_dying = (not self.player.alive) or (not self.ai.alive)
        self._impact_timer = C.IMPACT_SETTLE_DURATION
        self.state = "impact"

    def _end_flight(self, landing_x: float | None, dying: bool = False) -> None:
        self._controller_for(self.current_tank).end_turn(
            self.current_tank, self._world(), landing_x
        )
        self.flying = None
        if dying:
            return
        nxt = self.next_tank or self._other(self.current_tank)
        self.current_tank = nxt
        self.next_tank = None
        self.state = "player_turn" if self.current_tank is self.player else "ai_turn"
        self._controller_for(self.current_tank).begin_turn(
            self.current_tank, self._world()
        )

    def _enter_round_over(self) -> None:
        msg, p_delta, ai_delta = round_outcome(self.player.alive, self.ai.alive)
        self.round_over_msg = msg
        self.player_score += p_delta
        self.ai_score += ai_delta
        if is_match_over(self.player_score, self.ai_score):
            self.match_over_msg = (
                "YOU WIN THE MATCH"
                if self.player_score > self.ai_score
                else "AI WINS THE MATCH"
            )
            self.state = "match_end"
        else:
            self.state = "round_over"
