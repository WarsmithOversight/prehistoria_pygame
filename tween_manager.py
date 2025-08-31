# tween_manager.py
# A flexible animation system using an orchestrator and composable "puzzle pieces".

import pygame
from shared_helpers import hex_to_pixel, hex_geometry, get_point_on_bezier_curve

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = False

def ease_in_out_cubic(t):
    """A classic easing function for smooth acceleration and deceleration."""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

# ──────────────────────────────────────────────────
# ⚙️ Orchestrator (The TweenManager)
# ──────────────────────────────────────────────────

class TweenManager:
    """
    Interprets animation calls, assembles the correct tween and updater
    "puzzle pieces", and manages all active animation instances.
    """
    def __init__(self, persistent_state, variable_state):

        # Initializes a list to hold all currently running animations
        self.active_tweens = []

        # Stores references to the game's persistent and variable state
        self.persistent_state = persistent_state
        self.variable_state = variable_state

        # Maps animation type strings to their corresponding classes
        self.ANIMATION_MAP = {
            'travel': TravelTween,
            'fade': FadeTween,
            'pan': PanTween,
        }

        # Maps drawable type strings to their corresponding updater classes
        self.UPDATER_MAP = {
            'player_token': PlayerTokenUpdater,
            'value': ValueUpdater,
            'camera_offset': OffsetUpdater,
        }

    def add_tween(self, target_dict, animation_type, drawable_type='value', on_complete=None, **kwargs):
        
        # Retrieves the correct animation type
        animation_class = self.ANIMATION_MAP.get(animation_type)
        if not animation_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Animation type '{animation_type}' not found.")
            return

        # Retrieves the correct updater type
        updater_class = self.UPDATER_MAP.get(drawable_type)
        if not updater_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Updater for drawable type '{drawable_type}' not found.")
            return

        # Creates an instance of the chosen updater, which handles how the animation affects a specific object
        updater = updater_class(self.persistent_state, self.variable_state)
        
        # Creates an instance of the tween class, passing in the target, updater, and other parameters
        tween_instance = animation_class(target_dict, updater, on_complete, **kwargs)
        
        # Adds the newly created tween to the list of active animations
        self.active_tweens.append(tween_instance)
        if DEBUG: print(f"[TweenManager] ✅ Tween created: '{animation_type}' on '{drawable_type}'.")

    def update(self, dt):
        """Updates all active tweens and removes any that have finished."""
        
        # Iterates through all active tweens and calls their update method
        for tween in self.active_tweens:
            tween.update(dt)
        
        # Filters out any tweens that have completed their animation
        self.active_tweens = [t for t in self.active_tweens if not t.is_finished]

# ──────────────────────────────────────────────────
# ⚙️ Base Tween Class
# ──────────────────────────────────────────────────

class Tween:
    """A base class that all animation types will inherit from."""
    def __init__(self, target_dict, updater, on_complete):
        
        # Stores a reference to the dictionary that will be modified by the tween
        self.target_dict = target_dict
        
        # Stores a reference to the updater object that applies changes to the target
        self.updater = updater
        
        # Stores a reference to an optional function to be called on completion
        # [ ] TODO: I think this allows me to do stuff on triggered on an animation
        # being completed.
        self.on_complete = on_complete

        # A flag to indicate if the animation has finished
        self.is_finished = False

    def update(self, dt):
        # A placeholder method that must be implemented by subclasses
        raise NotImplementedError

    def finish(self):
        """Marks the tween as finished and calls the completion callback."""

        # Sets the finished flag to true, ensuring the animation only completes once
        if not self.is_finished: # Prevent multiple calls
            self.is_finished = True

            # Calls the completion callback if one was provided
            if self.on_complete:
                self.on_complete()

# ──────────────────────────────────────────────────
# 🎬 Tween Types
# ──────────────────────────────────────────────────

class PanTween(Tween):
    """Animates an object's 'offset' attribute from a start to an end tuple."""
    def __init__(self, target_dict, updater, on_complete, start_val, end_val, duration):
        super().__init__(target_dict, updater, on_complete)
        self.start_x, self.start_y = start_val
        self.end_x, self.end_y = end_val
        self.duration = max(0.01, duration)
        self.timer = 0

        # Set the initial state
        self.updater.on_start(self.target_dict, (self.start_x, self.start_y))

    def update(self, dt):
        if self.is_finished: return

        self.timer += dt
        progress = min(1.0, self.timer / self.duration)

        # Apply the easing function for smooth motion
        eased_progress = ease_in_out_cubic(progress)

        # Interpolate both x and y coordinates
        current_x = self.start_x + (self.end_x - self.start_x) * eased_progress
        current_y = self.start_y + (self.end_y - self.start_y) * eased_progress

        # Update the target via the updater
        self.updater.on_update(self.target_dict, (current_x, current_y))

        if progress >= 1.0:
            # Snap to the final position to avoid floating point inaccuracies
            self.updater.on_update(self.target_dict, (self.end_x, self.end_y))
            self.finish()

