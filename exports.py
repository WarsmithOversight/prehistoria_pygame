# exports.py
# A unified script for generating all data and visual asset exports.

import pygame
import math
import json
from renderer import render_giant_z_pot
from shared_helpers import hex_to_pixel


# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────
# This toggle allows for faster, low-res testing vs. high-quality final output.
FULL_RES_MAP_RENDER = False                 # Set to True for a full-resolution PNG map export.
MAP_RENDER_SCALE = 1.0 if FULL_RES_MAP_RENDER else 0.1 # Renders at a reduced scale for faster testing.

# Toggles for which elevation heatmaps to export as PNG files.
EXPORT_FINAL_ELEVATION_HEATMAP = False      # Toggles the export of the final combined elevation heatmap.
EXPORT_CONTINENTAL_SCALE_HEATMAP = False    # Toggles the export of the continental scale heatmap.
EXPORT_TOPOGRAPHIC_SCALE_HEATMAP = False    # Toggles the export of the topographic scale heatmap.
EXPORT_COASTAL_SCALE_HEATMAP = False        # Toggles the export of the coastal scale heatmap.

# ──────────────────────────────────────────────────
# 🛠️ Export Helpers
# ──────────────────────────────────────────────────

def _get_map_dimensions(tiledata, persistent_state, scale_factor=1.0):
    """Calculates the total pixel dimensions needed to render the entire map."""

    # Initialize min and max coordinates with extreme values
    min_x, max_x = math.inf, -math.inf
    min_y, max_y = math.inf, -math.inf

    # Use a temporary variable_state for this calculation
    variable_state_calc = {"var_current_zoom": scale_factor, "var_render_offset": (0, 0)}

    # Iterate through each tile to find the map's bounding box
    for q, r in tiledata:

        # Get the pixel coordinates for the current hex
        px, py = hex_to_pixel(q, r, persistent_state, variable_state_calc)

        # Account for the full canvas size of the tile sprite to find the map extents
        min_x = min(min_x, px - (persistent_state["pers_tile_canvas_w"] * scale_factor) / 2)
        max_x = max(max_x, px + (persistent_state["pers_tile_canvas_w"] * scale_factor) / 2)
        min_y = min(min_y, py - (persistent_state["pers_tile_canvas_h"] * scale_factor) / 2)
        max_y = max(max_y, py + (persistent_state["pers_tile_canvas_h"] * scale_factor) / 2)

    # Calculate the final image dimensions and render offset
    img_width = int(max_x - min_x)
    img_height = int(max_y - min_y)
    render_offset = (min_x, min_y)
    
    return img_width, img_height, render_offset

def export_tiledata_json(tiledata):
    """Saves the complete, final tiledata to a JSON file."""
    
    try:

        # Clean the data for JSON serialization, removing any non-standard types
        cleaned = {
            f"{q},{r}": {k: v for k, v in tile.items() if isinstance(v, (int, float, str, list, dict, bool, type(None)))}
            for (q, r), tile in tiledata.items()
        }

        # Open the file and dump the cleaned data
        with open("tiledata_export.json", "w") as f:
            json.dump(cleaned, f, indent=2)
        print("[exports] ✅ Saved tiledata.json.")
    except Exception as e:
        print(f"[exports] ❌ ERROR: Failed to save tiledata.json: {e}")

def export_map_render_png(tiledata, persistent_state, assets_state):
    """Renders the full world map with all terrain sprites."""

    try:

        # Calculate the required dimensions and render offset for the map
        img_width, img_height, render_offset = _get_map_dimensions(tiledata, persistent_state, MAP_RENDER_SCALE)
        
        # Set up a temporary variable state for rendering
        variable_state_render = {
            "var_current_zoom": MAP_RENDER_SCALE,
            "var_is_zooming": False,
            "var_render_offset": render_offset
        }
        
        # Create a Pygame surface for the map
        map_surface = pygame.Surface((img_width, img_height))
        map_surface.fill((0, 0, 0))
        
        # Call the main renderer to draw the world to the surface
        render_giant_z_pot(map_surface, tiledata, {}, persistent_state, assets_state, variable_state_render)
        
        # Save the rendered surface as a PNG file
        pygame.image.save(map_surface, "map_render.png")
        print("[exports] ✅ Generated map_render.png.")
    except Exception as e:
        print(f"[exports] ❌ ERROR: Failed to generate map render: {e}")

