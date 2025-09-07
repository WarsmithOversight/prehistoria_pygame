# scenes/game_scene/load_assets.py
import os
import pygame
from shared_helpers import build_zoom_steps

DEBUG = True

def load_player_assets(assets_state, persistent_state):
    """
    Loads and processes a specific list of player token sprites.
    """

    TOKENS_TO_LOAD = [
        "frog_01.png",
        "bird_01.png",
        # Add more token filenames here as they are created.
    ]

    assets_path = "scenes/game_scene/assets/artwork"
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
    
    # Define how large the token should be relative to the hex tile width.
    TOKEN_SCALE_FACTOR = 0.55
    tile_hex_w = persistent_state["pers_tile_hex_w"]

    player_assets = {}

    # 🔄 Load, Parse, and Scale each token from the list
    for filename in TOKENS_TO_LOAD:
        
        #  PATH Create the full path to the asset file.
        full_path = os.path.join(assets_path, filename)
        
        # ROBUSTNESS Use a try-except block to handle missing files gracefully.
        try:
            sprite = pygame.image.load(full_path).convert_alpha()
        except pygame.error as e:
            print(f"[assets] ⚠️ Could not load player token '{filename}': {e}")
            continue # Skip to the next token in the list

        # 🔑 Use the filename without the extension as the unique key (e.g., "frog_1").
        species_sprite_name = filename.removesuffix('.png')
        
        # 📏 Resize the base sprite to fit the hex tile.
        # Calculate the target width based on the hex width and our scale factor.
        target_w = int(tile_hex_w * TOKEN_SCALE_FACTOR)
        
        # Calculate the new height to maintain the sprite's aspect ratio.
        original_w, original_h = sprite.get_size()
        aspect_ratio = original_h / original_w
        target_h = int(target_w * aspect_ratio)
        
        # Overwrite the original large sprite with the newly scaled one.
        sprite = pygame.transform.smoothscale(sprite, (target_w, target_h))

        # 📍 Calculate a centered blit offset based on this specific sprite's dimensions.
        blit_offset = (-sprite.get_width() / 2, -sprite.get_height() / 2)

        # 🖼️ Pre-scale the sprite for all zoom levels.
        sprite_by_zoom = {}
        ow, oh = sprite.get_size()
        for z in zoom_steps:
            if abs(z - 1.0) < 1e-6:
                sprite_by_zoom[z] = sprite
            else:
                tw, th = max(1, int(ow * z)), max(1, int(oh * z))
                scaled = pygame.transform.smoothscale(sprite, (tw, th))
                sprite_by_zoom[z] = scaled

        # 💾 Store the complete asset data.
        player_assets[species_sprite_name] = {
            "sprite": sprite,
            "scale": sprite_by_zoom,
            "blit_offset": blit_offset,
        }

    assets_state["player_assets"] = player_assets
    print(f"[assets] ✅ Loaded {len(player_assets)} player token assets.")


def load_indicator_asset(assets_state, persistent_state):
    """Loads and scales the player-provided indicator asset from disk."""
    # 🎨 How large the indicator should be relative to a hex tile's width.
    INDICATOR_SCALE_FACTOR = 0.1

    # ✨ FIX: Ensure the 'ui_assets' dictionary exists before we do anything else.
    # This makes the function robust, even if it's called first.
    if "ui_assets" not in assets_state:
        assets_state["ui_assets"] = {}

    try:
        # ⚙️ Get the tile width to scale against.
        tile_hex_w = persistent_state["pers_tile_hex_w"]

        # Load the original, high-resolution image.
        full_path = "scenes/game_scene/assets/artwork/indicator.png" # ✅ Corrected Path
        original_surface = pygame.image.load(full_path).convert_alpha()
        
        # 📏 Calculate the new size while maintaining the aspect ratio.
        target_w = int(tile_hex_w * INDICATOR_SCALE_FACTOR)
        original_w, original_h = original_surface.get_size()
        aspect_ratio = original_h / original_w
        target_h = int(target_w * aspect_ratio)
        
        # Overwrite the original surface with the new, scaled version.
        indicator_surface = pygame.transform.smoothscale(original_surface, (target_w, target_h))
        
        # Store the finished asset in the global state.
        assets_state["ui_assets"]["collectible_indicator"] = indicator_surface
        
        print(f"[Assets] ✅ Loaded and scaled '{full_path}' asset.")

    except pygame.error as e:
        print(f"[Assets] ❌ Failed to load 'sprites/artwork/indicator.png': {e}")
        # Create a placeholder. This is now safe because we know 'ui_assets' exists.
        assets_state["ui_assets"]["collectible_indicator"] = pygame.Surface((20, 20), pygame.SRCALPHA)

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

    GLOW_INNER_BRIGHTNESS = 50 # The solid brightness of the inner hex (0-255)
    GLOW_FADE_PERCENT = 0.4    # The outer 40% of the hex will be a fade-out gradient

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

