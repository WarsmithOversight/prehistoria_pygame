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

def get_panel_dimensions(panel_id, element_definitions, layout_blueprint, assets_state):
    """
    Calculates all necessary dimensions for a complex procedural UI panel and its elements.
    This is the single source of truth for UI layout geometry.
    """
    dims = {}
    dims['row_widths'] = []    # To store the calculated width of each row
    dims['row_heights'] = []   # To store the calculated height of each row

    # ──────────────────────────────────────────────────
    # 📏 1. Calculate the size of each individual element
    # ──────────────────────────────────────────────────

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

    # ✨ REFACTORED: Now, loop through the definitions to store each element's final size.
    dims['element_dims'] = {}
    for item_id, element_def in element_definitions.items():
        if element_def.get("type") == "button":
            # All buttons use the same, pre-calculated uniform size.
            final_w, final_h = dims["uniform_button_final_size"]
            dims['element_dims'][item_id] = {"final_size": (final_w, final_h)}
 
        elif element_def.get("type") == "text_block":
            max_width = element_def["properties"]["max_width"]
            font = get_font(element_def["style"]['font_size_key'])
            final_height = _calculate_wrapped_text_height(element_def["content"], font, max_width)
            dims['element_dims'][item_id] = {"final_size": (max_width, final_height)}
 
        elif element_def.get("type") == "static_image":
            size = element_def["properties"]["size"]
            dims['element_dims'][item_id] = {"final_size": size}

# ──────────────────────────────────────────────────
    # 🖼️ 2. Process Layout Blueprint to Calculate Row and Panel Sizes
    # ──────────────────────────────────────────────────    
    pad_x, pad_y = UI_ELEMENT_PADDING

    # ┌──────────────────────────────────────────────┐
    # │   Step 2A: Measure the Raw Content Area      │
    # └──────────────────────────────────────────────┘
    # First, we loop through the blueprint to measure the total dimensions
    # of the UI elements themselves, without any outer panel padding.
    max_content_width = 0
    total_content_height = 0

    for row_items in layout_blueprint:
        # For backward compatibility, treat a single dict as a row with one item.
        if not isinstance(row_items, list):
            row_items = [row_items]
 
        current_row_width = 0
        max_row_height = 0
 
        # Calculate the total width of all elements in this row.
        # Find the height of the tallest element, which defines the row's height.
        for item in row_items:
            item_id = item.get("id")
            if not item_id: continue
            
            elem_w, elem_h = dims['element_dims'][item_id]["final_size"]
            current_row_width += elem_w
            if elem_h > max_row_height:
                max_row_height = elem_h
 
        # Add the horizontal padding *between* the elements in the row.
        if len(row_items) > 1:
            current_row_width += pad_x * (len(row_items) - 1)
 
        # Store this row's final dimensions for the placement method to use later.
        dims['row_widths'].append(current_row_width)
        dims['row_heights'].append(max_row_height)
 
        # Check if this is the widest row we've seen so far.
        if current_row_width > max_content_width:
            max_content_width = current_row_width
        
        # Add the tallest element's height to the total content height.
        total_content_height += max_row_height

    # Add the vertical padding *between* the rows.
    if len(layout_blueprint) > 1:
        total_content_height += pad_y * (len(layout_blueprint) - 1)

    # ┌──────────────────────────────────────────────┐
    # │   Step 2B: Calculate Padded Background Size  │
    # └──────────────────────────────────────────────┘
    # Now, add the outer padding around the raw content to get the size
    # of the dark, textured background area.
    panel_background_w = int(max_content_width + (pad_x * 2))
    panel_background_h = int(total_content_height + (pad_y * 2))
    dims["panel_background_size"] = (panel_background_w, panel_background_h)

    # ┌──────────────────────────────────────────────┐
    # │   Step 2C: Calculate Final Panel with Border │
    # └──────────────────────────────────────────────┘
    # Finally, add the width of the decorative bark border to get the
    # absolute final dimensions for the entire panel surface.
    bark_pieces = assets_state["ui_assets"].get("bark_border_pieces", {})
    border_dim = bark_pieces['1'].get_width() if bark_pieces else 12
    dims["bark_border_tile_dim"] = border_dim
    
    final_panel_w = panel_background_w + border_dim
    final_panel_h = panel_background_h + border_dim
    dims["final_panel_size"] = (final_panel_w, final_panel_h)
    
    # 🔊 Print a dynamic success message with useful dev info.
    if DEBUG:
        print(f"[ui_dimensions] ✅ Dimensions for '{panel_id}' panel ({len(layout_blueprint)} elements) calculated. Final size: {final_panel_w}x{final_panel_h}.")
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