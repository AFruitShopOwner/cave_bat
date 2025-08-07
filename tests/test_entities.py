import os
import random

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from cave_bat.config import BAT_X, MAX_GAP, MIN_GAP, WINDOW_HEIGHT, WINDOW_WIDTH
from cave_bat.entities import Bat, Obstacle


def setup_module(module: object) -> None:
    pygame.init()


def teardown_module(module: object) -> None:
    pygame.quit()


def test_bat_flap_and_update() -> None:
    random.seed(1)
    bat = Bat(BAT_X, WINDOW_HEIGHT // 2)
    initial_y = bat.y
    bat.flap()
    bat.update(0.016)
    assert bat.y < initial_y  # moved up after flap impulse (negative vy)


def test_obstacle_world_polys_and_offscreen() -> None:
    random.seed(2)
    obs = Obstacle(WINDOW_WIDTH + 10, WINDOW_HEIGHT // 2, (MIN_GAP + MAX_GAP) // 2)
    polys = obs.world_polys()
    assert isinstance(polys, list) and len(polys) >= 2
    # Move obstacle far left
    for _ in range(1000):
        obs.update(0.016)
    assert obs.offscreen() is True
