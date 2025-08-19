import os, pygame
from shared_helpers import build_zoom_steps

# def initialize_various_assets_states(assets_state):

def desaturate_surface(surf, factor):
    """
    Returns a desaturated version of a surface.
    A factor of 0.0 means no change, 1.0 means full grayscale.
    """
    if factor <= 0.0: return surf
    if factor > 1.0: factor = 1.0

    # 1. Create a grayscale version of the sprite.
    #    This uses the standard formula for luminance to preserve brightness.
    grayscale_surf = surf.copy()
    pixels = pygame.PixelArray(grayscale_surf)
    for x in range(grayscale_surf.get_width()):
        for y in range(grayscale_surf.get_height()):
            r, g, b, a = grayscale_surf.get_at((x, y))
            luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
            pixels[x, y] = (luminance, luminance, luminance, a)
    pixels.close()

    # 2. Blend the grayscale version over the original.
    #    The alpha is determined by the desaturation factor.
    result_surf = surf.copy()
    grayscale_surf.set_alpha(int(255 * factor))
    result_surf.blit(grayscale_surf, (0, 0))
    
    return result_surf

def load_tileset_assets(assets_state, persistent_state):
    tile_path   = "sprites/tiles"
    tile_prefix = "hex"
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h   = persistent_state["pers_tile_hex_h"]
    tile_hex_w   = persistent_state["pers_tile_hex_h"]

    persistent_state.setdefault("pers_zoom_config", {
        "min_zoom": 0.20, "max_zoom": 1.00, "zoom_interval": 0.05
    })
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    tileset = {}

    for filename in os.listdir(tile_path):
        if not filename.startswith(tile_prefix) or not filename.endswith(".png"):
            continue

        full_path = os.path.join(tile_path, filename)
        base_name = filename[len(tile_prefix):-4] # e.g., Mountain00-river000010-00 or Dirt02

        terrain_name = ""
        variant_str = ""
        river_bitmask = None
        
        # Check for the special river-aware tile format
        if "-river" in base_name:
            parts = base_name.split("-river")
            main_part = parts[0] # e.g., Mountain00
            river_part = parts[1].split("-")[0] # e.g., 000010
            
            terrain_name = ''.join([i for i in main_part if not i.isdigit()])
            variant_str = ''.join([i for i in main_part if i.isdigit()])
            river_bitmask = river_part
        else:
            # Original logic for simple tiles
            terrain_name = ''.join([i for i in base_name if not i.isdigit()])
            variant_str = ''.join([i for i in base_name if i.isdigit()])

        if not (terrain_name and variant_str and variant_str.isdigit()):
            print(f"[tileset] ❌ Could not parse terrain/variant in filename: {filename}")
            continue
            
        variant = int(variant_str)
        sprite = pygame.image.load(full_path).convert_alpha()

        # ──────────────────────────────────────────────────
        # 🎨 Apply Tints to Specific Terrains
        # ──────────────────────────────────────────────────
        if terrain_name == "Marsh":
            TINT_COLOR = (50, 115, 130, 40) 
            tint_surface = pygame.Surface(sprite.get_size(), flags=pygame.SRCALPHA)
            center_x = tile_canvas_w / 2
            center_y = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
            w, h = tile_hex_w, tile_hex_h
            hex_points = [
                (center_x, center_y - h / 2), (center_x + w / 2, center_y - h / 4),
                (center_x + w / 2, center_y + h / 4), (center_x, center_y + h / 2),
                (center_x - w / 2, center_y + h / 4), (center_x - w / 2, center_y - h / 4),
            ]
            pygame.draw.polygon(tint_surface, TINT_COLOR, hex_points)
            sprite.blit(tint_surface, (0, 0))
            print(f"[assets] 🎨 Applied a hex-masked blue tint to '{filename}'.")

        elif terrain_name == "Scrublands":
            # This color is a sandy yellow sampled from your desert dunes tile
            TINT_COLOR = (191, 175, 129, 40)
            tint_surface = pygame.Surface(sprite.get_size(), flags=pygame.SRCALPHA)
            center_x = tile_canvas_w / 2
            center_y = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
            w, h = tile_hex_w, tile_hex_h
            hex_points = [
                (center_x, center_y - h / 2), (center_x + w / 2, center_y - h / 4),
                (center_x + w / 2, center_y + h / 4), (center_x, center_y + h / 2),
                (center_x - w / 2, center_y + h / 4), (center_x - w / 2, center_y - h / 4),
            ]
            pygame.draw.polygon(tint_surface, TINT_COLOR, hex_points)
            sprite.blit(tint_surface, (0, 0))
            print(f"[assets] 🎨 Applied a hex-masked sand tint to '{filename}'.")

        elif terrain_name == "Mountain":
            sprite = desaturate_surface(sprite, 0.30)
            print(f"[assets] 🎨 Desaturated '{filename}'.")

        elif terrain_name == "Highlands":
            sprite = desaturate_surface(sprite, 0.50)
            print(f"[assets] 🎨 Desaturated '{filename}'.")
            
        center_from_top = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
        blit_offset = (-tile_canvas_w / 2, -center_from_top)
        
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "variant": variant,
            "filename": filename
        }
        
        # Add the river bitmask if it was parsed
        if river_bitmask:
            entry["river_bitmask"] = river_bitmask

        if terrain_name not in tileset:
            tileset[terrain_name] = []
        tileset[terrain_name].append(entry)

    assets_state["tileset"] = tileset
    
    # Corrected print summary to avoid errors if only one terrain type is loaded
    total_sprites = sum(len(v) for v in tileset.values())
    print(f"[assets] ✅ Loaded {total_sprites} total sprites across {len(tileset)} terrain types.")

