"""Game entities and rendering helpers.

Contains particle effects, the player-controlled bat, and obstacle generation/drawing.
"""

from __future__ import annotations

import math
import random

import pygame

from .config import (
    BAT_BODY_RADIUS,
    BAT_COLOR,
    BAT_MEMBRANE,
    BAT_RIM,
    BAT_WING_LENGTH,
    BAT_WING_SPAN,
    COL_ROCK_BASE,
    COL_ROCK_SHADE,
    EYE_COLOR,
    FLAP_IMPULSE,
    GRAVITY,
    MAX_FALL_SPEED,
    OBSTACLE_WIDTH,
    PUPIL_COLOR,
    SCROLL_SPEED,
    WATER_COLOR,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    WING_FLAP_AMPLITUDE_DEG,
    WING_FLAP_DURATION,
)
from .utils import circle_polygon_collision, clamp, scale_color


class Particle:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x = random.uniform(0, WINDOW_WIDTH)
        self.y = random.uniform(0, WINDOW_HEIGHT)
        self.vx = -random.uniform(15.0, 40.0)
        self.vy = random.uniform(-6.0, 6.0)
        self.radius = random.uniform(1.0, 2.5)
        self.alpha = random.randint(35, 65)

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -10 or self.y < -20 or self.y > WINDOW_HEIGHT + 20:
            self.reset()
            self.x = WINDOW_WIDTH + random.uniform(0, 120)

    def draw(self, surf: pygame.Surface) -> None:
        color = (200, 200, 220, self.alpha)
        s = pygame.Surface((int(self.radius * 4), int(self.radius * 4)), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (s.get_width() // 2, s.get_height() // 2), int(self.radius))
        surf.blit(s, (int(self.x), int(self.y)), special_flags=pygame.BLEND_PREMULTIPLIED)


class WaterDrop:
    def __init__(self, x: float, y: float) -> None:
        self.x = x + random.uniform(-2.0, 2.0)
        self.y = y
        self.vx = random.uniform(-25.0, 25.0)
        self.vy = random.uniform(40.0, 90.0)
        self.radius = 2.0
        self.alive = True

    def update(self, dt: float, obstacles: list[Obstacle]) -> None:
        if not self.alive:
            return
        self.vy += 1800.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > WINDOW_HEIGHT + 10:
            self.alive = False
            return
        # Die on impact with any spike polygon
        for obs in obstacles:
            for poly in obs.world_polys():
                if circle_polygon_collision(self.x, self.y, self.radius, poly):
                    self.alive = False
                    return

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        s = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(s, (*WATER_COLOR, 180), (4, 4), 2)
        surf.blit(s, (int(self.x) - 4, int(self.y) - 4), special_flags=pygame.BLEND_PREMULTIPLIED)


class Bat:
    def __init__(self, x: int, y: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vy = 0.0
        self.alive = True

        self.wing_timer = 0.0
        self.base_idle_phase = random.random() * math.tau

    def reset(self, x: int, y: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vy = 0.0
        self.alive = True
        self.wing_timer = 0.0

    def flap(self) -> None:
        if not self.alive:
            return
        self.vy = FLAP_IMPULSE
        self.wing_timer = WING_FLAP_DURATION

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.vy = clamp(self.vy + GRAVITY * dt, -9999.0, MAX_FALL_SPEED)
        self.y += self.vy * dt

        if self.wing_timer > 0.0:
            self.wing_timer -= dt

    def get_draw_rotation(self) -> float:
        # Tilt nose up when going up, down when falling
        t = clamp(-self.vy / 700.0, -0.8, 0.6)
        return t * 35.0  # degrees

    def draw(self, surf: pygame.Surface) -> None:
        # Wing angle: quick flap when triggered; subtle idle flutter otherwise
        if self.wing_timer > 0.0:
            phase = 1.0 - (self.wing_timer / WING_FLAP_DURATION)
            wing_angle_deg = WING_FLAP_AMPLITUDE_DEG * math.sin(phase * math.pi)
        else:
            idle = math.sin(pygame.time.get_ticks() * 0.009 + self.base_idle_phase) * 8.0
            wing_angle_deg = idle

        self._draw_bat(surf, (int(self.x), int(self.y)), self.get_draw_rotation(), wing_angle_deg)

    def _draw_bat(
        self,
        surf: pygame.Surface,
        center: tuple[int, int],
        rotation_deg: float,
        wing_angle_deg: float,
    ) -> None:
        cx, cy = center

        # Precompute trigs
        rot_rad = math.radians(rotation_deg)
        cos_r = math.cos(rot_rad)
        sin_r = math.sin(rot_rad)

        def rotate_point(px: float, py: float) -> tuple[int, int]:
            rx = px * cos_r - py * sin_r
            ry = px * sin_r + py * cos_r
            return int(cx + rx), int(cy + ry)

        # Body (circle) and head with subtle rim light
        body_color = BAT_COLOR
        head_radius = int(BAT_BODY_RADIUS * 0.7)

        # Base body
        pygame.draw.circle(surf, body_color, (cx, cy), BAT_BODY_RADIUS)
        head_pos = rotate_point(BAT_BODY_RADIUS + head_radius - 4, 0)
        pygame.draw.circle(surf, body_color, head_pos, head_radius)

        # Rim light along top-left side
        rim_offset = (-4, -4)
        pygame.draw.circle(
            surf,
            BAT_RIM,
            (cx + rim_offset[0], cy + rim_offset[1]),
            BAT_BODY_RADIUS,
            2,
        )
        pygame.draw.circle(
            surf,
            BAT_RIM,
            (head_pos[0] + rim_offset[0], head_pos[1] + rim_offset[1]),
            head_radius,
            2,
        )

        # Ears
        ear_offset = head_radius - 2
        left_ear_base = rotate_point(BAT_BODY_RADIUS + head_radius - 6, -ear_offset)
        right_ear_base = rotate_point(BAT_BODY_RADIUS + head_radius - 6, ear_offset)

        def ear_points(base: tuple[int, int], side: int) -> list[tuple[int, int]]:
            bx, by = base
            tip = rotate_point(BAT_BODY_RADIUS + head_radius + 12, side * (-ear_offset - 10))
            return [base, (bx - 6, by - 6), tip, (bx + 4, by + 2)]

        pygame.draw.polygon(surf, body_color, ear_points(left_ear_base, -1))
        pygame.draw.polygon(surf, body_color, ear_points(right_ear_base, +1))

        # Eyes
        eye_r = max(2, head_radius // 4)
        left_eye = rotate_point(BAT_BODY_RADIUS + head_radius - eye_r - 2, -eye_r)
        right_eye = rotate_point(BAT_BODY_RADIUS + head_radius - eye_r - 2, eye_r)
        pygame.draw.circle(surf, EYE_COLOR, left_eye, eye_r)
        pygame.draw.circle(surf, EYE_COLOR, right_eye, eye_r)
        pygame.draw.circle(surf, PUPIL_COLOR, left_eye, max(1, eye_r // 2))
        pygame.draw.circle(surf, PUPIL_COLOR, right_eye, max(1, eye_r // 2))

        # Wings
        wing_angle_rad = math.radians(wing_angle_deg)

        def wing_points(side: int) -> list[tuple[int, int]]:
            # side: -1 left, +1 right
            base_local = (0, side * (BAT_BODY_RADIUS - 6))
            span = BAT_WING_SPAN
            length = BAT_WING_LENGTH

            # Apply wing flap angle around base hinge
            cos_w = math.cos(wing_angle_rad * side)
            sin_w = math.sin(wing_angle_rad * side)

            def local_transform(px: float, py: float) -> tuple[int, int]:
                # wing rotation around base hinge, then body rotation
                # rotate around hinge in wing plane
                wx = (px - base_local[0]) * cos_w - (py - base_local[1]) * sin_w + base_local[0]
                wy = (px - base_local[0]) * sin_w + (py - base_local[1]) * cos_w + base_local[1]
                return rotate_point(wx, wy)

            tip = local_transform(length, side * 0)
            front = local_transform(length * 0.55, side * (span * 0.55))
            back = local_transform(length * 0.55, side * (-span * 0.55))
            base_front = local_transform(-6, side * (span * 0.25))
            base_back = local_transform(-6, side * (-span * 0.25))

            return [base_back, back, tip, front, base_front]

        def draw_wing(side: int) -> None:
            pts = wing_points(side)
            pygame.draw.polygon(surf, BAT_MEMBRANE, pts)
            pygame.draw.lines(surf, BAT_RIM, False, pts, 2)

        draw_wing(-1)
        draw_wing(+1)


class Obstacle:
    def __init__(self, x: int, gap_y: int, gap_h: int) -> None:
        self.x = float(x)
        self.gap_y = gap_y
        self.gap_h = gap_h
        self.passed = False
        self._rng = random.Random(random.randint(0, 10_000_000))
        # Each obstacle is a cluster of organic stalactites and stalagmites.
        # Store a single top and single bottom polygon for clarity and stronger silhouettes.
        self._top_spikes: list[list[tuple[int, int]]] = []
        self._bottom_spikes: list[list[tuple[int, int]]] = []

        # Subtle per-obstacle color variation
        tint = self._rng.uniform(0.9, 1.1)
        self.col_base = scale_color(COL_ROCK_BASE, tint)
        self.col_shade = scale_color(COL_ROCK_SHADE, tint * 0.98)

        self._build_spikes()

    @property
    def top_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), 0, OBSTACLE_WIDTH, max(0, self.gap_y))

    @property
    def bottom_rect(self) -> pygame.Rect:
        bottom_top = self.gap_y + self.gap_h
        return pygame.Rect(int(self.x), bottom_top, OBSTACLE_WIDTH, WINDOW_HEIGHT - bottom_top)

    def update(self, dt: float) -> None:
        self.x -= SCROLL_SPEED * dt

    def offscreen(self) -> bool:
        return self.x + OBSTACLE_WIDTH < -20

    def _organic_spike(
        self, tip_x: int, tip_y: int, base_y: int, base_width: int, downward: bool
    ) -> list[tuple[int, int]]:
        # Build a tapered polygon with slight waviness on sides
        # Ordered counter-clockwise to avoid self-intersection
        rng = self._rng
        half = base_width // 2
        left_base_x = max(0, tip_x - half)
        right_base_x = min(OBSTACLE_WIDTH, tip_x + half)

        side_segments = 5
        left_path: list[tuple[int, int]] = []  # from base to tip
        right_path: list[tuple[int, int]] = []  # from base to tip
        for i in range(side_segments + 1):
            t = i / side_segments
            y = int((1 - t) * base_y + t * tip_y)
            bulge = int(math.sin(t * math.pi) * rng.randint(2, 6))
            left_x = int((1 - t) * left_base_x + t * (tip_x - 1)) - bulge
            right_x = int((1 - t) * right_base_x + t * (tip_x + 1)) + bulge
            left_path.append((left_x, y))
            right_path.append((right_x, y))

        if downward:
            # Ceiling: start at left base, go up left side to tip,
            # then down right side to right base
            poly = [left_path[0]] + left_path[1:] + list(reversed(right_path[1:])) + [right_path[0]]
        else:
            # Floor: start at left base (bottom), go up along left to tip,
            # then back along right to base
            poly = [left_path[0]] + left_path[1:] + list(reversed(right_path[1:])) + [right_path[0]]
        return poly

    def _build_spikes(self) -> None:
        rng = self._rng
        # One stalactite with strong variation (much wider base)
        tip_x = rng.randint(16, OBSTACLE_WIDTH - 16)
        tip_y = self.gap_y + rng.randint(8, 52)
        base_width = rng.randint(int(OBSTACLE_WIDTH * 0.6), int(OBSTACLE_WIDTH * 0.9))
        self._top_spikes.append(self._organic_spike(tip_x, tip_y, 0, base_width, downward=True))

        # One stalagmite with strong variation (much wider base)
        bottom_top = self.gap_y + self.gap_h
        tip_x = rng.randint(16, OBSTACLE_WIDTH - 16)
        tip_y = bottom_top - rng.randint(8, 52)
        base_width = rng.randint(int(OBSTACLE_WIDTH * 0.6), int(OBSTACLE_WIDTH * 0.9))
        self._bottom_spikes.append(
            self._organic_spike(
                tip_x,
                tip_y,
                WINDOW_HEIGHT,
                base_width,
                downward=False,
            )
        )

    def draw(self, surf: pygame.Surface) -> None:
        ox = int(self.x)

        def offset_poly(poly: list[tuple[int, int]]) -> list[tuple[int, int]]:
            return [(ox + px, py) for (px, py) in poly]

        def draw_spike(poly: list[tuple[int, int]]) -> None:
            world_poly = offset_poly(poly)
            # Base fill
            pygame.draw.polygon(surf, self.col_base, world_poly)
            # Outline only (no bright side highlight)
            pygame.draw.lines(surf, self.col_shade, True, world_poly, 2)

        for sp in self._top_spikes:
            draw_spike(sp)
        for sp in self._bottom_spikes:
            draw_spike(sp)

    def world_polys(self) -> list[list[tuple[int, int]]]:
        ox = int(self.x)

        def offset_poly(poly: list[tuple[int, int]]) -> list[tuple[int, int]]:
            return [(ox + px, py) for (px, py) in poly]

        return [offset_poly(p) for p in (self._top_spikes + self._bottom_spikes)]

    def get_top_tip_world(self) -> tuple[int, int] | None:
        if not self._top_spikes:
            return None
        # Tip is highest y on top polygon path near center
        poly = self._top_spikes[0]
        # Convert to world
        ox = int(self.x)
        world = [(ox + px, py) for (px, py) in poly]
        # Find minimal y point
        tip = min(world, key=lambda p: p[1])
        return tip
