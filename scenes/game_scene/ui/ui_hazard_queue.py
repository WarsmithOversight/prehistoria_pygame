# ui/ui_hazard_queue.py
# A UI panel that displays upcoming environmental hazards.

from ui_dimensions import get_panel_dimensions, UI_ELEMENT_PADDING
from ui_components import BasePanel, UICard, assemble_organic_panel

DEBUG = True

class HazardQueuePanel(BasePanel):
    """
    A UI panel that can be toggled on and off screen with a smooth animation
    to display upcoming hazard cards.
    """
    def __init__(self, persistent_state, assets_state, tween_manager, hazard_deck, event_bus):
        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.tween_manager = tween_manager
        self.event_bus = event_bus
        self.drawable_key = "hazard_queue_panel"
        self.is_shown = False # The panel starts in its hidden state
        self.hazard_deck = hazard_deck
        self.is_in_selection_mode = False # The new master switch for interactivity
 
        # 🃏 Get the initial three cards from the deck and store them.
        self.cards_in_slots = self.hazard_deck.draw_cards(3)

        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────

        self.element_definitions = {}
        self.layout_blueprint = []
 
        # ✨ Dynamically create a UI element for each card in our hand.
        for i, card_data in enumerate(self.cards_in_slots):
            element_id = f"card_slot_{i}"
            # Use a multi-line f-string for the new display format
            card_text = (
                f"{card_data['name']}\n"
                f"{card_data['type']}\n"
                f"{card_data['difficulty']}"
            )
            
            self.element_definitions[element_id] = {
                "type": "text_block",
                "content": card_text,
                "style": {"font_size_key": "regular_medium", "text_color": (255, 220, 200), "align": "center"},
                "properties": {"max_width": 100} # Set width for a single card display
            }

        #  Horizontal Layout: A list containing one list (a single row of our three cards)
        self.layout_blueprint = [[
            {"id": "card_slot_0"},
            {"id": "card_slot_1"},
            {"id": "card_slot_2"}
        ]]
 
        # ──────────────────────────────────────────────────
        # 📐 Layout, Assembly, & Positioning
        # ──────────────────────────────────────────────────
        # 🗺️ Calculate all dimensions for the panel and its children
        self.dims = get_panel_dimensions(
            "HazardQueuePanel",
            self.element_definitions,
            self.layout_blueprint,
            self.assets_state
        )
        
        # 🏭 Assemble the panel surface using the standard organic builder
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        
        # 📍 Define the on-screen and off-screen positions
        screen_w, _ = self.persistent_state["pers_screen"].get_size()
        panel_w, panel_h = self.surface.get_size()

        # The panel is horizontally centered for both positions
        x_pos = (screen_w - panel_w) / 2
        
        # Position it just peeking down from the top of the screen
        self.pos_hidden = (x_pos, -panel_h + 15)
        
        # Position it fully visible with a small margin at the top
        self.pos_shown = (x_pos, 20)
        
        # Set the initial position and create a background copy for drawing
        self.rect = self.surface.get_rect(topleft=self.pos_hidden)
        self.background = self.surface.copy()
        
        # 👶 Create and place the child UI elements on the panel
        self.cards = self._create_and_place_elements()

        # 👂 Subscribe to the event that starts the hazard selection process
        self.event_bus.subscribe("HAZARD_EVENT_START", self.on_hazard_event_start)

    def on_hazard_event_start(self, data=None):
        """Event handler for when a hazard event begins."""
        if DEBUG: print(f"[HazardQueue] 👂 Heard HAZARD_EVENT_START. Entering selection mode.")
        self.is_in_selection_mode = True
 
        # If the panel is currently hidden, animate it into view.
        if not self.is_shown:
            self.toggle_visibility()
        
        # ✨ Tell each card to activate its glow effect.
        for card in self.cards:
            card.set_glow(True)

    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        cards = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = UI_ELEMENT_PADDING

        current_y = (self.surface.get_height() - content_h) / 2 + pad_y
        start_x_offset = (self.surface.get_width() - content_w) / 2

        for i, row_items in enumerate(self.layout_blueprint):
            # For backward compatibility, treat a single dict as a row with one item
            if not isinstance(row_items, list):
                row_items = [row_items]
            
            # Center the entire row horizontally within the content area
            row_width = self.dims['row_widths'][i]
            current_x = start_x_offset + (content_w - row_width) / 2

            for item in row_items:
                item_id = item.get("id")
                element_def = self.element_definitions.get(item_id)
                if not element_def: continue

                # Find the original card data that corresponds to this slot index.
                slot_index = int(item_id.split('_')[-1])
                card_data = self.cards_in_slots[slot_index]

                elem_dims_data = self.dims['element_dims'][item_id]
                elem_w, elem_h = elem_dims_data["final_size"]

                # ✨ FIX: Calculate the exact center point for the card to avoid truncation errors.
                # The card component itself will build its final rect from this more precise point.
                card_center_x = current_x + elem_w / 2
                card_center_y = current_y + elem_h / 2

                card = UICard(
                    size=(elem_w, elem_h),
                    center_pos=(card_center_x, card_center_y),
                    card_data=card_data,
                    assets_state=self.assets_state,
                    event_bus=self.event_bus
                )
                cards.append(card)
                # Move to the next element's horizontal position in the row
                current_x += elem_w + pad_x
            
            # Move to the next row's vertical position
            row_height = self.dims['row_heights'][i]
            current_y += row_height + pad_y
            
        return cards
        
    def toggle_visibility(self):
        """Animates the panel between its hidden and shown positions."""
        # 🎯 Determine the start and end positions for the animation
        start_pos = self.rect.topleft
        end_pos = self.pos_shown if not self.is_shown else self.pos_hidden
        
        # 🎌 Flip the state flag
        self.is_shown = not self.is_shown
        
        # 🚀 Create the tween animation
        self.tween_manager.add_tween(
            target_dict=self.rect,              # The object to animate (the panel's rect)
            animation_type='value',               # The existing PanTween works perfectly for position
            key_to_animate='topleft',           # ✨ Add this required key
            drawable_type='rect_position',      # Our new updater for pygame.Rect objects
            start_val=start_pos,
            end_val=end_pos,
            duration=0.4,                       # A quick, snappy animation
        )
        if DEBUG: print(f"[HazardQueue] ✅ Toggled visibility to: {'Shown' if self.is_shown else 'Hidden'}")

    def handle_events(self, events, mouse_pos):
        """Handles events for any interactive elements on this panel."""
        local_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        # Delegate events to each interactive card.
        for card in self.cards:
            card.handle_events(events, local_mouse_pos)

    def update(self, notebook):
        """Draws child elements and publishes the panel to the renderer."""
        # 🎨 Redraw the panel's pristine background
        self.surface.blit(self.background, (0, 0))
        
        # ✍️ Draw all child elements (like text) onto the panel's surface
        for card in self.cards:
            card.draw(self.surface)

        # 📚 Publish the final, composed surface to the notebook for rendering
        super().update(notebook)