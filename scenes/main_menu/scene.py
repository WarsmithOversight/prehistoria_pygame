# main_menu/scene.py
# The first scene the player sees when booting the game

from load_ui_assets import load_all_ui_assets
from scenes.main_menu.ui import MainMenuPanel

# ──────────────────────────────────────────────────
# 🏛️ Main Menu Scene
# ──────────────────────────────────────────────────

class MainMenuScene:
    def __init__(self, manager):

        # Stores a reference to the scene manager and global state objects
        self.manager = manager; self.persistent_state = manager.persistent_state
        self.assets_state = manager.assets_state; self.notebook = manager.notebook
        
        # Initializes the main menu panel to None
        self.main_menu_panel = None

    def on_enter(self, data=None):
        '''Called at the end of SceneManager init.'''

        # Loads all UI assets from disk
        load_all_ui_assets(self.assets_state, self.persistent_state)

        # Creates an instance of the MainMenuPanel
        self.main_menu_panel = MainMenuPanel(self.persistent_state, self.assets_state, self)
        
        # Gets the screen dimensions
        screen_w, screen_h = self.persistent_state["pers_screen"].get_size()
        
        # Gets the panel's rect and centers it on the screen
        panel_rect = self.main_menu_panel.rect
        panel_rect.center = (screen_w / 2, screen_h / 2)
        self.main_menu_panel.rect = panel_rect

    def on_exit(self):
        '''Cleans up the main menu panel from the notebook'''
        if self.main_menu_panel and self.main_menu_panel.drawable_key in self.notebook:
            del self.notebook[self.main_menu_panel.drawable_key]

    def handle_events(self, events, mouse_pos):
        '''Delegates event handling to the menu panel if it exists and a transition isn't happening'''
        if self.main_menu_panel and not self.manager.is_transitioning:
            self.main_menu_panel.handle_events(events, mouse_pos)

    def update(self, dt):
        '''Delegates the update call to the menu panel if it exists'''
        if self.main_menu_panel:
            self.main_menu_panel.update(self.notebook)