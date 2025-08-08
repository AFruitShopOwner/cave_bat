from __future__ import annotations

"""Game configuration constants for Cave Bat."""

# Game configuration
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

# Physics
GRAVITY = 1800.0  # px/s^2
FLAP_IMPULSE = -600.0  # px/s
MAX_FALL_SPEED = 1200.0  # px/s

# Obstacles
SCROLL_SPEED = 280.0  # px/s (legacy default; dynamic speed can override at runtime)
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
COL_ROCK_BASE = (74, 76, 92)  # bluish limestone base
COL_ROCK_SHADE = (58, 60, 78)  # occluded shade
COL_ROCK_EDGE = (150, 150, 180)  # cool chalky highlight
WATER_COLOR = (130, 180, 255)
BLOOD_COLOR = (200, 30, 40)

BAT_COLOR = (24, 24, 28)
BAT_RIM = (120, 115, 160)
BAT_MEMBRANE = (30, 30, 36)
# New bat materials for richer rendering
BAT_FUR = (28, 28, 34)
BAT_FUR_DARK = (18, 18, 22)
BAT_MEMBRANE_LIGHT = (44, 44, 52)
BAT_INNER_EAR = (90, 70, 110)
BAT_NOSE = (70, 60, 80)
BAT_FANG = (230, 230, 235)
EYE_COLOR = (220, 220, 230)
PUPIL_COLOR = (28, 28, 32)
EYE_LID_COLOR = (40, 40, 46)

# Wing animation
# Longer duration for a slower, more graceful flap
WING_FLAP_DURATION = 0.45  # seconds per triggered flap
WING_FLAP_AMPLITUDE_DEG = 64.0

# Forward motion (environment scroll) driven by bat flaps
# Thrust increases forward speed on each flap; speed decays via drag when idle
FORWARD_THRUST = 260.0  # instantaneous speed added on flap (px/s)
MAX_FORWARD_SPEED = 360.0  # clamp for comfort
FORWARD_DRAG = 1.6  # per-second proportional drag coefficient
