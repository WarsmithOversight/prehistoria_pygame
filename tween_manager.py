# tween_manager.py
# A flexible animation system using an orchestrator and composable "puzzle pieces".

import math
from shared_helpers import hex_to_pixel, hex_geometry, get_point_on_bezier_curve

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True # Set to True to get print statements from tweens

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
        self.active_tweens = []
        self.persistent_state = persistent_state
        self.variable_state = variable_state

        # ✨ MAPS: The animation map is now much simpler.
        self.ANIMATION_MAP = {
            'value': ValueTween, # The new, powerful, all-purpose tween
            'travel': TravelTween,
            'bob': BobTween,
        }
        self.UPDATER_MAP = {
            'player_token': PlayerTokenUpdater,
            'generic': GenericUpdater, # A new, more flexible updater
            'camera_offset': OffsetUpdater,
            'rect_position': RectPositionUpdater,
        }

    def add_tween(self, target_dict, animation_type, drawable_type='generic', on_complete=None, **kwargs):
        animation_class = self.ANIMATION_MAP.get(animation_type)
        if not animation_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Animation type '{animation_type}' not found.")
            return

        updater_class = self.UPDATER_MAP.get(drawable_type)
        if not updater_class:
            if DEBUG: print(f"[TweenManager] ⚠️ Updater for drawable type '{drawable_type}' not found.")
            return

        updater = updater_class(self.persistent_state, self.variable_state)
        tween_instance = animation_class(target_dict, updater, on_complete, **kwargs)
        self.active_tweens.append(tween_instance)
        if DEBUG: print(f"[TweenManager] ✅ Tween created: '{animation_type}' on '{drawable_type}'.")

    def update(self, dt):
        """Updates all active tweens and removes any that have finished."""
        for tween in self.active_tweens:
            tween.update(dt)
        self.active_tweens = [t for t in self.active_tweens if not t.is_finished]

    def remove_tweens_by_target(self, target_dict):
        """Finds and removes all active tweens that are acting on a specific target dictionary."""
        initial_count = len(self.active_tweens)
        self.active_tweens = [t for t in self.active_tweens if t.target_dict is not target_dict]
        if DEBUG: print(f"[TweenManager] ✅ Removed {initial_count - len(self.active_tweens)} tweens for target.")

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
        raise NotImplementedError

    def finish(self):
        """Marks the tween as finished and calls the completion callback."""
        if not self.is_finished:
            self.is_finished = True
            if self.on_complete:
                self.on_complete()

# ──────────────────────────────────────────────────
# 🎬 Tween Types
# ──────────────────────────────────────────────────

class ValueTween(Tween):
    """
    Animates any key on a target dictionary. Can handle numbers, tuples, or lists of numbers.
    This powerful tween replaces the old PanTween and FadeTween.
    """
    def __init__(self, target_dict, updater, on_complete, key_to_animate, start_val, end_val, duration, easing_func=ease_in_out_cubic):
        super().__init__(target_dict, updater, on_complete)
        self.key = key_to_animate
        self.start_val = start_val
        self.end_val = end_val
        self.duration = max(0.01, duration)
        self.easing_func = easing_func
        self.timer = 0
        self.updater.on_start(self.target_dict, self.key, self.start_val)

    def update(self, dt):
        if self.is_finished: return

        self.timer += dt
        progress = min(1.0, self.timer / self.duration)
        eased_progress = self.easing_func(progress)
        
        # ✨ LOGIC: Smart interpolation based on value type
        current_val = None
        if isinstance(self.start_val, (int, float)):
            # Handle single numbers (replaces FadeTween)
            current_val = self.start_val + (self.end_val - self.start_val) * eased_progress
        elif isinstance(self.start_val, (tuple, list)):
            # Handle tuples/lists (replaces PanTween)
            new_vals = []
            for i in range(len(self.start_val)):
                start = self.start_val[i]
                end = self.end_val[i]
                interpolated = start + (end - start) * eased_progress
                new_vals.append(interpolated)
            current_val = type(self.start_val)(new_vals)

        if current_val is not None:
            self.updater.on_update(self.target_dict, self.key, current_val)

        if progress >= 1.0:
            self.updater.on_update(self.target_dict, self.key, self.end_val)
            self.finish()

