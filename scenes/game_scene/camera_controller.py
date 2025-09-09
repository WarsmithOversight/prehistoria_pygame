# In camera_controller.py
import pygame, math
from shared_helpers import hex_to_pixel

class CameraController:
    """Manages all camera state, including auto-centering and zoom configuration."""
    
    def __init__(self, persistent_state, variable_state, tween_manager, event_bus, pan_speed=15):

        # ✨ Store references to the global state and systems
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.tween_manager = tween_manager
        self.event_bus = event_bus

        # 👂 Subscribe to camera-related events
        self.event_bus.subscribe("CENTER_CAMERA_ON_TILE", self.on_center_camera)

        # Read the static configuration from persistent_state
        self.zoom_config = self.persistent_state["pers_zoom_config"]

        # 💾 Set pan_speed once at the start.
        self.pan_speed = pan_speed

        # Sync internal state with the initial values from variable_state
        self.offset = list(variable_state.get("var_render_offset", (0, 0)))
        self.dev_quickboot = bool(persistent_state.get("pers_dev_quickboot"))

        if self.dev_quickboot:
            # Lock zoom entirely to a single step
            fixed = float(persistent_state.get("pers_quickboot_zoom", 0.40))
            self.zoom_config.update({"min_zoom": fixed, "max_zoom": fixed, "zoom_interval": 1.0})
            self.zoom = fixed
            variable_state["var_current_zoom"] = fixed

            # Don’t run the dynamic min-zoom computation at all
            print(f"[Camera] ⚙️ Dev Quickboot: zoom locked at {fixed:.2f}.")
            print(f"[Camera] ✅ Camera controller initialized.")
            return

        # ⚙️ Calculate Dynamic Minimum Zoom
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
        map_cols = self.persistent_state["pers_map_size"]["cols"]
        map_rows = self.persistent_state["pers_map_size"]["rows"]

        tile_w = self.persistent_state["pers_tile_hex_w"]
        tile_h = self.persistent_state["pers_tile_hex_h"]

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
        
        print(f"[Camera] ✅ Camera controller initialized.")

    def on_center_camera(self, data):
        """Event handler for centering the camera on a specific tile."""
        self.center_on_tile(data["q"], data["r"], animated=data.get("animated", True))

    def center_on_map(self, persistent_state, variable_state, animated=True):
        """Calculates the correct offset to center the map and updates the state."""
        # Get screen and map center coordinates
        screen = self.persistent_state["pers_screen"]
        screen_w, screen_h = screen.get_size()
        screen_center_px = (screen_w / 2, screen_h / 2)
        map_center_q, map_center_r = self.persistent_state["pers_map_center"]
        
        # ✨ FIX: Get the pure "world space" pixel position, ignoring current camera state.
        temp_variable_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        map_center_world_px = hex_to_pixel(map_center_q, map_center_r, self.persistent_state, temp_variable_state)

        # Calculate the required offset to align the map center with the screen center
        offset_x = screen_center_px[0] - (map_center_world_px[0] * self.zoom)
        offset_y = screen_center_px[1] - (map_center_world_px[1] * self.zoom)

        if animated:
            # ✨ Animate the camera pan instead of instantly setting the offset
            self.tween_manager.add_tween(
                target_dict=self,
                animation_type='value',
                key_to_animate='offset',
                drawable_type='camera_offset',
                start_val=tuple(self.offset),
                end_val=(offset_x, offset_y),
                duration=1.0 # seconds
            )
            print(f"[Camera] ✅ Panning to center of map.")
        else:
            # Instantly set the offset and update the global state.
            self.offset = [offset_x, offset_y]
            self.variable_state["var_render_offset"] = tuple(self.offset)
            print(f"[Camera] ✅ Map instantly centered.")
 
    def center_on_tile(self, q, r, animated=True):        
        """Calculates the offset to center the view on a specific hex coordinate."""
        
        # 1. Get screen center
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
        screen_center_px = (screen_w / 2, screen_h / 2)
        
        # 2. Get the target tile's world pixel position (at 1x zoom)
        # We temporarily ignore the current zoom and offset for this calculation.
        temp_variable_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        target_world_px = hex_to_pixel(q, r, self.persistent_state, temp_variable_state)
        
        # 3. Calculate the new offset needed to align the target with the screen center,
        #    accounting for the current zoom level.
        target_offset_x = screen_center_px[0] - (target_world_px[0] * self.zoom)
        target_offset_y = screen_center_px[1] - (target_world_px[1] * self.zoom)
 
        if animated:
            # ✨ Animate the camera pan
            self.tween_manager.add_tween(
                target_dict=self,
                animation_type='value',
                key_to_animate='offset',
                drawable_type='camera_offset',
                start_val=tuple(self.offset),
                end_val=(target_offset_x, target_offset_y),
                duration=0.7 # seconds
            )
            print(f"[Camera] ✅ Scrolling to tile ({q},{r}).")
        else:
            self.offset = [target_offset_x, target_offset_y]
            print(f"[Camera] ✅ Snapping to tile ({q},{r}).")

    def handle_events(self, events):
        """Processes events for panning and zooming."""

        # Panning
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: self.offset[1] += self.pan_speed
        if keys[pygame.K_s]: self.offset[1] -= self.pan_speed
        if keys[pygame.K_a]: self.offset[0] += self.pan_speed
        if keys[pygame.K_d]: self.offset[0] -= self.pan_speed
            
        if self.dev_quickboot:
            return  # ignore zoom input entirely

        # Zooming
        for event in events:
            if event.type == pygame.MOUSEWHEEL:

                # Get the screen center as our anchor point.
                screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
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

    def update(self):
        """Writes the controller's current values into the global variable_state."""
        self._clamp_offset_to_bounds()
        self.variable_state["var_render_offset"] = tuple(self.offset)
        self.variable_state["var_current_zoom"] = self.zoom

    def _snap_zoom(self):
        """Snaps the current zoom level to the nearest discrete step."""
        
        if getattr(self, "dev_quickboot", False):
            # Hard clamp to the fixed value
            self.zoom = round(self.zoom_config["min_zoom"], 2)
            return
        
        config = self.zoom_config
        step, min_z, max_z = config["zoom_interval"], config["min_zoom"], config["max_zoom"]
        
        # Snap to the nearest absolute multiple of the zoom interval.
        snapped = round(self.zoom / step) * step

        # Then, clamp the result to the dynamic min/max bounds.
        clamped = max(min_z, min(max_z, snapped))
        self.zoom = round(clamped, 2)

    def _clamp_offset_to_bounds(self):
            """Ensures the camera's offset does not allow panning past the map's edge."""

            # Grab measurements from persistent state
            screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
            map_cols = self.persistent_state["pers_map_size"]["cols"]
            map_rows = self.persistent_state["pers_map_size"]["rows"]
            tile_w = self.persistent_state["pers_tile_hex_w"]
            tile_h = self.persistent_state["pers_tile_hex_h"]

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