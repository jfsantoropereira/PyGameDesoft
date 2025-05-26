import pygame
import sys
import math
import json
import os
from . import constants
from .config import config_manager
from .camera import Camera
from .entities.ball import Ball
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

        self.camera = Camera()
        self.ball = Ball()
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
                            
                            print(f"Kicking: Power={power*100:.0f}%, Aim={self.aim_angle:.1f}deg, Contact(X:{cx:.2f}, Z:{cz:.2f})")
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
                print(f"Kicking (MAX POWER AUTO): Power={power*100:.0f}%, Aim={self.aim_angle:.1f}deg, Contact(X:{cx:.2f}, Z:{cz:.2f})")
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
            self.time_since_kick += dt # Increment time since kick - still useful for other potential logic
            # Check if ball crossed goal line (y<=0)
            if self.ball.world_pos.y <= 0:
                # Determine if it's a goal
                if constants.GOAL_MIN_X <= self.ball.world_pos.x <= constants.GOAL_MAX_X and \
                   constants.BALL_RADIUS <= self.ball.world_pos.z <= constants.CROSSBAR_Z:
                    print("GOAL!")
                    self.goals_scored += 1
                    self.coins_earned += 10  # Award 10 coins per goal
                    self.game_state = "goal_scored"
                    self.goal_scored_timer = 0.0
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
        # Goal Frame (Simplified 3D lines projected)
        # Posts (at Y=0, Z=0 to Z=CROSSBAR_Z)
        goal_posts_world = [
            (constants.GOAL_MIN_X, 0, 0), (constants.GOAL_MIN_X, 0, constants.CROSSBAR_Z),
            (constants.GOAL_MAX_X, 0, 0), (constants.GOAL_MAX_X, 0, constants.CROSSBAR_Z),
        ]
        # Crossbar (at Y=0, Z=CROSSBAR_Z, between X_MIN and X_MAX)
        goal_crossbar_world = [
            (constants.GOAL_MIN_X, 0, constants.CROSSBAR_Z), (constants.GOAL_MAX_X, 0, constants.CROSSBAR_Z)
        ]

        goal_line_color = constants.WHITE
        # Draw Posts
        p1_start_screen = camera.world_to_screen(*goal_posts_world[0])
        p1_end_screen = camera.world_to_screen(*goal_posts_world[1])
        pygame.draw.line(screen, goal_line_color, p1_start_screen, p1_end_screen, 5)
        
        p2_start_screen = camera.world_to_screen(*goal_posts_world[2])
        p2_end_screen = camera.world_to_screen(*goal_posts_world[3])
        pygame.draw.line(screen, goal_line_color, p2_start_screen, p2_end_screen, 5)
        
        # Draw Crossbar
        cb_start_screen = camera.world_to_screen(*goal_crossbar_world[0])
        cb_end_screen = camera.world_to_screen(*goal_crossbar_world[1])
        pygame.draw.line(screen, goal_line_color, cb_start_screen, cb_end_screen, 5)

        # Pitch Lines (example: goal line and a center circle)
        # Goal line (Y=0, between X_MIN and X_MAX at Z=0)
        goal_line_start_world = (constants.GOAL_MIN_X - 2, 0, 0) # Extend slightly for visibility
        goal_line_end_world = (constants.GOAL_MAX_X + 2, 0, 0)
        pygame.draw.line(screen, goal_line_color, camera.world_to_screen(*goal_line_start_world), camera.world_to_screen(*goal_line_end_world), 3)
        
        # Center circle (on ground Z=BALL_RADIUS, at Y=some_midfield_y, radius e.g. 9.15m)
        # Drawing a projected circle is more complex; for now, a line at midfield.
        midfield_line_y = 25 # Arbitrary midfield Y
        midfield_start_world = (-15, midfield_line_y, 0)
        midfield_end_world = (15, midfield_line_y, 0)
        pygame.draw.line(screen, goal_line_color, camera.world_to_screen(*midfield_start_world), camera.world_to_screen(*midfield_end_world), 2)
        
        # Penalty Arc (more complex, skip for now for MVP)

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

    def render(self):
        self.screen.fill(constants.DARK_GREEN)
        
        # Draw the game world
        self.draw_pitch_and_goal(self.screen, self.camera)
        
        # Draw the ball
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

        # Font for text
        font = pygame.font.Font(None, 36)

        # Game state message overlay
        if self.game_state == "goal_scored":
            goal_text = font.render("GOAL! +10 coins", True, constants.YELLOW)
            goal_rect = goal_text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))
            self.screen.blit(goal_text, goal_rect)

        elif self.game_state == "past_goal_line":
            miss_text = font.render("MISS! Try again", True, constants.RED)
            miss_rect = miss_text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))
            self.screen.blit(miss_text, miss_rect)

        # Player info
        player_text = font.render(f"Player: {self.selected_player}", True, constants.WHITE)
        self.screen.blit(player_text, (10, 10))

        # Game statistics
        stats_text = font.render(f"Goals: {self.goals_scored}  Attempts: {self.attempts_made}  Coins: {self.coins_earned}", True, constants.WHITE)
        self.screen.blit(stats_text, (10, 50))

        # Display coins earned in this session
        coin_text = font.render(f"Coins this session: {self.coins_earned}", True, constants.YELLOW)
        self.screen.blit(coin_text, (10, 90))

        # Instructions
        if self.game_state == "placing_ball":
            instructions = [
                "Click to place ball",
                "Enter: Confirm placement", 
                "ESC: Exit to Menu"
            ]
            for i, instruction in enumerate(instructions):
                inst_text = font.render(instruction, True, constants.WHITE)
                self.screen.blit(inst_text, (constants.SCREEN_WIDTH - 250, 10 + i * 30))
        elif self.game_state == "ready_to_kick":
            instructions = [
                "Arrow Keys: Aim",
                "WASD: Contact Point", 
                "Space: Charge Power",
                "ESC: Exit to Menu"
            ]
            for i, instruction in enumerate(instructions):
                inst_text = font.render(instruction, True, constants.WHITE)
                self.screen.blit(inst_text, (constants.SCREEN_WIDTH - 250, 10 + i * 30))

        # Ball live position readout
        pos_text = font.render(
            f"Ball Pos: X={self.ball.world_pos.x:.1f}  Y={self.ball.world_pos.y:.1f}  Z={self.ball.world_pos.z:.2f}",
            True,
            constants.WHITE,
        )
        self.screen.blit(pos_text, (10, 130))

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
