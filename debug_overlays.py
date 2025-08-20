# debug_overlays.py
# Functions for adding visual debugging information to the notebook.

from shared_helpers import hex_geometry
import random
from generate_terrain import TERRAIN_TAG_PRIORITY

# ──────────────────────────────────────────────────
# ⚙️ Debug Toggles
# ──────────────────────────────────────────────────
# Set these to True or False to control which overlays are active.
SHOW_HEX_CENTERS    = False     # Renders a small circle at the center of each hex.
SHOW_COORDINATES    = False     # Renders the (q,r) coordinate on each hex.
SHOW_REGION_BORDERS = False     # Draws lines between different regional IDs.
SHOW_TERRAIN_TAGS   = False     # Draws a colored circle representing the terrain type.
SHOW_SPINE          = False     # Draws the continent spine used for elevation.
SHOW_RIVER_PATHS    = False     # Draws a series of dots along each river path.
SHOW_RIVER_ENDPOINTS = False    # Draws a special circle on river sources and destinations.

SPINE_TRIM_MODE = 'NONE' # Can be 'PERCENT', 'ABSOLUTE', or 'NONE'
SPINE_TRIM_VALUE = 3       # The value to use for trimming (e.g., 20% or 4 tiles)

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

OVERLAY_COLORS = {
    # --- Sandy Zone (Yellows/Browns) ---
    "central_desert":     (238, 213, 153),  # Bright, sandy yellow
    "adjacent_scrubland": (205, 180, 140),  # Lighter, dusty tan
    "leeward":            (0, 255, 255),    # Darker, brownish sand

    # --- Green Zone (Greens) ---
    "windward":           (255, 0, 255),    # Vibrant, lush green
    
    # --- Rocky Zone (Grays) ---
    "highlands":          (190, 190, 190),  # Light rock gray
    
    # --- Neutral / Special ---
    "lowlands":           (72, 120, 110),   # Muted teal for marshes/wetlands
    "hex_center":         (30, 30, 30),     # Grey
    "continent_spine":    (30, 30, 30),     # Grey
    "river_source":       (0, 0, 0),
    "river_termination":  (220, 20, 60),    # Crimson Red
    }

# ──────────────────────────────────────────────────
# 📷 Individual Overlay Functions
# ──────────────────────────────────────────────────

def add_spine_overlay(tiledata, notebook, persistent_state):
    """
    Draws an overlay on spine tiles, with support for trimming the spokes.
    """
    # Get the z-order formula for continent spines
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("continent_spine")

    # Handle the case where the z-formula is missing
    if not z_formula:
        print("⚠️ Continent spine z-formula not found in persistent_state.")
        return

    # Define the color for the spine overlay
    color = OVERLAY_COLORS["continent_spine"]

    # Iterate through all tiles and add an overlay to those with spine data
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    for q, r in land_coords:
        tile = tiledata[(q, r)]
        if "spine_data" in tile:
            data = tile["spine_data"]
            dist = data["dist_on_spoke"]
            max_dist = data["spoke_max_dist"]

            # Determine if the overlay should be visible based on the trim mode
            is_visible = True
            if SPINE_TRIM_MODE == 'PERCENT' and max_dist > 0:

                # Calculate the threshold for trimming by percentage
                keep_fraction = 1.0 - (SPINE_TRIM_VALUE / 100.0)

                # Hide the overlay if the distance is beyond the threshold
                if dist >= max_dist * keep_fraction:
                    is_visible = False
            elif SPINE_TRIM_MODE == 'ABSOLUTE':

                # Hide the overlay if the distance is within the absolute trim value from the end
                if dist >= max_dist - SPINE_TRIM_VALUE:
                    is_visible = False

            # Skip to the next tile if the overlay should not be visible
            if not is_visible:
                continue

            # Calculate the z-order for the overlay
            overlay_z = z_formula(r)

            # Add the circle overlay to the notebook
            notebook[f"overlay_spine_{q}_{r}"] = {
                "type": "circle", "coord": (q, r), "z": overlay_z,
                "color": color, "base_radius": 50, "opacity": 128, "tag": "spine",
            }

def add_hex_center_overlay(tiledata, notebook, persistent_state):
    """Draws a black circle at the mathematical center of every hex."""

    # Get the z-order values from persistent state
    z_order = persistent_state["pers_z_order"]
    z_cel_tile = z_order["cel"]["tile"]
    z_offset = z_order["offset"]["hex_center"]

    # Iterate through all tiles
    for (q, r), tile in tiledata.items():

        # Get the base z-order of the tile, or use the default
        base_z = tile.get("z", z_cel_tile)

        # Create a unique key for the overlay
        key = f"dbg_center_{q}_{r}"

        # Add the circle overlay to the notebook
        notebook[key] = {
            "type": "circle", "coord": (q, r),
            "z": base_z + z_offset,
            "color": OVERLAY_COLORS["hex_center"], "base_radius": 30,
        }

