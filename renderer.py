# renderer.py
# The core rendering engine, responsible for sorting and drawing all visual elements.

from shared_helpers import hex_to_pixel, hex_geometry
import pygame, hashlib, math

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
FONT_CACHE = {}

# ──────────────────────────────────────────────────
# ⚙️ Initialization & Core Loop
# ──────────────────────────────────────────────────

def initialize_render_states(persistent_state, notebook):
    """
    Initializes and stores all render-specific configurations,
    including the centralized z-order formulas.
    """
    Z_ROW_MULTIPLIER = 0.001
    vert_offset = lambda r: r * Z_ROW_MULTIPLIER
    persistent_state["pers_z_formulas"] = {
        "tile":          lambda r: 1.0 + vert_offset(r),
        "collectible_shadow": lambda r: 1.0 + vert_offset(r) + 0.00071,
        "collectible_glow":   lambda r: 1.0 + vert_offset(r) + 0.00072,
        "collectible_icon":   lambda r: 1.0 + vert_offset(r) + 0.00073,
        "path_curve":       lambda r: 1.0 + vert_offset(r) + 0.0008,
        "path_curve_glide": lambda r: 1.0 + vert_offset(r) + 0.00081, # ✨ Add z-formula for the new type
        "debug_text":    lambda r: 1.0 + vert_offset(r) + 0.00085, # ✨ Add z-formula for debug text
        "player_token":  lambda r: 1.0 + vert_offset(r) + 0.0009,
        "indicator":     lambda r: 2.0,
        "debug_icon":    lambda r: 2.0 + 0.1,
        "terrain_tag":   lambda r: 2.0 + 0.2,
        "coordinate":    lambda r: 2.0 + 0.3,
        "continent_spine": lambda r: 2.0 + 0.4,
        "region_border": lambda r: 2.0 + 0.5,
        "debug_gap":     lambda r: 2.0 + 0.6,
        "ui_panel":      lambda r: 3.0,
        "screen_glow_red":lambda r: 3.8,
        "splash_screen": lambda r: 3.9,
        "fade_overlay":  lambda r: 4.0, # Highest z-value, always on top
    }

    # Create the fade overlay "buddy" here to guarantee it exists before any scene.
    # This is the "black curtain" that is down at the start of the program.
    notebook['FADE'] = {'type': 'fade_overlay', 'value': 255, 'z': persistent_state["pers_z_formulas"]["fade_overlay"](0)}

    if DEBUG: print("[renderer] ✅ Render states and z-formulas initialized.")

def get_z_value(drawable):
    # Checks if the drawable has a 'z' attribute and returns it
    if hasattr(drawable, 'z'):
        return drawable.z
    # If not, it checks if the drawable is a dictionary and returns the 'z' key's value, or 0 if not present
    elif isinstance(drawable, dict):
        return drawable.get('z', 0)
    # Returns a default z-value of 0 for all other cases
    return 0

def render_giant_z_pot(screen, notebook, persistent_state, assets_state, variable_state):
    """
    Renders all drawable items from the notebook, intelligently unpacking
    both top-level items and nested dictionaries like tile_objects.
    """
    to_draw = []
    
    # 🧠 Intelligently unpack the notebook into a single list of drawables.
    for key, value in notebook.items():
        # Case 1: The value is the dictionary of all tile objects.
        if key == 'tile_objects':
            to_draw.extend(value.values()) # Add all individual Tile objects
        # Case 2: The value is a standard drawable dictionary (like a UI panel or overlay).
        elif isinstance(value, dict) and 'type' in value:
            to_draw.append(value)

    # Sort the comprehensive list of drawables by their z-value.
    to_draw.sort(key=get_z_value)

    # 🎨 Iterate through the sorted list and render each drawable.
    for drawable in to_draw:
        # Retrieves the type of the drawable.
        typ = getattr(drawable, 'type', None) or drawable.get('type')
        interpreter = TYPEMAP.get(typ)

        if interpreter:
            interpreter(screen, drawable, persistent_state, assets_state, variable_state)
        elif DEBUG:
            print(f"[renderer] ❌ No interpreter found for drawable type '{typ}'")

# ──────────────────────────────────────────────────
# ⌨️ Drawable Interpreters
# ──────────────────────────────────────────────────

