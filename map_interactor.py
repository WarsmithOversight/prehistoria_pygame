# In map_interactor.py
# (I'm providing a complete, clean version of this class for clarity)

import pygame
from shared_helpers import pixel_to_hex

class MapInteractor:
    """Handles all non-UI input for the game world."""
    def __init__(self):
        self.hovered_tile = None
        self.is_panning = False
        self.last_mouse_pos = (0, 0)

    def handle_events(self, events, mouse_pos, tile_objects, persistent_state, variable_state):
        """Processes events and returns pan_delta and any clicked coordinate."""
        # Reset click and pan state for this frame
        pan_delta = (0, 0)
        clicked_coord = None

        # --- Event Processing ---
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.is_panning = True
                self.last_mouse_pos = mouse_pos
                
                # If we are not panning, register a click on the hovered tile
                if self.hovered_tile:
                    clicked_coord = (self.hovered_tile.q, self.hovered_tile.r)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_panning = False

        # --- Pan Calculation ---
        if self.is_panning:
            current_mouse_pos = mouse_pos
            dx = current_mouse_pos[0] - self.last_mouse_pos[0]
            dy = current_mouse_pos[1] - self.last_mouse_pos[1]
            pan_delta = (dx, dy)
            self.last_mouse_pos = current_mouse_pos
            
            # If the mouse moved significantly, it was a pan, not a click
            if abs(dx) > 2 or abs(dy) > 2:
                clicked_coord = None
            
        # --- Hover State Update ---
        if self.hovered_tile:
            self.hovered_tile.hovered = False
            self.hovered_tile = None

        if not self.is_panning:
            hovered_coord = pixel_to_hex(mouse_pos, persistent_state, variable_state)
            tile = tile_objects.get(hovered_coord)
            if tile:
                tile.hovered = True
                self.hovered_tile = tile
        
        # Return both values to the main loop
        return pan_delta, clicked_coord