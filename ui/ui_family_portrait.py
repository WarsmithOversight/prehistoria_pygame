# ui/ui_family_portrait.py
# A UI panel that visually represents the player's species population.

import pygame
import random
from .ui_components import BasePanel, UIStaticImage
from .ui_dimensions import get_panel_dimensions
from .ui_components import assemble_organic_panel

DEBUG = True

class UIFamilyPortraitPanel(BasePanel):
    """
    A dynamic UI panel that displays a species family, now built using the
    standard panel assembly system for a consistent look and feel.
    """
    def __init__(self, player, persistent_state, assets_state, event_bus):
        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.player = player
        self.event_bus = event_bus
        self.drawable_key = f"family_portrait_p{self.player.player_id}"
        self.is_dirty = False 

        # 🎨 1. Assemble the Portrait Image
        # First, create the combined image of the sepia background and members.
        # This will be treated as a single piece of content for our panel.
        portrait_assets = self.assets_state["family_portraits"][self.player.species_name]
        self.background_layer = portrait_assets["background"]
        self.all_member_layers = portrait_assets["members"]
        self.visible_member_indices = list(range(int(self.player.current_population)))
        
        # Create the composite image that will be displayed.
        self.portrait_image_surface = self._create_composite_image()

        # ──────────────────────────────────────────────────
        # 🎨 2. Define Panel Content & Layout
        # ──────────────────────────────────────────────────
        self.element_definitions = {
            "portrait_image": {
                "type": "static_image",
                # Pass the surface we just created as the content.
                "content": self.portrait_image_surface,
                "properties": {
                    # The size is derived directly from the image itself.
                    "size": self.portrait_image_surface.get_size()
                }
            }
        }
        self.layout_blueprint = [[{"id": "portrait_image"}]] # Now a list of lists

        # ──────────────────────────────────────────────────
        # 📐 3. Calculate Dimensions & Assemble Panel
        # ──────────────────────────────────────────────────
        # ✨ STANDARDIZED: Call the central layout engine.
        self.dims = get_panel_dimensions(
            f"FamilyPortrait_P{self.player.player_id}",
            self.element_definitions,
            self.layout_blueprint,
            self.assets_state
        )

        # Use the standard assembler to create the beautiful organic panel.
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
        self.rect = self.surface.get_rect(bottomright=(screen_w - 20, screen_h - 20))

        # Create and place the UI element instances (our static image).
        self.elements = self._create_and_place_elements()

        # 👂 Subscribe to events
        self.event_bus.subscribe("PLAYER_POPULATION_CHANGED", self.on_population_changed)
        if DEBUG:
            print(f"[UI Portrait] ✅ Panel created for Player {self.player.player_id} ({self.player.species_name}).")

    def _create_composite_image(self):
        """Creates a single surface with the background and visible members."""
        # Start with a copy of the background layer.
        composite_surface = self.background_layer.copy()
        # Blit each visible member on top.
        for index in self.visible_member_indices:
            if 0 <= index < len(self.all_member_layers):
                member_layer = self.all_member_layers[index]
                composite_surface.blit(member_layer, (0, 0))
        return composite_surface
        
    def _create_and_place_elements(self):
        """Creates and positions all UI elements (in this case, just the image)."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = self.assets_state.get("UI_ELEMENT_PADDING", (20, 20)) # Get padding from assets
        
        # ✨ STANDARDIZED: Use the new row-based placement logic.
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
 
                image_component = UIStaticImage(rect=element_rect, surface=element_def["content"])
                elements.append(image_component)
                current_x += elem_w + pad_x
            
            row_height = self.dims['row_heights'][i]
            current_y += row_height + pad_y

        return elements

    def on_population_changed(self, data):
        """Handles population changes and marks the panel for redraw."""
        # (This method's logic remains the same, but we add a check)
        if data["player_id"] != self.player.player_id: return
        
        old_pop = len(self.visible_member_indices)
        new_population = int(data["current_population"])
        
        # (The rest of the population update logic is unchanged)
        while len(self.visible_member_indices) > new_population:
            member_to_remove = random.choice(self.visible_member_indices)
            self.visible_member_indices.remove(member_to_remove)
        while len(self.visible_member_indices) < new_population:
            all_possible_indices = list(range(len(self.all_member_layers)))
            hidden_indices = [i for i in all_possible_indices if i not in self.visible_member_indices]
            if hidden_indices:
                member_to_add = random.choice(hidden_indices)
                self.visible_member_indices.append(member_to_add)

        if old_pop != len(self.visible_member_indices):
            self.is_dirty = True

    def _redraw_panel(self):
        """Re-creates the composite image and updates the UI element."""
        # Re-create the composite image with the new population.
        self.portrait_image_surface = self._create_composite_image()
        
        # Find the image component in our elements list and update its surface.
        for element in self.elements:
            if isinstance(element, UIStaticImage):
                element.surface = self.portrait_image_surface
        
        # Reset the dirty flag.
        self.is_dirty = False
        if DEBUG: print(f"[UI Portrait] 🎨 Redrew portrait for Player {self.player.player_id}.")

    def update(self, notebook):
        """Draws child elements and publishes the final panel."""
        # If the population changed, rebuild the image content.
        if self.is_dirty:
            self._redraw_panel()

        # Draw all child elements (our image) onto this panel's main surface.
        for element in self.elements:
            element.draw(self.surface)

        # Publish the final, complete panel to the renderer.
        super().update(notebook)