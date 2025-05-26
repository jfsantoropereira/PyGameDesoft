# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# Goal dimensions
GOAL_MIN_X = -4.0
GOAL_MAX_X = 4.0
CROSSBAR_Z = 2.5

# Ball properties
BALL_RADIUS = 0.11
BALL_REST_Z = BALL_RADIUS  # Ball rests on the ground, its center is at its radius height
BALL_REFERENCE_PIXEL_DIAMETER = 20 # Example base size in pixels at reference depth

# Spawn area
SPAWN_Y_MIN = 16.5
SPAWN_Y_MAX = 40.0

# Physics
GRAVITY = 9.81

# Input
ARROW_KEY_INCREMENT_DEG = 2.0

# Colors (provisional, can be refined later)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 128, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Camera
CAMERA_POSITION = (0, 80, 30)
CAMERA_LOOK_AT_DIRECTION = (0, -1, 0) # -Y direction

# UI
POWER_BAR_SEGMENTS = 4
