import os
import random

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from cave_bat.config import BAT_X, MAX_GAP, MIN_GAP, WINDOW_HEIGHT, WINDOW_WIDTH
from cave_bat.entities import Bat, Obstacle, WaterDrop, BloodDrop, BatPart


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


def test_water_drop_update_and_cull() -> None:
    """Test WaterDrop updates and culls offscreen."""
    random.seed(3)
    drop = WaterDrop(100, 100)
    initial_alive = drop.alive
    drop.x = -60
    drop.update(0.016, [], 0.0)
    assert not drop.alive
    # Onscreen, should stay alive initially
    drop = WaterDrop(WINDOW_WIDTH / 2, 100)
    drop.update(0.016, [], 0.0)
    assert drop.alive


def test_blood_drop_lifetime() -> None:
    """Test BloodDrop fades over lifetime."""
    random.seed(4)
    drop = BloodDrop(100, 100)
    initial_age = drop.age
    drop.update(0.1, [], 0.0)
    assert drop.age > initial_age
    # Fast-forward to death
    drop.age = drop.life + 0.1
    drop.update(0.016, [], 0.0)
    assert not drop.alive


def test_bat_part_cull() -> None:
    """Test BatPart culls offscreen."""
    random.seed(5)
    part = BatPart(100, 100, 0, 0, 0, 0, shape="circle", radius=10)
    part.x = -70
    part.update(0.016, 0.0)
    assert not part.alive
    part = BatPart(WINDOW_WIDTH / 2, 100, 0, 0, 0, 0, shape="circle", radius=10)
    part.y = WINDOW_HEIGHT + 40
    part.update(0.016, 0.0)
    assert not part.alive
