# tween_manager.py
# A flexible animation system using an orchestrator and composable "puzzle pieces".

import pygame
from shared_helpers import hex_to_pixel, hex_geometry, get_point_on_bezier_curve

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True

# ──────────────────────────────────────────────────
# ⚙️ Orchestrator (The TweenManager)
# ──────────────────────────────────────────────────

class TweenManager:
    """
    Interprets animation calls, assembles the correct tween and updater
    "puzzle pieces", and manages all active animation instances.
    """
    def __init__(self, persistent_state, variable_state):
        self.active_tweens = []
        self.persistent_state = persistent_state
        self.variable_state = variable_state

        # 🧩 The "Puzzle Piece" Registry 🧩
        # Maps string names to the classes that handle the logic.
        self.ANIMATION_MAP = {
            'travel': TravelTween,
        }
        self.UPDATER_MAP = {
            'player_token': PlayerTokenUpdater,
        }

    def add_tween(self, target_dict, animation_type, drawable_type, on_complete=None, **kwargs):
        """
        The main entry point to create and start an animation.

        Args:
            target_dict (dict): The drawable from the notebook to be animated.
            animation_type (str): The kind of animation to perform (e.g., 'travel').
            drawable_type (str): The type of drawable being animated (e.g., 'player_token').
            on_complete (callable, optional): A function to call when the tween finishes.
            **kwargs: Arguments specific to the animation type (e.g., path, speed).
        """
        # Look up the correct animation class (e.g., TravelTween)
        animation_class = self.ANIMATION_MAP.get(animation_type)
        if not animation_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Animation type '{animation_type}' not found.")
            return

        # Look up the correct updater class (e.g., PlayerTokenUpdater)
        updater_class = self.UPDATER_MAP.get(drawable_type)
        if not updater_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Updater for drawable type '{drawable_type}' not found.")
            return

        # Assemble the puzzle: create an instance of the updater
        updater = updater_class(self.persistent_state, self.variable_state)

        # Create the final tween instance, passing it the updater and all other info
        tween_instance = animation_class(
            target_dict,
            updater,
            on_complete,
            **kwargs
        )

        self.active_tweens.append(tween_instance)
        print(f"[TweenManager] ✅ Tween created: '{animation_type}' on '{drawable_type}'.")

    def update(self, dt):
        """Updates all active tweens and removes any that have finished."""
        # Update all tweens
        for tween in self.active_tweens:
            tween.update(dt)

        # Filter out finished tweens
        self.active_tweens = [t for t in self.active_tweens if not t.is_finished]

# ──────────────────────────────────────────────────
# ⚙️ Base Tween Class
# ──────────────────────────────────────────────────

class Tween:
    """A base class that all animation types will inherit from."""
    def __init__(self, target_dict, updater, on_complete):
        self.target_dict = target_dict
        self.updater = updater
        self.on_complete = on_complete
        self.is_finished = False

    def update(self, dt):
        # This method will be implemented by each specific animation subclass.
        raise NotImplementedError

    def finish(self):
        """Marks the tween as finished and calls the completion callback."""
        self.is_finished = True
        if self.on_complete:
            self.on_complete()

# ──────────────────────────────────────────────────
# 🧩 Puzzle Pieces
# ──────────────────────────────────────────────────

# 🏞️ --- Animation Types ---

