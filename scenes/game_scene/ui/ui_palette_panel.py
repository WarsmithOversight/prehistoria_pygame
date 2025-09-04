import pygame
from ui_components import BasePanel, Button, assemble_organic_panel
from ui_dimensions import get_panel_dimensions

DEBUG = True

class UIPalettePanel(BasePanel):
    """A dynamically-sized panel for testing UI components, built with the modern layout system."""
    def __init__(self, persistent_state, assets_state, tile_objects, event_bus):

        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "ui_palette_panel"
        self.event_bus = event_bus
        self.tile_objects = tile_objects # Store for action callbacks

        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────
        self.element_definitions = {
            "trigger_hazard_btn": {
                "type": "button",
                "text_options": ["Hazard"],
                "style": { "font_size_key": "regular_small", "text_color": (255, 200, 200), "align": "center" },
                "action": lambda: self.event_bus.post("DEBUG_TRIGGER_HAZARD")
            }
        }

        # ──────────────────────────────────────────────────
        # 📐 Layout & Assembly
        # ──────────────────────────────────────────────────
        self.layout_blueprint = self.ui_layout()
        self.dims = get_panel_dimensions(
            "PalettePanel", # Pass a unique name for the panel here
            self.element_definitions,
            self.layout_blueprint,
            self.assets_state
        )
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        self.rect = self.surface.get_rect(bottomleft=(20, self.persistent_state["pers_screen"].get_height() - 20))
        self.elements = self._create_and_place_elements()


    def ui_layout(self):
        """Defines the high-level layout blueprint for this panel."""
        return [
            [{"id": "trigger_hazard_btn"}]
        ]
    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = self.assets_state.get("UI_ELEMENT_PADDING", (20, 20))

        current_y = (self.surface.get_height() - content_h) / 2 + pad_y
        start_x_offset = (self.surface.get_width() - content_w) / 2

        for i, row_items in enumerate(self.layout_blueprint):
            if not isinstance(row_items, list): row_items = [row_items]
 
            # Center the entire row horizontally within the content area
            row_width = self.dims['row_widths'][i]
            current_x = start_x_offset + (content_w - row_width) / 2
 
            for item in row_items:
                item_id = item.get("id")
                element_def = self.element_definitions.get(item_id)
                if not element_def: continue
 
                elem_dims_data = self.dims['element_dims'][item_id]
                elem_w, elem_h = elem_dims_data["final_size"]
                element_rect = pygame.Rect(current_x, current_y, elem_w, elem_h)
 
                button = Button(
                    rect=element_rect,
                    text=element_def["text_options"][0],
                    assets_state=self.assets_state,
                    style=element_def["style"],
                    dims=self.dims,
                    callback=element_def["action"]
                )
                elements.append(button)
                current_x += elem_w + pad_x
            
            # Move to the next row's vertical position
            row_height = self.dims['row_heights'][i]
            current_y += row_height + pad_y
        return elements

    def handle_events(self, events, mouse_pos):
        """Passes events and a localized mouse position to all interactive elements."""
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