class FadeTween(Tween):
    """Animates a 'value' key in the target dictionary from a start to an end value."""
    def __init__(self, target_dict, updater, on_complete, start_val, end_val, duration):
        
        # Calls the parent class's constructor
        super().__init__(target_dict, updater, on_complete)

        # Stores the start, end, and duration values for the fade animation
        self.start_val = start_val
        self.end_val = end_val

        # Ensures the duration is a non-zero value to prevent division by zero errors
        self.duration = max(0.01, duration)

        # Initializes a timer to track the animation's progress
        self.timer = 0

        # Calls the updater to set the initial value of the target
        self.updater.on_start(self.target_dict, 'value', self.start_val)

    def update(self, dt):
        
        # Exits the update loop if the animation is already finished
        if self.is_finished: return

        # Increments the timer by the elapsed time since the last frame
        self.timer += dt
        
        # Calculates the animation's progress as a value from 0.0 to 1.0
        progress = min(1.0, self.timer / self.duration)

        # Calculates the current value based on the progress using linear interpolation
        current_val = self.start_val + (self.end_val - self.start_val) * progress

        # Applies the new value to the target dictionary via the updater
        self.updater.on_update(self.target_dict, 'value', current_val)

        # Only prints debug information if DEBUG is enabled and the animation is not at 100% progress
        if DEBUG and progress < 1.0:
            print(f"[FadeTween] 🐞 dt: {dt:.4f}, timer: {self.timer:.2f}/{self.duration:.2f}, progress: {progress:.2%}, current_val: {current_val:.1f}")

        # Checks if the animation has reached or exceeded its duration
        if progress >= 1.0:

            # Snaps the target to the final end value to avoid floating point inaccuracies
            self.updater.on_update(self.target_dict, 'value', self.end_val) # Snap to final value
            
            # Marks the animation as finished
            self.finish()

class TravelTween(Tween):
    def __init__(self, target_dict, updater, on_complete, path, speed_hps):

        # Calls the parent class's constructor
        super().__init__(target_dict, updater, on_complete)

        # Stores the speed of travel in hexes per second
        self.speed = speed_hps

        # Initializes lists for the hex and pixel path segments
        self.path_hex = []
        self.path_pixels = []

        # Initializes counters for the current segment and progress along that segment
        self.current_segment = 0
        self.progress = 0.0

        # Sets the initial pixel position of the target based on its hex coordinates
        self.target_dict['pixel_pos'] = self.updater.get_world_pixel(target_dict['q'], target_dict['r'])
        
        # Populates the path lists and finishes if the path is invalid
        self._initialize_path(path)

        # Exits the constructor if the path was invalid and the tween was finished
        if self.is_finished: return
        # Sets up the first travel segment
        self._setup_segment()

    def _initialize_path(self, path):

        # Checks for an empty or single-point path and finishes the tween if found
        if not path or len(path) < 2: self.finish(); return
        
        # Determines if the path is a list of hex coordinates
        is_hex_path = isinstance(path[0], tuple) and len(path[0]) == 2
        
        # Assigns the path to the appropriate list
        if is_hex_path: self.path_hex = path
        else: self.path_pixels = path
    
    def _setup_segment(self):

        # Gets the total number of hexes in the path
        path_length = len(self.path_hex)

        # Checks if this is the first or final segment of the path
        is_first = self.current_segment == 0
        is_final = self.current_segment == path_length - 1

        # Gets the current, previous, and next hex coordinates from the path
        current_coord = self.path_hex[self.current_segment]
        prev_coord = self.path_hex[self.current_segment - 1] if not is_first else None
        next_coord = self.path_hex[self.current_segment + 1] if not is_final else None        
        
        # Gets the geometric data for the current hex
        geom = self.updater.get_hex_geom(current_coord[0], current_coord[1])
        
        # Determines the starting point of the Bezier curve segment
        self.p0 = geom['center'] if is_first else self.updater.get_edge_center(geom, prev_coord)
        
        # Determines the end point of the Bezier curve segment
        self.p2 = geom['center'] if is_final else self.updater.get_edge_center(geom, next_coord)
        
        # Sets the control point of the Bezier curve to the center of the current hex
        self.p1 = geom['center']

        # Notifies the updater that a new segment is starting, if a next hex exists
        if next_coord: self.updater.on_segment_start(self.target_dict, current_coord, next_coord)
    
    def update(self, dt):

        # Exits the update loop if the animation is finished
        if self.is_finished: return

        # Increments the progress along the current path segment
        self.progress = min(1.0, self.progress + (self.speed * dt))

        # Calculates the new pixel position on the Bezier curve
        new_pixel_pos = get_point_on_bezier_curve(self.p0, self.p1, self.p2, self.progress)
        
        # Updates the target dictionary with the new pixel position
        self.target_dict['pixel_pos'] = new_pixel_pos
    
        # Checks if the current segment has finished
        if self.progress >= 1.0:
            
            # Notifies the updater that the segment has been completed
            self.updater.on_segment_complete(self.target_dict, self.path_hex[self.current_segment])
            
            # Moves to the next segment
            self.current_segment += 1
            
            # Checks if all segments in the path have been completed
            if self.current_segment >= len(self.path_hex):
            
                # Marks the animation as finished
                self.finish()
            else:
            
                # Resets progress and sets up the next segment
                self.progress = 0.0
                self._setup_segment()

