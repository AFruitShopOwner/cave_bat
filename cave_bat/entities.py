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
    BAT_RIM,
    COL_ROCK_BASE,
    COL_ROCK_SHADE,
    FLAP_IMPULSE,
    GRAVITY,
    MAX_FALL_SPEED,
    OBSTACLE_WIDTH,
    SCROLL_SPEED,
    WATER_COLOR,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .utils import circle_polygon_collision, clamp, scale_color


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
        # Animation state
        self._wing_phase = 0.0  # continuous idle flutter phase (radians)
        self._flap_time_left = 0.0  # time remaining in active flap burst
        self._wing_angle_deg = 0.0  # computed per-frame

    def reset(self, x: int, y: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vy = 0.0
        self.alive = True
        self._wing_phase = 0.0
        self._flap_time_left = 0.0
        self._wing_angle_deg = 0.0

    def flap(self) -> None:
        if not self.alive:
            return
        self.vy = FLAP_IMPULSE
        # Trigger a stronger wing flap burst
        from .config import WING_FLAP_DURATION

        self._flap_time_left = max(self._flap_time_left, WING_FLAP_DURATION)

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.vy = clamp(self.vy + GRAVITY * dt, -9999.0, MAX_FALL_SPEED)
        self.y += self.vy * dt
        # Advance idle flutter phase (slower when falling fast)
        speed_factor = 1.0 + clamp(abs(self.vy) / 600.0, 0.0, 0.8)
        # Much slower idle flutter baseline
        self._wing_phase += dt * 2.4 * (0.7 + 0.3 * speed_factor)
        # Decrease active flap timer
        if self._flap_time_left > 0.0:
            self._flap_time_left = max(0.0, self._flap_time_left - dt)
        # Compute wing angle for this frame (idle flutter + active flap burst)
        from .config import WING_FLAP_AMPLITUDE_DEG, WING_FLAP_DURATION

        idle_amp = 12.0  # gentle idle amplitude
        idle = idle_amp * math.sin(self._wing_phase)
        # Smooth flap envelope: sin(pi*t) (starts and ends at 0, peaks at t=0.5)
        if self._flap_time_left > 0.0 and WING_FLAP_DURATION > 0.0:
            t = 1.0 - (self._flap_time_left / WING_FLAP_DURATION)
            t = clamp(t, 0.0, 1.0)
            s = math.sin(math.pi * t)
            burst = WING_FLAP_AMPLITUDE_DEG * s
        else:
            burst = 0.0
        self._wing_angle_deg = idle + burst

    def draw(self, surf: pygame.Surface) -> None:
        # Procedural bat, side view facing right: body, head, ears, one near wing (front), one far wing (back)
        from .config import (
            BAT_FANG,
            BAT_FUR,
            BAT_FUR_DARK,
            BAT_INNER_EAR,
            BAT_MEMBRANE,
            BAT_MEMBRANE_LIGHT,
            BAT_RIM,
            EYE_COLOR,
            PUPIL_COLOR,
            EYE_LID_COLOR,
            BAT_WING_LENGTH,
            BAT_WING_SPAN,
        )

        cx, cy = int(self.x), int(self.y)
        r = BAT_BODY_RADIUS

        # Body tilt based on vertical velocity (like Flappy Bird)
        tilt = clamp(self.vy / 900.0, -0.35, 0.9)  # radians approx
        cos_t, sin_t = math.cos(tilt), math.sin(tilt)

        def rot(x: float, y: float) -> tuple[int, int]:
            rx = cx + int(x * cos_t - y * sin_t)
            ry = cy + int(x * sin_t + y * cos_t)
            return rx, ry

        # Draw wings (side view). Shoulder located slightly forward on body
        def draw_side_wing(shoulder_world: tuple[int, int], near: bool) -> None:
            sx, sy = shoulder_world
            L = float(BAT_WING_LENGTH)
            S = float(BAT_WING_SPAN)
            # Wing defined in local coords with forward = +X (to the right). Membrane extends backward (-X)
            base_points = [
                (0.0, 0.0),  # shoulder
                (-1.00 * L, -0.10 * S),  # top outer tip (aft/up)
                (-1.10 * L, 0.25 * S),  # aft peak
                (-0.60 * L, 0.55 * S),  # inner membrane peak
                (-0.15 * L, 0.18 * S),  # root lower
            ]
            # Wing rotation around shoulder by flap angle (near wing uses full, far wing slightly reduced)
            ang_deg = self._wing_angle_deg * (1.0 if near else 0.75)
            ang = math.radians(ang_deg)
            ca, sa = math.cos(ang), math.sin(ang)

            def rloc(x: float, y: float) -> tuple[int, int]:
                rx = sx + int(x * ca - y * sa)
                ry = sy + int(x * sa + y * ca)
                return rx, ry

            outline = [rloc(x, y) for (x, y) in base_points]
            color = BAT_MEMBRANE if near else scale_color(BAT_MEMBRANE, 0.8)
            pygame.draw.polygon(surf, color, outline)
            pygame.draw.lines(surf, BAT_RIM, True, outline, 2 if near else 1)
            # Ribs
            rib_targets = [base_points[2], base_points[3]]
            for bx, by in rib_targets:
                p0 = rloc(0.0, 0.0)
                p1 = rloc(bx, by)
                pygame.draw.line(surf, BAT_MEMBRANE_LIGHT, p0, p1, 2 if near else 1)

        # Shoulder location relative to body center (slightly forward and up)
        shoulder_world = rot(r * 0.25, -r * 0.25)
        # Far wing first (behind body)
        draw_side_wing(shoulder_world, near=False)

        # Draw body (two-tone fur ellipse with rim light)
        body_rect = pygame.Rect(0, 0, int(r * 2.0), int(r * 2.2))
        body_rect.center = (cx, cy)
        pygame.draw.ellipse(surf, BAT_FUR, body_rect)
        # Lower shadow
        shadow_rect = body_rect.copy()
        shadow_rect.height = int(body_rect.height * 0.55)
        shadow_rect.top = body_rect.centery
        pygame.draw.ellipse(surf, BAT_FUR_DARK, shadow_rect)
        # Rim outline
        pygame.draw.ellipse(surf, BAT_RIM, body_rect, 2)

        # Head (front, facing right)
        head_r = int(r * 0.85)
        head_center = rot(r * 0.85, -r * 0.15)
        pygame.draw.circle(surf, BAT_FUR, head_center, head_r)
        pygame.draw.circle(surf, BAT_RIM, head_center, head_r, 2)

        # Ears (one prominent near ear, one smaller far ear)
        near_ear = [
            rot(r * 0.65, -r * 1.2),
            rot(r * 0.95, -r * 0.5),
            rot(r * 0.35, -r * 0.55),
        ]
        far_ear = [
            rot(r * 0.45, -r * 1.05),
            rot(r * 0.70, -r * 0.55),
            rot(r * 0.25, -r * 0.60),
        ]
        pygame.draw.polygon(surf, BAT_FUR, near_ear)
        pygame.draw.polygon(surf, BAT_FUR, far_ear)
        pygame.draw.polygon(surf, BAT_RIM, near_ear, 2)
        pygame.draw.polygon(surf, BAT_RIM, far_ear, 1)
        # Inner ear on near ear only
        inner_near = [
            rot(r * 0.68, -r * 1.05),
            rot(r * 0.88, -r * 0.62),
            rot(r * 0.52, -r * 0.65),
        ]
        pygame.draw.polygon(surf, BAT_INNER_EAR, inner_near)

        # Single eye (near side)
        eye_pos = rot(r * 0.95, -r * 0.12)
        eye_r = max(2, int(r * 0.22))
        pygame.draw.circle(surf, EYE_COLOR, eye_pos, eye_r)
        # Pupil slight look based on vy
        look = clamp(self.vy / 600.0, -0.6, 0.6)
        pupil_offset = (int(look * eye_r * 0.6), int(eye_r * 0.15))
        pygame.draw.circle(
            surf,
            PUPIL_COLOR,
            (eye_pos[0] + pupil_offset[0], eye_pos[1] + pupil_offset[1]),
            max(1, eye_r // 2),
        )
        # Upper eyelid
        lid_w = int(eye_r * 2.2)
        lid_h = int(eye_r * 0.9)
        pygame.draw.arc(
            surf,
            EYE_LID_COLOR,
            pygame.Rect(eye_pos[0] - lid_w // 2, eye_pos[1] - lid_h, lid_w, lid_h),
            math.pi,
            2 * math.pi,
            2,
        )

        # Simple muzzle/fang near bottom of head
        fang_base = rot(r * 1.05, r * 0.35)
        fang = [
            fang_base,
            rot(r * 1.00, r * 0.55),
            rot(r * 1.12, r * 0.55),
        ]
        pygame.draw.polygon(surf, BAT_FANG, fang)

        # Near wing in front of body
        draw_side_wing(shoulder_world, near=True)


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

    def update(self, dt: float, scroll_speed: float | None = None) -> None:
        speed = SCROLL_SPEED if scroll_speed is None else scroll_speed
        self.x -= speed * dt

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
