import pygame
import math
import random
from ui.ui_font_and_styles import get_font
from ui.ui_dimensions import UI_ELEMENT_PADDING, BUTTON_CORNER_CHAOS_FACTOR

class Button:
    """A generic, stateful UI button that caches its base and composites on the fly."""
    def __init__(self, rect, text, assets_state, style, dims, callback):
        self.rect = rect
        self.callback = callback
        self.assets_state = assets_state
        self.is_visible = True
        self.style = style
        self.dims = dims
        self.font = get_font(style["font_size_key"])
        
        # Caching: Generate the complex base surface ONCE.
        self.base_surface = _generate_button_base_surface(assets_state, dims)
        
        # Generate the initial text surface.
        self.text_surface = self.font.render(text, True, style["text_color"])
        self._calculate_text_rect()

        self.state = "normal"
        self._is_pressed = False

    def _calculate_text_rect(self):
        """Calculates the centered position for the text on the button base."""
        border_width, border_height = self.base_surface.get_size()
        final_size = self.dims["hexagonal_background_size"]
        bg_offset_x = (border_width - final_size[0]) / 2
        
        align = self.style.get("align", "center")
        text_rect_center = (border_width / 2, border_height / 2)
        
        if align == "left":
            self.text_rect = self.text_surface.get_rect(midleft=(bg_offset_x + UI_ELEMENT_PADDING[0], text_rect_center[1]))
        elif align == "right":
            self.text_rect = self.text_surface.get_rect(midright=(border_width - bg_offset_x - UI_ELEMENT_PADDING[0], text_rect_center[1]))
        else: # Default to center
            self.text_rect = self.text_surface.get_rect(center=text_rect_center)

    def update_text(self, new_text):
        """Fast text-only update. Only re-renders the text surface."""
        self.text_surface = self.font.render(new_text, True, self.style["text_color"])
        self._calculate_text_rect()

    def handle_events(self, events, mouse_pos):
        is_hovering = self.rect.collidepoint(mouse_pos)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and is_hovering:
                self._is_pressed = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._is_pressed and is_hovering:
                    self.callback()
                self._is_pressed = False
        
        if self._is_pressed and is_hovering: self.state = "active"
        elif is_hovering: self.state = "hover"
        else: self.state = "normal"

    def draw(self, surface, offset=(0, 0)): # ✨ Add an offset argument
        """Draws the cached base and the current text surface separately."""
        surface.blit(self.base_surface, self.rect.topleft)
        surface.blit(self.text_surface, (self.rect.left + self.text_rect.left, self.rect.top + self.text_rect.top))

# How a Button is Built 🔘 ##
# 1.  Carve the Stone Core: 
#         A solid hexagonal shape with a stony texture 
#         is carved out. This is the base of the button.
# 2.  Define the Border:
#         A path is drawn around the hexagon to mark where 
#         the border will be.
# 3.  Chip the Edges: 
#         This path is then made jagged and chaotic, as if 
#         the edges of the stone have been naturally weathered.
# 4.  Create the Border Piece: 
#         A separate stone texture is "stamped out" 
#         using this jagged, chipped path, creating a rough, aged border.
# 5.  Final Assembly:
#         The finished, chipped border is placed on top of 
#         the hexagonal stone core.
# 6.  Add the Inscription:
#         Finally, the button's text is rendered and placed 
#         in the center.

