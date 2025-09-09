# scenes/game_scene/ui/ui_extinction_panel.py
# A simple panel to display the game over message.

import pygame
from ui.ui_base_panel_components import BasePanel, assemble_organic_panel
from ui.ui_dimensions import get_panel_dimensions, UI_ELEMENT_PADDING 
from ui.ui_generic_components import UITextBlock
from ui.ui_font_and_styles import get_style

class UIExtinctionPanel(BasePanel):
    """A UI panel that displays the 'extinction' game over message."""
    def __init__(self, persistent_state, assets_state):
        # ──────────────────────────────────────────────────
        # ⚙️ Core Setup
        # ──────────────────────────────────────────────────
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "extinction_panel"

        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────
        self.element_definitions = {
                    "extinction": {
                        "type": "text_block",
                        "content": (
                            "Your species has gone extinct.\n"
                            "\n"
                            "Better luck next time!"
                        ),
                        "style": get_style("paragraph_text"),
                        "properties": {"max_width": 550}
                    }
                }


        # ──────────────────────────────────────────────────
        # 📐 Layout, Assembly, & Positioning
        # ──────────────────────────────────────────────────

        self.layout_blueprint = [
            [{"id": "extinction"}]
        ]


        # 1. Calculate final dimensions for the panel and all its child elements
        self.dims = get_panel_dimensions(
            "WelcomePanel", # Pass a unique name for the panel here
            self.element_definitions,
            self.layout_blueprint,
            self.assets_state
        )

        # 2. Assemble the main panel surface
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        screen_rect = self.persistent_state["pers_screen"].get_rect()
        self.rect = self.surface.get_rect(center=screen_rect.center)

        # 3. Create and place the UI element instances
        self.elements = self._create_and_place_elements()

    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = UI_ELEMENT_PADDING

        # Find the starting position for the content area
        start_x = (self.surface.get_width() - content_w) / 2
        current_y = (self.surface.get_height() - content_h) / 2 + pad_y

        # ✨ FIX: Add a nested loop to correctly handle the list-of-lists format.
        for row_items in self.layout_blueprint:
            # This inner loop correctly accesses the item dictionary within the row list.
            for item in row_items:
                item_id = item.get("id")
                element_def = self.element_definitions.get(item_id)
                if not element_def: continue
 
                elem_dims_data = self.dims['element_dims'][item_id]
                elem_w, elem_h = elem_dims_data["final_size"]
                elem_x = start_x + (content_w - elem_w) / 2 # Center horizontally
                
                element_rect = pygame.Rect(elem_x, current_y, elem_w, elem_h)
 
                # Instantiate the correct component class                    
                if element_def.get("type") == "text_block":
                    wrapped_lines = elem_dims_data["wrapped_lines"]
                    text_block = UITextBlock(rect=element_rect, line_data=wrapped_lines, style=element_def["style"], assets_state=self.assets_state)
                    elements.append(text_block)
 
                # Advance the y-position for the next element in the row
                current_y += elem_h + pad_y

        return elements

    def update(self, notebook):
        # Draw all child elements onto this panel's surface
        for element in self.elements:
            element.draw(self.surface)
        # Publish the final, complete panel to the renderer's notebook
        super().update(notebook)
        