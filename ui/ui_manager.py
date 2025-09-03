# ui/ui_manager.py
# Handles the creation, management, and rendering of all UI elements.

from .ui_palette_panel import UIPalettePanel
from .ui_family_portrait import UIFamilyPortraitPanel
from .ui_hazard_queue import HazardQueuePanel

DEBUG = True

# ──────────────────────────────────────────────────
# ⚙️ UI Orchestrator
# ──────────────────────────────────────────────────

class UIManager:
    """Orchestrates all UI components, including static and dynamic panels."""
    def __init__(self, persistent_state, assets_state, event_bus, initial_player, notebook, tween_manager, hazard_deck):
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.event_bus = event_bus
        self.notebook = notebook
        self.tween_manager = tween_manager
        self.hazard_deck = hazard_deck

        # --- Panel Management ---
        # For persistent panels that are always on screen
        self.static_panels = {}
        # For panels that change based on game state (e.g., active player)
        self.portrait_panel = None

        # 👂 Subscribe to game-wide events
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)

        # --- Initial Panel Creation ---
        # Create static panels like the palette here
        self.static_panels["ui_palette"] = UIPalettePanel(persistent_state, assets_state, notebook['tile_objects'], self.event_bus)
        self.static_panels["hazard_queue"] = HazardQueuePanel(persistent_state, assets_state, self.tween_manager, self.hazard_deck, self.event_bus)
 
        # Create the initial portrait for the starting player
        self.create_portrait_panel(initial_player)

        if DEBUG:
            print("[UIManager] ✅ UIManager instantiated and subscribed to events.")

    def on_active_player_changed(self, new_player):
        """Event handler that fires when the turn changes, rebuilding player-specific UI."""
        if DEBUG: print(f"[UIManager] 👂 Heard ACTIVE_PLAYER_CHANGED for Player {new_player.player_id}. Rebuilding portrait.")
        
        # 1. 🗑️ Tear down the old panel using our new destroy method
        if self.portrait_panel:
            self.portrait_panel.destroy(self.notebook) # Use the correct notebook reference

        # 2. 🏗️ Rebuild the panel for the new player
        self.create_portrait_panel(new_player)

    def create_portrait_panel(self, player):
        """
        Helper method to instantiate a new family portrait panel,
        but only if the required assets actually exist.
        """
        species_name = player.species_name
        
        # 🛡️ Guard clause: Check if the assets for this species' portrait were loaded.
        if "family_portraits" not in self.assets_state or \
           species_name not in self.assets_state["family_portraits"]:
            if DEBUG:
                print(f"[UIManager] ⚠️  No family portrait assets found for '{species_name}'. Skipping panel creation.")
            return # Fail silently by not creating the panel.
 
        # If the assets exist, proceed with creating the panel.
        self.portrait_panel = UIFamilyPortraitPanel(
            player=player,
            persistent_state=self.persistent_state,
            assets_state=self.assets_state,
            event_bus=self.event_bus
        )

    def handle_events(self, events, mouse_pos):
        """
        Checks for mouse collision and propagates events to all active panels.
        Returns True if the mouse is over any UI element.
        """
        all_panels = list(self.static_panels.values())
        if self.portrait_panel:
            all_panels.append(self.portrait_panel)

        mouse_is_over_ui = any(p.rect and p.rect.collidepoint(mouse_pos) for p in all_panels)

        if mouse_is_over_ui:
            for panel in all_panels:
                if hasattr(panel, 'handle_events'):
                    panel.handle_events(events, mouse_pos)

        return mouse_is_over_ui

    def update(self, notebook):
        """Updates all active panels, causing them to publish to the notebook."""
        # Update static panels
        for panel in self.static_panels.values():
            panel.update(notebook)
        
        # Update the dynamic portrait panel if it exists
        if self.portrait_panel:
            self.portrait_panel.update(notebook)

    def toggle_hazard_queue(self):
        """Delegates the toggle request to the hazard queue panel."""
        if "hazard_queue" in self.static_panels:
            self.static_panels["hazard_queue"].toggle_visibility()