def _generate_single_heatmap(tiledata, persistent_state, data_key, output_filename):
    """
    Generic internal function to render a heatmap from a specific data key.
    """
    try:
        # Calculate map dimensions for a full-res heatmap
        img_width, img_height, render_offset = _get_map_dimensions(tiledata, persistent_state, 1.0)
        
        # Create a new surface for the heatmap
        heatmap_surface = pygame.Surface((img_width, img_height))
        heatmap_surface.fill((0, 0, 0))

        # Determine the radius of the heatmap dots
        dot_radius = int(persistent_state["pers_tile_hex_w"] / 2 * 0.9)
        
        # Set up a temporary variable state for calculations
        variable_state_calc = {"var_current_zoom": 1.0, "var_render_offset": render_offset}

        # Find all valid values for the given key
        values = [t[data_key] for t in tiledata.values() if data_key in t and t[data_key] is not None]
        if not values:
            print(f"[exports] ⚠️ No data found for key '{data_key}'. Skipping heatmap.")
            return
            
        # Find the min, max, and range of the data values for normalization
        min_val, max_val = min(values), max(values)
        val_range = max_val - min_val or 1

        # Iterate through each tile to draw its heatmap dot
        for coord, tile in tiledata.items():
            if data_key in tile and tile[data_key] is not None:
                # Normalize the value to a 0.0-1.0 range

                norm_val = (tile[data_key] - min_val) / val_range

                # Convert hex coordinates to pixel coordinates
                px, py = hex_to_pixel(coord[0], coord[1], persistent_state, variable_state_calc)

                # Map the normalized value to a color using a blue -> green -> yellow/red gradient
                if norm_val < 0.5:
                    color = (0, int(255 * (norm_val * 2)), int(255 * (1 - (norm_val * 2))))
                else:
                    color = (int(255 * ((norm_val - 0.5) * 2)), int(255 * (1 - (norm_val - 0.5) * 2)), 0)
                
                # Draw the circle on the heatmap surface
                pygame.draw.circle(heatmap_surface, color, (int(px), int(py)), dot_radius)
        
        # Save the generated heatmap image
        pygame.image.save(heatmap_surface, output_filename)
        print(f"[exports] ✅ Successfully generated {output_filename}.")
    except Exception as e:
        print(f"[exports] ❌ ERROR: Failed to generate {output_filename}: {e}")

def run_heatmap_exports(tiledata, persistent_state):
    """Checks constants and runs the heatmap generator for each enabled type."""
    # Call the heatmap generator for each enabled heatmap type
    if EXPORT_FINAL_ELEVATION_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'final_elevation', 'heatmap_final_elevation.png')
    if EXPORT_CONTINENTAL_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'continental_scale', 'heatmap_continental.png')
    if EXPORT_TOPOGRAPHIC_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'topographic_scale', 'heatmap_topographic.png')
    if EXPORT_COASTAL_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'coastal_scale', 'heatmap_coastal.png')
    if EXPORT_COASTAL_SCALE_HEATMAP:
        _generate_single_heatmap(tiledata, persistent_state, 'vertical_scale', 'heatmap_vertical.png')


def run_all_exports(tiledata, persistent_state, assets_state):
    """The main orchestrator function called from third_main.py."""

    # Call the individual export functions in sequence
    export_tiledata_json(tiledata)
    run_heatmap_exports(tiledata, persistent_state) # 👈 New unified call
    export_map_render_png(tiledata, persistent_state, assets_state)
