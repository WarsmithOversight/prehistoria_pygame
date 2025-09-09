# ui/migration_event_panel.py
# Contains the logic and UI panel for the turn-based Migration Events.

import random
import pygame
from ui.ui_base_panel_components import BasePanel, assemble_organic_panel
from ui.ui_dimensions import get_panel_dimensions
from ui.ui_generic_components import UITextBlock
from ui.ui_font_and_styles import get_style, get_font

DEBUG = True

# ──────────────────────────────────────────────────
# 💿 Data Structure
# ──────────────────────────────────────────────────

class MigrationEvent:
    """A data class to hold all information about a single migration event."""
    def __init__(self, event_id, description, trigger_type, trigger_param, is_enabled=True):
        self.event_id = event_id            # Unique identifier, e.g., "desert_hazard"
        self.description = description      # Text displayed on the panel
        self.trigger_type = trigger_type    # The condition, e.g., "enter_terrain"
        self.trigger_param = trigger_param  # The trigger's data, e.g., ["DesertDunes"]
        self.is_enabled = is_enabled        # For black/whitelisting

# ──────────────────────────────────────────────────
# ⚙️ Event Manager (The "Battery")
# ──────────────────────────────────────────────────

class MigrationEventManager:
    """Manages the master list of events and the logic for selecting them."""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.events = []
        self.active_event = None
        self.event_bus.subscribe("PLAYER_LANDED_ON_TILE", self.on_player_landed)
        self._initialize_events()

    def _initialize_events(self):
        """Populates the master list of all possible migration events."""
        # This data is migrated from the GameManager
        event_data = [
            MigrationEvent(
                event_id="desert_hazard",
                description="Entering Desert terrain is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["DesertDunes"]
            ),
            MigrationEvent(
                event_id="scrub_hazard",
                description="Entering Scrublands is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["Scrublands"]
            ),
            MigrationEvent(
                event_id="marsh_hazard",
                description="Entering a Marsh is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["Marsh"]
            ),
            MigrationEvent(
                event_id="highland_hazard",
                description="Entering Highlands or Hills is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["Highlands", "Hills"]
            ),
            MigrationEvent(
                event_id="forest_hazard",
                description="Entering a Forest is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["Woodlands", "ForestBroadleaf"]
            ),
            MigrationEvent(
                event_id="plains_hazard",
                description="Entering the Plains is hazardous.",
                trigger_type="enter_terrain",
                trigger_param=["Plains"]
            )
        ]
        self.events.extend(event_data)
        if DEBUG:
            print(f"[MigrationManager] ✅ Initialized with {len(self.events)} events.")

    def add_event(self, event):
        """Adds a new MigrationEvent to the list."""
        pass # To be implemented

    def remove_event(self, event_id):
        """Removes a MigrationEvent from the list by its ID."""
        pass # To be implemented

    def enable_event(self, event_id, is_enabled=True):
        """Enables or disables an event, effectively white/blacklisting it."""
        pass # To be implemented

    def select_random_event(self):
        """Selects a random, enabled event for the start of a turn."""
        eligible_events = [e for e in self.events if e.is_enabled]
        if not eligible_events:
            if DEBUG: print("[MigrationManager] ⚠️ No eligible events to select from.")
            return None
        
        return random.choice(eligible_events)

    def set_new_active_event(self):
        """Selects a new event, sets it as the manager's active event, and returns it."""
        new_event = self.select_random_event()
        self.active_event = new_event
        return new_event
    
    def on_player_landed(self, data):
        """Checks if the player's move triggers the active migration hazard."""
        if not self.active_event: return

        tile = data["tile"]
        if not tile: return

        hazardous_terrains = self.active_event.trigger_param
        if tile.terrain in hazardous_terrains:
            print(f"[MigrationManager] 📢 Player landed on hazardous terrain ({tile.terrain}). Requesting hazard event.")
            self.event_bus.post("REQUEST_HAZARD_EVENT", {"trigger": "migration_event"})
 

# ──────────────────────────────────────────────────
# 🖼️ UI Panel (The "Power Tool")
# ──────────────────────────────────────────────────

