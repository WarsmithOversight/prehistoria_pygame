import pygame
from math import ceil
from .ui_components import BasePanel, Button, assemble_organic_panel, UI_ELEMENT_PADDING
from .ui_dimensions import get_panel_dimensions

DEBUG = True

class UIPalettePanel(BasePanel):
    """A dynamically-sized panel for testing UI components, built with the modern layout system."""
    def __init__(self, persistent_state, assets_state, tile_objects):

        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "ui_palette_panel"
        self.buttons_by_id = {}
        self.toggle_states = {"toggle_btn": 0}
        self.tile_objects = tile_objects # Store for action callbacks

        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────
        self.button_definitions = {
            "long_text_btn": {
                "type": "button",
                "text_options": ["A Button With Very Long Text"],
                "style": { "font_size_key": "regular_medium", "text_color": (255, 255, 255), "align": "center" },
                "action": lambda: print("[UI Palette] Clicked: Long Text")
            },
            "small_text_btn": {
                "type": "button",
                "text_options": ["Small Font"],
                "style": { "font_size_key": "regular_small", "text_color": (200, 220, 255), "align": "center" },
                "action": lambda: print("[UI Palette] Clicked: Small Font")
            },
            "left_align_btn": {
                "type": "button",
                "text_options": ["Aligned Left"],
                "style": { "font_size_key": "regular_medium", "text_color": (255, 255, 255), "align": "left" },
                "action": lambda: print("[UI Palette] Clicked: Left Align")
            },
            "right_align_btn": {
                "type": "button",
                "text_options": ["Aligned Right"],
                "style": { "font_size_key": "regular_medium", "text_color": (255, 255, 255), "align": "right" },
                "action": lambda: print("[UI Palette] Clicked: Right Align")
            },
            "toggle_btn": {
                "type": "button",
                "text_options": ["Toggle: Option A", "Toggle: Option B", "Toggle: Option C"],
                "style": { "font_size_key": "regular_medium", "text_color": (220, 255, 220), "align": "center" },
                "action": lambda: self.on_toggle_click("toggle_btn")
            }
        }

        # ──────────────────────────────────────────────────
        # 📐 Layout & Assembly
        # ──────────────────────────────────────────────────
        self.layout_blueprint = self.ui_layout()
        self.dims = get_panel_dimensions(self.button_definitions, self.layout_blueprint, self.assets_state)
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        self.rect = self.surface.get_rect(bottomleft=(20, self.persistent_state["pers_screen"].get_height() - 20))
        self.elements = self._create_and_place_elements()


    def ui_layout(self):
        """Defines the high-level layout blueprint for this panel."""
        return [
            {"id": "long_text_btn"},
            {"id": "small_text_btn"},
            {"id": "left_align_btn"},
            {"id": "right_align_btn"},
            {"id": "toggle_btn"}
        ]

    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = UI_ELEMENT_PADDING

        start_x = (self.surface.get_width() - content_w) / 2
        current_y = (self.surface.get_height() - content_h) / 2 + pad_y

        for item in self.layout_blueprint:
            item_id = item.get("id")
            element_def = self.button_definitions.get(item_id)
            if not element_def: continue

            elem_dims_data = self.dims['element_dims'][item_id]
            elem_w, elem_h = elem_dims_data["final_size"]
            elem_x = start_x + (content_w - elem_w) / 2 # Center horizontally
            element_rect = pygame.Rect(elem_x, current_y, elem_w, elem_h)

            button = Button(
                rect=element_rect,
                text=element_def["text_options"][0],
                assets_state=self.assets_state,
                style=element_def["style"],
                dims=self.dims,
                callback=element_def["action"]
            )
            elements.append(button)
            self.buttons_by_id[item_id] = button
            current_y += elem_h + pad_y
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
    def on_toggle_click(self, button_id):
        """Handles the logic for the multi-state toggle button."""
        self.toggle_states[button_id] = (self.toggle_states[button_id] + 1) % len(self.button_definitions[button_id]["text_options"])
        new_text = self.button_definitions[button_id]["text_options"][self.toggle_states[button_id]]
        self.buttons_by_id[button_id].update_text(new_text)