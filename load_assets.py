# load_assets.py
# A dedicated module for loading, processing, and caching all game assets.

import os
import pygame
from shared_helpers import build_zoom_steps

DEBUG = True

# [ ] TODO: run every single PNG with transperancy through this when loading it
def load_png(path, with_alpha=True):
    surf = pygame.image.load(path)
    return surf.convert_alpha() if with_alpha else surf.convert()

# ⚙️ Initialization
def load_player_assets(assets_state, persistent_state):
    """
    Loads and processes all player token sprites.
    """
    # ⚙️ Setup
    assets_path = "sprites/player_token"
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
    
    # Define how large the token should be relative to the hex tile width
    TOKEN_SCALE_FACTOR = 0.55
    tile_hex_w = persistent_state["pers_tile_hex_w"]

    player_assets = {}

    # 🔄 Load, Parse, and Scale
    for filename in os.listdir(assets_path):
        if not filename.endswith(".png"):
            continue

        # Use the filename without the extension as the unique key (e.g., "frog_1")
        species_sprite_name = filename.removesuffix('.png')
        
        full_path = os.path.join(assets_path, filename)
        sprite = pygame.image.load(full_path).convert_alpha()

        # --- Resize the base sprite to fit the hex tile ---
        # Calculate the target width based on the hex width and our scale factor.
        target_w = int(tile_hex_w * TOKEN_SCALE_FACTOR)
        
        # Calculate the new height to maintain the sprite's aspect ratio.
        original_w, original_h = sprite.get_size()
        aspect_ratio = original_h / original_w
        target_h = int(target_w * aspect_ratio)
        
        # Overwrite the original large sprite with the newly scaled one.
        sprite = pygame.transform.smoothscale(sprite, (target_w, target_h))

        # Calculate a centered blit offset based on this specific sprite's dimensions
        blit_offset = (-sprite.get_width() / 2, -sprite.get_height() / 2)

        # Pre-scale the sprite for all zoom levels (Good work here!)
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # Store the complete asset data
        player_assets[species_sprite_name] = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
        }

    assets_state["player_assets"] = player_assets
    print(f"[assets] ✅ Loaded {len(player_assets)} player token assets.")


def initialize_asset_states(persistent_state):
    """
    Calculates and stores universal, asset-related geometry and configurations
    into the persistent_state dictionary.
    """
        
    persistent_state["pers_tile_canvas_w"] = 256   # PNG width
    persistent_state["pers_tile_canvas_h"] = 384   # PNG height
    persistent_state["pers_tile_hex_w"]    = 256   # Dimensions of artwork within PNG
    persistent_state["pers_tile_hex_h"]    = 260   # Dimensions of artwork within PNG
    
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


# ──────────────────────────────────────────────────
# 🎨 Helper Functions
# ──────────────────────────────────────────────────

def desaturate_surface(surf, factor):
    """
    Returns a desaturated version of a surface.
    A factor of 0.0 means no change, 1.0 means full grayscale.
    """

    # 1. Check for valid desaturation factor and return early if no change is needed.
    if factor <= 0.0: return surf
    if factor > 1.0: factor = 1.0

    # 2. Create a grayscale version of the sprite.
    #    This uses the standard formula for luminance to preserve brightness.
    grayscale_surf = surf.copy()
    pixels = pygame.PixelArray(grayscale_surf)

    # Loop through all pixels to calculate and apply the new grayscale value
    for x in range(grayscale_surf.get_width()):
        for y in range(grayscale_surf.get_height()):
            r, g, b, a = grayscale_surf.get_at((x, y))

            # Calculate luminance for a proper grayscale conversion
            luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
            pixels[x, y] = (luminance, luminance, luminance, a)
    pixels.close()

    # 3. Blend the grayscale version over the original.
    #    The alpha is determined by the desaturation factor.
    result_surf = surf.copy()

    # Set the alpha of the grayscale surface for blending
    grayscale_surf.set_alpha(int(255 * factor))

    # Blit the semitransparent grayscale surface onto the original
    result_surf.blit(grayscale_surf, (0, 0))
    
    return result_surf

# ──────────────────────────────────────────────────
# 📦 Asset Loaders
# ──────────────────────────────────────────────────

