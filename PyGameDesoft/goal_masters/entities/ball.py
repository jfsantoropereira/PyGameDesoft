import pygame
import math
import random
# import constants
# from config import config_manager

from .. import constants
from ..config import config_manager

class Ball:
    def __init__(self, initial_position=None):
        self.radius = constants.BALL_RADIUS
        self.world_pos = pygame.math.Vector3(0, 0, 0)
        self.velocity = pygame.math.Vector3(0, 0, 0)
        self.is_kicked = False
        self.is_on_ground = True # Starts on the ground
        self.lateral_acceleration_x = 0.0

        # Knuckleball state
        self.knuckle_acceleration = pygame.math.Vector3(0, 0, 0)
        self.knuckle_change_timer = 0.0
        self.current_knuckle_interval = 0.0 # Stores the randomly chosen interval duration

        # Sprite placeholder (a simple circle)
        # In a real game, this would be an image, and its base size might be in world units or pixels at a reference depth
        self.base_sprite_radius_world_units = self.radius 
        self.color = constants.WHITE

        if initial_position:
            self.world_pos.xyz = initial_position
        else:
            self.spawn()

    def spawn(self):
        """Resets the ball to a random spawn position on the ground."""
        # Get spawn position from config or use defaults if not found
        spawn_x = config_manager.get_setting('spawn_position_x', default=0.0)
        spawn_y = config_manager.get_setting('spawn_position_y', default=30.0)
        # Z position is always based on ball radius to be on the ground
        spawn_z = constants.BALL_REST_Z

        self.world_pos.xyz = (spawn_x, spawn_y, spawn_z)
        self.velocity.xyz = (0, 0, 0)
        self.is_kicked = False
        self.is_on_ground = True
        self.lateral_acceleration_x = 0.0
        # Reset knuckleball state on spawn
        self.knuckle_acceleration.xyz = (0, 0, 0)
        self.knuckle_change_timer = 0.0
        self.current_knuckle_interval = 0.0 # Initialize with 0, will be set on first knuckle effect
        print(f"Ball spawned at {self.world_pos}")

    def kick(self, power_fraction, horizontal_aim_deg, pointer_x_offset, pointer_z_offset):
        """
        Calculates initial velocity and acceleration based on kick parameters.
        pointer_x_offset: Horizontal striking offset on ball front face, right = +, left = −. Range ± r.
        pointer_z_offset: Vertical striking offset, up = +, down = -. Range ± r (used for vertical angle).
        """
        min_strength = config_manager.get_setting('min_kick_strength')
        max_strength = config_manager.get_setting('max_kick_strength')
        max_curve_accel = config_manager.get_setting('max_kick_curve')

        # Clamp power_fraction
        power_fraction = max(0.0, min(1.0, power_fraction))

        # Calculate V_horz (Launch Speed)
        v_horz = min_strength + power_fraction * (max_strength - min_strength)

        # Horizontal Aim Angle (θx)
        # Angle 0 is straight towards -Y. Positive angle rotates clockwise (towards +X).
        theta_x_rad = math.radians(horizontal_aim_deg)

        # Vertical Aim Angle (θz)
        # θz = − pointer_z_offset / r × 45° (clamped)
        # Clamp pointer_z_offset to [-radius, radius]
        clamped_pointer_z_offset = max(-self.radius, min(self.radius, pointer_z_offset))
        vertical_angle_deg = (-clamped_pointer_z_offset / self.radius) * 45.0
        # Clamp vertical angle to avoid extreme trajectories (e.g., straight up/down which tan would dislike)
        # Max 45 deg up, Min -45 deg (can be adjusted)
        clamped_vertical_angle_deg = max(-45.0, min(45.0, vertical_angle_deg)) 
        theta_z_rad = math.radians(clamped_vertical_angle_deg)

        # Velocity Components
        # Vx = V_horz · sin θx
        # Vy = − V_horz · cos θx (negative because +Y is midfield, aim is towards goal in -Y)
        # Vz = V_horz · tan θz
        self.velocity.x = v_horz * math.sin(theta_x_rad)
        self.velocity.y = -v_horz * math.cos(theta_x_rad) 
        self.velocity.z = v_horz * math.tan(theta_z_rad)

        # Curve Dynamics
        # a_x = − (pointer_x_offset / r) × max_kick_curve
        # Clamp pointer_x_offset to [-radius, radius]
        clamped_pointer_x_offset = max(-self.radius, min(self.radius, pointer_x_offset))
        self.lateral_acceleration_x = -(clamped_pointer_x_offset / self.radius) * max_curve_accel
        
        self.is_kicked = True
        self.is_on_ground = False # Ball is now airborne
        # Initialize knuckleball timer and interval on kick, so it's ready if threshold met
        min_interval = config_manager.get_setting('knuckleball_min_change_interval', 0.0)
        max_interval = config_manager.get_setting('knuckleball_max_change_interval', 1.0)
        self.current_knuckle_interval = random.uniform(min_interval, max_interval)
        self.knuckle_change_timer = 0.0 # Start timer
        self.knuckle_acceleration.xyz = (0,0,0) # Ensure no knuckle effect right at kick start unless speed is already high

        print(f"Ball kicked: V={self.velocity}, AimH={horizontal_aim_deg}, AimV={clamped_vertical_angle_deg}, PtrX={pointer_x_offset}, PtrZ={pointer_z_offset}, AccelX={self.lateral_acceleration_x}")


    def update(self, dt):
        if not self.is_kicked:
            return

        # Knuckleball parameters from config
        knuckle_threshold_speed = config_manager.get_setting('knuckleball_threshold_speed', 25.0)
        knuckle_min_accel = config_manager.get_setting('knuckleball_min_acceleration', 0.0)
        knuckle_max_accel = config_manager.get_setting('knuckleball_max_acceleration', 2.0)
        knuckle_min_interval = config_manager.get_setting('knuckleball_min_change_interval', 0.0)
        knuckle_max_interval = config_manager.get_setting('knuckleball_max_change_interval', 1.0)

        current_speed = self.velocity.length()

        if current_speed > knuckle_threshold_speed and self.world_pos.z > self.radius:
            self.knuckle_change_timer += dt
            if self.knuckle_change_timer >= self.current_knuckle_interval:
                self.knuckle_change_timer = 0.0 # Reset timer
                self.current_knuckle_interval = random.uniform(knuckle_min_interval, knuckle_max_interval)
                
                kn_accel_x = random.uniform(knuckle_min_accel, knuckle_max_accel) * random.choice([-1, 1])
                # Knuckle effect on Z could be similar, or perhaps biased if desired (e.g. more often down?)
                # For now, symmetrical like X.
                kn_accel_z = random.uniform(knuckle_min_accel, knuckle_max_accel) * random.choice([-1, 1])
                self.knuckle_acceleration.xyz = (kn_accel_x, 0, kn_accel_z)
        else:
            # If speed drops or ball is on ground, reset knuckle effect
            self.knuckle_acceleration.xyz = (0, 0, 0)
            self.knuckle_change_timer = 0.0 # Reset timer for next potential activation
            # Optionally, could also reset self.current_knuckle_interval here or let it persist

        # Apply gravity and Z-component of knuckleball acceleration
        self.velocity.z += (self.knuckle_acceleration.z - constants.GRAVITY) * dt

        # Apply curve dynamics and X-component of knuckleball acceleration if ball is in the air
        if self.world_pos.z > self.radius: # Apply only while Z > r
            self.velocity.x += (self.lateral_acceleration_x + self.knuckle_acceleration.x) * dt
        else:
            # If it was curving but now on ground, curve effect might stop or change.
            # Knuckle effect is already handled above to stop if on ground or too slow.
            # For MVP, let's assume curve accel stops if Z condition not met.
            pass # lateral_acceleration_x will not be applied if this else branch is taken next tick and world_pos.z <= radius

        # Update position (Y velocity is not affected by curve or knuckle)
        self.world_pos += self.velocity * dt
        
        # Check for ground collision
        if self.world_pos.z <= self.radius and self.velocity.z < 0:
            self.world_pos.z = self.radius
            
            # Get bounce and friction parameters from config
            z_restitution = config_manager.get_setting('ball_bounce_z_restitution', default=0.5)
            xy_retention = config_manager.get_setting('ball_friction_xy_retention', default=0.5)
            
            self.velocity.z *= -z_restitution # Bounce with configured Z restitution
            self.is_on_ground = True
            
            # Apply configured XY friction (speed retention)
            self.velocity.x *= xy_retention 
            self.velocity.y *= xy_retention

            # If vertical bounce is very small, effectively stop vertical motion to prevent micro-bounces
            if abs(self.velocity.z) < 0.1: # Threshold for stopping vertical bounce
                self.velocity.z = 0

            # If overall speed is very low after bounce and friction, consider the ball stopped
            if self.velocity.length_squared() < 0.1: # Threshold for stopping
                 self.is_kicked = False # Ball is no longer considered in active play
                 self.velocity.xyz = (0,0,0) # Come to a full stop
            
            print(f"Ball hit ground at {self.world_pos}, bounced with Vz={self.velocity.z:.2f}")
        elif self.world_pos.z > self.radius:
            self.is_on_ground = False # Explicitly set is_on_ground to false if airborne


    def draw(self, screen, camera):
        # Get screen coordinates and size from camera
        screen_x, screen_y = camera.world_to_screen(self.world_pos.x, self.world_pos.y, self.world_pos.z)
        
        # Base size of the ball is its diameter in world units.
        base_diameter_world = self.radius * 2.0

        scaled_diameter_pixels_w, scaled_diameter_pixels_h = camera.get_sprite_display_size(
            base_diameter_world, 
            base_diameter_world, # Assuming square aspect ratio for the ball sprite
            self.world_pos.x, self.world_pos.y, self.world_pos.z # Pass full world coordinates
        )
        # For a circle, we need radius. 
        # Ensure it's at least 1 pixel.
        display_radius = max(1, int(scaled_diameter_pixels_w / 2))


        # Draw a simple circle as a placeholder sprite
        if display_radius > 0 : # Only draw if visible
            pygame.draw.circle(screen, self.color, (screen_x, screen_y), display_radius)

    def reset(self):
        self.spawn()

