import random

import pygame

from . import config as C
from .controller import AIController, PlayerController, World
from .projectile import Projectile, damage_at
from .tank import Tank
from .terrain import Terrain

STATE_PLAYER_TURN = "player_turn"
STATE_AI_TURN = "ai_turn"
STATE_FLIGHT = "flight"
STATE_ROUND_OVER = "round_over"


class Game:
    def __init__(
        self,
        seed: int | None = None,
        ai_difficulty: str = C.AI_DEFAULT_DIFFICULTY,
    ) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Tank Game")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, C.HUD_FONT_SIZE)
        self.big_font = pygame.font.SysFont(None, C.ROUND_OVER_FONT_SIZE)

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

        self.wind = self._roll_wind()
        self.flying: Projectile | None = None
        self.current_tank: Tank = self.player
        self.next_tank: Tank | None = None
        self.state = STATE_PLAYER_TURN
        self.round_over_msg = ""
        self._frame_events: list[pygame.event.Event] = []
        self.running = True

        self._controller_for(self.current_tank).begin_turn(
            self.current_tank, self._world()
        )

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

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()
        pygame.quit()

    def _handle_events(self) -> None:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r and self.state == STATE_ROUND_OVER:
                    self._reset_round()
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

    def _on_impact(self, x: float, y: float) -> None:
        self.terrain.apply_crater(int(x), y, C.EXPLOSION_RADIUS)
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
        if not self.player.alive and not self.ai.alive:
            self.round_over_msg = "DRAW"
        elif not self.player.alive:
            self.round_over_msg = "AI WINS"
        else:
            self.round_over_msg = "PLAYER WINS"
        self.state = STATE_ROUND_OVER

    def _reset_round(self) -> None:
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

    def _render(self) -> None:
        self.screen.fill(C.SKY_COLOR)
        self.terrain.render(self.screen)
        for t in self.tanks:
            t.render(self.screen)
        if self.flying is not None:
            self.flying.render(self.screen)
        self._render_hud()
        if self.state == STATE_ROUND_OVER:
            self._render_round_over()
        pygame.display.flip()

    def _render_hud(self) -> None:
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
        wind_str = self._wind_string()
        wind_surf = self.font.render(wind_str, True, C.HUD_COLOR)
        wind_rect = wind_surf.get_rect()
        wind_rect.topright = (C.SCREEN_W - 10, 8)
        self.screen.blit(wind_surf, wind_rect)

    def _wind_string(self) -> str:
        mag = abs(self.wind)
        if mag < 1.0:
            return "WIND --- 0"
        arrow = ">" if self.wind > 0 else "<"
        bars = arrow * max(1, min(5, int(mag / 10) + 1))
        if self.wind > 0:
            return f"WIND {bars} {self.wind:+.0f}"
        return f"WIND {bars} {self.wind:+.0f}"

    def _render_round_over(self) -> None:
        msg = f"ROUND OVER — {self.round_over_msg}"
        sub = "press R to play again, ESC to quit"
        surf = self.big_font.render(msg, True, C.ROUND_OVER_COLOR)
        rect = surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 18))
        self.screen.blit(surf, rect)
        sub_surf = self.font.render(sub, True, C.HUD_DIM_COLOR)
        sub_rect = sub_surf.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 18))
        self.screen.blit(sub_surf, sub_rect)
