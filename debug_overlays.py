# debug_overlays.py
# Functions for adding visual debugging information to the notebook.

from shared_helpers import hex_geometry, get_neighbor_in_direction
import random

# ──────────────────────────────────────────────────
# ⚙️ Debug Toggles
# ──────────────────────────────────────────────────
# Set these to True or False to control which overlays are active.
SHOW_HEX_CENTERS    = False
SHOW_COORDINATES    = False
SHOW_REGION_BORDERS = False
SHOW_TERRAIN_TAGS   = False
SHOW_SPINE          = False
SHOW_RIVER_PATHS    = False 
SHOW_RIVER_ENDPOINTS = False


# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

from generate_terrain import TERRAIN_TAG_PRIORITY

OVERLAY_COLORS = {
    # --- Sandy Zone (Yellows/Browns) ---
    "central_desert":     (238, 213, 153),  # Bright, sandy yellow
    "adjacent_scrubland": (205, 180, 140),  # Lighter, dusty tan
    "leeward":            (0, 255, 255),   # Darker, brownish sand

    # --- Green Zone (Greens) ---
    "windward":           (255, 0, 255),   # Vibrant, lush green
    
    # --- Rocky Zone (Grays) ---
    "highlands":          (190, 190, 190),  # Light rock gray
    
    # --- Neutral / Special ---
    "lowlands":           (72, 120, 110),   # Muted teal for marshes/wetlands
    "hex_center":         (30, 30, 30),        # Grey
    "continent_spine":    (30, 30, 30), # Grey
    "river_source":       (0, 0, 0),
    "river_termination":  (220, 20, 60),   # Crimson Red
    }

# ──────────────────────────────────────────────────
# 📷 Individual Overlay Functions
# ──────────────────────────────────────────────────

# --- Add these new constants at the top with the other toggles ---
SPINE_TRIM_MODE = 'NONE' # Can be 'PERCENT', 'ABSOLUTE', or 'NONE'
SPINE_TRIM_VALUE = 3       # The value to use for trimming (e.g., 20% or 4 tiles)

def add_spine_overlay(tiledata, notebook, persistent_state):
    """
    Draws an overlay on spine tiles, with support for trimming the spokes.
    """
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("continent_spine")

    if not z_formula:
        print("⚠️ Continent spine z-formula not found in persistent_state.")
        return

    color = OVERLAY_COLORS["continent_spine"]

    for (q, r), tile in tiledata.items():
        if "spine_data" in tile:
            data = tile["spine_data"]
            dist = data["dist_on_spoke"]
            max_dist = data["spoke_max_dist"]

            is_visible = True
            if SPINE_TRIM_MODE == 'PERCENT' and max_dist > 0:
                keep_fraction = 1.0 - (SPINE_TRIM_VALUE / 100.0)
                if dist >= max_dist * keep_fraction:
                    is_visible = False
            elif SPINE_TRIM_MODE == 'ABSOLUTE':
                if dist >= max_dist - SPINE_TRIM_VALUE:
                    is_visible = False
            
            if not is_visible:
                continue

            overlay_z = z_formula(r)
            notebook[f"overlay_spine_{q}_{r}"] = {
                "type": "circle", "coord": (q, r), "z": overlay_z,
                "color": color, "base_radius": 50, "opacity": 128, "tag": "spine",
            }

def add_hex_center_overlay(tiledata, notebook, persistent_state):
    """Draws a black circle at the mathematical center of every hex."""
    z_order = persistent_state["pers_z_order"]
    z_cel_tile = z_order["cel"]["tile"]
    z_offset = z_order["offset"]["hex_center"]

    for (q, r), tile in tiledata.items():
        base_z = tile.get("z", z_cel_tile)
        notebook[f"dbg_center_{q}_{r}"] = {
            "type": "circle", "coord": (q, r),
            "z": base_z + z_offset,
            "color": OVERLAY_COLORS["hex_center"], "base_radius": 30,
        }

