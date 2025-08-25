# renderer.py
# The core rendering engine, responsible for sorting and drawing all visual elements.

from shared_helpers import hex_to_pixel, snap_zoom_to_nearest_step, hex_geometry
import pygame, hashlib


# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
FONT_CACHE = {}

# ──────────────────────────────────────────────────
# ⚙️ Initialization & Core Loop
# ──────────────────────────────────────────────────

# In renderer.py

def initialize_render_states(persistent_state):
    """
    Initializes and stores all render-specific configurations,
    including the centralized z-order formulas.
    """
    # Define a constant to create a consistent vertical position offset
    Z_ROW_MULTIPLIER = 0.001
    
    # Create a reusable helper function for the vertical position offset.
    vert_offset = lambda r: r * Z_ROW_MULTIPLIER

    # Z-Order Formulas
    persistent_state["pers_z_formulas"] = {

        # --- Layer 1: Core World ---
        "tile":          lambda r: 1.0 + vert_offset(r),
        "path_curve":     lambda r: 1.0 + vert_offset(r) + 0.0001, # Just under the token
        "player_token":  lambda r: 1.0 + vert_offset(r) + 0.0002, # Just above its tile

        # --- Layer 2: Debug Overlays ---
        "debug_icon":    lambda r: 2.0 + 0.1,
        "terrain_tag":   lambda r: 2.0 + 0.2,
        "coordinate":    lambda r: 2.0 + 0.3,
        "continent_spine": lambda r: 2.0 + 0.4,
        "region_border": lambda r: 2.0 + 0.5,
        "debug_gap":     lambda r: 2.0 + 0.6,
    }
    
    print("[renderer] ✅ Render states and z-formulas initialized.")

    
def get_font(size):
    """Return a cached SysFont of the given size."""

    # Check if the requested font size is already in the cache
    font = FONT_CACHE.get(size)
    if font is None:

        # If not, create a new font and store it in the cache
        font = pygame.font.SysFont("Arial", size)
        FONT_CACHE[size] = font
    return font

def get_z_value(drawable):
    """A universal getter for 'z' that works on both objects and dicts."""
    if hasattr(drawable, 'z'):
        return drawable.z
    elif isinstance(drawable, dict):
        return drawable.get('z', 0)
    return 0

def render_giant_z_pot(screen, tile_objects, notebook, persistent_state, assets_state, variable_state):
    """
    Collects every entry from both tiledata and notebook,
    sorts them all by 'z', and steps through them in order.
    If any entry is missing 'z', skips it and prints a debug message (if DEBUG).
    """

    # Combine all drawable entries from both the tiledata and the notebook
    draw_pot = list(tile_objects.values()) + list(notebook.values())

    # Filter out entries missing a 'z' value and count the number skipped
    to_draw = []
    skipped = 0

    for entry in draw_pot:
        # This universal check now correctly finds 'z' in both objects and dictionaries
        has_z = hasattr(entry, 'z') or (isinstance(entry, dict) and 'z' in entry)
        if has_z:
            to_draw.append(entry)
        else:
            skipped += 1

    # Print a debug message if any drawables were skipped
    if DEBUG and skipped:
        print(f"[renderer] ⚠️ {skipped} drawables skipped (missing 'z' value)")

    # Sort the list of drawables by their z-order
    to_draw.sort(key=get_z_value)

    # Render each drawable in z-order
    for drawable in to_draw:

        # Get the interpreter for the drawable's type
        typ = getattr(drawable, 'type', None) or drawable.get('type') # Also make this universal
        interpreter = TYPEMAP.get(typ)
        if interpreter:

            # Call the appropriate interpreter function
            interpreter(screen, drawable, persistent_state, assets_state, variable_state)
        else:
            # Optionally log or handle missing interpreter
            pass

# ──────────────────────────────────────────────────
# ⌨️ Drawable Interpreters
# ──────────────────────────────────────────────────

