# micro_main.py
# main entry point. Runs game loop, initalizers and initializes dicts.

import pygame
from scene_manager import SceneManager
from renderer import render_giant_z_pot, initialize_render_states
from shared_helpers import initialize_shared_helper_states
from load_assets import initialize_asset_states, initialize_font_cache
from tween_manager import TweenManager

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True

# ──────────────────────────────────────────────────
# 🏁 Initialization
# ──────────────────────────────────────────────────

pygame.init()
pygame.font.init()
initialize_font_cache()
screen = pygame.display.set_mode((1280, 840))
pygame.display.set_caption("Prehistoria Digital Prototype")
clock = pygame.time.Clock()

persistent_state = {}
variable_state = {}
notebook = {}
assets_state = {}
persistent_state["pers_screen"] = screen
persistent_state["pers_clock"] = clock

initialize_shared_helper_states(persistent_state)
initialize_render_states(persistent_state, notebook) # Pass notebook to create the initial fade overlay
initialize_asset_states(persistent_state)

persistent_state["pers_zoom_config"] = {"min_zoom": 0.10, "max_zoom": 1.00, "zoom_interval": 0.02, "settle_ms": 120}
variable_state["var_current_zoom"] = 1
variable_state["var_render_offset"] = (0, 0)

# 🌎 World Generation Config
persistent_state["pers_region_count"] = 16

# ──────────────────────────────────────────────────
# 🎬 Initialize Managers
# ──────────────────────────────────────────────────
tween_manager = TweenManager(persistent_state, variable_state)
scene_manager = SceneManager(persistent_state, assets_state, variable_state, notebook, tween_manager)

# ──────────────────────────────────────────────────
# ⏰ Main Loop
# ──────────────────────────────────────────────────
print(f"[main] ✅ Main game loop initiated.")
clock.tick()
while scene_manager.running:
    dt = clock.tick(60) / 1000.0
    events = pygame.event.get()
    mouse_pos = pygame.mouse.get_pos()

    for event in events:
        if event.type == pygame.QUIT:
            scene_manager.quit_game()
            
    # ⚙️ Update State
    scene_manager.handle_events(events, mouse_pos)
    scene_manager.update(dt)
    tween_manager.update(dt)

    # 🎨 Render
    screen.fill((0, 0, 0))
    render_giant_z_pot(screen, notebook.get('tile_objects', {}), notebook, persistent_state, assets_state, variable_state)
    
    pygame.display.flip()

pygame.quit()

