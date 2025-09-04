
import os
import pygame
from shared_helpers import build_zoom_steps, desaturate_surface

DEBUG = True

def initialize_asset_states(persistent_state):
    """
    Calculates and stores universal, asset-related geometry and configurations
    into the persistent_state dictionary.
    """
        
    persistent_state["pers_tile_canvas_w"] = 256   # PNG width
    persistent_state["pers_tile_canvas_h"] = 384   # PNG height
    persistent_state["pers_tile_hex_w"]    = 255   # Dimensions of artwork within PNG
    persistent_state["pers_tile_hex_h"]    = 258   # Dimensions of artwork within PNG
    
    canvas_w = persistent_state["pers_tile_canvas_w"]
    canvas_h = persistent_state["pers_tile_canvas_h"]
    hex_h = persistent_state["pers_tile_hex_h"]

    # Calculate the center y-position of the hex artwork on the canvas.
    center_y = canvas_h - (hex_h / 2)
    center_x = canvas_w / 2

    # Store the calculated blit offset as the single source of truth.
    persistent_state["pers_asset_blit_offset"] = (-center_x, -center_y)
    
    if DEBUG:
        print(f"[assets] ✅ Universal asset states loaded.")


def load_tileset_assets(assets_state, persistent_state):
    """
    Loads all base terrain and river-aware sprites.
    Parses filenames to extract terrain name, variant, and river bitmasks.
    """

    # 🏞️ Define Paths & Configuration
    tile_path   = "scenes/game_scene/assets/tiles"
    tile_prefix = "hex"
    tile_canvas_w = persistent_state["pers_tile_canvas_w"]
    tile_canvas_h = persistent_state["pers_tile_canvas_h"]
    tile_hex_h   = persistent_state["pers_tile_hex_h"]
    tile_hex_w   = persistent_state["pers_tile_hex_w"]
    blit_offset = persistent_state["pers_asset_blit_offset"]

    # Pre-calculate all possible zoom levels
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    tileset = {}

    # ✍️ Load and Parse Each File
    # Iterate through all files in the tiles directory
    for filename in os.listdir(tile_path):

        # Skip any files that don't match the hex sprite naming convention
        if not filename.startswith(tile_prefix) or not filename.endswith(".png"):
            continue

        # Strip the prefix and suffix to get the base name
        full_path = os.path.join(tile_path, filename)
        base_name = filename[len(tile_prefix):-4] # e.g., Mountain00-river000010-00 or Dirt02

        # Initialize variables for parsing
        terrain_name = ""
        variant_str = ""
        river_bitmask = None
        
        # Check for the special river-aware tile format
        if "-river" in base_name:
            parts = base_name.split("-river")
            main_part = parts[0] # e.g., Mountain
            variant_part = parts[1].split("-")[1] # e.g., 00
            river_bitmask = parts[1].split("-")[0] # e.g., 000010

            # Extract the terrain name and variant from the main part
            terrain_name = ''.join([i for i in main_part if not i.isdigit()])
            variant_str = variant_part # Use the variant from the end
        else:
            # Original logic for simple tiles without a river
            terrain_name = ''.join([i for i in base_name if not i.isdigit()])
            variant_str = ''.join([i for i in base_name if i.isdigit()])

        # Validate that the terrain name and variant were parsed correctly
        if not (terrain_name and variant_str and variant_str.isdigit()):
            print(f"[tileset] ❌ Could not parse terrain/variant in filename: {filename}")
            continue
            
        # Convert the variant string to an integer
        variant = int(variant_str)

        # Load the sprite image
        sprite = pygame.image.load(full_path).convert_alpha()

        # ──────────────────────────────────────────────────
        # 🎨 Apply Tints to Specific Terrains
        # ──────────────────────────────────────────────────
        if terrain_name == "Marsh":
            TINT_COLOR = (50, 115, 130, 40) 
            tint_surface = pygame.Surface(sprite.get_size(), flags=pygame.SRCALPHA)

            # Define the vertices of the hexagonal tint overlay
            center_x = tile_canvas_w / 2
            center_y = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
            w, h = tile_hex_w, tile_hex_h
            hex_points = [
                (center_x, center_y - h / 2), (center_x + w / 2, center_y - h / 4),
                (center_x + w / 2, center_y + h / 4), (center_x, center_y + h / 2),
                (center_x - w / 2, center_y + h / 4), (center_x - w / 2, center_y - h / 4),
            ]

            # Draw the tinted hexagon and blit it onto the sprite
            pygame.draw.polygon(tint_surface, TINT_COLOR, hex_points)
            sprite.blit(tint_surface, (0, 0))

        elif terrain_name == "Scrublands":
            # This color is a sandy yellow sampled from your desert dunes tile
            TINT_COLOR = (191, 175, 129, 40)
            tint_surface = pygame.Surface(sprite.get_size(), flags=pygame.SRCALPHA)

            # Define the vertices of the hexagonal tint overlay
            center_x = tile_canvas_w / 2
            center_y = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
            w, h = tile_hex_w, tile_hex_h
            hex_points = [
                (center_x, center_y - h / 2), (center_x + w / 2, center_y - h / 4),
                (center_x + w / 2, center_y + h / 4), (center_x, center_y + h / 2),
                (center_x - w / 2, center_y + h / 4), (center_x - w / 2, center_y - h / 4),
            ]

            # Draw the tinted hexagon and blit it onto the sprite
            pygame.draw.polygon(tint_surface, TINT_COLOR, hex_points)
            sprite.blit(tint_surface, (0, 0))

        elif terrain_name == "Woodlands":
            # This color is a deep, humid green to create a more tropical feel.
            TINT_COLOR = (20, 100, 70, 40) # RGBA
            tint_surface = pygame.Surface(sprite.get_size(), flags=pygame.SRCALPHA)

            # Define the vertices of the hexagonal tint overlay
            center_x = tile_canvas_w / 2
            center_y = tile_canvas_h - tile_hex_h + (tile_hex_h / 2)
            w, h = tile_hex_w, tile_hex_h
            hex_points = [
                (center_x, center_y - h / 2), (center_x + w / 2, center_y - h / 4),
                (center_x + w / 2, center_y + h / 4), (center_x, center_y + h / 2),
                (center_x - w / 2, center_y + h / 4), (center_x - w / 2, center_y - h / 4),
            ]

            # Draw the tinted hexagon and blit it onto the sprite
            pygame.draw.polygon(tint_surface, TINT_COLOR, hex_points)
            sprite.blit(tint_surface, (0, 0))

        elif terrain_name == "Mountain":

            # Desaturate the mountain sprite by 30%
            sprite = desaturate_surface(sprite, 0.30)

        elif terrain_name == "Highlands":

            # Desaturate the highlands sprite by 50%
            sprite = desaturate_surface(sprite, 0.50)
            
        # 📏 Pre-scale for Zoom Levels
    
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()

        # Create a scaled version of the sprite for each zoom level
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # 💾 Store the Assets
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

        # Add the asset entry to the tileset dictionary
        if terrain_name not in tileset:
        #     tileset[terrain_name] = [] old code
        # tileset[terrain_name].append(entry)

            # ✨ OPTIMIZATION: Create sub-lists for base and river variants
            tileset[terrain_name] = {'base': [], 'river': []}
        
        if river_bitmask:
            tileset[terrain_name]['river'].append(entry)
        else:
            tileset[terrain_name]['base'].append(entry)

    assets_state["tileset"] = tileset
    
    # Print a summary of the loaded assets
    total_sprites = sum(len(v) for v in tileset.values())
    print(f"[assets] ✅ Loaded {total_sprites} total sprites across {len(tileset)} terrain types.")