def load_tileset_assets(assets_state, persistent_state):
    """
    Loads all base terrain and river-aware sprites.
    Parses filenames to extract terrain name, variant, and river bitmasks.
    """

    # 🏞️ Define Paths & Configuration
    tile_path   = "sprites/tiles"
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
            main_part = parts[0] # e.g., Mountain00
            river_part = parts[1].split("-")[0] # e.g., 000010
            
            # Extract the terrain name and variant from the main part
            terrain_name = ''.join([i for i in main_part if not i.isdigit()])
            variant_str = ''.join([i for i in main_part if i.isdigit()])
            river_bitmask = river_part
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
# Next review: Tint shorelines based on edge-sharing terrain type.

    """
    Loads and parses the special coastline auto-tiling assets.
    """

    # 🌊 Define Paths & Configuration
    tile_path = "sprites/coast"
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

# ──────────────────────────────────────────────────
# 💧 River & Water Overlays
# ──────────────────────────────────────────────────

def load_river_assets(assets_state, persistent_state):
    """
    Loads and parses the river auto-tiling assets from the 'sprites/rivers' directory.
    """

    # Define Paths & Configuration
    tile_path = "sprites/rivers" 
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
    tile_path = "sprites/river_mouths"
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
    tile_path = "sprites/rivers"  # Make sure this is the correct folder name
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

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────
GLOW_INNER_BRIGHTNESS = 50 # The solid brightness of the inner hex (0-255)
GLOW_FADE_PERCENT = 0.4    # The outer 40% of the hex will be a fade-out gradient

# ──────────────────────────────────────────────────
# 🎨 Asset Generation
# ──────────────────────────────────────────────────

def create_glow_mask(persistent_state, assets_state):
    """
    Creates a full set of pre-scaled hexagonal glow masks, one for each
    discrete zoom level, and caches them for high-performance rendering.
    """
    # ⚙️ Setup & Dependencies
    canvas_w = persistent_state["pers_tile_canvas_w"]
    canvas_h = persistent_state["pers_tile_canvas_h"]
    hex_w = persistent_state["pers_tile_hex_w"]
    hex_h = persistent_state["pers_tile_hex_h"]
    
    # Get all the zoom levels we need to pre-scale for.
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
    
    # Create a single, high-quality base surface that tightly fits the hexagon artwork.
    hex_surface = pygame.Surface((hex_w, hex_h), pygame.SRCALPHA)
    center_x, center_y = hex_w / 2, hex_h / 2
    
    # 📐 Define Hexagon Geometry & Draw Base Glow
    # This part is the same as before, creating the beautiful gradient glow.
    outer_points = [
        (center_x, center_y - hex_h / 2), (center_x + hex_w / 2, center_y - hex_h / 4),
        (center_x + hex_w / 2, center_y + hex_h / 4), (center_x, center_y + hex_h / 2),
        (center_x - hex_w / 2, center_y + hex_h / 4), (center_x - hex_w / 2, center_y - hex_h / 4)]
    inner_scale = 1.0 - GLOW_FADE_PERCENT
    inner_points = []
    for x, y in outer_points:
        new_x = center_x + (x - center_x) * inner_scale
        new_y = center_y + (y - center_y) * inner_scale
        inner_points.append((new_x, new_y))
    pygame.draw.polygon(hex_surface, (GLOW_INNER_BRIGHTNESS,) * 3, inner_points)
    num_gradient_steps = int((hex_h / 2) * GLOW_FADE_PERCENT)
    for i in range(6):
        p1_inner, p2_inner = inner_points[i], inner_points[(i + 1) % 6]
        p1_outer, p2_outer = outer_points[i], outer_points[(i + 1) % 6]
        for j in range(num_gradient_steps):
            t = j / num_gradient_steps
            start_x, start_y = p1_inner[0] * (1 - t) + p1_outer[0] * t, p1_inner[1] * (1 - t) + p1_outer[1] * t
            end_x, end_y = p2_inner[0] * (1 - t) + p2_outer[0] * t, p2_inner[1] * (1 - t) + p2_outer[1] * t
            brightness = int(GLOW_INNER_BRIGHTNESS * (1 - t))
            if brightness > 0:
                pygame.draw.line(hex_surface, (brightness,) * 3, (start_x, start_y), (end_x, end_y), 2)

    # 🖼️ Pre-scale and Composite For All Zoom Levels
    glow_masks_by_zoom = {}
    
    # Loop through each zoom step and create a perfectly scaled mask.
    for z in zoom_steps:
        scaled_canvas_w = max(1, int(canvas_w * z))
        scaled_canvas_h = max(1, int(canvas_h * z))
        
        # Scale the original hex artwork to the target zoom size.
        scaled_hex_w = max(1, int(hex_w * z))
        scaled_hex_h = max(1, int(hex_h * z))
        scaled_hex_surface = pygame.transform.smoothscale(hex_surface, (scaled_hex_w, scaled_hex_h))
        
        # Create the final canvas for this zoom level.
        final_surface_for_zoom = pygame.Surface((scaled_canvas_w, scaled_canvas_h), pygame.SRCALPHA)
        
        # Calculate the correct position to blit the scaled artwork onto the scaled canvas.
        offset_x, offset_y = persistent_state["pers_asset_blit_offset"]
        blit_pos_x = (scaled_canvas_w / 2) + (offset_x * z)
        blit_pos_y = (-offset_y * z) - (scaled_hex_h / 2)
        
        # Blit our generated glow onto the final canvas for this zoom level.
        final_surface_for_zoom.blit(scaled_hex_surface, (blit_pos_x, blit_pos_y))
        
        # Store the finished, pre-scaled mask in our dictionary.
        glow_masks_by_zoom[z] = final_surface_for_zoom
            
    print(f"[assets] ✅ Pre-scaled hexagonal glow masks created for all zoom levels.")
    assets_state["glow_masks_by_zoom"] = glow_masks_by_zoom