# ──────────────────────────────────────────────────
# 🎬 Tween Targets
# ──────────────────────────────────────────────────

class OffsetUpdater:
    """A specialized updater for a 2-element list, like a camera offset."""
    def __init__(self, persistent_state, variable_state): pass

    def on_start(self, target, value): target.offset = list(value)

    def on_update(self, target, value): target.offset = list(value)

class ValueUpdater:
    """A generic updater that simply sets a key on the target dictionary."""
    def __init__(self, persistent_state, variable_state): pass

    # Sets the initial value on the target dictionary
    def on_start(self, target_dict, key, value): target_dict[key] = value

    # Updates the value on the target dictionary during the animation
    def on_update(self, target_dict, key, value): target_dict[key] = value

class PlayerTokenUpdater:
    
    def __init__(self, persistent_state, variable_state):
        
        # Stores references to the game's persistent and variable state
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        
        # Retrieves the z-formula for player tokens from the persistent state
        self.z_formula = self.persistent_state["pers_z_formulas"]["player_token"]
        
        # Stores the row of the previous path segment for elevation calculations
        self.previous_segment_r = 0

    def get_world_pixel(self, q, r):

        # Calculates the world pixel coordinates from hex coordinates
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_to_pixel(q, r, self.persistent_state, temp_state)
    
    def get_hex_geom(self, q, r):

        # Retrieves the geometric data for a specific hex
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_geometry(q, r, self.persistent_state, temp_state)

    def get_edge_center(self, geom, adjacent_coord):
        
        # Calculates the center point of the edge shared with an adjacent hex
        try:
            
            # Finds the direction of the adjacent hex
            edge_dir = [d for d, n in geom['neighbors'].items() if n == adjacent_coord][0]
            
            # Gets the coordinates of the two corners that define the edge
            edge_corners = geom['edges'][self.persistent_state['pers_edge_index'][edge_dir]]
            
            # Returns the midpoint of the edge
            return ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)
        except (IndexError, KeyError):
            
            # Returns the hex center if the adjacent hex is not a neighbor
            return geom['center']

    def on_segment_start(self, target_dict, current_coord, next_coord):
        
        # Gets the row of the current and next hexes
        current_r = current_coord[1]
        next_r = next_coord[1]
        
        # Stores the current row to check for downward movement later
        self.previous_segment_r = current_r
        
        # Updates the z-index to the next hex's elevation if the token is moving to a higher row
        if next_r > current_r:
            target_dict['z'] = self.z_formula(next_r)    
    
    def on_segment_complete(self, target_dict, completed_coord):
        
        # Updates the token's hex coordinates to the completed hex
        target_dict['q'] = completed_coord[0]
        target_dict['r'] = completed_coord[1]
        
        # Gets the row of the completed hex
        completed_r = completed_coord[1]
        
        # Updates the z-index to the current hex's elevation if the token is moving to a lower row
        if completed_r < self.previous_segment_r:
            target_dict['z'] = self.z_formula(completed_r)