def create_collectibles_assets(assets_state, persistent_state):
    """
    Assembler function that orchestrates the creation of all collectible assets.
    It calls specialized functions to load the icon and generate the glow and shadow.
    """
    # ⚙️ Create the main dictionary to hold all collectible assets.
    assets_state["collectible_assets"] = {}

    # 📜 Call the specialized function to load and process the scroll icon.
    assets_state["collectible_assets"]["icon"] = _load_collectible_icon(persistent_state)
    
    # ✨ Call the specialized function to procedurally generate the glow effect.
    assets_state["collectible_assets"]["glow"] = _create_collectible_glow(persistent_state)
    
    # ⚫ Call the specialized function to procedurally generate the drop shadow.
    assets_state["collectible_assets"]["shadow"] = _create_collectible_shadow(persistent_state)

    print(f"[assets] ✅ Collectible assets assembled (Icon, Glow, Shadow).")

def _load_collectible_icon(persistent_state):
    """Loads, processes, and pre-scales the collectible's scroll icon."""
    
    # 🎨 Config & Constants
    SCROLL_SCALE_FACTOR = 0.5  # New: Makes the icon 50% of the hex width.
    
    # ⚙️ Shared Setup
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
    tile_hex_w = persistent_state["pers_tile_hex_w"]

    try:
        # 📜 Load the base scroll image from the file.
        scroll_sprite_path = "scenes/game_scene/assets/artwork/scroll.png" # ✅ Corrected Path
        base_sprite = pygame.image.load(scroll_sprite_path).convert_alpha()

        # 📏 Resize the base sprite to fit the desired scale on the hex tile.
        target_w = int(tile_hex_w * SCROLL_SCALE_FACTOR)
        original_w, original_h = base_sprite.get_size()
        aspect_ratio = original_h / original_w
        target_h = int(target_w * aspect_ratio)
        scaled_base_sprite = pygame.transform.smoothscale(base_sprite, (target_w, target_h))

        # 🖼️ Pre-scale the icon for every zoom level.
        icon_by_zoom = {}
        ow, oh = scaled_base_sprite.get_size()
        for z in zoom_steps:
            tw, th = max(1, int(ow * z)), max(1, int(oh * z))
            icon_by_zoom[z] = pygame.transform.smoothscale(scaled_base_sprite, (tw, th))
        
        # 💾 Return the completed, pre-scaled icon assets.
        return {
            "scale": icon_by_zoom,
            "blit_offset": (-scaled_base_sprite.get_width() / 2, -scaled_base_sprite.get_height() / 2)
        }
        
    except pygame.error as e:
        print(f"[assets] ❌ Error loading collectible icon: {e}")
        return None

