"""Game loop, scene management, and rendering composition for Cave Bat."""

from __future__ import annotations

import math
import random
import sys

import pygame

from .config import (
    BAT_BODY_RADIUS,
    BAT_X,
    FORWARD_DRAG,
    FORWARD_THRUST,
    COL_BG_BOTTOM,
    COL_BG_TOP,
    COL_LAYER_1,
    COL_LAYER_2,
    COL_LAYER_3,
    FPS,
    MARGIN_TOP_BOTTOM,
    MAX_GAP,
    MIN_GAP,
    OBSTACLE_SPACING,
    OBSTACLE_WIDTH,
    SCROLL_SPEED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .entities import Bat, Obstacle, WaterDrop, BloodDrop, BatPart
from .utils import circle_polygon_collision


class Game:
    """Top-level game controller: manages state, input, update, and draw."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.DOUBLEBUF)
        pygame.display.set_caption("Cave Bat")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont(None, 64)
        self.font_small = pygame.font.SysFont(None, 28)
        self._make_overlays()
        self._build_parallax()
        self.drops: list[WaterDrop] = []
        self.blood: list[BloodDrop] = []
        self.bat_parts: list[BatPart] = []

        # Precompute gradient background
        self.bg_gradient = self._generate_gradient_surface()

        self.reset()

    def _make_overlays(self) -> None:
        # Vignette low-res then scale (loop for compatibility)
        small_w, small_h = 320, int(320 * WINDOW_HEIGHT / WINDOW_WIDTH)
        s = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        cx, cy = small_w / 2.0, small_h / 2.0
        max_d = math.hypot(cx, cy)
        for y in range(small_h):
            for x in range(small_w):
                d = math.hypot(x - cx, y - cy) / max_d
                alpha = int(max(0, min(220, (d - 0.55) * 255 / (1.0 - 0.55))))
                s.set_at((x, y), (0, 0, 0, alpha))
        self.vignette = pygame.transform.smoothscale(s, (WINDOW_WIDTH, WINDOW_HEIGHT))

        # Procedural rock texture overlay (multiplies colors to add cavernous variation)
        self.rock_mult = self._generate_rock_texture()

        # Soft drifting mist to add humidity and depth
        self.mist_tex = self._generate_mist_texture()

    def _generate_gradient_surface(self) -> pygame.Surface:
        """Precompute vertical gradient as a surface for fast blitting."""
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Use loop for compatibility if surfarray issues
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            r = int(COL_BG_TOP[0] * (1 - t) + COL_BG_BOTTOM[0] * t)
            g = int(COL_BG_TOP[1] * (1 - t) + COL_BG_BOTTOM[1] * t)
            b = int(COL_BG_TOP[2] * (1 - t) + COL_BG_BOTTOM[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (WINDOW_WIDTH, y))
        return surf

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

    def _generate_rock_texture(self) -> pygame.Surface:
        # Original loop for compatibility
        base_w, base_h = 320, int(320 * WINDOW_HEIGHT / WINDOW_WIDTH)
        tex = pygame.Surface((base_w, base_h))

        # Multi-frequency trigonometric noise for striated rocky appearance
        for y in range(base_h):
            for x in range(base_w):
                xf = x / base_w
                yf = y / base_h
                v = 0.0
                v += math.sin(xf * 21.0 + math.sin(yf * 7.0)) * 0.45
                v += math.sin(yf * 17.0 + math.sin(xf * 9.0 + 1.7)) * 0.35
                v += math.sin((xf + yf) * 13.0) * 0.20
                # Ridge the noise (rocks have creases)
                v = abs(v)
                # Map to [0..1]
                v = max(0.0, min(1.0, v))
                # Convert to a gentle darkening multiplier around 220..255
                c = int(230 - 40 * v)
                tex.set_at((x, y), (c, c, c))

        rock_mult = pygame.transform.smoothscale(tex, (WINDOW_WIDTH, WINDOW_HEIGHT))
        return rock_mult

    def _generate_mist_texture(self) -> pygame.Surface:
        # Original loop for compatibility
        w, h = 320, int(320 * WINDOW_HEIGHT / WINDOW_WIDTH)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                xf = x / w
                yf = y / h
                v = 0.0
                v += math.sin((xf * 6.0) + math.sin(yf * 2.0)) * 0.6
                v += math.sin((yf * 4.0) + math.sin(xf * 3.0 + 1.3)) * 0.4
                v = (v + 2.0) / 4.0  # map roughly to [0..1]
                # Fade mist near screen top to suggest warmer air near ceiling is clearer
                fade = min(1.0, max(0.0, (yf * 1.2)))
                a = int(0 + 28 * v * fade)
                s.set_at((x, y), (180, 188, 200, a))
        return pygame.transform.smoothscale(s, (WINDOW_WIDTH, WINDOW_HEIGHT))

    def reset(self) -> None:
        self.bat = Bat(BAT_X, WINDOW_HEIGHT // 2)
        self.obstacles: list[Obstacle] = []
        self.spawn_timer = 0.0
        self.score = 0
        self.best = 0
        self.game_over = False
        self.time_accum = 0.0
        # Bat-driven forward motion state
        self.forward_speed = SCROLL_SPEED * 0.0  # start stationary
        self.scroll_offset = 0.0

        # Pre-warm obstacles so cave is visible immediately
        x = WINDOW_WIDTH + 200
        for _ in range(6):
            gap_h = random.randint(MIN_GAP, MAX_GAP)
            gap_y = random.randint(MARGIN_TOP_BOTTOM, WINDOW_HEIGHT - MARGIN_TOP_BOTTOM - gap_h)
            self.obstacles.append(Obstacle(x, gap_y, gap_h))
            x += OBSTACLE_SPACING
        self.drops.clear()
        self.blood.clear()
        self.bat_parts.clear()

    def spawn_obstacle(self) -> None:
        gap_h = random.randint(MIN_GAP, MAX_GAP)
        gap_y = random.randint(MARGIN_TOP_BOTTOM, WINDOW_HEIGHT - MARGIN_TOP_BOTTOM - gap_h)
        x = WINDOW_WIDTH + 80
        self.obstacles.append(Obstacle(x, gap_y, gap_h))

    def update(self, dt: float) -> None:
        # Continuous time accumulator for background effects
        self.time_accum += dt
        if not self.game_over:
            self.bat.update(dt)

            # Update forward speed: apply drag each frame
            self.forward_speed -= self.forward_speed * FORWARD_DRAG * dt
            # Clamp more aggressively
            self.forward_speed = max(0.0, min(self.forward_speed, FORWARD_THRUST + SCROLL_SPEED))
            # Integrate scroll offset based on current forward speed
            self.scroll_offset += self.forward_speed * dt

            # Spawn obstacles
            # Spawn spacing depends on forward speed; if very slow, don't jam spawn
            spacing = max(OBSTACLE_SPACING * 0.8, OBSTACLE_SPACING * min(1.5, (self.forward_speed + 1.0) / (SCROLL_SPEED + 1.0)))
            if len(self.obstacles) == 0 or (self.obstacles[-1].x < WINDOW_WIDTH - spacing):
                self.spawn_obstacle()

            # Update obstacles and scoring
            for obs in self.obstacles:
                obs.update(dt, scroll_speed=self.forward_speed)
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

            # Collisions with obstacles (with distance culling)
            bat_r = BAT_BODY_RADIUS
            bat_cx = self.bat.x
            bat_cy = self.bat.y
            cull_dist = 200.0  # Skip if obstacle is farther than this
            for obs in self.obstacles:
                if abs(obs.x + OBSTACLE_WIDTH / 2 - bat_cx) > cull_dist:  # Center distance
                    continue
                # Precise circle-polygon collision against each spike poly
                collided = False
                for poly in obs.world_polys():
                    if circle_polygon_collision(bat_cx, bat_cy, bat_r, poly):
                        collided = True
                        break
                if collided:
                    # Spawn blood only if near a tip (stalactite or stalagmite)
                    tip_candidates: list[tuple[int, int]] = []
                    top_tip = obs.get_top_tip_world()
                    if top_tip is not None:
                        tip_candidates.append(top_tip)
                    bottom_tip = obs.get_bottom_tip_world()
                    if bottom_tip is not None:
                        tip_candidates.append(bottom_tip)
                    # Find closest tip to bat center
                    if tip_candidates:
                        tx, ty = min(
                            tip_candidates,
                            key=lambda p: (p[0] - bat_cx)**2 + (p[1] - bat_cy)**2,
                        )
                        dx = tx - bat_cx
                        dy = ty - bat_cy
                        dist2 = dx * dx + dy * dy
                        if dist2 <= (bat_r + 10)**2:
                            # Spawn a burst of blood droplets at the tip
                            for _ in range(22):
                                self.blood.append(BloodDrop(tx, ty))
                    self.trigger_game_over()
                    break

        # Update water drops (with early culling)
        alive_drops: list[WaterDrop] = []
        for d in self.drops:
            if d.x < -50 or d.x > WINDOW_WIDTH + 50:
                d.alive = False
                continue
            d.update(dt, self.obstacles, scroll_speed=self.forward_speed)
            if d.alive:
                alive_drops.append(d)
        self.drops = alive_drops

        # Update blood drops (with early culling)
        alive_blood: list[BloodDrop] = []
        for b in self.blood:
            if b.x < -50 or b.x > WINDOW_WIDTH + 50:
                b.alive = False
                continue
            b.update(dt, self.obstacles, scroll_speed=self.forward_speed)
            if b.alive:
                alive_blood.append(b)
        self.blood = alive_blood

        # Update bat parts (with early culling)
        alive_parts: list[BatPart] = []
        for p in self.bat_parts:
            if p.x < -60 or p.x > WINDOW_WIDTH + 60 or p.y > WINDOW_HEIGHT + 30:
                p.alive = False
                continue
            p.update(dt, scroll_speed=self.forward_speed)
            if p.alive:
                alive_parts.append(p)
                # Spawn a small trail of blood from falling parts
                if random.random() < 4.0 * dt:  # Approx 4 drips/sec/part
                    self.blood.append(BloodDrop(p.x, p.y))
        self.bat_parts = alive_parts

    def trigger_game_over(self) -> None:
        if not self.game_over:
            self.game_over = True
            self.bat.alive = False
            self.best = max(self.best, self.score)
            # Spawn bat parts exactly once on death
            self.bat_parts = self.bat.break_apart()

    def perform_flap(self) -> None:
        """Perform a flap: update bat velocity and add forward thrust."""
        self.bat.flap()
        self.forward_speed += FORWARD_THRUST

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.game_over:
                    self.reset()
                else:
                    self.perform_flap()
            elif event.key in (pygame.K_r,):
                self.reset()
            elif event.key in (pygame.K_ESCAPE,):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.game_over:
                    self.reset()
                else:
                    self.perform_flap()

    def draw_background(self, surf: pygame.Surface) -> None:
        # Use precomputed gradient
        surf.blit(self.bg_gradient, (0, 0))

        # Parallax paper-cut cave silhouettes (continuous ridge, no striping)
        for color, speed, amp, freq, base_top, base_bot, step, phase in self.layers:
            motion = self.scroll_offset * speed
            # Top ridge
            points_top: list[tuple[int, int]] = [(0, 0)]
            x = 0
            while x <= WINDOW_WIDTH:
                y_top = base_top + int(math.sin((x + motion) * freq + phase) * amp)
                points_top.append((x, y_top))
                x += step
            points_top.append((WINDOW_WIDTH, 0))
            pygame.draw.polygon(surf, color, points_top)

            # Bottom ridge
            points_bottom: list[tuple[int, int]] = [(0, WINDOW_HEIGHT)]
            x = 0
            while x <= WINDOW_WIDTH:
                y_bot = base_bot + int(math.sin((x + 300 + motion) * freq + phase) * amp)
                points_bottom.append((x, y_bot))
                x += step
            points_bottom.append((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.draw.polygon(surf, color, points_bottom)

        # Apply rock texture multiplier for cavern feel
        surf.blit(self.rock_mult, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # Add subtle drifting mist (two layers for variation)
        ox = int(-(self.scroll_offset * 0.15)) % self.mist_tex.get_width()
        oy = int(math.sin(self.time_accum * 0.23) * 8)
        # Tile horizontally to cover screen
        for layer in (0.0, 0.35):
            layer_ox = (ox + int(layer * 200)) % self.mist_tex.get_width()
            dest1 = (-layer_ox, oy)
            dest2 = (self.mist_tex.get_width() - layer_ox, oy)
            surf.blit(self.mist_tex, dest1)
            surf.blit(self.mist_tex, dest2)

    def draw(self) -> None:
        self.draw_background(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        for d in self.drops:
            d.draw(self.screen)
        # If the bat has broken apart, draw the falling pieces.
        if self.bat_parts:
            for p in self.bat_parts:
                p.draw(self.screen)
        # Otherwise, draw the main bat only if it is alive.
        elif self.bat.alive:
            self.bat.draw(self.screen)
        for b in self.blood:
            b.draw(self.screen)
        # Vignette overlay
        self.screen.blit(self.vignette, (0, 0))
        self._draw_ui(self.screen)
        pygame.display.flip()

    def _draw_ui(self, surf: pygame.Surface) -> None:
        score_text = self.font_big.render(str(self.score), True, (230, 230, 230))
        surf.blit(score_text, score_text.get_rect(midtop=(WINDOW_WIDTH // 2, 20)))

        help_text = self.font_small.render(
            "Space or Left Click to flap • R to restart • Esc to quit",
            True,
            (180, 180, 190),
        )
        surf.blit(help_text, help_text.get_rect(midbottom=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 12)))

        if self.game_over:
            title = self.font_big.render("Game Over", True, (250, 230, 230))
            retry = self.font_small.render("Press Space/Click to play again", True, (210, 210, 220))
            best = self.font_small.render(f"Best: {self.best}", True, (200, 200, 210))
            surf.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))
            surf.blit(retry, retry.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10)))
            surf.blit(best, best.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 44)))

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self.handle_input(event)

            # Update scene
            self.update(dt)
            self.draw()


def main() -> None:
    Game().run()