class MigrationEventPanel(BasePanel):
    """A UI panel that displays and animates the selection of a Migration Event."""
    def __init__(self, persistent_state, assets_state, tween_manager, event_bus):
        # ⚙️ Core Setup
        super().__init__(persistent_state, assets_state)
        self.tween_manager = tween_manager
        self.event_bus = event_bus
        self.drawable_key = "migration_event_panel"
        
        # 🔋 Instantiate the manager, giving it the event bus
        self.manager = MigrationEventManager(self.event_bus)

        # 🎨 Store child components for animation
        self.event_displays = {} # Maps event_id to its UITextBlock component

        # 🚩 State Management
        self.is_animating = False
        # ✨ A counter to ensure old, overlapping animations don't interfere with new ones.
        self.animation_cycle_id = 0
        
        # ──────────────────────────────────────────────────
        # 🎨 Content & Style Definitions
        # ──────────────────────────────────────────────────
        self.element_definitions = {}
        self.layout_blueprint = []
        
        # Dynamically create a UI element for each event
        for event in self.manager.events:
            element_id = f"event_{event.event_id}"
            self.element_definitions[element_id] = {
                "type": "text_block",
                "content": event.description,
                # ✨ Use a style name from our central style guide.
                "style": get_style("migration_event_muted"), # Use the new specific style
                "properties": {"max_width": 200}
            }
            # Each event gets its own row for a vertical stack
            self.layout_blueprint.append([{"id": element_id}])

        # ──────────────────────────────────────────────────
        # 📐 Layout, Assembly, & Positioning
        # ──────────────────────────────────────────────────
        self.dims = get_panel_dimensions(
            "MigrationEventPanel", self.element_definitions, self.layout_blueprint, self.assets_state
        )
        self.surface = assemble_organic_panel(
            self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state
        )
        # Position the panel on the left side of the screen, centered vertically
        screen_h = self.persistent_state.get("SCREEN_HEIGHT", 720) # Default to 720 if not found
        self.rect = self.surface.get_rect(left=20, centery=screen_h // 2)

        self.background = self.surface.copy()
        self._create_and_place_elements()

        # 👂 Subscribe to the event that starts the turn
        self.event_bus.subscribe("TURN_STARTED", self.on_turn_started)

    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        # This logic is standard across our panels
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = self.assets_state.get("UI_ELEMENT_PADDING", (20, 20))
        current_y = (self.surface.get_height() - content_h) / 2 + pad_y
        start_x_offset = (self.surface.get_width() - content_w) / 2

        for i, row_items in enumerate(self.layout_blueprint):
            row_width = self.dims['row_widths'][i]
            current_x = start_x_offset + (content_w - row_width) / 2
            for item in row_items:
                item_id = item.get("id")
                event_id = item_id.replace("event_", "")
                element_def = self.element_definitions.get(item_id)
                if not element_def: continue

                elem_dims_data = self.dims['element_dims'][item_id]
                elem_w, elem_h = elem_dims_data["final_size"]
                element_rect = pygame.Rect(current_x, current_y, elem_w, elem_h)

                # ✨ FIX: Get the pre-wrapped lines from the dims data
                wrapped_lines = elem_dims_data["wrapped_lines"]
                text_block = UITextBlock(element_rect, wrapped_lines, element_def["style"], self.assets_state)

                self.event_displays[event_id] = text_block
                
                current_x += elem_w + pad_x
            row_height = self.dims['row_heights'][i]
            current_y += row_height + pad_y

    def on_turn_started(self, event_data=None):
        """
        Event handler for the start of a turn. This now immediately determines
        the outcome and tells the GameManager, then starts the visual animation.
        """
        # 🧠 1. Immediately select the event and post the result. This is the core logic.
        if not event_data or "player" not in event_data:
            return
        final_event = self.manager.set_new_active_event()
        if not final_event:
            return
        self.event_bus.post("MIGRATION_EVENT_SELECTED", {"player": event_data["player"], "event": final_event})

        # 🎨 2. Start the purely visual "fluff" animation.
        self.start_turn_animation(final_event)


    def start_turn_animation(self, final_event):
        """Initiates the 'fortune wheel' animation to select a new event."""

        # ✨ Increment the cycle ID. Any animations from a previous cycle will now be invalid.
        self.animation_cycle_id += 1
        current_cycle = self.animation_cycle_id
        
        self.is_animating = True        
        if DEBUG: print(f"[MigrationPanel] 🎰 Fortune wheel starting... secretly chose '{final_event.event_id}'.")

        # 2. 📝 Set up the animation sequence.
        # Get all event IDs in the order they appear on screen.
        all_event_ids = [event.event_id for event in self.manager.events]
        
        # Define how many times to "spin" and how fast.
        spins = 2
        animation_sequence = (all_event_ids * spins) + all_event_ids[:all_event_ids.index(final_event.event_id) + 1]
        animation_duration = 0.12 # seconds per flash

        # 3. ✨ Define the recursive function that will create the chain.
        def run_animation_step(index):

            # 🛡️ Guard clause: If a new animation has started, abort this old one.
            if current_cycle != self.animation_cycle_id:
                return

            # ✨ Get the style dictionaries once from our central system.
            style_muted = get_style("migration_event_muted")
            style_highlight = get_style("migration_event_active")

            # De-highlight the previous item
            if index > 0:
                prev_event_id = animation_sequence[index - 1]
                self.event_displays[prev_event_id].text_color = style_muted["text_color"]

            # If we are at the end of the sequence, we're done.
            if index >= len(animation_sequence):
                # ✨ FIX: Manually ensure the final item is and stays highlighted.
                self.event_displays[self.manager.active_event.event_id].text_color = style_highlight["text_color"]
                self.is_animating = False
                if DEBUG: print(f"[MigrationPanel] ✅ Animation finished. Event '{self.manager.active_event.event_id}' is active.")
                return

            # Highlight the current item
            current_event_id = animation_sequence[index]
            target_display = self.event_displays[current_event_id]

            # This is our simple "flash" from gray to white. We can make this more complex later.
            self.tween_manager.add_tween(
                target_display, 'value', key_to_animate='text_color', drawable_type='generic',
                start_val=style_muted["text_color"], end_val=style_highlight["text_color"],
                duration=animation_duration, on_complete=lambda: run_animation_step(index + 1)
            )

        # 4. 🚀 Kick off the animation chain from the first item.
        run_animation_step(0)

    def update(self, notebook):
        """Draws child elements and publishes the panel to the renderer."""
        self.surface.blit(self.background, (0, 0))
        for display in self.event_displays.values():
            # The offset is the panel's top-left corner relative to the display component's rect
            display.draw(self.surface, offset=(0,0))
        super().update(notebook)