def tile_type_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """
    Renders tiles, with special logic for river-aware mountains.
    """

    # 🖼️ Resolve Sprite and Variants
    q, r = drawable.q, drawable.r

    # Get the terrain type, defaulting to "Base" if not specified
    terrain = drawable.terrain or "Base"
    tileset = assets_state["tileset"]

    # 0) Early special-cases (example)
    # terrain = (drawable.get("terrain") or "Base")
    # if terrain == "Ocean":
    #     ocean_interpreter(screen, drawable, persistent_state, assets_state)
    #     return

    # Resolve variants for the given terrain
    variants = tileset.get(terrain)
    if not variants:
        if DEBUG: print(f"[renderer] ⚠️ Missing terrain '{terrain}', falling back to 'Base'.")
        terrain = "Base"
        variants = tileset.get("Base", [])
        if not variants:
            if DEBUG: print("[renderer] ❌ No 'Base' variants available.")
            return
    non_river_variants = [v for v in variants if "river_bitmask" not in v]
    if not non_river_variants:
        non_river_variants = variants

    # Create a stable hash from the tile's coordinates and terrain type
    seed = f"{q},{r},{terrain}".encode()
    h = int.from_bytes(hashlib.md5(seed).digest(), "big")
    stable_variant_index = h % len(non_river_variants)
    
    # Initialize the sprite entry as None
    entry = None

    # Handle the special case for river-aware mountain tiles
    if terrain == "Mountain" and hasattr(drawable, 'river_data'):

        # Suppress the separate river overlay since the tile itself has the river baked in
        drawable.suppress_river_overlay = True
        river_bitmask = drawable.river_data["bitmask"]

        # Find ANY mountain sprite with the correct bitmask
        matching_river_mountains = [
            ms for ms in variants if ms.get("river_bitmask") == river_bitmask
        ]

        if matching_river_mountains:
            # Pick one consistently based on the tile's hash to prevent flickering.
            entry = matching_river_mountains[h % len(matching_river_mountains)]

    if entry is None:
        # If no special sprite was found, find a standard base tile.
        non_river_variants = [v for v in variants if "river_bitmask" not in v]

        # Select a variant consistently based on the hash
        if non_river_variants:
            stable_variant_index = h % len(non_river_variants)
            entry = non_river_variants[stable_variant_index]
        else:

            # Failsafe: fall back to any available variant
            entry = variants[h % len(variants)] # Failsafe

    if not entry:
        if DEBUG: print(f"[renderer] ❌ Could not resolve a sprite for {terrain} at ({q},{r}).")
        return

    # 🔄 Apply Scaling and Blitting
    current_zoom = variable_state.get("var_current_zoom", 1.0)

    # Get the pixel coordinates for the hex
    px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    # Calculate the blit offset to center the sprite on the tile
    off_x, off_y = entry["blit_offset"]

    # The current_zoom is now guaranteed to be a valid, snapped value.
    offset_scale = current_zoom
    ox = int(off_x * offset_scale)
    oy = int(off_y * offset_scale)

    # Get the correct pre-scaled sprite from the cache. This is a fast dictionary lookup.
    sprite_map = entry.get("scale") or {1.0: entry["sprite"]}
    final = sprite_map.get(current_zoom)

    # Failsafe if the snapped zoom level doesn't have a pre-scaled sprite.
    if final is None:
        if DEBUG: print(f"[renderer] ❌ Missing pre-scaled sprite for zoom level {current_zoom:.2f} for '{terrain}'.")
        return

    # Blit the selected base terrain sprite
    screen.blit(final, (px + ox, py + oy))

    # 🌊 Blit Overlays (Coast, River, etc.)
    # Render coastline if the tile has a `has_shoreline` tag

