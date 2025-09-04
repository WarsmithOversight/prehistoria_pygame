# ui_components.py
# stores dependancies from ui panels

import random, math, pygame
from .ui_dimensions import UI_ELEMENT_PADDING, BUTTON_CORNER_CHAOS_FACTOR, _calculate_wrapped_text_height
from load_assets import get_font

DEBUG = True

def create_procedural_rectangular_glow(size, color):
    """
    Creates a high-quality, soft "spill" of light by simulating a blur effect.
    This mimics the glow style of cards from games like Hearthstone.
    """
    # 🎨 Config: Control the glow's appearance here
    width, height = size
    GLOW_PADDING = 25  # How far the glow should spill from the edges
    BLUR_PASSES = 6      # How soft/blurry the glow is. More passes = softer.
    MAX_ALPHA = 200      # The brightness of the glow's core.

    # 🖼️ Create the final surface, larger than the card to contain the spill
    padded_size = (width + GLOW_PADDING * 2, height + GLOW_PADDING * 2)
    glow_surface = pygame.Surface(padded_size, pygame.SRCALPHA)

    # 1. ✍️ Draw the initial solid shape of the card in the center of our surface.
    # This will be the "light source" that we blur.
    card_shape_rect = pygame.Rect(GLOW_PADDING, GLOW_PADDING, width, height)
    pygame.draw.rect(glow_surface, (*color, MAX_ALPHA), card_shape_rect, 0, border_radius=12)

    # 2. ✨ Simulate the blur effect.
    # We repeatedly scale the image down and then back up. The smoothscale
    # algorithm's interpolation naturally blurs the edges with each pass.
    for i in range(BLUR_PASSES):
        # Scale down to half size, creating a blur
        scaled_down = pygame.transform.smoothscale(glow_surface, (padded_size[0] // 2, padded_size[1] // 2))
        # Scale back up to original size, enhancing the blur
        glow_surface = pygame.transform.smoothscale(scaled_down, padded_size)

    # 3. (Optional) Add a slightly brighter "core" to make the edge pop.
    # This helps define the card shape within the soft glow.
    pygame.draw.rect(glow_surface, (*color, 50), card_shape_rect, 2, border_radius=10)

    # --- 4. Create a "Stamp" to Punch a Hole in the Center ---
    mask = pygame.Surface(padded_size, pygame.SRCALPHA)
    mask.fill((255, 255, 255, 255)) # Start with a fully opaque (white) mask

    base_rect = pygame.Rect(GLOW_PADDING, GLOW_PADDING, width, height)

    # 🎨 Control the size of the transparent stamp here.
    # A negative number makes the hole LARGER than the card, creating a margin.
    STAMP_INSET = -4

    # Create the feathered hole by drawing a solid black rect in the middle,
    # slightly smaller than the card's shape to create a soft inner edge.
    FEATHER = 4
    hole_rect = base_rect.inflate(STAMP_INSET * 2, STAMP_INSET * 2)
    pygame.draw.rect(mask, (0, 0, 0, 255), hole_rect, 0, border_radius=8)

    # Blur the mask to create the soft, feathered edge for our stamp.
    for i in range(FEATHER):
        mask = pygame.transform.smoothscale(pygame.transform.smoothscale(mask, (padded_size[0]//2, padded_size[1]//2)), padded_size)

    # Apply the mask to the glow surface using multiplicative blending.
    glow_surface.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)

    return glow_surface

class Button:
    """A generic, stateful UI button that caches its base and composites on the fly."""
    def __init__(self, rect, text, assets_state, style, dims, callback):
        self.rect = rect
        self.callback = callback
        self.assets_state = assets_state
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

    def draw(self, surface):
        """Draws the cached base and the current text surface separately."""
        surface.blit(self.base_surface, self.rect.topleft)
        surface.blit(self.text_surface, (self.rect.left + self.text_rect.left, self.rect.top + self.text_rect.top))

class UITextBlock:
    """A UI component for displaying potentially multi-line, wrapped text."""
    def __init__(self, rect, text, style, assets_state):
        self.rect = rect
        self.text = text
        self.style = style
        self.assets_state = assets_state

        # ✨ FIX: Get the font from the central cache in the assets module.
        font_key = self.style.get("font_size_key", "regular_medium")
        self.font = get_font(font_key)
        self.text_color = self.style.get('text_color', (255, 220, 220))
        self.line_height = self.font.get_linesize()

        # 🏞️ Perform the wrapping calculation once and cache the resulting line data.
        self.line_data = self._wrap_text()

    def _wrap_text(self):
        """
        Performs word-by-word wrapping and identifies the last line of each paragraph.
        Returns a list of dictionaries, e.g., [{'text': '...', 'is_last_in_para': False}]
        """

        line_data = []
        paragraphs = self.text.split('\n')
        for para in paragraphs:
            if not para:
                # Add empty lines as the end of their own "paragraph"
                line_data.append({'text': '', 'is_last_in_para': True})
                continue
            words = para.split(' ')
            current_line_words = []
            for word in words:
                current_line_words.append(word)
                line_text = ' '.join(current_line_words)
                line_width, _ = self.font.size(line_text)

                if line_width > self.rect.width:
                    word_that_didnt_fit = current_line_words.pop()

                    # This line is full, so it's not the last in the paragraph (unless it's a 1-word line).
                    line_data.append({'text': ' '.join(current_line_words), 'is_last_in_para': False})
                    current_line_words = [word_that_didnt_fit]

            if current_line_words:

                # This is the last line of the current paragraph.
                line_data.append({'text': ' '.join(current_line_words), 'is_last_in_para': True})
        
        return line_data

    def get_total_height(self):
        """Calculates the final height of the text block after wrapping."""
        return len(self.line_data) * self.line_height

    def draw(self, surface):
        """
        Draws the text onto the target surface, handling alignment and justification.
        """
        align = self.style.get('align', 'left')
        
        # ✨ FIX: Define a background color to force Pygame's "solid" rendering path,
        # which often fixes anti-aliasing bugs on certain systems.
        BG_COLOR = (20, 20, 20)

        current_y = self.rect.top

        for line_info in self.line_data:
            line_text = line_info['text']
            is_last_in_para = line_info['is_last_in_para']

            if not line_text: # Skip rendering for empty lines, but advance y
                current_y += self.line_height
                continue

            if align == 'justify' and not is_last_in_para:
                words = line_text.split(' ')
                if len(words) <= 1:
                    # Not enough words to justify, treat as left-aligned
                    line_surface = self.font.render(line_text, True, self.text_color, BG_COLOR)
                    line_surface.set_colorkey(BG_COLOR)
                else:
                    # Calculate the width of words and the space needed
                    words_width = sum(self.font.size(w)[0] for w in words)
                    total_space_needed = self.rect.width - words_width
                    space_per_gap = total_space_needed / (len(words) - 1)

                    # Draw word by word with calculated spacing
                    current_x = self.rect.left
                    for word in words:
                        word_surface = self.font.render(word, True, self.text_color, BG_COLOR)
                        word_surface.set_colorkey(BG_COLOR)
                        surface.blit(word_surface, (current_x, current_y))
                        current_x += word_surface.get_width() + space_per_gap
            
            # Standard alignment logic (also handles the last line of justified text)
            else:
                line_surface = self.font.render(line_text, True, self.text_color, BG_COLOR)
                line_surface.set_colorkey(BG_COLOR)
                if align == 'center':
                    x = self.rect.centerx - (line_surface.get_width() / 2)
                elif align == 'right':
                    x = self.rect.right - line_surface.get_width()
                else: # Default to 'left'
                    x = self.rect.left
                surface.blit(line_surface, (x, current_y))
            
            current_y += self.line_height

class UIStaticImage:
    """A simple component that just draws a pre-rendered surface."""
    def __init__(self, rect, surface):
        self.rect = rect
        self.surface = surface

    def draw(self, target_surface):
        """Draws the static image onto the target surface."""
        if self.surface:
            target_surface.blit(self.surface, self.rect.topleft)

class UICard:
    """
    A composite UI component that displays formatted text and handles interactive
    states like a button (glowing, clicking).
    """
    def __init__(self, rect, card_data, assets_state, event_bus):
        # ⚙️ Core Attributes
        self.rect = rect
        self.card_data = card_data
        self.assets_state = assets_state
        self.event_bus = event_bus

        # 🚩 State Management
        self.is_glowing = False
        self._is_pressed = False

        # 👶 Child Components: Contains a UITextBlock to render the text.
        text_rect = pygame.Rect(0, 0, rect.width, rect.height)
        text_style = {"font_size_key": "regular_medium", "text_color": (255, 220, 200), "align": "center"}
        card_text = (
            f"{self.card_data['name']}\n"
            f"{self.card_data['type']}\n"
            f"{self.card_data['difficulty']}"
        )
        self.text_block = UITextBlock(rect=text_rect, text=card_text, style=text_style, assets_state=self.assets_state)

        # ✨ NEW: Create and cache a custom, procedural glow surface for this card.
        self.cached_glow_surface = create_procedural_rectangular_glow(
            size=self.rect.size,
            color=(0, 180, 255) # A nice magic blue
        )

    def set_glow(self, is_glowing):
        """Externally sets the glowing state of the card."""
        self.is_glowing = is_glowing

    def handle_events(self, events, mouse_pos):
        """Handles mouse input to detect clicks, just like a button."""
        is_hovering = self.rect.collidepoint(mouse_pos)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and is_hovering:
                self._is_pressed = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._is_pressed and is_hovering:
                    # When clicked, post an event with this card's data.
                    self.event_bus.post("UI_CARD_CLICKED", self.card_data)
                    if DEBUG: print(f"[UICard] ✅ Clicked card: {self.card_data['id']}")
                self._is_pressed = False

    def draw(self, surface):
        """Draws the card's text and, if glowing, a surrounding glow effect."""
        # 1. ✍️ Always create the text content on its own surface first.
        # This surface is the exact size of the card's logical rectangle.
        text_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.text_block.draw(text_surface)
 
        # ✨ If the card is glowing, draw the pre-rendered procedural glow first.
        if self.is_glowing and self.cached_glow_surface:
            # The glow surface is larger than the card, so we need to offset it.
            glow_w, glow_h = self.cached_glow_surface.get_size()
            offset_x = (self.rect.width - glow_w) / 2
            offset_y = (self.rect.height - glow_h) / 2
            blit_pos = (self.rect.left + offset_x, self.rect.top + offset_y)
            
            # 🎨 Draw the glow. The ADD blend mode creates a nice lighting effect.
            surface.blit(self.cached_glow_surface, blit_pos, special_flags=pygame.BLEND_RGBA_ADD)

        # ✍️ Always draw the text on top of everything else.
        surface.blit(text_surface, self.rect.topleft)

# 
# ✨ FIX: The following classes and functions were nested inside UICard.
# They have been un-indented to be at the top level of the module.
#

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

    def destroy(self, notebook):
        """Removes the panel's drawable from the notebook, effectively hiding it."""
        if self.drawable_key and self.drawable_key in notebook:
            del notebook[self.drawable_key]
        if DEBUG: print(f"[BasePanel] ✅ Destroyed drawable: '{self.drawable_key}'")

'''
ui_components.py - A Toolbox for Procedural UI Elements
=========================================================

This file acts as a "factory" for creating visual UI components. It does not
decide layout, dimensions, or positioning; it simply builds the components
based on instructions it receives.

Function Call Hierarchy (A Bird's-Eye View):
----------------------------------------------

## How a Panel is Built 🖼️ ##

1.  Create the Background: 
        A dark, textured canvas is created first. 
        This serves as the backing for the frame.
2.  Cut the Wood: 
        Four straight, textured "planks" are made for the 
        top, bottom, left, and right sides.
3.  Carve the Squiggles: 
        The inner edge of each plank is "carved" with
        a wavy, organic line, making it look natural and hand-hewn.
4.  Assemble the Frame: 
        The four wavy planks are arranged into a rectangle.
5.  Round the Corners: 
        The sharp corners of the assembled frame are then 
        carved into smooth, rounded joints, seamlessly connecting the edges.
6.  Final Assembly: 
        The finished, carved frame is placed on top of the 
        background canvas to create the complete panel.

## How a Button is Built 🔘 ##

1.  Carve the Stone Core: 
        A solid hexagonal shape with a stony texture 
        is carved out. This is the base of the button.
2.  Define the Border:
        A path is drawn around the hexagon to mark where 
        the border will be.
3.  Chip the Edges: 
        This path is then made jagged and chaotic, as if 
        the edges of the stone have been naturally weathered.
4.  Create the Border Piece: 
        A separate stone texture is "stamped out" 
        using this jagged, chipped path, creating a rough, aged border.
5.  Final Assembly:
        The finished, chipped border is placed on top of 
        the hexagonal stone core.
6.  Add the Inscription:
        Finally, the button's text is rendered and placed 
        in the center.
'''

def _generate_button_base_surface(assets_state, dims):
    """
    Generates only the static, procedural parts of the button (background and border).
    This is the slow part that we want to cache.
    """
    corners = dims["hexagonal_corner_points"]
    final_size = dims["hexagonal_background_size"]
    
    border_lines = _generate_procedural_border_lines(corners, assets_state, dims)
    background_surface = hexagonal_background_panel_helper(assets_state, corners, final_size)

    min_x = min(p[0] for p in border_lines["outer"])
    max_x = max(p[0] for p in border_lines["outer"])
    min_y = min(p[1] for p in border_lines["outer"])
    max_y = max(p[1] for p in border_lines["outer"])
    border_width, border_height = max_x - min_x, max_y - min_y

    border_surface = pygame.Surface((border_width, border_height), pygame.SRCALPHA)
    
    offset = (-min_x, -min_y)
    translated_outer = [(p[0] + offset[0], p[1] + offset[1]) for p in border_lines["outer"]]
    translated_inner = [(p[0] + offset[0], p[1] + offset[1]) for p in border_lines["inner"]]

    border_pieces = assets_state["ui_assets"].get("stone_border_pieces", {})
    if border_pieces:
        tile_dim = border_pieces['1'].get_width()
        master_tile = pygame.Surface((tile_dim * 3, tile_dim * 3))
        for r in range(3):
            for c in range(3):
                master_tile.blit(border_pieces[str(r*3+c+1)], (c*tile_dim, r*tile_dim))
        
        tex_w, tex_h = master_tile.get_size()
        for x in range(0, int(border_width), tex_w):
            for y in range(0, int(border_height), tex_h):
                border_surface.blit(master_tile, (x, y))

    mask = pygame.Surface((border_width, border_height), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), translated_outer)
    pygame.draw.polygon(mask, (0, 0, 0, 0), translated_inner)
    border_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    final_button_surface = pygame.Surface((border_width, border_height), pygame.SRCALPHA)
    
    bg_offset_x = (border_width - final_size[0]) / 2
    bg_offset_y = (border_height - final_size[1]) / 2
    final_button_surface.blit(background_surface, (bg_offset_x, bg_offset_y))
    final_button_surface.blit(border_surface, (0, 0))
    
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
    chaos_distance = BUTTON_CORNER_CHAOS_FACTOR
    
    for point in perfect_centerline:
        random_angle = random.uniform(0, 2 * math.pi)
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

# ──────────────────────────────────────────────────
# Panel Generation
# ──────────────────────────────────────────────────


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
    SAFE_ZONE_RATIO = 1 / 2
    
    # Of the remaining "action zone," how much amplitude belongs to the main wave (e.g., 0.8 = 80%).
    PRIMARY_WAVE_RATIO = 0.9
    
    # How many tile widths it takes for one main "swoop" to complete.
    PRIMARY_WAVELENGTH_IN_TILES = 15
    
    # How many smaller swoops appear on top of each main swoop.
    SECONDARY_SWOOPS_PER_PRIMARY = 3
    
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