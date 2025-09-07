# scenes/loading_screen/scene.py

# 📚 Standard Library Imports
import pygame
import time
import threading
import queue
import json

#  Helper & Manager Imports from Project Root
from audio_manager import AudioManager
from load_tile_assets import *
from scenes.game_scene.load_assets import *
from ui.ui_font_and_styles import get_font, get_style

# 🌍 World Generation Imports (from this same folder)
from .initialize_tiledata import *
from .generate_terrain import *
from .elevation import *
from .rivers import *
from .biomes import *
from .tile import *

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
            splash_image = pygame.image.load("scenes/loading_screen/splash.png").convert_alpha()
            
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

        # ✨ Renders the loading text using the central style system
        loading_style = get_style("highlight") # "highlight" uses a large, regular font
        font = get_font(loading_style["font_size_key"])
        text_color = loading_style["text_color"]
        text_surf = font.render("Prehistoria Digital Prototype ... Loading ...", True, text_color)
        
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
                self.audio_manager.load_sfx_directory("scenes/game_scene/sfx")

                # Plays the game's soundtrack
                self.audio_manager.play_music("scenes/loading_screen/soundtrack.mp3")

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
            ("Load Portrait Assets", load_family_portrait_assets, (self.assets_state,)),
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
        export_tiledata_json

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

def export_tiledata_json(tiledata):
    """Saves the complete, final tiledata to a JSON file."""
    
    try:
        # 🏞️ Clean the data for JSON serialization.
        cleaned = {
            f"{q},{r}": {
                # 1. Round floats to 3 decimal points, leave other types as is.
                k: round(v, 3) if isinstance(v, float) else v
                for k, v in tile.items()
                # 2. Exclude the 'type' key and any non-standard JSON types.
                if k != 'type' and isinstance(v, (int, float, str, list, dict, bool, type(None)))
            }
            for (q, r), tile in tiledata.items()
        }

        # 💾 Open the file and dump the cleaned data.
        with open("tiledata_export.json", "w") as f:
            json.dump(cleaned, f, indent=2)
        print(f"[exports] ✅ Saved tiledata.json.")
    except Exception as e:
        print(f"[exports] ❌ ERROR: Failed to save tiledata.json: {e}")