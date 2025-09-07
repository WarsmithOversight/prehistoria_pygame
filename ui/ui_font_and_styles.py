# ui/ui_font_and_styles.py
# The single source of truth for all font loading and UI text styles.

import pygame

DEBUG = True

# ──────────────────────────────────────────────────
#  Font Loading & Caching
# ──────────────────────────────────────────────────

# A module-level dictionary to act as a singleton cache for all font objects.
_FONT_CACHE = {}
_DEFAULT_FONT_KEY = "regular_medium"

def initialize_font_cache():
    """Loads all predefined fonts into the central cache. Call this once on startup."""
    font_configs = {
        "styles": {
            "regular": "fonts/static/NotoSans-Regular.ttf",
            "bold": "fonts/static/NotoSans-Bold.ttf"
        },
        "sizes": {"small": 12, "medium": 16, "large": 20},
    }
    for style_name, font_path in font_configs["styles"].items():
        for size_name, size_pixels in font_configs["sizes"].items():
            font_key = f"{style_name}_{size_name}"
            try:
                _FONT_CACHE[font_key] = pygame.font.Font(font_path, size_pixels)
            except pygame.error:
                if DEBUG: print(f"[assets] ❌ FONT ERROR: Could not load '{font_path}'. Key '{font_key}' is unavailable.")
    if DEBUG: print(f"[assets] ✅ {len(_FONT_CACHE)} fonts loaded into cache.")

def get_font(key="regular_medium"):
    """Retrieves a font from the cache, falling back to the default if not found."""
    font = _FONT_CACHE.get(key)
    if not font and DEBUG: print(f"[assets] ⚠️ Font key '{key}' not found. Falling back to default.")
    return font or _FONT_CACHE.get(_DEFAULT_FONT_KEY)

# ──────────────────────────────────────────────────
# 🎨 Style Definitions
# ──────────────────────────────────────────────────

UI_STYLES = {
    "panel_title":  {"font_size_key": "bold_large",     "text_color": (255, 220, 180), "align": "center"},
    "default":      {"font_size_key": "regular_small", "text_color": (200, 200, 200), "align": "center"},
    "button":       {"font_size_key": "regular_medium", "text_color": (255, 220, 200), "align": "center"},
    "highlight":    {"font_size_key": "regular_small",  "text_color": (255, 255, 100), "align": "center"},
    "empowered":    {"font_size_key": "regular_small", "text_color": (190, 130, 255), "align": "center"}, # A distinct purple
    "disabled":     {"font_size_key": "regular_small", "text_color": (100, 100, 100), "align": "center"},
 
    # --- Hazard Card Specific Styles ---
    "card_name":       {"font_size_key": "regular_small", "text_color": (220, 220, 220)},
    "card_type":       {"font_size_key": "regular_small", "text_color": (220, 180, 180)}, # A reddish-brown
    "card_subtype":    {"font_size_key": "regular_small", "text_color": (200, 200, 200)},
    "hazard_predator": {"font_size_key": "regular_small", "text_color": (220, 180, 180)}, # A reddish-brown
    "hazard_rival":    {"font_size_key": "regular_small", "text_color": (180, 180, 220)}, # A blueish tint
    "hazard_climate":  {"font_size_key": "regular_small", "text_color": (200, 220, 220)}, # A whitish-gray
 
    # --- Difficulty Colors ---
    "difficulty_5":    {"font_size_key": "regular_small", "text_color": (100, 255, 100)}, # Green
    "difficulty_6":    {"font_size_key": "regular_small", "text_color": (173, 255, 47)},  # Yellow-Green
    "difficulty_7":    {"font_size_key": "regular_small", "text_color": (255, 165, 0)},  # Orange
    "difficulty_8":    {"font_size_key": "regular_small", "text_color": (255, 100, 100)},  # Red
 
    # --- Stat Modifiers ---
    "modifier_good":   {"font_size_key": "regular_small", "text_color": (100, 255, 100)}, # Green
    "modifier_bad":    {"font_size_key": "regular_small", "text_color": (255, 100, 100)},  # Red

    # --- Stat Slot Specific Styles ---
    "stat_name":       {"font_size_key": "regular_small", "text_color": (200, 200, 200)},
    "stat_value":      {"font_size_key": "regular_large", "text_color": (220, 220, 220)},
}

def get_style(style_name: str) -> dict:
    """Retrieves a style dictionary by name, falling back to the default style."""
    style = UI_STYLES.get(style_name)
    if not style:
        if DEBUG: print(f"[styles] ⚠️ Style '{style_name}' not found. Falling back to default.")
        return UI_STYLES["default"]
    return style