# Next review: Tint shorelines based on edge-sharing terrain type.

    if hasattr(drawable, 'has_shoreline'):
        has_shoreline = drawable.has_shoreline
        coast_sprites = assets_state["tileset"].get("Coast", [])
        
        # Find all coast sprites with a matching bitmask
        matching_variants = [s for s in coast_sprites if s.get("bitmask") == has_shoreline]

        if matching_variants:

            # Select a variant consistently based on the tile's hash
            seed = f"{q},{r},Coast,{has_shoreline}".encode()
            h = int.from_bytes(hashlib.md5(seed).digest(), "big")
            coast_entry = matching_variants[h % len(matching_variants)]

            # Get the pre-scaled sprite for the current zoom
            coast_sprite_map = coast_entry.get("scale") or {1.0: coast_entry["sprite"]}
            final_coast_sprite = coast_sprite_map.get(current_zoom) or coast_sprite_map.get(1.0)
            
            # Blit the coastline overlay
            coast_off_x, coast_off_y = coast_entry["blit_offset"]
            cox = int(coast_off_x * offset_scale)
            coy = int(coast_off_y * offset_scale)
            
            if final_coast_sprite:
                screen.blit(final_coast_sprite, (px + cox, py + coy))

    # Blit river, mouth, and spring overlays
    if hasattr(drawable, 'river_data') and not getattr(drawable, 'suppress_river_overlay', False):
        river_bitmask_str = drawable.river_data["bitmask"]
        
        # Determine which kind of river piece to draw based on its properties
        is_source = drawable.river_data.get("is_river_source", False)
        is_mountain = getattr(drawable, 'is_mountain', False)
        connection_count = river_bitmask_str.count('1')

        # A tile is a "spring" (RiverEnd) only if it's a source and has just one connection.
        if is_source and not is_mountain and connection_count <= 1:
            sprite_key = "RiverEnd"
        else:

            # Otherwise, treat it as a regular river or a mouth.
            is_ocean_endpoint = getattr(drawable, 'is_ocean', False)
            is_lowland_endpoint = getattr(drawable, 'lowlands', False)
            is_lake_endpoint = getattr(drawable, 'is_lake', False)
            is_endpoint = is_ocean_endpoint or is_lowland_endpoint or is_lake_endpoint
            
            # If it's an endpoint, use the RiverMouth sprite, otherwise use a regular River sprite
            sprite_key = "RiverMouth" if is_endpoint else "River"

        # --- Blitting Logic ---
        if sprite_key == "RiverMouth":
            # Mouths use special decomposition logic to handle multiple inflows
            for i, bit in enumerate(river_bitmask_str):
                if bit == '1':

                    # Create a simple bitmask for a single connection
                    simple_mask_list = ['0'] * 6
                    simple_mask_list[i] = '1'
                    simple_mask = "".join(simple_mask_list)
                    
                    mouth_sprites = assets_state["tileset"].get(sprite_key, [])
                    matching_variants = [s for s in mouth_sprites if s.get("bitmask") == simple_mask]

                    if matching_variants:

                        # Select the sprite consistently based on a new hash
                        seed = f"{q},{r},{sprite_key},{simple_mask}".encode()
                        h = int.from_bytes(hashlib.md5(seed).digest(), "big")
                        entry = matching_variants[h % len(matching_variants)]
                        sprite_map = entry.get("scale") or {1.0: entry["sprite"]}
                        final_sprite = sprite_map.get(current_zoom) or sprite_map.get(1.0)
                        off_x, off_y = entry["blit_offset"]
                        rox, roy = int(off_x * offset_scale), int(off_y * offset_scale)
                        if final_sprite:
                            screen.blit(final_sprite, (px + rox, py + roy))
        else:

            # Regular Rivers and Springs use the same, simpler blitting logic
            river_sprites = assets_state["tileset"].get(sprite_key, [])
            matching_variants = [s for s in river_sprites if s.get("bitmask") == river_bitmask_str]
            
            if matching_variants:

                # Select the sprite consistently based on a new hash
                seed = f"{q},{r},{sprite_key},{river_bitmask_str}".encode()
                h = int.from_bytes(hashlib.md5(seed).digest(), "big")
                entry = matching_variants[h % len(matching_variants)]
                sprite_map = entry.get("scale") or {1.0: entry["sprite"]}
                final_sprite = sprite_map.get(current_zoom) or sprite_map.get(1.0)
                off_x, off_y = entry["blit_offset"]
                rox, roy = int(off_x * offset_scale), int(off_y * offset_scale)
                if final_sprite:
                    screen.blit(final_sprite, (px + rox, py + roy))
                                               
    # Check if the tile object has the 'hovered' attribute and if it's True
    if getattr(drawable, 'hovered', False) or getattr(drawable, 'is_selected', False):

        # Get the dictionary of pre-scaled glow masks.
        glow_masks = assets_state.get("glow_masks_by_zoom")
        if glow_masks:

            # Look up the correct mask using the current_zoom value (already calculated).
            final_glow = glow_masks.get(current_zoom)
            if final_glow:

                # Blit the pre-scaled mask. This is extremely fast.
                screen.blit(final_glow, (px + ox, py + oy), special_flags=pygame.BLEND_RGB_ADD)
    
    # Check for movement overlay glow
    if getattr(drawable, 'movement_overlay', False):
        color_key = getattr(drawable, 'move_color', 'good')
        
        tinted_glows_by_color = assets_state.get("tinted_glows", {})
        masks_for_this_color = tinted_glows_by_color.get(color_key)
        
        if masks_for_this_color:
            final_glow = masks_for_this_color.get(current_zoom)
            if final_glow:
                off_x, off_y = persistent_state["pers_asset_blit_offset"]
                ox = int(off_x * current_zoom)
                oy = int(off_y * current_zoom)
                screen.blit(final_glow, (px + ox, py + oy))
        
