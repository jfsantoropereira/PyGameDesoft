import pygame
import constants

class ContactSelector:
    def __init__(self, hud_x, hud_y, hud_radius, ball_actual_radius):
        self.hud_rect = pygame.Rect(hud_x - hud_radius, hud_y - hud_radius, 2 * hud_radius, 2 * hud_radius)
        self.hud_center_x = hud_x
        self.hud_center_y = hud_y
        self.hud_radius = hud_radius  # Radius of the magnified ball display on HUD
        self.ball_actual_radius = ball_actual_radius # Actual radius of the game ball, for scaling offsets

        # Contact point offsets relative to the ball's center, in world units (e.g., meters)
        # These range from -ball_actual_radius to +ball_actual_radius
        self.contact_x_offset = 0.0 
        self.contact_z_offset = 0.0

        self.pointer_color = constants.RED
        self.ball_hud_color = constants.WHITE
        self.border_color = constants.BLACK
        self.pointer_size = 10 # pixels for the 'X' pointer arms

        # Movement speed of the pointer on the HUD, relative to hud_radius per second
        self.pointer_move_increment_world = self.ball_actual_radius / 10.0 # Move 1/10th of ball radius per key press for now
                                                                      # This needs to be tied to WASD input handling rate

    def get_contact_offsets(self):
        """Returns the current contact point offsets (x_offset, z_offset) in world units."""
        return self.contact_x_offset, self.contact_z_offset

    def set_contact_offsets(self, x_offset, z_offset):
        """Manually sets the contact point offsets, clamping them to the ball's radius."""
        self.contact_x_offset = max(-self.ball_actual_radius, min(self.ball_actual_radius, x_offset))
        self.contact_z_offset = max(-self.ball_actual_radius, min(self.ball_actual_radius, z_offset))

    def move_pointer(self, dx_world, dz_world):
        """
        Moves the contact pointer by given world unit deltas.
        dx_world: change in x offset (world units)
        dz_world: change in z offset (world units)
        """
        new_x_offset = self.contact_x_offset + dx_world
        new_z_offset = self.contact_z_offset + dz_world
        self.set_contact_offsets(new_x_offset, new_z_offset)
        # print(f"ContactSelector: Moved to x_off={self.contact_x_offset:.2f}, z_off={self.contact_z_offset:.2f}")

    def handle_input(self, event):
        """
        Handles WASD input to move the pointer.
        This should be called for pygame.KEYDOWN events.
        Returns True if input was processed, False otherwise.
        """
        increment = self.pointer_move_increment_world 
        moved = False
        if event.key == pygame.K_w:
            self.move_pointer(0, increment) # Positive Z offset (up on ball front face)
            moved = True
        elif event.key == pygame.K_s:
            self.move_pointer(0, -increment) # Negative Z offset (down on ball front face)
            moved = True
        elif event.key == pygame.K_a:
            self.move_pointer(-increment, 0) # Negative X offset (left on ball front face)
            moved = True
        elif event.key == pygame.K_d:
            self.move_pointer(increment, 0)  # Positive X offset (right on ball front face)
            moved = True
        
        if moved:
            print(f"ContactSelector: Offsets X={self.contact_x_offset:.3f}, Z={self.contact_z_offset:.3f}")
        return moved

    def draw(self, screen):
        # Draw the magnified ball representation
        pygame.draw.circle(screen, self.ball_hud_color, (self.hud_center_x, self.hud_center_y), self.hud_radius)
        pygame.draw.circle(screen, self.border_color, (self.hud_center_x, self.hud_center_y), self.hud_radius, 2)

        # Calculate pointer position on the HUD
        # Map world offsets (-radius to +radius) to HUD display (-hud_radius to +hud_radius)
        pointer_hud_x = self.hud_center_x + (self.contact_x_offset / self.ball_actual_radius) * self.hud_radius
        # For Z-offset on ball, positive Z is up. On screen, positive Y is down.
        # So a positive Z-offset should move the pointer upwards on the HUD circle.
        pointer_hud_y = self.hud_center_y - (self.contact_z_offset / self.ball_actual_radius) * self.hud_radius

        # Draw the red 'X' pointer
        s = self.pointer_size // 2
        pygame.draw.line(screen, self.pointer_color, 
                         (pointer_hud_x - s, pointer_hud_y - s), 
                         (pointer_hud_x + s, pointer_hud_y + s), 2)
        pygame.draw.line(screen, self.pointer_color, 
                         (pointer_hud_x - s, pointer_hud_y + s), 
                         (pointer_hud_x + s, pointer_hud_y - s), 2)

# Example usage:
if __name__ == '__main__':
    pygame.init()
    class MockConstants:
        SCREEN_WIDTH = 1280
        SCREEN_HEIGHT = 720
        RED = (255,0,0)
        WHITE = (255,255,255)
        BLACK = (0,0,0)
        BALL_RADIUS = 0.11 # Actual game ball radius
    constants = MockConstants()

    screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    pygame.display.set_caption("Contact Selector Test")
    clock = pygame.time.Clock()

    # Position the contact selector (e.g., upper right)
    hud_display_radius = 50 # Pixel radius of the HUD ball
    hud_margin = 20
    cs_x = constants.SCREEN_WIDTH - hud_display_radius - hud_margin
    cs_y = hud_display_radius + hud_margin
    contact_selector = ContactSelector(cs_x, cs_y, hud_display_radius, constants.BALL_RADIUS)

    running = True
    print("Use WASD to move contact pointer. Q to quit.")

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                # Pass WASD to contact selector
                contact_selector.handle_input(event)
        
        # No update method needed for contact_selector itself, input handling is direct.

        screen.fill((100, 100, 100)) # Background
        contact_selector.draw(screen)
        pygame.display.flip()
        
    pygame.quit()
