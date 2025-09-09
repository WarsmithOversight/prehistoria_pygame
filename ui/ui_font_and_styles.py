# ui/ui_font_and_styles.py
# The single source of truth for all font loading and UI text styles.

import pygame

DEBUG = True

# ──────────────────────────────────────────────────
#  Font Loading & Caching
# ──────────────────────────────────────────────────

_FONT_CACHE = {}
# ✨ GOAL 1: Update the default font key to use a specific point size.
_DEFAULT_FONT_KEY = "regular_14"

def initialize_font_cache():
    """Loads all predefined fonts into the central cache. Call this once on startup."""
    font_configs = {
        "styles": {
            "regular": "fonts/static/NotoSans-Regular.ttf",
            "bold": "fonts/static/NotoSans-Bold.ttf"
        },
        # ✨ GOAL 1: Define a range of exact point sizes instead of named sizes.
        "sizes": range(10, 21) # Loads fonts from 10pt to 20pt
    }
    for style_name, font_path in font_configs["styles"].items():
        for size_pixels in font_configs["sizes"]:
            # ✨ GOAL 1: The new key is based on the pixel size, e.g., "regular_14"
            font_key = f"{style_name}_{size_pixels}"
            try:
                _FONT_CACHE[font_key] = pygame.font.Font(font_path, size_pixels)
            except pygame.error:
                if DEBUG: print(f"[assets] ❌ FONT ERROR: Could not load '{font_path}'. Key '{font_key}' is unavailable.")
    if DEBUG: print(f"[assets] ✅ {len(_FONT_CACHE)} fonts loaded into cache.")

def get_font(key="regular_14"):
    """Retrieves a font from the cache, falling back to the default if not found."""
    font = _FONT_CACHE.get(key)
    if not font and DEBUG: print(f"[assets] ⚠️ Font key '{key}' not found. Falling back to default.")
    return font or _FONT_CACHE.get(_DEFAULT_FONT_KEY)

# ──────────────────────────────────────────────────
# 🎨 Style Definitions
# ──────────────────────────────────────────────────

UI_STYLES = {
    # ✨ GOAL 2: Create more specific, component-based style names.
    
    # --- Generic & Shared Styles ---
    "paragraph_text": {"font_size_key": "regular_14", "text_color": (220, 220, 220), "align": "justify"},
    "panel_title":      {"font_size_key": "bold_18",   "text_color": (255, 220, 180), "align": "center"},
    "button_primary":   {"font_size_key": "regular_16", "text_color": (255, 220, 200), "align": "center"},
    "button_disabled":  {"font_size_key": "regular_16", "text_color": (150, 150, 150), "align": "center"},

    # --- Migration Event Panel ---
    "migration_event_active":    {"font_size_key": "regular_14", "text_color": (200, 200, 200), "align": "left"},
    "migration_event_muted":     {"font_size_key": "regular_14", "text_color": (100, 100, 100), "align": "left"},

    # --- Hazard Card ---
    "hazard_card_name":       {"font_size_key": "regular_16", "text_color": (220, 220, 220)},
    "hazard_card_body":       {"font_size_key": "regular_12", "text_color": (200, 200, 200)},
    "hazard_card_subtype":    {"font_size_key": "regular_12", "text_color": (200, 200, 200)},
    "hazard_card_predator":   {"font_size_key": "regular_12", "text_color": (220, 180, 180)},
    "hazard_card_rival":      {"font_size_key": "regular_12", "text_color": (180, 180, 220)},
    "hazard_card_climate":    {"font_size_key": "regular_12", "text_color": (200, 220, 220)},
    "hazard_card_empowered":  {"font_size_key": "regular_12", "text_color": (190, 130, 255)},
    "hazard_card_condition":  {"font_size_key": "regular_12", "text_color": (120, 120, 120)},
 
    # --- Hazard Card Difficulty Colors ---
    "hazard_difficulty_5":    {"font_size_key": "regular_12", "text_color": (100, 255, 100)},
    "hazard_difficulty_6":    {"font_size_key": "regular_12", "text_color": (173, 255, 47)},
    "hazard_difficulty_7":    {"font_size_key": "regular_12", "text_color": (255, 165, 0)},
    "hazard_difficulty_8":    {"font_size_key": "regular_12", "text_color": (255, 100, 100)},
 
    # --- Player Stat Display ---
    "stat_display_name":      {"font_size_key": "regular_12", "text_color": (200, 200, 200)},
    "stat_display_value":     {"font_size_key": "regular_18", "text_color": (220, 220, 220)},

    # --- Loading Screen ---
    "loading_screen_status": {"font_size_key": "regular_16", "text_color": (255, 255, 100), "align": "left"},

    # --- Extinction Panel ---
    "extinction_panel_body": {"font_size_key": "regular_14", "text_color": (200, 200, 200), "align": "center"},
}

def get_style(style_name: str) -> dict:
    """Retrieves a style dictionary by name, falling back to a default style."""
    style = UI_STYLES.get(style_name)
    if not style:
        if DEBUG: print(f"[styles] ⚠️ Style '{style_name}' not found. Falling back to a default.")
        # Create a fallback default on the fly to avoid crashing
        return {"font_size_key": _DEFAULT_FONT_KEY, "text_color": (255, 0, 255), "align": "center"}
    return style