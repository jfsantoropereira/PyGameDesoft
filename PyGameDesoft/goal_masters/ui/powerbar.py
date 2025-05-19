import pygame
from .. import constants

class PowerBar:
    def __init__(self, x, y, width, height, segments=constants.POWER_BAR_SEGMENTS):
        self.rect = pygame.Rect(x, y, width, height)
        self.segments = segments
        self.charge_level = 0  # Current number of lit segments (0 to self.segments)
        self.is_charging = False
        self.charge_time_per_segment = 0.25  # Seconds to fill one segment
        self.current_segment_charge_time = 0
        self.power_fraction_on_release = 0.0
        self.kick_at_full_power = False # Flag to indicate automatic kick at full power

        self.border_color = constants.BLACK
        self.empty_color = constants.WHITE
        self.filled_color = constants.RED
        self.border_width = 2

    def start_charging(self):
        if not self.is_charging and self.charge_level < self.segments:
            self.is_charging = True
            self.current_segment_charge_time = 0
            print("PowerBar: Started charging")
        elif self.charge_level >= self.segments:
            print("PowerBar: Already fully charged")

    def stop_charging(self):
        if self.is_charging:
            self.is_charging = False
            # Only set power fraction if not already set by reaching full charge
            if not self.kick_at_full_power: 
                self.power_fraction_on_release = self.charge_level / self.segments
            print(f"PowerBar: Stopped charging. Power fraction: {self.power_fraction_on_release:.2f}")
            return True # Indicates charging was active and stopped
        return False # Indicates it wasn't charging

    def get_power_fraction(self):
        """Returns the power fraction from the last charge cycle."""
        return self.power_fraction_on_release

    def reset(self):
        """Resets the power bar for the next kick."""
        self.charge_level = 0
        self.is_charging = False
        self.current_segment_charge_time = 0
        self.power_fraction_on_release = 0.0
        self.kick_at_full_power = False # Reset flag
        print("PowerBar: Reset")

    def update(self, dt):
        if self.is_charging and self.charge_level < self.segments:
            self.current_segment_charge_time += dt
            if self.current_segment_charge_time >= self.charge_time_per_segment:
                self.charge_level += 1
                self.current_segment_charge_time = 0 
                print(f"PowerBar: Charge level {self.charge_level}/{self.segments}")
                if self.charge_level >= self.segments:
                    self.is_charging = False 
                    self.power_fraction_on_release = 1.0 # Full power
                    self.kick_at_full_power = True # Signal for automatic kick
                    print("PowerBar: Fully charged - KICK INITIATED")
        # If it fills up, is_charging remains true until space is released.

    def draw(self, screen):
        pygame.draw.rect(screen, self.border_color, self.rect, self.border_width)
        segment_width = (self.rect.width - 2 * self.border_width) / self.segments
        
        for i in range(self.segments):
            seg_rect = pygame.Rect(
                self.rect.x + self.border_width + i * segment_width,
                self.rect.y + self.border_width,
                segment_width - (1 if i < self.segments -1 else 0), # Small gap or no gap
                self.rect.height - 2 * self.border_width
            )
            
            color = self.filled_color if i < self.charge_level else self.empty_color
            pygame.draw.rect(screen, color, seg_rect)

    def is_fully_charged_for_kick(self):
        """Checks if the bar is full and a kick should be triggered.
        Resets the flag after checking to ensure one kick per full charge.
        """
        if self.kick_at_full_power:
            self.kick_at_full_power = False # Reset after check
            return True
        return False

# Example usage:
if __name__ == '__main__':
    pygame.init()
    # Mock constants for standalone testing if needed:
    class MockConstants:
        SCREEN_WIDTH = 1280
        SCREEN_HEIGHT = 720
        POWER_BAR_SEGMENTS = 4
        BLACK = (0,0,0)
        WHITE = (255,255,255)
        RED = (255,0,0)
    constants = MockConstants()

    screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    pygame.display.set_caption("PowerBar Test")
    clock = pygame.time.Clock()
    
    # Position the power bar (e.g., bottom center)
    pb_width = 200
    pb_height = 30
    pb_x = (constants.SCREEN_WIDTH - pb_width) // 2
    pb_y = constants.SCREEN_HEIGHT - pb_height - 20
    power_bar = PowerBar(pb_x, pb_y, pb_width, pb_height)
    
    running = True
    kick_requested = False
    
    print("Hold SPACE to charge, release to see power. Q to quit.")

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_SPACE:
                    if not kick_requested: # Prevent re-charging if a kick is pending acknowledgement
                        power_bar.start_charging()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if power_bar.is_charging or power_bar.charge_level > 0: # Check if it was charging or has charge
                        if power_bar.stop_charging():
                            kick_power = power_bar.get_power_fraction()
                            print(f"KICK EVENT! Power: {kick_power:.2f}")
                            kick_requested = True # Simulate kick happening
                            # In game, ball.kick() would be called here
        
        if kick_requested:
            # After kick, reset power bar for next use
            # This might happen after a delay or ball reset in the main game
            print("Kick acknowledged, resetting power bar.")
            power_bar.reset()
            kick_requested = False

        power_bar.update(dt)
        
        screen.fill((100, 100, 100)) # Background
        power_bar.draw(screen)
        pygame.display.flip()
        
    pygame.quit()