def create_tinted_glow_masks(persistent_state, assets_state):
    """
    Creates a set of pre-scaled, tinted hexagonal glow masks for all movement and hazard types.
    Uses different border styles for movement vs. hazards.
    """
    # ──────────────────────────────────────────────────
    # 🎨 Define All Colors and Styles
    # ──────────────────────────────────────────────────
    # Combine all colors into one dictionary
    colors_to_generate = {
        "good": (40, 180, 70),
        "medium": (255, 215, 0),
        "bad": (220, 20, 60),
        "hazard": (150, 0, 210), # Deep Violet
    }
    
    # Style 1: Primary border for standard movement (Outer Band)
    PRIMARY_BORDER_STOPS = {
        "outer_edge": 1.1,
        "solid_band_start": 0.93,
        "solid_band_end": 0.87,
        "inner_fade_end": 0.69,
    }

    # Style 2: Secondary border for hazards (Inner Ring)
    SECONDARY_BORDER_STOPS = {
        "outer_edge": 0.80,
        "solid_band_start": 0.77,
        "solid_band_end": 0.70,
        "inner_fade_end": 0.65,
    }
    
    # The maximum alpha for the solid part of the glow.
    MAX_ALPHA = 170 

    assets_state["tinted_glows"] = {}

    # ──────────────────────────────────────────────────
    # ✨ Generate a Mask for Each Color
    # ──────────────────────────────────────────────────
    for color_name, color_rgb in colors_to_generate.items():
        
        # Get base dimensions from persistent state.
        canvas_w = persistent_state["pers_tile_canvas_w"]
        canvas_h = persistent_state["pers_tile_canvas_h"]
        hex_w = persistent_state["pers_tile_hex_w"]
        hex_h = persistent_state["pers_tile_hex_h"]
        zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
        
        # Create the high-quality surface to draw our master glow on.
        hex_surface = pygame.Surface((hex_w, hex_h), pygame.SRCALPHA)
        center_x, center_y = hex_w / 2, hex_h / 2

        # 📐 Define Concentric Hexagon Points
        # Helper function to generate the points for a hexagon at a given scale.
        def get_hex_points(scale):
            # The base points for a full-sized (scale=1.0) hexagon.
            base_points = [
                (center_x, center_y - hex_h / 2), (center_x + hex_w / 2, center_y - hex_h / 4),
                (center_x + hex_w / 2, center_y + hex_h / 4), (center_x, center_y + hex_h / 2),
                (center_x - hex_w / 2, center_y + hex_h / 4), (center_x - hex_w / 2, center_y - hex_h / 4)
            ]
            if abs(scale - 1.0) < 1e-6:
                return base_points
            # For other scales, interpolate each point towards the center.
            return [(center_x + (px - center_x) * scale, center_y + (py - center_y) * scale) for px, py in base_points]

        if color_name == "hazard":
            border_stops_to_use = SECONDARY_BORDER_STOPS
        else:
            border_stops_to_use = PRIMARY_BORDER_STOPS

        # Generate the vertex lists for each of our defined border stops.
        points_outer_edge = get_hex_points(border_stops_to_use["outer_edge"])
        points_solid_start = get_hex_points(border_stops_to_use["solid_band_start"])
        points_solid_end = get_hex_points(border_stops_to_use["solid_band_end"])
        points_inner_fade_end = get_hex_points(border_stops_to_use["inner_fade_end"])
        
        # ✍️ Draw the Gradient Bands
        # This is where the magic happens. We draw thin, interpolated polygons.
        # The number of steps determines how smooth the gradient is.
        GRADIENT_STEPS = 15 

        # 1. Draw the outer fade-in (from transparent to solid).
        for i in range(GRADIENT_STEPS):
            t = i / (GRADIENT_STEPS - 1) # Interpolation factor (0.0 to 1.0)
            alpha = int(MAX_ALPHA * t)   # Alpha goes from 0 to MAX_ALPHA
            
            # Create the polygon for this step by interpolating between the two boundaries.
            poly_points = []
            for j in range(6):
                x = points_outer_edge[j][0] * (1 - t) + points_solid_start[j][0] * t
                y = points_outer_edge[j][1] * (1 - t) + points_solid_start[j][1] * t
                poly_points.append((x, y))
            pygame.draw.polygon(hex_surface, (*color_rgb, alpha), poly_points)

        # 2. Draw the solid color band.
        pygame.draw.polygon(hex_surface, (*color_rgb, MAX_ALPHA), points_solid_start)

        # 3. Draw the inner fade-out (from solid to transparent).
        for i in range(GRADIENT_STEPS):
            t = i / (GRADIENT_STEPS - 1)
            alpha = int(MAX_ALPHA * (1 - t)) # Alpha goes from MAX_ALPHA down to 0

            poly_points = []
            for j in range(6):
                x = points_solid_end[j][0] * (1 - t) + points_inner_fade_end[j][0] * t
                y = points_solid_end[j][1] * (1 - t) + points_inner_fade_end[j][1] * t
                poly_points.append((x, y))
            pygame.draw.polygon(hex_surface, (*color_rgb, alpha), poly_points)

        # 🖼️ Pre-scale and Composite For All Zoom Levels
        # This part is identical to your original function, ensuring performance.
        glow_masks_by_zoom = {}
        for z in zoom_steps:
            scaled_canvas_w = max(1, int(canvas_w * z))
            scaled_canvas_h = max(1, int(canvas_h * z))
            scaled_hex_w = max(1, int(hex_w * z))
            scaled_hex_h = max(1, int(hex_h * z))
            scaled_hex_surface = pygame.transform.smoothscale(hex_surface, (scaled_hex_w, scaled_hex_h))
            final_surface_for_zoom = pygame.Surface((scaled_canvas_w, scaled_canvas_h), pygame.SRCALPHA)
            offset_x, offset_y = persistent_state["pers_asset_blit_offset"]
            blit_pos_x = (scaled_canvas_w / 2) + (offset_x * z)
            blit_pos_y = (-offset_y * z) - (scaled_hex_h / 2)
            final_surface_for_zoom.blit(scaled_hex_surface, (blit_pos_x, blit_pos_y))
            glow_masks_by_zoom[z] = final_surface_for_zoom
                
        assets_state["tinted_glows"][color_name] = glow_masks_by_zoom
            
    print(f"[assets] ✅ Pre-scaled tinted glow masks created for {list(colors_to_generate.keys())}.")


