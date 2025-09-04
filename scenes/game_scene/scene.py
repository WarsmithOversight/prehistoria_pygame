# scenes/game_scene/scene.py

# 📚 Standard Library Imports
import json
import pygame

# 🌍 Project-Wide Imports
from ui_manager import UIManager

# 🎬 Scene-Specific Imports (from this folder)
from .event_bus import EventBus
from .hazard_deck import HazardDeck
from .player import Player
from .collectibles import seed_collectibles
from .camera_controller import CameraController
from .game_manager import GameManager
from .map_interactor import MapInteractor
from .ui_welcome_panel import UIWelcomePanel

# ──────────────────────────────────────────────────
# 🎮 Game Scene
# ──────────────────────────────────────────────────
class GameScene:
    def __init__(self, manager):

        # Stores references to global game state objects
        self.manager = manager
        self.persistent_state = manager.persistent_state
        self.assets_state = manager.assets_state
        self.variable_state = manager.variable_state
        self.notebook = manager.notebook

        # Initializes a dictionary to hold the game's controllers
        self.controllers = {}

    def on_enter(self, data=None):
        print("[GameScene] ✅ Entered. Initializing controllers in a paused state...")
        
        # 📜 Load species data from a JSON file.
        with open("scenes/game_scene/species.json", "r") as f:
            all_species_data = json.load(f)

        # ⚙️ Create the EventBus.
        event_bus = EventBus()

        # 🃏 Create the one and only hazard deck for the game.
        hazard_deck = HazardDeck()

        # 🐣 Create player instances first, so we know their starting locations.
        players = [
            Player(player_id=1, lineage_name="frog", all_species_data=all_species_data, tile_objects=self.notebook['tile_objects'], notebook=self.notebook, assets_state=self.assets_state, persistent_state=self.persistent_state, event_bus=event_bus),
            Player(player_id=2, lineage_name="bird", all_species_data=all_species_data, tile_objects=self.notebook['tile_objects'], notebook=self.notebook, assets_state=self.assets_state, persistent_state=self.persistent_state, event_bus=event_bus)
        ]
        
        # 💎 Seed collectibles, now avoiding the players' starting regions.
        collectible_instances = seed_collectibles(
            self.persistent_state, self.notebook['tile_objects'],
            self.notebook, self.manager.tween_manager, players
        )

        # ⚙️ Create core controllers.
        camera_controller = CameraController(self.persistent_state, self.variable_state, self.manager.tween_manager)
 
        # 🕹️ Create the main game manager instance.
        game_manager = GameManager(
            players, collectible_instances, self.manager.scenes["LOADING"].audio_manager,
            camera_controller, self.notebook['tile_objects'], event_bus, 
            self.manager.tween_manager, self.notebook, self.persistent_state, self.variable_state
        )

        # 🎨 Create the UI Manager, passing it the event bus and the starting player.
        ui_manager = UIManager(
            self.persistent_state, self.assets_state, event_bus, players[0],
            self.notebook, self.manager.tween_manager, hazard_deck
        )
 
        # Assembles the full dictionary of controllers
        self.controllers = {
            'camera': camera_controller,
            'interactor': MapInteractor(),
            'event_bus': event_bus,
            'ui': ui_manager,
            'game': game_manager
        }
       
        # Gets the camera controller instance
        camera = self.controllers['camera']

        # Sets the camera's zoom level
        camera.zoom = camera.zoom_config['min_zoom'] * 2

        # Ensures the camera snaps to a valid zoom step
        camera._snap_zoom() # Ensure the new zoom is a valid step.

        # Centers the camera on the world map
        camera.center_on_map(self.persistent_state, self.variable_state, animated=False)
        
        # Creates the welcome panel UI
        self.welcome_panel = UIWelcomePanel(self.persistent_state, self.assets_state, self)

    def start_game(self):
       """Called by the welcome panel's continue button."""
       print("[GameScene] ✅ Continue clicked. Game is now active.")

       # Unpause the game manager
       self.controllers['game'].unpause()
 
       # Remove the welcome panel from the screen
       if self.welcome_panel and self.welcome_panel.drawable_key in self.notebook:
           del self.notebook[self.welcome_panel.drawable_key]

       # Releases the reference to the welcome panel
       self.welcome_panel = None

    def on_exit(self):

        # Clears the controllers dictionary
        self.controllers = {}

        # Clean up any remaining drawables from the notebook
        # Finds all keys to delete from the notebook
        keys_to_delete = [k for k in self.notebook if k not in ['FADE', 'tile_objects']]
        
        # Iterates and deletes each key
        for k in keys_to_delete: del self.notebook[k]
    
    def handle_events(self, events, mouse_pos):

        # Exits if controllers are not yet initialized or a transition is in progress
        if not self.controllers or self.manager.is_transitioning: return
        
        # Gets the game manager instance
        game_manager = self.controllers['game']
 
         # Manages events based on whether the game is paused
        if game_manager.is_paused:

            # --- Paused (Welcome Screen) Event Loop ---
            if self.welcome_panel:
                self.welcome_panel.handle_events(events, mouse_pos)
            self.controllers['camera'].handle_events(events, self.persistent_state)
            
            # Delegate events to the UI, but not anything else since the game is paused
            ui_handled = self.welcome_panel and self.welcome_panel.rect and self.welcome_panel.rect.collidepoint(mouse_pos)
            
        else:
            # --- Active Game Event Loop ---
            self.controllers['camera'].handle_events(events, self.persistent_state)
            
            # Checks if the UI handled the event
            ui_handled = self.controllers['ui'].handle_events(events, mouse_pos)
            
            # If the UI didn't handle it, delegate to the map interactor
            if not ui_handled:
                pan, click, hover = self.controllers['interactor'].handle_events(events, mouse_pos, self.notebook.get('tile_objects',{}), self.persistent_state, self.variable_state)
                
                # Updates the path overlay based on the hover position
                game_manager.update_path_overlay(hover)

                # Handles a click event if it occurred
                if click: game_manager.handle_click(click)
                
                # Pans the camera if the interactor returns a pan value
                if pan != (0,0): self.controllers['camera'].pan(pan[0], pan[1])
            else:
                game_manager.update_path_overlay(None)
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        game_manager.advance_turn()
                    elif event.key == pygame.K_q:
                        self.controllers['ui'].toggle_hazard_queue()
    
    def update(self, dt):

        # Exits if controllers are not initialized
        if not self.controllers: return

        # Updates the game based on the paused state
        # 1. Update systems that run regardless of game state.
        self.controllers['camera'].update(self.persistent_state, self.variable_state)
        self.controllers['ui'].update(self.notebook)
 
        # 2. Update systems based on the paused state.
        if self.controllers['game'].is_paused:
            # While paused, we also need to update the welcome panel.
            if self.welcome_panel:
                self.welcome_panel.update(self.notebook)
        else:
            # Once unpaused, update the main game logic.
            self.controllers['game'].update(dt)