def load_coast_assets(assets_state, persistent_state):
    """
    Loads and parses the special coastline auto-tiling assets.
    - Looks in a specific 'sprites/coast' directory.
    - Parses filenames like 'hexCoast011000-01.png'.
    - Stores the bitmask with the sprite data.
    """
    tile_path = "sprites/coast" # <-- Specific directory
    tile_prefix = "hex"
    terrain_name = "Coast"
    
    # Re-use existing geometry and zoom data
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # Ensure the "Coast" key exists in the tileset
    if terrain_name not in assets_state["tileset"]:
        assets_state["tileset"][terrain_name] = []

    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        # --- Specific Parser for Coastlines ---
        # Example: hexCoast011000-01.png -> basename = Coast011000-01
        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):] # "011000"
            variant = int(variant_part)
        except ValueError:
            print(f"[coast_loader] ❌ Could not parse coast tile: {filename}")
            continue

        # --- (The rest is the same as the original loader) ---
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()

        center_from_top = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
        blit_offset = (-tile_canvas_w / 2, -center_from_top)
        
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask, # <-- Store the parsed mask
            "variant": variant,
            "filename": filename
        }
        assets_state["tileset"][terrain_name].append(entry)

    print(f"[assets] ✅ Loaded {len(assets_state['tileset'][terrain_name])} coast overlay sprites.")

# In load_assets.py

def load_river_assets(assets_state, persistent_state):
    """
    Loads and parses the river auto-tiling assets.
    - Looks in 'sprites/rivers'.
    - Parses filenames like 'hexRiver011000-00.png'.
    """
    tile_path = "sprites/rivers"  # <-- Directory for river sprites
    tile_prefix = "hex"
    terrain_name = "River"        # <-- Key for the assets dictionary

    # Re-use existing geometry and zoom data
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # Ensure the "River" key exists in the tileset
    if terrain_name not in assets_state["tileset"]:
        assets_state["tileset"][terrain_name] = []

    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        # --- Parser for River Filenames ---
        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):] # e.g., "010110"
            variant = int(variant_part)
        except ValueError:
            print(f"[river_loader] ❌ Could not parse river tile: {filename}")
            continue

        # --- (The rest is identical to the other loaders) ---
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()

        center_from_top = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
        blit_offset = (-tile_canvas_w / 2, -center_from_top)
        
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask, # <-- Store the parsed mask
            "variant": variant,
            "filename": filename
        }
        assets_state["tileset"][terrain_name].append(entry)

    print(f"[assets] ✅ Loaded {len(assets_state['tileset'][terrain_name])} river overlay sprites.")

def load_river_mouth_assets(assets_state, persistent_state):
    """
    Loads and parses the river mouth auto-tiling assets.
    - Looks in 'sprites/river_mouths'.
    - Parses filenames like 'hexRiverMouth011000-00.png'.
    """
    tile_path = "sprites/river_mouths" # <-- New directory
    tile_prefix = "hex"
    terrain_name = "RiverMouth"        # <-- New key for the assets dictionary

    # Re-use existing geometry and zoom data
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    if terrain_name not in assets_state["tileset"]:
        assets_state["tileset"][terrain_name] = []

    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):]
            variant = int(variant_part)
        except ValueError:
            print(f"[river_mouth_loader] ❌ Could not parse river mouth tile: {filename}")
            continue

        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()

        center_from_top = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
        blit_offset = (-tile_canvas_w / 2, -center_from_top)
        
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask,
            "variant": variant,
            "filename": filename
        }
        assets_state["tileset"][terrain_name].append(entry)

    print(f"[assets] ✅ Loaded {len(assets_state['tileset'].get(terrain_name, []))} river mouth sprites.")

def load_river_end_assets(assets_state, persistent_state):
    """Loads and parses the river end/spring sprites."""
    tile_path = "sprites/rivers"  # Make sure this is the correct folder name
    tile_prefix = "hex"
    terrain_name = "RiverEnd"        # The new, dedicated key for these assets

    # --- (The rest of the function is identical to load_river_mouth_assets) ---
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    if terrain_name not in assets_state["tileset"]:
        assets_state["tileset"][terrain_name] = []

    if not os.path.isdir(tile_path):
        print(f"[assets] ⚠️  Directory not found, skipping: {tile_path}")
        return

    for filename in os.listdir(tile_path):
        # We need to parse "hexRiverLakeEnd..." filenames but store them as "RiverEnd"
        if not filename.startswith("hexRiverLakeEnd") or not filename.endswith(".png"):
            continue

        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            # Manually specify the prefix to strip from the filename
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len("RiverLakeEnd"):] 
            variant = int(variant_part)
        except ValueError:
            print(f"[river_end_loader] ❌ Could not parse tile: {filename}")
            continue

        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()

        center_from_top = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
        blit_offset = (-tile_canvas_w / 2, -center_from_top)
        
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6: sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                sprite_by_zoom[z] = pygame.transform.smoothscale(sprite, (tw, th))

        entry = { "sprite": sprite, "scale": sprite_by_zoom, "blit_offset": blit_offset, "terrain": terrain_name, "bitmask": bitmask, "variant": variant, "filename": filename }
        assets_state["tileset"][terrain_name].append(entry)

    print(f"[assets] ✅ Loaded {len(assets_state['tileset'].get(terrain_name, []))} river end sprites.")