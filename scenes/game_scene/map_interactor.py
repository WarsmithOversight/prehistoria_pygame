# scenes/game_scene/map_interactor.py
# The specialist for all direct user interaction with the hex grid.
# A "sensory organ" for the map.

import pygame
from shared_helpers import pixel_to_hex

# ────────────────────────────────────────────────── #
# 🎨 Config & Constants
# ────────────────────────────────────────────────── #
DEBUG = False
# ✨ NEW: Set this to the string name of any tile attribute to display it.
# Examples: "final_elevation", "topographical_scale", "terrain", "river_data", "coord"
# Set to None to disable the overlay.
DEBUG_ATTRIBUTE_TO_SHOW = "topographic_scale"

# ──────────────────────────────────────────────────
# Input Handler
# ──────────────────────────────────────────────────

class MapInteractor:
    """
    Handles all direct user interaction with the hex grid, including
    mouse hovering, panning, and clicking.
    """
    def __init__(self, event_bus, notebook, tile_objects, persistent_state, variable_state):
        # ⚙️ Store references to core systems and state
        self.event_bus = event_bus
        self.notebook = notebook
        self.tile_objects = tile_objects
        self.persistent_state = persistent_state
        self.variable_state = variable_state

        # 🚩 State Management
        self.hovered_hex = None
        self._is_panning = False
        self._pan_start_pos = None
        # ✨ NEW: Keep track of the keys for our debug drawables
        self._debug_keys = set()

    def update(self, mouse_pos):
        """A per-frame update loop for continuous actions like hovering and debug overlays."""
        # 🗺️ Get the current hex coordinate under the mouse.
        hex_coord = pixel_to_hex(mouse_pos, self.persistent_state, self.variable_state)

        # 🛑 If the hovered hex hasn't changed, do nothing.
        if hex_coord != self.hovered_hex:
            # 🎨 De-highlight the old tile
            if self.hovered_hex and self.tile_objects.get(self.hovered_hex):
                self.tile_objects[self.hovered_hex].hovered = False
            
            # ✨ Highlight the new tile
            if hex_coord and self.tile_objects.get(hex_coord):
                self.tile_objects[hex_coord].hovered = True
            
            # 💾 Update the state and announce the change.
            self.hovered_hex = hex_coord
            self.event_bus.post("HOVERED_HEX_CHANGED", {"coord": self.hovered_hex})
        
        # ✨ NEW: Call the debug overlay manager
        self._update_debug_overlay()


    def _update_debug_overlay(self):
        """Creates, updates, or removes debug text drawables in the notebook."""
        # 🛑 If debugging is off, ensure all debug text is removed.
        if not DEBUG or not DEBUG_ATTRIBUTE_TO_SHOW:
            if self._debug_keys:
                for key in self._debug_keys:
                    if key in self.notebook:
                        del self.notebook[key]
                self._debug_keys.clear()
            return

        # ✍️ If debugging is on, update the text for every tile.
        new_keys = set()
        for coord, tile in self.tile_objects.items():
            key = f"debug_text_{coord[0]}_{coord[1]}"
            new_keys.add(key)

            # Get the attribute value, providing 'N/A' if it doesn't exist.
            value = getattr(tile, DEBUG_ATTRIBUTE_TO_SHOW, 'N/A')
            
            # For dictionaries, we might want a cleaner representation.
            if isinstance(value, dict):
                # Example for river_data: show only the bitmask
                if DEBUG_ATTRIBUTE_TO_SHOW == 'river_data' and 'bitmask' in value:
                    value = value['bitmask']
                else: # Otherwise, just convert the whole dict to a string
                    value = str(value)
            
            text_to_display = str(value)

            # Create or update the drawable in the notebook.
            self.notebook[key] = {
                'type': 'debug_tile_text',
                'q': coord[0],
                'r': coord[1],
                'text': text_to_display,
                'z': self.persistent_state["pers_z_formulas"]["debug_text"](coord[1])
            }
        
        # 🧹 Clean up any old keys that are no longer used.
        keys_to_remove = self._debug_keys - new_keys
        for key in keys_to_remove:
            if key in self.notebook:
                del self.notebook[key]
        self._debug_keys = new_keys


    def handle_events(self, events, mouse_pos):
        """
        Processes user input events to determine panning, hovering, and clicks.
        Returns a (pan_vector, clicked_coord) tuple.
        """
        pan_vector = (0, 0)
        clicked_coord = None
        
        # ──────────────────────────────────────────────────
        # 🖐️ Pan Logic
        # ──────────────────────────────────────────────────
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3: # Right-click to start panning
                self._is_panning = True
                self._pan_start_pos = mouse_pos
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self._is_panning = False
                self._pan_start_pos = None
            if event.type == pygame.MOUSEMOTION and self._is_panning:
                pan_vector = (event.pos[0] - self._pan_start_pos[0], event.pos[1] - self._pan_start_pos[1])
                self._pan_start_pos = event.pos

        # ────────────────────────────────────────────────── #
        # 👆 Click Logic
        # ────────────────────────────────────────────────── #

        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1: # Left-click to select/move
                if self.tile_objects.get(self.hovered_hex):
                    clicked_coord = self.hovered_hex

        return pan_vector, clicked_coord