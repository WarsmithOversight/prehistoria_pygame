# exports.py
# A unified script for generating all data and visual asset exports.

import pygame
import math
import json
from renderer import render_giant_z_pot
from shared_helpers import hex_to_pixel

# --- Configuration ---
# This toggle allows for faster, low-res testing vs. high-quality final output.
FULL_RES_MAP_RENDER = False
MAP_RENDER_SCALE = 1.0 if FULL_RES_MAP_RENDER else 0.1 # Renders at reduced scale for speed

EXPORT_FINAL_ELEVATION_HEATMAP = True
EXPORT_CONTINENTAL_SCALE_HEATMAP = True
EXPORT_TOPOGRAPHIC_SCALE_HEATMAP = True
EXPORT_COASTAL_SCALE_HEATMAP = True

def _get_map_dimensions(tiledata, persistent_state, scale_factor=1.0):
    """Calculates the total pixel dimensions needed to render the entire map."""
    min_x, max_x = math.inf, -math.inf
    min_y, max_y = math.inf, -math.inf

    # Use a temporary variable_state for this calculation
    variable_state_calc = {"var_current_zoom": scale_factor, "var_render_offset": (0, 0)}

    for q, r in tiledata:
        px, py = hex_to_pixel(q, r, persistent_state, variable_state_calc)
        # Account for the full canvas size of the tile sprite to find the map extents
        min_x = min(min_x, px - (persistent_state["pers_tile_canvas_w"] * scale_factor) / 2)
        max_x = max(max_x, px + (persistent_state["pers_tile_canvas_w"] * scale_factor) / 2)
        min_y = min(min_y, py - (persistent_state["pers_tile_canvas_h"] * scale_factor) / 2)
        max_y = max(max_y, py + (persistent_state["pers_tile_canvas_h"] * scale_factor) / 2)

    img_width = int(max_x - min_x)
    img_height = int(max_y - min_y)
    render_offset = (min_x, min_y)
    
    return img_width, img_height, render_offset

def export_tiledata_json(tiledata):
    """Saves the complete, final tiledata to a JSON file."""
    print("💾 Saving tiledata.json...")
    try:
        # Clean the data for JSON serialization, removing any non-standard types
        cleaned = {
            f"{q},{r}": {k: v for k, v in tile.items() if isinstance(v, (int, float, str, list, dict, bool, type(None)))}
            for (q, r), tile in tiledata.items()
        }
        with open("tiledata_export.json", "w") as f:
            json.dump(cleaned, f, indent=2)
        print("   -> Success.")
    except Exception as e:
        print(f"   -> ❌ ERROR: Failed to save tiledata.json: {e}")

def export_map_render_png(tiledata, persistent_state, assets_state):
    """Renders the full world map with all terrain sprites."""
    print(f"🎨 Exporting map_render.png at {MAP_RENDER_SCALE*100:.0f}% resolution...")
    try:
        img_width, img_height, render_offset = _get_map_dimensions(tiledata, persistent_state, MAP_RENDER_SCALE)
        
        variable_state_render = {
            "var_current_zoom": MAP_RENDER_SCALE,
            "var_is_zooming": False,
            "var_render_offset": render_offset
        }
        
        map_surface = pygame.Surface((img_width, img_height))
        map_surface.fill((0, 0, 0))
        
        render_giant_z_pot(map_surface, tiledata, {}, persistent_state, assets_state, variable_state_render)
        
        pygame.image.save(map_surface, "map_render.png")
        print("   -> Success.")
    except Exception as e:
        print(f"   -> ❌ ERROR: Failed to generate map render: {e}")

def _generate_single_heatmap(tiledata, persistent_state, data_key, output_filename):
    """
    Generic internal function to render a heatmap from a specific data key.
    """
    print(f"[Exports] 🎨 Generating heatmap for '{data_key}' -> {output_filename}...")
    try:
        img_width, img_height, render_offset = _get_map_dimensions(tiledata, persistent_state, 1.0)
        heatmap_surface = pygame.Surface((img_width, img_height))
        heatmap_surface.fill((0, 0, 0))
        dot_radius = int(persistent_state["pers_tile_hex_w"] / 2 * 0.9)
        
        variable_state_calc = {"var_current_zoom": 1.0, "var_render_offset": render_offset}

        # Find all valid values for the given key
        values = [t[data_key] for t in tiledata.values() if data_key in t and t[data_key] is not None]
        if not values:
            print(f"[Exports] ⚠️ No data found for key '{data_key}'. Skipping heatmap.")
            return
            
        min_val, max_val = min(values), max(values)
        val_range = max_val - min_val or 1

        for coord, tile in tiledata.items():
            if data_key in tile and tile[data_key] is not None:
                norm_val = (tile[data_key] - min_val) / val_range
                px, py = hex_to_pixel(coord[0], coord[1], persistent_state, variable_state_calc)

                # Blue -> Green -> Yellow/Red gradient
                if norm_val < 0.5:
                    color = (0, int(255 * (norm_val * 2)), int(255 * (1 - (norm_val * 2))))
                else:
                    color = (int(255 * ((norm_val - 0.5) * 2)), int(255 * (1 - (norm_val - 0.5) * 2)), 0)
                
                pygame.draw.circle(heatmap_surface, color, (int(px), int(py)), dot_radius)
        
        pygame.image.save(heatmap_surface, output_filename)
        print(f"[Exports] ✅ Successfully generated {output_filename}.")
    except Exception as e:
        print(f"[Exports] ❌ ERROR: Failed to generate {output_filename}: {e}")

def run_heatmap_exports(tiledata, persistent_state):
    """Checks constants and runs the heatmap generator for each enabled type."""
    if EXPORT_FINAL_ELEVATION_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'final_elevation', 'heatmap_final_elevation.png')
    if EXPORT_CONTINENTAL_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'continental_scale', 'heatmap_continental.png')
    if EXPORT_TOPOGRAPHIC_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'topographic_scale', 'heatmap_topographic.png')
    if EXPORT_COASTAL_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'coastal_scale', 'heatmap_coastal.png')

def run_all_exports(tiledata, persistent_state, assets_state):
    """The main orchestrator function called from third_main.py."""
    print("\n--- 🚀 Running All Exports ---")
    export_tiledata_json(tiledata)
    run_heatmap_exports(tiledata, persistent_state) # 👈 New unified call
    export_map_render_png(tiledata, persistent_state, assets_state)
    print("--- ✅ Exports Complete ---\n")
