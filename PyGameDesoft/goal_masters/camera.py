from . import constants
import math
from .config import config_manager

# Minimum effective depth for perspective scaling to avoid division by zero or extreme scaling.
MIN_PERSPECTIVE_DEPTH = 0.1  # metres (reduced from 1.0 for closer interaction, must be > 0)

class Camera:
    def __init__(self):
        # These will serve as defaults if config is missing specific entries
        self.default_pos_x = constants.CAMERA_POSITION[0]
        self.default_pos_y = constants.CAMERA_POSITION[1]
        self.default_pos_z = constants.CAMERA_POSITION[2]
        
        self.position = [self.default_pos_x, self.default_pos_y, self.default_pos_z]
        self.camera_fov_degrees = 60.0
        self.focal_length_pixels = 0.0
        self.downlook_radians = 0.0
        self.cos_downlook = 1.0
        self.sin_downlook = 0.0
        
        self.reload_config() # Load initial configuration values

    def reload_config(self):
        """Reloads camera parameters from the configuration manager."""
        # Defaults from constants.CAMERA_POSITION or hardcoded reasonable values
        cam_pos_x_default = self.default_pos_x
        cam_pos_y_default = self.default_pos_y
        cam_height_default = self.default_pos_z 
        fov_default = 60.0
        downlook_default = 0.0

        configured_pos_x = config_manager.get_setting('camera_position_x', default=cam_pos_x_default)
        configured_pos_y = config_manager.get_setting('camera_position_y', default=cam_pos_y_default)
        configured_height = config_manager.get_setting('camera_height', default=cam_height_default)
        
        self.position = [configured_pos_x, configured_pos_y, configured_height]

        self.camera_fov_degrees = config_manager.get_setting('camera_fov_degrees', default=fov_default)
        
        # Clamp FOV to a practical range to avoid math errors (e.g., tan(90) or tan(0))
        # Typical FOV range is (0, 180) exclusive. Let's use 1 to 179 degrees.
        safe_fov_degrees = max(1.0, min(179.0, self.camera_fov_degrees))
        if safe_fov_degrees != self.camera_fov_degrees:
            print(f"Warning: camera_fov_degrees {self.camera_fov_degrees} out of range, clamped to {safe_fov_degrees}.")
            self.camera_fov_degrees = safe_fov_degrees
            
        fov_radians = math.radians(self.camera_fov_degrees)
        
        # Calculate focal length in pixels based on FOV and screen width
        # focal_length = (screenWidth / 2) / tan(FOV / 2)
        if math.tan(fov_radians / 2) == 0: # Should be caught by FOV clamping
            self.focal_length_pixels = float('inf') 
        else:
            self.focal_length_pixels = (constants.SCREEN_WIDTH / 2) / math.tan(fov_radians / 2)
        
        self.downlook_degrees = config_manager.get_setting('camera_downlook_degrees', default=downlook_default)
        self.downlook_radians = math.radians(self.downlook_degrees)
        self.cos_downlook = math.cos(self.downlook_radians)
        self.sin_downlook = math.sin(self.downlook_radians)
        
        print(f"Camera config loaded/reloaded: Position={self.position}, FOV={self.camera_fov_degrees}deg, Downlook={self.downlook_degrees}deg, FocalLengthPixels={self.focal_length_pixels:.2f}px")

    def _get_view_space_coords(self, world_x, world_y, world_z):
        """Transforms world coords to camera view space and calculates depth."""
        rel_x = world_x - self.position[0]
        rel_y = world_y - self.position[1]
        rel_z = world_z - self.position[2]

        # Depth along camera's forward vector (F = (0, -cos_a, -sin_a))
        # depth = dot((rel_x, rel_y, rel_z), F)
        depth = rel_y * (-self.cos_downlook) + rel_z * (-self.sin_downlook)

        # Coords on camera's view plane (Right R=(1,0,0), Up U=(0, sin_a, cos_a))
        # view_plane_x = dot((rel_x, rel_y, rel_z), R)
        view_plane_x = rel_x 
        # view_plane_y = dot((rel_x, rel_y, rel_z), U)
        view_plane_y = rel_y * self.sin_downlook + rel_z * self.cos_downlook
        
        return view_plane_x, view_plane_y, depth

    def get_projection_scale(self, depth_along_view_axis):
        """ Returns the perspective scaling factor (focal_length / depth). """
        # Note: depth_along_view_axis should be already > MIN_PERSPECTIVE_DEPTH from caller
        if depth_along_view_axis <= 0: # Should ideally not happen if MIN_PERSPECTIVE_DEPTH is used by caller
             return 0 # Avoid division by zero / negative, results in zero size/displacement
        return self.focal_length_pixels / depth_along_view_axis

    def world_to_screen(self, world_x, world_y, world_z):
        view_x, view_y, depth = self._get_view_space_coords(world_x, world_y, world_z)

        if depth < MIN_PERSPECTIVE_DEPTH:
            return (-9999, -9999)  # Off-screen or too close

        # Perspective projection: screen_coord = view_coord * focal_length / depth
        # Effectively: screen_coord_displace = view_coord * self.get_projection_scale(depth)
        
        # Using direct formula to avoid double division if get_projection_scale implies one
        screen_x_displace = view_x * self.focal_length_pixels / depth
        screen_y_displace = view_y * self.focal_length_pixels / depth 

        screen_x = constants.SCREEN_WIDTH / 2 + screen_x_displace
        screen_y = constants.SCREEN_HEIGHT / 2 - screen_y_displace # Positive view_y is up

        return round(screen_x), round(screen_y)

    def get_sprite_display_size(self, base_width, base_height, world_x, world_y, world_z):
        """
        Calculates the display size (width, height) of a sprite based on its world Y-coordinate.
        "Shrink sprite size proportional to distance (Y)" is interpreted as:
        display_size = base_size * (cam_dist_factor / world_y) which is base_size * projection_scale.
        """
        # This method now requires full world coordinates for proper depth calculation.
        _view_x, _view_y, depth = self._get_view_space_coords(world_x, world_y, world_z)

        if depth < MIN_PERSPECTIVE_DEPTH:
            return (0, 0) # Too close or behind

        # Scale factor is focal_length / depth.
        # Using get_projection_scale which implements this with MIN_PERSPECTIVE_DEPTH check (implicitly done by caller check)
        scale_factor = self.get_projection_scale(depth) # depth here is already > MIN_PERSPECTIVE_DEPTH
        
        display_width = base_width * scale_factor
        display_height = base_height * scale_factor
        
        return int(max(1, display_width)), int(max(1, display_height)) # Ensure at least 1x1 pixel