def debug_tile_text_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Renders text on a rounded, semi-transparent background for debugging."""
    text_str = drawable.get('text', '')
    if not text_str:
        return

    # ⚙️ Get font and state
    zoom = variable_state.get("var_current_zoom", 1.0)
    # Make font size smaller at high zoom levels to avoid clutter
    font_size = 12 if zoom > 0.5 else 14
    if font_size not in FONT_CACHE:
        FONT_CACHE[font_size] = pygame.font.Font(None, font_size)
    font = FONT_CACHE[font_size]

    # ✍️ Anti-jagged text trick: render white text on black, then make black transparent
    text_surf = font.render(text_str, True, (255, 255, 255), (0, 0, 0))
    text_surf.set_colorkey((0, 0, 0))
    text_rect = text_surf.get_rect()

    # 🎨 Create the rounded, semi-transparent background
    padding = 6
    bg_rect = pygame.Rect(0, 0, text_rect.width + padding, text_rect.height + padding)
    bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
    bg_color = (0, 0, 0, 150) # Black with 150/255 alpha
    border_radius = 5 # How rounded the corners are
    pygame.draw.rect(bg_surf, bg_color, bg_surf.get_rect(), border_radius=border_radius)

    # 📍 Calculate position
    q, r = drawable['q'], drawable['r']
    px, py = hex_to_pixel(q, r, persistent_state, variable_state)
    
    # Center the background, then shift it up
    bg_rect.center = (px, py)
    vertical_offset = -int(35 * zoom) # Shift text up
    bg_rect.move_ip(0, vertical_offset)
    
    # Center the text on the background
    text_rect.center = bg_rect.center

    # ✨ Blit to the main screen
    screen.blit(bg_surf, bg_rect)
    screen.blit(text_surf, text_rect)

def splash_screen_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """A simple interpreter that blits a pre-rendered surface, like a splash screen."""
    
    # Retrieves the pre-rendered surface from the drawable dictionary
    surface = drawable.get("surface")

    # Blits the surface onto the screen if it exists
    if surface:
        screen.blit(surface, (0, 0))
        
def screen_glow_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Draws a pre-rendered screen-sized glow effect with variable alpha."""
    alpha = int(drawable.get("alpha", 0))
    if alpha > 0:
        color_key = drawable.get("color", "red")
        asset_key = f"screen_edge_glow_{color_key}"
        glow_asset = assets_state["ui_assets"].get(asset_key)
        if glow_asset:
            # Use a copy to avoid modifying the original asset's alpha
            glow_copy = glow_asset.copy()
            glow_copy.set_alpha(alpha)
            screen.blit(glow_copy, (0, 0))

