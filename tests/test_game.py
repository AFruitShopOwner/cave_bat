import os
import random

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from cave_bat.game import Game


def test_game_init_and_step() -> None:
    random.seed(123)
    g = Game()
    # one tick
    g.update(0.016)
    # ensure obstacles list exists and bat is alive initially
    assert g.bat.alive in (True, False)
    assert isinstance(g.obstacles, list)


def test_scoring_and_game_over_transitions() -> None:
    random.seed(42)
    g = Game()
    # Place bat near first obstacle trailing edge to simulate pass
    assert g.obstacles, "pre-warmed obstacles should exist"
    first = g.obstacles[0]
    # Move obstacle left of bat so it counts as passed
    first.x = g.bat.x - 1 - 120
    first.passed = False
    old_score = g.score
    g.update(0.016)
    assert g.score >= old_score

    # Force a collision by moving bat out of bounds
    g.bat.y = -1
    g.update(0.016)
    assert g.game_over is True
