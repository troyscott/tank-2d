import asyncio
import random

import pygame

from . import config as C
from .controller import AIController, PlayerController, World
from .projectile import Projectile, damage_at
from .tank import Tank
from .terrain import Terrain
from .particles import ParticleSystem
from .audio import AudioSystem

STATE_MENU = "menu"
STATE_PLAYER_TURN = "player_turn"
STATE_AI_TURN = "ai_turn"
STATE_FLIGHT = "flight"
STATE_IMPACT = "impact"
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
        # Initialize only the pygame modules we need — explicitly skip
        # pygame.init() (which would also fire mixer.init()). The game ships
        # silent on purpose; see specs/SPEC.md for the audio history.
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Tank Game")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        # Font(None, ...) uses pygame's bundled default font and works the
        # same on native + pygbag/browser. SysFont triggers a system font
        # lookup that hangs in WebAssembly.
        font_path = "assets/Rajdhani-Bold.ttf"
        try:
            self.font = pygame.font.Font(font_path, C.HUD_FONT_SIZE)
            self.big_font = pygame.font.Font(font_path, C.ROUND_OVER_FONT_SIZE)
            self.title_font = pygame.font.Font(font_path, C.MENU_TITLE_FONT_SIZE)
            self.menu_font = pygame.font.Font(font_path, C.MENU_LINE_FONT_SIZE)
        except Exception:
            self.font = pygame.font.Font(None, C.HUD_FONT_SIZE)
            self.big_font = pygame.font.Font(None, C.ROUND_OVER_FONT_SIZE)
            self.title_font = pygame.font.Font(None, C.MENU_TITLE_FONT_SIZE)
            self.menu_font = pygame.font.Font(None, C.MENU_LINE_FONT_SIZE)
            
        try:
            self.bg_img = pygame.image.load("assets/bg.png").convert()
            self.bg_img = pygame.transform.scale(self.bg_img, (C.SCREEN_W, C.SCREEN_H))
        except Exception:
            self.bg_img = None
            
        self.game_surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))

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
        self._frame_events: list[pygame.event.Event] = []
        # After a projectile lands, hold STATE_IMPACT for a beat so the crater
        # has time to register before the next turn starts. These remember
        # what _end_flight needs to do once the timer expires.
        self._impact_timer = 0.0
        self._impact_landing_x: float | None = None
        self._impact_dying = False
        self.running = True
        
        self.particles = ParticleSystem()
        self.audio = AudioSystem()
        self.shake_timer = 0.0
        self.shake_amount = 0.0

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
                elif event.key == pygame.K_m:
                    self.audio.toggle()
                elif self.state == STATE_MENU and event.key in DIFFICULTY_KEYS:
                    self._start_match(DIFFICULTY_KEYS[event.key])
                elif event.key == pygame.K_r:
                    if self.state == STATE_ROUND_OVER:
                        self._start_round()
                    elif self.state == STATE_MATCH_END:
                        self.state = STATE_MENU
        self._frame_events = events

    def _update(self, dt: float) -> None:
        self.particles.update(dt)
        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_amount *= 0.9
            
        for t in self.tanks:
            if t.alive and t.hp < C.TANK_HP * 0.5:
                if random.random() < 0.2:
                    cx, cy = t.body_center()
                    self.particles.spawn_tank_smoke(cx, cy)
                    
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
            self.particles.spawn_smoke_trail(self.flying.x, self.flying.y)
            if self.flying.hit_terrain(self.terrain):
                self._on_impact(self.flying.x, self.flying.y)
            elif self.flying.off_screen(C.SCREEN_W, C.SCREEN_H):
                # Off-screen miss: no impact sound, no settle period — just
                # hand the turn over.
                self._end_flight(landing_x=None)
        elif self.state == STATE_IMPACT:
            self._impact_timer -= dt
            if self._impact_timer <= 0.0:
                # Settle's done — either roll into the round-over screen (if
                # someone died) or hand the turn over.
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
        self.audio.play("fire")

    def _on_impact(self, x: float, y: float) -> None:
        self.terrain.apply_crater(int(x), y, C.EXPLOSION_RADIUS)
        self.particles.spawn_explosion(x, y)
        self.audio.play("explosion")
        self.shake_timer = 0.5
        self.shake_amount = 15.0
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
        print(
            f"BOOM at ({int(x)},{int(y)})  wind={self.wind:+.0f}  "
            f"player_hp={self.player.hp} ai_hp={self.ai.hp}"
        )

        # Hold STATE_IMPACT briefly so the bang and the crater register before
        # the next turn (or the round-over screen) appears. _update finishes
        # the bookkeeping when the timer expires.
        self._impact_landing_x = x
        self._impact_dying = (not self.player.alive) or (not self.ai.alive)
        self._impact_timer = C.IMPACT_SETTLE_DURATION
        self.state = STATE_IMPACT

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
        if is_match_over(self.player_score, self.ai_score):
            self.match_over_msg = (
                "YOU WIN THE MATCH"
                if self.player_score > self.ai_score
                else "AI WINS THE MATCH"
            )
            self.state = STATE_MATCH_END
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
            self.terrain.flatten_under(t.x, C.TANK_BODY_W + 10)
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
        if self.bg_img:
            self.game_surface.blit(self.bg_img, (0, 0))
        else:
            self.game_surface.fill(C.SKY_COLOR)
            
        if self.state == STATE_MENU:
            self._render_menu(self.game_surface)
            self.screen.blit(self.game_surface, (0, 0))
            pygame.display.flip()
            return
            
        self.terrain.render(self.game_surface)
        for t in self.tanks:
            t.render(self.game_surface)
        if self.flying is not None:
            self.flying.render(self.game_surface)
            
        self.particles.render(self.game_surface, additive=False)
        self.particles.render(self.game_surface, additive=True)
            
        self._render_hud(self.game_surface)
        if self.state == STATE_ROUND_OVER:
            self._render_round_over(self.game_surface)
        elif self.state == STATE_MATCH_END:
            self._render_match_end(self.game_surface)
            
        dx, dy = 0, 0
        if self.shake_timer > 0 and self.shake_amount > 0.5:
            dx = random.uniform(-self.shake_amount, self.shake_amount)
            dy = random.uniform(-self.shake_amount, self.shake_amount)
            
        self.screen.blit(self.game_surface, (int(dx), int(dy)))
        pygame.display.flip()

    def _render_menu(self, surface: pygame.Surface) -> None:
        title = self.title_font.render("TANK", True, C.HUD_COLOR)
        title_rect = title.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 80))
        surface.blit(title, title_rect)

        subtitle = self.menu_font.render(
            "best-of-5 artillery duel", True, C.HUD_DIM_COLOR
        )
        sub_rect = subtitle.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 30))
        surface.blit(subtitle, sub_rect)

        for i, (label, color) in enumerate(
            [
                ("1   EASY", C.HUD_COLOR),
                ("2   MEDIUM", C.HUD_COLOR),
                ("3   HARD", C.HUD_COLOR),
            ]
        ):
            line = self.menu_font.render(label, True, color)
            r = line.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 20 + i * 32))
            surface.blit(line, r)

        sound_state = "ON" if self.audio.enabled else "OFF"
        sound_label = f"M   SOUND ({sound_state})"
        s_line = self.menu_font.render(sound_label, True, C.HUD_DIM_COLOR)
        s_r = s_line.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 20 + 3 * 32 + 10))
        surface.blit(s_line, s_r)

        hint = self.font.render(
            "ESC quits", True, C.HUD_DIM_COLOR
        )
        hint_rect = hint.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 40))
        surface.blit(hint, hint_rect)

    def _render_hud(self, surface: pygame.Surface) -> None:
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
            # draw drop shadow
            shadow = self.font.render(left, True, (0, 0, 0))
            surface.blit(shadow, (12, 10))
            surf = self.font.render(left, True, color)
            surface.blit(surf, (10, 8))

        # Center: score (best of ROUNDS_TO_WIN * 2 - 1)
        score_str = (
            f"{self.player_score}  -  {self.ai_score}    "
            f"[{self.difficulty}]"
        )
        score_surf = self.font.render(score_str, True, C.HUD_COLOR)
        score_shadow = self.font.render(score_str, True, (0, 0, 0))
        score_rect = score_surf.get_rect()
        score_rect.midtop = (C.SCREEN_W // 2, 8)
        shadow_rect = score_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        surface.blit(score_shadow, shadow_rect)
        surface.blit(score_surf, score_rect)

        # Right: wind
        wind_str = self._wind_string()
        wind_surf = self.font.render(wind_str, True, C.HUD_COLOR)
        wind_shadow = self.font.render(wind_str, True, (0, 0, 0))
        wind_rect = wind_surf.get_rect()
        wind_rect.topright = (C.SCREEN_W - 10, 8)
        shadow_rect = wind_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        surface.blit(wind_shadow, shadow_rect)
        surface.blit(wind_surf, wind_rect)

        # Player HP Bar (Top Left, below text)
        p_frac = self.player.hp / C.TANK_HP
        p_w = int(150 * p_frac)
        pygame.draw.rect(surface, C.HP_BAR_BG_COLOR, (10, 36, 150, 8))
        if p_w > 0:
            r = int(255 * (1.0 - p_frac))
            g = int(255 * p_frac)
            pygame.draw.rect(surface, (r, g, 60), (10, 36, p_w, 8))
            
        # AI HP Bar (Top Right, below text)
        ai_frac = self.ai.hp / C.TANK_HP
        ai_w = int(150 * ai_frac)
        ai_x = C.SCREEN_W - 10 - 150
        pygame.draw.rect(surface, C.HP_BAR_BG_COLOR, (ai_x, 36, 150, 8))
        if ai_w > 0:
            r = int(255 * (1.0 - ai_frac))
            g = int(255 * ai_frac)
            pygame.draw.rect(surface, (r, g, 60), (ai_x + 150 - ai_w, 36, ai_w, 8))

    def _wind_string(self) -> str:
        mag = abs(self.wind)
        if mag < 1.0:
            return "WIND --- 0"
        arrow = ">" if self.wind > 0 else "<"
        bars = arrow * max(1, min(5, int(mag / 10) + 1))
        return f"WIND {bars} {self.wind:+.0f}"

    def _render_round_over(self, surface: pygame.Surface) -> None:
        msg = f"ROUND — {self.round_over_msg}"
        sub = (
            f"score {self.player_score} - {self.ai_score}    "
            f"press R for next round, ESC to quit"
        )
        self._draw_overlay(surface, msg, sub)

    def _render_match_end(self, surface: pygame.Surface) -> None:
        msg = self.match_over_msg
        sub = (
            f"final score {self.player_score} - {self.ai_score}    "
            f"press R for menu, ESC to quit"
        )
        self._draw_overlay(surface, msg, sub)

    def _draw_overlay(self, surface: pygame.Surface, msg: str, sub: str) -> None:
        # draw a semi-transparent black overlay
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        
        surf = self.big_font.render(msg, True, C.ROUND_OVER_COLOR)
        shadow = self.big_font.render(msg, True, (0, 0, 0))
        rect = surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 18))
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        surface.blit(shadow, shadow_rect)
        surface.blit(surf, rect)
        
        sub_surf = self.font.render(sub, True, C.HUD_DIM_COLOR)
        sub_shadow = self.font.render(sub, True, (0, 0, 0))
        sub_rect = sub_surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 18))
        sub_shadow_rect = sub_rect.copy()
        sub_shadow_rect.x += 2
        sub_shadow_rect.y += 2
        surface.blit(sub_shadow, sub_shadow_rect)
        surface.blit(sub_surf, sub_rect)
