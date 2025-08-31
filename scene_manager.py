# scene_manager.py
# Orchestrates the flow of the game through different scenes (e.g., main menu, loading, in-game).

import pygame, time, os, json
import threading, queue
from ui.ui_components import BasePanel, Button, assemble_organic_panel, UI_ELEMENT_PADDING
from ui.ui_dimensions import get_panel_dimensions
from ui.ui_welcome_panel import UIWelcomePanel
from load_assets import *
from world_generation.initialize_tiledata import *
from world_generation.generate_terrain import *
from world_generation.elevation import run_elevation_generation
from world_generation.rivers import run_river_generation
from world_generation.biomes import assign_biomes_to_regions
from world_generation.tile import create_tile_objects_from_data
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
        self.manager = manager; self.persistent_state = manager.persistent_state; self.assets_state = manager.assets_state
        self.variable_state = manager.variable_state; self.notebook = manager.notebook; self.audio_manager = AudioManager()
        self.has_started_loading = False
        self.loading_thread = None
        self.result_queue = queue.Queue()

    def update(self, dt):
        # While the loading thread is running, check the queue for a result.
        if self.loading_thread and not self.result_queue.empty():
            # Retrieve the loaded data from the queue.
            loaded_tile_objects = self.result_queue.get()
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

        # ✨ FIX: Use the new centralized get_font function.
        font = get_font("regular_medium")
        text_surf = font.render("Prehistoria Digital Prototype ... Loading ...", True, (200, 200, 200))
        text_rect = text_surf.get_rect(bottomleft=(20, screen.get_height() - 20))
        splash_surface.blit(text_surf, text_rect)
        z_formula = self.persistent_state["pers_z_formulas"]["splash_screen"]
        self.notebook['SPLASH'] = {'type': 'splash_screen', 'surface': splash_surface, 'z': z_formula(0)}
    
    def start_load_process(self):
        """This is now called by the SceneManager after the fade-in is complete."""
        if not self.has_started_loading:
            self.has_started_loading = True
            # The target function for our thread. It will run run_load_sequence
            # and put the return value into our queue.
            def worker():
                self.audio_manager.play_music("soundtrack.mp3")
                tile_objects = self.run_load_sequence()
                self.result_queue.put(tile_objects)

            self.loading_thread = threading.Thread(target=worker)
            self.loading_thread.start()


    def _run_timed_step(self, name, func, args):
        start_time = time.time(); result = func(*args); end_time = time.time()
        print(f"  - {name:<25} took {end_time - start_time:.4f} seconds.")
        return result

    def run_load_sequence(self):
        print("\n" + "─" * 40); print("Starting Full World Generation & Asset Load"); print("─" * 40)
        total_start_time = time.time()
        
        asset_steps = [("Load Tileset Assets", load_tileset_assets, (self.assets_state, self.persistent_state)),("Load Coast Assets", load_coast_assets, (self.assets_state, self.persistent_state)),("Load River Assets", load_river_assets, (self.assets_state, self.persistent_state)),("Load River Mouth Assets", load_river_mouth_assets, (self.assets_state, self.persistent_state)),("Load River End Assets", load_river_end_assets, (self.assets_state, self.persistent_state)),("Load Player Assets", load_player_assets, (self.assets_state, self.persistent_state)),("Create Glow Masks", create_glow_mask, (self.persistent_state, self.assets_state)),("Create Tinted Glows", create_tinted_glow_masks, (self.persistent_state, self.assets_state)),]
        for name, func, args in asset_steps: self._run_timed_step(name, func, args)
        
        # Treat tiledata as a temporary, local variable for the generation process
        self._run_timed_step("Initialize Region Seeds", initialize_region_seeds, (self.persistent_state, self.variable_state))
        local_tiledata = self._run_timed_step("Initialize Tiledata", initialize_tiledata, (self.persistent_state, self.variable_state))
        
        world_gen_steps = [("Calculate Map Center", calculate_and_store_map_center, (local_tiledata, self.persistent_state)),("Add Dist from Center", add_distance_from_center_to_tiledata, (local_tiledata, self.persistent_state)),("Add Dist from Ocean", add_distance_from_ocean_to_tiledata, (local_tiledata, self.persistent_state)),("Calculate Monsoon Bands", calculate_monsoon_bands, (local_tiledata, self.persistent_state)),("Tag Continent Spine", tag_continent_spine, (local_tiledata, self.persistent_state)),("Tag Initial Ocean", tag_initial_ocean, (local_tiledata, self.variable_state)),("Tag Ocean Coastline", tag_ocean_coastline, (local_tiledata, self.persistent_state)),("Tag Mountains", tag_mountains, (local_tiledata, self.persistent_state)),("Run Elevation Generation", run_elevation_generation, (local_tiledata, self.persistent_state)),("Assign Biomes", assign_biomes_to_regions, (local_tiledata, self.persistent_state)),("Tag Lowlands", tag_lowlands, (local_tiledata, self.persistent_state)),("Tag Mountain Ranges", tag_mountain_range, (local_tiledata,)),("Sculpt Mountain Ranges", sculpt_mountain_ranges, (local_tiledata, self.persistent_state)),("Tag Central Desert", tag_central_desert, (local_tiledata, self.persistent_state)),("Tag Adj. Scrublands", tag_adjacent_scrublands, (local_tiledata, self.persistent_state)),("Add Windward/Leeward", add_windward_and_leeward_tags, (local_tiledata, self.persistent_state)),
            # This is the corrected sequence for rivers, shorelines, and final terrain
            ("Run River Generation", run_river_generation, (local_tiledata, self.persistent_state)),
            ("Resolve Shorelines", resolve_shoreline_bitmasks, (local_tiledata, self.persistent_state)),
            ("Fill Terrain from Tags", fill_in_terrain_from_tags, (local_tiledata,)),
        ]

        for name, func, args in world_gen_steps: self._run_timed_step(name, func, args)

        tile_objects = self._run_timed_step("Create Tile Objects", create_tile_objects_from_data, (local_tiledata,))

        total_end_time = time.time()
        print("─" * 40); print(f"Total Load Time: {total_end_time - total_start_time:.4f} seconds."); print("─" * 40 + "\n")
        return tile_objects
    
    def on_exit(self):
        if 'SPLASH' in self.notebook: del self.notebook['SPLASH']
    def handle_events(self, events, mouse_pos): pass

