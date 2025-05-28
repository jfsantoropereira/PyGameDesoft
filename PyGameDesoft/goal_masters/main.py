import pygame
import sys
import math
import json
import os
from . import constants
from .config import config_manager
from .camera import Camera
from .entities.ball import Ball
from .entities.goalkeeper import Goalkeeper
from .ui.powerbar import PowerBar
from .ui.contact_selector import ContactSelector

# Define HUD positions (can be moved to constants.py later if preferred)
HUD_POWER_BAR_WIDTH = 200
HUD_POWER_BAR_HEIGHT = 30
HUD_POWER_BAR_X = (constants.SCREEN_WIDTH - HUD_POWER_BAR_WIDTH) // 2
HUD_POWER_BAR_Y = constants.SCREEN_HEIGHT - HUD_POWER_BAR_HEIGHT - 20

HUD_CONTACT_SELECTOR_RADIUS = 50
HUD_CONTACT_SELECTOR_MARGIN = 20
HUD_CONTACT_SELECTOR_X = constants.SCREEN_WIDTH - HUD_CONTACT_SELECTOR_RADIUS - HUD_CONTACT_SELECTOR_MARGIN
HUD_CONTACT_SELECTOR_Y = HUD_CONTACT_SELECTOR_RADIUS + HUD_CONTACT_SELECTOR_MARGIN

# Coin display settings
COIN_SIZE = 32  # Size of the coin image in pixels
COIN_MARGIN = 10  # Margin from the screen edges
COIN_FONT_SIZE = 24  # Size of the coin count text

