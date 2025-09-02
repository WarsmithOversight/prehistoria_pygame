# scene_manager.py
# Orchestrates the flow of the game through different scenes (e.g., main menu, loading, in-game).

import pygame, time, json
import threading, queue
from ui.ui_welcome_panel import UIWelcomePanel
from ui.ui_main_menu import MainMenuPanel
from load_assets import *
from world_generation.initialize_tiledata import *
from world_generation.generate_terrain import *
from world_generation.elevation import run_elevation_generation
from world_generation.rivers import run_river_generation
from world_generation.biomes import assign_biomes_to_regions
from world_generation.tile import create_tile_objects_from_data
from collectibles import seed_collectibles
from audio_manager import AudioManager
from tween_manager import TweenManager

# Import controllers that will be used in the InGameScene
from camera_controller import CameraController
from map_interactor import MapInteractor
from event_bus import EventBus
from player import Player
from game_manager import GameManager
from ui.ui_manager import UIManager

DEBUG = True
DEV_FADE_OUT_DURATION = 1  # seconds
DEV_FADE_IN_DURATION = 1.5   # seconds

# ──────────────────────────────────────────────────
# 🎬 Scene Manager
# ──────────────────────────────────────────────────

class SceneManager:
    """Orchestrates scene flow using a tween-based fading system."""
    def __init__(self, persistent_state, assets_state, variable_state, notebook, tween_manager):
        
        # Stores references to global game state objects
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.variable_state = variable_state
        self.notebook = notebook
        self.tween_manager = tween_manager

        # Sets the main game loop flag to True
        self.running = True

        # A flag to prevent multiple scene transitions at once
        self.is_transitioning = False

        # Initializes all scenes and stores them in a dictionary
        self.scenes = {
            "MAIN_MENU": MainMenuScene(self),
            "LOADING": LoadingScene(self),
            "IN_GAME": InGameScene(self)
        }

        # Sets the initial active scene
        self.active_scene_key = "MAIN_MENU"
        self.active_scene = self.scenes[self.active_scene_key]

        # Calls the on_enter method for the first scene
        self.active_scene.on_enter()

       # Kick off the initial fade-in for the very first scene.
        self.tween_manager.add_tween(
            target_dict=self.notebook['FADE'],
           animation_type='fade',
           start_val=self.notebook['FADE'].get('value', 255),
           end_val=0,
           duration=DEV_FADE_IN_DURATION
       )

    def change_scene(self, new_scene_key, data=None, fade_out_duration=DEV_FADE_OUT_DURATION, fade_in_duration=DEV_FADE_IN_DURATION, on_fade_in_complete=None):
        '''When called, fades out, starts the next scene, and fades it in'''
        # Prevents a new transition if one is already in progress
        if self.is_transitioning: return

        # Sets the flag to indicate a transition is starting
        self.is_transitioning = True

        def on_fade_out_complete():
            # Exits the current scene
            self.active_scene.on_exit()

            # Updates the active scene to the new one
            self.active_scene_key = new_scene_key
            self.active_scene = self.scenes[new_scene_key]

            # Enters the new scene
            self.active_scene.on_enter(data)

            # Create the fade-in tween
            def on_final_transition_complete():

                # Resets the transition flag when the final fade-in is done
                self.is_transitioning = False

                # Calls the optional callback function if provided
                if on_fade_in_complete:
                    on_fade_in_complete()

            # Starts the fade-in animation
            self.tween_manager.add_tween(
                target_dict=self.notebook['FADE'],
                animation_type='fade',
                start_val=self.notebook['FADE'].get('value', 255), end_val=0, duration=fade_in_duration,
                on_complete=on_final_transition_complete
            )

        # Starts the initial fade-out animation
        self.tween_manager.add_tween(
            target_dict=self.notebook['FADE'],
            animation_type='fade',
            start_val=self.notebook['FADE'].get('value', 0), end_val=255, duration=fade_out_duration,
            on_complete=on_fade_out_complete
        )

    def handle_events(self, events, mouse_pos):
        '''Delegates event handling to the active scene'''
        self.active_scene.handle_events(events, mouse_pos)

    def update(self, dt):
        '''Delegates the update call to the active scene'''
        self.active_scene.update(dt)

    def quit_game(self):
        '''Sets the running flag to False to exit the main game loop'''
        self.running = False

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
        load_all_ui_assets(self.assets_state)

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

