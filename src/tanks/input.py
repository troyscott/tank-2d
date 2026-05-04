import pygame
from dataclasses import dataclass
from . import config as C


@dataclass
class Intent:
    action: str
    payload: str | None = None


class InputRouter:
    """Consumes raw Pygame events and hardware inputs, outputting high-level Intents and Virtual Keys."""

    def __init__(self):
        self.touch_mode = False
        self.active_touches: dict[int, tuple[float, float]] = {}
        self.virtual_keys: dict[str, bool] = {
            "LEFT": False,
            "RIGHT": False,
            "UP": False,
            "DOWN": False,
            "SPACE": False,
        }
        self.frame_events: list[pygame.event.Event] = []

    def poll(self, game_state: str) -> list[Intent]:
        intents = []
        events = pygame.event.get()
        self.frame_events = events

        for event in events:
            if event.type == pygame.QUIT:
                intents.append(Intent("QUIT"))
            elif event.type == pygame.KEYDOWN:
                self.touch_mode = False
                if event.key == pygame.K_ESCAPE:
                    intents.append(Intent("QUIT"))
                elif event.key == pygame.K_m:
                    intents.append(Intent("TOGGLE_AUDIO"))
                elif game_state == "menu" and event.key in {
                    pygame.K_1: "easy",
                    pygame.K_2: "medium",
                    pygame.K_3: "hard",
                }:
                    diff = {
                        pygame.K_1: "easy",
                        pygame.K_2: "medium",
                        pygame.K_3: "hard",
                    }[event.key]
                    intents.append(Intent("START_MATCH", payload=diff))
                elif event.key == pygame.K_r:
                    if game_state == "round_over":
                        intents.append(Intent("START_ROUND"))
                    elif game_state == "match_end":
                        intents.append(Intent("GOTO_MENU"))
            elif event.type == pygame.FINGERDOWN:
                self.touch_mode = True
                tx, ty = event.x * C.SCREEN_W, event.y * C.SCREEN_H
                self.active_touches[event.finger_id] = (tx, ty)
                self._handle_touch_menu(tx, ty, game_state, intents)
            elif event.type == pygame.FINGERMOTION:
                if event.finger_id in self.active_touches:
                    self.active_touches[event.finger_id] = (
                        event.x * C.SCREEN_W,
                        event.y * C.SCREEN_H,
                    )
            elif event.type == pygame.FINGERUP:
                self.active_touches.pop(event.finger_id, None)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.touch_mode = True
                tx, ty = pygame.mouse.get_pos()
                self.active_touches[-1] = (tx, ty)
                self._handle_touch_menu(tx, ty, game_state, intents)
            elif event.type == pygame.MOUSEMOTION:
                if -1 in self.active_touches:
                    self.active_touches[-1] = pygame.mouse.get_pos()
            elif event.type == pygame.MOUSEBUTTONUP:
                self.active_touches.pop(-1, None)

        self._compute_virtual_keys(game_state)
        return intents

    def _handle_touch_menu(
        self, x: float, y: float, game_state: str, intents: list[Intent]
    ) -> None:
        menu_1 = pygame.Rect(C.SCREEN_W // 2 - 100, C.SCREEN_H // 2 + 10, 200, 30)
        menu_2 = pygame.Rect(C.SCREEN_W // 2 - 100, C.SCREEN_H // 2 + 42, 200, 30)
        menu_3 = pygame.Rect(C.SCREEN_W // 2 - 100, C.SCREEN_H // 2 + 74, 200, 30)
        menu_m = pygame.Rect(C.SCREEN_W // 2 - 100, C.SCREEN_H // 2 + 116, 200, 30)
        menu_r = pygame.Rect(C.SCREEN_W // 2 - 200, C.SCREEN_H // 2, 400, 80)

        if game_state == "menu":
            if menu_1.collidepoint(x, y):
                intents.append(Intent("START_MATCH", "easy"))
            elif menu_2.collidepoint(x, y):
                intents.append(Intent("START_MATCH", "medium"))
            elif menu_3.collidepoint(x, y):
                intents.append(Intent("START_MATCH", "hard"))
            elif menu_m.collidepoint(x, y):
                intents.append(Intent("TOGGLE_AUDIO"))
        elif game_state == "round_over":
            if menu_r.collidepoint(x, y):
                intents.append(Intent("START_ROUND"))
        elif game_state == "match_end":
            if menu_r.collidepoint(x, y):
                intents.append(Intent("GOTO_MENU"))

    def _compute_virtual_keys(self, game_state: str) -> None:
        self.virtual_keys = {
            "LEFT": False,
            "RIGHT": False,
            "UP": False,
            "DOWN": False,
            "SPACE": False,
        }

        try:
            keys = pygame.key.get_pressed()
            self.virtual_keys["LEFT"] = keys[pygame.K_LEFT]
            self.virtual_keys["RIGHT"] = keys[pygame.K_RIGHT]
            self.virtual_keys["UP"] = keys[pygame.K_UP]
            self.virtual_keys["DOWN"] = keys[pygame.K_DOWN]
            self.virtual_keys["SPACE"] = keys[pygame.K_SPACE]
        except pygame.error:
            # Video system not initialized (e.g. headless tests)
            pass

        btn_left = pygame.Rect(20, C.SCREEN_H - 100, 80, 80)
        btn_right = pygame.Rect(120, C.SCREEN_H - 100, 80, 80)
        btn_down = pygame.Rect(C.SCREEN_W - 300, C.SCREEN_H - 100, 80, 80)
        btn_up = pygame.Rect(C.SCREEN_W - 200, C.SCREEN_H - 100, 80, 80)
        btn_fire = pygame.Rect(C.SCREEN_W - 100, C.SCREEN_H - 100, 80, 80)

        for x, y in self.active_touches.values():
            if game_state == "player_turn":
                if btn_left.collidepoint(x, y):
                    self.virtual_keys["LEFT"] = True
                if btn_right.collidepoint(x, y):
                    self.virtual_keys["RIGHT"] = True
                if btn_down.collidepoint(x, y):
                    self.virtual_keys["DOWN"] = True
                if btn_up.collidepoint(x, y):
                    self.virtual_keys["UP"] = True
                if btn_fire.collidepoint(x, y):
                    self.virtual_keys["SPACE"] = True