# ──────────────────────────────────────────────────
# 🎮 In-Game Scene
# ──────────────────────────────────────────────────
class InGameScene:
    def __init__(self, manager):
        self.manager = manager; self.persistent_state = manager.persistent_state; self.assets_state = manager.assets_state
        self.variable_state = manager.variable_state; self.notebook = manager.notebook
        self.controllers = {}
    def on_enter(self, data=None):
        print("[InGameScene] ✅ Entered. Initializing controllers in a paused state...")
        with open("species.json", "r") as f: all_species_data = json.load(f)
        players = [Player(player_id=1, species_name="frog", all_species_data=all_species_data, tile_objects=self.notebook['tile_objects'], notebook=self.notebook, assets_state=self.assets_state, persistent_state=self.persistent_state)]
        
        # 1. Create controllers that the GameManager depends on FIRST.
        camera_controller = CameraController(self.persistent_state, self.variable_state, self.manager.tween_manager)
        event_bus = EventBus()
 
        # 2. Now create the GameManager and pass the finished controllers to it.
        game_manager = GameManager(players, camera_controller, self.notebook['tile_objects'], event_bus, self.manager.tween_manager, self.notebook, self.persistent_state, self.variable_state)
 
        # 3. Assemble the final dictionary of all controllers.
        self.controllers = {
            'camera': camera_controller,
            'interactor': MapInteractor(),
            'event_bus': event_bus,
            'ui': UIManager(self.persistent_state, self.assets_state, self.notebook['tile_objects']),
            'game': game_manager
        }
       
        # --- Set up the initial "Welcome" camera state ---
        # 1. Directly set the camera to be fully zoomed out.
        camera = self.controllers['camera']
        camera.zoom = camera.zoom_config['min_zoom'] * 2
        camera._snap_zoom() # Ensure the new zoom is a valid step.

        # 2. Instantly center the camera on the map without animation.
        camera.center_on_map(self.persistent_state, self.variable_state, animated=False)
        self.welcome_panel = UIWelcomePanel(self.persistent_state, self.assets_state, self)

    
    def start_game(self):
       """Called by the welcome panel's continue button."""
       print("[InGameScene] ✅ Continue clicked. Game is now active.")

       # Unpause the game manager
       self.controllers['game'].unpause()
 
       # Remove the welcome panel from the screen
       if self.welcome_panel and self.welcome_panel.drawable_key in self.notebook:
           del self.notebook[self.welcome_panel.drawable_key]
       self.welcome_panel = None # Release the reference

    def on_exit(self):
        self.controllers = {}

        # Clean up any remaining drawables from the notebook
        keys_to_delete = [k for k in self.notebook if k not in ['FADE', 'tile_objects']]
        for k in keys_to_delete: del self.notebook[k]
    
    def handle_events(self, events, mouse_pos):
        if not self.controllers or self.manager.is_transitioning: return
        game_manager = self.controllers['game']
 
        if game_manager.is_paused:
            # --- Paused (Welcome Screen) Event Loop ---
            if self.welcome_panel:
                self.welcome_panel.handle_events(events, mouse_pos)
            self.controllers['camera'].handle_events(events, self.persistent_state)
            ui_handled = self.welcome_panel and self.welcome_panel.rect and self.welcome_panel.rect.collidepoint(mouse_pos)
            if not ui_handled:
                pan, _, _ = self.controllers['interactor'].handle_events(events, mouse_pos, self.notebook.get('tile_objects',{}), self.persistent_state, self.variable_state)
                if pan != (0,0): self.controllers['camera'].pan(pan[0], pan[1])
        else:
            # --- Active Game Event Loop ---
            self.controllers['camera'].handle_events(events, self.persistent_state)
            ui_handled = self.controllers['ui'].handle_events(events, mouse_pos)
            if not ui_handled:
                pan, click, hover = self.controllers['interactor'].handle_events(events, mouse_pos, self.notebook.get('tile_objects',{}), self.persistent_state, self.variable_state)
                game_manager.update_path_overlay(hover)
                if click: game_manager.handle_click(click)
                if pan != (0,0): self.controllers['camera'].pan(pan[0], pan[1])
            else:
                game_manager.update_path_overlay(None)
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game_manager.advance_turn()
    
    def update(self, dt):
        if not self.controllers: return
        if self.controllers['game'].is_paused:
            if self.welcome_panel:
                self.welcome_panel.update(self.notebook)
        else:
            self.controllers['ui'].update(self.notebook)
        self.controllers['camera'].update(self.persistent_state, self.variable_state)

