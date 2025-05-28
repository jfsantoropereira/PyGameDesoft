import pygame
import math
import os
from .. import constants
from ..config import config_manager

class Goalkeeper:
    def __init__(self):
        # Goalkeeper dimensions (2m tall, 1.5m wide)
        self.width = 1.5
        self.height = 2.0
        
        # Position (center of the rectangle)
        self.world_pos = pygame.math.Vector3(0.0, 0.0, 1.0)  # x=0, y=0, z=1 (bottom touches ground)
        
        # Movement properties
        self.velocity_x = 0.0
        self.target_x = 0.0  # Target x position to follow ball
        
        # Visual properties
        self.color = constants.BLUE  # Blue goalkeeper (fallback for rectangle)
        
        # Load goalkeeper sprite
        try:
            sprite_path = os.path.join(os.path.dirname(__file__), "..", "..", "imagens", "Yashin Sprite Request May 28 2025.png")
            self.sprite = pygame.image.load(sprite_path)
            self.has_sprite = True
            print(f"Goalkeeper sprite loaded from: {sprite_path}")
        except Exception as e:
            print(f"Failed to load goalkeeper sprite: {e}")
            self.sprite = None
            self.has_sprite = False
        
        print(f"Goalkeeper spawned at {self.world_pos}")

    def update(self, dt, ball):
        """Update goalkeeper position based on ball location"""
        # Get configuration parameters
        max_speed = config_manager.get_setting('goalkeeper_max_speed', default=5.0)
        max_acceleration = config_manager.get_setting('goalkeeper_max_acceleration', default=8.0)
        
        # Set target x position based on ball's x position if ball is in flight
        if ball.is_kicked and not ball.is_on_ground:
            self.target_x = ball.world_pos.x
        
        # Calculate desired velocity to reach target
        distance_to_target = self.target_x - self.world_pos.x
        desired_velocity = 0.0
        
        if abs(distance_to_target) > 0.01:  # Small threshold to avoid jitter
            # Calculate desired velocity (with speed limit)
            desired_speed = min(abs(distance_to_target) * 5.0, max_speed)  # Proportional with max speed
            desired_velocity = desired_speed if distance_to_target > 0 else -desired_speed
        
        # Apply acceleration limits
        velocity_change = desired_velocity - self.velocity_x
        max_velocity_change = max_acceleration * dt
        
        if abs(velocity_change) > max_velocity_change:
            velocity_change = max_velocity_change if velocity_change > 0 else -max_velocity_change
        
        self.velocity_x += velocity_change
        
        # Update position
        self.world_pos.x += self.velocity_x * dt
        
        # Keep goalkeeper within reasonable bounds (goal area)
        goalkeeper_bounds = 6.0  # Allow some movement beyond goal posts
        self.world_pos.x = max(-goalkeeper_bounds, min(goalkeeper_bounds, self.world_pos.x))

    def check_save(self, ball):
        """Check if goalkeeper saves the ball (ball at y=0 and contacts goalkeeper)"""
        # Check if ball is approaching or at goal line (y <= 0.5 to catch it earlier)
        if ball.world_pos.y <= 0.5 and ball.velocity.y < 0:  # Ball moving towards goal
            # Check if ball is within goalkeeper's reach
            ball_x = ball.world_pos.x
            ball_z = ball.world_pos.z
            
            # Goalkeeper rectangle bounds (add some tolerance for ball radius)
            tolerance = 0.15  # Slightly larger than ball radius for better collision
            left_bound = self.world_pos.x - self.width / 2 - tolerance
            right_bound = self.world_pos.x + self.width / 2 + tolerance
            bottom_bound = self.world_pos.z - self.height / 2 - tolerance
            top_bound = self.world_pos.z + self.height / 2 + tolerance
            
            # Check collision with goalkeeper rectangle
            if (left_bound <= ball_x <= right_bound and 
                bottom_bound <= ball_z <= top_bound):
                return True
        
        return False

    def save_ball(self, ball):
        """Perform a save - reverse ball's y velocity and add some randomness"""
        if ball.velocity.y < 0:  # Only save if ball is moving towards goal
            # Reverse y velocity with some energy loss
            ball.velocity.y = abs(ball.velocity.y) * 0.8
            
            # Add some horizontal deflection based on where ball hit goalkeeper
            contact_offset = ball.world_pos.x - self.world_pos.x
            deflection_strength = 2.0
            ball.velocity.x += contact_offset * deflection_strength
            
            # Slight upward deflection
            ball.velocity.z += 1.0
            
            # Ensure ball doesn't continue past goalkeeper
            if ball.world_pos.y <= 0:
                ball.world_pos.y = 0.1  # Push ball slightly away from goal line
            
            print(f"SAVE! Goalkeeper deflected ball at x={ball.world_pos.x:.2f}")
            return True
        return False

    def draw(self, screen, camera):
        """Draw the goalkeeper as a sprite if available, otherwise as a rectangle"""
        if self.has_sprite and self.sprite:
            # Draw sprite
            # Get the center of the goalkeeper for screen projection
            center_x = self.world_pos.x
            center_y = self.world_pos.y
            center_z = self.world_pos.z  # Center Z position
            
            # Convert center to screen coordinates
            screen_x, screen_y = camera.world_to_screen(center_x, center_y, center_z)

            # Visual scaling to make sprite appear larger without changing hitbox
            visual_scale_factor = 1.25 # Make sprite appear 25% larger
            display_width_world = self.width * visual_scale_factor
            display_height_world = self.height * visual_scale_factor
            
            # Calculate sprite display size using the same method as other game objects
            scaled_width_pixels, scaled_height_pixels = camera.get_sprite_display_size(
                display_width_world,   # Use visually scaled world width
                display_height_world,  # Use visually scaled world height
                center_x,
                center_y,
                center_z
            )
            
            # Scale the sprite to match the goalkeeper's world dimensions
            if scaled_width_pixels > 0 and scaled_height_pixels > 0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_width_pixels), int(scaled_height_pixels)))
                
                # Position the sprite so it's centered on the goalkeeper's world position
                sprite_rect = scaled_sprite.get_rect()
                sprite_rect.center = (screen_x, screen_y)
                
                screen.blit(scaled_sprite, sprite_rect)
        else:
            # Fallback to rectangle drawing (existing code)
            # Get the four corners of the goalkeeper rectangle in world coordinates
            half_width = self.width / 2
            half_height = self.height / 2
            
            # Bottom corners
            bottom_left = (self.world_pos.x - half_width, self.world_pos.y, self.world_pos.z - half_height)
            bottom_right = (self.world_pos.x + half_width, self.world_pos.y, self.world_pos.z - half_height)
            
            # Top corners  
            top_left = (self.world_pos.x - half_width, self.world_pos.y, self.world_pos.z + half_height)
            top_right = (self.world_pos.x + half_width, self.world_pos.y, self.world_pos.z + half_height)
            
            # Convert to screen coordinates
            corners_screen = []
            for corner in [bottom_left, bottom_right, top_right, top_left]:
                screen_x, screen_y = camera.world_to_screen(corner[0], corner[1], corner[2])
                corners_screen.append((screen_x, screen_y))
            
            # Draw the rectangle
            if len(corners_screen) >= 3:  # Need at least 3 points to draw a polygon
                pygame.draw.polygon(screen, self.color, corners_screen)
                
                # Draw outline
                pygame.draw.polygon(screen, constants.BLACK, corners_screen, 2)

    def reset(self):
        """Reset goalkeeper to initial position"""
        self.world_pos.x = 0.0
        self.velocity_x = 0.0
        self.target_x = 0.0
        print("Goalkeeper reset to initial position") 