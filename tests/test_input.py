import pygame
import pytest
from unittest.mock import patch

from tanks import config as C
from tanks.input import InputRouter


@pytest.fixture
def input_router():
    pygame.display.init()  # Needed for events
    return InputRouter()


def test_quit_event(input_router):
    with patch("pygame.event.get", return_value=[pygame.event.Event(pygame.QUIT)]):
        intents = input_router.poll("menu")
        assert len(intents) == 1
        assert intents[0].action == "QUIT"


def test_escape_key_quits(input_router):
    with patch(
        "pygame.event.get",
        return_value=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
    ):
        intents = input_router.poll("menu")
        assert len(intents) == 1
        assert intents[0].action == "QUIT"


def test_menu_keys_start_match(input_router):
    with patch(
        "pygame.event.get",
        return_value=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)],
    ):
        intents = input_router.poll("menu")
        assert len(intents) == 1
        assert intents[0].action == "START_MATCH"
        assert intents[0].payload == "medium"


def test_r_key_in_round_over(input_router):
    with patch(
        "pygame.event.get",
        return_value=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)],
    ):
        intents = input_router.poll("round_over")
        assert len(intents) == 1
        assert intents[0].action == "START_ROUND"


def test_touch_btn_fire(input_router):
    # Simulate touch down on FIRE button (bottom right)
    tx = (C.SCREEN_W - 60) / C.SCREEN_W
    ty = (C.SCREEN_H - 60) / C.SCREEN_H

    event = pygame.event.Event(pygame.FINGERDOWN, finger_id=1, x=tx, y=ty)
    with patch("pygame.event.get", return_value=[event]):
        input_router.poll("player_turn")

    assert input_router.touch_mode is True
    assert input_router.virtual_keys["SPACE"] is True
    assert input_router.virtual_keys["LEFT"] is False


def test_touch_btn_left(input_router):
    # Simulate touch down on LEFT button (bottom left, x=20..100)
    tx = 60 / C.SCREEN_W
    ty = (C.SCREEN_H - 60) / C.SCREEN_H

    event = pygame.event.Event(pygame.FINGERDOWN, finger_id=1, x=tx, y=ty)
    with patch("pygame.event.get", return_value=[event]):
        input_router.poll("player_turn")

    assert input_router.virtual_keys["LEFT"] is True


def test_mouse_btn_fire(input_router):
    # Simulate mouse click on FIRE button
    mx, my = C.SCREEN_W - 60, C.SCREEN_H - 60

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN)
    with patch("pygame.event.get", return_value=[event]):
        with patch("pygame.mouse.get_pos", return_value=(mx, my)):
            input_router.poll("player_turn")

    assert input_router.touch_mode is True
    assert input_router.virtual_keys["SPACE"] is True