def _create_collectible_glow(persistent_state):
    """Procedurally generates a custom, pre-scaled blue glow effect."""
   
    # 🎨 Config & Constants
    GLOW_COLOR = (70, 150, 255)
    GLOW_MAX_ALPHA = 120
    GLOW_SIZE_FACTOR = 0.6      # New: Slightly larger than the icon.
    GLOW_FADE_PERCENT = 0.5
    GLOW_VERTICAL_OFFSET = -10  # New: Reduced offset to better align with the icon.

    # ⚙️ Shared Setup
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])
    tile_hex_w = persistent_state["pers_tile_hex_w"]

    # 📐 Define Hexagon Geometry.
    glow_hex_w = int(tile_hex_w * GLOW_SIZE_FACTOR)
    glow_hex_h = int(glow_hex_w * (persistent_state["pers_tile_hex_h"] / tile_hex_w))
    hex_surface = pygame.Surface((glow_hex_w, glow_hex_h), pygame.SRCALPHA)
    center_x, center_y = glow_hex_w / 2, glow_hex_h / 2

    # Get points for the outer edge and inner solid part of the glow.
    outer_points = [
        (center_x, center_y - glow_hex_h / 2), (center_x + glow_hex_w / 2, center_y - glow_hex_h / 4),
        (center_x + glow_hex_w / 2, center_y + glow_hex_h / 4), (center_x, center_y + glow_hex_h / 2),
        (center_x - glow_hex_w / 2, center_y + glow_hex_h / 4), (center_x - glow_hex_w / 2, center_y - glow_hex_h / 4)]
    inner_scale = 1.0 - GLOW_FADE_PERCENT
    inner_points = [(center_x + (x - center_x) * inner_scale, center_y + (y - center_y) * inner_scale) for x, y in outer_points]

    # ✍️ Draw the feathered gradient glow.
    GRADIENT_STEPS = 15
    for i in range(GRADIENT_STEPS):
        t = i / (GRADIENT_STEPS - 1)
        alpha = int(GLOW_MAX_ALPHA * t)
        poly_points = []
        for j in range(6):
            x = outer_points[j][0] * (1 - t) + inner_points[j][0] * t
            y = outer_points[j][1] * (1 - t) + inner_points[j][1] * t
            poly_points.append((x,y))
        pygame.draw.polygon(hex_surface, (*GLOW_COLOR, alpha), poly_points)

    # 🖼️ Pre-scale the glow for every zoom level, applying the vertical offset.
    glow_by_zoom = {}
    for z in zoom_steps:
        scaled_w, scaled_h = max(1, int(glow_hex_w * z)), max(1, int(glow_hex_h * z))
        scaled_glow = pygame.transform.smoothscale(hex_surface, (scaled_w, scaled_h))
        final_canvas = pygame.Surface((scaled_w, scaled_h + abs(int(GLOW_VERTICAL_OFFSET * z))), pygame.SRCALPHA)
        final_canvas.blit(scaled_glow, (0, 0 if GLOW_VERTICAL_OFFSET > 0 else abs(int(GLOW_VERTICAL_OFFSET * z))))
        glow_by_zoom[z] = final_canvas

    # 💾 Return the completed, pre-scaled glow assets.
    return {
        "scale": glow_by_zoom,
        "blit_offset": (-glow_hex_w / 2, (-glow_hex_h / 2) + GLOW_VERTICAL_OFFSET)
    }