class Game:
    def __init__(self, selected_player="Elvis", player_config=None):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption("Goal Masters")
        self.clock = pygame.time.Clock()
        self.running = True

        # Player configuration
        self.selected_player = selected_player
        self.player_config = player_config or self.load_default_player_config()
        self.apply_player_config()

        # Game statistics
        self.goals_scored = 0
        self.attempts_made = 0
        self.coins_earned = 0

        # Load coin image and set coin count
        try:
            coin_image_path = os.path.join(os.path.dirname(__file__), "..", "imagens", "moeda.png")
            self.coin_image = pygame.image.load(coin_image_path)
            self.coin_image = pygame.transform.scale(self.coin_image, (COIN_SIZE, COIN_SIZE))
        except:
            # If coin image is not found, create a simple yellow circle
            self.coin_image = pygame.Surface((COIN_SIZE, COIN_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(self.coin_image, (255, 255, 0), (COIN_SIZE//2, COIN_SIZE//2), COIN_SIZE//2)

        # Load stadium crowd image
        try:
            crowd_image_path = os.path.join(os.path.dirname(__file__), "..", "imagens", "Stadium Crowd Wide from Yashin Request.png")
            self.stadium_crowd_image = pygame.image.load(crowd_image_path).convert_alpha()
            print(f"Stadium crowd image loaded: {self.stadium_crowd_image.get_size()}")
        except Exception as e:
            print(f"Failed to load stadium crowd image: {e}")
            self.stadium_crowd_image = None

        self.camera = Camera()
        self.ball = Ball()
        self.goalkeeper = Goalkeeper()
        self.power_bar = PowerBar(HUD_POWER_BAR_X, HUD_POWER_BAR_Y, HUD_POWER_BAR_WIDTH, HUD_POWER_BAR_HEIGHT)
        self.contact_selector = ContactSelector(HUD_CONTACT_SELECTOR_X, HUD_CONTACT_SELECTOR_Y, 
                                              HUD_CONTACT_SELECTOR_RADIUS, constants.BALL_RADIUS)

        self.aim_angle = 0  # Horizontal aim in degrees
        self.kick_angle_rad = 0.0 # Added for arrow rendering
        self.game_state = "placing_ball" # Start with ball placement mode
        self.goal_scored_timer = 0
        self.goal_scored_display_time = 2.0 # Seconds to display GOAL message (as per acceptance test)
        self.past_line_timer = 0.0
        self.past_line_display_time = 3.0 # Seconds before reset when ball crosses goal line without scoring
        self.time_since_kick = 0.0 # Timer to track time since last kick. May not be needed with new reset logic.
        self.kick_y_position = 0.0 # Store Y-coordinate of the ball at the time of kick
        self.last_awarded_coins = 0 # Store the amount of coins awarded for the last goal

        # Load goal sound
        try:
            goal_sound_path = os.path.join(os.path.dirname(__file__), "..", "imagens", "galvao-bueno-olha-o-gol.mp3")
            self.goal_sound = pygame.mixer.Sound(goal_sound_path)
            print("Goal sound loaded successfully.")
        except pygame.error as e:
            print(f"Failed to load goal sound: {e}")
            self.goal_sound = None

        # Load kick sound
        try:
            kick_sound_path = os.path.join(os.path.dirname(__file__), "..", "imagens", "ChuteGoal.mp3")
            self.kick_sound = pygame.mixer.Sound(kick_sound_path)
            print("Kick sound loaded successfully.")
        except pygame.error as e:
            print(f"Failed to load kick sound: {e}")
            self.kick_sound = None

        print(f"Game Initialized with player: {selected_player}")
        print(f"Ball initial world position: {self.ball.world_pos}")

    def load_default_player_config(self):
        """Load default player configuration if not provided"""
        default_config = {
            "Elvis": {
                "min_kick_strength": 15.0,
                "max_kick_strength": 35.0,
                "max_kick_curve": 3.0
            }
        }
        return default_config

    def apply_player_config(self):
        """Apply the selected player's configuration to the game"""
        if self.selected_player in self.player_config:
            player_stats = self.player_config[self.selected_player]
            # Update config manager with player-specific values
            config_manager.settings['min_kick_strength'] = player_stats['min_kick_strength']
            config_manager.settings['max_kick_strength'] = player_stats['max_kick_strength']
            config_manager.settings['max_kick_curve'] = player_stats['max_kick_curve']
            print(f"Applied {self.selected_player} config: Min Strength: {player_stats['min_kick_strength']}, Max Strength: {player_stats['max_kick_strength']}, Max Curve: {player_stats['max_kick_curve']}")

    def reset_for_kick(self):
        self.ball.reset()
        self.goalkeeper.reset()
        self.power_bar.reset()
        # self.contact_selector.set_contact_offsets(0,0) # Optionally reset contact point
        self.aim_angle = 0
        self.kick_angle_rad = 0.0 # Reset kick_angle_rad
        self.game_state = "placing_ball"  # Return to ball placement after reset
        print("Scene reset for new kick.")

    def place_ball_at_position(self, world_x, world_y):
        """Place the ball at the specified world coordinates"""
        # Ensure ball is on the ground
        self.ball.world_pos.x = world_x
        self.ball.world_pos.y = world_y
        self.ball.world_pos.z = constants.BALL_RADIUS
        print(f"Ball placed at: X={world_x:.1f}, Y={world_y:.1f}, Z={constants.BALL_RADIUS}")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_r: # Config reload AND Manual Reset
                    print("R key pressed: Reloading config and resetting scene...")
                    config_manager.reload_config()
                    self.apply_player_config()  # Reapply player config after reload
                    self.camera.reload_config() # Reload camera parameters
                    self.reset_for_kick() # Manually reset the game state
                    print(f"Game config reloaded. Min Strength: {config_manager.get_setting('min_kick_strength')}")
                    print("Scene manually reset.")
                
                if self.game_state == "placing_ball":
                    # Press Enter to confirm ball placement and move to aiming
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        self.game_state = "ready_to_kick"
                        print("Ball placement confirmed. Ready to aim and kick.")
                
                elif self.game_state == "ready_to_kick":
                    # Aiming with arrow keys
                    if event.key == pygame.K_LEFT:
                        self.aim_angle -= constants.ARROW_KEY_INCREMENT_DEG
                        self.kick_angle_rad = math.radians(self.aim_angle) # Update kick_angle_rad
                    elif event.key == pygame.K_RIGHT:
                        self.aim_angle += constants.ARROW_KEY_INCREMENT_DEG
                        self.kick_angle_rad = math.radians(self.aim_angle) # Update kick_angle_rad
                    
                    # Contact selector with WASD
                    self.contact_selector.handle_input(event) # Let contact_selector filter WASD itself

                    # Power bar charging
                    if event.key == pygame.K_SPACE:
                        if not self.ball.is_kicked:
                            self.power_bar.start_charging()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.game_state == "placing_ball":
                    # Place ball with mouse click
                    if event.button == 1:  # Left mouse button
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        world_coords = self.camera.screen_to_world_on_ground(mouse_x, mouse_y)
                        if world_coords:
                            world_x, world_y = world_coords
                            # Ensure the ball is placed within reasonable bounds
                            if -20 <= world_x <= 20 and 16.5 <= world_y <= 50:
                                self.place_ball_at_position(world_x, world_y)
                            else:
                                print(f"Ball placement out of bounds: X={world_x:.1f}, Y={world_y:.1f}")
                        else:
                            print("Cannot place ball at this location")
            
            if event.type == pygame.KEYUP:
                if self.game_state == "ready_to_kick":
                    if event.key == pygame.K_SPACE:
                        if self.power_bar.stop_charging(): # Returns true if it was charging
                            power = self.power_bar.get_power_fraction()
                            cx, cz = self.contact_selector.get_contact_offsets()
                            
                            self.kick_y_position = self.ball.world_pos.y # Record Y-pos at kick
                            print(f"Kicking from Y={self.kick_y_position:.2f}m: Power={power*100:.0f}%, Aim={self.aim_angle:.1f}deg, Contact(X:{cx:.2f}, Z:{cz:.2f})")
                            if self.kick_sound:
                                self.kick_sound.play()
                            self.ball.kick(
                                power_fraction=power,
                                horizontal_aim_deg=self.aim_angle,
                                pointer_x_offset=cx,
                                pointer_z_offset=cz
                            )
                            self.game_state = "ball_kicked"
                            self.attempts_made += 1
                            self.time_since_kick = 0.0 # Reset timer on new kick
                            # Power bar is reset internally by its logic or by game state change
                            # self.power_bar.reset() # Will be reset when scene resets

    def update(self, dt):
        if self.game_state == "ready_to_kick":
            self.power_bar.update(dt) # Update power bar charging

            # Check for automatic kick when power bar is full
            if self.power_bar.is_fully_charged_for_kick():
                power = self.power_bar.get_power_fraction() # Should be 1.0 as set in powerbar.py
                cx, cz = self.contact_selector.get_contact_offsets()
                self.kick_y_position = self.ball.world_pos.y # Record Y-pos at kick
                print(f"Kicking (MAX POWER AUTO) from Y={self.kick_y_position:.2f}m: Power={power*100:.0f}%, Aim={self.aim_angle:.1f}deg, Contact(X:{cx:.2f}, Z:{cz:.2f})")
                if self.kick_sound:
                    self.kick_sound.play()
                self.ball.kick(
                    power_fraction=power, 
                    horizontal_aim_deg=self.aim_angle,
                    pointer_x_offset=cx,
                    pointer_z_offset=cz
                )
                self.game_state = "ball_kicked"
                self.attempts_made += 1
                self.time_since_kick = 0.0
        
        elif self.game_state == "ball_kicked":
            self.ball.update(dt)
            self.goalkeeper.update(dt, self.ball)
            self.time_since_kick += dt # Increment time since kick - still useful for other potential logic
            
            # Check for goalkeeper save BEFORE checking for goals
            if self.goalkeeper.check_save(self.ball):
                if self.goalkeeper.save_ball(self.ball):
                    # Save was successful, don't check for goals this frame
                    return
            
            # Check if ball crossed goal line (y<=0)
            if self.ball.world_pos.y <= 0:
                # Determine if it's a goal
                if constants.GOAL_MIN_X <= self.ball.world_pos.x <= constants.GOAL_MAX_X and \
                   constants.BALL_RADIUS <= self.ball.world_pos.z <= constants.CROSSBAR_Z:
                    print("GOAL!")
                    self.goals_scored += 1
                    
                    # Determine coins based on kick distance
                    if self.kick_y_position > 40:
                        self.last_awarded_coins = 40
                    elif self.kick_y_position > 30: # and <= 40 implied
                        self.last_awarded_coins = 20
                    else: # Covers 16.5 < Y <= 30 and any other valid goal case
                        self.last_awarded_coins = 10
                        
                    self.coins_earned += self.last_awarded_coins
                    print(f"Awarded {self.last_awarded_coins} coins for goal from Y={self.kick_y_position:.2f}m")
                    self.game_state = "goal_scored"
                    self.goal_scored_timer = 0.0
                    if self.goal_sound:
                        self.goal_sound.play()
                else:
                    # Only transition to past_goal_line if not already in that state or goal_scored state
                    if self.game_state == "ball_kicked": 
                        print("Ball crossed goal line (no goal). Waiting to reset.")
                        self.game_state = "past_goal_line"
                        self.past_line_timer = 0.0

        elif self.game_state == "past_goal_line":
            # Ball continues to update visually even after crossing line, until reset
            self.ball.update(dt) 
            self.past_line_timer += dt
            if self.past_line_timer >= self.past_line_display_time:
                self.reset_for_kick()
        
        elif self.game_state == "goal_scored":
            # Ball might continue to update visually for a short period or freeze
            # self.ball.update(dt) # Optionally freeze ball by not updating
            self.goal_scored_timer += dt
            if self.goal_scored_timer >= self.goal_scored_display_time:
                self.reset_for_kick()

    def draw_pitch_and_goal(self, screen, camera):
        # Essential pitch markings around the goal area only
        PENALTY_AREA_LENGTH = 16.5  # meters from goal line (corrected from 11.0)
        PENALTY_ARC_RADIUS = 9.15  # meters
        
        # Calculate boundaries for penalty area
        goal_line_y = 0
        penalty_area_left_x = -16.5  # Half of penalty area width (33m total)
        penalty_area_right_x = 16.5
        
        line_color = constants.WHITE
        line_thickness = 2
        
        # Helper function to draw a line at ground level (z=0)
        def draw_ground_line(start_x, start_y, end_x, end_y, thickness=line_thickness):
            start_screen = camera.world_to_screen(start_x, start_y, 0)
            end_screen = camera.world_to_screen(end_x, end_y, 0)
            pygame.draw.line(screen, line_color, start_screen, end_screen, thickness)
        
        # Helper function to draw an arc at ground level
        def draw_ground_arc(center_x, center_y, radius, start_angle, end_angle, thickness=line_thickness):
            # Draw arc by approximating with line segments
            num_segments = 20
            angle_step = (end_angle - start_angle) / num_segments
            
            for i in range(num_segments):
                angle1 = start_angle + i * angle_step
                angle2 = start_angle + (i + 1) * angle_step
                
                x1 = center_x + radius * math.cos(angle1)
                y1 = center_y + radius * math.sin(angle1)
                x2 = center_x + radius * math.cos(angle2)
                y2 = center_y + radius * math.sin(angle2)
                
                draw_ground_line(x1, y1, x2, y2, thickness)
        
        # 1. GOAL LINE (back line)
        draw_ground_line(-25, goal_line_y, 25, goal_line_y, 3) # Updated to x=-25 to x=25
        
        # NEW: Side Lines
        # Adjust far y-coordinate to be further from camera to avoid projection issues
        # Camera is at y=65. Previous 64.9 was too close.
        side_line_far_y = 45.0 
        # Left side line
        draw_ground_line(-25, goal_line_y, -25, side_line_far_y, 3)
        # Right side line
        draw_ground_line(25, goal_line_y, 25, side_line_far_y, 3)
        
        # 2. PENALTY AREA (penalty box)
        # Left side of penalty box
        draw_ground_line(penalty_area_left_x, goal_line_y, penalty_area_left_x, PENALTY_AREA_LENGTH)
        # Right side of penalty box
        draw_ground_line(penalty_area_right_x, goal_line_y, penalty_area_right_x, PENALTY_AREA_LENGTH)
        # Top of penalty box
        draw_ground_line(penalty_area_left_x, PENALTY_AREA_LENGTH, penalty_area_right_x, PENALTY_AREA_LENGTH)
        
        # 3. PENALTY ARC - the big semicircle at the edge of the penalty area
        penalty_spot_distance = 11.0  # meters from goal line
        # Calculate angle so arc tips touch penalty box edge at y=16.5m
        # Arc center at (0, 11), radius 9.15m, box edge at y=16.5m
        # Distance from arc center to box edge: 16.5 - 11 = 5.5m
        # cos(θ) = 5.5 / 9.15, so θ = arccos(5.5/9.15)
        arc_half_angle = math.acos(5.5 / PENALTY_ARC_RADIUS)
        start_angle = math.pi/2 - arc_half_angle
        end_angle = math.pi/2 + arc_half_angle
        draw_ground_arc(0, penalty_spot_distance, PENALTY_ARC_RADIUS, start_angle, end_angle)
        
        # 4. PENALTY SPOT
        penalty_spot_radius = 0.11  # meters (as specified by user)
        penalty_spot_screen = camera.world_to_screen(0, penalty_spot_distance, 0)
        # Use proper rendering logic like the ball
        spot_diameter_world = penalty_spot_radius * 2
        scaled_diameter_pixels, _ = camera.get_sprite_display_size(
            spot_diameter_world, 
            spot_diameter_world,
            0,  # x position
            penalty_spot_distance,  # y position  
            0   # z position (on ground)
        )
        spot_radius_pixels = max(1, int(scaled_diameter_pixels / 2))
        pygame.draw.circle(screen, line_color, penalty_spot_screen, spot_radius_pixels)
        
        # 5. GOAL FRAME (keeping the existing goal posts and crossbar)
        # Posts (at Y=0, Z=0 to Z=CROSSBAR_Z)
        goal_posts_world = [
            (constants.GOAL_MIN_X, 0, 0), (constants.GOAL_MIN_X, 0, constants.CROSSBAR_Z),
            (constants.GOAL_MAX_X, 0, 0), (constants.GOAL_MAX_X, 0, constants.CROSSBAR_Z),
        ]
        # Crossbar (at Y=0, Z=CROSSBAR_Z, between X_MIN and X_MAX)
        goal_crossbar_world = [
            (constants.GOAL_MIN_X, 0, constants.CROSSBAR_Z), (constants.GOAL_MAX_X, 0, constants.CROSSBAR_Z)
        ]

        goal_post_color = constants.WHITE
        # Draw Posts
        p1_start_screen = camera.world_to_screen(*goal_posts_world[0])
        p1_end_screen = camera.world_to_screen(*goal_posts_world[1])
        pygame.draw.line(screen, goal_post_color, p1_start_screen, p1_end_screen, 5)
        
        p2_start_screen = camera.world_to_screen(*goal_posts_world[2])
        p2_end_screen = camera.world_to_screen(*goal_posts_world[3])
        pygame.draw.line(screen, goal_post_color, p2_start_screen, p2_end_screen, 5)
        
        # Draw Crossbar
        cb_start_screen = camera.world_to_screen(*goal_crossbar_world[0])
        cb_end_screen = camera.world_to_screen(*goal_crossbar_world[1])
        pygame.draw.line(screen, goal_post_color, cb_start_screen, cb_end_screen, 5)

    def draw_kick_indicator_arrow(self, surface, camera):
        if self.game_state != "ready_to_kick":
            return

        arrow_color = constants.RED
        arrow_length = 1.5  # meters, adjust as needed
        arrow_head_length = 0.5  # meters
        arrow_head_angle_offset = math.pi / 6  # 30 degrees for barbs spread

        # Arrow origin at ball's center on the ground plane
        ball_center_x = self.ball.world_pos.x
        ball_center_y = self.ball.world_pos.y
        ball_center_z = constants.BALL_RADIUS  # Draw arrow on ground plane
        
        # Tip of the arrow's main shaft
        # Based on ball.kick: Vx = V_horz * sin(theta_x_rad), Vy = -V_horz * cos(theta_x_rad)
        # So, tip_dx = length * sin(angle), tip_dy = -length * cos(angle)
        tip_x = ball_center_x + arrow_length * math.sin(self.kick_angle_rad)
        tip_y = ball_center_y - arrow_length * math.cos(self.kick_angle_rad) # -Y is forward

        # Project points to screen
        # All points are on ground plane at Z=BALL_RADIUS
        p_base_screen = camera.world_to_screen(ball_center_x, ball_center_y, ball_center_z)
        p_tip_screen = camera.world_to_screen(tip_x, tip_y, ball_center_z)

        if p_base_screen[0] < -constants.SCREEN_WIDTH or p_tip_screen[0] < -constants.SCREEN_WIDTH: # Basic off-screen check
            return

        # Draw main shaft
        pygame.draw.line(surface, arrow_color, p_base_screen, p_tip_screen, 3)

        # Calculate arrowhead barbs
        # Angle of the main shaft
        main_shaft_angle_rad = self.kick_angle_rad 

        # Barb 1
        barb1_angle_rad = main_shaft_angle_rad + math.pi - arrow_head_angle_offset
        barb1_x = tip_x + arrow_head_length * math.sin(barb1_angle_rad)
        barb1_y = tip_y - arrow_head_length * math.cos(barb1_angle_rad)
        p_barb1_screen = camera.world_to_screen(barb1_x, barb1_y, ball_center_z)
        pygame.draw.line(surface, arrow_color, p_tip_screen, p_barb1_screen, 3)

        # Barb 2
        barb2_angle_rad = main_shaft_angle_rad + math.pi + arrow_head_angle_offset
        barb2_x = tip_x + arrow_head_length * math.sin(barb2_angle_rad)
        barb2_y = tip_y - arrow_head_length * math.cos(barb2_angle_rad)
        p_barb2_screen = camera.world_to_screen(barb2_x, barb2_y, ball_center_z)
        pygame.draw.line(surface, arrow_color, p_tip_screen, p_barb2_screen, 3)

    def draw_stadium_crowd(self, screen, camera):
        """Draw the stadium crowd image behind the goal as a 2x2 tile grid"""
        if not self.stadium_crowd_image:
            return
        
        # Base position for the 2x2 grid
        base_crowd_world_x = 0  # Centered
        base_crowd_world_y = -5 # 5m behind goal
        base_crowd_bottom_z = 2 # Bottom of the lowest tiles 2m above ground
        
        # Get the original image dimensions
        original_tile_pixel_width, original_tile_pixel_height = self.stadium_crowd_image.get_rect().size
        
        # Define the world width of a single tile
        tile_world_width = 40  # meters wide for one tile
        # Maintain aspect ratio for the height of one tile
        tile_world_height = original_tile_pixel_height * (tile_world_width / original_tile_pixel_width)
        
        for row in range(2):  # 0 for bottom row, 1 for top row
            for col in range(2):  # 0 for left column, 1 for right column
                
                # Calculate center X for the current tile
                # The grid is centered at base_crowd_world_x.
                # If col=0, center is base_crowd_world_x - tile_world_width/2
                # If col=1, center is base_crowd_world_x + tile_world_width/2
                current_tile_center_x = base_crowd_world_x - (tile_world_width / 2) + (col * tile_world_width)
                
                # Calculate bottom Z for the current tile
                current_tile_bottom_z = base_crowd_bottom_z + (row * tile_world_height)
                current_tile_top_z = current_tile_bottom_z + tile_world_height

                # Get screen positions for the four corners of the current tile
                bottom_left_screen = camera.world_to_screen(
                    current_tile_center_x - tile_world_width / 2, base_crowd_world_y, current_tile_bottom_z
                )
                bottom_right_screen = camera.world_to_screen(
                    current_tile_center_x + tile_world_width / 2, base_crowd_world_y, current_tile_bottom_z
                )
                top_left_screen = camera.world_to_screen(
                    current_tile_center_x - tile_world_width / 2, base_crowd_world_y, current_tile_top_z
                )
                top_right_screen = camera.world_to_screen(
                    current_tile_center_x + tile_world_width / 2, base_crowd_world_y, current_tile_top_z
                )
                
                # Basic culling for the current tile (can be improved)
                # If all x are < -100 or all x > SCREEN_WIDTH + 100, skip.
                all_x_coords = [bottom_left_screen[0], bottom_right_screen[0], top_left_screen[0], top_right_screen[0]]
                if all(x < -100 for x in all_x_coords) or all(x > constants.SCREEN_WIDTH + 100 for x in all_x_coords):
                    continue 
                # Similar check for y (though less likely for a wide background)
                all_y_coords = [bottom_left_screen[1], bottom_right_screen[1], top_left_screen[1], top_right_screen[1]]
                if all(y < -100 for y in all_y_coords) or all(y > constants.SCREEN_HEIGHT + 100 for y in all_y_coords):
                    continue

                # Calculate apparent screen width and height for this tile
                # This uses the projected bottom corners for width, and projected left corners for height.
                # More robust methods might consider all four points or use affine transforms for non-rectangular quads.
                
                # Approximate screen width based on the bottom edge of the tile
                app_screen_width = abs(bottom_right_screen[0] - bottom_left_screen[0])
                # Approximate screen height based on the left edge of the tile
                app_screen_height = abs(bottom_left_screen[1] - top_left_screen[1])

                # Ensure minimum size of 1x1 pixel to avoid errors with scale
                scaled_width = max(1, int(app_screen_width))
                scaled_height = max(1, int(app_screen_height))

                if scaled_width > 0 and scaled_height > 0:
                    try:
                        scaled_tile_image = pygame.transform.scale(
                            self.stadium_crowd_image, 
                            (scaled_width, scaled_height)
                        )
                        
                        # Blit position is the top-left most point of the projected quad
                        blit_x = min(top_left_screen[0], bottom_left_screen[0], top_right_screen[0], bottom_right_screen[0])
                        blit_y = min(top_left_screen[1], bottom_left_screen[1], top_right_screen[1], bottom_right_screen[1])
                        
                        screen.blit(scaled_tile_image, (blit_x, blit_y))
                    except pygame.error as e:
                        print(f"Error scaling or blitting crowd tile: {e}. Scaled size: ({scaled_width}, {scaled_height})")
                        pass # Continue if one tile fails

    def render(self):
        self.screen.fill(constants.DARK_GREEN)
        
        # Draw the stadium crowd first (behind everything)
        self.draw_stadium_crowd(self.screen, self.camera)
        
        # Draw the game world
        self.draw_pitch_and_goal(self.screen, self.camera)
        
        # Draw the ball and goalkeeper in proper depth order (higher Y = farther = render first)
        ball_screen_pos = self.camera.world_to_screen(self.ball.world_pos.x, self.ball.world_pos.y, self.ball.world_pos.z)
        
        # Calculate scaled ball diameter using camera method
        ball_diameter_world = constants.BALL_RADIUS * 2
        scaled_diameter_pixels_w, _ = self.camera.get_sprite_display_size(
            ball_diameter_world, 
            ball_diameter_world, # Assuming ball sprite is square in terms of base units
            self.ball.world_pos.x,
            self.ball.world_pos.y,
            self.ball.world_pos.z
        )
        ball_radius_pixels = max(1, int(scaled_diameter_pixels_w / 2)) # Ensure at least 1 pixel radius
        
        # Render in depth order: farther objects (higher Y) first, closer objects (lower Y) last
        if self.ball.world_pos.y > self.goalkeeper.world_pos.y:
            # Ball is farther, draw ball first then goalkeeper
            pygame.draw.circle(self.screen, constants.WHITE, ball_screen_pos, ball_radius_pixels)
            self.goalkeeper.draw(self.screen, self.camera)
        else:
            # Goalkeeper is farther, draw goalkeeper first then ball
            self.goalkeeper.draw(self.screen, self.camera)
            pygame.draw.circle(self.screen, constants.WHITE, ball_screen_pos, ball_radius_pixels)

        # Draw ball placement preview in placement mode
        if self.game_state == "placing_ball":
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_coords = self.camera.screen_to_world_on_ground(mouse_x, mouse_y)
            if world_coords:
                world_x, world_y = world_coords
                if -20 <= world_x <= 20 and 16.5 <= world_y <= 50:
                    preview_screen_pos = self.camera.world_to_screen(world_x, world_y, constants.BALL_RADIUS)
                    preview_radius_pixels = max(1, int(scaled_diameter_pixels_w / 2))
                    # Draw semi-transparent preview ball
                    preview_surface = pygame.Surface((preview_radius_pixels * 2, preview_radius_pixels * 2), pygame.SRCALPHA)
                    pygame.draw.circle(preview_surface, (255, 255, 255, 128), (preview_radius_pixels, preview_radius_pixels), preview_radius_pixels)
                    self.screen.blit(preview_surface, (preview_screen_pos[0] - preview_radius_pixels, preview_screen_pos[1] - preview_radius_pixels))

        # Draw aim arrow during ready_to_kick
        if self.game_state == "ready_to_kick":
            self.draw_kick_indicator_arrow(self.screen, self.camera)

        # Draw contact selector UI
        self.contact_selector.draw(self.screen)

        # Draw power bar UI
        self.power_bar.draw(self.screen)

        font = pygame.font.Font(None, 36)

        # Game state message overlay
        if self.game_state == "goal_scored":
            goal_text_message = f"GOAL! +{self.last_awarded_coins} coins"
            goal_text = font.render(goal_text_message, True, constants.YELLOW)
            goal_rect = goal_text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))
            self.screen.blit(goal_text, goal_rect)

        elif self.game_state == "past_goal_line":
            miss_text = font.render("MISS! Try again", True, constants.RED)
            miss_rect = miss_text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))
            self.screen.blit(miss_text, miss_rect)

        # --- Text display at the BOTTOM of the screen ---
        line_spacing = 5
        text_margin = 10  # Margin from screen edges
        font_height = font.get_height()

        # -- Bottom-LEFT Text (Stacked) --
        # Line 1 (Bottom-most on left): Game Statistics (Goals/Attempts)
        ga_stats_text_str = f"Goals: {self.goals_scored}  Attempts: {self.attempts_made}"
        ga_stats_text_surface = font.render(ga_stats_text_str, True, constants.WHITE)
        ga_stats_text_y = constants.SCREEN_HEIGHT - font_height - text_margin 
        self.screen.blit(ga_stats_text_surface, (text_margin, ga_stats_text_y))

        # Line 2 (Middle on left): Session Coins
        session_coins_text_str = f"Session Coins: {self.coins_earned}"
        session_coins_text_surface = font.render(session_coins_text_str, True, constants.WHITE)
        session_coins_text_y = ga_stats_text_y - font_height - line_spacing
        self.screen.blit(session_coins_text_surface, (text_margin, session_coins_text_y))

        # Line 3 (Top-most on left): Player Info
        player_text_str = f"Player: {self.selected_player}"
        player_text_surface = font.render(player_text_str, True, constants.WHITE)
        player_text_y = session_coins_text_y - font_height - line_spacing
        self.screen.blit(player_text_surface, (text_margin, player_text_y))

        # -- Bottom-RIGHT Text (Stacked) --
        controls_title_str = "Controls:"
        control_line1_str = "Click/Enter: Place/Confirm"
        control_line2_str = "Arrows: Aim | WASD: Contact"
        control_line3_str = "Space: Charge | R: Reset"
        control_line4_str = "ESC: Menu"

        control_texts = [
            font.render(controls_title_str, True, constants.WHITE),
            font.render(control_line1_str, True, constants.WHITE),
            font.render(control_line2_str, True, constants.WHITE),
            font.render(control_line3_str, True, constants.WHITE),
            font.render(control_line4_str, True, constants.WHITE),
        ]

        for i, text_surface in enumerate(control_texts):
            text_x = constants.SCREEN_WIDTH - text_surface.get_width() - text_margin
            # Start from the bottom and stack upwards
            text_y = constants.SCREEN_HEIGHT - (len(control_texts) - i) * font_height - (len(control_texts) - 1 - i) * line_spacing - text_margin
            self.screen.blit(text_surface, (text_x, text_y))

        pygame.display.flip()

    def run(self):
        print("Starting Game Loop. Arrows: Aim, WASD: Contact, Space: Charge/Kick.")
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

        print("Exiting Game")
        return {
            'goals': self.goals_scored,
            'attempts': self.attempts_made,
            'coins_earned': self.coins_earned
        }

    def run_with_player(self, selected_player, player_config):
        """Run the game with a specific player configuration"""
        self.selected_player = selected_player
        self.player_config = player_config
        self.apply_player_config()
        return self.run()

if __name__ == '__main__':
    game = Game()
    game.run()
