import asyncio
import random

import pygame

from . import config as C
from .audio import AudioSystem
from .controller import AIController, PlayerController, World
from .projectile import Projectile, damage_at
from .tank import Tank
from .terrain import Terrain

STATE_MENU = "menu"
STATE_PLAYER_TURN = "player_turn"
STATE_AI_TURN = "ai_turn"
STATE_FLIGHT = "flight"
STATE_ROUND_OVER = "round_over"
STATE_MATCH_END = "match_end"

DIFFICULTY_KEYS = {
    pygame.K_1: "easy",
    pygame.K_2: "medium",
    pygame.K_3: "hard",
}


def round_outcome(player_alive: bool, ai_alive: bool) -> tuple[str, int, int]:
    """Decide round outcome from final HP states. Returns (msg, p_delta, ai_delta)."""
    if not player_alive and not ai_alive:
        return ("DRAW", 0, 0)
    if not player_alive:
        return ("AI WINS", 0, 1)
    if not ai_alive:
        return ("PLAYER WINS", 1, 0)
    return ("ONGOING", 0, 0)


def is_match_over(player_score: int, ai_score: int, threshold: int = C.ROUNDS_TO_WIN) -> bool:
    return player_score >= threshold or ai_score >= threshold


class Game:
    def __init__(
        self,
        seed: int | None = None,
        ai_difficulty: str = C.AI_DEFAULT_DIFFICULTY,
        skip_menu: bool = False,
    ) -> None:
        # Pre-init mixer with desired buffer/rate before pygame.init() so the
        # mixer comes up at our chosen settings (or no-ops on dummy audio).
        try:
            pygame.mixer.pre_init(C.AUDIO_SAMPLE_RATE, -16, 2, C.AUDIO_BUFFER)
        except pygame.error:
            pass
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Tank Game")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        # pygame.font.Font(None, ...) uses pygame's bundled default font and
        # works the same on native + pygbag/browser. SysFont triggers a system
        # font lookup that hangs in WebAssembly.
        self.font = pygame.font.Font(None, C.HUD_FONT_SIZE)
        self.big_font = pygame.font.Font(None, C.ROUND_OVER_FONT_SIZE)
        self.title_font = pygame.font.Font(None, C.MENU_TITLE_FONT_SIZE)
        self.menu_font = pygame.font.Font(None, C.MENU_LINE_FONT_SIZE)

        self.audio = AudioSystem()

        self.rng = random.Random(seed)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=seed)
        self.player = Tank(x=C.PLAYER_X, color=C.PLAYER_COLOR, facing=+1)
        self.ai = Tank(x=C.AI_X, color=C.AI_COLOR, facing=-1)
        self.tanks: list[Tank] = [self.player, self.ai]
        for t in self.tanks:
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
        self._frame_events: list[pygame.event.Event] = []
        self.running = True

        if skip_menu:
            self._start_match(ai_difficulty)
        else:
            self.state = STATE_MENU

    def _controller_for(self, tank: Tank):
        return self.player_ctrl if tank is self.player else self.ai_ctrl

    def _world(self) -> World:
        return World(
            terrain=self.terrain,
            wind=self.wind,
            gravity=C.GRAVITY,
            tanks=self.tanks,
            audio=self.audio,
        )

    def _roll_wind(self) -> float:
        lo, hi = C.WIND_RANGE
        return self.rng.uniform(lo, hi)

    async def run(self) -> None:
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()
            # Yield to the event loop so pygbag (browser/WebAssembly) can
            # render a frame; harmless under native asyncio.
            await asyncio.sleep(0)
        pygame.quit()

    def _handle_events(self) -> None:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state == STATE_MENU and event.key in DIFFICULTY_KEYS:
                    self._start_match(DIFFICULTY_KEYS[event.key])
                elif event.key == pygame.K_r:
                    if self.state == STATE_ROUND_OVER:
                        self._start_round()
                    elif self.state == STATE_MATCH_END:
                        self.state = STATE_MENU
        self._frame_events = events

    def _update(self, dt: float) -> None:
        if self.state in (STATE_PLAYER_TURN, STATE_AI_TURN):
            ctrl = self._controller_for(self.current_tank)
            fired = ctrl.tick(
                self.current_tank, self._world(), dt, self._frame_events
            )
            if fired:
                self._fire(self.current_tank)
                self.next_tank = self._other(self.current_tank)
                self.state = STATE_FLIGHT
        elif self.state == STATE_FLIGHT and self.flying is not None:
            self.flying.update(dt, gravity=C.GRAVITY, wind=self.wind)
            if self.flying.hit_terrain(self.terrain):
                self._on_impact(self.flying.x, self.flying.y)
            elif self.flying.off_screen(C.SCREEN_W, C.SCREEN_H):
                self._end_flight(landing_x=None)

    def _other(self, tank: Tank) -> Tank:
        return self.ai if tank is self.player else self.player

    def _fire(self, tank: Tank) -> None:
        tip_x, tip_y = tank.barrel_tip()
        self.flying = Projectile.fired_from(
            tip_x, tip_y, tank.angle_deg, tank.power, tank.facing
        )
        self.audio.play("fire")

    def _on_impact(self, x: float, y: float) -> None:
        self.terrain.apply_crater(int(x), y, C.EXPLOSION_RADIUS)
        impact = (x, y)
        any_hit = False
        for t in self.tanks:
            if not t.alive:
                continue
            dmg = damage_at(impact, t.body_center())
            if dmg > 0:
                t.take_damage(dmg)
                any_hit = True
        for t in self.tanks:
            t.seat(self.terrain)
        self.audio.play("explosion")
        if any_hit:
            self.audio.play("hit")
        print(
            f"BOOM at ({int(x)},{int(y)})  wind={self.wind:+.0f}  "
            f"player_hp={self.player.hp} ai_hp={self.ai.hp}"
        )
        if not self.player.alive or not self.ai.alive:
            self._end_flight(landing_x=x, dying=True)
            self._enter_round_over()
            return
        self._end_flight(landing_x=x)

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
        self.state = (
            STATE_PLAYER_TURN if self.current_tank is self.player else STATE_AI_TURN
        )
        self._controller_for(self.current_tank).begin_turn(
            self.current_tank, self._world()
        )

    def _enter_round_over(self) -> None:
        msg, p_delta, ai_delta = round_outcome(self.player.alive, self.ai.alive)
        self.round_over_msg = msg
        self.player_score += p_delta
        self.ai_score += ai_delta
        if p_delta > 0:
            self.audio.play("round_win")
        if is_match_over(self.player_score, self.ai_score):
            self.match_over_msg = (
                "YOU WIN THE MATCH"
                if self.player_score > self.ai_score
                else "AI WINS THE MATCH"
            )
            self.state = STATE_MATCH_END
            if self.player_score > self.ai_score:
                self.audio.play("round_win")
        else:
            self.state = STATE_ROUND_OVER

    def _start_match(self, difficulty: str) -> None:
        self.difficulty = difficulty
        self.player_score = 0
        self.ai_score = 0
        self.ai_ctrl = AIController(
            difficulty=difficulty,
            rng=random.Random(self.rng.randint(0, 1_000_000)),
        )
        self._start_round()

    def _start_round(self) -> None:
        new_seed = self.rng.randint(0, 1_000_000)
        self.terrain = Terrain.generate(C.SCREEN_W, seed=new_seed)
        for t in self.tanks:
            t.hp = C.TANK_HP
            t.seat(self.terrain)
        self.wind = self._roll_wind()
        self.flying = None
        self.current_tank = self.player
        self.next_tank = None
        self.state = STATE_PLAYER_TURN
        self.round_over_msg = ""
        self.ai_ctrl.last_offset_x = 0.0
        self._controller_for(self.current_tank).begin_turn(
            self.current_tank, self._world()
        )

    # ---------------- rendering ----------------
    def _render(self) -> None:
        self.screen.fill(C.SKY_COLOR)
        if self.state == STATE_MENU:
            self._render_menu()
            pygame.display.flip()
            return
        self.terrain.render(self.screen)
        for t in self.tanks:
            t.render(self.screen)
        if self.flying is not None:
            self.flying.render(self.screen)
        self._render_hud()
        if self.state == STATE_ROUND_OVER:
            self._render_round_over()
        elif self.state == STATE_MATCH_END:
            self._render_match_end()
        pygame.display.flip()

    def _render_menu(self) -> None:
        title = self.title_font.render("TANK", True, C.HUD_COLOR)
        title_rect = title.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 80))
        self.screen.blit(title, title_rect)

        subtitle = self.menu_font.render(
            "best-of-5 artillery duel", True, C.HUD_DIM_COLOR
        )
        sub_rect = subtitle.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 30))
        self.screen.blit(subtitle, sub_rect)

        for i, (label, color) in enumerate(
            [
                ("1   EASY", C.HUD_COLOR),
                ("2   MEDIUM", C.HUD_COLOR),
                ("3   HARD", C.HUD_COLOR),
            ]
        ):
            line = self.menu_font.render(label, True, color)
            r = line.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 20 + i * 32))
            self.screen.blit(line, r)

        hint = self.font.render(
            "ESC quits", True, C.HUD_DIM_COLOR
        )
        hint_rect = hint.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 40))
        self.screen.blit(hint, hint_rect)

    def _render_hud(self) -> None:
        # Left: turn status
        if self.state == STATE_PLAYER_TURN:
            left = (
                f"YOU   ANGLE {self.player.angle_deg:5.1f}   "
                f"POWER {self.player.power:5.0f}"
            )
            color = C.HUD_COLOR
        elif self.state == STATE_AI_TURN:
            left = "AI THINKING..."
            color = C.HUD_DIM_COLOR
        elif self.state == STATE_FLIGHT:
            who = "YOU" if self.current_tank is self.player else "AI"
            left = f"{who} fired"
            color = C.HUD_DIM_COLOR
        else:
            left = ""
            color = C.HUD_COLOR
        if left:
            surf = self.font.render(left, True, color)
            self.screen.blit(surf, (10, 8))

        # Center: score (best of ROUNDS_TO_WIN * 2 - 1)
        score_str = (
            f"{self.player_score}  -  {self.ai_score}    "
            f"[{self.difficulty}]"
        )
        score_surf = self.font.render(score_str, True, C.HUD_COLOR)
        score_rect = score_surf.get_rect()
        score_rect.midtop = (C.SCREEN_W // 2, 8)
        self.screen.blit(score_surf, score_rect)

        # Right: wind
        wind_surf = self.font.render(self._wind_string(), True, C.HUD_COLOR)
        wind_rect = wind_surf.get_rect()
        wind_rect.topright = (C.SCREEN_W - 10, 8)
        self.screen.blit(wind_surf, wind_rect)

    def _wind_string(self) -> str:
        mag = abs(self.wind)
        if mag < 1.0:
            return "WIND --- 0"
        arrow = ">" if self.wind > 0 else "<"
        bars = arrow * max(1, min(5, int(mag / 10) + 1))
        return f"WIND {bars} {self.wind:+.0f}"

    def _render_round_over(self) -> None:
        msg = f"ROUND — {self.round_over_msg}"
        sub = (
            f"score {self.player_score} - {self.ai_score}    "
            f"press R for next round, ESC to quit"
        )
        self._draw_overlay(msg, sub)

    def _render_match_end(self) -> None:
        msg = self.match_over_msg
        sub = (
            f"final score {self.player_score} - {self.ai_score}    "
            f"press R for menu, ESC to quit"
        )
        self._draw_overlay(msg, sub)

    def _draw_overlay(self, msg: str, sub: str) -> None:
        surf = self.big_font.render(msg, True, C.ROUND_OVER_COLOR)
        rect = surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 18))
        self.screen.blit(surf, rect)
        sub_surf = self.font.render(sub, True, C.HUD_DIM_COLOR)
        sub_rect = sub_surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 18))
        self.screen.blit(sub_surf, sub_rect)