def load_coast_assets(assets_state, persistent_state):
 # TODO: Tint shorelines based on edge-sharing terrain type.

    """
    Loads and parses the special coastline auto-tiling assets.
    """

    # 🌊 Define Paths & Configuration
    tile_path = "scenes/game_scene/assets/coast"
    tile_prefix = "hex"
    terrain_name = "Coast"
    blit_offset = persistent_state["pers_asset_blit_offset"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # # Ensure the "Coast" key exists in the tileset
    # if terrain_name not in assets_state["tileset"]:
    #     assets_state["tileset"][terrain_name] = []

    # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup in the renderer.
    # The structure will be { "bitmask1": [variantA, variantB], "bitmask2": [...] }
    assets_state["tileset"][terrain_name] = {}

    # ✍️ Loop, Parse, and Store
    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        # ✨ FIX: Exclude the more specific "RiverEnd" sprites from this general loader.
        if "LakeEnd" in filename:
            continue

        # Parse filename for bitmask and variant
        # Example: hexCoast011000-01.png -> basename = Coast011000-01
        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):] # "011000"
            variant = int(variant_part)
        except ValueError:
            print(f"[coast_loader] ❌ Could not parse coast tile: {filename}")
            continue

        # Load and pre-scale sprite
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()
        
        if not sprite:
            if DEBUG: print(f"[assets] ❌ Failed to load image: {full_path}")
            continue

        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # Store asset with parsed bitmask
        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask, # <-- Store the parsed mask
            "variant": variant,
            "filename": filename
        }
        # assets_state["tileset"][terrain_name].append(entry) old code, replaced with optimization
    
        # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup in the renderer.
        # Append this variant to the list for its specific bitmask
        if bitmask not in assets_state["tileset"][terrain_name]:
            assets_state["tileset"][terrain_name][bitmask] = []
        assets_state["tileset"][terrain_name][bitmask].append(entry)

    total_coast_sprites = sum(len(v) for v in assets_state['tileset'][terrain_name].values())
    print(f"[assets] ✅ Loaded {total_coast_sprites} coast overlay sprites.")