def fade_overlay_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Draws a screen-sized black rectangle with a variable alpha value."""
    
    # Retrieves the 'value' key from the drawable dictionary and converts it to an integer for the alpha value
    alpha = int(drawable.get("value", 0))
            
    # Checks if the alpha value is greater than 0
    if alpha > 0:

        # Creates a new surface with the same dimensions as the screen and an alpha channel for transparency
        
        # Fills the surface with a transparent black color, using the alpha value for transparency
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))

        # Blits the overlay onto the screen
        screen.blit(overlay, (0,0))

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

    # ✨ OPTIMIZATION: Now, the tile_type_interpreter can directly access the correct list without any filtering.
    # Resolve variants for the given terrain
    variants = tileset.get(terrain)
    if not variants or not variants.get('base'):
        if DEBUG: print(f"[renderer] ⚠️ Missing terrain '{terrain}', falling back to 'Base'.")
        terrain = "Base"
        variants = tileset.get("Base", {})
        if not variants.get('base'):
            if DEBUG: print("[renderer] ❌ No 'Base' variants available.")
            return

    # ✨ OPTIMIZATION: Directly access the pre-filtered list of base variants.
    non_river_variants = variants.get('base', [])

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
            ms for ms in variants.get('river', []) if ms.get("river_bitmask") == river_bitmask
        ]

        if matching_river_mountains:
            # Pick one consistently based on the tile's hash to prevent flickering.
            entry = matching_river_mountains[h % len(matching_river_mountains)]

    # If no special river-mountain sprite was found, fall back to a standard base tile.
    if not entry and non_river_variants:

        # Select a variant consistently based on the hash
        stable_variant_index = h % len(non_river_variants)
        entry = non_river_variants[stable_variant_index]

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

# [ ] TODO review: Tint shorelines based on edge-sharing terrain type.

    if hasattr(drawable, 'has_shoreline'):
        # has_shoreline = drawable.has_shoreline old code
        # coast_sprites = assets_state["tileset"].get("Coast", [])
        
        # # Find all coast sprites with a matching bitmask
        # matching_variants = [s for s in coast_sprites if s.get("bitmask") == has_shoreline]

        shoreline_bitmask = drawable.has_shoreline
        
        # ✨ OPTIMIZATION: Fast dictionary lookup instead of list filtering.
        coast_sprites_by_mask = assets_state["tileset"].get("Coast", {})
        matching_variants = coast_sprites_by_mask.get(shoreline_bitmask)

        if matching_variants:

            # Select a variant consistently based on the tile's hash
            # seed = f"{q},{r},Coast,{has_shoreline}".encode() old code
            
            # ✨ OPTIMIZATION: Fast dictionary lookup instead of list filtering.
            seed = f"{q},{r},Coast,{shoreline_bitmask}".encode()
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
                    
                    # mouth_sprites = assets_state["tileset"].get(sprite_key, [])
                    # matching_variants = [s for s in mouth_sprites if s.get("bitmask") == simple_mask] old code

                    # ✨ OPTIMIZATION: Fast dictionary lookup.
                    mouth_sprites_by_mask = assets_state["tileset"].get(sprite_key, {})
                    matching_variants = mouth_sprites_by_mask.get(simple_mask)

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
            # river_sprites = assets_state["tileset"].get(sprite_key, []) old code
            # matching_variants = [s for s in river_sprites if s.get("bitmask") == river_bitmask_str]
            
            # ✨ OPTIMIZATION: Fast dictionary lookup.
            river_sprites_by_mask = assets_state["tileset"].get(sprite_key, {})
            matching_variants = river_sprites_by_mask.get(river_bitmask_str)

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
    # ---  LAYER 1: Draw the Primary Movement Overlay ---
    
        primary_color_key = getattr(drawable, 'primary_move_color', None)
        if primary_color_key:
            glow_mask = assets_state.get("tinted_glows", {}).get(primary_color_key)
            if glow_mask:
                final_glow = glow_mask.get(current_zoom)
                if final_glow:
                    screen.blit(final_glow, (px + ox, py + oy))

        # --- LAYER 2: Draw the Secondary Overlay on top ---
        secondary_color_key = getattr(drawable, 'secondary_move_color', None)
        if secondary_color_key:
            glow_mask = assets_state.get("tinted_glows", {}).get(secondary_color_key)
            if glow_mask:
                final_glow = glow_mask.get(current_zoom)
                if final_glow:
                    screen.blit(final_glow, (px + ox, py + oy))

    # 🧠 Delegate to the Tilebox interpreter if the tilebox contains anything
    if hasattr(drawable, 'tilebox') and drawable.tilebox:
        tilebox_interpreter(screen, drawable, persistent_state, variable_state, assets_state)

def tilebox_interpreter(screen, tile_drawable, persistent_state, variable_state, assets_state):
    """
    The specialist interpreter for drawing status icons in the "Tilebox" area.
    """
    # ⚙️ Setup & Data
    # Get the list of resources to display from the tile
    resources_to_draw = tile_drawable.tilebox.get('resources', [])
    if not resources_to_draw:
        return

    # Get the pixel geometry for the tile
    q, r = tile_drawable.q, tile_drawable.r
    geom = hex_geometry(q, r, persistent_state, variable_state)

    # Define the tilebox hex using its corners
    nw_corner = geom['corners'][5]
    ne_corner = geom['corners'][1]

    # ✍️ Calculate Icon Positions
    # For a single resource, place it in the center of the brow
    if len(resources_to_draw) == 1:
        # The center is simply the midpoint of the two corners
        center_x = (nw_corner[0] + ne_corner[0]) / 2
        center_y = (nw_corner[1] + ne_corner[1]) / 2
        anchor_points = [(center_x, center_y)]
    else:
        # For multiple resources, space them out evenly along the brow
        anchor_points = []
        num_icons = len(resources_to_draw)
        for i in range(num_icons):
            # Interpolate between the NW and NE corners
            t = (i + 1) / (num_icons + 1) # e.g., for 2 icons, t = 0.33 and 0.66
            x = nw_corner[0] * (1 - t) + ne_corner[0] * t
            y = nw_corner[1] * (1 - t) + ne_corner[1] * t
            anchor_points.append((x, y))

    # 🎨 Draw the Icons
    # Define a simple color for our resource icon for now
    resource_color = (255, 165, 0) # Orange
    zoom = variable_state.get("var_current_zoom", 1.0)
    radius = max(2, int(8 * zoom))

    for point in anchor_points:
        pygame.draw.circle(screen, resource_color, (int(point[0]), int(point[1])), radius)
        
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
    
    # ✨ 1. Determine color based on the drawable's type.
    drawable_type = drawable.get('type')
    if drawable_type == 'path_curve_glide':
        color = (177, 33, 255)  # Purple for glide paths
    else:
        color = (255, 222, 33)  # Yellow for standard paths

    # Retrieves the current, previous, and next hex coordinates from the drawable dictionary
    coord = drawable.get("coord")
    prev_coord = drawable.get("prev_coord")
    next_coord = drawable.get("next_coord")

    # Gets the geometric data for the current hex
    geom = hex_geometry(coord[0], coord[1], persistent_state, variable_state)
    
    # Determine the start and end points of the curve for this tile
    entry_dir, exit_dir = None, None

    # Determines the starting point of the curve within the tile
    if prev_coord is None:

        # If there is no previous hex, the path starts at the center of the current hex
        p_start = geom['center']
    else:

        # Finds the direction of the adjacent previous hex
        entry_dir = [d for d, n in geom['neighbors'].items() if n == prev_coord][0]
        
        # Gets the two corners that define the entry edge
        edge_corners = geom['edges'][persistent_state['pers_edge_index'][entry_dir]]
        
        # The start point is the midpoint of the entry edge
        p_start = ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)

    # Determines the end point of the curve within the tile
    if next_coord is None:

        # If there is no next hex, the path ends at the center of the current hex
        p_end = geom['center']
    else:

        # Finds the direction of the adjacent next hex
        exit_dir = [d for d, n in geom['neighbors'].items() if n == next_coord][0]
        
        # Gets the two corners that define the exit edge
        edge_corners = geom['edges'][persistent_state['pers_edge_index'][exit_dir]]
        
        # The end point is the midpoint of the exit edge
        p_end = ((edge_corners[0][0] + edge_corners[1][0]) / 2, (edge_corners[0][1] + edge_corners[1][1]) / 2)

    # A path is straight if the entry and exit directions are opposites.
    # Defines a mapping of each direction to its opposite
    opposite_directions = {
        "E": "W", "W": "E",
        "NE": "SW", "SW": "NE",
        "NW": "SE", "SE": "NW"
    }

    # Checks if a straight path is possible by comparing the entry and exit directions
    is_straight = entry_dir and exit_dir and exit_dir == opposite_directions.get(entry_dir)

    # Retrieves the current zoom level and calculates the thickness of the line
    zoom = variable_state.get("var_current_zoom", 1.0)
    thickness = max(2, int(16 * zoom))

    # If the path is a straight line, it is drawn as a simple line
    if is_straight:
        pygame.draw.line(screen, color, p_start, p_end, thickness)

    # Otherwise, it is drawn as a Bezier curve for a smooth turn
    else:
        # For turns, find the pivot corner to use as the Bézier control point
        # The control point is the center of the hex by default
        control_point = geom['center']

        # If both a previous and next hex exist, a more specific control point is calculated
        if prev_coord and next_coord:

            # Gets the corner indices for both the entry and exit edges
            entry_corners = set(persistent_state["pers_hex_anatomy"]["edges"][persistent_state['pers_edge_index'][entry_dir]]["corner_pair"])
            exit_corners = set(persistent_state["pers_hex_anatomy"]["edges"][persistent_state['pers_edge_index'][exit_dir]]["corner_pair"])
            # Find the shared corner, if one exists
            intersection = entry_corners.intersection(exit_corners)
            if intersection:

                # The shared corner is used as the pivot point for the curve
                pivot_corner_index = list(intersection)[0]
                control_point = geom['corners'][pivot_corner_index]

        # Draws the Bezier curve using the start, control, and end points
        _draw_bezier_curve(screen, p_start, control_point, p_end, thickness, color)

def ui_panel_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """Renders a pre-surfaced UI panel from the notebook."""
    # Get the pre-rendered surface from the drawable
    surface = drawable.get("surface")
    
    # Get the position and dimensions from the drawable
    rect = drawable.get("rect")
    
    # Blit the surface to the screen if both exist
    if surface and rect:
        screen.blit(surface, rect)

def artwork_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """
    A single, generic interpreter for all map-based artwork (players, collectibles, etc.).
    It uses keys within the drawable to look up the correct asset data.
    """
    # ⚙️ Get shared state
    current_zoom = variable_state.get("var_current_zoom", 1.0)
    
    # 🎨 Look up the asset data using keys from the drawable itself.
    asset_category = drawable.get("asset_category")
    asset_key = drawable.get("asset_key")
    
    asset_data = assets_state.get(asset_category, {}).get(asset_key)
    if not asset_data:
        if DEBUG: print(f"[renderer] ⚠️ Missing asset data for '{asset_category}.{asset_key}'")
        return

    # 📍 Calculate screen position from the hex coordinate.
    px, py = hex_to_pixel(drawable['q'], drawable['r'], persistent_state, variable_state)
    
    # 🤸 Apply local tweening offset (e.g., bobbing) if it exists.
    # The offset is in world pixels, so it must be scaled by the current zoom.
    if 'pixel_pos' in drawable:
        # Handle positional tweens (like player movement) by overriding the hex position.
        world_px, world_py = drawable['pixel_pos']
        offset_x, offset_y = variable_state.get("var_render_offset", (0, 0))
        px = (world_px * current_zoom) + offset_x
        py = (world_py * current_zoom) + offset_y
    
    local_offset_x, local_offset_y = drawable.get('local_render_offset', (0, 0))
    px += local_offset_x * current_zoom
    py += local_offset_y * current_zoom
    
    # 🖼️ Get the correctly pre-scaled sprite and its blit offset from the asset data.
    sprite_map = asset_data.get("scale", {})
    final_sprite = sprite_map.get(current_zoom)
    
    if final_sprite:
        off_x, off_y = asset_data["blit_offset"]
        
        # 📏 The blit offset is relative to the asset's center, so it also needs scaling.
        ox = int(off_x * current_zoom)
        oy = int(off_y * current_zoom)
        
        # 🎨 Blit the final sprite to the screen at its calculated position.
        screen.blit(final_sprite, (px + ox, py + oy))

def render_indicator(screen, drawable, persistent_state, assets_state, variable_state):
    """Renders the indicator orbiting the player at a fixed radius."""
    # 🎨 Config: Adjust this radius to change the diameter of the "train tracks."
    # This value is in world pixels, so it will scale with zoom.
    INDICATOR_ORBIT_RADIUS = 120

    # ⚙️ Get Asset and State
    original_asset = assets_state["ui_assets"]["collectible_indicator"]
    angle_deg = drawable['angle']
    current_zoom = variable_state["var_current_zoom"]

    # 🗺️ Calculate Orbital Anchor Point
    # The GameManager now provides the exact world-space anchor point.
    # We just need to convert it to screen space by applying camera zoom and offset.
    world_anchor_x, world_anchor_y = drawable['anchor_world_pos']
    cam_offset_x, cam_offset_y = variable_state.get("var_render_offset", (0, 0))
    
    center_x = (world_anchor_x * current_zoom) + cam_offset_x
    center_y = (world_anchor_y * current_zoom) + cam_offset_y

    # Convert the angle to radians for trigonometric functions.
    angle_rad = math.radians(angle_deg)
    
    # Calculate the offset from the center based on the angle and our desired radius.
    # The radius is scaled by zoom to maintain a consistent visual distance.
    radius = INDICATOR_ORBIT_RADIUS * current_zoom
    offset_x = radius * math.cos(angle_rad)
    offset_y = -radius * math.sin(angle_rad)

    # The final anchor point is the tile's center plus our calculated offset.
    screen_anchor_x = center_x + offset_x
    screen_anchor_y = center_y + offset_y

    # 🔄 Rotate the Asset Around its Pivot
    final_angle = angle_deg
    rotated_asset = pygame.transform.rotate(original_asset, final_angle)
    rotated_rect = rotated_asset.get_rect()

    # To place the pivot on the anchor, we find the vector from the sprite's center 
    # to its pivot point, rotate it, and use it as an offset.
    # Original pivot is at (0, height/2). Original center is at (width/2, height/2).
    # The vector from center to pivot is thus (-width/2, 0).
    offset_vector = pygame.math.Vector2(-original_asset.get_width() / 2, 0)
    rotated_offset = offset_vector.rotate(-final_angle)

    # The center of our blit rect should be the anchor point PLUS the offset vector.
    # This effectively moves the center of the image so the pivot can land on the anchor.
    blit_center_x = screen_anchor_x + rotated_offset.x
    blit_center_y = screen_anchor_y + rotated_offset.y

    # ✨ Draw the asset on screen.
    rotated_rect.center = (blit_center_x, blit_center_y)
    screen.blit(rotated_asset, rotated_rect)

# ──────────────────────────────────────────────────
# ⌨️ Interpreter Dispatch
# ──────────────────────────────────────────────────
# The type map that dispatches draw calls to the correct interpreter.
TYPEMAP = {
    "tile": tile_type_interpreter,
    "circle": circle_type_interpreter,
    "artwork": artwork_interpreter,
    "path_curve": path_curve_interpreter,
    "path_curve_glide": path_curve_interpreter,
    "ui_panel": ui_panel_interpreter,
    "splash_screen": splash_screen_interpreter,
    "fade_overlay": fade_overlay_interpreter,
    "screen_glow_overlay": screen_glow_interpreter,
    "indicator": render_indicator,
    "debug_tile_text": debug_tile_text_interpreter, # ✨ Register the new interpreter
   }