def circle_type_interpreter(screen, drawable, persistent_state, assets_state, variable_state):

    # Determine if the circle position is based on hex coordinates or explicit pixel coordinates
    if "pixel_coord" in drawable:
        px, py = drawable["pixel_coord"]
    else:
        q, r = drawable["coord"]
        px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    # Get the current zoom and color
    zoom = variable_state.get("var_current_zoom", 1.0)
    color = drawable.get("color", (0, 0, 0))
    radius = 0

    # Determine the radius based on a matching line thickness or a base radius
    if "matches_line_thickness" in drawable:
        base_thickness = drawable["matches_line_thickness"]
        final_thickness = max(1, int(base_thickness * zoom))
        radius = final_thickness // 2
    else:
        base_radius = drawable.get("base_radius", 30)
        radius = max(1, int(base_radius * zoom))

    radius = max(1, radius)
    
    # Check for a "width" property to draw a hollow circle
    width = drawable.get("width", 0) # Default to 0 (filled)
    final_width = max(1, int(width * zoom)) if width > 0 else 0

    # Draw the circle on the screen
    pygame.draw.circle(screen, color, (int(px), int(py)), radius, final_width)

def text_type_interpreter(screen, drawable, persistent_state, assets_state, variable_state):

    # Convert hex coordinates to pixel coordinates
    q = getattr(drawable, 'q', drawable.get('coord', [0, 0])[0])
    r = getattr(drawable, 'r', drawable.get('coord', [0, 0])[1])
    px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    # Adjust font size based on zoom so it stays readable
    zoom = variable_state.get("var_current_zoom", 1.0)
    base_size = drawable.get("base_size", 16)
    font_size = max(8, int(base_size * zoom))

    # Get cached font object
    font = get_font(font_size)

    # Prepare the text and color for rendering
    text = str(getattr(drawable, 'text', drawable.get("text", "")))
    color = getattr(drawable, 'color', drawable.get("color", (0, 0, 0)))

    # Render the text and blit it to the screen
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(px, py))
    screen.blit(surf, rect.topleft)


def edge_line_type_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """
    Draws a zoom-safe line between p1 and p2 from drawable.
    """

    # Get the start and end pixel coordinates
    p1 = drawable["p1"]
    p2 = drawable["p2"]

    # Get the color and thickness properties
    color = drawable.get("color", (0, 0, 0))
    zoom = variable_state.get("var_current_zoom", 1.0)

    # Adjust the line thickness based on zoom
    thickness = max(1, int(drawable.get("thickness", 2) * zoom))

    # Draw the line on the screen
    pygame.draw.line(screen, color, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), thickness)

