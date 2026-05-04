import pytest

from tanks import config as C
from tanks.game import Game
from tanks.input import Intent


def test_game_starts_in_menu_by_default():
    game = Game()
    assert game.state == "menu"


def test_game_skip_menu_starts_in_player_turn():
    game = Game(skip_menu=True)
    assert game.state == "player_turn"


def test_intent_start_match():
    game = Game()
    game.handle_intent(Intent("START_MATCH", "hard"))
    assert game.difficulty == "hard"
    assert game.state == "player_turn"


def test_intent_start_round_from_round_over():
    game = Game()
    game.state = "round_over"
    game.handle_intent(Intent("START_ROUND"))
    assert game.state == "player_turn"


def test_intent_quit_returns_false():
    game = Game()
    assert game.handle_intent(Intent("QUIT")) is False


def test_intent_toggle_audio():
    game = Game()
    initial = game.audio.enabled
    game.handle_intent(Intent("TOGGLE_AUDIO"))
    assert game.audio.enabled != initial


def test_game_fires_projectile():
    game = Game(skip_menu=True)
    game.player.angle_deg = 45
    game.player.power = 300

    # Tick with SPACE held down to fire
    virtual_keys = {"SPACE": True}
    game.update(0.1, virtual_keys, [])

    assert game.state == "flight"
    assert game.flying is not None
    assert game.flying.x == pytest.approx(game.player.barrel_tip()[0])


def test_projectile_landing_transitions_to_impact():
    game = Game(skip_menu=True)
    game.state = "flight"
    # Create a projectile just above terrain
    from tanks.projectile import Projectile

    game.flying = Projectile(C.SCREEN_W // 2, 0.0, 0, 100)

    # Run update loop until impact
    while game.state == "flight":
        game.update(0.01, {}, [])

    assert game.state == "impact"


def test_impact_transitions_to_next_turn():
    game = Game(skip_menu=True)
    game.state = "impact"
    game._impact_timer = 0.05
    game.current_tank = game.player
    game.next_tank = game.ai

    game.update(0.1, {}, [])
    assert game.state == "ai_turn"
    assert game.current_tank is game.ai
