import math
import random
import sys
from typing import List, Tuple

import pygame


# Game configuration
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

# Physics
GRAVITY = 1800.0  # px/s^2
FLAP_IMPULSE = -600.0  # px/s
MAX_FALL_SPEED = 1200.0  # px/s

# Obstacles
SCROLL_SPEED = 280.0  # px/s
OBSTACLE_SPACING = 360  # px between obstacles
OBSTACLE_WIDTH = 120
MIN_GAP = 210
MAX_GAP = 290
MARGIN_TOP_BOTTOM = 96

# Bat
BAT_X = int(WINDOW_WIDTH * 0.28)
BAT_BODY_RADIUS = 24
BAT_WING_SPAN = 72
BAT_WING_LENGTH = 48

# Palette (moody paper-cut silhouettes)
COL_BG_TOP = (9, 11, 20)
COL_BG_BOTTOM = (15, 17, 28)
COL_LAYER_1 = (22, 24, 36)
COL_LAYER_2 = (29, 31, 44)
COL_LAYER_3 = (36, 38, 52)
COL_ROCK_BASE = (74, 76, 92)      # bluish limestone base
COL_ROCK_SHADE = (58, 60, 78)     # occluded shade
COL_ROCK_EDGE = (150, 150, 180)   # cool chalky highlight
WATER_COLOR = (130, 180, 255)

BAT_COLOR = (24, 24, 28)
BAT_RIM = (120, 115, 160)
BAT_MEMBRANE = (30, 30, 36)
EYE_COLOR = (220, 220, 230)
PUPIL_COLOR = (28, 28, 32)

# Wing animation
WING_FLAP_DURATION = 0.23  # seconds per triggered flap
WING_FLAP_AMPLITUDE_DEG = 45.0


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

    def update(self, dt: float, obstacles: List["Obstacle"]) -> None:
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


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def circle_rect_collision(cx: float, cy: float, r: float, rect: pygame.Rect) -> bool:
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) <= r * r


def distance_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def point_in_polygon(px: float, py: float, poly: List[Tuple[float, float]]) -> bool:
    # Ray casting
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > py) != (y2 > py)):
            x_at_y = x1 + (py - y1) * (x2 - x1) / (y2 - y1 + 1e-9)
            if x_at_y > px:
                inside = not inside
    return inside


def circle_polygon_collision(cx: float, cy: float, r: float, poly: List[Tuple[float, float]]) -> bool:
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


