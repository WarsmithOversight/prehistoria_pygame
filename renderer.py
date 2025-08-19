# renderer.py
from shared_helpers import hex_to_pixel, snap_zoom_to_nearest_step
import pygame

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
FONT_CACHE = {}

# In renderer.py

def initialize_render_states(persistent_state):
    """
    Initializes and stores all render-specific configurations,
    including the centralized z-order formulas.
    """
    # 1. Define the row multiplier as a constant.
    Z_ROW_MULTIPLIER = 0.001
    
    # 2. Create a reusable helper function for the vertical position offset.
    vert_offset = lambda r: r * Z_ROW_MULTIPLIER

    # 3. Use the helper in the main formulas dictionary.
    persistent_state["pers_z_formulas"] = {
        # --- Base Terrain ---
        # The formulas are now much cleaner and easier to read.
        "tile":          lambda r: 1.0 + vert_offset(r),

        # --- Debug Overlays ---
        "debug_icon":    lambda r: 1.0 + vert_offset(r) + 0.0003,
        "terrain_tag":   lambda r: 1.0 + vert_offset(r) + 0.0004,
        "coordinate":    lambda r: 1.0 + vert_offset(r) + 0.0005,
        "continent_spine": lambda r: 1.0 + vert_offset(r) + 0.0006,
        
        # --- Static Overlays ---
        "region_border": lambda: 1.5,
    }
    
    print("✅ Render states and z-formulas initialized.")

def get_font(size):
    """Return a cached SysFont of the given size."""
    font = FONT_CACHE.get(size)
    if font is None:
        font = pygame.font.SysFont("Arial", size)
        FONT_CACHE[size] = font
    return font

