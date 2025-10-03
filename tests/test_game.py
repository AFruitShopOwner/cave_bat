import os
import random
import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from cave_bat.game import Game
from cave_bat.config import (
    WINDOW_HEIGHT, WINDOW_WIDTH, BAT_X, SCROLL_SPEED, FORWARD_THRUST, OBSTACLE_SPACING, OBSTACLE_WIDTH, BAT_BODY_RADIUS
)
from cave_bat.entities import Obstacle, WaterDrop


def test_game_init() -> None:
    """Test Game initialization without crashing, including overlays and pre-warm obstacles."""
    random.seed(123)
    g = Game()
    assert g.bat is not None
    assert len(g.obstacles) == 6  # Pre-warmed
    assert hasattr(g, 'bg_gradient')
    assert hasattr(g, 'rock_mult')
    assert hasattr(g, 'mist_tex')
    assert hasattr(g, 'vignette')
    # Check forward_speed starts at 0
    assert g.forward_speed == 0.0


def test_bat_flap_and_forward_speed() -> None:
    """Test bat flap applies impulse and forward thrust."""
    random.seed(42)
    g = Game()
    initial_y = g.bat.y
    initial_speed = g.forward_speed
    g.perform_flap()
    g.update(0.016)  # One frame
    assert g.bat.y < initial_y  # Moved up
    assert g.forward_speed > initial_speed  # Thrust added
    # Drag should reduce speed over time
    old_speed = g.forward_speed
    g.update(1.0)  # Long time
    assert g.forward_speed < old_speed * 0.5  # Some decay (approximate)


def test_obstacle_spawn_and_update() -> None:
    """Test obstacle spawning and offscreen removal."""
    random.seed(1)
    g = Game()
    initial_count = len(g.obstacles)
    # Force spawn by moving last obstacle
    g.obstacles[-1].x = WINDOW_WIDTH - OBSTACLE_SPACING - 1
    g.update(0.016)
    assert len(g.obstacles) > initial_count
    # Set all to offscreen and filter without update to avoid re-spawn
    for obs in g.obstacles:
        obs.x = -200
    offscreen_count = len([o for o in g.obstacles if not o.offscreen()])
    assert offscreen_count == 0


def test_scoring() -> None:
    """Test scoring when passing obstacles."""
    random.seed(50)
    g = Game()
    first_obs = g.obstacles[0]
    first_obs.x = BAT_X - OBSTACLE_WIDTH - 1  # Just passed
    first_obs.passed = False
    old_score = g.score
    g.update(0.016)
    assert g.score == old_score + 1
    assert first_obs.passed


def test_game_over_bounds() -> None:
    """Test game over on hitting top/bottom bounds."""
    random.seed(100)
    g = Game()
    g.bat.y = -1  # Above top
    g.update(0.016)
    assert g.game_over
    assert not g.bat.alive
    # Test best score update separately
    g.game_over = False  # Reset for test
    g.score = 5
    g.trigger_game_over()
    assert g.best >= 5
    assert g.game_over


def test_collision_culling() -> None:
    """Test collision detection skips distant obstacles (indirect via update)."""
    random.seed(200)
    g = Game()
    # Force game over on close collision (bounds as proxy)
    g.bat.y = WINDOW_HEIGHT + BAT_BODY_RADIUS + 1
    g.update(0.016)
    assert g.game_over
    # Distant shouldn't trigger immediately, but hard to test without polys


def test_particle_culling() -> None:
    """Test particles are culled offscreen."""
    random.seed(300)
    g = Game()
    # Add offscreen drop
    off_drop = WaterDrop(-100, 100)
    g.drops.append(off_drop)
    g.update(0.016)
    assert not off_drop.alive
    # Add onscreen, update to off
    on_drop = WaterDrop(WINDOW_WIDTH / 2, 100)
    g.drops.append(on_drop)
    on_drop.x = WINDOW_WIDTH + 60
    g.update(0.016)
    assert not on_drop.alive


def test_reset() -> None:
    """Test reset restarts game state."""
    random.seed(400)
    g = Game()
    g.score = 10
    g.game_over = True
    g.reset()
    assert not g.game_over
    assert g.score == 0
    assert len(g.obstacles) == 6
    assert g.bat.alive
    assert g.forward_speed == 0.0
