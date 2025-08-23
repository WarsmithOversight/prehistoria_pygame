import pygame
from shared_helpers import pixel_to_hex

class MapInteractor:
    """
    Handles all non-UI input for the game world.
    """
    def __init__(self):
        self.hovered_tile = None
        self.selected_tile = None
        
        # State variables for panning
        self.is_panning = False
        self.last_mouse_pos = (0, 0)

    def handle_events(self, events, mouse_pos, tile_objects, persistent_state, variable_state):
        """
        Processes all events for hovering, selecting, and panning.
        Returns the pixel delta for any map panning that occurred this frame.
        """
        # ──────────────────────────────────────────────────
        # ⚙️ Event Processing: Just for turning panning on/off
        # ──────────────────────────────────────────────────
        # The event loop is now only used to flip the is_panning switch.
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.is_panning = True
                self.last_mouse_pos = mouse_pos
                
                # Tile selection still happens on the initial click
                if self.hovered_tile and self.hovered_tile.passable:
                    self.selected_tile = self.hovered_tile
                    print(f"[Interactor] ✅ Selected tile: {self.selected_tile}")

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_panning = False
    
        # ──────────────────────────────────────────────────
        # ⚙️ State Processing: Calculate the pan delta
        # ──────────────────────────────────────────────────
        pan_delta = (0, 0)
        # This logic now runs once per frame, outside the event loop.
        if self.is_panning:
            # Use the most current mouse position for the calculation.
            current_mouse_pos = mouse_pos
            dx = current_mouse_pos[0] - self.last_mouse_pos[0]
            dy = current_mouse_pos[1] - self.last_mouse_pos[1]
            pan_delta = (dx, dy)
            
            # CRITICAL: Update the last mouse position for the next frame.
            self.last_mouse_pos = current_mouse_pos
            
        # ──────────────────────────────────────────────────
        # 🎨 Update Hover State
        # ──────────────────────────────────────────────────
        if self.hovered_tile:
            self.hovered_tile.hovered = False
            self.hovered_tile = None

        if not self.is_panning:
            hovered_coord = pixel_to_hex(mouse_pos, persistent_state, variable_state)
            tile = tile_objects.get(hovered_coord)
            if tile:
                tile.hovered = True
                self.hovered_tile = tile
        
        # Return the final calculated movement delta.
        return pan_delta