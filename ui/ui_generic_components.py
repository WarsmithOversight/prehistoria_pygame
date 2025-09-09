# ui.ui_generic_components.py
# stores dependancies from ui panels

import pygame
from ui.ui_font_and_styles import get_font

DEBUG = True

# def create_procedural_rectangular_glow(size, color):
#     """
#     Creates a high-quality, soft "spill" of light by simulating a blur effect.
#     This mimics the glow style of cards from games like Hearthstone.
#     """
#     # 🎨 Config: Control the glow's appearance here
#     width, height = size
#     GLOW_PADDING = 40  # How far the glow should spill from the edges
#     BLUR_PASSES = 7      # How soft/blurry the glow is. More passes = softer.
#     MAX_ALPHA = 200      # The brightness of the glow's core.

#     # 🖼️ Create the final surface, larger than the card to contain the spill
#     padded_size = (width + GLOW_PADDING * 2, height + GLOW_PADDING * 2)
#     glow_surface = pygame.Surface(padded_size, pygame.SRCALPHA)

#     # 1. ✍️ Draw the initial solid shape of the card in the center of our surface.
#     # This will be the "light source" that we blur.
#     card_shape_rect = pygame.Rect(GLOW_PADDING, GLOW_PADDING, width, height)
#     pygame.draw.rect(glow_surface, (*color, MAX_ALPHA), card_shape_rect, 0, border_radius=12)

#     # 2. ✨ Simulate the blur effect.
#     # We repeatedly scale the image down and then back up. The smoothscale
#     # algorithm's interpolation naturally blurs the edges with each pass.
#     for i in range(BLUR_PASSES):
#         # Scale down to half size, creating a blur
#         scaled_down = pygame.transform.smoothscale(glow_surface, (padded_size[0] // 2, padded_size[1] // 2))
#         # Scale back up to original size, enhancing the blur
#         glow_surface = pygame.transform.smoothscale(scaled_down, padded_size)

#     # 3. (Optional) Add a slightly brighter "core" to make the edge pop.
#     # This helps define the card shape within the soft glow.
#     pygame.draw.rect(glow_surface, (*color, 50), card_shape_rect, 2, border_radius=10)

#     # --- 4. Create a "Stamp" to Punch a Hole in the Center ---
#     mask = pygame.Surface(padded_size, pygame.SRCALPHA)
#     mask.fill((255, 255, 255, 255)) # Start with a fully opaque (white) mask

#     base_rect = pygame.Rect(GLOW_PADDING, GLOW_PADDING, width, height)

#     # 🎨 Control the size of the transparent stamp here.
#     # A positive value makes the hole SMALLER, creating a feathered inner glow.
#     STAMP_INSET = 2        # ✨ FIX: A tiny inset to create a soft overlap with the card edge.
#     # Create the feathered hole by drawing a solid black rect in the middle.
#     FEATHER = 2            # ✨ FIX: Reduced feathering on the hole-punch mask to preserve more glow.

#     # Use a negative value with inflate() to shrink the rectangle from its base size.
#     hole_rect = base_rect.inflate(-STAMP_INSET * 2, -STAMP_INSET * 2)
#     pygame.draw.rect(mask, (0, 0, 0, 255), hole_rect, 0, border_radius=8)

#     # Blur the mask to create the soft, feathered edge for our stamp.
#     for i in range(FEATHER):
#         mask = pygame.transform.smoothscale(pygame.transform.smoothscale(mask, (padded_size[0]//2, padded_size[1]//2)), padded_size)

#     # Apply the mask to the glow surface using multiplicative blending.
#     glow_surface.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)

#     return glow_surface

class UITextBlock:
    """A UI component for displaying potentially multi-line, wrapped text."""
    def __init__(self, rect, line_data, style, assets_state):
        self.rect = rect
        self.style = style
        self.assets_state = assets_state
        self.is_visible = True
        # ✨ Get the font from our new, centralized font system.
        self.font = get_font(self.style.get("font_size_key", "regular_14"))
        self.text_color = self.style.get('text_color', (255, 220, 220))
        self.line_height = self.font.get_linesize()
        self.line_data = line_data # ✨ No longer calculates its own wrapping

    def get_total_height(self):
        """Calculates the final height of the text block after wrapping."""
        return len(self.line_data) * self.line_height

    def draw(self, surface, offset=(0, 0)):
        """
        Draws the text onto the target surface, handling alignment and justification.
        """
        if not self.is_visible: return
        align = self.style.get('align', 'left')
        
        # 📝 NOTE: The process of rendering to a solid background and then setting a
        # colorkey is a required workaround. It forces Pygame's 'solid' rendering
        # path, which produces much higher-quality anti-aliasing for this font.
        BG_COLOR = (20, 20, 20)

        current_y = self.rect.top + offset[1]

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
                    current_x = self.rect.left + offset[0]
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
                    x = self.rect.centerx - (line_surface.get_width() / 2) + offset[0]
                elif align == 'right':
                    x = self.rect.right - line_surface.get_width() + offset[0]
                else: # Default to 'left'
                    x = self.rect.left + offset[0]
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