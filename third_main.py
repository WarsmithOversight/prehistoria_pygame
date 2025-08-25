# micro_main.py
# main entry point. Runs game loop, initalizers and initializes dicts.

import pygame
import json
from map_interactor import MapInteractor
from camera_controller import CameraController
from player import Player
from game_manager import GameManager
from event_bus import EventBus
from tween_manager import TweenManager

from world_generation.initialize_tiledata import (
    initialize_tiledata, initialize_region_seeds,
    add_distance_from_center_to_tiledata, add_distance_from_ocean_to_tiledata,
    tag_continent_spine, calculate_and_store_map_center,
    calculate_monsoon_bands
)
from world_generation.generate_terrain import (
    tag_mountains, tag_initial_ocean,
    tag_ocean_coastline, resolve_shoreline_bitmasks,
    tag_lowlands, tag_mountain_range,
    tag_central_desert, add_windward_and_leeward_tags,
    fill_in_terrain_from_tags,tag_adjacent_scrublands,
    sculpt_mountain_ranges
)
from renderer import (
    render_giant_z_pot, initialize_render_states,
)
from load_assets import (
    load_tileset_assets, load_coast_assets,
    load_river_assets, load_river_mouth_assets,
    load_river_end_assets, initialize_asset_states,
    create_glow_mask, load_player_assets, create_tinted_glow_masks,
)
from world_generation.tile import create_tile_objects_from_data
from shared_helpers import initialize_shared_helper_states
from debug_overlays import add_all_debug_overlays
from world_generation.elevation import run_elevation_generation
from exports import run_all_exports
from world_generation.rivers import run_river_generation
from world_generation.biomes import assign_biomes_to_regions

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
GENERATE_EXPORTS = True

# ──────────────────────────────────────────────────
# 🏁 Initialization
# ──────────────────────────────────────────────────

# 🔹 Init Pygame
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((1280, 840))
pygame.display.set_caption("Mini Map Renderer")
clock = pygame.time.Clock()


# 📔 Initialize dicts
persistent_state = {}
trigger_state = {}
variable_state = {}
notebook = {}
tiledata = {}
assets_state = {}
river_paths = {}
persistent_state["pers_screen"] = screen

# ⚙️ Add config to dicts
initialize_shared_helper_states(persistent_state)
initialize_render_states(persistent_state)
initialize_asset_states(persistent_state)

persistent_state["pers_zoom_config"] = {
    "min_zoom": 0.10,
    "max_zoom": 1.00,
    "zoom_interval": 0.02,
    "settle_ms": 120,
}
variable_state["var_current_zoom"] = 1
variable_state["var_render_offset"] = (0, 0)


# 🌎 Region states
persistent_state["pers_region_count"] = 16  # N extra after 2 starting

# ──────────────────────────────────────────────────
# 🌎 World Generation
# ──────────────────────────────────────────────────

# --- 🗺️ Initialize Tiledata ---
initialize_region_seeds(persistent_state, variable_state)
tiledata = initialize_tiledata(persistent_state, variable_state)  # normalize + rectangle + passable flags
calculate_and_store_map_center(tiledata, persistent_state)
add_distance_from_center_to_tiledata(tiledata, persistent_state)
add_distance_from_ocean_to_tiledata(tiledata, persistent_state)
calculate_monsoon_bands(tiledata, persistent_state)
tag_continent_spine(tiledata, persistent_state)

# --- ⛰️ Tag Fundamental Geography ---
tag_initial_ocean(tiledata, variable_state)
tag_ocean_coastline(tiledata, persistent_state) # Defines "is_coast"
tag_mountains(tiledata, persistent_state)       # Defines mountains and "dist_to_mountain"
run_elevation_generation(tiledata, persistent_state)
assign_biomes_to_regions(tiledata, persistent_state)

# --- 🔭 Tag More Detailed Features ---
tag_lowlands(tiledata, persistent_state)
tag_mountain_range(tiledata)
sculpt_mountain_ranges(tiledata, persistent_state)
tag_central_desert(tiledata, persistent_state)
tag_adjacent_scrublands(tiledata, persistent_state)
add_windward_and_leeward_tags(tiledata, persistent_state)

# --- 🏞️ Rivers, and Shorelines ---
river_paths = run_river_generation(tiledata, persistent_state)
resolve_shoreline_bitmasks(tiledata, persistent_state)

