# ui/ui_dev_panel.py
# A specific UI panel for housing developer tools.

import pygame
from .ui_components import BasePanel, Button, create_grid_placements, assemble_organic_panel, UI_ELEMENT_PADDING
DEBUG = True

# ──────────────────────────────────────────────────
# Panel Class
# ──────────────────────────────────────────────────

class DevPanel(BasePanel):
    """A dynamically-sized panel in the top right for developer actions."""
    def __init__(self, persistent_state, assets_state, tile_objects):
        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.tile_objects = tile_objects 
        self.drawable_key = "ui_dev_panel"

        # 📐 Dynamic Layout Calculation
        grid_dims = (1, 1)
        button_asset = self.assets_state["ui_assets"]["buttons"].get("save_map")
        button_size = button_asset["normal"].get_size() if button_asset else (175, 59)
        # Use our global constant for the panel's internal margins
        panel_width = button_size[0] + (UI_ELEMENT_PADDING[0] * 2)
        panel_height = button_size[1] + (UI_ELEMENT_PADDING[1] * 2)
        
        # 🎨 Panel and Element Creation
        self.surface = assemble_organic_panel(panel_width, panel_height, self.assets_state)
        screen_w, _ = self.persistent_state["pers_screen"].get_size()
        self.rect = self.surface.get_rect(topright=(screen_w - 20, 20))
        placements = create_grid_placements(self.surface.get_rect(), grid_dims, button_size)
        
        # Instantiate the button, using a lambda to pass this panel instance to the action callback
        self.save_button = Button(placements[0], "save_map", lambda: export_map_action(self), self.assets_state)
        
        self.elements = [self.save_button]

    def handle_events(self, events, mouse_pos):
        """Passes events and a localized mouse position to all interactive elements."""
        
        # Convert global mouse position to be relative to this panel's top-left corner
        local_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        
        for element in self.elements:
            element.handle_events(events, local_mouse_pos)

    def update(self, notebook):
        """Draws child elements and then publishes the final panel to the notebook."""
        for element in self.elements:
            element.draw(self.surface)
        super().update(notebook)

# ──────────────────────────────────────────────────
# 🎬 Action Callbacks
# ──────────────────────────────────────────────────
# This section encapsulates all of the action callbacks of this script's panel buttons

import math
import pygame
from renderer import render_giant_z_pot
from shared_helpers import hex_to_pixel

def export_map_action(panel):
    """Handles the entire map export process when called by a UI element."""
    print(f"[{panel.drawable_key}] ✅ Action triggered, starting map export...")
    MAP_RENDER_SCALE = 0.2

    try:
        # 🗺️ Part 1: Calculate map dimensions
        min_x, max_x = math.inf, -math.inf
        min_y, max_y = math.inf, -math.inf
        variable_state_calc = {"var_current_zoom": MAP_RENDER_SCALE, "var_render_offset": (0, 0)}

        for q, r in panel.tile_objects.keys():
            px, py = hex_to_pixel(q, r, panel.persistent_state, variable_state_calc)
            min_x = min(min_x, px - (panel.persistent_state["pers_tile_canvas_w"] * MAP_RENDER_SCALE) / 2)
            max_x = max(max_x, px + (panel.persistent_state["pers_tile_canvas_w"] * MAP_RENDER_SCALE) / 2)
            min_y = min(min_y, py - (panel.persistent_state["pers_tile_canvas_h"] * MAP_RENDER_SCALE) / 2)
            max_y = max(max_y, py + (panel.persistent_state["pers_tile_canvas_h"] * MAP_RENDER_SCALE) / 2)
        
        img_width = int(max_x - min_x)
        img_height = int(max_y - min_y)
        render_offset = (-min_x, -min_y)

        # 🎨 Part 2: Render the map to a new surface
        variable_state_render = {"var_current_zoom": MAP_RENDER_SCALE, "var_render_offset": render_offset}
        map_surface = pygame.Surface((img_width, img_height))
        map_surface.fill((0, 0, 0))
        
        render_giant_z_pot(map_surface, panel.tile_objects, {}, panel.persistent_state, panel.assets_state, variable_state_render)
        
        # 💾 Part 3: Save the final image
        pygame.image.save(map_surface, "map_render_action.png")
        print(f"[{panel.drawable_key}] ✅ Successfully exported map to 'map_render_action.png'.")

    except Exception as e:
        if DEBUG: print(f"[{panel.drawable_key}] ❌ ERROR: Failed to generate map render: {e}")