def render_giant_z_pot(screen, tiledata, notebook, persistent_state, assets_state, variable_state):
    """
    Collects every entry from both tiledata and notebook,
    sorts them all by 'z', and steps through them in order.
    If any entry is missing 'z', skips it and prints a debug message (if DEBUG).
    """

    # Step 1: Combine all entries
    draw_pot = list(tiledata.values()) + list(notebook.values())

    # Step 2: Filter out entries missing 'z', count skips
    to_draw = []
    skipped = 0
    for entry in draw_pot:
        if "z" in entry:
            to_draw.append(entry)
        else:
            skipped += 1

    # Step 3: Debug print if needed
    if DEBUG and skipped:
        print(f"[renderer] {skipped} drawables skipped (missing 'z' value)")

    # Step 4: Sort by z
    to_draw.sort(key=lambda d: d.get("z", 0))

    # Step 5: Render in z order
    for drawable in to_draw:
        typ = drawable.get("type")
        interpreter = TYPEMAP.get(typ)
        if interpreter:
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
    q, r = drawable["coord"]
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

    import hashlib
    seed = f"{q},{r},{terrain}".encode()
    h = int.from_bytes(hashlib.md5(seed).digest(), "big")
    stable_variant_index = h % len(non_river_variants)
    
    entry = None


    if terrain == "Mountain" and "river_data" in drawable:
        drawable['suppress_river_overlay'] = True
        river_bitmask = drawable["river_data"]["bitmask"]

        # ✅ NEW LOGIC: Find ANY mountain sprite with the correct bitmask, regardless of variant.
        matching_river_mountains = [
            ms for ms in variants if ms.get("river_bitmask") == river_bitmask
        ]

        if matching_river_mountains:
            # We found one or more sprites for this river direction.
            # Pick one consistently based on the tile's hash to prevent flickering.
            entry = matching_river_mountains[h % len(matching_river_mountains)]

    # --- FALLBACK LOGIC ---
    if entry is None:
        # If no special sprite was found, find a standard base tile.
        non_river_variants = [v for v in variants if "river_bitmask" not in v]
        if non_river_variants:
            stable_variant_index = h % len(non_river_variants)
            entry = non_river_variants[stable_variant_index]
        else:
            entry = variants[h % len(variants)] # Failsafe

    if not entry:
        if DEBUG: print(f"[renderer] ❌ Could not resolve a sprite for {terrain} at ({q},{r}).")
        return

    current_zoom = variable_state.get("var_current_zoom", 1.0)
    is_zooming   = bool(variable_state.get("var_is_zooming"))
    snapped_zoom = snap_zoom_to_nearest_step(persistent_state, variable_state) if not is_zooming else None

    px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    off_x, off_y = entry["blit_offset"]
    offset_scale = current_zoom if is_zooming else snapped_zoom
    ox = int(off_x * offset_scale)
    oy = int(off_y * offset_scale)

    if is_zooming:
        spr = entry["sprite"]
        tw = max(1, int(spr.get_width() * current_zoom))
        th = max(1, int(spr.get_height() * current_zoom))
        final = pygame.transform.scale(spr, (tw, th))
    else:
        sprite_map = entry.get("scale") or {1.0: entry["sprite"]}
        final = sprite_map.get(snapped_zoom) or sprite_map.get(1.0)
        if final is None:
            if DEBUG: print(f"[renderer] ❌ Missing sprite at {snapped_zoom:.2f} and 1.0 for '{terrain}'.")
            return

    # Blit the selected Base Terrain (either special or fallback)
    screen.blit(final, (px + ox, py + oy))

    if "has_shoreline" in drawable:
        has_shoreline = drawable["has_shoreline"]
        coast_sprites = assets_state["tileset"].get("Coast", [])
        
        matching_variants = [s for s in coast_sprites if s.get("bitmask") == has_shoreline]

        if matching_variants:
            import hashlib
            seed = f"{q},{r},Coast,{has_shoreline}".encode()
            h = int.from_bytes(hashlib.md5(seed).digest(), "big")
            coast_entry = matching_variants[h % len(matching_variants)]

            coast_sprite_map = coast_entry.get("scale") or {1.0: coast_entry["sprite"]}
            final_coast_sprite = coast_sprite_map.get(snapped_zoom) or coast_sprite_map.get(1.0)
            
            coast_off_x, coast_off_y = coast_entry["blit_offset"]
            cox = int(coast_off_x * offset_scale)
            coy = int(coast_off_y * offset_scale)
            
            if final_coast_sprite:
                screen.blit(final_coast_sprite, (px + cox, py + coy))

    # 🏞️ Blit River, Mouth, and Spring Overlays
    if "river_data" in drawable and not drawable.get('suppress_river_overlay'):
        river_bitmask_str = drawable["river_data"]["bitmask"]
        
        # --- Determine which kind of river piece to draw ---
        is_source = drawable["river_data"].get("is_river_source", False)
        is_mountain = drawable.get("is_mountain", False)
        connection_count = river_bitmask_str.count('1')

        # A tile is a "spring" (RiverEnd) only if it's a source AND has just one connection.
        if is_source and not is_mountain and connection_count <= 1:
            sprite_key = "RiverEnd"
        else:
            # Otherwise (if it has multiple connections), treat it as a regular river or mouth.
            is_ocean_endpoint = drawable.get("is_ocean", False)
            is_lowland_endpoint = drawable.get("lowlands", False)
            is_lake_endpoint = drawable.get("is_lake", False)
            is_endpoint = is_ocean_endpoint or is_lowland_endpoint or is_lake_endpoint
            
            sprite_key = "RiverMouth" if is_endpoint else "River"

        # --- Blitting Logic ---
        if sprite_key == "RiverMouth":
            # Mouths use special decomposition logic to handle multiple inflows
            for i, bit in enumerate(river_bitmask_str):
                if bit == '1':
                    simple_mask_list = ['0'] * 6
                    simple_mask_list[i] = '1'
                    simple_mask = "".join(simple_mask_list)
                    
                    mouth_sprites = assets_state["tileset"].get(sprite_key, [])
                    matching_variants = [s for s in mouth_sprites if s.get("bitmask") == simple_mask]

                    if matching_variants:
                        import hashlib
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
                import hashlib
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

    if "pixel_coord" in drawable:
        px, py = drawable["pixel_coord"]
    else:
        q, r = drawable["coord"]
        px, py = hex_to_pixel(q, r, persistent_state, variable_state)

    zoom = variable_state.get("var_current_zoom", 1.0)
    color = drawable.get("color", (0, 0, 0))
    radius = 0

    if "matches_line_thickness" in drawable:
        base_thickness = drawable["matches_line_thickness"]
        final_thickness = max(1, int(base_thickness * zoom))
        radius = final_thickness // 2
    else:
        base_radius = drawable.get("base_radius", 30)
        radius = max(1, int(base_radius * zoom))

    radius = max(1, radius)
    
    # ✅ NEW: Check for a "width" property to draw a hollow circle
    width = drawable.get("width", 0) # Default to 0 (filled)
    final_width = max(1, int(width * zoom)) if width > 0 else 0

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

    # Prepare text and color
    text = str(drawable.get("text", ""))
    color = drawable.get("color", (0, 0, 0))

    # Render text
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(px, py))
    screen.blit(surf, rect.topleft)


def edge_line_type_interpreter(screen, drawable, persistent_state, assets_state, variable_state):
    """
    Draws a zoom-safe line between p1 and p2 from drawable.
    """
    p1 = drawable["p1"]
    p2 = drawable["p2"]
    color = drawable.get("color", (0, 0, 0))
    zoom = variable_state.get("var_current_zoom", 1.0)
    thickness = max(1, int(drawable.get("thickness", 2) * zoom))

    # Apply zoom scaling (p1/p2 already scaled in hex_geometry, so just cast to int)
    pygame.draw.line(screen, color, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), thickness)

# ──────────────────────────────────────────────────
# ⌨️ Interpreter Dispatch
# ──────────────────────────────────────────────────

TYPEMAP = {
    "tile": tile_type_interpreter,
    "circle": circle_type_interpreter,
    "text": text_type_interpreter,
    "edge_line": edge_line_type_interpreter,
}