def player_token_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Renders the player token using pixel_pos if available, otherwise q,r."""

    current_zoom = variable_state.get("var_current_zoom", 1.0)

    if 'pixel_pos' in drawable:
        # The token is animating, use the precise pixel position.
        base_px, base_py = drawable['pixel_pos']
        # Apply camera transforms to the world-space pixel position
        offset_x, offset_y = variable_state.get("var_render_offset", (0, 0))
        px = (base_px * current_zoom) + offset_x
        py = (base_py * current_zoom) + offset_y
    else:
        # The token is static, calculate position from its hex coordinates.
        px, py = hex_to_pixel(drawable['q'], drawable['r'], persistent_state, variable_state)

    # 🖼️ Get the correctly pre-scaled sprite and its offset
    sprite_map = drawable.get("scale") or {1.0: drawable["sprite"]}
    final = sprite_map.get(current_zoom)
    off_x, off_y = drawable["blit_offset"]

    if final:
        # Scale the blit offset for the current zoom level
        offset_scale = current_zoom
        ox = int(off_x * offset_scale)
        oy = int(off_y * offset_scale)
        screen.blit(final, (px + ox, py + oy))

def _draw_bezier_curve(surface, p0, p1, p2, thickness, color):
    """Helper to draw a quadratic Bézier curve."""
    points = []
    # The more steps, the smoother the curve
    for t in range(21):
        t /= 20.0
        x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        points.append((x, y))

    pygame.draw.lines(surface, color, False, points, thickness)

def path_curve_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Draws a smooth curve inside a tile based on the path's entry and exit points."""
    coord = drawable.get("coord")
    prev_coord = drawable.get("prev_coord")
    next_coord = drawable.get("next_coord")

    geom = hex_geometry(coord[0], coord[1], persistent_state, variable_state)
    
    # Determine the start and end points of the curve for this tile
    entry_dir, exit_dir = None, None

    if prev_coord is None:
        p_start = geom['center']
    else:
        entry_dir = [d for d, n in geom['neighbors'].items() if n == prev_coord][0]
        edge_corners = geom['edges'][persistent_state['pers_edge_index'][entry_dir]]
        p_start = ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)

    if next_coord is None:
        p_end = geom['center']
    else:
        exit_dir = [d for d, n in geom['neighbors'].items() if n == next_coord][0]
        edge_corners = geom['edges'][persistent_state['pers_edge_index'][exit_dir]]
        p_end = ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)

    # A path is straight if the entry and exit directions are opposites.
    opposite_directions = {
        "E": "W", "W": "E",
        "NE": "SW", "SW": "NE",
        "NW": "SE", "SE": "NW"
    }
    is_straight = entry_dir and exit_dir and exit_dir == opposite_directions.get(entry_dir)

    zoom = variable_state.get("var_current_zoom", 1.0)
    thickness = max(2, int(16 * zoom))
    color = (255, 222, 33)

    if is_straight:
        pygame.draw.line(screen, color, p_start, p_end, thickness)
    else:
        # For turns, find the pivot corner to use as the Bézier control point
        control_point = geom['center']
        if prev_coord and next_coord:
            entry_corners = set(persistent_state["pers_hex_anatomy"]["edges"][persistent_state['pers_edge_index'][entry_dir]]["corner_pair"])
            exit_corners = set(persistent_state["pers_hex_anatomy"]["edges"][persistent_state['pers_edge_index'][exit_dir]]["corner_pair"])
            # Find the shared corner, if one exists
            intersection = entry_corners.intersection(exit_corners)
            if intersection:
                pivot_corner_index = list(intersection)[0]
                control_point = geom['corners'][pivot_corner_index]
        _draw_bezier_curve(screen, p_start, control_point, p_end, thickness, color)
     

def debug_triangle_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """
    Draws a polygon from a pre-defined list of world-space vertices and a color.
    This "dumb" interpreter is responsible for applying camera transformations.
    """
    # 🎨 Get the pre-defined color and world-space vertices from the drawable
    color = drawable.get("color", (255, 0, 0)) # Default to red if no color is specified
    world_points = drawable.get("points", [])
    
    if not world_points:
        return

    # 🎥 Apply camera zoom and offset to each point
    zoom = variable_state.get("var_current_zoom", 1.0)
    offset_x, offset_y = variable_state.get("var_render_offset", (0, 0))
    
    screen_points = []
    for wx, wy in world_points:
        sx = (wx * zoom) + offset_x
        sy = (wy * zoom) + offset_y
        screen_points.append((sx, sy))
        
    # ✍️ Draw the final polygon on the screen
    pygame.draw.polygon(screen, color, screen_points)

# ──────────────────────────────────────────────────
# ⌨️ Interpreter Dispatch
# ──────────────────────────────────────────────────
# The type map that dispatches draw calls to the correct interpreter.
TYPEMAP = {
    "tile": tile_type_interpreter,
    "circle": circle_type_interpreter,
    "text": text_type_interpreter,
    "edge_line": edge_line_type_interpreter,
    "player_token": player_token_interpreter,
    "path_curve": path_curve_interpreter,
    "debug_triangle": debug_triangle_interpreter,
}


