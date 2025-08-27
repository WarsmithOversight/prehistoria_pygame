# ui_components.py
# stores dependancies from ui panels

import random, math, pygame


# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

RAW_SQUIGGLE_ANCHOR_INSET = 2.0  # The "spine" of the wave, main artistic control
SECONDARY_AMPLITUDE_FACTOR = 0.4 # Secondary wave is 40% of the primary's amplitude
PRIMARY_FREQ_RANGE = (1.5, 2.0)  # Slower, wider waves
SECONDARY_FREQ_RANGE = (4.0, 6.0) # Faster, smaller waves
SEGMENTS_PER_TILE = 10           # Controls curve smoothness
UI_ELEMENT_PADDING = (25, 15) # (Horizontal, Vertical)

DEBUG = True

# ──────────────────────────────────────────────────
# Generic Classes
# ──────────────────────────────────────────────────

class Button:
    """A generic, stateful UI button."""
    def __init__(self, rect, asset_name, callback, assets_state):
        self.rect = rect
        self.callback = callback
        self.asset_name = asset_name
        self.assets_state = assets_state

        # Fetch the pre-loaded button images from the assets dictionary
        self.images = self.assets_state["ui_assets"]["buttons"].get(self.asset_name, {})
        if not self.images:
            if DEBUG: print(f"[Button] ⚠️  Assets for '{self.asset_name}' not found.")

        # Internal state management
        self.state = "normal"  # Can be "normal", "hover", or "active"
        self._is_pressed = False

    def handle_events(self, events, mouse_pos):
        """Processes a list of events to update the button's state and trigger its callback."""
        
        # Use the provided mouse_pos instead of calling pygame.mouse.get_pos()
        is_hovering = self.rect.collidepoint(mouse_pos)

        for event in events:
            # Handle mouse button down
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and is_hovering:
                self._is_pressed = True
            
            # Handle mouse button up
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # If released over the button, trigger the callback
                if self._is_pressed and is_hovering:
                    self.callback()
                self._is_pressed = False
        
        # Update visual state based on hover and press status
        if self._is_pressed and is_hovering:
            self.state = "active"
        elif is_hovering:
            self.state = "hover"
        else:
            self.state = "normal"

    def draw(self, surface):
        """Draws the button onto the provided surface."""
        # Select the correct image based on the current state
        image_to_draw = self.images.get(self.state)
        
        # Blit the image if it exists
        if image_to_draw:
            surface.blit(image_to_draw, self.rect.topleft)

class BasePanel:
    """A base class for all UI panels."""
    def __init__(self, persistent_state, assets_state):
        self.persistent_state = persistent_state
        self.assets_state = assets_state
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

# ──────────────────────────────────────────────────
# Components & Helpers
# ──────────────────────────────────────────────────

def _generate_squiggly_points(start_pos, end_pos, segments, primary_amplitude):
    """Generates a list of points for a single squiggly line with randomized compound waves."""
    points = []
    secondary_amplitude = primary_amplitude * SECONDARY_AMPLITUDE_FACTOR
    freq1 = random.uniform(*PRIMARY_FREQ_RANGE)
    freq2 = random.uniform(*SECONDARY_FREQ_RANGE)
    phase1 = random.uniform(0, 2 * math.pi)
    phase2 = random.uniform(0, 2 * math.pi)
    is_horizontal = abs(start_pos[1] - end_pos[1]) < abs(start_pos[0] - end_pos[0])
    
    for i in range(segments + 1):
        t = i / segments
        x = start_pos[0] + t * (end_pos[0] - start_pos[0])
        y = start_pos[1] + t * (end_pos[1] - start_pos[1])
        undulation1 = primary_amplitude * math.sin(t * freq1 * math.pi + phase1)
        undulation2 = secondary_amplitude * math.sin(t * freq2 * math.pi + phase2)
        fade_factor = math.sin(t * math.pi)
        total_undulation = (undulation1 + undulation2) * fade_factor
        if is_horizontal:
            points.append((x, y + total_undulation))
        else:
            points.append((x + total_undulation, y))
    return points

