# micro_main.py
# main entry point. Runs game loop, initalizers and initializes dicts.

import pygame

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
)
from renderer import (
    render_giant_z_pot, initialize_render_states,
)
from load_assets import (
    load_tileset_assets, load_coast_assets,
    load_river_assets, load_river_mouth_assets,
    load_river_end_assets,
)
from world_generation.tile import create_tile_objects_from_data
from shared_helpers import initialize_shared_helper_states, hex_to_pixel
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

# ⚙️ Add config to dicts
initialize_shared_helper_states(persistent_state)
initialize_render_states(persistent_state)

persistent_state["pers_screen"] = screen
persistent_state["pers_tile_canvas_w"] = 256   # PNG width
persistent_state["pers_tile_canvas_h"] = 384   # PNG height
persistent_state["pers_tile_hex_w"]    = 256   # Dimensions of artwork within PNG
persistent_state["pers_tile_hex_h"]    = 260   # Dimensions of artwork within PNG

# 🌎 Region states
persistent_state["pers_region_count"] = 16  # N extra after 2 starting

# 📷 Zoom states
variable_state["var_current_zoom"] = 0.15
variable_state["var_is_zooming"] = False
variable_state["var_zoom_last_tick"] = 0
persistent_state["pers_zoom_config"] = {
    "min_zoom": 0.10,
    "max_zoom": 1.00,
    "zoom_interval": 0.05,   # 0.2, 0.25, 0.30, ... , 1.0
    "settle_ms": 180         # debounce after wheel stops
}

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
tag_central_desert(tiledata, persistent_state)
tag_adjacent_scrublands(tiledata, persistent_state)
add_windward_and_leeward_tags(tiledata, persistent_state)

# --- 🏞️ Rivers, and Shorelines ---
river_paths = run_river_generation(tiledata, persistent_state)
resolve_shoreline_bitmasks(tiledata, persistent_state)

# --- 🎨 Add Terrain ---
fill_in_terrain_from_tags(tiledata)
create_tile_objects_from_data(tiledata)

# --- 🐛 Debug Sequence ---
add_all_debug_overlays(tiledata, river_paths, notebook, persistent_state, variable_state)

# --- 📁 Load Assets ---
load_tileset_assets(assets_state, persistent_state)
load_coast_assets(assets_state, persistent_state)
load_river_assets(assets_state, persistent_state)
load_river_mouth_assets(assets_state, persistent_state)
load_river_end_assets(assets_state, persistent_state)

# --- 📷 Exports ---
if GENERATE_EXPORTS:
    run_all_exports(tiledata, persistent_state, assets_state)

# --- 🎥 Initial Camera Setup ---
screen_w, screen_h = persistent_state["pers_screen"].get_size()
screen_center_px = (screen_w / 2, screen_h / 2)

map_center_q, map_center_r = persistent_state["pers_map_center"]

# Temporarily set offset to 0 to calculate the world pixel coordinate
variable_state["var_render_offset"] = (0, 0) 
map_center_px = hex_to_pixel(
    map_center_q, map_center_r, persistent_state, variable_state
)

# The final offset is the difference required to move the map center to the screen center
offset_x = screen_center_px[0] - map_center_px[0]
offset_y = screen_center_px[1] - map_center_px[1]
variable_state["var_render_offset"] = (offset_x, offset_y)
print(f"[main] ✅ Camera centered with offset {variable_state['var_render_offset']}")

# ──────────────────────────────────────────────────
# ⏰ Main Loop
# ──────────────────────────────────────────────────
running = True
print(f"[main] ✅ Main game loop initiated.")
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # handle_zoom_debounce(persistent_state, variable_state)
    render_giant_z_pot(screen, tiledata, notebook, persistent_state, assets_state, variable_state)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()

# Zoom Event Handler
# for event in pygame.event.get():
#     if event.type == pygame.MOUSEWHEEL:
#         zoom_config = persistent_state["pers_zoom_config"]
#         scale = variable_state["var_scale_factor"]
#         # wheel.y: +1 up, -1 down (invert if needed)
#         scale *= (1.0 + 0.1 * event.y)  # 10% per notch feels nice
#         scale = max(zoom_config["min_zoom"], min(zoom_config["max_zoom"], scale))
#         variable_state["var_scale_factor"] = scale
#         variable_state["var_is_zooming"] = True
#         variable_state["var_zoom_last_tick"] = pygame.time.get_ticks()

# def handle_zoom_debounce(persistent_state, variable_state):
#     if not variable_state.get("var_is_zooming"):
#         return
#     now = pygame.time.get_ticks()
#     if now - variable_state["var_zoom_last_ms"] >= persistent_state["pers_zoom_config"]["settle_ms"]:
#         # snap and exit zooming mode
#         from shared_helpers import snap_zoom
#         snapped = snap_zoom(persistent_state, variable_state)
#         variable_state["var_current_zoom"] = snapped
#         variable_state["var_is_zooming"] = False

