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
    BAT_FUR,
    BAT_FUR_DARK,
    BAT_MEMBRANE,
    BAT_MEMBRANE_LIGHT,
    BAT_INNER_EAR,
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
from .config import BLOOD_COLOR


class Particle:
    """Base class for particles with common physics and culling."""

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.alive = True

    def update_base(
        self, dt: float, scroll_speed: float = 0.0, cull_left: float = -50.0, cull_right: float = None, cull_bottom: float = None
    ) -> None:
        """Common update: apply damping/gravity, integrate, cull offscreen."""
        if not self.alive:
            return
        # Early horizontal cull
        if cull_right is None:
            cull_right = WINDOW_WIDTH + 50
        if self.x < cull_left or self.x > cull_right:
            self.alive = False
            return
        # Default physics (override in subclasses)
        self.vx *= (1.0 - min(0.4, 2.0 * dt))
        self.vy += 2000.0 * dt
        self.x += (self.vx - scroll_speed) * dt
        self.y += self.vy * dt
        # Vertical cull
        if cull_bottom is not None and self.y > cull_bottom:
            self.alive = False


class WaterDrop(Particle):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x + random.uniform(-2.0, 2.0), y, random.uniform(-8.0, 8.0), random.uniform(20.0, 60.0))
        self.radius = 2.0

    def update(self, dt: float, obstacles: list["Obstacle"], scroll_speed: float = 0.0) -> None:
        self.update_base(dt, scroll_speed, cull_bottom=WINDOW_HEIGHT + 10)
        if not self.alive:
            return
        # Specific adjustments
        self.vx *= (1.0 - min(0.6, 3.0 * dt))
        self.vy += 1800.0 * dt
        # Die on impact
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