def _generate_button_base_surface(assets_state, dims):
    """
    Generates only the static, procedural parts of the button (background and border).
    This is the slow part that we want to cache.
    """

    # 🧰 Step 1: Get all necessary geometry and assets
    corners = dims["hexagonal_corner_points"]
    final_size = dims["hexagonal_background_size"]

    final_canvas_size = dims["uniform_button_final_size"]
    border_lines = _generate_procedural_border_lines(corners, assets_state, dims)
    background_surface = hexagonal_background_panel_helper(assets_state, corners, final_size)

    # 🎨 Step 2: Create the crisp, textured border fill
    # Determine the size of the surface needed to contain the entire border
    min_x, max_x = min(p[0] for p in border_lines["outer"]), max(p[0] for p in border_lines["outer"])
    min_y, max_y = min(p[1] for p in border_lines["outer"]), max(p[1] for p in border_lines["outer"])
    border_render_size = (max_x - min_x, max_y - min_y)
    textured_border = pygame.Surface(border_render_size, pygame.SRCALPHA)

    # ✨ 1. Create a smoother, lower-resolution texture using your scaling idea.
    border_pieces = assets_state["ui_assets"].get("stone_border_pieces", {})
    if border_pieces:
        tile_dim = border_pieces['1'].get_width()
        # Assemble the high-res 3x3 tile
        master_tile = pygame.Surface((tile_dim * 3, tile_dim * 3))
        for r in range(3):
            for c in range(3):
                master_tile.blit(border_pieces[str(r*3+c+1)], (c*tile_dim, r*tile_dim))
        
        # Scale it down and then smoothscale it back up to create a softer, larger texture
        scaled_down = pygame.transform.scale(master_tile, (master_tile.get_width() // 2, master_tile.get_height() // 2))
        soft_master_tile = pygame.transform.smoothscale(scaled_down, master_tile.get_size())

        # Now, tile this new "soft" tile onto the border surface
        tex_w, tex_h = master_tile.get_size()
        for x in range(0, int(border_render_size[0]), tex_w):
            for y in range(0, int(border_render_size[1]), tex_h):
                textured_border.blit(soft_master_tile, (x, y))

    # Create a mask from the border's procedural shape
    border_mask = pygame.Surface(border_render_size, pygame.SRCALPHA)
    offset = (-min_x, -min_y)
    translated_outer = [(p[0] + offset[0], p[1] + offset[1]) for p in border_lines["outer"]]
    translated_inner = [(p[0] + offset[0], p[1] + offset[1]) for p in border_lines["inner"]]
    pygame.draw.polygon(border_mask, (255, 255, 255, 255), translated_outer)
    pygame.draw.polygon(border_mask, (0, 0, 0, 0), translated_inner)

    # Use the mask to "stamp out" the final textured border
    textured_border.blit(border_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # ✨ 2. Create a clean, sharp, semi-transparent stroke without the blur.
    stroke_surface = pygame.Surface(border_render_size, pygame.SRCALPHA)
    pygame.draw.polygon(stroke_surface, (20, 15, 10, 150), translated_outer, 2) # A dark, semi-transparent stroke

    # 📦 Step 4: Composite all layers onto the final canvas
    final_button_surface = pygame.Surface(final_canvas_size, pygame.SRCALPHA)

    # Layer 1: The centered hexagonal background
    bg_w, bg_h = final_size
    bg_offset_x = (final_canvas_size[0] - bg_w) / 2
    bg_offset_y = (final_canvas_size[1] - bg_h) / 2

    final_button_surface.blit(background_surface, (bg_offset_x, bg_offset_y))

    # Layer 2 & 3: The stroke and border, centered on the final canvas
    border_offset_x = (final_canvas_size[0] - border_render_size[0]) / 2
    border_offset_y = (final_canvas_size[1] - border_render_size[1]) / 2
    final_button_surface.blit(stroke_surface, (border_offset_x, border_offset_y))
    final_button_surface.blit(textured_border, (border_offset_x, border_offset_y))

    return final_button_surface

def hexagonal_background_panel_helper(assets_state, corners, final_size):
    """
    Creates the base button surface using a pre-calculated hexagonal shape.
    """
    # Config & Dimensions
    BACKGROUND_COLOR = (45, 35, 30) # A dark, stony brown
    WATERMARK_ALPHA = 20

    #  grab final dimensions from ui_dimensions
    final_width, final_height = final_size

    # Create the Tiled Background Canvas
    texture_canvas = pygame.Surface((final_width, final_height))
    texture_canvas.fill(BACKGROUND_COLOR)
    
    watermark = assets_state["ui_assets"].get("stone_background_watermark")
    if watermark:
        watermark.set_alpha(WATERMARK_ALPHA)
        tex_w, tex_h = watermark.get_size()
        for x in range(0, int(final_width), tex_w):
            for y in range(0, int(final_height), tex_h):
                texture_canvas.blit(watermark, (x, y))

    # Stamp Out the Hexagonal Shape
    final_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)
    mask = pygame.Surface((final_width, final_height), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), corners)
    final_surface.blit(texture_canvas, (0, 0))
    final_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return final_surface

def _generate_procedural_border_lines(corners, assets_state, dims):
    """
    A consolidated function that handles the entire procedural border generation pipeline.
    """
    # ──────────────────────────────────────────────────
    # ⚙️ Step 1: Setup
    # ──────────────────────────────────────────────────
    
    # Get necessary values from assets and the dimensions dictionary
    border_pieces = assets_state["ui_assets"].get("stone_border_pieces", {})
    tile_dim = dims.get("stone_border_tile_dim", 12)
    inner_chaos_offset = dims.get("inner_line_max_chaos_offset", 4)
    
    # Define the constants for the final jagged effect
    INNER_CHAOS_NODES_LONG = (3, 5)
    INNER_CHAOS_NODES_SHORT = (1, 2)
    INNER_CHAOS_SCALE_FACTOR = 0.5

    # The starting point is the perfect hexagonal shape
    perfect_centerline = corners

    # ──────────────────────────────────────────────────
    # 🌀 Step 2: Create a Chaotic Centerline
    # ──────────────────────────────────────────────────
    
    # Create a wobbly version of the centerline by randomly offsetting each point.
    chaotic_centerline = []

    # ✨ FIX: Calculate the maximum chaos based on the border's thickness to create a safe zone.
    # The "action zone" for chaos is half the border's thickness.
    # We then apply our chaos factor to that zone.
    max_chaos_distance = (tile_dim / 2) * BUTTON_CORNER_CHAOS_FACTOR
    
    for point in perfect_centerline:
        random_angle = random.uniform(0, 2 * math.pi)
        chaos_distance = random.uniform(0, max_chaos_distance) # Randomize distance for more variation
        offset_x = math.cos(random_angle) * chaos_distance 
        offset_y = math.sin(random_angle) * chaos_distance 
        chaotic_centerline.append((point[0] + offset_x, point[1] + offset_y))

    # ──────────────────────────────────────────────────
    # ✨ Step 3: Create Parallel Inner & Outer Lines (Miter Join Method)
    # ──────────────────────────────────────────────────
    
    primed_inner_line = []
    final_outer_line = []
    offset_distance = tile_dim / 2
    
    # This new logic calculates the mitered offset for each vertex.
    num_points = len(chaotic_centerline)
    for i, point in enumerate(chaotic_centerline):
        # Get the previous and next points to determine the two connecting edges.
        prev_point = chaotic_centerline[(i - 1) % num_points]
        next_point = chaotic_centerline[(i + 1) % num_points]

        # --- Calculate the perpendicular for the incoming edge ---
        dx1, dy1 = point[0] - prev_point[0], point[1] - prev_point[1]
        mag1 = math.hypot(dx1, dy1)
        # The perpendicular vector pointing outwards for a clockwise polygon is (dy, -dx)
        perp1 = (dy1 / mag1, -dx1 / mag1) if mag1 > 0 else (0, 0)

        # --- Calculate the perpendicular for the outgoing edge ---
        dx2, dy2 = next_point[0] - point[0], next_point[1] - point[1]
        mag2 = math.hypot(dx2, dy2)
        perp2 = (dy2 / mag2, -dx2 / mag2) if mag2 > 0 else (0, 0)
        
        # --- Average the two perpendiculars to get the miter vector ---
        miter_vec_x = perp1[0] + perp2[0]
        miter_vec_y = perp1[1] + perp2[1]
        miter_mag = math.hypot(miter_vec_x, miter_vec_y)
        
        # Normalize the miter vector to get the final direction to push the point.
        if miter_mag > 0:
            # This check prevents sharp corners from becoming too long.
            # We adjust the offset distance based on the angle of the corner.
            dot_product = perp1[0] * perp2[0] + perp1[1] * perp2[1]
            miter_adjust = max(0.7, (1 + dot_product) / 2)
            adjusted_offset = offset_distance / miter_adjust

            unit_miter_x, unit_miter_y = miter_vec_x / miter_mag, miter_vec_y / miter_mag
        else:
            unit_miter_x, unit_miter_y = 0, 0
            adjusted_offset = offset_distance

        # Create the new inner and outer points by pushing along the miter vector.
        primed_inner_line.append((
            point[0] - unit_miter_x * adjusted_offset,
            point[1] - unit_miter_y * adjusted_offset
        ))
        final_outer_line.append((
            point[0] + unit_miter_x * adjusted_offset,
            point[1] + unit_miter_y * adjusted_offset
        ))

    # ──────────────────────────────────────────────────
    # ✨ Step 4: Add Final Jagged Variance to Inner Line
    # ──────────────────────────────────────────────────
    
    # Take the 'primed' inner line and add the final high-frequency chaos to its segments.
    final_jagged_inner_line = []
    num_points = len(primed_inner_line)
    for i in range(num_points):
        start_point = primed_inner_line[i]
        end_point = primed_inner_line[(i + 1) % num_points]
        is_long = i == 0 or i == 3

        # Determine number of new nodes to add
        if is_long:
            num_nodes = random.randint(*INNER_CHAOS_NODES_LONG)
        else:
            num_nodes = random.randint(*INNER_CHAOS_NODES_SHORT)
        
        interpolation_factors = sorted([random.random() for _ in range(num_nodes)])
        segment_points = [start_point]
        
        # Calculate max offset for this segment
        max_offset = inner_chaos_offset
        if not is_long:
            max_offset *= INNER_CHAOS_SCALE_FACTOR

        # Create and offset the new points
        for t in interpolation_factors:
            px = start_point[0] * (1 - t) + end_point[0] * t
            py = start_point[1] * (1 - t) + end_point[1] * t
            
            offset_dist = random.uniform(0, max_offset)
            random_ang = random.uniform(0, 2 * math.pi)
            ox = math.cos(random_ang) * offset_dist
            oy = math.sin(random_ang) * offset_dist
            
            segment_points.append((px + ox, py + oy))

        segment_points.append(end_point)
        final_jagged_inner_line.extend(segment_points[:-1])

    # ──────────────────────────────────────────────────
    # 📦 Return Finalized Set of Lines
    # ──────────────────────────────────────────────────
    
    return {
        "inner": final_jagged_inner_line,
        "center": perfect_centerline,
        "outer": final_outer_line
    }

