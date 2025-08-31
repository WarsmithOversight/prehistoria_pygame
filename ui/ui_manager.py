# ui_manager.py
# Handles the creation, management, and rendering of all UI elements.

from .ui_palette_panel import UIPalettePanel

DEBUG = True

# ──────────────────────────────────────────────────
# ⚙️ UI Orchestrator
# ──────────────────────────────────────────────────

class UIManager:
    """Orchestrates all UI components."""
    def __init__(self, persistent_state, assets_state, tile_objects):
            
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.panels = {}
        
        # List of Panels
        self.panels["ui_palette"] = UIPalettePanel(persistent_state, assets_state, tile_objects)

        if DEBUG:
            print(f"[UIManager] ✅ All UI panels instantiated.")
                        
    def handle_events(self, events, mouse_pos):
        """
        Checks for mouse collision with any panel and propagates events.
        Returns True if the mouse is over any UI element, False otherwise.
        """
        # First, determine if the mouse is over ANY panel
        mouse_is_over_ui = False
        for panel in self.panels.values():
            if panel.rect and panel.rect.collidepoint(mouse_pos):
                mouse_is_over_ui = True
                break # No need to check other panels

        # If the mouse is over a UI element, pass events to the handlers
        if mouse_is_over_ui:
            for panel in self.panels.values():
                if hasattr(panel, 'handle_events'):
                    panel.handle_events(events, mouse_pos)

        return mouse_is_over_ui
    
    def update(self, notebook):
        """Updates all active panels, causing them to publish to the notebook."""
        for panel in self.panels.values():
            panel.update(notebook)

