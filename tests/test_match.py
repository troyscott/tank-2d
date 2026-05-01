import pytest

from tanks import config as C
from tanks.game import is_match_over, round_outcome


def test_round_outcome_player_wins_when_ai_dead():
    msg, dp, dai = round_outcome(player_alive=True, ai_alive=False)
    assert msg == "PLAYER WINS"
    assert (dp, dai) == (1, 0)


def test_round_outcome_ai_wins_when_player_dead():
    msg, dp, dai = round_outcome(player_alive=False, ai_alive=True)
    assert msg == "AI WINS"
    assert (dp, dai) == (0, 1)


def test_round_outcome_draw_when_both_dead():
    msg, dp, dai = round_outcome(player_alive=False, ai_alive=False)
    assert msg == "DRAW"
    assert (dp, dai) == (0, 0)


def test_round_outcome_ongoing_when_both_alive():
    msg, dp, dai = round_outcome(player_alive=True, ai_alive=True)
    assert msg == "ONGOING"
    assert (dp, dai) == (0, 0)


@pytest.mark.parametrize(
    "p_score,ai_score,expected",
    [
        (0, 0, False),
        (2, 2, False),
        (3, 0, True),
        (0, 3, True),
        (3, 2, True),
        (2, 3, True),
    ],
)
def test_is_match_over(p_score, ai_score, expected):
    assert is_match_over(p_score, ai_score) is expected


def test_is_match_over_uses_default_threshold():
    assert is_match_over(C.ROUNDS_TO_WIN, 0) is True
    assert is_match_over(C.ROUNDS_TO_WIN - 1, 0) is False
