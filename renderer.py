# renderer.py
# The core rendering engine, responsible for sorting and drawing all visual elements.

from shared_helpers import hex_to_pixel, snap_zoom_to_nearest_step
import pygame, hashlib


# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
FONT_CACHE = {}

# ──────────────────────────────────────────────────
# ⚙️ Initialization & Core Loop
# ──────────────────────────────────────────────────

def initialize_render_states(persistent_state):
    """
    Initializes and stores all render-specific configurations,
    including the centralized z-order formulas.
    """
    # Define a constant to create a consistent vertical position offset
    Z_ROW_MULTIPLIER = 0.001
    
    # Create a reusable helper function for the vertical position offset.
    vert_offset = lambda r: r * Z_ROW_MULTIPLIER

    # Use the helper in the main formulas dictionary
    persistent_state["pers_z_formulas"] = {

        # --- Base Terrain ---
        "tile":          lambda r: 1.0 + vert_offset(r),

        # --- Debug Overlays ---
        "debug_icon":    lambda r: 1.0 + vert_offset(r) + 0.0003,
        "terrain_tag":   lambda r: 1.0 + vert_offset(r) + 0.0004,
        "coordinate":    lambda r: 1.0 + vert_offset(r) + 0.0005,
        "continent_spine": lambda r: 1.0 + vert_offset(r) + 0.0006,
        "region_border": lambda r: 1.0 + vert_offset(r) + 0.5,
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

def render_giant_z_pot(screen, tiledata, notebook, persistent_state, assets_state, variable_state):
    """
    Collects every entry from both tiledata and notebook,
    sorts them all by 'z', and steps through them in order.
    If any entry is missing 'z', skips it and prints a debug message (if DEBUG).
    """

    # Combine all drawable entries from both the tiledata and the notebook
    draw_pot = list(tiledata.values()) + list(notebook.values())

    # Filter out entries missing a 'z' value and count the number skipped
    to_draw = []
    skipped = 0
    for entry in draw_pot:
        if "z" in entry:
            to_draw.append(entry)
        else:
            skipped += 1

    # Print a debug message if any drawables were skipped
    if DEBUG and skipped:
        print(f"[renderer] {skipped} drawables skipped (missing 'z' value)")

    # Sort the list of drawables by their z-order
    to_draw.sort(key=lambda d: d.get("z", 0))

    # Render each drawable in z-order
    for drawable in to_draw:

        # Get the interpreter for the drawable's type
        typ = drawable.get("type")
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
    q, r = drawable["coord"]

    # Get the terrain type, defaulting to "Base" if not specified
    terrain = drawable.get("terrain") or "Base"
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
    if terrain == "Mountain" and "river_data" in drawable:

        # Suppress the separate river overlay since the tile itself has the river baked in
        drawable['suppress_river_overlay'] = True
        river_bitmask = drawable["river_data"]["bitmask"]

        # Find ANY mountain sprite with the correct bitmask
        matching_river_mountains = [
            ms for ms in variants if ms.get("river_bitmask") == river_bitmask
        ]

        if matching_river_mountains:
            # Pick one consistently based on the tile's hash to prevent flickering.
            entry = matching_river_mountains[h % len(matching_river_mountains)]

    # --- FALLBACK LOGIC ---
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
    # Get the current zoom and zooming state
    current_zoom = variable_state.get("var_current_zoom", 1.0)
    is_zooming   = bool(variable_state.get("var_is_zooming"))

    # Snap the zoom to the nearest step for crisp rendering when not actively zooming
    snapped_zoom = snap_zoom_to_nearest_step(persistent_state, variable_state) if not is_zooming else None

    # Get the pixel coordinates for the hex
    px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    # Calculate the blit offset to center the sprite on the tile
    off_x, off_y = entry["blit_offset"]
    offset_scale = current_zoom if is_zooming else snapped_zoom
    ox = int(off_x * offset_scale)
    oy = int(off_y * offset_scale)

    # Get the final sprite based on the zoom level
    if is_zooming:

        # Use a smooth scaling for fluid zoom animations
        spr = entry["sprite"]
        tw = max(1, int(spr.get_width() * current_zoom))
        th = max(1, int(spr.get_height() * current_zoom))
        final = pygame.transform.scale(spr, (tw, th))
    else:

        # Use the pre-rendered, scaled sprites for sharp, fast rendering
        sprite_map = entry.get("scale") or {1.0: entry["sprite"]}
        final = sprite_map.get(snapped_zoom) or sprite_map.get(1.0)
        if final is None:
            if DEBUG: print(f"[renderer] ❌ Missing sprite at {snapped_zoom:.2f} and 1.0 for '{terrain}'.")
            return

    # Blit the selected base terrain sprite
    screen.blit(final, (px + ox, py + oy))

    # 🌊 Blit Overlays (Coast, River, etc.)
    # Render coastline if the tile has a `has_shoreline` tag
    if "has_shoreline" in drawable:
        has_shoreline = drawable["has_shoreline"]
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
            final_coast_sprite = coast_sprite_map.get(snapped_zoom) or coast_sprite_map.get(1.0)
            
            # Blit the coastline overlay
            coast_off_x, coast_off_y = coast_entry["blit_offset"]
            cox = int(coast_off_x * offset_scale)
            coy = int(coast_off_y * offset_scale)
            
            if final_coast_sprite:
                screen.blit(final_coast_sprite, (px + cox, py + coy))

    # Blit river, mouth, and spring overlays
    if "river_data" in drawable and not drawable.get('suppress_river_overlay'):
        river_bitmask_str = drawable["river_data"]["bitmask"]
        
        # Determine which kind of river piece to draw based on its properties
        is_source = drawable["river_data"].get("is_river_source", False)
        is_mountain = drawable.get("is_mountain", False)
        connection_count = river_bitmask_str.count('1')

        # A tile is a "spring" (RiverEnd) only if it's a source and has just one connection.
        if is_source and not is_mountain and connection_count <= 1:
            sprite_key = "RiverEnd"
        else:

            # Otherwise, treat it as a regular river or a mouth.
            is_ocean_endpoint = drawable.get("is_ocean", False)
            is_lowland_endpoint = drawable.get("lowlands", False)
            is_lake_endpoint = drawable.get("is_lake", False)
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
                        final_sprite = sprite_map.get(snapped_zoom) or sprite_map.get(1.0)
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
                final_sprite = sprite_map.get(snapped_zoom) or sprite_map.get(1.0)
                off_x, off_y = entry["blit_offset"]
                rox, roy = int(off_x * offset_scale), int(off_y * offset_scale)
                if final_sprite:
                    screen.blit(final_sprite, (px + rox, py + roy))

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
    q, r = drawable["coord"]
    px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    # Adjust font size based on zoom so it stays readable
    zoom = variable_state.get("var_current_zoom", 1.0)
    base_size = drawable.get("base_size", 16)
    font_size = max(8, int(base_size * zoom))

    # Get cached font object
    font = get_font(font_size)

    # Prepare the text and color for rendering
    text = str(drawable.get("text", ""))
    color = drawable.get("color", (0, 0, 0))

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

# ──────────────────────────────────────────────────
# ⌨️ Interpreter Dispatch
# ──────────────────────────────────────────────────
# The type map that dispatches draw calls to the correct interpreter.
TYPEMAP = {
    "tile": tile_type_interpreter,
    "circle": circle_type_interpreter,
    "text": text_type_interpreter,
    "edge_line": edge_line_type_interpreter,
}


