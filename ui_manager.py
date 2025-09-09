# ui/ui_manager.py
# Handles the creation, management, and rendering of all UI elements.

from scenes.game_scene.ui.ui_palette_panel import UIPalettePanel
from scenes.game_scene.ui.ui_family_portrait import UIFamilyPortraitPanel
from scenes.game_scene.migration_event_manager import MigrationEventPanel
from scenes.game_scene.ui.ui_extinction_panel import UIExtinctionPanel

DEBUG = True

# ──────────────────────────────────────────────────
# ⚙️ UI Orchestrator
# ──────────────────────────────────────────────────

class UIManager:
    """Orchestrates all UI components, including static and dynamic panels."""
    def __init__(self, persistent_state, assets_state, event_bus, initial_player, notebook, tween_manager):
            self.persistent_state = persistent_state
            self.assets_state = assets_state
            self.event_bus = event_bus
            self.notebook = notebook
            self.tween_manager = tween_manager
            self.players = [initial_player]
            self.active_player = initial_player
            self.is_low_pop_glow_active = False

            # --- Panel Management ---
            # For persistent panels that are always on screen
            self.static_panels = {}
            # For panels that change based on game state (e.g., active player)
            self.portrait_panel = None

            # 👂 Subscribe to game-wide events
            self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)
            self.event_bus.subscribe("PLAYER_POPULATION_CHANGED", self.on_population_changed)
            self.event_bus.subscribe("PLAYER_EXTINCT", self.on_player_extinct)


            # --- Initial Panel Creation ---
            # Create static panels like the palette here
            self.static_panels["ui_palette"] = UIPalettePanel(persistent_state, assets_state, notebook['tile_objects'], self.event_bus)

            # ✨ Create the new Migration Event panel
            self.static_panels["migration_events"] = MigrationEventPanel(
                persistent_state=persistent_state,
                assets_state=assets_state,
                tween_manager=self.tween_manager,
                event_bus=event_bus)

            # Create the initial portrait for the starting player
            self.create_portrait_panel(initial_player)

            # ✨ Create the screen glow drawable in the notebook.
            z_formula = self.persistent_state["pers_z_formulas"]["ui_panel"]
            self.notebook['SCREEN_GLOW'] = {
                'type': 'screen_glow_overlay', 'color': 'red', 'alpha': 0, 'z': z_formula(0) + 0.1
            }

            if DEBUG:
                print("[UIManager] ✅ UIManager instantiated and subscribed to events.")
         
    def on_population_changed(self, data):
        """Checks if any player has a low population to activate the persistent glow."""
        glow_drawable = self.notebook.get('SCREEN_GLOW')
        if not glow_drawable: return
 
        # This event doesn't tell us which player changed, so we must check all.
        # A more advanced system might pass the specific player in the event data.
        is_any_player_low = any(p.current_population == 1 for p in self.players)
 
        if is_any_player_low:
            self.is_low_pop_glow_active = True
            glow_drawable['alpha'] = 255 # Turn glow on fully
        else:
            self.is_low_pop_glow_active = False
            glow_drawable['alpha'] = 0 # Turn it off

    def on_player_extinct(self, data):
        """Handles the game over state by showing the extinction panel."""
        # 🎨 If there isn't already a game over panel, create one.
        if "extinction_panel" not in self.static_panels:
            self.static_panels["extinction_panel"] = UIExtinctionPanel(self.persistent_state, self.assets_state)

    def on_active_player_changed(self, new_player):
        """Event handler that fires when the turn changes, rebuilding player-specific UI."""
        # Update our reference to the currently active player
        self.active_player = new_player
        
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
            event_bus=self.event_bus,
            tween_manager=self.tween_manager
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