if __name__ == '__main__':
    # Example Usage (assuming constants.py is accessible)
    # This part won't run directly without adjusting imports if goal_masters/ is not in PYTHONPATH
    # or if not run as `python -m goal_masters.camera` from parent dir.
    # For simplicity, let's imagine constants are loaded if we could run this.
    
    # Mock constants for standalone testing if needed:
    class MockConstants:
        SCREEN_WIDTH = 1280
        SCREEN_HEIGHT = 720
        CAMERA_POSITION = (0, 50, 12)
    
    #constants = MockConstants() # Uncomment to test standalone here by overriding import

    cam = Camera()
    print(f"Camera initialized with position: {cam.position} and cam_dist_factor: {cam.focal_length_pixels}")

    # Test points:
    # 1. Ball at far spawn edge, on the ground
    world_coords_far = (0, constants.SPAWN_Y_MIN, constants.BALL_RADIUS)
    scale_far = cam.get_projection_scale(world_coords_far[1])
    screen_coords_far = cam.world_to_screen(*world_coords_far)
    sprite_size_far = cam.get_sprite_display_size(1, 1, *world_coords_far) # base size of 1x1 world unit
    print(f"Far point {world_coords_far}: scale={scale_far:.2f}, screen_pos={screen_coords_far}, sprite_scale_mult={sprite_size_far}")

    # 2. Ball at near spawn edge, on the ground
    world_coords_near = (0, constants.SPAWN_Y_MAX, constants.BALL_RADIUS)
    scale_near = cam.get_projection_scale(world_coords_near[1])
    screen_coords_near = cam.world_to_screen(*world_coords_near)
    sprite_size_near = cam.get_sprite_display_size(1, 1, *world_coords_near)
    print(f"Near point {world_coords_near}: scale={scale_near:.2f}, screen_pos={screen_coords_near}, sprite_scale_mult={sprite_size_near}")

    # 3. Object to the right, at midfield height, at camera's Z height
    world_coords_right_mid = (10, 25, cam.position[2]) 
    scale_mid = cam.get_projection_scale(world_coords_right_mid[1])
    screen_coords_right_mid = cam.world_to_screen(*world_coords_right_mid)
    sprite_size_mid = cam.get_sprite_display_size(1,1, *world_coords_right_mid)
    print(f"Mid point {world_coords_right_mid}: scale={scale_mid:.2f}, screen_pos={screen_coords_right_mid}, sprite_scale_mult={sprite_size_mid}")

    # 4. Object on the goal line (Y=0), should use epsilon
    world_coords_goal_line = (0, 0, 0)
    scale_goal = cam.get_projection_scale(world_coords_goal_line[1]) # uses MIN_Y_FOR_PROJECTION_SCALE
    screen_coords_goal_line = cam.world_to_screen(*world_coords_goal_line)
    sprite_size_goal = cam.get_sprite_display_size(1,1, *world_coords_goal_line)
    print(f"Goal line point {world_coords_goal_line}: scale={scale_goal:.2f}, screen_pos={screen_coords_goal_line}, sprite_scale_mult={sprite_size_goal}")

    # 5. Object directly under camera, on ground
    world_coords_under_cam = (cam.position[0], cam.position[1], 0)
    scale_under = cam.get_projection_scale(world_coords_under_cam[1])
    screen_coords_under_cam = cam.world_to_screen(*world_coords_under_cam)
    sprite_size_under = cam.get_sprite_display_size(1,1, *world_coords_under_cam)
    print(f"Under camera point {world_coords_under_cam}: scale={scale_under:.2f}, screen_pos={screen_coords_under_cam}, sprite_scale_mult={sprite_size_under}")
