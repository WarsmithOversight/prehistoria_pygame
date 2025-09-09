# ui_assets.py
import os
import pygame
from shared_helpers import desaturate_surface
from ui.ui_font_and_styles import initialize_font_cache

DEBUG = True

# ──────────────────────────────────────────────────
# Textures
# ──────────────────────────────────────────────────

def load_ui_textures(assets_state):
    """Loads all full-resolution source textures for the UI."""
    
    path_to_textures = "textures"

    # A dictionary mapping texture filenames to their asset keys
    textures_to_load = {
        "ZM_Basecolor.png": "bark_full_res",
        "STZ_basecolor.png": "stone_full_res"
    }

    for filename, key in textures_to_load.items():
        source_file = os.path.join(path_to_textures, filename)
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
    
    GRAYSCALE_TEXTURE_SIZE = (196, 196) # The scale of the repeating background pattern

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
            "border_width": 10,                  # The thickness of this border style
            "desaturation": 0.0                  # How much to desaturate (0.0 = none)
        },
        {
            "source_key": "stone_full_res",
            "output_key": "stone_border_pieces",
            "border_width": 5,                 
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

# ui_assets.py

def create_screen_edge_glow(screen_size, color, thickness):
    """Creates a surface with a soft, exponential glow around the screen edges."""
    width, height = screen_size
    # Create the target surface with per-pixel alpha
    glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    base_color = color[:3]
    base_alpha = color[3] if len(color) > 3 else 255
    
    # Create a base rectangle for the full screen
    base_rect = pygame.Rect(0, 0, width, height)

    # Draw a series of shrinking, fading rectangle outlines from the edge inwards
    for i in range(thickness):
        # 't' represents our progress from the edge (0.0) to the inside (1.0)
        t = i / thickness
        
        # Use an exponential curve for a nice, soft falloff
        alpha = base_alpha * (1 - t)**2 
        rect_color = (*base_color, int(alpha))
        
        # Create a new rectangle inset by 'i' pixels
        # inflate shrinks the rect; it applies to each side, so we multiply by 2
        inset_rect = base_rect.inflate(-i * 2, -i * 2)
        
        # Draw the outline of the inset rectangle (1 pixel thick)
        pygame.draw.rect(glow_surface, rect_color, inset_rect, 1)
 
    return glow_surface

def load_all_ui_assets(assets_state, persistent_state):
    """Orchestrator to run the entire UI asset creation pipeline."""
    assets_state["ui_assets"] = {}
    
    initialize_font_cache()
    load_ui_textures(assets_state)
    create_grayscale_ui_watermarks(assets_state)
    create_ui_border_assets(assets_state)

    # ✨ Create the new procedural screen glow asset.
    screen = persistent_state["pers_screen"]
    screen_w, screen_h = screen.get_size()
    # Now that we have the size, store it for any other systems that might need it.
    assets_state["screen_size"] = (screen_w, screen_h)

    red_glow_color = (255, 50, 50, 150) # Red with a base alpha of 150
    # The final argument is the 'thickness' in pixels, which you can easily edit here.
    assets_state["ui_assets"]["screen_edge_glow_red"] = create_screen_edge_glow((screen_w, screen_h), red_glow_color, 80)