# ──────────────────────────────────────────────────
# ⏳ Loading Scene
# ──────────────────────────────────────────────────
class LoadingScene:
    def __init__(self, manager):

        # Stores references to global game state objects
        self.manager = manager
        self.persistent_state = manager.persistent_state
        self.assets_state = manager.assets_state
        self.variable_state = manager.variable_state
        self.notebook = manager.notebook

        # Creates an instance of the audio manager
        self.audio_manager = AudioManager()

        # Initializes flags and variables for the loading process
        self.has_started_loading = False
        self.loading_thread = None
        self.result_queue = queue.Queue()

    def update(self, dt):
        # While the loading thread is running, check the queue for a result.
        if self.loading_thread and not self.result_queue.empty():

            # Retrieve the loaded data from the queue.
            loaded_tile_objects = self.result_queue.get()

            # Stores the loaded tile objects in the notebook
            self.notebook['tile_objects'] = loaded_tile_objects

            # Mark the thread as joined.
            self.loading_thread.join()
            self.loading_thread = None

            # Prime the clock after the long process.
            self.manager.persistent_state["pers_clock"].tick()

            # Now that loading is complete, trigger the transition.
            self.manager.change_scene("IN_GAME")
    
    def on_enter(self, data=None):

        # Resets the loading flag
        self.has_started_loading = False

        # Creates a black surface for the splash screen
        screen = self.persistent_state["pers_screen"]
        splash_surface = pygame.Surface(screen.get_size())
        splash_surface.fill((0, 0, 0))
        try:

            # 🖼️ Load and Scale the Logo
            # Loads the splash screen image
            splash_image = pygame.image.load("splash.png").convert_alpha()
            
            # Define how wide the logo should be as a ratio of screen width.
            LOGO_WIDTH_RATIO = 0.5
            
            # Gets the original image dimensions
            original_w, original_h = splash_image.get_size()
            
            # Calculates the new width based on the screen size ratio
            target_w = int(screen.get_width() * LOGO_WIDTH_RATIO)
            
            # Calculates the aspect ratio and new height
            aspect_ratio = original_h / original_w
            target_h = int(target_w * aspect_ratio)
            
            # Scales the logo smoothly to the new dimensions
            scaled_logo = pygame.transform.smoothscale(splash_image, (target_w, target_h))
            
            # Gets the rectangle for the scaled logo and centers it
            splash_rect = scaled_logo.get_rect(center=screen.get_rect().center)
            
            # Blits the scaled logo onto the splash surface
            splash_surface.blit(scaled_logo, splash_rect)        
        
        except pygame.error: pass

        # Renders the loading text
        font = get_font("regular_large")
        text_surf = font.render("Prehistoria Digital Prototype ... Loading ...", True, (200, 200, 200))
        
        # Gets the rectangle for the text and positions it
        text_rect = text_surf.get_rect(bottomleft=(20, screen.get_height() - 20))
        
        # Blits the text onto the splash surface
        splash_surface.blit(text_surf, text_rect)
        
        # Retrieves the z-index formula for splash screens
        z_formula = self.persistent_state["pers_z_formulas"]["splash_screen"]

        # Adds the splash screen surface to the notebook as a drawable
        self.notebook['SPLASH'] = {'type': 'splash_screen', 'surface': splash_surface, 'z': z_formula(0)}
    
    def start_load_process(self):
        """This is now called by the SceneManager after the fade-in is complete."""
        
        # Checks if the loading process has already started
        if not self.has_started_loading:

            # Sets the flag to indicate loading has begun
            self.has_started_loading = True
            
            # The target function for our thread. It will run run_load_sequence
            # and put the return value into our queue.
            def worker():

                # 💿 Load all sound effects from the specified directory.
                self.audio_manager.load_sfx_directory("sfx")

                # Plays the game's soundtrack
                self.audio_manager.play_music("soundtrack.mp3")

                # Runs the main world generation sequence
                tile_objects = self.run_load_sequence()

                # Puts the result of the loading sequence into the queue
                self.result_queue.put(tile_objects)

            # Creates and starts a new thread for the worker function
            self.loading_thread = threading.Thread(target=worker)
            self.loading_thread.start()

    def _run_timed_step(self, name, func, args):

        # Records the start time of the function call
        start_time = time.time()

        # Calls the function with the provided arguments
        result = func(*args)

        # Records the end time
        end_time = time.time()

        # Prints the time taken to a readable format
        print(f"  - {name:<25} took {end_time - start_time:.4f} seconds.")

        # Returns the result of the function call
        return result

    def run_load_sequence(self):

        # Prints a header for the world generation log
        print("\n" + "─" * 40)
        print("Starting Full World Generation & Asset Load")
        print("─" * 40)

        # Records the total start time
        total_start_time = time.time()
        
        # Defines a list of asset loading steps
        asset_steps = [
            ("Load Tileset Assets", load_tileset_assets, (self.assets_state, self.persistent_state)),
            ("Load Coast Assets", load_coast_assets, (self.assets_state, self.persistent_state)),
            ("Load River Assets", load_river_assets, (self.assets_state, self.persistent_state)),
            ("Load River Mouth Assets", load_river_mouth_assets, (self.assets_state, self.persistent_state)),
            ("Load River End Assets", load_river_end_assets, (self.assets_state, self.persistent_state)),
            ("Load Player Assets", load_player_assets, (self.assets_state, self.persistent_state)),
            ("Create Collectible Assets", create_collectibles_assets, (self.assets_state, self.persistent_state)),
            ("Create Glow Masks", create_glow_mask, (self.persistent_state, self.assets_state)),
            ("Create Tinted Glows", create_tinted_glow_masks, (self.persistent_state, self.assets_state)),
            ("Load Indicator Asset", load_indicator_asset, (self.assets_state, self.persistent_state)),
            ]
        
        # Iterates through the list and runs each asset loading step
        for name, func, args in asset_steps: self._run_timed_step(name, func, args)
        
        # Treat tiledata as a temporary, local variable for the generation process
        # Runs the step to initialize region seeds
        self._run_timed_step("Initialize Region Seeds", initialize_region_seeds, (self.persistent_state, self.variable_state))
        
        # Runs the step to initialize the tile data
        local_tiledata = self._run_timed_step("Initialize Tiledata", initialize_tiledata, (self.persistent_state, self.variable_state))
        
        # Defines a list of world generation steps
        world_gen_steps = [("Calculate Map Center", calculate_and_store_map_center, (local_tiledata, self.persistent_state)),("Add Dist from Center", add_distance_from_center_to_tiledata, (local_tiledata, self.persistent_state)),("Add Dist from Ocean", add_distance_from_ocean_to_tiledata, (local_tiledata, self.persistent_state)),("Calculate Monsoon Bands", calculate_monsoon_bands, (local_tiledata, self.persistent_state)),("Tag Continent Spine", tag_continent_spine, (local_tiledata, self.persistent_state)),("Tag Initial Ocean", tag_initial_ocean, (local_tiledata, self.variable_state)),("Tag Ocean Coastline", tag_ocean_coastline, (local_tiledata, self.persistent_state)),("Tag Mountains", tag_mountains, (local_tiledata, self.persistent_state)), ("Sculpt Mountain Ranges", sculpt_mountain_ranges, (local_tiledata, self.persistent_state)), ("Run Elevation Generation", run_elevation_generation, (local_tiledata, self.persistent_state)),("Assign Biomes", assign_biomes_to_regions, (local_tiledata, self.persistent_state)),("Tag Lowlands", tag_lowlands, (local_tiledata, self.persistent_state)),("Tag Mountain Ranges", tag_mountain_range, (local_tiledata,)), ("Tag Central Desert", tag_central_desert, (local_tiledata, self.persistent_state)),("Tag Adj. Scrublands", tag_adjacent_scrublands, (local_tiledata, self.persistent_state)),("Add Windward/Leeward", add_windward_and_leeward_tags, (local_tiledata, self.persistent_state)),
            # This is the corrected sequence for rivers, shorelines, and final terrain
            ("Run River Generation", run_river_generation, (local_tiledata, self.persistent_state)),
            ("Resolve Shorelines", resolve_shoreline_bitmasks, (local_tiledata, self.persistent_state)),
            ("Fill Terrain from Tags", fill_in_terrain_from_tags, (local_tiledata,)),
        ]

        # Iterates through the list and runs each world generation step
        for name, func, args in world_gen_steps: self._run_timed_step(name, func, args)

        # Runs the final step to create the drawable tile objects
        tile_objects = self._run_timed_step("Create Tile Objects", create_tile_objects_from_data, (local_tiledata,))

        # Records the total end time
        total_end_time = time.time()

        # Prints the total load time
        print("─" * 40)
        print(f"Total Load Time: {total_end_time - total_start_time:.4f} seconds.")
        print("─" * 40 + "\n")

        # Returns the final tile objects
        return tile_objects
        
    def on_exit(self):

        # Cleans up the splash screen from the notebook when the scene is exited
        if 'SPLASH' in self.notebook: del self.notebook['SPLASH']
    
    def handle_events(self, events, mouse_pos): pass

