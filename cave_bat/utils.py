"""Geometry and color utility functions used across the game."""

from __future__ import annotations

import math
from typing import Sequence
import numpy as np
import pygame


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a numeric value into the inclusive range [lo, hi]."""
    return max(lo, min(hi, value))


def distance_point_to_segment(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    """Shortest distance from point (px,py) to segment A(ax,ay)-B(bx,by)."""
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def closest_point_on_segment(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> tuple[float, float]:
    """Return the closest point on the segment A(ax,ay)-B(bx,by) to point P(px,py)."""
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0:
        return ax, ay
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx = ax + t * abx
    cy = ay + t * aby
    return cx, cy


def point_in_polygon(px: float, py: float, poly: Sequence[tuple[float, float]]) -> bool:
    """Return True if point (px,py) is inside the simple polygon described by poly."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            x_at_y = x1 + (py - y1) * (x2 - x1) / (y2 - y1 + 1e-9)
            if x_at_y > px:
                inside = not inside
    return inside


def circle_polygon_collision(
    cx: float,
    cy: float,
    r: float,
    poly: Sequence[tuple[float, float]],
) -> bool:
    """True if circle centered at (cx,cy) with radius r intersects polygon poly."""
    if point_in_polygon(cx, cy, poly):
        return True
    # Check edges
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if distance_point_to_segment(cx, cy, x1, y1, x2, y2) <= r:
            return True
    return False


def polygon_closest_point(
    px: float, py: float, poly: Sequence[tuple[float, float]]
) -> tuple[float, float]:
    """Closest point on polygon edges to (px,py)."""
    best: tuple[float, float] | None = None
    best_d2 = float("inf")
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cx, cy = closest_point_on_segment(px, py, x1, y1, x2, y2)
        d2 = (cx - px) * (cx - px) + (cy - py) * (cy - py)
        if d2 < best_d2:
            best_d2 = d2
            best = (cx, cy)
    # Fallback if polygon is degenerate
    return best if best is not None else (px, py)


def scale_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Scale an RGB color by factor, clamped to [0,255]."""
    r, g, b = color
    return (
        int(clamp(r * factor, 0, 255)),
        int(clamp(g * factor, 0, 255)),
        int(clamp(b * factor, 0, 255)),
    )


def procedural_noise_surface(w: int, h: int, noise_func: callable) -> np.ndarray:
    """Generate a noise surface using NumPy meshgrid and a custom noise function.

    Args:
        w, h: Dimensions.
        noise_func: Function taking X, Y meshgrids and returning noise values.

    Returns:
        RGB or RGBA array for surfarray.
    """
    x = np.linspace(0, 1, w, dtype=np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    v = noise_func(X, Y)
    # Default to grayscale; subclasses can extend
    c = np.clip(v * 255, 0, 255).astype(np.uint8)
    return np.stack([c, c, c], axis=-1)


def draw_offset_polygon(
    surf: pygame.Surface,
    poly: list[tuple[int, int]],
    ox: int,
    color: tuple[int, int, int],
    width: int = 0,
    shade_color: tuple[int, int, int] | None = None,
) -> None:
    """Draw a polygon with x-offset, supporting base fill and optional shade outline."""
    world_poly = [(ox + px, py) for (px, py) in poly]
    pygame.draw.polygon(surf, color, world_poly)
    if shade_color:
        pygame.draw.lines(surf, shade_color, True, world_poly, width or 2)