def add_qr_coordinates_overlay(tiledata, notebook, persistent_state):
    """Draws the (q,r) coordinate as text on each tile."""

    # Get the z-order formula for coordinates
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("coordinate")

    # Handle the case where the z-formula is missing
    if not z_formula:
        print("⚠️ Coordinate z-formula not found in persistent_state.")
        return

    # Iterate through all tiles
    for (q, r), tile in tiledata.items():

        # Calculate the z-order for the text overlay
        overlay_z = z_formula(r)

        # Add the text overlay to the notebook
        notebook[f"coord_{q}_{r}"] = {
            "type": "text",
            "coord": (q, r),
            "z": overlay_z,
            "text": f"{q},{r}",
            "color": (0, 0, 0),
            "base_size": 16,
        }

def add_region_border_overlay(tiledata, notebook, persistent_state, variable_state):
    """Draws thick black lines between different regions."""

    # Initialize sets to track which edges and vertices have been drawn
    drawn_edges = set()
    border_vertices = set()

    # Define line thickness and z-order
    line_thickness = 20
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_border = z_formulas.get("region_border", lambda: 1.5)() # Default to 1.5 if not found
    
    # Iterate through each tile to find region borders
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    for q, r in land_coords:
        tile = tiledata[(q, r)]
        if tile.get("region_id") is None: continue

        # Get the geometry for the current tile
        geo = hex_geometry(q, r, persistent_state, variable_state)
        this_region = tile["region_id"]

        # Loop through each of the tile's edges
        for idx, (p1, p2) in geo["edges"].items():
            edge_name = persistent_state["pers_hex_anatomy"]["edges"][idx]["name"]
            
            # Get the coordinates of the neighbor on the other side of the edge
            nq, nr = geo["neighbors"][edge_name]
            neighbor = tiledata.get((nq, nr))

            # Check if the neighbor exists and is in a different region
            if not neighbor or neighbor.get("region_id") != this_region:

                # Create a consistent key for the edge regardless of direction
                edge_key = tuple(sorted(((q, r), (nq, nr))))

                # Only draw the edge if it hasn't been drawn yet
                if edge_key in drawn_edges: continue

                # Add the edge to the set of drawn edges
                drawn_edges.add(edge_key)

                # Add the line overlay to the notebook
                key = f"region_edge_{q}_{r}_{edge_name}"
                notebook[key] = {
                    "type": "edge_line", "p1": p1, "p2": p2,
                    "z": z_border, 
                    "color": (0, 0, 0), "thickness": line_thickness,
                }
                
                # Add the vertices of the border line to a set
                border_vertices.add(p1)
                border_vertices.add(p2)

    # Draw a circle on each unique border vertex
    for i, vertex in enumerate(border_vertices):

        # Add a small circle to the notebook for each border vertex
        notebook[f"border_vertex_{i}"] = {
            "type": "circle",
            "pixel_coord": vertex,
            "z": z_border + 0.01, 
            "color": (0, 0, 0),
            "matches_line_thickness": line_thickness,
        }

def add_terrain_tag_overlay(tiledata, notebook, persistent_state):
    """
    Draws colored circles representing the highest-priority terrain tag on a tile,
    compatible with single and combined tag rules.
    """

    # Get the z-order offset for terrain tags
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("terrain_tag")
    if not z_formula:
        print("⚠️ Terrain tag z-formula not found in persistent_state.")
        return
    
    # Iterate through all tiles
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    for q, r in land_coords:
        tile = tiledata[(q, r)]

        # Loop through the terrain tag priority rules
        for rule in TERRAIN_TAG_PRIORITY:

            # Check if all tags in the current rule are present on the tile
            if all(tile.get(tag) for tag in rule):

                # Use the first tag in the rule as the color key
                color_key = rule[0]
                color = OVERLAY_COLORS.get(color_key)

                # Skip to the next rule if no color is found
                if not color:
                    break 

                # Add the circle overlay to the notebook
                overlay_z = z_formula(r)
                notebook[f"overlay_{color_key}_{q}_{r}"] = {
                    "type": "circle", "coord": (q, r), "z": overlay_z,
                    "color": color, "base_radius": 50, "opacity": 128, "tag": color_key,
                }

                # Break the inner loop once a matching rule is found
                break
                
