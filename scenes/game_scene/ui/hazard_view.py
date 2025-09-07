# scenes/game_scene/hazard_view.py
# A single, consolidated UI system for managing the entire Hazard Event flow.

import pygame
from ui.ui_base_panel_components import BasePanel, assemble_organic_panel, background_panel_helper
from ui.ui_dimensions import get_panel_dimensions
from ui.ui_generic_components import UITextBlock
from ui.ui_font_and_styles import get_font, get_style

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────
DEBUG = True

# ──────────────────────────────────────────────────
# 🎨 Child Display Components
# ──────────────────────────────────────────────────

class UIDataSlot:
    """A versatile, data-driven UI component for displaying styled text."""
    def __init__(self, rect, assets_state, callback):
        # ⚙️ Core Attributes
        self.rect = rect  # This rect will be animated by the tween manager
        self.assets_state = assets_state
        self.callback = callback
        self.data_id = None # To identify what data this slot holds (e.g., a card name or a stat name)

        # 🎨 Surface & Background
        # As per our design, slots use the simpler helper for a clean background
        self.surface = background_panel_helper(
            self.rect.size, self.rect.size, self.assets_state
        )
        self.background = self.surface.copy()

        # 🚩 State Management
        self.is_selectable = False
        self._is_pressed = False
        self.line_data = [] # Stores the structured text data
        self.rendered_fragments = [] # Stores pre-rendered (surface, rect) tuples

    def update_data(self, line_data, data_id=None):
        """Receives structured text data and re-renders the slot's content."""
        self.line_data = line_data
        self.data_id = data_id
        self._render_text_fragments()

    def set_selectable(self, is_selectable):
        """Controls the interactivity and visual highlight of the slot."""
        if self.is_selectable == is_selectable: return # No change
        self.is_selectable = is_selectable
        self._render_text_fragments() # Re-render to apply/remove highlight

    def _render_text_fragments(self):
        """The core rendering logic. Turns structured data into drawable surfaces."""
        self.rendered_fragments.clear()
        
        # Use the "highlight" style as the base if the slot is selectable
        base_style_name = "highlight" if self.is_selectable else "default"
        # For stats, the default name style is stat_name, not a generic default.
        if self.data_id in ["fight", "flight", "freeze", "territoriality", "climate_resistance"]:
            base_style_name = "stat_name"

        # This is a simple layout algorithm to handle multiple text fragments

        # ✨ New Centering Logic
        # Step 1: Render all fragments and calculate the total block size
        lines = []
        current_line = []
        total_text_height = 0
        max_text_width = 0
 
        for item in self.line_data:
            if item['text'].startswith('\n'):
                lines.append(current_line)
                current_line = []
 
            style_name = item.get("style", base_style_name)
            style = get_style(style_name)
            font = get_font(style["font_size_key"])
            text = item['text'].lstrip('\n')
            surface = font.render(text, True, style["text_color"])
            current_line.append(surface)
        lines.append(current_line)
 
        line_heights = [max(frag.get_height() for frag in line) if line else 0 for line in lines]
        total_text_height = sum(line_heights) + (5 * (len(lines) - 1)) # Add 5px spacing between lines
 
        # Step 2: Calculate the starting position to center the block
        start_y = (self.rect.height - total_text_height) / 2
        current_y = start_y
 
        # Step 3: Blit the fragments with centered alignment
        for i, line in enumerate(lines):
            line_width = sum(frag.get_width() for frag in line)
            current_x = (self.rect.width - line_width) / 2
            for frag in line:
                frag_rect = frag.get_rect(topleft=(current_x, current_y))
                self.rendered_fragments.append((frag, frag_rect))
                current_x += frag.get_width()
            current_y += line_heights[i] + 5

    def handle_event(self, event, mouse_pos):
        """Handles mouse input for click detection."""
        if not self.is_selectable: return False
        
        is_hovering = self.rect.collidepoint(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and is_hovering:
            self._is_pressed = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._is_pressed and is_hovering:
                self.callback(self) # Pass the entire slot object
                return True # Event was handled
            self._is_pressed = False
        return False

    def draw(self, parent_surface):
        """Draws the slot's background and its pre-rendered text fragments."""
        # 1. Draw the base background
        self.surface.blit(self.background, (0, 0))

        # 2. Draw the text fragments onto the slot's surface
        for frag_surface, frag_rect in self.rendered_fragments:
            self.surface.blit(frag_surface, frag_rect)

        # 3. Blit the entire completed slot onto the parent at its animated position
        parent_surface.blit(self.surface, self.rect.topleft)


# ──────────────────────────────────────────────────
# 🎨 Main View Orchestrator
# ──────────────────────────────────────────────────

class HazardView:
    """A single class that manages the Hazard Queue and Stat Display panels."""
    def __init__(self, persistent_state, assets_state, tween_manager, event_bus, hazard_manager, initial_player):
        # ⚙️ Core System References
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.tween_manager = tween_manager
        self.event_bus = event_bus
        self.hazard_manager = hazard_manager # Direct reference for tight coupling
        self.player = initial_player
        self.state = "IDLE" # Can be IDLE, AWAITING_CARD_SELECTION, AWAITING_STAT_SELECTION, RESOLVING
        
        # 🚩 Shared View State
        self.is_shown = False # The master toggle for the entire view (top and bottom panels)
        self.is_event_active = False # Controls whether the stat panel is visible and interactive
        self.selected_slot = None # Stores the UIDataSlot instance being resolved
        self.selected_card_original_pos = None # Stores its pre-animation position

        # ✨ ARCHITECTURE: The HazardView now manages one large, transparent surface.
        # This allows child elements like cards to animate freely without being
        # clipped by their parent panel's boundaries.
        screen_size = self.persistent_state["pers_screen"].get_size()
        self.surface = pygame.Surface(screen_size, pygame.SRCALPHA)
        self.rect = self.surface.get_rect(topleft=(0,0))
        self.drawable_key = "hazard_view_surface"

        # ✨ ARCHITECTURE: Create the visual trays (the "game board")
        self.hazard_queue_tray = BasePanel(persistent_state, assets_state)
        self.stat_tray = BasePanel(persistent_state, assets_state)
        self.discard_tray = BasePanel(persistent_state, assets_state)

        # ✨ ARCHITECTURE: Create lists to hold the independent UIDataSlot objects
        self.hazard_slots = []
        self.stat_slots = []
        
        # 🏗️ Build the initial UI
        self._build_ui_layout()

        # 👂 Subscribe to events
        self._register_listeners()

    def _register_listeners(self):
        """Subscribe to events that require UI updates."""
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)
        # We can listen for player location changes to update empowerment "live"
        self.event_bus.subscribe("PLAYER_LOCATION_CHANGED", self.on_player_state_changed)
        # The HazardManager will now call public methods directly, reducing event reliance.

    def _prepare_card_line_data(self, card, is_empowered):
        """Translates a HazardCard object into structured line_data for a UIDataSlot."""
        if not card: return [] # Handle empty slots
        
        line_data = []

        # Line 1: Name
        line_data.append({"text": card.name, "style": "card_name"})

        # Line 2: Hazard Type
        if card.hazard_type == "Predator":
            line_data.append({"text": f"\n{card.hazard_type}", "style": "hazard_predator"})
        elif card.hazard_type == "Rival":
            line_data.append({"text": f"\n{card.hazard_type}", "style": "hazard_rival"})
        else: # Climate
            line_data.append({"text": f"\n{card.hazard_type}", "style": "hazard_climate"})
 
        # Line 3: Difficulty
        difficulty_style = f"difficulty_{card.base_difficulty}" if 5 <= card.base_difficulty <= 8 else "default"
        line_data.append({"text": "\nDifficulty ", "style": "default"})
        line_data.append({"text": str(card.base_difficulty), "style": difficulty_style})
 
        # Line 4: Trait (e.g., Ambusher)
        if card.predator_type:
            line_data.append({"text": f"\n{card.predator_type}", "style": "card_subtype"})
        
        # Line 5: Empowerment 
        if is_empowered:
            line_data.append({"text": "\nEmpowered", "style": "empowered"})
        elif card.empowerment_condition:
            terrain_types = ", ".join(card.empowerment_condition.get("terrain", []))
            if terrain_types:
                line_data.append({"text": f"\n({terrain_types})", "style": "disabled"})

        return line_data

    def _prepare_stat_line_data(self, stat_name):
        """Translates a player stat into structured line_data for a UIDataSlot."""
        base_value = getattr(self.player, stat_name, 0)
        # 📝 TODO: Get real modifier from player/game state
        modifier = 0 # Placeholder
 
        display_name = "Climate" if stat_name == "climate_resistance" else stat_name.capitalize()
        line_data = [
            {"text": display_name, "style": "stat_name"},
            {"text": f"\n{base_value}", "style": "stat_value"}
        ]
 
        if modifier > 0:
            line_data.append({"text": f" (+{modifier})", "style": "modifier_good"})
        elif modifier < 0:
            line_data.append({"text": f" ({modifier})", "style": "modifier_bad"})
        
        return line_data

    def _build_ui_layout(self):
        """Constructs or reconstructs both the queue and stat panels."""
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size()

        # ──────────────────────────────────────────────────
        # 🃏 1. Define Slot Geometry & Create Instances
        # ──────────────────────────────────────────────────
        # Define the fixed, hard-coded dimensions for our "game pieces"
        # NOTE: Data slot sizing
        card_slot_size = (210, 120)
        stat_slot_size = (140, 100)
        padding = 10

        # Create the UIDataSlot instances for the hazard queue
        self.hazard_slots.clear()
        for i in range(3):
            # The rect is temporary; its position will be set later.
            temp_rect = pygame.Rect((0, 0), card_slot_size)
            slot = UIDataSlot(temp_rect, self.assets_state, self.on_card_selected)
            self.hazard_slots.append(slot)
 
        # Create the UIDataSlot instances for the player stats
        self.stat_slots.clear()
        stats_to_show = ["fight", "flight", "freeze", "territoriality", "climate_resistance"]
        for stat_name in stats_to_show:
            temp_rect = pygame.Rect((0, 0), stat_slot_size)
            slot = UIDataSlot(temp_rect, self.assets_state, self.on_stat_selected)
            self.stat_slots.append(slot)

        # ──────────────────────────────────────────────────
        # 🖼️ 2. Build the Visual Trays
        # ──────────────────────────────────────────────────
        
        # --- Hazard Queue Tray (Top) ---
        num_queue_slots = len(self.hazard_slots)
        queue_slots_width = (num_queue_slots * card_slot_size[0]) + ((num_queue_slots - 1) * padding)

        # ✨ Add padding to all four sides of the content area.
        queue_tray_content_w = queue_slots_width + (2 * padding) 
        queue_tray_content_h = card_slot_size[1] + (2 * padding)

        # The tray surface needs to be larger to accommodate the border
        border_dim = self.assets_state["ui_assets"].get("bark_border_pieces", {'1': pygame.Surface((12,12))})['1'].get_width()
        queue_tray_w = queue_tray_content_w + border_dim
        queue_tray_h = queue_tray_content_h + border_dim
 
        self.hazard_queue_tray.surface = assemble_organic_panel(
            (queue_tray_w, queue_tray_h),
            (queue_tray_content_w, queue_tray_content_h),
            self.assets_state
        )
 
        # Calculate the tray's final hidden and shown positions
        queue_pos_hidden = ((screen_w - queue_tray_w) / 2, -queue_tray_h + 15)
        queue_pos_shown = ((screen_w - queue_tray_w) / 2, 20)
        self.hazard_queue_tray.hidden_pos = queue_pos_hidden
        self.hazard_queue_tray.shown_pos = queue_pos_shown
        self.hazard_queue_tray.rect = self.hazard_queue_tray.surface.get_rect(
            topleft=queue_pos_hidden if not self.is_shown else queue_pos_shown
        )

        # --- Discard Tray (Top Left) ---
        discard_tray_size = (card_slot_size[0] + border_dim, card_slot_size[1] + border_dim)
        self.discard_tray.surface = assemble_organic_panel(
            discard_tray_size,
            card_slot_size,
            self.assets_state
        )
        discard_pos_shown_x = self.hazard_queue_tray.shown_pos[0] - discard_tray_size[0] - padding
        discard_pos_shown_y = self.hazard_queue_tray.shown_pos[1]
        self.discard_tray.shown_pos = (discard_pos_shown_x, discard_pos_shown_y)
        self.discard_tray.hidden_pos = (discard_pos_shown_x, self.hazard_queue_tray.hidden_pos[1])
        
        self.discard_tray.rect = self.discard_tray.surface.get_rect(
            topleft=self.discard_tray.hidden_pos if not self.is_shown else self.discard_tray.shown_pos
        )


        # --- Stat Tray (Bottom) ---
        num_stat_slots = len(self.stat_slots)
        stat_slots_width = (num_stat_slots * stat_slot_size[0]) + ((num_stat_slots - 1) * padding)

        # ✨ Add padding to all four sides of the content area.
        stat_tray_content_w = stat_slots_width + (2 * padding)
        stat_tray_content_h = stat_slot_size[1] + (2 * padding)

        stat_tray_w = stat_tray_content_w + border_dim
        stat_tray_h = stat_tray_content_h + border_dim
  
        self.stat_tray.surface = assemble_organic_panel(
            (stat_tray_w, stat_tray_h),
            (stat_tray_content_w, stat_tray_content_h),
            self.assets_state
        )
 
        # Calculate the tray's final hidden and shown positions
        stat_pos_hidden = ((screen_w - stat_tray_w) / 2, screen_h - 15)
        stat_pos_shown = ((screen_w - stat_tray_w) / 2, screen_h - stat_tray_h - 20)
        self.stat_tray.hidden_pos = stat_pos_hidden
        self.stat_tray.shown_pos = stat_pos_shown
        self.stat_tray.rect = self.stat_tray.surface.get_rect(
            topleft=stat_pos_hidden if not self.is_shown else stat_pos_shown
        )
 
        # ──────────────────────────────────────────────────
        # 📍 3. Position and Populate Slots
        # ──────────────────────────────────────────────────
 
        # --- Position and Populate Hazard Slots ---
        # ✨ The manager now provides a richer list of (card, is_empowered) tuples
        cards_in_queue = self.hazard_manager.get_queue_with_empowerment_status()

        # ✨ Account for the border AND the new surrounding padding.
        start_x = self.hazard_queue_tray.rect.left + (border_dim / 2) + padding 
        start_y = self.hazard_queue_tray.rect.top + (border_dim / 2) + padding

        for i, slot in enumerate(self.hazard_slots):
            slot_x = start_x + i * (card_slot_size[0] + padding)
            slot.rect.topleft = (slot_x, start_y)
            
            if i < len(cards_in_queue):
                card_data, is_empowered = cards_in_queue[i]
                if card_data:
                    line_data = self._prepare_card_line_data(card_data, is_empowered)
                    slot.update_data(line_data, data_id=card_data.name)
            else: # Handle empty slots
                slot.update_data([], data_id=None)
 
        # --- Position and Populate Stat Slots ---
        # ✨ Account for the border AND the new surrounding padding.
        start_x = self.stat_tray.rect.left + (border_dim / 2) + padding
        start_y = self.stat_tray.rect.top + (border_dim / 2) + padding
        for i, slot in enumerate(self.stat_slots):
            stat_name = stats_to_show[i]
            slot_x = start_x + i * (stat_slot_size[0] + padding)
            slot.rect.topleft = (slot_x, start_y)
 
            line_data = self._prepare_stat_line_data(stat_name)
            slot.update_data(line_data, data_id=stat_name)

        if DEBUG: print(f"[HazardView] ✅ Rebuilt UI layout for Player {self.player.player_id}.")

    def toggle_visibility(self):
        """Animates both panels between their hidden and shown positions."""
        self.is_shown = not self.is_shown
        
        # ✨ New Animation Logic for Independent Trays and Slots
        # We calculate the destination for the tray, then apply the same movement delta
        # to all the slots that sit on top of it.
        
        # --- Animate Top Tray & Slots ---
        start_pos_q_tray = self.hazard_queue_tray.rect.topleft
        end_pos_q_tray = self.hazard_queue_tray.shown_pos if self.is_shown else self.hazard_queue_tray.hidden_pos
        self.tween_manager.add_tween(self.hazard_queue_tray.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos_q_tray, end_val=end_pos_q_tray, duration=0.4)
 
        delta_y_q = end_pos_q_tray[1] - start_pos_q_tray[1]
        for slot in self.hazard_slots:
            if slot is self.selected_slot: continue # Don't animate the selected card if it's in the center
            start_pos_slot = slot.rect.topleft
            end_pos_slot = (start_pos_slot[0], start_pos_slot[1] + delta_y_q)
            self.tween_manager.add_tween(slot.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos_slot, end_val=end_pos_slot, duration=0.4)
 
        # Animate the Discard Tray
        start_pos_d_tray = self.discard_tray.rect.topleft
        end_pos_d_tray = self.discard_tray.shown_pos if self.is_shown else self.discard_tray.hidden_pos
        self.tween_manager.add_tween(self.discard_tray.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos_d_tray, end_val=end_pos_d_tray, duration=0.4)

        # --- Animate Bottom Tray & Slots ---
        start_pos_s_tray = self.stat_tray.rect.topleft
        end_pos_s_tray = self.stat_tray.shown_pos if self.is_shown else self.stat_tray.hidden_pos
        self.tween_manager.add_tween(self.stat_tray.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos_s_tray, end_val=end_pos_s_tray, duration=0.4)
 
        delta_y_s = end_pos_s_tray[1] - start_pos_s_tray[1]
        for slot in self.stat_slots:
            start_pos_slot = slot.rect.topleft
            end_pos_slot = (start_pos_slot[0], start_pos_slot[1] + delta_y_s)
            self.tween_manager.add_tween(slot.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos_slot, end_val=end_pos_slot, duration=0.4)
        
        if DEBUG: print(f"[HazardView] ✅ Toggled visibility to: {'Shown' if self.is_shown else 'Hidden'}")

    def start_hazard_sequence(self, cards_in_queue):
        """Called directly by HazardManager to begin the UI flow for an event."""
        if DEBUG: print("[HazardView] 🎬 Hazard sequence started. Awaiting card selection.")
        self.is_event_active = True
        self.state = "AWAITING_CARD_SELECTION"
        
        # 1. Ensure the view is visible, sliding it in if needed.
        if not self.is_shown:
            self.toggle_visibility()
            
        # 2. Make the hazard cards in the queue selectable
        for slot in self.hazard_slots:
            slot.set_selectable(True)

    def on_card_selected(self, selected_slot):
        """Callback when a player clicks a hazard card."""

        # 🛡️ Guard clause: Only allow card selection in the correct state.
        if self.state != "AWAITING_CARD_SELECTION": return

        card_name = selected_slot.data_id
        card_data = next((c for c in self.hazard_manager.hazard_queue if c.name == card_name), None)
        if not card_data: return
 
        if DEBUG: print(f"[HazardView] 👉 Player selected card: {card_name}")
        self.state = "AWAITING_STAT_SELECTION"

        self.selected_slot = selected_slot
        self.selected_card_original_pos = selected_slot.rect.topleft

        # 1. Tell the manager which card was chosen.
        self.hazard_manager.on_card_selected(card_data)

        # 2. Make all cards non-selectable.
        for slot in self.hazard_slots:
            slot.set_selectable(False)

        # 3. Animate the selected card to the center "arena".
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size() 
        card_w, card_h = selected_slot.rect.size

        # ✨ Calculate the dynamic vertical position as requested.
        center_y = screen_h / 2
        safe_area_y = self.assets_state.get("UI_ELEMENT_PADDING", (20, 20))[1]
        target_bottom_y = center_y - (safe_area_y / 2)
        target_top_y = target_bottom_y - card_h

        end_pos = ((screen_w - card_w) / 2, target_top_y)

        self.tween_manager.add_tween(self.selected_slot.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=self.selected_card_original_pos, end_val=end_pos, duration=0.5)

        # 4. Make the eligible stats selectable
        for slot in self.stat_slots:
            is_eligible = slot.data_id in card_data.eligible_stats
            slot.set_selectable(is_eligible)

    def on_stat_selected(self, selected_slot):
        """Callback when a player clicks a stat button."""
        # 🛡️ Guard clause: Only allow stat selection in the correct state.
        if self.state != "AWAITING_STAT_SELECTION": return

        stat_name = selected_slot.data_id
        if DEBUG: print(f"[HazardView] 👉 Player selected stat: {stat_name}")
        self.state = "RESOLVING"

        # 1. Lock the UI by making stats non-selectable again.
        for slot in self.stat_slots:
            slot.set_selectable(False)

        # 2. Tell the manager the player has made their choice.
        self.hazard_manager.on_stat_selected({
            "stat_name": stat_name,
            "stat_value": getattr(self.player, stat_name, 0)
        })
        
        # 3. The manager will resolve the event and then call `end_hazard_sequence`.
    
    def end_hazard_sequence(self):
        """Called by HazardManager to reset the UI after an event concludes."""
        if DEBUG: print("[HazardView] 🎬 Hazard sequence ended. Resetting UI.")
        
        # Reset all stat displays to their disabled, default state.
        for slot in self.stat_slots:
            slot.set_selectable(False)

        # Animate the selected card back to its home slot.
        def on_return_complete():
            """Cleanup logic that runs after the card is back in the tray."""
            self.is_event_active = False
            self.state = "IDLE"
            self.selected_slot = None
            self.selected_card_original_pos = None

            # Rebuild the panels to show the new card drawn by the manager.
            self._build_ui_layout()

            # Hide the view if it's currently shown.
            if self.is_shown:
                self.toggle_visibility()

        if self.selected_slot and self.selected_card_original_pos:
            start_pos = self.selected_slot.rect.topleft
            end_pos = self.selected_card_original_pos
            self.tween_manager.add_tween(self.selected_slot.rect, 'value', key_to_animate='topleft', drawable_type='rect_position', start_val=start_pos, end_val=end_pos, duration=0.5, on_complete=on_return_complete)

    def on_active_player_changed(self, new_player):
        """Event handler to rebuild the stat panel for the new player."""
        self.player = new_player
        # Default to hidden at the start of a new turn/player
        if self.is_shown:
            self.toggle_visibility()
        self._build_ui_layout() # This will reconstruct the entire UI

    def on_player_state_changed(self, event_data):
        """Event handler to update empowerment glows."""
        # 📝 TODO: Implement live empowerment checking.
        # This would involve getting the player's new tile from event_data,
        # looping through self.hazard_card_displays, checking their empowerment
        # condition, and calling redraw_text() if it changed.
        pass

    def handle_events(self, events, mouse_pos):
        """Delegates events to the appropriate interactive child components."""
        # We check for events even if the panel is animating.
        # The rects for all slots are now in screen coordinates, so no conversion is needed.
        for slot in self.hazard_slots + self.stat_slots:
            for event in events:
                if slot.handle_event(event, mouse_pos):
                    return True # Event was handled, stop processing.
        return False

    def update(self, notebook):
        """Draws all components onto this view's master surface and publishes it."""
        # 1. Clear the master surface for this frame
        self.surface.fill((0, 0, 0, 0))

        # ✨ New Drawing Logic for the "Game Board" Architecture
        # 2. Draw the visual trays first to act as a backdrop.
        self.surface.blit(self.hazard_queue_tray.surface, self.hazard_queue_tray.rect)
        self.surface.blit(self.stat_tray.surface, self.stat_tray.rect)
        self.surface.blit(self.discard_tray.surface, self.discard_tray.rect)
 
        # 3. Draw the independent UIDataSlots on top of the trays.
        for slot in self.hazard_slots:
            slot.draw(self.surface)
        for slot in self.stat_slots:
            slot.draw(self.surface)

        # 5. Publish the single, final surface to the main renderer
        z_formula = self.persistent_state["pers_z_formulas"]["ui_panel"]
        notebook[self.drawable_key] = {
            "type": "ui_panel",
            "surface": self.surface,
            "rect": self.rect,
            "z": z_formula(0)
        }