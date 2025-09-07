# scenes/game_scene/map_interactor.py
# The specialist for all direct user interaction with the hex grid.
# A "sensory organ" for the map.

import pygame
from shared_helpers import pixel_to_hex
DEBUG = False

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

    def update(self, mouse_pos):
        """A per-frame update loop for continuous actions like hovering."""
        # 🗺️ Get the current hex coordinate under the mouse.
        hex_coord = pixel_to_hex(mouse_pos, self.persistent_state, self.variable_state)

        # 🛑 If the hovered hex hasn't changed, do nothing.
        if hex_coord == self.hovered_hex:
            return
        
        # 🎨 De-highlight the old tile
        if self.hovered_hex and self.tile_objects.get(self.hovered_hex):
            self.tile_objects[self.hovered_hex].hovered = False
        
        # ✨ Highlight the new tile
        if hex_coord and self.tile_objects.get(hex_coord):
            self.tile_objects[hex_coord].hovered = True
        
        # 💾 Update the state and announce the change.
        self.hovered_hex = hex_coord
        self.event_bus.post("HOVERED_HEX_CHANGED", {"coord": self.hovered_hex})

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
                    if DEBUG: print(f"[Interactor] ✅ Click detected on hex: {clicked_coord}")

        return pan_vector, clicked_coord
