import pygame
import sys
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

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption("Goal Masters")
        self.clock = pygame.time.Clock()
        self.running = True

        self.camera = Camera()
        self.ball = Ball()
        self.power_bar = PowerBar(HUD_POWER_BAR_X, HUD_POWER_BAR_Y, HUD_POWER_BAR_WIDTH, HUD_POWER_BAR_HEIGHT)
        self.contact_selector = ContactSelector(HUD_CONTACT_SELECTOR_X, HUD_CONTACT_SELECTOR_Y, 
                                              HUD_CONTACT_SELECTOR_RADIUS, constants.BALL_RADIUS)

        self.aim_angle = 0  # Horizontal aim in degrees
        self.game_state = "ready_to_kick" # Possible states: ready_to_kick, ball_kicked, goal_scored, past_goal_line
        self.goal_scored_timer = 0
        self.goal_scored_display_time = 2.0 # Seconds to display GOAL message (as per acceptance test)
        self.past_line_timer = 0.0
        self.past_line_display_time = 3.0 # Seconds before reset when ball crosses goal line without scoring
        self.time_since_kick = 0.0 # Timer to track time since last kick. May not be needed with new reset logic.

        print("Game Initialized")
        print(f"Ball initial world position: {self.ball.world_pos}")

    def reset_for_kick(self):
        self.ball.reset()
        self.power_bar.reset()
        # self.contact_selector.set_contact_offsets(0,0) # Optionally reset contact point
        self.aim_angle = 0
        self.game_state = "ready_to_kick"
        print("Scene reset for new kick.")

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
                    self.camera.reload_config() # Reload camera parameters
                    self.reset_for_kick() # Manually reset the game state
                    print(f"Game config reloaded. Min Strength: {config_manager.get_setting('min_kick_strength')}")
                    print("Scene manually reset.")
                
                if self.game_state == "ready_to_kick":
                    # Aiming with arrow keys
                    if event.key == pygame.K_LEFT:
                        self.aim_angle -= constants.ARROW_KEY_INCREMENT_DEG
                    elif event.key == pygame.K_RIGHT:
                        self.aim_angle += constants.ARROW_KEY_INCREMENT_DEG
                    
                    # Contact selector with WASD
                    self.contact_selector.handle_input(event) # Let contact_selector filter WASD itself

                    # Power bar charging
                    if event.key == pygame.K_SPACE:
                        if not self.ball.is_kicked:
                            self.power_bar.start_charging()
            
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
                            self.time_since_kick = 0.0 # Reset timer on new kick
                            # Power bar is reset internally by its logic or by game state change
                            # self.power_bar.reset() # Will be reset when scene resets

    def update(self, dt):
        if self.game_state == "ready_to_kick":
            self.power_bar.update(dt) # Update power bar charging
        
        elif self.game_state == "ball_kicked":
            self.ball.update(dt)
            self.time_since_kick += dt # Increment time since kick - still useful for other potential logic
            # Check if ball crossed goal line (y<=0)
            if self.ball.world_pos.y <= 0:
                # Determine if it's a goal
                if constants.GOAL_MIN_X <= self.ball.world_pos.x <= constants.GOAL_MAX_X and \
                   constants.BALL_RADIUS <= self.ball.world_pos.z <= constants.CROSSBAR_Z:
                    print("GOAL!")
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

    def render(self):
        self.screen.fill(constants.GREEN)  # Basic pitch color

        self.draw_pitch_and_goal(self.screen, self.camera)
        self.ball.draw(self.screen, self.camera)
        self.power_bar.draw(self.screen)
        self.contact_selector.draw(self.screen)

        if self.game_state == "goal_scored":
            font = pygame.font.Font(None, 100)
            text = font.render("GOAL!", True, constants.WHITE)
            text_rect = text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))
            self.screen.blit(text, text_rect)
        
        # HUD Readouts (placeholders)
        font = pygame.font.Font(None, 36)
        aim_text = font.render(f"Aim: {self.aim_angle:.1f}°", True, constants.WHITE)
        self.screen.blit(aim_text, (10, 10))
        # Power readout can be part of power_bar or separate
        # Lateral m/s^2 - this is self.ball.lateral_acceleration_x if kicked
        lat_accel = self.ball.lateral_acceleration_x if self.ball.is_kicked else 0.0
        lat_text = font.render(f"Curve Acc: {lat_accel:.2f} m/s²", True, constants.WHITE)
        self.screen.blit(lat_text, (10, 50))
        power_display = self.power_bar.charge_level / self.power_bar.segments if self.power_bar.is_charging or self.power_bar.charge_level > 0 else self.power_bar.power_fraction_on_release
        if self.game_state == "ball_kicked": # show last used power if ball is kicked
            power_display = self.power_bar.power_fraction_on_release
        power_text = font.render(f"Power: {power_display*100:.0f}%", True, constants.WHITE)
        self.screen.blit(power_text, (10, 90))

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
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = Game()
    game.run()
