# ui_manager.py
# Handles the creation, management, and rendering of all UI elements.

import pygame
import os
import math

DEBUG = True

# ──────────────────────────────────────────────────
# 🖼️ Base Panel Class
# ──────────────────────────────────────────────────

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
# 🎨 UI Panel Helpers
# ──────────────────────────────────────────────────

def background_panel_helper(target_surface, assets_state):
    """Fills a surface with a solid color and a tiled watermark texture."""
    # Define background appearance
    BACKGROUND_COLOR = (20, 20, 20)
    WATERMARK_ALPHA = 10

    # Fill with the solid color
    target_surface.fill(BACKGROUND_COLOR)

    # Get the watermark texture
    watermark = assets_state["ui_assets"].get("background_watermark")
    if watermark:
        watermark.set_alpha(WATERMARK_ALPHA)
        tex_w, tex_h = watermark.get_size()
        # Tile the watermark across the entire surface
        for x in range(0, target_surface.get_width(), tex_w):
            for y in range(0, target_surface.get_height(), tex_h):
                target_surface.blit(watermark, (x, y))

def panel_border_helper(target_surface, assets_state):
    """
    Draws the seamless 9-slice border onto the target surface using a 
    repeating 3-tile pattern for each edge.
    """
    # 🎨 Asset & Dimension Setup
    border_pieces = assets_state["ui_assets"].get("border_pieces")
    if not border_pieces: return

    # Get dimensions and the size of a single tile
    panel_w, panel_h = target_surface.get_size()
    tile_step = border_pieces['1'].get_width()

    # Define the repeating tile sequences for each edge
    top_sequence = ['1', '2', '3']
    left_sequence = ['1', '4', '7']
    right_sequence = ['3', '6', '9']
    bottom_sequence = ['7', '8', '9']
    
    # ✍️ Border Drawing Logic
    # Draw Top & Bottom Edges
    # Iterate across the width of the panel, tile by tile.
    for x in range(0, panel_w, tile_step):
        # Determine which of the three tiles in the sequence to use
        tile_index = (x // tile_step) % 3
        
        # Blit the top edge tile
        top_tile_key = top_sequence[tile_index]
        target_surface.blit(border_pieces[top_tile_key], (x, 0))
        
        # Blit the bottom edge tile
        bottom_tile_key = bottom_sequence[tile_index]
        target_surface.blit(border_pieces[bottom_tile_key], (x, panel_h - tile_step))

    # Draw Left & Right Edges
    # Iterate down the height of the panel, tile by tile.
    # This loop re-blits the corners to keep the code clean and simple.
    for y in range(0, panel_h, tile_step):
        # Determine which of the three tiles in the sequence to use
        tile_index = (y // tile_step) % 3
        
        # Blit the left edge tile
        left_tile_key = left_sequence[tile_index]
        target_surface.blit(border_pieces[left_tile_key], (0, y))

        # Blit the right edge tile
        right_tile_key = right_sequence[tile_index]
        target_surface.blit(border_pieces[right_tile_key], (panel_w - tile_step, y))

def generate_undulating_poly(rect, segments_per_side, max_displacement):
    """
    Takes a pygame.Rect and returns a list of points for an undulating polygon.

    - rect: The base rectangle for the polygon.
    - segments_per_side: How many points to generate along each edge.
    - max_displacement: The maximum number of pixels a point can be shifted.
    """
    points = []
    
    # Use a shared random phase for all sides to create a continuous wave feel
    phase_x = random.uniform(0, 2 * math.pi)
    phase_y = random.uniform(0, 2 * math.pi)
    
    # 🏞️ Process Top, Right, Bottom, Left edges in order
    # Top Edge (Left to Right)
    for i in range(segments_per_side):
        t = i / segments_per_side
        x = rect.left + t * rect.width
        y = rect.top
        # Displace vertically (y-axis)
        displacement = max_displacement * math.sin(t * 3 * math.pi + phase_x)
        points.append((x, y + displacement))

    # Right Edge (Top to Bottom)
    for i in range(segments_per_side):
        t = i / segments_per_side
        x = rect.right
        y = rect.top + t * rect.height
        # Displace horizontally (x-axis)
        displacement = max_displacement * math.sin(t * 3 * math.pi + phase_y)
        points.append((x + displacement, y))

    # Bottom Edge (Right to Left)
    for i in range(segments_per_side):
        t = i / segments_per_side
        x = rect.right - t * rect.width
        y = rect.bottom
        # Displace vertically (y-axis)
        displacement = max_displacement * math.sin(t * 3 * math.pi + phase_x)
        points.append((x, y + displacement))

    # Left Edge (Bottom to Top)
    for i in range(segments_per_side):
        t = i / segments_per_side
        x = rect.left
        y = rect.bottom - t * rect.height
        # Displace horizontally (x-axis)
        displacement = max_displacement * math.sin(t * 3 * math.pi + phase_y)
        points.append((x + displacement, y))
        
    return points


def assemble_ui_panel(width, height, assets_state):
    """Orchestrator that builds and returns a complete UI panel surface."""
    border_pieces = assets_state["ui_assets"].get("border_pieces")
    if not border_pieces: 
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Get the tile size from the first piece.
    tile_step = border_pieces['1'].get_width()
    
    # The seamless pattern repeats every 3 tiles.
    pattern_size = tile_step * 3

    # Round the desired dimensions UP to the nearest multiple of the 3-tile pattern size.
    # This ensures the border always ends perfectly on tiles '3', '7', and '9'.
    final_width = math.ceil(width / pattern_size) * pattern_size
    final_height = math.ceil(height / pattern_size) * pattern_size
    
    # Ensure the final dimensions are at least one full pattern size.
    # This prevents a crash from pygame.Surface((0, N)) if the requested width/height is 0.
    if final_width == 0: final_width = pattern_size
    if final_height == 0: final_height = pattern_size

    # Create the final surface with the corrected dimensions.
    panel_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)

    # Call the helpers to draw the components onto the surface.
    background_panel_helper(panel_surface, assets_state)
    panel_border_helper(panel_surface, assets_state)

    return panel_surface

# ──────────────────────────────────────────────────
# 🧪 Test Panel Implementation
# ──────────────────────────────────────────────────

class TestPanel(BasePanel):
    """A specific panel that uses the assembly helpers to build itself."""
    def __init__(self, persistent_state, assets_state):
        super().__init__(persistent_state, assets_state)
        self.drawable_key = "ui_panel_test"

        # ⚙️ Define the panel's desired size and position
        desired_width = 350
        desired_height = 400
        
        # Call the orchestrator to get the final, correctly sized panel surface
        self.surface = assemble_ui_panel(desired_width, desired_height, assets_state)
        
        # Define the panel's screen position
        screen = self.persistent_state["pers_screen"]
        _, screen_height = screen.get_size()
        panel_x = 20
        panel_y = (screen_height - self.surface.get_height()) / 2
        self.rect = self.surface.get_rect(topleft=(panel_x, panel_y))

    def update(self, notebook):
        """Publishes the main panel and its border assets (for debugging) to the notebook."""
        # First, publish the main panel as usual
        if self.surface and self.rect and self.drawable_key:
            z_formula = self.persistent_state["pers_z_formulas"]["ui_panel"]
            notebook[self.drawable_key] = {
                "type": "ui_panel",
                "surface": self.surface,
                "rect": self.rect,
                "z": z_formula(0)
            }

        # 🐞 Blit individual border assets next to the panel for debugging
        border_pieces = self.assets_state["ui_assets"].get("border_pieces")
        if DEBUG and border_pieces:
            # Get the z-value for UI elements so they draw on top
            z_value = self.persistent_state["pers_z_formulas"]["ui_panel"](0) + 0.1
            
            # Define a starting position for our debug grid (to the right of the panel)
            start_x = self.rect.right + 20
            current_x = start_x
            current_y = self.rect.top
            
            # Loop through each of the 8 border pieces
            for name, piece_surface in border_pieces.items():
                # Create a unique key for the notebook
                debug_key = f"debug_border_{name}"
                piece_rect = piece_surface.get_rect(topleft=(current_x, current_y))
                
                # Add the piece to the notebook to be drawn by the renderer
                notebook[debug_key] = {
                    "type": "ui_panel", # Reuse the existing ui_panel interpreter
                    "surface": piece_surface,
                    "rect": piece_rect,
                    "z": z_value
                }
                
                # Move to the next position in our grid
                current_x += piece_surface.get_width() + 5
                # Wrap to the next row if we go too far across the screen
                if current_x > start_x + 100:
                    current_x = start_x
                    current_y += piece_surface.get_height() + 5

# ──────────────────────────────────────────────────
# ⚙️ UI Orchestrator
# ──────────────────────────────────────────────────

class UIManager:
    """Orchestrates all UI components."""
    def __init__(self, persistent_state, assets_state):
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.panels = {}

        # Create and store an instance of our test panel
        self.panels["test_panel"] = TestPanel(persistent_state, assets_state)
        if DEBUG:
            print(f"[UIManager] ✅ Test panel class instantiated.")

    def update(self, notebook):
        """Updates all active panels, causing them to publish to the notebook."""
        for panel in self.panels.values():
            panel.update(notebook)