# ──────────────────────────────────────────────────
# 📜 Main Menu Panel UI
# ──────────────────────────────────────────────────
class MainMenuPanel(BasePanel):
    def __init__(self, persistent_state, assets_state, scene):
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "main_menu_panel"; self.scene = scene

        self.button_definitions = {
            "new_world": {
                "type": "button", # Add the type definition
                "text_options": ["New World"],
                "style": {"font_size_key": "regular_large", "text_color": (255, 255, 255), "align": "center"},
                "action": self.on_new_world
            },
            "load_world": {
                "type": "button", # Add the type definition
                "text_options": ["Load Saved World"],
                "style": {"font_size_key": "regular_large", "text_color": (150, 150, 150), "align": "center"},
                "action": self.on_load_world
            },
            "dev_quickboot": {
                "type": "button", # Add the type definition
                "text_options": ["Dev Quickboot"],
                "style": {"font_size_key": "regular_large", "text_color": (255, 255, 255), "align": "center"},
                "action": self.on_dev_quickboot
            }
        }
        # ✨ NEW: Define a proper layout blueprint, just like the Welcome Panel
        self.layout_blueprint = [
            {"id": "new_world"},
            {"id": "load_world"},
            {"id": "dev_quickboot"}
        ]
        self.dims = get_panel_dimensions(self.button_definitions, self.layout_blueprint, self.assets_state)
        self.surface = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        self.elements = self._create_and_place_elements()
        
        # ✨ FIX: Create a pristine background and a separate drawing surface.
        self.background = assemble_organic_panel(self.dims["final_panel_size"], self.dims["panel_background_size"], self.assets_state)
        self.surface = self.background.copy() # The surface we will actually draw on.
        self.rect = self.surface.get_rect()
 
    def _create_and_place_elements(self):
        """Creates and positions all UI elements based on the calculated dimensions."""
        elements = []
        content_w, content_h = self.dims["panel_background_size"]
        pad_x, pad_y = UI_ELEMENT_PADDING
 
        start_x = (self.surface.get_width() - content_w) / 2
        current_y = (self.surface.get_height() - content_h) / 2 + pad_y
 
        for item in self.layout_blueprint:
            item_id = item.get("id")
            element_def = self.button_definitions.get(item_id)
            if not element_def: continue
 
            elem_dims_data = self.dims['element_dims'][item_id]
            elem_w, elem_h = elem_dims_data["final_size"]
            elem_x = start_x + (content_w - elem_w) / 2 # Center horizontally
            element_rect = pygame.Rect(elem_x, current_y, elem_w, elem_h)
 
            # Pass the main self.dims dictionary, which holds the uniform geometry
            button = Button(rect=element_rect, text=element_def["text_options"][0], assets_state=self.assets_state, style=element_def["style"], dims=self.dims, callback=element_def["action"])
            elements.append(button)
            current_y += elem_h + pad_y
        return elements

    def on_new_world(self):
        # Get the instance of the loading scene from the manager
        loading_scene = self.scene.manager.scenes["LOADING"]
        # Tell the manager to change scenes, and to call start_load_process when the fade-in is done.
        self.scene.manager.change_scene(
            "LOADING",
            on_fade_in_complete=loading_scene.start_load_process
        )
    
    def on_load_world(self):
        if DEBUG: print("[MainMenu] ⚠️ 'Load Saved World' is not yet implemented.")
    
    def on_dev_quickboot(self):
        persistent_state = self.scene.manager.persistent_state
        variable_state = self.scene.manager.variable_state

        persistent_state["pers_dev_quickboot"] = True
        persistent_state["pers_quickboot_zoom"] = 0.40

        # Make the zoom config a single legal step.
        persistent_state["pers_zoom_config"] = {
            "min_zoom": persistent_state["pers_quickboot_zoom"],
            "max_zoom": persistent_state["pers_quickboot_zoom"],
            "zoom_interval": 1.0,      # any value; snapping will clamp to min/max anyway
            "settle_ms": 0
        }

        # Seed current zoom to the fixed value (so first render is correct)
        variable_state["var_current_zoom"] = persistent_state["pers_quickboot_zoom"]

        # Proceed exactly like "New World" (or your prefab path—your choice)
        loading_scene = self.scene.manager.scenes["LOADING"]
        
        # Tell the manager to change scenes, and to call start_load_process when the fade-in is done.
        self.scene.manager.change_scene(
            "LOADING",
            on_fade_in_complete=loading_scene.start_load_process
        )

    def handle_events(self, events, mouse_pos):
        local_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        for element in self.elements: element.handle_events(events, local_mouse_pos)
    
    def update(self, notebook):
        # ✨ FIX: "Wipe" the surface by blitting the clean background onto it each frame.
        self.surface.blit(self.background, (0, 0))
        for element in self.elements: element.draw(self.surface)
        super().update(notebook)