# Example usage (for testing, if run standalone with appropriate path adjustments or mocks)
if __name__ == '__main__':
    # This requires pygame and other modules to be available.
    # And constants/config_manager to be importable (e.g. by adjusting PYTHONPATH)
    # Mocking for simple test:
    class MockConstants:
        BALL_RADIUS = 0.11
        BALL_REST_Z = 0.11
        SPAWN_Y_MIN = 16.5
        SPAWN_Y_MAX = 40.0
        GRAVITY = 9.81
        WHITE = (255,255,255)
        CAMERA_POSITION = (0,50,12) # Needed by camera
        SCREEN_WIDTH = 1280 # Needed by camera
        SCREEN_HEIGHT = 720 # Needed by camera

    class MockConfigManager:
        def get_setting(self, key):
            if key == 'min_kick_strength': return 15.0
            if key == 'max_kick_strength': return 35.0
            if key == 'max_kick_curve': return 3.0
            return None
    
    constants = MockConstants()
    config_manager = MockConfigManager()

    # Need to mock camera for draw test or skip draw test
    class MockCamera:
        def __init__(self):
            self.position = constants.CAMERA_POSITION
            self.cam_dist_factor = self.position[1]
            self.PROJECTION_MIN_Y_EPSILON = 0.1
        
        def get_projection_scale(self, world_y):
            effective_world_y = max(world_y, self.PROJECTION_MIN_Y_EPSILON)
            return self.cam_dist_factor / effective_world_y

        def world_to_screen(self, world_x, world_y, world_z):
            scale = self.get_projection_scale(world_y)
            screen_x = constants.SCREEN_WIDTH / 2 + world_x * scale
            screen_y = (constants.SCREEN_HEIGHT / 2) - (world_z - self.position[2]) * scale
            return int(screen_x), int(screen_y)

        def get_sprite_display_size(self, base_w, base_h, world_x, world_y, world_z):
            scale = self.get_projection_scale(world_y)
            dw = base_w * scale
            dh = base_h * scale
            return int(max(1, dw)), int(max(1, dh))

    pygame.init() # Pygame needed for Vector3
    screen = pygame.display.set_mode((100,100)) # Dummy screen for draw
    
    ball = Ball()
    print(f"Initial ball state: pos={ball.world_pos}, vel={ball.velocity}, kicked={ball.is_kicked}")
    
    ball.kick(power_fraction=0.5, horizontal_aim_deg=10, pointer_x_offset=0.05, pointer_z_offset=-0.02)
    print(f"After kick: pos={ball.world_pos}, vel={ball.velocity}, kicked={ball.is_kicked}, ax={ball.lateral_acceleration_x}")

    dt = 0.1 # 100ms
    for i in range(20): # Simulate 2 seconds
        ball.update(dt)
        print(f"Update {i+1}: pos={ball.world_pos}, vel={ball.velocity}, on_ground={ball.is_on_ground}, kicked={ball.is_kicked}")
        if not ball.is_kicked and ball.is_on_ground:
            break
    
    # Test drawing (requires a camera instance)
    mock_camera = MockCamera()
    ball.draw(screen, mock_camera) # This would draw on the dummy screen
    pygame.display.flip() # To see it if running interactively with a visible window
    
    ball.reset()
    print(f"After reset: pos={ball.world_pos}, vel={ball.velocity}, kicked={ball.is_kicked}")
    
    pygame.quit()
