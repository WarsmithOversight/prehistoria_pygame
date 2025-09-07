import pygame
import math
import random

DEBUG = True

class BasePanel:
    """A base class for all UI panels."""
    def __init__(self, persistent_state, assets_state):
        self.persistent_state = persistent_state
        self.assets_state = assets_state

        # ✨ Add a visibility flag for conditional rendering.
        self.is_visible = True

        self.surface = None
        self.rect = None
        self.drawable_key = None # Unique key for the notebook

    def update(self, notebook):
        """Creates the drawable dictionary and publishes it to the notebook."""
        if self.surface and self.rect and self.drawable_key:
            z_formula = self.persistent_state["pers_z_formulas"]["ui_panel"]
            
            notebook[self.drawable_key] = {
                "type": "ui_panel",
                "surface": self.surface,
                "rect": self.rect,
                "z": z_formula(0) # UI z-value doesn't depend on row
            }

    def destroy(self, notebook):
        """Removes the panel's drawable from the notebook, effectively hiding it."""
        if self.drawable_key and self.drawable_key in notebook:
            del notebook[self.drawable_key]
        if DEBUG: print(f"[BasePanel] ✅ Destroyed drawable: '{self.drawable_key}'")

## How a Panel is Built 🖼️ ##

# 1.  Create the Background: 
#         A dark, textured canvas is created first. 
#         This serves as the backing for the frame.
# 2.  Cut the Wood: 
#         Four straight, textured "planks" are made for the 
#         top, bottom, left, and right sides.
# 3.  Carve the Squiggles: 
#         The inner edge of each plank is "carved" with
#         a wavy, organic line, making it look natural and hand-hewn.
# 4.  Assemble the Frame: 
#         The four wavy planks are arranged into a rectangle.
# 5.  Round the Corners: 
#         The sharp corners of the assembled frame are then 
#         carved into smooth, rounded joints, seamlessly connecting the edges.
# 6.  Final Assembly: 
#         The finished, carved frame is placed on top of the 
#         background canvas to create the complete panel.

def assemble_organic_panel(panel_size, background_size, assets_state):
    """Orchestrator that builds a complete panel with a procedural organic border."""
    width, height = panel_size

    # Create the oversized background surface first.
    final_panel = background_panel_helper(panel_size, background_size, assets_state)

    # Assemble the four edge pieces on a separate, temporary surface.
    frame_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    top_edge = create_organic_panel_edge(width, 'horizontal', ['1', '2', '3'], assets_state)
    bottom_edge = create_organic_panel_edge(width, 'horizontal', ['7', '8', '9'], assets_state)
    left_edge = create_organic_panel_edge(height, 'vertical', ['1', '4', '7'], assets_state)
    right_edge = create_organic_panel_edge(height, 'vertical', ['3', '6', '9'], assets_state)

    frame_surface.blit(top_edge, (0, 0))
    frame_surface.blit(left_edge, (0, 0))
    frame_surface.blit(right_edge, (width - right_edge.get_width(), 0))
    frame_surface.blit(bottom_edge, (0, height - bottom_edge.get_height()))

    # Carve the corners of the assembled frame.
    frame_surface = _carve_corners_geometrically(frame_surface, assets_state)

    # Blit the finished frame onto the background.
    final_panel.blit(frame_surface, (0,0))
    
    return final_panel

def background_panel_helper(panel_size, background_size, assets_state):
    """Creates the base panel surface, including a centered, tiled watermark background."""
    # 🎨 Config & Constants
    BACKGROUND_COLOR = (20, 20, 20)
    WATERMARK_ALPHA = 15

    # 📏 Unpack the pre-calculated dimensions
    width, height = panel_size
    bg_width, bg_height = background_size

    # 🖼️ Create the oversized final surface
    panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # 🏞️ Create the smaller, tiled background texture
    tiled_background = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
    tiled_background.fill(BACKGROUND_COLOR)
    watermark = assets_state["ui_assets"].get("bark_background_watermark")
    if watermark:
        watermark.set_alpha(WATERMARK_ALPHA)
        tex_w, tex_h = watermark.get_size()
        for x in range(0, bg_width, tex_w):
            for y in range(0, bg_height, tex_h):
                tiled_background.blit(watermark, (x, y))

    # 📍 Blit the tiled texture into the center of the main panel
    blit_x = (width - bg_width) / 2
    blit_y = (height - bg_height) / 2
    panel_surface.blit(tiled_background, (blit_x, blit_y))
    
    return panel_surface