def add_river_path_overlay(river_paths, notebook, persistent_state):
    """
    Draws river paths with randomized colors, sizes, and a z-offset
    to ensure larger dots are always drawn behind smaller ones.
    """

    # Check if there are any river paths to draw
    if not river_paths:
        return

    # Get the z-order formula for debug icons
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("debug_icon")
    if not z_formula:
        print("⚠️ Terrain tag z-formula not found in persistent_state.")
        return
    
    # Define the radius range for the overlay circles
    max_radius = 60
    min_radius = 10

    # Loop through each river path
    for i, path in enumerate(river_paths):
        path_len = len(path)
        if path_len <= 1: continue

        # Create a unique, random size offset for this entire river path
        size_offset_factor = 1.0 + random.uniform(-0.15, 0.15) # +/- 15%

        # Assign a random color to the entire river path
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

        # Loop through each coordinate in the river path
        for j, coord in enumerate(path):
            q, r = coord
            
            # Normalize the tile's position along the path from 0.0 to 1.0
            normalized_pos = j / (path_len - 1)

            # Create a scale factor to make the dots at the source larger
            scale_factor = 1.0 - normalized_pos

            # Clamp the scale factor to a minimum value
            clamped_scale = 0.2 + (scale_factor * 0.8)

            # Calculate the base radius for the current dot
            base_radius = min_radius + (max_radius - min_radius) * clamped_scale
            
            # Apply the random offset to the final radius
            final_radius = int(base_radius * size_offset_factor)

            # Adjust the z-value based on radius to ensure larger dots draw first
            # A larger radius results in a smaller z-offset, pushing it further back.
            z_offset_for_size = (max_radius - final_radius) * 0.000001
            overlay_z = z_formula(r) + z_offset_for_size
            
            # Add the river path dot to the notebook
            unique_key = f"overlay_river_{i}_{j}_{q}_{r}"
            notebook[unique_key] = {
                "type": "circle", "coord": (q, r), "z": overlay_z,
                "color": color, "base_radius": final_radius, "opacity": 200
            }

def add_river_endpoints_overlay(river_paths, notebook, persistent_state):
    """
    Draws a hollow circle on the source and termination tile of each river.
    """

    # Check if there are any river paths to draw
    if not river_paths:
        return

    # Get the z-order formula for debug icons
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("debug_icon")

    if not z_formula:
        print("⚠️ Terrain tag z-formula not found in persistent_state.")
        return
    
    # Define the colors and properties for the overlay circles
    source_color = OVERLAY_COLORS["river_source"]
    term_color = OVERLAY_COLORS["river_termination"]
    radius = 70 
    outline_width = 15 # The base thickness of the circle's outline

    # Loop through each river path
    for path in river_paths:
        if not path: continue

        # Get the coordinates of the source and termination tiles
        source_q, source_r = path[0]
        term_q, term_r = path[-1]

        # Add a circle for the river source
        notebook[f"overlay_river_source_{source_q}_{source_r}"] = {
            "type": "circle", "coord": (source_q, source_r),
            "z": z_formula(source_r) + 0.0001,
            "color": source_color, "base_radius": radius, "opacity": 255,
            "width": outline_width 
        }

        # Add a circle for the river termination, but only if it's not the same tile as the source
        if (source_q, source_r) != (term_q, term_r):
             notebook[f"overlay_river_term_{term_q}_{term_r}"] = {
                "type": "circle", "coord": (term_q, term_r),
                "z": z_formula(term_r) + 0.0001,
                "color": term_color, "base_radius": radius, "opacity": 255,
                "width": outline_width
            }

# ──────────────────────────────────────────────────
# 🛠️ Assembler
# ──────────────────────────────────────────────────

def add_all_debug_overlays(tiledata, river_paths, notebook, persistent_state, variable_state):
    """Calls all debug drawable functions based on the toggle switches at the top of the file."""
    
    # Check each toggle and call the corresponding function
    if SHOW_HEX_CENTERS:
        add_hex_center_overlay(tiledata, notebook, persistent_state)
        
    if SHOW_COORDINATES:
        add_qr_coordinates_overlay(tiledata, notebook, persistent_state)
        
    if SHOW_REGION_BORDERS:
        add_region_border_overlay(tiledata, notebook, persistent_state, variable_state)
        
    if SHOW_TERRAIN_TAGS:
        add_terrain_tag_overlay(tiledata, notebook, persistent_state)

    if SHOW_SPINE:
        add_spine_overlay(tiledata, notebook, persistent_state)

    if SHOW_RIVER_PATHS:
        add_river_path_overlay(river_paths, notebook, persistent_state)

    if SHOW_RIVER_ENDPOINTS:
        add_river_endpoints_overlay(river_paths, notebook, persistent_state)

    print("[debug] ✅ Debug overlays added.")