def create_organic_panel_edge(length, orientation, tile_sequence, assets_state):
    """Creates a single, processed, wavy edge surface for any side."""
    border_pieces = assets_state["ui_assets"].get("border_pieces")
    if not border_pieces: return pygame.Surface((32, 32), pygame.SRCALPHA)
    
    tile_dim = border_pieces['1'].get_width()
    BORDER_THICKNESS = tile_dim
    SAFE_ZONE = tile_dim * 1
    
    primary_amp = RAW_SQUIGGLE_ANCHOR_INSET
    secondary_amp = primary_amp * SECONDARY_AMPLITUDE_FACTOR
    FINAL_INSET = math.ceil(primary_amp + secondary_amp)
    
    action_zone_length = length - (SAFE_ZONE * 2)
    num_tiles = action_zone_length / tile_dim
    SEGMENTS = int(num_tiles * SEGMENTS_PER_TILE)

    if orientation == 'horizontal':
        width, height = length, BORDER_THICKNESS
    else:
        width, height = BORDER_THICKNESS, length

    strip_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(length // tile_dim + 1):
        tile_key = tile_sequence[i % len(tile_sequence)]
        if orientation == 'horizontal':
            strip_surface.blit(border_pieces[tile_key], (i * tile_dim, 0))
        else:
            strip_surface.blit(border_pieces[tile_key], (0, i * tile_dim))

    if orientation == 'horizontal':
        line1_squiggle = _generate_squiggly_points((SAFE_ZONE, FINAL_INSET), (width - SAFE_ZONE, FINAL_INSET), SEGMENTS, primary_amp)
        line2_squiggle = _generate_squiggly_points((SAFE_ZONE, height - FINAL_INSET), (width - SAFE_ZONE, height - FINAL_INSET), SEGMENTS, primary_amp)
        mask_points = [(0, 0), (SAFE_ZONE, 0), *line1_squiggle, (width - SAFE_ZONE, 0), (width, 0), (width, height), 
                       (width - SAFE_ZONE, height), *reversed(line2_squiggle), (SAFE_ZONE, height), (0, height)]
    else:
        line1_squiggle = _generate_squiggly_points((FINAL_INSET, SAFE_ZONE), (FINAL_INSET, height - SAFE_ZONE), SEGMENTS, primary_amp)
        line2_squiggle = _generate_squiggly_points((width - FINAL_INSET, SAFE_ZONE), (width - FINAL_INSET, height - SAFE_ZONE), SEGMENTS, primary_amp)
        mask_points = [(0, 0), (0, SAFE_ZONE), *line1_squiggle, (0, height - SAFE_ZONE), (0, height), (width, height), 
                       (width, height - SAFE_ZONE), *reversed(line2_squiggle), (width, SAFE_ZONE), (width, 0)]
    
    mask_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(mask_surface, (255, 255, 255), mask_points)
    strip_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return strip_surface

def _carve_corners_geometrically(frame_surface, assets_state):
    """
    Carves the panel corners by creating a perfect radial band, precisely
    matching the user's compass and paper cutout analogy.
    """
    # ⚙️ Geometry Setup from Your Diagrams
    border_pieces = assets_state["ui_assets"].get("border_pieces", {})
    if not border_pieces: return frame_surface

    tile_dim = border_pieces['1'].get_width()
    width, height = frame_surface.get_size()

    # Calculate the inset distance, which defines where the edges meet the corner
    primary_amp = RAW_SQUIGGLE_ANCHOR_INSET
    secondary_amp = primary_amp * SECONDARY_AMPLITUDE_FACTOR
    final_inset = primary_amp + secondary_amp # Use the precise float value

    # The distance from the pivot to the inner (blue) points
    inner_radius = final_inset
    
    # The distance from the pivot to the outer (yellow) points
    outer_radius = tile_dim - final_inset

    # The locations of the four pivots, set 1px outside the corner tile
    pivot_points = {
        "top_left": (tile_dim + 1, tile_dim + 1),
        "top_right": (width - tile_dim - 1, tile_dim + 1),
        "bottom_left": (tile_dim + 1, height - tile_dim - 1),
        "bottom_right": (width - tile_dim - 1, height - tile_dim - 1)
    }
    
    # The bounding box for each corner's pixel region to optimize the process
    corner_regions = {
        "top_left": pygame.Rect(0, 0, tile_dim, tile_dim),
        "top_right": pygame.Rect(width - tile_dim, 0, tile_dim, tile_dim),
        "bottom_left": pygame.Rect(0, height - tile_dim, tile_dim, tile_dim),
        "bottom_right": pygame.Rect(width - tile_dim, height - tile_dim, tile_dim, tile_dim)
    }

    # ✍️ Carve the Band
    for name, rect in corner_regions.items():
        center_x, center_y = pivot_points[name]
        
        # Iterate over every pixel only within this corner's bounding box
        for x in range(rect.left, rect.right):
            for y in range(rect.top, rect.bottom):
                # Measure distance from the pixel to the pivot point
                dist = math.hypot(x - center_x, y - center_y)
                # Keep the pixel ONLY if its distance is between the inner and outer radii
                is_in_band = inner_radius <= dist <= outer_radius
                
                if not is_in_band:
                    frame_surface.set_at((x, y), (0, 0, 0, 0))
                        
    return frame_surface

def background_panel_helper(width, height, assets_state):
    """Creates the base panel surface, including a centered, tiled watermark background."""
    
    # 🎨 Config & Constants
    BACKGROUND_COLOR = (20, 20, 20)
    WATERMARK_ALPHA = 5

    # ⚙️ Calculate BG dimensions based on final panel size
    border_pieces = assets_state["ui_assets"].get("border_pieces", {})
    tile_dim = border_pieces['1'].get_width() if border_pieces else 32
    padding = tile_dim / 2
    bg_width = int(width - (padding * 2))
    bg_height = int(height - (padding * 2))

    # 🖼️ Create  the oversized final surface
    panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # 🏞️ Create the smaller, tiled background texture
    tiled_background = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
    tiled_background.fill(BACKGROUND_COLOR)
    watermark = assets_state["ui_assets"].get("background_watermark")
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

def create_grid_placements(panel_rect, grid_dims, item_size):
    """
    Calculates the positions for items in a centered grid within a panel.
    Returns a dictionary of rects, keyed by cell index (0, 1, 2...).
    """
    placements = {}
    cols, rows = grid_dims
    item_w, item_h = item_size
    pad_x, pad_y = UI_ELEMENT_PADDING

    # Calculate the total width and height required for the grid content
    total_content_w = (cols * item_w) + ((cols - 1) * pad_x)
    total_content_h = (rows * item_h) + ((rows - 1) * pad_y)

    # Calculate the starting top-left position to center the grid inside the panel
    start_x = panel_rect.left + (panel_rect.width - total_content_w) / 2
    start_y = panel_rect.top + (panel_rect.height - total_content_h) / 2

    # Generate the rect for each cell in the grid
    for i in range(rows * cols):
        row = i // cols
        col = i % cols
        
        # Calculate the position for this specific cell
        cell_x = start_x + col * (item_w + pad_x)
        cell_y = start_y + row * (item_h + pad_y)
        
        # Create and store the rect
        placements[i] = pygame.Rect(cell_x, cell_y, item_w, item_h)
        
    return placements


# ──────────────────────────────────────────────────
# Assembler
# ──────────────────────────────────────────────────

def assemble_organic_panel(width, height, assets_state):
    """Orchestrator that builds a complete panel with a procedural organic border."""

    # 1. Create the oversized background surface first.
    final_panel = background_panel_helper(width, height, assets_state)

    # 2. Assemble the four edge pieces on a separate, temporary surface.
    frame_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    top_edge = create_organic_panel_edge(width, 'horizontal', ['1', '2', '3'], assets_state)
    bottom_edge = create_organic_panel_edge(width, 'horizontal', ['7', '8', '9'], assets_state)
    left_edge = create_organic_panel_edge(height, 'vertical', ['1', '4', '7'], assets_state)
    right_edge = create_organic_panel_edge(height, 'vertical', ['3', '6', '9'], assets_state)

    frame_surface.blit(top_edge, (0, 0))
    frame_surface.blit(left_edge, (0, 0))
    frame_surface.blit(right_edge, (width - right_edge.get_width(), 0))
    frame_surface.blit(bottom_edge, (0, height - bottom_edge.get_height()))

    # 3. Carve the corners of the assembled frame.
    frame_surface = _carve_corners_geometrically(frame_surface, assets_state)

    # 4. Blit the finished frame onto the background.
    final_panel.blit(frame_surface, (0,0))
    
    return final_panel

