import functools
import random

import pygame
from . import config as C


class Renderer:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Tank Game")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))

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

    def draw(self, game, touch_mode: bool, virtual_keys: dict[str, bool]) -> None:
        if self.bg_img:
            self.game_surface.blit(self.bg_img, (0, 0))
        else:
            self.game_surface.fill(C.SKY_COLOR)

        if game.state == "menu":
            self._render_menu(self.game_surface, game)
            self.screen.blit(self.game_surface, (0, 0))
            pygame.display.flip()
            return

        game.terrain.render(self.game_surface)
        for t in game.tanks:
            t.render(self.game_surface)
        if game.flying is not None:
            self._render_projectile(self.game_surface, game.flying)

        game.particles.render(self.game_surface, additive=False)
        game.particles.render(self.game_surface, additive=True)

        self._render_hud(self.game_surface, game)
        if game.state in ("player_turn", "ai_turn", "flight"):
            self._render_touch_ui(self.game_surface, touch_mode, virtual_keys)

        if game.state == "round_over":
            self._render_round_over(self.game_surface, game)
        elif game.state == "match_end":
            self._render_match_end(self.game_surface, game)

        dx, dy = 0.0, 0.0
        if game.shake_timer > 0 and game.shake_amount > 0.5:
            dx = random.uniform(-game.shake_amount, game.shake_amount)
            dy = random.uniform(-game.shake_amount, game.shake_amount)

        self.screen.blit(self.game_surface, (int(dx), int(dy)))
        pygame.display.flip()

    def _draw_text_with_shadow(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int],
        pos: tuple[int, int],
        anchor: str = "topleft",
        offset: tuple[int, int] = (2, 2),
    ) -> None:
        surf = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))
        rect = surf.get_rect(**{anchor: pos})
        shadow_rect = rect.copy()
        shadow_rect.x += offset[0]
        shadow_rect.y += offset[1]
        surface.blit(shadow, shadow_rect)
        surface.blit(surf, rect)

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _get_projectile_glow(radius: int, r: int, g: int, b: int) -> pygame.Surface:
        glow_size = radius * 4
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (r, g, b, 100), (glow_size, glow_size), glow_size)
        return glow

    def _render_projectile(self, surface: pygame.Surface, proj) -> None:
        radius = C.PROJECTILE_RADIUS
        glow = self._get_projectile_glow(
            radius, C.PROJECTILE_COLOR[0], C.PROJECTILE_COLOR[1], C.PROJECTILE_COLOR[2]
        )
        glow_size = radius * 4
        surface.blit(
            glow,
            (int(proj.x - glow_size), int(proj.y - glow_size)),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (int(proj.x), int(proj.y)),
            radius,
        )

    def _render_touch_ui(
        self, surface: pygame.Surface, touch_mode: bool, virtual_keys: dict[str, bool]
    ) -> None:
        if not touch_mode:
            return

        def draw_btn(rect, text, active):
            color = (255, 255, 255, 100) if active else (255, 255, 255, 30)
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, color, btn_surf.get_rect(), border_radius=10)
            pygame.draw.rect(
                btn_surf, (255, 255, 255, 150), btn_surf.get_rect(), 2, border_radius=10
            )
            surface.blit(btn_surf, rect.topleft)

            txt_surf = self.font.render(text, True, (255, 255, 255))
            txt_rect = txt_surf.get_rect(center=rect.center)
            surface.blit(txt_surf, txt_rect)

        # Aim (Bottom Left)
        draw_btn(
            pygame.Rect(20, C.SCREEN_H - 100, 80, 80),
            "<",
            virtual_keys.get("LEFT", False),
        )
        draw_btn(
            pygame.Rect(120, C.SCREEN_H - 100, 80, 80),
            ">",
            virtual_keys.get("RIGHT", False),
        )

        # Power & Fire (Bottom Right)
        draw_btn(
            pygame.Rect(C.SCREEN_W - 300, C.SCREEN_H - 100, 80, 80),
            "P-",
            virtual_keys.get("DOWN", False),
        )
        draw_btn(
            pygame.Rect(C.SCREEN_W - 200, C.SCREEN_H - 100, 80, 80),
            "P+",
            virtual_keys.get("UP", False),
        )
        draw_btn(
            pygame.Rect(C.SCREEN_W - 100, C.SCREEN_H - 100, 80, 80),
            "FIRE",
            virtual_keys.get("SPACE", False),
        )

    def _render_menu(self, surface: pygame.Surface, game) -> None:
        # Draw a semi-transparent dark overlay to dim the background
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        def draw_menu_item(key_text, label_text, color, y_pos):
            self._draw_text_with_shadow(
                surface,
                self.menu_font,
                key_text,
                color,
                (C.SCREEN_W // 2 - 15, y_pos),
                anchor="topright",
            )
            self._draw_text_with_shadow(
                surface,
                self.menu_font,
                label_text,
                color,
                (C.SCREEN_W // 2 + 15, y_pos),
                anchor="topleft",
            )

        self._draw_text_with_shadow(
            surface,
            self.title_font,
            "TANK",
            C.HUD_COLOR,
            (C.SCREEN_W // 2, C.SCREEN_H // 2 - 80),
            anchor="center",
            offset=(4, 4),
        )
        self._draw_text_with_shadow(
            surface,
            self.menu_font,
            "best-of-5 artillery duel",
            C.HUD_DIM_COLOR,
            (C.SCREEN_W // 2, C.SCREEN_H // 2 - 30),
            anchor="center",
        )

        for i, (key_val, label, color) in enumerate(
            [
                ("1", "EASY", C.HUD_COLOR),
                ("2", "MEDIUM", C.HUD_COLOR),
                ("3", "HARD", C.HUD_COLOR),
            ]
        ):
            draw_menu_item(key_val, label, color, C.SCREEN_H // 2 + 20 + i * 32)

        sound_state = "ON" if game.audio.enabled else "OFF"
        draw_menu_item(
            "M",
            f"SOUND ({sound_state})",
            C.HUD_DIM_COLOR,
            C.SCREEN_H // 2 + 20 + 3 * 32 + 10,
        )

        self._draw_text_with_shadow(
            surface,
            self.font,
            "ESC quits",
            C.HUD_DIM_COLOR,
            (C.SCREEN_W // 2, C.SCREEN_H - 40),
            anchor="center",
        )

    def _render_hud(self, surface: pygame.Surface, game) -> None:
        # Left: turn status
        if game.state == "player_turn":
            left = (
                f"YOU   ANGLE {game.player.angle_deg:5.1f}   "
                f"POWER {game.player.power:5.0f}"
            )
            color = C.HUD_COLOR
        elif game.state == "ai_turn":
            left = "AI THINKING..."
            color = C.HUD_DIM_COLOR
        elif game.state == "flight":
            who = "YOU" if game.current_tank is game.player else "AI"
            left = f"{who} fired"
            color = C.HUD_DIM_COLOR
        else:
            left = ""
            color = C.HUD_COLOR

        if left:
            self._draw_text_with_shadow(
                surface, self.font, left, color, (10, 8), anchor="topleft"
            )

        # Center: score
        score_str = f"{game.player_score}  -  {game.ai_score}    [{game.difficulty}]"
        self._draw_text_with_shadow(
            surface,
            self.font,
            score_str,
            C.HUD_COLOR,
            (C.SCREEN_W // 2, 8),
            anchor="midtop",
        )

        # Right: wind
        wind_str = self._wind_string(game.wind)
        self._draw_text_with_shadow(
            surface,
            self.font,
            wind_str,
            C.HUD_COLOR,
            (C.SCREEN_W - 10, 8),
            anchor="topright",
        )

        # Player HP Bar
        p_frac = game.player.hp / C.TANK_HP
        p_w = int(150 * p_frac)
        pygame.draw.rect(surface, C.HP_BAR_BG_COLOR, (10, 36, 150, 8))
        if p_w > 0:
            r = int(255 * (1.0 - p_frac))
            g = int(255 * p_frac)
            pygame.draw.rect(surface, (r, g, 60), (10, 36, p_w, 8))

        # AI HP Bar
        ai_frac = game.ai.hp / C.TANK_HP
        ai_w = int(150 * ai_frac)
        ai_x = C.SCREEN_W - 10 - 150
        pygame.draw.rect(surface, C.HP_BAR_BG_COLOR, (ai_x, 36, 150, 8))
        if ai_w > 0:
            r = int(255 * (1.0 - ai_frac))
            g = int(255 * ai_frac)
            pygame.draw.rect(surface, (r, g, 60), (ai_x + 150 - ai_w, 36, ai_w, 8))

    def _wind_string(self, wind: float) -> str:
        mag = abs(wind)
        if mag < 1.0:
            return "WIND --- 0"
        arrow = ">" if wind > 0 else "<"
        bars = arrow * max(1, min(5, int(mag / 10) + 1))
        return f"WIND {bars} {wind:+.0f}"

    def _render_round_over(self, surface: pygame.Surface, game) -> None:
        msg = f"ROUND — {game.round_over_msg}"
        sub = (
            f"score {game.player_score} - {game.ai_score}    "
            f"press R for next round, ESC to quit"
        )
        self._draw_overlay(surface, msg, sub)

    def _render_match_end(self, surface: pygame.Surface, game) -> None:
        msg = game.match_over_msg
        sub = (
            f"final score {game.player_score} - {game.ai_score}    "
            f"press R for menu, ESC to quit"
        )
        self._draw_overlay(surface, msg, sub)

    def _draw_overlay(self, surface: pygame.Surface, msg: str, sub: str) -> None:
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        self._draw_text_with_shadow(
            surface,
            self.big_font,
            msg,
            C.ROUND_OVER_COLOR,
            (C.SCREEN_W // 2, C.SCREEN_H // 2 - 18),
            anchor="center",
            offset=(3, 3),
        )
        self._draw_text_with_shadow(
            surface,
            self.font,
            sub,
            C.HUD_DIM_COLOR,
            (C.SCREEN_W // 2, C.SCREEN_H // 2 + 18),
            anchor="center",
        )