def add_qr_coordinates_overlay(tiledata, notebook, persistent_state):
    """Draws the (q,r) coordinate as text on each tile."""
    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("coordinate")

    if not z_formula:
        print("⚠️ Coordinate z-formula not found in persistent_state.")
        return

    for (q, r), tile in tiledata.items():
        overlay_z = z_formula(r)
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
    drawn_edges = set()
    border_vertices = set()
    line_thickness = 20
    z_order = persistent_state["pers_z_order"]
    z_border = z_order["offset"]["region_border"]

    for (q, r), tile in tiledata.items():
        if tile.get("region_id") is None: continue
        geo = hex_geometry(q, r, persistent_state, variable_state)
        this_region = tile["region_id"]

        for idx, (p1, p2) in geo["edges"].items():
            edge_name = persistent_state["pers_hex_anatomy"]["edges"][idx]["name"]
            nq, nr = geo["neighbors"][edge_name]
            neighbor = tiledata.get((nq, nr))

            if not neighbor or neighbor.get("region_id") != this_region:
                edge_key = tuple(sorted(((q, r), (nq, nr))))
                if edge_key in drawn_edges: continue
                drawn_edges.add(edge_key)

                key = f"region_edge_{q}_{r}_{edge_name}"
                notebook[key] = {
                    "type": "edge_line", "p1": p1, "p2": p2,
                    "z": z_border, 
                    "color": (0, 0, 0), "thickness": line_thickness,
                }
                
                border_vertices.add(p1)
                border_vertices.add(p2)

    for i, vertex in enumerate(border_vertices):
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
    offset = persistent_state["pers_z_order"]["offset"]["terrain_tag"]
    for (q, r), tile in tiledata.items():
        if not tile.get("passable"):
            continue

        for rule in TERRAIN_TAG_PRIORITY:
            if all(tile.get(tag) for tag in rule):
                color_key = rule[0]
                color = OVERLAY_COLORS.get(color_key)

                if not color:
                    break 

                overlay_z = tile["z"] + offset
                notebook[f"overlay_{color_key}_{q}_{r}"] = {
                    "type": "circle", "coord": (q, r), "z": overlay_z,
                    "color": color, "base_radius": 50, "opacity": 128, "tag": color_key,
                }
                break
                
def add_river_path_overlay(river_paths, notebook, persistent_state):
    """
    Draws river paths with randomized colors, sizes, and a z-offset
    to ensure larger dots are always drawn behind smaller ones.
    """
    if not river_paths:
        return

    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("debug_icon")
    if not z_formula: return

    max_radius = 60
    min_radius = 10

    for i, path in enumerate(river_paths):
        path_len = len(path)
        if path_len <= 1: continue

        # 1. ✅ Create a unique, random size offset for this entire river path
        #    This ensures no two rivers will have the exact same dot sizes.
        size_offset_factor = 1.0 + random.uniform(-0.15, 0.15) # +/- 15%

        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

        for j, coord in enumerate(path):
            q, r = coord
            
            normalized_pos = j / (path_len - 1)
            scale_factor = 1.0 - normalized_pos
            clamped_scale = 0.2 + (scale_factor * 0.8)
            
            base_radius = min_radius + (max_radius - min_radius) * clamped_scale
            
            # 2. ✅ Apply the random offset to the final radius
            final_radius = int(base_radius * size_offset_factor)

            # 3. ✅ Adjust the z-value based on radius to ensure larger dots draw first
            #    A larger radius results in a smaller z-offset, pushing it further back.
            z_offset_for_size = (max_radius - final_radius) * 0.000001
            overlay_z = z_formula(r) + z_offset_for_size
            
            unique_key = f"overlay_river_{i}_{j}_{q}_{r}"
            notebook[unique_key] = {
                "type": "circle", "coord": (q, r), "z": overlay_z,
                "color": color, "base_radius": final_radius, "opacity": 200
            }

def add_river_endpoints_overlay(river_paths, notebook, persistent_state):
    """
    Draws a hollow circle on the source and termination tile of each river.
    """
    if not river_paths:
        return

    z_formulas = persistent_state.get("pers_z_formulas", {})
    z_formula = z_formulas.get("debug_icon")
    if not z_formula: return

    source_color = OVERLAY_COLORS["river_source"]
    term_color = OVERLAY_COLORS["river_termination"]
    radius = 70 
    outline_width = 15 # The base thickness of the circle's outline

    for path in river_paths:
        if not path: continue

        source_q, source_r = path[0]
        term_q, term_r = path[-1]

        # ✅ 3. Add a "width" property to make the circle hollow
        notebook[f"overlay_river_source_{source_q}_{source_r}"] = {
            "type": "circle", "coord": (source_q, source_r),
            "z": z_formula(source_r) + 0.0001,
            "color": source_color, "base_radius": radius, "opacity": 255,
            "width": outline_width 
        }

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
    print("🎨 Adding debug overlays...")
    
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

    print("✅ Debug overlays added.")