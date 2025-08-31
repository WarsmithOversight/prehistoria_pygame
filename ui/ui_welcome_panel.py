# ui/ui_welcome_panel.py
# The UI Panel for the game's initial welcome screen.

import pygame
from .ui_components import BasePanel, Button, UITextBlock, assemble_organic_panel
from .ui_dimensions import get_panel_dimensions, UI_ELEMENT_PADDING

DEBUG = True

class UIWelcomePanel(BasePanel):
    """
    A panel that displays a welcome message and a continue button.
    This class now fully constructs and manages the panel.
    """
    def __init__(self, persistent_state, assets_state, scene):
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "welcome_panel"
        self.scene = scene

        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────
        self.element_definitions = {
            "welcome_text": {
                "type": "text_block",
                "content": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi in auctor enim. "
                    "Nunc ac urna sodales, fermentum turpis a, feugiat tellus. Mauris ultricies ut "
                    "lectus ut ultricies. Maecenas in semper neque. Lorem ipsum dolor sit amet, "
                    "consectetur adipiscing elit. Phasellus vulputate sed ante vitae vestibulum. Sed "
                    "vitae imperdiet ipsum, vel pulvinar purus. Integer auctor tellus eget commodo "
                    "consectetur. Duis at imperdiet massa, nec interdum neque. Sed facilisis sit amet "
                    "ligula sit amet dignissim. Cras quis interdum nulla. Curabitur quis est eget "
                    "nunc tincidunt pellentesque. Vivamus molestie nisl lobortis dignissim eleifend. "
                    "Aenean pretium dui vel tincidunt laoreet.\n\n"
                    "Nam maximus efficitur iaculis. Donec ipsum erat, euismod eu rutrum sed, "
                    "imperdiet et risus. Phasellus efficitur vitae risus ac pellentesque. Aenean "
                    "finibus porttitor ligula in rhoncus. Mauris quis libero nulla. Proin a orci "
                    "risus. Phasellus ultricies at odio hendrerit aliquet. Mauris laoreet nibh odio, "
                    "quis ullamcorper nisi rutrum quis.\n\n"
                    "Praesent pulvinar magna eget felis bibendum suscipit. Morbi a ante felis. Sed eu "
                    "lectus dolor. Fusce tempus dui vel libero egestas aliquet. Cras at ex efficitur, "
                    "porttitor arcu non, vehicula quam. Mauris massa nisi, tempor ut condimentum vel, "
                    "laoreet sed mauris. Vestibulum congue lacus eu nulla efficitur, vitae elementum "
                    "nunc sodales. Nullam a nunc vitae nibh ultricies tempor eget non sapien. Nulla "
                    "vel diam vitae nunc accumsan rutrum id eu mauris. Pellentesque nisl orci, porta "
                    "non facilisis iaculis, tristique vel ipsum."                ),
                "style": {"font_size_key": "regular_medium", "text_color": (220, 220, 220), "align": "justify"},
                "properties": {"max_width": 550}
            },
            "continue_button": {
                "type": "button",
                "text_options": ["Continue"],
                "style": {"font_size_key": "regular_medium", "text_color": (255, 255, 255), "align": "center"},
                # Point the action to the new method on the scene object
                "action": lambda: self.scene.start_game()
            }
        }

        # ──────────────────────────────────────────────────
        # 📐 Layout & Assembly
        # ──────────────────────────────────────────────────
        self.layout_blueprint = [
            {"id": "welcome_text"},
            {"id": "continue_button"}
        ]
        
        # 1. Calculate final dimensions for the panel and all its child elements
        self.dims = get_panel_dimensions(self.element_definitions, self.layout_blueprint, self.assets_state)

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

        for item in self.layout_blueprint:
            item_id = item.get("id")
            element_def = self.element_definitions.get(item_id)
            if not element_def: continue

            elem_dims_data = self.dims['element_dims'][item_id]
            elem_w, elem_h = elem_dims_data["final_size"]
            elem_x = start_x + (content_w - elem_w) / 2 # Center horizontally
            
            element_rect = pygame.Rect(elem_x, current_y, elem_w, elem_h)

            # Instantiate the correct component class
            if element_def.get("type") == "button":
                # Pass the main self.dims dictionary for uniform button geometry
                button = Button(rect=element_rect, text=element_def["text_options"][0], assets_state=self.assets_state, style=element_def["style"], dims=self.dims, callback=element_def["action"])
                elements.append(button)
                
            elif element_def.get("type") == "text_block":
                text_block = UITextBlock(rect=element_rect, text=element_def["content"], style=element_def["style"], assets_state=self.assets_state)
                elements.append(text_block)

            # Advance the y-position for the next element
            current_y += elem_h + pad_y
            
        return elements

    def handle_events(self, events, mouse_pos):
        # Translate mouse position to be local to the panel
        local_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        for element in self.elements:
            # Only Buttons need to handle events
            if hasattr(element, 'handle_events'):
                element.handle_events(events, local_mouse_pos)

    def update(self, notebook):
        # Draw all child elements onto this panel's surface
        for element in self.elements:
            element.draw(self.surface)
        # Publish the final, complete panel to the renderer's notebook
        super().update(notebook)