# --- 🎨 Add Terrain ---
fill_in_terrain_from_tags(tiledata)
tile_objects = create_tile_objects_from_data(tiledata)

# --- 🐛 Debug Sequence ---
add_all_debug_overlays(tile_objects, river_paths, notebook, persistent_state, variable_state)

# --- 📁 Load Assets ---
load_tileset_assets(assets_state, persistent_state)
load_coast_assets(assets_state, persistent_state)
load_river_assets(assets_state, persistent_state)
load_river_mouth_assets(assets_state, persistent_state)
load_river_end_assets(assets_state, persistent_state)
load_player_assets(assets_state, persistent_state)
create_glow_mask(persistent_state, assets_state)
create_tinted_glow_masks(persistent_state, assets_state)

# --- 📷 Exports ---
if GENERATE_EXPORTS:
    run_all_exports(tiledata, persistent_state, assets_state)

# ──────────────────────────────────────────────────
# 🎬 Initialize Players & Controllers
# ──────────────────────────────────────────────────
# 1. Load the master species data from the JSON file
with open("species.json", "r") as f:
    all_species_data = json.load(f)
print(f"[main] ✅ Loaded data for {len(all_species_data)} species from JSON.")

# 2. Initialize Player Instances
players = []

# This section shows how you would initialize multiple players based on setup choices.
# For now, it's commented out as requested.
# 
# num_players = 2 
# player_species_choices = ["frog", "dinosaur"] # This would come from a player selection screen
# 
# for i in range(num_players):
#     player_id = i + 1
#     species_name = player_species_choices[i]
#     player_instance = Player(
#         player_id=player_id,
#         species_name=species_name,
#         all_species_data=all_species_data,
#         tile_objects=tile_objects,
#         notebook=notebook,
#         assets_state=assets_state,
#         persistent_state=persistent_state
#     )
#     players.append(player_instance)

# Hardcoded single player for now
players.append(
    Player(
        player_id=1,
        species_name="frog",
        all_species_data=all_species_data,
        tile_objects=tile_objects,
        notebook=notebook,
        assets_state=assets_state,
        persistent_state=persistent_state
    )
)

# 3. Initialize Controllers
camera_controller = CameraController(persistent_state, variable_state)
map_interactor = MapInteractor()
event_bus = EventBus()

tween_manager = TweenManager(persistent_state, variable_state)
game_manager = GameManager(players, camera_controller, tile_objects, event_bus, tween_manager, notebook, persistent_state, variable_state)

# ──────────────────────────────────────────────────
# ⏰ Main Loop
# ──────────────────────────────────────────────────
running = True
print(f"[main] ✅ Main game loop initiated.")
while running:
    # Get all user events once at the start of the frame.
    dt = clock.tick(60) / 1000.0 # Delta time in seconds
    events = pygame.event.get()
    mouse_pos = pygame.mouse.get_pos()

    # The only event handled directly in the loop is quitting the game.
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                game_manager.advance_turn()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                game_manager.add_resource_to_active_player_tile()
            
    # ──────────────────────────────────────────────────
    # ⚙️ Update State
    # ──────────────────────────────────────────────────

    # Update all active animations
    tween_manager.update(dt)

    # Handle direct camera controls like keyboard panning and scroll wheel zooming.
    camera_controller.handle_events(events, persistent_state)
    
    # The interactor now returns the pan delta, clicked coord, and hovered coord
    pan_delta, clicked_coord, hovered_coord = map_interactor.handle_events(events, mouse_pos, tile_objects, persistent_state, variable_state)

    # Update the path overlay based on the currently hovered tile
    game_manager.update_path_overlay(hovered_coord)

    # If a tile was clicked, pass its coordinate to the GameManager to handle
    if clicked_coord:
        game_manager.handle_click(clicked_coord)

    # If the interactor reported a drag, command the camera to pan.
    if pan_delta != (0, 0):
        camera_controller.pan(pan_delta[0], pan_delta[1])
        
    # Finalize the camera's state for this frame
    camera_controller.update(persistent_state, variable_state)
        
    # 🎨 Render
    render_giant_z_pot(screen, tile_objects, notebook, persistent_state, assets_state, variable_state)

    # Update the full display and cap the framerate.
    pygame.display.flip()

pygame.quit()
