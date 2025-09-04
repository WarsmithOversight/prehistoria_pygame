import pygame
from ui_components import BasePanel, Button, assemble_organic_panel
from ui_dimensions import get_panel_dimensions, UI_ELEMENT_PADDING

DEBUG: True

# ──────────────────────────────────────────────────
# 📜 Main Menu Panel UI
# ──────────────────────────────────────────────────
class MainMenuPanel(BasePanel):
    def __init__(self, persistent_state, assets_state, scene):

        # Calls the parent class constructor
        super().__init__(persistent_state, assets_state)

        # Defines the unique key for this drawable in the notebook
        self.drawable_key = "main_menu_panel"
        
        # Stores a reference to the main menu scene
        self.scene = scene

        # Defines the properties of the UI elements in this panel
        self.element_definitions = {
            "new_world": {
                "type": "button",
                "text_options": ["New World"],
                "style": {"font_size_key": "regular_large", "text_color": (255, 255, 255), "align": "center"},
                "action": self.on_new_world
            },
            "load_world": {
                "type": "button",
                "text_options": ["Load Saved World"],
                "style": {"font_size_key": "regular_large", "text_color": (150, 150, 150), "align": "center"},
                "action": self.on_load_world
            },
            "dev_quickboot": {
                "type": "button", # Add the type definition
                "text_options": ["Dev Quickboot"],
                "style": {"font_size_key": "regular_large", "text_color": (255, 255, 255), "align": "center"},
                "action": self.on_dev_quickboot
            }
        }

        # Defines the order and IDs for the UI elements
        # Each item is now in its own row (a list within the main list)
        self.layout_blueprint = [
            [{"id": "new_world"}],
            [{"id": "load_world"}],
            [{"id": "dev_quickboot"}]
        ]

        # Calculates the dimensions of the panel and its elements
        self.dims = get_panel_dimensions(
            "MainMenuPanel", # Pass a unique name for the panel here
            self.element_definitions,
            self.layout_blueprint,
            self.assets_state
        )
        
        # Creates the surface for the panel
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        
        # Creates and places the UI elements on the panel
        self.elements = self._create_and_place_elements()
        
        # Creates a pristine background surface
        self.background = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        
        # Creates a copy of the background to draw on each frame
        self.surface = self.background.copy() # The surface we will actually draw on.
        
        # Gets the rectangle for the drawing surface
        self.rect = self.surface.get_rect()
 
    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = UI_ELEMENT_PADDING
 
        current_y = (self.surface.get_height() - content_h) / 2 + pad_y
        start_x_offset = (self.surface.get_width() - content_w) / 2

        for i, row_items in enumerate(self.layout_blueprint):
            if not isinstance(row_items, list): row_items = [row_items]
 
            row_width = self.dims['row_widths'][i]
            current_x = start_x_offset + (content_w - row_width) / 2
 
            for item in row_items:
                item_id = item.get("id")
                element_def = self.element_definitions.get(item_id)
                if not element_def: continue
 
                elem_dims_data = self.dims['element_dims'][item_id]
                elem_w, elem_h = elem_dims_data["final_size"]
                element_rect = pygame.Rect(current_x, current_y, elem_w, elem_h)
 
                button = Button(rect=element_rect, text=element_def["text_options"][0], assets_state=self.assets_state, style=element_def["style"], dims=self.dims, callback=element_def["action"])
                elements.append(button)
                current_x += elem_w + pad_x
            
            row_height = self.dims['row_heights'][i]
            current_y += row_height + pad_y
        return elements

    def on_new_world(self):

        # Get the instance of the loading scene from the manager
        loading_scene = self.scene.manager.scenes["LOADING"]

        # Tell the manager to change scenes, and to call start_load_process when the fade-in is done.
        self.scene.manager.change_scene(
            "LOADING",
            on_fade_in_complete=loading_scene.start_load_process
        )
    
    def on_load_world(self):
        
        # Prints a debug message for an unimplemented feature
        if DEBUG: print("[MainMenu] ⚠️ 'Load Saved World' is not yet implemented.")
    
    def on_dev_quickboot(self):
        persistent_state = self.scene.manager.persistent_state
        variable_state = self.scene.manager.variable_state

        persistent_state["pers_dev_quickboot"] = True
        persistent_state["pers_quickboot_zoom"] = 0.40

        # Make the zoom config a single legal step.
        persistent_state["pers_zoom_config"] = {
            "min_zoom": persistent_state["pers_quickboot_zoom"],
            "max_zoom": persistent_state["pers_quickboot_zoom"],
            "zoom_interval": 1.0,      # any value; snapping will clamp to min/max anyway
            "settle_ms": 0
        }

        # Seed current zoom to the fixed value (so first render is correct)
        variable_state["var_current_zoom"] = persistent_state["pers_quickboot_zoom"]

        # Proceed exactly like "New World" (or your prefab path—your choice)
        loading_scene = self.scene.manager.scenes["LOADING"]
        
        # Tell the manager to change scenes, and to call start_load_process when the fade-in is done.
        self.scene.manager.change_scene(
            "LOADING",
            on_fade_in_complete=loading_scene.start_load_process
        )

    def handle_events(self, events, mouse_pos):
        
        # Translates the global mouse position to a local position relative to the panel
        local_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        
        # Delegates event handling to each UI element
        for element in self.elements: element.handle_events(events, local_mouse_pos)
    
    def update(self, notebook):

        # Wipes the surface clean by blitting the background onto it
        self.surface.blit(self.background, (0, 0))

        # Draws each UI element on the surface
        for element in self.elements: element.draw(self.surface)

        # Calls the parent class's update method
        super().update(notebook)