class BloodDrop(Particle):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x + random.uniform(-1.5, 1.5), y + random.uniform(-1.5, 1.5),
                         random.uniform(-110.0, 140.0), random.uniform(-60.0, 80.0))
        self.radius = random.uniform(1.5, 3.0)
        self.life = random.uniform(0.45, 0.8)
        self.age = 0.0

    def update(self, dt: float, obstacles: list["Obstacle"], scroll_speed: float = 0.0) -> None:
        self.update_base(dt, scroll_speed, cull_bottom=WINDOW_HEIGHT + 10)
        if not self.alive:
            return
        self.age += dt
        if self.age >= self.life:
            self.alive = False
            return
        self.vy += 2400.0 * dt
        # Stop when hitting rock
        for obs in obstacles:
            for poly in obs.world_polys():
                if circle_polygon_collision(self.x, self.y, self.radius, poly):
                    self.alive = False
                    return

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        d = int(max(2, self.radius * 2.0))
        s = pygame.Surface((d + 2, d + 2), pygame.SRCALPHA)
        t = 1.0 - (self.age / max(0.0001, self.life))
        a = int(220 * t)
        pygame.draw.circle(s, (*BLOOD_COLOR, a), ((d + 2) // 2, (d + 2) // 2), int(self.radius))
        surf.blit(s, (int(self.x) - (d + 2) // 2, int(self.y) - (d + 2) // 2), special_flags=pygame.BLEND_PREMULTIPLIED)


class BatPart:
    """A detachable bat body part with simple physics and its own renderer."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        angle: float,
        angular_velocity: float,
        *,
        shape: str,
        # For circle
        radius: float | None = None,
        # For ellipse
        width: float | None = None,
        height: float | None = None,
        # For polygon
        local_points: list[tuple[float, float]] | None = None,
        # Optional wing rib targets in local space (drawn from origin)
        rib_targets: list[tuple[float, float]] | None = None,
        fill_color: tuple[int, int, int] = (255, 255, 255),
        outline_color: tuple[int, int, int] | None = None,
        outline_width: int = 1,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.angle = float(angle)
        self.angular_velocity = float(angular_velocity)
        self.shape = shape
        self.radius = radius
        self.width = width
        self.height = height
        self.local_points = local_points or []
        self.rib_targets = rib_targets or []
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.alive = True

    def update(self, dt: float, scroll_speed: float = 0.0) -> None:
        # Use similar base logic
        if not self.alive:
            return
        cull_left = -60
        cull_right = WINDOW_WIDTH + 60
        cull_bottom = WINDOW_HEIGHT + 30
        if self.x < cull_left or self.x > cull_right or self.y > cull_bottom:
            self.alive = False
            return
        # Physics
        self.vx *= (1.0 - min(0.4, 2.0 * dt))
        self.vy += 2000.0 * dt
        self.x += (self.vx - scroll_speed) * dt
        self.y += self.vy * dt
        self.angle += self.angular_velocity * dt

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        if self.shape == "circle" and self.radius is not None:
            pygame.draw.circle(surf, self.fill_color, (int(self.x), int(self.y)), int(self.radius))
            if self.outline_color is not None and self.outline_width > 0:
                pygame.draw.circle(
                    surf, self.outline_color, (int(self.x), int(self.y)), int(self.radius), self.outline_width
                )
            return
        if self.shape == "ellipse" and self.width is not None and self.height is not None:
            # Draw rotated ellipse by rendering to a temp surface
            w, h = int(self.width), int(self.height)
            w = max(2, w)
            h = max(2, h)
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, self.fill_color, pygame.Rect(0, 0, w, h))
            if self.outline_color is not None and self.outline_width > 0:
                pygame.draw.ellipse(s, self.outline_color, pygame.Rect(0, 0, w, h), self.outline_width)
            rot = pygame.transform.rotozoom(s, -math.degrees(self.angle), 1.0)
            r = rot.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(rot, r.topleft)
            return
        if self.shape == "polygon" and self.local_points:
            ca, sa = math.cos(self.angle), math.sin(self.angle)
            pts = [(int(self.x + px * ca - py * sa), int(self.y + px * sa + py * ca)) for (px, py) in self.local_points]
            pygame.draw.polygon(surf, self.fill_color, pts)
            if self.outline_color is not None and self.outline_width > 0:
                pygame.draw.lines(surf, self.outline_color, True, pts, self.outline_width)
            # Optional ribs (e.g., wing struts)
            for (rx, ry) in self.rib_targets:
                x2 = int(self.x + rx * ca - ry * sa)
                y2 = int(self.y + rx * sa + ry * ca)
                pygame.draw.line(surf, BAT_MEMBRANE_LIGHT, (int(self.x), int(self.y)), (x2, y2), 2)
            return


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

    def break_apart(self) -> list[BatPart]:
        """Generate detachable body parts from the current pose.

        Returns a list of BatPart instances that will fall and spin.
        """
        parts: list[BatPart] = []
        cx, cy = float(self.x), float(self.y)
        r = float(BAT_BODY_RADIUS)

        # Body tilt and helper to rotate offsets around bat center
        tilt = clamp(self.vy / 900.0, -0.35, 0.9)
        cos_t, sin_t = math.cos(tilt), math.sin(tilt)

        def rot(x: float, y: float) -> tuple[float, float]:
            rx = cx + (x * cos_t - y * sin_t)
            ry = cy + (x * sin_t + y * cos_t)
            return rx, ry

        # Random helper for velocities
        def rv(a: float, b: float) -> float:
            return random.uniform(a, b)

        # Wings: use same base geometry with current flap angle baked in
        from .config import BAT_WING_LENGTH, BAT_WING_SPAN

        shoulder_x, shoulder_y = rot(r * 0.25, -r * 0.25)
        L = float(BAT_WING_LENGTH)
        S = float(BAT_WING_SPAN)
        base_points = [
            (0.0, 0.0),
            (-1.00 * L, -0.10 * S),
            (-1.10 * L, 0.25 * S),
            (-0.60 * L, 0.55 * S),
            (-0.15 * L, 0.18 * S),
        ]

        def rotate_points(points: list[tuple[float, float]], deg: float) -> list[tuple[float, float]]:
            a = math.radians(deg)
            ca, sa = math.cos(a), math.sin(a)
            return [(px * ca - py * sa, px * sa + py * ca) for (px, py) in points]

        # Far wing (slightly reduced flap)
        far_deg = self._wing_angle_deg * 0.75
        far_pts = rotate_points(base_points, far_deg)
        parts.append(
            BatPart(
                shoulder_x,
                shoulder_y,
                vx=rv(-160, 60),
                vy=rv(-80, 80),
                angle=rv(-0.5, 0.5),
                angular_velocity=rv(-3.0, 3.0),
                shape="polygon",
                local_points=far_pts,
                rib_targets=[far_pts[2], far_pts[3]],
                fill_color=scale_color(BAT_MEMBRANE, 0.8),
                outline_color=BAT_RIM,
                outline_width=1,
            )
        )

        # Near wing (front)
        near_deg = self._wing_angle_deg * 1.0
        near_pts = rotate_points(base_points, near_deg)
        parts.append(
            BatPart(
                shoulder_x,
                shoulder_y,
                vx=rv(40, 180),
                vy=rv(-80, 80),
                angle=rv(-0.5, 0.5),
                angular_velocity=rv(-3.0, 3.0),
                shape="polygon",
                local_points=near_pts,
                rib_targets=[near_pts[2], near_pts[3]],
                fill_color=BAT_MEMBRANE,
                outline_color=BAT_RIM,
                outline_width=2,
            )
        )

        # Body (ellipse)
        body_w = r * 2.0
        body_h = r * 2.2
        parts.append(
            BatPart(
                cx,
                cy,
                vx=rv(-60, 60),
                vy=rv(-40, 60),
                angle=tilt,
                angular_velocity=rv(-1.5, 1.5),
                shape="ellipse",
                width=body_w,
                height=body_h,
                fill_color=BAT_FUR,
                outline_color=BAT_RIM,
                outline_width=2,
            )
        )

        # Head (circle)
        head_r = r * 0.85
        head_cx, head_cy = rot(r * 0.85, -r * 0.15)
        parts.append(
            BatPart(
                head_cx,
                head_cy,
                vx=rv(-80, 80),
                vy=rv(-100, 40),
                angle=0.0,
                angular_velocity=rv(-2.0, 2.0),
                shape="circle",
                radius=head_r,
                fill_color=BAT_FUR,
                outline_color=BAT_RIM,
                outline_width=2,
            )
        )

        # Ears as small triangles; anchor at their centroid
        near_ear_pts_world = [
            rot(r * 0.65, -r * 1.2),
            rot(r * 0.95, -r * 0.5),
            rot(r * 0.35, -r * 0.55),
        ]
        nx = sum(p[0] for p in near_ear_pts_world) / 3.0
        ny = sum(p[1] for p in near_ear_pts_world) / 3.0
        near_local = [(px - nx, py - ny) for (px, py) in near_ear_pts_world]
        parts.append(
            BatPart(
                nx,
                ny,
                vx=rv(20, 120),
                vy=rv(-80, 40),
                angle=0.0,
                angular_velocity=rv(-4.0, 4.0),
                shape="polygon",
                local_points=near_local,
                fill_color=BAT_FUR,
                outline_color=BAT_RIM,
                outline_width=2,
            )
        )

        far_ear_pts_world = [
            rot(r * 0.45, -r * 1.05),
            rot(r * 0.70, -r * 0.55),
            rot(r * 0.25, -r * 0.60),
        ]
        fx = sum(p[0] for p in far_ear_pts_world) / 3.0
        fy = sum(p[1] for p in far_ear_pts_world) / 3.0
        far_local = [(px - fx, py - fy) for (px, py) in far_ear_pts_world]
        parts.append(
            BatPart(
                fx,
                fy,
                vx=rv(-120, -20),
                vy=rv(-80, 40),
                angle=0.0,
                angular_velocity=rv(-4.0, 4.0),
                shape="polygon",
                local_points=far_local,
                fill_color=scale_color(BAT_FUR, 1.0),
                outline_color=BAT_RIM,
                outline_width=1,
            )
        )

        return parts


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

        def draw_spike(poly: list[tuple[int, int]]) -> None:
            from .utils import draw_offset_polygon
            draw_offset_polygon(surf, poly, ox, self.col_base, shade_color=self.col_shade)

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
        # For top stalactite, tip has the largest y (lower on screen)
        poly = self._top_spikes[0]
        # Convert to world
        ox = int(self.x)
        world = [(ox + px, py) for (px, py) in poly]
        tip = max(world, key=lambda p: p[1])
        return tip

    def get_bottom_tip_world(self) -> tuple[int, int] | None:
        if not self._bottom_spikes:
            return None
        poly = self._bottom_spikes[0]
        ox = int(self.x)
        world = [(ox + px, py) for (px, py) in poly]
        # For bottom stalagmite, tip has the smallest y (higher on screen)
        tip = min(world, key=lambda p: p[1])
        return tip