def create_organic_panel_edge(length, orientation, tile_sequence, assets_state):
    """Creates a single, processed, wavy edge surface for any side."""

    # ──────────────────────────────────────────────────
    # 🎨 Artistic Control Panel
    # ──────────────────────────────────────────────────
    # This section contains all the artistic controls for the squiggle effect.

    # How much of the border thickness is unaffected by squiggles (e.g., 1/3 is safe).
    SAFE_ZONE_RATIO = 2 / 3
    
    # Of the remaining "action zone," how much amplitude belongs to the main wave (e.g., 0.8 = 80%).
    PRIMARY_WAVE_RATIO = 0.9
    
    # How many tile widths it takes for one main "swoop" to complete.
    PRIMARY_WAVELENGTH_IN_TILES = 20
    
    # How many smaller swoops appear on top of each main swoop.
    SECONDARY_SWOOPS_PER_PRIMARY = 4
    
    # The smoothness of the curve. Higher is smoother.
    SEGMENTS_PER_TILE = 25
    
    # ──────────────────────────────────────────────────
    #  Helper Function
    # ──────────────────────────────────────────────────

    def _generate_squiggly_points(start_pos, end_pos, segments, p_amp, s_amp, p_wavelength_px, s_swoops):
        """A nested helper that generates points for a single squiggly line."""
        points = []
        
        # Calculate the total length of the line to be squiggled
        total_length = math.hypot(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
        if total_length == 0: return [start_pos, end_pos]
        
        # Calculate wave frequencies based on wavelength and swoops
        num_primary_waves = total_length / p_wavelength_px
        freq1 = num_primary_waves * 2
        freq2 = freq1 * s_swoops
        
        # Randomize the starting phase for a unique look
        phase1 = random.uniform(0, 2 * math.pi)
        phase2 = random.uniform(0, 2 * math.pi)
        
        is_horizontal = abs(start_pos[1] - end_pos[1]) < abs(start_pos[0] - end_pos[0])
        
        for i in range(segments + 1):
            t = i / segments
            x = start_pos[0] + t * (end_pos[0] - start_pos[0])
            y = start_pos[1] + t * (end_pos[1] - start_pos[1])
            
            undulation1 = p_amp * math.sin(t * freq1 * math.pi + phase1)
            undulation2 = s_amp * math.sin(t * freq2 * math.pi + phase2)
            
            fade_factor = math.sin(t * math.pi)
            total_undulation = (undulation1 + undulation2) * fade_factor
            
            if is_horizontal:
                points.append((x, y + total_undulation))
            else:
                points.append((x + total_undulation, y))
        return points

    # ──────────────────────────────────────────────────
    # ⚙️ Asset Loading & Geometry Calculation
    # ──────────────────────────────────────────────────

    # 📏 Get Asset Dimensions
    border_pieces = assets_state["ui_assets"].get("bark_border_pieces")
    if not border_pieces: return pygame.Surface((12, 12), pygame.SRCALPHA)
    tile_dim = border_pieces['1'].get_width()
    
    # 📐 Calculate Geometry from the Control Panel Constants
    safe_zone = tile_dim * SAFE_ZONE_RATIO
    action_zone = tile_dim - safe_zone
    max_amplitude = action_zone / 2
    
    FINAL_INSET = safe_zone + max_amplitude
    
    # Nonchalantly toss the calculated value into the state dictionary
    assets_state["var_wood_border_inset"] = FINAL_INSET

    primary_amp = max_amplitude * PRIMARY_WAVE_RATIO
    secondary_amp = max_amplitude - primary_amp
    
    p_wavelength_px = tile_dim * PRIMARY_WAVELENGTH_IN_TILES
    
    action_zone_length = length - (tile_dim * 2)
    num_tiles_in_action_zone = action_zone_length / tile_dim
    SEGMENTS = int(num_tiles_in_action_zone * SEGMENTS_PER_TILE)

    if orientation == 'horizontal':
        width, height = length, tile_dim
    else:
        width, height = tile_dim, length

    # ──────────────────────────────────────────────────
    # 🎨 Surface Assembly & Masking
    # ──────────────────────────────────────────────────

    # 🏞️ Tile the background texture
    strip_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(length // tile_dim + 1):
        tile_key = tile_sequence[i % len(tile_sequence)]
        if orientation == 'horizontal':
            strip_surface.blit(border_pieces[tile_key], (i * tile_dim, 0))
        else:
            strip_surface.blit(border_pieces[tile_key], (0, i * tile_dim))

    # ✍️ Generate the points for the mask using the new controls
    common_args = (SEGMENTS, primary_amp, secondary_amp, p_wavelength_px, SECONDARY_SWOOPS_PER_PRIMARY)
    if orientation == 'horizontal':
        line1_squiggle = _generate_squiggly_points((tile_dim, FINAL_INSET), (width - tile_dim, FINAL_INSET), *common_args)
        line2_squiggle = _generate_squiggly_points((tile_dim, height - FINAL_INSET), (width - tile_dim, height - FINAL_INSET), *common_args)
        mask_points = [(0, 0), (tile_dim, 0), *line1_squiggle, (width - tile_dim, 0), (width, 0), (width, height), 
                       (width - tile_dim, height), *reversed(line2_squiggle), (tile_dim, height), (0, height)]
    else:
        line1_squiggle = _generate_squiggly_points((FINAL_INSET, tile_dim), (FINAL_INSET, height - tile_dim), *common_args)
        line2_squiggle = _generate_squiggly_points((width - FINAL_INSET, tile_dim), (width - FINAL_INSET, height - tile_dim), *common_args)
        mask_points = [(0, 0), (0, tile_dim), *line1_squiggle, (0, height - tile_dim), (0, height), (width, height), 
                       (width, height - tile_dim), *reversed(line2_squiggle), (width, tile_dim), (width, 0)]
    
    # 🎭 Create the mask and apply it
    mask_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(mask_surface, (255, 255, 255), mask_points)
    strip_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    
    return strip_surface

def _carve_corners_geometrically(frame_surface, assets_state):
    """
    Carves the panel corners by generating a precise polygon mask for each corner,
    confining the operation to only the corner regions.
    """
    # ──────────────────────────────────────────────────
    # ⚙️ Step 1 & 2: Define Corner Geometry, Inset, and Radii
    # ──────────────────────────────────────────────────
    border_pieces = assets_state["ui_assets"].get("bark_border_pieces", {})
    if not border_pieces: return frame_surface

    tile_dim = border_pieces['1'].get_width()
    width, height = frame_surface.get_size()

    # Re-calculate the inset value to ensure it's a precise float.
    safe_zone = tile_dim / 2
    action_zone = tile_dim - safe_zone
    max_amplitude = action_zone / 2
    primary_amp = max_amplitude * 0.9
    final_inset = safe_zone + primary_amp + (max_amplitude - primary_amp)
    
    inner_radius = final_inset 
    outer_radius = tile_dim - final_inset

    corners_data = {
        "top_left": {
            "rect": pygame.Rect(0, 0, tile_dim + 1, tile_dim + 1),
            "pivot": (tile_dim + 1, tile_dim + 1),
            "angles": (math.pi, 3 * math.pi / 2)
        },
        "top_right": {
            "rect": pygame.Rect(width - tile_dim - 1, 0, tile_dim + 1, tile_dim + 1),
            "pivot": (width - tile_dim - 1, tile_dim + 1),
            "angles": (3 * math.pi / 2, 2 * math.pi)
        },
        "bottom_left": {
            "rect": pygame.Rect(0, height - tile_dim - 1, tile_dim + 1, tile_dim + 1),
            "pivot": (tile_dim + 1, height - tile_dim - 1),
            "angles": (math.pi / 2, math.pi)
        },
        "bottom_right": {
            "rect": pygame.Rect(width - tile_dim - 1, height - tile_dim - 1, tile_dim + 1, tile_dim + 1),
            "pivot": (width - tile_dim - 1, height - tile_dim - 1),
            "angles": (0, math.pi / 2)
        }
    }

    # ──────────────────────────────────────────────────
    # 🎨 Step 3 & 4: Generate Local Masks and Apply
    # ──────────────────────────────────────────────────
    ARC_SEGMENTS = 15

    for data in corners_data.values():
        corner_rect = data["rect"]
        pivot_x, pivot_y = data["pivot"]
        start_angle, end_angle = data["angles"]
        
        outer_arc_points, inner_arc_points = [], []
        for i in range(ARC_SEGMENTS + 1):
            t = i / ARC_SEGMENTS
            angle = start_angle + t * (end_angle - start_angle)
            
            outer_arc_points.append((pivot_x + math.cos(angle) * outer_radius, pivot_y + math.sin(angle) * outer_radius))
            inner_arc_points.append((pivot_x + math.cos(angle) * inner_radius, pivot_y + math.sin(angle) * inner_radius))

        # Combine points into a polygon relative to the full surface.
        mask_points = outer_arc_points + list(reversed(inner_arc_points))
        
        # ✨ NEW: Create a SMALL mask surface, just for the corner.
        local_mask = pygame.Surface(corner_rect.size, pygame.SRCALPHA)
        
        # Translate the polygon points to be relative to the small mask's (0,0).
        translated_points = [(p[0] - corner_rect.left, p[1] - corner_rect.top) for p in mask_points]
        pygame.draw.polygon(local_mask, (255, 255, 255, 255), translated_points)
        
        # ✨ NEW: Isolate the operation to a subsurface of the corner.
        # This modifies the original frame_surface directly.
        corner_subsurface = frame_surface.subsurface(corner_rect)
        corner_subsurface.blit(local_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
    return frame_surface