def load_river_assets(assets_state, persistent_state):
    """
    Loads and parses the river auto-tiling assets from the 'sprites/rivers' directory.
    """

    # Define Paths & Configuration
    tile_path = "scenes/game_scene/assets/rivers" 
    tile_prefix = "hex"
    terrain_name = "River"
    blit_offset = persistent_state["pers_asset_blit_offset"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # Ensure the "River" key exists in the tileset
    if terrain_name not in assets_state["tileset"]:
        # assets_state["tileset"][terrain_name] = [] old code

        # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup in the renderer.
        assets_state["tileset"][terrain_name] = {}

    # Loop, Parse, and Store
    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        # Parse the river filename for its bitmask and variant
        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):] # e.g., "010110"
            variant = int(variant_part)
        except ValueError:
            print(f"[river_loader] ❌ Could not parse river tile: {filename}")
            continue

        # Load and pre-scale the sprite
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()
        
        if not sprite:
            if DEBUG: print(f"[assets] ⚠️ Failed to load image: {full_path}")
            continue

        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # Store the asset
        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask, # <-- Store the parsed mask
            "variant": variant,
            "filename": filename
        }
        # assets_state["tileset"][terrain_name].append(entry) old code

        # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup in the renderer.
        if bitmask not in assets_state["tileset"][terrain_name]:
            assets_state["tileset"][terrain_name][bitmask] = []
        assets_state["tileset"][terrain_name][bitmask].append(entry)

    total_river_sprites = sum(len(v) for v in assets_state['tileset'][terrain_name].values())
    print(f"[assets] ✅ Loaded {total_river_sprites} river overlay sprites.")

def load_river_mouth_assets(assets_state, persistent_state):
    """
    Loads and parses the river mouth auto-tiling assets from a new directory.
    """

    # Define Paths & Configuration
    tile_path = "scenes/game_scene/assets/river_mouths"
    tile_prefix = "hex"
    terrain_name = "RiverMouth"
    blit_offset = persistent_state["pers_asset_blit_offset"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # if terrain_name not in assets_state["tileset"]: old code
    #     assets_state["tileset"][terrain_name] = []

    # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup.
    assets_state["tileset"][terrain_name] = {}

    # Loop, Parse, and Store
    for filename in os.listdir(tile_path):
        if not filename.startswith(f"{tile_prefix}{terrain_name}") or not filename.endswith(".png"):
            continue

        # Parse the filename for its bitmask and variant
        base_name_no_prefix = filename[len(tile_prefix):-4]
        
        try:
            mask_part, variant_part = base_name_no_prefix.split('-')
            bitmask = mask_part[len(terrain_name):]
            variant = int(variant_part)
        except ValueError:
            print(f"[river_mouth_loader] ❌ Could not parse river mouth tile: {filename}")
            continue

        # Load and pre-scale the sprite
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()
        
        if not sprite:
            if DEBUG: print(f"[assets] ⚠️ Failed to load image: {full_path}")
            continue

        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # Store the asset
        entry = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
            "terrain": terrain_name,
            "bitmask": bitmask,
            "variant": variant,
            "filename": filename
        }
        # assets_state["tileset"][terrain_name].append(entry) old code

        # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup.
        if bitmask not in assets_state["tileset"][terrain_name]:
            assets_state["tileset"][terrain_name][bitmask] = []
        assets_state["tileset"][terrain_name][bitmask].append(entry)

    total_mouth_sprites = sum(len(v) for v in assets_state['tileset'][terrain_name].values())
    print(f"[assets] ✅ Loaded {total_mouth_sprites} river mouth sprites.")

def load_river_end_assets(assets_state, persistent_state):
    """
    Loads and parses the river end/spring sprites.
    This function handles filenames with a special prefix, like 'hexRiverLakeEnd'.
    """

    # Define Paths & Configuration
    tile_path = "scenes/game_scene/assets/rivers"  # Make sure this is the correct folder name
    tile_prefix = "hex"
    terrain_name = "RiverEnd"        # The new, dedicated key for these assets

    # Re-use existing geometry and zoom data
    blit_offset = persistent_state["pers_asset_blit_offset"]
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # if terrain_name not in assets_state["tileset"]: old code
    #     assets_state["tileset"][terrain_name] = []

    # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup.
    assets_state["tileset"][terrain_name] = {}

    # Check for the existence of the directory and print a warning if not found
    if not os.path.isdir(tile_path):
        print(f"[assets] ⚠️  Directory not found, skipping: {tile_path}")
        return

    # Loop, Parse, and Store
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

        # Load and pre-scale the sprite
        full_path = os.path.join(tile_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()
        
        if not sprite:
            if DEBUG: print(f"[assets] ⚠️ Failed to load image: {full_path}")
            continue

        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6: sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                sprite_by_zoom[z] = pygame.transform.smoothscale(sprite, (tw, th))

        # Store the asset
        entry = { "sprite": sprite, "scale": sprite_by_zoom, "blit_offset": blit_offset, "terrain": terrain_name, "bitmask": bitmask, "variant": variant, "filename": filename }
        
        # assets_state["tileset"][terrain_name].append(entry) old code

        # ✨ OPTIMIZATION: Store by bitmask for O(1) lookup.
        if bitmask not in assets_state["tileset"][terrain_name]:
            assets_state["tileset"][terrain_name][bitmask] = []
        assets_state["tileset"][terrain_name][bitmask].append(entry)

    total_end_sprites = sum(len(v) for v in assets_state['tileset'][terrain_name].values())
    print(f"[assets] ✅ Loaded {total_end_sprites} river end sprites.")