def scale_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    r, g, b = color
    return (int(clamp(r * factor, 0, 255)), int(clamp(g * factor, 0, 255)), int(clamp(b * factor, 0, 255)))


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
        center: Tuple[int, int],
        rotation_deg: float,
        wing_angle_deg: float,
    ) -> None:
        cx, cy = center

        # Precompute trigs
        rot_rad = math.radians(rotation_deg)
        cos_r = math.cos(rot_rad)
        sin_r = math.sin(rot_rad)

        def rotate_point(px: float, py: float) -> Tuple[int, int]:
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
        pygame.draw.circle(surf, BAT_RIM, (cx + rim_offset[0], cy + rim_offset[1]), BAT_BODY_RADIUS, 2)
        pygame.draw.circle(surf, BAT_RIM, (head_pos[0] + rim_offset[0], head_pos[1] + rim_offset[1]), head_radius, 2)

        # Ears
        ear_offset = head_radius - 2
        left_ear_base = rotate_point(BAT_BODY_RADIUS + head_radius - 6, -ear_offset)
        right_ear_base = rotate_point(BAT_BODY_RADIUS + head_radius - 6, ear_offset)
        def ear_points(base: Tuple[int, int], side: int) -> List[Tuple[int, int]]:
            bx, by = base
            tip = rotate_point(BAT_BODY_RADIUS + head_radius + 12, side * ( -ear_offset - 10))
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

        def wing_points(side: int) -> List[Tuple[int, int]]:
            # side: -1 left, +1 right
            base_local = (0, side * (BAT_BODY_RADIUS - 6))
            span = BAT_WING_SPAN
            length = BAT_WING_LENGTH

            # Apply wing flap angle around base hinge
            cos_w = math.cos(wing_angle_rad * side)
            sin_w = math.sin(wing_angle_rad * side)

            def local_transform(px: float, py: float) -> Tuple[int, int]:
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
    def __init__(self, x: int, gap_y: int, gap_h: int):
        self.x = float(x)
        self.gap_y = gap_y
        self.gap_h = gap_h
        self.passed = False
        self._rng = random.Random(random.randint(0, 10_000_000))
        # Each obstacle is a cluster of organic stalactites and stalagmites.
        # Store a single top and single bottom polygon for clarity and stronger silhouettes.
        self._top_spikes: List[List[Tuple[int, int]]] = []
        self._bottom_spikes: List[List[Tuple[int, int]]] = []

        # Subtle per-obstacle color variation
        tint = self._rng.uniform(0.9, 1.1)
        self.col_base = scale_color(COL_ROCK_BASE, tint)
        self.col_shade = scale_color(COL_ROCK_SHADE, tint * 0.98)
        self.col_edge = scale_color(COL_ROCK_EDGE, clamp(tint * 1.03, 0.0, 2.0))

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

    def _organic_spike(self, tip_x: int, tip_y: int, base_y: int, base_width: int, downward: bool) -> List[Tuple[int, int]]:
        # Build a tapered polygon with slight waviness on sides (ordered CCW to avoid self-intersection)
        rng = self._rng
        half = base_width // 2
        left_base_x = max(0, tip_x - half)
        right_base_x = min(OBSTACLE_WIDTH, tip_x + half)

        side_segments = 5
        left_path: List[Tuple[int, int]] = []  # from base to tip
        right_path: List[Tuple[int, int]] = [] # from base to tip
        for i in range(side_segments + 1):
            t = i / side_segments
            y = int((1 - t) * base_y + t * tip_y)
            bulge = int(math.sin(t * math.pi) * rng.randint(2, 6))
            left_x = int((1 - t) * left_base_x + t * (tip_x - 1)) - bulge
            right_x = int((1 - t) * right_base_x + t * (tip_x + 1)) + bulge
            left_path.append((left_x, y))
            right_path.append((right_x, y))

        if downward:
            # Ceiling: start at left base, go up left side to tip, then down right side to right base
            poly = [left_path[0]] + left_path[1:] + list(reversed(right_path[1:])) + [right_path[0]]
        else:
            # Floor: start at left base (bottom), go up along left to tip, then back along right to base
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
        self._bottom_spikes.append(self._organic_spike(tip_x, tip_y, WINDOW_HEIGHT, base_width, downward=False))

    def draw(self, surf: pygame.Surface) -> None:
        ox = int(self.x)
        def offset_poly(poly: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
            return [(ox + px, py) for (px, py) in poly]

        def draw_spike(poly: List[Tuple[int, int]]) -> None:
            world_poly = offset_poly(poly)
            # Base fill
            pygame.draw.polygon(surf, self.col_base, world_poly)
            # Outline only (no bright side highlight)
            pygame.draw.lines(surf, self.col_shade, True, world_poly, 2)

        for sp in self._top_spikes:
            draw_spike(sp)
        for sp in self._bottom_spikes:
            draw_spike(sp)

    def world_polys(self) -> List[List[Tuple[int, int]]]:
        ox = int(self.x)
        def offset_poly(poly: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
            return [(ox + px, py) for (px, py) in poly]
        return [offset_poly(p) for p in (self._top_spikes + self._bottom_spikes)]

    def get_top_tip_world(self) -> Tuple[int, int] | None:
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


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cave Bat")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont(None, 64)
        self.font_small = pygame.font.SysFont(None, 28)
        self._make_overlays()
        self._build_parallax()
        self.drops: List[WaterDrop] = []

        self.reset()

    def _make_overlays(self) -> None:
        # Vignette low-res then scale
        small_w, small_h = 320, int(320 * WINDOW_HEIGHT / WINDOW_WIDTH)
        s = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        cx, cy = small_w / 2.0, small_h / 2.0
        max_d = math.hypot(cx, cy)
        for y in range(small_h):
            for x in range(small_w):
                d = math.hypot(x - cx, y - cy) / max_d
                alpha = int(clamp((d - 0.55) * 255 / (1.0 - 0.55), 0, 220))
                s.set_at((x, y), (0, 0, 0, alpha))
        self.vignette = pygame.transform.smoothscale(s, (WINDOW_WIDTH, WINDOW_HEIGHT))

        # Dust particles
        self.particles: List[Particle] = [Particle() for _ in range(28)]

    def _build_parallax(self) -> None:
        # Describe layered ridge parameters for runtime generation (continuous silhouettes)
        random_seed = 1337
        # Each layer: (color, speed, amp, freq, base_top, base_bot, step, phase)
        specs = [
            (COL_LAYER_3, 0.28, 30, 0.018, 70, WINDOW_HEIGHT - 70, 18),
            (COL_LAYER_2, 0.44, 40, 0.022, 60, WINDOW_HEIGHT - 60, 16),
            (COL_LAYER_1, 0.64, 55, 0.026, 50, WINDOW_HEIGHT - 50, 14),
        ]
        self.layers = []
        for idx, (color, speed, amp, freq, base_top, base_bot, step) in enumerate(specs):
            rng = random.Random(random_seed + idx * 999)
            phase = rng.random() * 1000.0
            self.layers.append((color, speed, amp, freq, base_top, base_bot, step, phase))

    def reset(self) -> None:
        self.bat = Bat(BAT_X, WINDOW_HEIGHT // 2)
        self.obstacles: List[Obstacle] = []
        self.spawn_timer = 0.0
        self.score = 0
        self.best = 0
        self.game_over = False

        # Pre-warm obstacles so cave is visible immediately
        x = WINDOW_WIDTH + 200
        for _ in range(6):
            gap_h = random.randint(MIN_GAP, MAX_GAP)
            gap_y = random.randint(MARGIN_TOP_BOTTOM, WINDOW_HEIGHT - MARGIN_TOP_BOTTOM - gap_h)
            self.obstacles.append(Obstacle(x, gap_y, gap_h))
            x += OBSTACLE_SPACING
        self.drops.clear()

    def spawn_obstacle(self) -> None:
        gap_h = random.randint(MIN_GAP, MAX_GAP)
        gap_y = random.randint(MARGIN_TOP_BOTTOM, WINDOW_HEIGHT - MARGIN_TOP_BOTTOM - gap_h)
        x = WINDOW_WIDTH + 80
        self.obstacles.append(Obstacle(x, gap_y, gap_h))

    def update(self, dt: float) -> None:
        if not self.game_over:
            self.bat.update(dt)

            # Spawn obstacles
            if len(self.obstacles) == 0 or (self.obstacles[-1].x < WINDOW_WIDTH - OBSTACLE_SPACING):
                self.spawn_obstacle()

            # Update obstacles and scoring
            for obs in self.obstacles:
                obs.update(dt)
                if not obs.passed and (obs.x + OBSTACLE_WIDTH) < self.bat.x:
                    obs.passed = True
                    self.score += 1
                # Occasionally spawn a dripping water drop from top tip
                if random.random() < 0.003:
                    top_tip = obs.get_top_tip_world()
                    if top_tip is not None:
                        self.drops.append(WaterDrop(top_tip[0], top_tip[1] + 2))

            # Remove offscreen
            self.obstacles = [o for o in self.obstacles if not o.offscreen()]

            # Collisions with cave bounds
            if self.bat.y - BAT_BODY_RADIUS <= 0 or self.bat.y + BAT_BODY_RADIUS >= WINDOW_HEIGHT:
                self.trigger_game_over()
        # Update water drops
        alive_drops: List[WaterDrop] = []
        for d in self.drops:
            d.update(dt, self.obstacles)
            if d.alive:
                alive_drops.append(d)
        self.drops = alive_drops

            # Collisions with obstacles
            bat_r = BAT_BODY_RADIUS
            bat_cx = self.bat.x
            bat_cy = self.bat.y
            for obs in self.obstacles:
                # Precise circle-polygon collision against each spike poly
                collided = False
                for poly in obs.world_polys():
                    if circle_polygon_collision(bat_cx, bat_cy, bat_r, poly):
                        collided = True
                        break
                if collided:
                    self.trigger_game_over()
                    break

    def trigger_game_over(self) -> None:
        if not self.game_over:
            self.game_over = True
            self.bat.alive = False
            self.best = max(self.best, self.score)

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.game_over:
                    self.reset()
                else:
                    self.bat.flap()
            elif event.key in (pygame.K_r,):
                self.reset()
            elif event.key in (pygame.K_ESCAPE,):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.game_over:
                    self.reset()
                else:
                    self.bat.flap()

    def draw_background(self, surf: pygame.Surface) -> None:
        # Vertical gradient
        for y in range(0, WINDOW_HEIGHT, 4):
            t = y / WINDOW_HEIGHT
            r = int(COL_BG_TOP[0] * (1 - t) + COL_BG_BOTTOM[0] * t)
            g = int(COL_BG_TOP[1] * (1 - t) + COL_BG_BOTTOM[1] * t)
            b = int(COL_BG_TOP[2] * (1 - t) + COL_BG_BOTTOM[2] * t)
            pygame.draw.rect(surf, (r, g, b), (0, y, WINDOW_WIDTH, 4))

        # Parallax paper-cut cave silhouettes (continuous ridge, no striping)
        tsec = pygame.time.get_ticks() * 0.001
        for (color, speed, amp, freq, base_top, base_bot, step, phase) in self.layers:
            motion = tsec * SCROLL_SPEED * speed
            # Top ridge
            points_top: List[Tuple[int, int]] = [(0, 0)]
            x = 0
            while x <= WINDOW_WIDTH:
                y_top = base_top + int(math.sin((x + motion) * freq + phase) * amp)
                points_top.append((x, y_top))
                x += step
            points_top.append((WINDOW_WIDTH, 0))
            pygame.draw.polygon(surf, color, points_top)

            # Bottom ridge
            points_bottom: List[Tuple[int, int]] = [(0, WINDOW_HEIGHT)]
            x = 0
            while x <= WINDOW_WIDTH:
                y_bot = base_bot + int(math.sin((x + 300 + motion) * freq + phase) * amp)
                points_bottom.append((x, y_bot))
                x += step
            points_bottom.append((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.draw.polygon(surf, color, points_bottom)

    def draw_ui(self, surf: pygame.Surface) -> None:
        score_text = self.font_big.render(str(self.score), True, (230, 230, 230))
        surf.blit(score_text, score_text.get_rect(midtop=(WINDOW_WIDTH // 2, 20)))

        help_text = self.font_small.render("Space or Left Click to flap • R to restart • Esc to quit", True, (180, 180, 190))
        surf.blit(help_text, help_text.get_rect(midbottom=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 12)))

        if self.game_over:
            title = self.font_big.render("Game Over", True, (250, 230, 230))
            retry = self.font_small.render("Press Space/Click to play again", True, (210, 210, 220))
            best = self.font_small.render(f"Best: {self.best}", True, (200, 200, 210))
            surf.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))
            surf.blit(retry, retry.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10)))
            surf.blit(best, best.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 44)))

    def draw(self) -> None:
        self.draw_background(self.screen)
        # Subtle drifting dust
        for p in self.particles:
            p.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        for d in self.drops:
            d.draw(self.screen)
        self.bat.draw(self.screen)
        # Vignette overlay
        self.screen.blit(self.vignette, (0, 0))
        self.draw_ui(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self.handle_input(event)

            # Update scene
            for p in self.particles:
                p.update(dt)
            self.update(dt)
            self.draw()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()