# ──────────────────────────────────────────────────
# 🎨 UI Asset Constants
# ──────────────────────────────────────────────────
# Constants for creating the grayscale background texture
GRAYSCALE_TEXTURE_SIZE = (196, 196) # The scale of the repeating background pattern

# ──────────────────────────────────────────────────
# 🖼️ UI Asset Creation Pipeline
# ──────────────────────────────────────────────────

# Replace your old load_ui_texture function with this new one:
def load_ui_textures(assets_state, ui_path):
    """Loads all full-resolution source textures for the UI."""
    
    # A dictionary mapping texture filenames to their asset keys
    textures_to_load = {
        "ZM_Basecolor.png": "bark_full_res",
        "STZ_basecolor.png": "stone_full_res"
    }

    for filename, key in textures_to_load.items():
        source_file = os.path.join(ui_path, filename)
        try:
            # Load the texture and store it using its new key
            full_res_texture = pygame.image.load(source_file).convert_alpha()
            assets_state["ui_assets"][key] = full_res_texture
            print(f"[assets] ✅ Loaded UI texture '{filename}' as '{key}'.")
        except pygame.error as e:
            if DEBUG: print(f"[assets] ❌ Error loading UI texture '{filename}': {e}")

def create_grayscale_ui_watermarks(assets_state):
    """Creates scaled, desaturated watermark textures for UI backgrounds."""
    
    # A dictionary mapping the source texture key to the desired output key
    textures_to_process = {
        "bark_full_res": "bark_background_watermark",
        "stone_full_res": "stone_background_watermark"
    }

    # Loop through and process each texture
    for source_key, output_key in textures_to_process.items():
        source_texture = assets_state["ui_assets"].get(source_key)
        if not source_texture:
            if DEBUG: print(f"[assets] ⚠️  Source texture '{source_key}' not found for watermark creation.")
            continue

        # Scale the texture down to the desired repeating size
        scaled_texture = pygame.transform.smoothscale(source_texture, GRAYSCALE_TEXTURE_SIZE)
        
        # Desaturate it to create the watermark effect
        grayscale_texture = desaturate_surface(scaled_texture, 1.0)
        
        # Store the result using its new key
        assets_state["ui_assets"][output_key] = grayscale_texture
        print(f"[assets] ✅ Created '{output_key}'.")