class TravelTween(Tween):
    """
    Animates a drawable along a path of destinations at a given speed.
    The path can be hex coordinates or pixel coordinates.
    """
    def __init__(self, target_dict, updater, on_complete, path, speed_hps):
        super().__init__(target_dict, updater, on_complete)
        self.speed = speed_hps
        self.path_hex = []
        self.path_pixels = []
        self.current_segment = 0
        self.progress = 0.0

        # Immediately add the pixel_pos key to start the animation
        self.target_dict['pixel_pos'] = self.updater.get_world_pixel(target_dict['q'], target_dict['r'])

        # Process the path to convert hex coords to pixels if needed
        self._initialize_path(path)
        # Failsafe: if path was invalid, finish immediately.
        if self.is_finished: return

        self._setup_segment()

    def _initialize_path(self, path):
        """Converts a path of hex coordinates into pixel coordinates for animation."""
        if not path or len(path) < 2:
            self.finish()
            return

        is_hex_path = isinstance(path[0], tuple) and len(path[0]) == 2

        if is_hex_path:
            self.path_hex = path
            # For hex paths, we will calculate pixel destinations segment by segment
        else:
            self.path_pixels = path
            if DEBUG: print("[TravelTween] ⚠️ Path is pixel-based; hex 'q' and 'r' will not be updated.")

    def _setup_segment(self):
        """Calculates the start, end, and control points for the current segment."""
        path_length = len(self.path_hex)
        is_first_segment = self.current_segment == 0
        is_final_segment = self.current_segment == path_length - 1

        current_coord = self.path_hex[self.current_segment]
        prev_coord = self.path_hex[self.current_segment - 1] if not is_first_segment else None

        # Look ahead to the next coordinate if one exists
        next_coord = None
        if not is_final_segment:
            next_coord = self.path_hex[self.current_segment + 1]

        geom = self.updater.get_hex_geom(current_coord[0], current_coord[1])

        #  P0 (Start Point)
        self.p0 = geom['center'] if is_first_segment else self.updater.get_edge_center(geom, prev_coord)

        # P2 (End Point)
        self.p2 = geom['center'] if is_final_segment else self.updater.get_edge_center(geom, next_coord)

        # P1 (Control Point) - makes the path curve or straighten
        self.p1 = geom['center']

        # Let the updater handle z-value changes
        if next_coord:
            self.updater.on_segment_start(self.target_dict, current_coord, next_coord)

    def update(self, dt):
        if self.is_finished: return

        self.progress = min(1.0, self.progress + (self.speed * dt))

        # Calculate the new pixel position using the curve
        new_pixel_pos = get_point_on_bezier_curve(self.p0, self.p1, self.p2, self.progress)
        self.target_dict['pixel_pos'] = new_pixel_pos

        # Check if the segment is complete
        if self.progress >= 1.0:
            path_length = len(self.path_hex)

            # Let the updater handle updating the token's q,r coordinates
            self.updater.on_segment_complete(self.target_dict, self.path_hex[self.current_segment])

            self.current_segment += 1

            # Check if the entire path is finished
            if self.current_segment >= path_length:
                self.finish() # The animation is now naturally complete
            else:
                # More segments remain, set up the next one
                self.progress = 0.0
                self._setup_segment()

# 🗿 --- Drawable Type Updaters ---

# 🗿 --- Drawable Type Updaters ---

class PlayerTokenUpdater:
    """Handles the unique animation problems for a 'player_token' drawable."""
    def __init__(self, persistent_state, variable_state):
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.z_formula = self.persistent_state["pers_z_formulas"]["player_token"]
        # Store the r-value from the start of the segment for comparison later
        self.previous_segment_r = 0

    def get_world_pixel(self, q, r):
        """Converts hex to a world-space pixel (ignoring camera)."""
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_to_pixel(q, r, self.persistent_state, temp_state)

    def get_hex_geom(self, q, r):
        """Gets hex geometry in world-space pixels (ignoring camera)."""
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_geometry(q, r, self.persistent_state, temp_state)

    def get_edge_center(self, geom, adjacent_coord):
        """Finds the pixel center of the edge shared with an adjacent hex."""
        try:
            edge_dir = [d for d, n in geom['neighbors'].items() if n == adjacent_coord][0]
            edge_corners = geom['edges'][self.persistent_state['pers_edge_index'][edge_dir]]
            return ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)
        except (IndexError, KeyError):
            return geom['center']

    def on_segment_start(self, target_dict, current_coord, next_coord):
        """Called when a new travel segment begins."""
        current_r = current_coord[1]
        next_r = next_coord[1]

        # Store the starting r-value for the 'on_complete' check
        self.previous_segment_r = current_r

        # SCENARIO 1: Moving DOWN (to a higher r and Z-value)
        # Update the Z-value EARLY to avoid clipping behind the destination.
        if next_r > current_r:
            target_dict['z'] = self.z_formula(next_r)

    def on_segment_complete(self, target_dict, completed_coord):
        """Called when a travel segment is finished."""
        # First, update the token's official q,r coordinates
        target_dict['q'] = completed_coord[0]
        target_dict['r'] = completed_coord[1]

        completed_r = completed_coord[1]

        # SCENARIO 2: Moving UP (to a lower r and Z-value)
        # Update the Z-value LATE (upon arrival) to prevent the token's tail
        # from clipping through the tile it just left.
        if completed_r < self.previous_segment_r:
            target_dict['z'] = self.z_formula(completed_r)