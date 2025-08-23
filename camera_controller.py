# In camera_controller.py
import pygame, math
from shared_helpers import hex_to_pixel

class CameraController:
    """Manages all camera state, including auto-centering and zoom configuration."""
    
    def __init__(self, persistent_state, variable_state, pan_speed=15):

        # ──────────────────────────────────────────────────
        # ⚙️ Read Config & Initial State
        # ──────────────────────────────────────────────────
        # Read the static configuration from persistent_state
        self.zoom_config = persistent_state["pers_zoom_config"]
        
        # Sync internal state with the initial values from variable_state
        self.offset = list(variable_state.get("var_render_offset", (0, 0)))
               
        # ──────────────────────────────────────────────────
        # ⚙️ Calculate Dynamic Minimum Zoom
        # ──────────────────────────────────────────────────
        screen_w, screen_h = persistent_state["pers_screen"].get_size()
        map_cols = persistent_state["pers_map_size"]["cols"]
        map_rows = persistent_state["pers_map_size"]["rows"]

        tile_w = persistent_state["pers_tile_hex_w"]
        tile_h = persistent_state["pers_tile_hex_h"]

        map_pixel_w_at_1x = (map_cols + 0.5) * tile_w
        map_pixel_h_at_1x = (map_rows * 0.75 + 0.25) * tile_h

        # Determine the zoom required to fit the map's width and height to the screen.
        zoom_to_fit_width = screen_w / map_pixel_w_at_1x if map_pixel_w_at_1x > 0 else 1.0
        zoom_to_fit_height = screen_h / map_pixel_h_at_1x if map_pixel_h_at_1x > 0 else 1.0
        hard_limit_raw = max(zoom_to_fit_width, zoom_to_fit_height)

        # Snap this hard limit UP to the next valid zoom step.
        zoom_interval = self.zoom_config["zoom_interval"]
        hard_limit_snapped = math.ceil(hard_limit_raw / zoom_interval) * zoom_interval

        # Define how many zoom steps of padding for the "endless ocean" effect.
        ZOOM_STEPS_OF_PADDING = 4
        soft_min_zoom = hard_limit_snapped + (ZOOM_STEPS_OF_PADDING * zoom_interval)
        
        # Failsafe to ensure min_zoom doesn't exceed max_zoom.
        final_min_zoom = min(soft_min_zoom, self.zoom_config["max_zoom"])

        # Overwrite the config's min_zoom with our new limit.
        self.zoom_config["min_zoom"] = final_min_zoom
        print(f"[Camera] ✅ Min zoom with padding set to {final_min_zoom:.2f}.")

        # Set the initial zoom, ensuring it's not less than our new minimum.
        initial_zoom = variable_state.get("var_current_zoom", 1.0)
        self.zoom = max(initial_zoom, final_min_zoom)

        # Immediately snap the initial zoom to be safe.
        self._snap_zoom()

        # ──────────────────────────────────────────────────
        # 💾 Internal State
        # ──────────────────────────────────────────────────
        self.pan_speed = pan_speed
        
        print(f"[Camera] ✅ Camera controller initialized.")

    def center_on_map(self, persistent_state, variable_state):
        """Calculates the correct offset to center the map and updates the state."""
        # Get screen and map center coordinates
        screen = persistent_state["pers_screen"]
        screen_w, screen_h = screen.get_size()
        screen_center_px = (screen_w / 2, screen_h / 2)
        map_center_q, map_center_r = persistent_state["pers_map_center"]
        
        # Calculate the pixel position of the map's center hex
        map_center_px = hex_to_pixel(map_center_q, map_center_r, persistent_state, variable_state)

        # Calculate the required offset to align the map center with the screen center
        offset_x = screen_center_px[0] - map_center_px[0]
        offset_y = screen_center_px[1] - map_center_px[1]
        
        # Update the controller's internal state
        self.offset = [offset_x, offset_y]
        
        # Update the global variable_state so all other modules see the change
        variable_state["var_render_offset"] = tuple(self.offset)
        print(f"[Camera] ✅ Map centered with offset {tuple(self.offset)}.")

    def handle_events(self, events, persistent_state):
        """Processes events for panning and zooming."""

        # Panning
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: self.offset[1] += self.pan_speed
        if keys[pygame.K_s]: self.offset[1] -= self.pan_speed
        if keys[pygame.K_a]: self.offset[0] += self.pan_speed
        if keys[pygame.K_d]: self.offset[0] -= self.pan_speed
            
        # Zooming
        for event in events:
            if event.type == pygame.MOUSEWHEEL:

                # Get the screen center as our anchor point.
                screen_w, screen_h = persistent_state["pers_screen"].get_size()
                screen_center = (screen_w / 2, screen_h / 2)

                # Find which point on the map is under the anchor BEFORE zooming.
                old_zoom = self.zoom
                world_point_x = (screen_center[0] - self.offset[0]) / old_zoom
                world_point_y = (screen_center[1] - self.offset[1]) / old_zoom

                # Apply the new zoom level and snap it to a valid step.
                self.zoom += event.y * self.zoom_config["zoom_interval"]
                self._snap_zoom() # self.zoom is now the final new_zoom.

                # Calculate the new offset required to keep the world point at the anchor.
                new_offset_x = screen_center[0] - (world_point_x * self.zoom)
                new_offset_y = screen_center[1] - (world_point_y * self.zoom)
                self.offset = [new_offset_x, new_offset_y]

    def update(self, persistent_state, variable_state):
        """Writes the controller's current values into the global variable_state."""
        self._clamp_offset_to_bounds(persistent_state)
        variable_state["var_render_offset"] = tuple(self.offset)
        variable_state["var_current_zoom"] = self.zoom

    def _snap_zoom(self):
        """Snaps the current zoom level to the nearest discrete step."""
        config = self.zoom_config
        step, min_z, max_z = config["zoom_interval"], config["min_zoom"], config["max_zoom"]
        
        # Snap to the nearest absolute multiple of the zoom interval.
        snapped = round(self.zoom / step) * step

        # Then, clamp the result to the dynamic min/max bounds.
        self.zoom = max(min_z, min(max_z, snapped))

    def _clamp_offset_to_bounds(self, persistent_state):
            """Ensures the camera's offset does not allow panning past the map's edge."""

            # Grab measurements from persistent state
            screen_w, screen_h = persistent_state["pers_screen"].get_size()
            map_cols = persistent_state["pers_map_size"]["cols"]
            map_rows = persistent_state["pers_map_size"]["rows"]
            tile_w = persistent_state["pers_tile_hex_w"]
            tile_h = persistent_state["pers_tile_hex_h"]

            # Define percentage margin
            margin_x = screen_w * 0.15
            margin_y = screen_h * 0.15

            # Calculate map width at 1x zoom
            map_pixel_w_at_1x = (map_cols + 0.5) * tile_w
            map_pixel_h_at_1x = (map_rows * 0.75 + 0.25) * tile_h

            # Multiply that with current zoom
            zoomed_map_w = map_pixel_w_at_1x * self.zoom
            zoomed_map_h = map_pixel_h_at_1x * self.zoom

            # Since min_zoom guarantees the map is larger than the screen,
            # we only need this simple, hard-clamping logic.
            # The margin is then applied to the boundaries.
            max_x = 0 - margin_x
            max_y = 0 - margin_y
            min_x = (screen_w - zoomed_map_w) + margin_x
            min_y = (screen_h - zoomed_map_h) + margin_y

            self.offset[0] = max(min_x, min(self.offset[0], max_x))
            self.offset[1] = max(min_y, min(self.offset[1], max_y))

    def get_offset(self):
        return tuple(self.offset)

    def get_zoom(self):
        return self.zoom
    
    def pan(self, dx, dy):
        """Applies a positional delta to the camera's offset."""
        self.offset[0] += dx
        self.offset[1] += dy