def _create_collectible_shadow(persistent_state):
    """Procedurally generates a soft, oval, pre-scaled drop shadow."""
   
    # 🎨 Config & Constants
    SHADOW_HORIZONTAL_DIAMETER = 100 # New: A good width for a 128px icon.
    SHADOW_VERTICAL_DIAMETER = 50    # New: A flattened oval for a nice 3D effect.
    SHADOW_MAX_ALPHA = 70
    SHADOW_FEATHER_STEPS = 15

    # ⚙️ Shared Setup
    zoom_steps = build_zoom_steps(persistent_state["pers_zoom_config"])

    # Create a master surface for the shadow.
    shadow_surface = pygame.Surface((SHADOW_HORIZONTAL_DIAMETER, SHADOW_VERTICAL_DIAMETER), pygame.SRCALPHA)
    
    # ✍️ Draw the feathered oval shadow by layering ellipses.
    for i in range(SHADOW_FEATHER_STEPS, 0, -1):
        t = i / SHADOW_FEATHER_STEPS
        alpha = int(SHADOW_MAX_ALPHA * (t**2))
        w, h = int(SHADOW_HORIZONTAL_DIAMETER * t), int(SHADOW_VERTICAL_DIAMETER * t)
        
        temp_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(temp_surf, (0,0,0,alpha), temp_surf.get_rect())

        shadow_surface.blit(temp_surf, ((SHADOW_HORIZONTAL_DIAMETER - w) // 2, (SHADOW_VERTICAL_DIAMETER - h) // 2), special_flags=pygame.BLEND_RGBA_ADD)

    # 🖼️ Pre-scale the shadow for every zoom level.
    shadow_by_zoom = {}
    ow, oh = shadow_surface.get_size()
    for z in zoom_steps:
        tw, th = max(1, int(ow * z)), max(1, int(oh * z))
        shadow_by_zoom[z] = pygame.transform.smoothscale(shadow_surface, (tw, th))
    
    # 💾 Return the completed, pre-scaled shadow assets.
    return {
        "scale": shadow_by_zoom,
        "blit_offset": (-SHADOW_HORIZONTAL_DIAMETER / 2, -SHADOW_VERTICAL_DIAMETER / 2)
    }
    
def load_family_portrait_assets(assets_state):
    """
    Loads layered family portrait assets for the UI.
    """
    # 🎨 Config & Constants
    portraits_base_path = "scenes/game_scene/assets/artwork/family_portraits" # ✅ Corrected Path
    PORTRAIT_SCALE_FACTOR = 0.5 # Adjust the size of the portraits. 1.0 is original size.
    
    # ⚙️ Initialize the dictionary in the global assets state.
    assets_state["family_portraits"] = {}

    #  ROBUSTNESS: Check if the base directory exists before proceeding.
    if not os.path.isdir(portraits_base_path):
        print(f"[assets] ⚠️  Family portraits directory not found, skipping: '{portraits_base_path}'")
        return

    # 📂 Iterate through each species' subfolder in the portraits directory.
    for species_name in os.listdir(portraits_base_path):
        species_dir_path = os.path.join(portraits_base_path, species_name)
        
        # Ensure we're only processing directories.
        if not os.path.isdir(species_dir_path):
            continue

        # Prepare temporary storage for this species' layers.
        background_layer = None
        member_layers_unsorted = []
        
        # 🖼️ Load each PNG layer file within the species' folder.
        for filename in os.listdir(species_dir_path):
            if not filename.endswith(".png"):
                continue

            full_path = os.path.join(species_dir_path, filename)
            
            try:
               # 1. Load the original image from disk with alpha transparency.
               original_surface = pygame.image.load(full_path).convert_alpha()

               # 2. Scale the image to its final size.
               if PORTRAIT_SCALE_FACTOR != 1.0:
                   original_w, original_h = original_surface.get_size()
                   new_w = max(1, int(original_w * PORTRAIT_SCALE_FACTOR))
                   new_h = max(1, int(original_h * PORTRAIT_SCALE_FACTOR))
                   scaled_surface = pygame.transform.smoothscale(original_surface, (new_w, new_h))
               else:
                   scaled_surface = original_surface

               # 3. ✨ Directly use the scaled surface with its original colors and alpha.
               final_surface = scaled_surface

               # 4. Parse the filename and store the final, processed surface.
               base_name = filename.removesuffix('.png')
               if base_name.endswith("_bg"):
                   background_layer = final_surface
               else:
                   parts = base_name.split('_')
                   if len(parts) > 1 and parts[-1].isdigit():
                       member_index = int(parts[-1])
                       member_layers_unsorted.append((member_index, final_surface))

            except pygame.error as e:
                print(f"[assets] ❌ Could not load portrait layer '{filename}': {e}")
                continue # Skip to the next file
        
        # 🔢 Sort the family members numerically by their parsed index.
        member_layers_unsorted.sort(key=lambda item: item[0])
        
        # Create the final, clean list of sorted surfaces.
        sorted_member_surfaces = [surface for index, surface in member_layers_unsorted]

        # 💾 Store the final, structured data for this species.
        if background_layer and sorted_member_surfaces:
            assets_state["family_portraits"][species_name] = {
                "background": background_layer,
                "members": sorted_member_surfaces,
            }
            if DEBUG:
                print(f"[assets]   - Processed '{species_name}': Found background and {len(sorted_member_surfaces)} members.")
        else:
            print(f"[assets] ⚠️  Skipping portrait for '{species_name}': Missing background or member layers.")
    
    print(f"[assets] ✅ Loaded {len(assets_state['family_portraits'])} complete family portraits.")