# ──────────────────────────────────────────────────
# 🎮 In-Game Scene
# ──────────────────────────────────────────────────
class InGameScene:
    def __init__(self, manager):

        # Stores references to global game state objects
        self.manager = manager
        self.persistent_state = manager.persistent_state
        self.assets_state = manager.assets_state
        self.variable_state = manager.variable_state
        self.notebook = manager.notebook

        # Initializes a dictionary to hold the game's controllers
        self.controllers = {}
        
# scene_manager.py -> InGameScene

    def on_enter(self, data=None):
        print("[InGameScene] ✅ Entered. Initializing controllers in a paused state...")
        
        # 📜 Load species data from a JSON file.
        with open("species.json", "r") as f:
            all_species_data = json.load(f)

        # 🐣 Create player instances first, so we know their starting locations.
        players = [
            Player(player_id=1, lineage_name="frog", all_species_data=all_species_data, tile_objects=self.notebook['tile_objects'], notebook=self.notebook, assets_state=self.assets_state, persistent_state=self.persistent_state),
            Player(player_id=2, lineage_name="bird", all_species_data=all_species_data, tile_objects=self.notebook['tile_objects'], notebook=self.notebook, assets_state=self.assets_state, persistent_state=self.persistent_state)
        ]
        
        # 💎 Seed collectibles, now avoiding the players' starting regions.
        collectible_instances = seed_collectibles(
            self.persistent_state, self.notebook['tile_objects'],
            self.notebook, self.manager.tween_manager, players
        )

        # ⚙️ Create core controllers.
        camera_controller = CameraController(self.persistent_state, self.variable_state, self.manager.tween_manager)
        event_bus = EventBus()
 
        # 🕹️ Create the main game manager instance.
        game_manager = GameManager(
            players, collectible_instances, self.manager.scenes["LOADING"].audio_manager,
            camera_controller, self.notebook['tile_objects'], event_bus, 
            self.manager.tween_manager, self.notebook, self.persistent_state, self.variable_state
        )
 
        # Assembles the full dictionary of controllers
        self.controllers = {
            'camera': camera_controller,
            'interactor': MapInteractor(),
            'event_bus': event_bus,
            'ui': UIManager(self.persistent_state, self.assets_state, self.notebook['tile_objects']),
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
       print("[InGameScene] ✅ Continue clicked. Game is now active.")

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
            # TODO: This is where the game happens
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
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game_manager.advance_turn()
    
    def update(self, dt):

        # Exits if controllers are not initialized
        if not self.controllers: return

        # Updates the game based on the paused state
        if self.controllers['game'].is_paused:
            if self.welcome_panel:
                self.welcome_panel.update(self.notebook)
        else:
            self.controllers['ui'].update(self.notebook)
            self.controllers['game'].update(dt)

        # Updates the camera controller regardless of the game state
        self.controllers['camera'].update(self.persistent_state, self.variable_state)

