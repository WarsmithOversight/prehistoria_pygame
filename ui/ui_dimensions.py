# ui/ui_dimensions.py
# A centralized module for calculating all complex UI geometry.

import pygame
from load_assets import get_font

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────
DEBUG = True

TEXT_PADDING = (10, 10)
NEW_CORNER_OFFSET = 15
BUTTON_CORNER_CHAOS_FACTOR = 3
UI_ELEMENT_PADDING = (20, 20)
INNER_CHAOS_OFFSET_DIVISOR = 2

def get_panel_dimensions(element_definitions, layout_blueprint, assets_state):
    """
    Calculates all necessary dimensions for a complex procedural UI panel and its elements.
    This is the single source of truth for UI layout geometry.
    """
    dims = {}
    dims['element_dims'] = {} # To store the final size of each individual element

    # ──────────────────────────────────────────────────
    # 📏 1. Calculate the size of each individual element
    # ──────────────────────────────────────────────────
    max_element_width = 0
    total_content_height = 0

    # ✨ NEW: First, find the max text size for ALL buttons in this panel
    max_button_text_w, max_button_text_h = 0, 0
    for item_id, element_def in element_definitions.items():
        if element_def.get("type") == "button":

            # ✨ FIX: Use the new centralized get_font function.
            font = get_font(element_def["style"]["font_size_key"])
            for text in element_def["text_options"]:
                w, h = font.size(text)
                if w > max_button_text_w: max_button_text_w = w
                if h > max_button_text_h: max_button_text_h = h
 
    # ✨ NEW: Now, calculate the single, uniform button geometry ONCE
    if max_button_text_w > 0:
        stone_pieces = assets_state["ui_assets"].get("stone_border_pieces", {})
        tile_dim = stone_pieces['1'].get_width() if stone_pieces else 12
        dims["stone_border_tile_dim"] = tile_dim # ✨ FIX: Store the correct border width for the renderer.
        chaos_offset = tile_dim / INNER_CHAOS_OFFSET_DIVISOR
        padded_w = max_button_text_w + (TEXT_PADDING[0] * 2) + (chaos_offset * 2)
        padded_h = max_button_text_h + (TEXT_PADDING[1] * 2) + (chaos_offset * 2)
        hex_bg_w = padded_w + (2 * NEW_CORNER_OFFSET)
        hex_bg_h = padded_h
        final_w = hex_bg_w + tile_dim + (BUTTON_CORNER_CHAOS_FACTOR * 2)
        final_h = hex_bg_h + tile_dim + (BUTTON_CORNER_CHAOS_FACTOR * 2)
        
        # Store this uniform geometry in the main dims dict for all buttons to use
        dims["uniform_button_final_size"] = (final_w, final_h)
        dims["hexagonal_background_size"] = (hex_bg_w, hex_bg_h)
        dims["hexagonal_corner_points"] = [
            (NEW_CORNER_OFFSET, 0), (NEW_CORNER_OFFSET + padded_w, 0),
            (hex_bg_w, hex_bg_h / 2), (NEW_CORNER_OFFSET + padded_w, hex_bg_h),
            (NEW_CORNER_OFFSET, hex_bg_h), (0, hex_bg_h / 2)]

    for i, item in enumerate(layout_blueprint):
        item_id = item.get("id")
        if not item_id: continue
        
        element_def = element_definitions.get(item_id)
        if not element_def: continue

        # --- Calculate Button Dimensions ---
        if element_def.get("type") == "button":

            # All buttons now use the same, pre-calculated uniform size
            final_w, final_h = dims["uniform_button_final_size"]
            dims['element_dims'][item_id] = {"final_size": (final_w, final_h)}

            if final_w > max_element_width: max_element_width = final_w
            total_content_height += final_h

        # --- Calculate Text Block Dimensions ---
        elif element_def.get("type") == "text_block":
            max_width = element_def["properties"]["max_width"]

            # ✨ FIX: Use the new centralized get_font function.
            font = get_font(element_def["style"]['font_size_key'])

            final_height = _calculate_wrapped_text_height(element_def["content"], font, max_width)            
            dims['element_dims'][item_id] = {"final_size": (max_width, final_height)}
            if max_width > max_element_width: max_element_width = max_width
            total_content_height += final_height

    # ──────────────────────────────────────────────────
    # 🖼️ 2. Calculate Overall Panel Size
    # ──────────────────────────────────────────────────
    bark_pieces = assets_state["ui_assets"].get("bark_border_pieces", {})
    dims["bark_border_tile_dim"] = bark_pieces['1'].get_width() if bark_pieces else 12
    
    pad_x, pad_y = UI_ELEMENT_PADDING
    
    # The final content size is based on the elements we just measured
    panel_content_w = int(max_element_width + (pad_x * 2))
    panel_content_h = int(total_content_height + ((len(layout_blueprint) + 1) * pad_y))
    dims["panel_background_size"] = (panel_content_w, panel_content_h)

    # The total panel size includes the decorative border
    final_panel_w = panel_content_w + dims["bark_border_tile_dim"]
    final_panel_h = panel_content_h + dims["bark_border_tile_dim"]
    dims["final_panel_size"] = (final_panel_w, final_panel_h)

    if DEBUG:
        print(f"[ui_dimensions] ✅ Dimensions calculated.")
    return dims

def _calculate_wrapped_text_height(text, font, max_width):
    """A helper function to calculate the total height of wrapped text."""
    lines = []
    paragraphs = text.split('\n')
    for para in paragraphs:
        if not para:
            lines.append("")
            continue
        words = para.split(' ')
        current_line_words = []
        for word in words:
            current_line_words.append(word)
            line_text = ' '.join(current_line_words)
            line_width, _ = font.size(line_text)
            if line_width > max_width:
                word_that_didnt_fit = current_line_words.pop()
                final_line_text = ' '.join(current_line_words)
                lines.append(final_line_text)
                current_line_words = [word_that_didnt_fit]
        if current_line_words:
            lines.append(' '.join(current_line_words))
    return len(lines) * font.get_linesize()