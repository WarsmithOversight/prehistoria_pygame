# ui/ui_family_portrait.py
# A UI panel that visually represents the player's species population.

import pygame
import random
from ui_components import BasePanel, UIStaticImage
from ui_dimensions import get_panel_dimensions
from ui_components import assemble_organic_panel

DEBUG = True

class UIFamilyPortraitPanel(BasePanel):
    """
    A dynamic UI panel that displays a species family, now built using the
    standard panel assembly system for a consistent look and feel.
    """
    def __init__(self, player, persistent_state, assets_state, event_bus, tween_manager):
        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.player = player
        self.event_bus = event_bus
        self.tween_manager = tween_manager
        self.drawable_key = f"family_portrait_p{self.player.player_id}"

        # ✨ NEW: A list to manage members who are currently fading out.
        # It will store dicts: {'surface': surface, 'alpha_dict': {'value': 255}}
        self.fading_out_members = []

        # 🎨 1. Assemble the Portrait Image
        # First, create the combined image of the sepia background and members.
        # This will be treated as a single piece of content for our panel.
        portrait_assets = self.assets_state["family_portraits"][self.player.species_name]
        self.background_layer = portrait_assets["background"]
        self.all_member_layers = portrait_assets["members"]
        self.visible_member_indices = list(range(int(self.player.current_population)))
        
        # ──────────────────────────────────────────────────
        # 🎨 2. Define Panel Content & Layout
        # ──────────────────────────────────────────────────
        self.element_definitions = {
            "portrait_image": {
                "type": "static_image",
                # Pass the surface we just created as the content.
                "content": self.background_layer,
                "properties": {
                    # The size is derived directly from the image itself.
                    "size": self.background_layer.get_size()
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
        
        new_population = int(data["current_population"])
        
        # ✨ If population decreased, start a fade-out tween.
        while len(self.visible_member_indices) > new_population:
            if not self.visible_member_indices: break
            # Choose a random visible member to remove.
            member_to_remove = random.choice(self.visible_member_indices)
            self.visible_member_indices.remove(member_to_remove)

            # Create the data structure for the fading animation.
            fade_info = {
                'surface': self.all_member_layers[member_to_remove],
                'alpha_dict': {'value': 255} # A dictionary for the tween to target.
            }
            self.fading_out_members.append(fade_info)
 
            # Define what happens when the fade is complete.
            def on_fade_complete(info=fade_info):
                # Remove the member from the fading list so it stops being drawn.
                if info in self.fading_out_members:
                    self.fading_out_members.remove(info)
 
            # Start the fade tween.
            self.tween_manager.add_tween(
                fade_info['alpha_dict'], 'fade',
                start_val=255, end_val=0, duration=1.0, drawable_type='generic',
                on_complete=on_fade_complete
            )
 
        # If population increased, add a new member instantly.
        while len(self.visible_member_indices) < new_population:
            all_possible_indices = list(range(len(self.all_member_layers)))
            hidden_indices = [i for i in all_possible_indices if i not in self.visible_member_indices]
            if hidden_indices:
                member_to_add = random.choice(hidden_indices)
                self.visible_member_indices.append(member_to_add)

    def update(self, notebook):
        """Draws child elements and publishes the final panel."""
        for element in self.elements:
            element.draw(self.surface)

        # 📍 Get the correct top-left position from our background image element.
        # This ensures members are drawn in the center, not the corner.
        image_offset = self.elements[0].rect.topleft if self.elements else (0, 0)

        # ✨ NEW: Draw the member layers directly onto the main panel surface.
        # This allows us to handle transparency for individual members.
        for index in self.visible_member_indices:
            if 0 <= index < len(self.all_member_layers):
                self.surface.blit(self.all_member_layers[index], image_offset)
        
        # ✨ Draw any members that are currently fading out.
        for fade_info in self.fading_out_members:
            surface_to_fade = fade_info['surface']
            alpha = fade_info['alpha_dict']['value']
            surface_to_fade.set_alpha(alpha)
            self.surface.blit(surface_to_fade, image_offset)

        # Publish the final, complete panel to the renderer.
        super().update(notebook)