# Replace your old create_ui_border_assets function with this new one:
def create_ui_border_assets(assets_state):
    """
    Creates 9-slice border pieces for multiple UI styles (e.g., bark, stone).
    Each style can have its own source texture, border width, and processing.
    """
    
    # A list defining all the border styles we want to generate
    border_styles = [
        {
            "source_key": "bark_full_res",      # Which texture to use
            "output_key": "bark_border_pieces",  # What to name the final asset group
            "border_width": 12,                  # The thickness of this border style
            "desaturation": 0.0                  # How much to desaturate (0.0 = none)
        },
        {
            "source_key": "stone_full_res",
            "output_key": "stone_border_pieces",
            "border_width": 6,                 
            "desaturation": 0.6                  # Apply a slight desaturation for a grayer look
        }
    ]

    # Loop through and generate the assets for each style
    for style in border_styles:
        source_texture = assets_state["ui_assets"].get(style["source_key"])
        if not source_texture:
            if DEBUG: print(f"[assets] ⚠️ Source texture '{style['source_key']}' not found for border creation.")
            continue

        processed_texture = source_texture
        # Apply desaturation if specified
        if style["desaturation"] > 0.0:
            processed_texture = desaturate_surface(source_texture, style["desaturation"])

        # Create the master tile to be sliced
        border_width = style["border_width"]
        master_tile_size = (border_width * 3, border_width * 3)
        master_tile = pygame.transform.smoothscale(processed_texture, master_tile_size)
        
        # Slice the master tile into 9 pieces
        border_pieces = {}
        for row in range(3):
            for col in range(3):
                piece_num = str(row * 3 + col + 1)
                slice_rect = pygame.Rect(col * border_width, row * border_width, border_width, border_width)
                border_pieces[piece_num] = master_tile.subsurface(slice_rect).copy()

        # Save the finished set of pieces using the specified output key
        assets_state["ui_assets"][style["output_key"]] = border_pieces
        print(f"[assets] ✅ Created 9 UI border pieces for style '{style['output_key']}'.")

# ──────────────────────────────────────────────────
# 🔠 Font Cache & Management
# ──────────────────────────────────────────────────
# A module-level dictionary to act as a singleton cache for all font objects.
_FONT_CACHE = {}
_DEFAULT_FONT_KEY = "regular_medium"


def initialize_font_cache():
    """Loads all predefined fonts into the central cache. Call this once on startup."""
    font_configs = {
        # ✨ FIX: Point back to the static fonts that Pygame can render correctly.
        "styles": {
            "regular": "sprites/fonts/static/NotoSans-Regular.ttf",
            "bold": "sprites/fonts/static/NotoSans-Bold.ttf"
        },
        "sizes": {"small": 10, "medium": 14, "large": 18},
    }
    for style_name, font_path in font_configs["styles"].items():
        for size_name, size_pixels in font_configs["sizes"].items():
            font_key = f"{style_name}_{size_name}"
            try:
                _FONT_CACHE[font_key] = pygame.font.Font(font_path, size_pixels)
            except pygame.error:
                if DEBUG: print(f"[assets] ❌ FONT ERROR: Could not load '{font_path}'. Key '{font_key}' is unavailable.")
    if DEBUG: print(f"[assets] ✅ {len(_FONT_CACHE)} fonts loaded into cache.")

def get_font(key="regular_medium"):
    """Retrieves a font from the cache, falling back to the default if not found."""
    font = _FONT_CACHE.get(key)
    if not font and DEBUG: print(f"[assets] ⚠️ Font key '{key}' not found. Falling back to default.")
    return font or _FONT_CACHE.get(_DEFAULT_FONT_KEY)

# Now, update the main orchestrator to call this new function
def load_all_ui_assets(assets_state):
    """Orchestrator to run the entire UI asset creation pipeline."""
    assets_state["ui_assets"] = {}
    ui_path = "sprites/ui"
    
    load_ui_textures(assets_state, ui_path)
    create_grayscale_ui_watermarks(assets_state)
    create_ui_border_assets(assets_state)