class TravelTween(Tween):
    def __init__(self, target_dict, updater, on_complete, path, speed_hps):
        super().__init__(target_dict, updater, on_complete)
        self.speed = speed_hps
        self.path_hex = []
        self.path_pixels = []
        self.current_segment = 0
        self.progress = 0.0
        self.target_dict['pixel_pos'] = self.updater.get_world_pixel(target_dict['q'], target_dict['r'])
        self._initialize_path(path)
        if self.is_finished: return
        self._setup_segment()

    def _initialize_path(self, path):
        if not path or len(path) < 2: self.finish(); return
        is_hex_path = isinstance(path[0], tuple) and len(path[0]) == 2
        if is_hex_path: self.path_hex = path
        else: self.path_pixels = path
    
    def _setup_segment(self):
        path_length = len(self.path_hex)
        is_first = self.current_segment == 0
        is_final = self.current_segment == path_length - 1
        current_coord = self.path_hex[self.current_segment]
        prev_coord = self.path_hex[self.current_segment - 1] if not is_first else None
        next_coord = self.path_hex[self.current_segment + 1] if not is_final else None        
        geom = self.updater.get_hex_geom(current_coord[0], current_coord[1])
        self.p0 = geom['center'] if is_first else self.updater.get_edge_center(geom, prev_coord)
        self.p2 = geom['center'] if is_final else self.updater.get_edge_center(geom, next_coord)
        self.p1 = geom['center']
        if next_coord: self.updater.on_segment_start(self.target_dict, current_coord, next_coord)
    
    def update(self, dt):
        if self.is_finished: return
        self.progress = min(1.0, self.progress + (self.speed * dt))
        new_pixel_pos = get_point_on_bezier_curve(self.p0, self.p1, self.p2, self.progress)
        self.target_dict['pixel_pos'] = new_pixel_pos
        if self.progress >= 1.0:
            self.updater.on_segment_complete(self.target_dict, self.path_hex[self.current_segment])
            self.current_segment += 1
            if self.current_segment >= len(self.path_hex):
                self.finish()
            else:
                self.progress = 0.0
                self._setup_segment()

class BobTween(Tween):
    """
    A looping tween that creates a vertical "bobbing" motion on a drawable
    by modifying its 'local_render_offset'.
    """
    def __init__(self, target_dict, updater, on_complete, amplitude, period):
        super().__init__(target_dict, updater, on_complete)
        self.amplitude = amplitude
        self.period = max(0.01, period)
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        vertical_offset = self.amplitude * math.sin(2 * math.pi * self.timer / self.period)
        self.updater.on_update(self.target_dict, 'local_render_offset', (0, vertical_offset))

# ──────────────────────────────────────────────────
# 🎬 Tween Updaters (How Tweens Affect Objects)
# ──────────────────────────────────────────────────

class RectPositionUpdater:
   """A specialized updater that sets the 'topleft' attribute of a pygame.Rect object."""
   def __init__(self, persistent_state, variable_state): pass
   def on_start(self, target_rect, key, value): target_rect.topleft = value
   def on_update(self, target_rect, key, value): target_rect.topleft = value

class OffsetUpdater:
    """A specialized updater for a camera offset."""
    def __init__(self, persistent_state, variable_state): pass
    def on_start(self, target, key, value): setattr(target, key, list(value))
    def on_update(self, target, key, value): setattr(target, key, list(value))

class GenericUpdater:
    """A generic updater that simply sets a key on the target dictionary."""
    def __init__(self, persistent_state, variable_state): pass
    def on_start(self, target_dict, key, value): target_dict[key] = value
    def on_update(self, target_dict, key, value): target_dict[key] = value

class PlayerTokenUpdater:
    def __init__(self, persistent_state, variable_state):
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.z_formula = self.persistent_state["pers_z_formulas"]["player_token"]
        self.previous_segment_r = 0

    def get_world_pixel(self, q, r):
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_to_pixel(q, r, self.persistent_state, temp_state)
    
    def get_hex_geom(self, q, r):
        temp_state = {"var_current_zoom": 1.0, "var_render_offset": (0, 0)}
        return hex_geometry(q, r, self.persistent_state, temp_state)

    def get_edge_center(self, geom, adjacent_coord):
        try:
            edge_dir = [d for d, n in geom['neighbors'].items() if n == adjacent_coord][0]
            edge_corners = geom['edges'][self.persistent_state['pers_edge_index'][edge_dir]]
            return ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)
        except (IndexError, KeyError):
            return geom['center']

    def on_segment_start(self, target_dict, current_coord, next_coord):
        current_r, next_r = current_coord[1], next_coord[1]
        self.previous_segment_r = current_r
        if next_r > current_r:
            target_dict['z'] = self.z_formula(next_r)    
    
    def on_segment_complete(self, target_dict, completed_coord):
        target_dict['q'], target_dict['r'] = completed_coord[0], completed_coord[1]
        completed_r = completed_coord[1]
        if completed_r < self.previous_segment_r:
            target_dict['z'] = self.z_formula(completed_r)