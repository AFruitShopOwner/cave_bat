import math
import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from cave_bat.utils import (
    circle_polygon_collision,
    clamp,
    distance_point_to_segment,
    point_in_polygon,
)


def test_clamp_basic() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_distance_point_to_segment_endpoints() -> None:
    # segment (0,0)-(10,0)
    assert math.isclose(distance_point_to_segment(0, 0, 0, 0, 10, 0), 0.0)
    assert math.isclose(distance_point_to_segment(10, 0, 0, 0, 10, 0), 0.0)
    assert math.isclose(distance_point_to_segment(5, 5, 0, 0, 10, 0), 5.0)


def test_point_in_polygon() -> None:
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert point_in_polygon(5, 5, square) is True
    assert point_in_polygon(-1, -1, square) is False


def test_circle_polygon_collision() -> None:
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    # center inside
    assert circle_polygon_collision(5, 5, 1, square) is True
    # grazing edge
    assert circle_polygon_collision(11, 5, 1, square) is True
    # outside
    assert circle_polygon_collision(20, 5, 1, square) is False
