# collectibles.py
# A home for standalone game elements that manage their own state and logic.

import random
import math
from shared_helpers import axial_distance, hex_to_pixel

# ──────────────────────────────────────────────────
# ⚙️ Collectible Manager (The "Battery")
# ──────────────────────────────────────────────────
class CollectibleManager:
    """Manages all logic related to collectibles, including seeding and collection."""
    def __init__(self, event_bus, notebook, tween_manager, persistent_state, players, tile_objects, audio_manager):
        # ⚙️ Core System References
        self.event_bus = event_bus
        self.notebook = notebook
        self.tween_manager = tween_manager
        self.audio_manager = audio_manager
        self.persistent_state = persistent_state

        # 🚩 State
        self.active_player = players[0] # Start with the first player

        # 💎 State
        self.collectibles = seed_collectibles(persistent_state, tile_objects, notebook, tween_manager, players)

        # 👂 Event Subscriptions
        self.event_bus.subscribe("PLAYER_LANDED_ON_TILE", self.on_player_landed)
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)

    def update(self, dt):
        """Update loop for continuous logic, like the nearest collectible indicator."""
        self._update_nearest_collectible_indicator()

    def on_player_landed(self, data):
        """Checks if a player has landed on a collectible and processes the outcome."""
        player = data["player"]
        tile = data["tile"]

        # 🛡️ Guard clause if tile data is missing
        if not tile: return

        # Check if a collectible exists at this coordinate.
        collected_item = next((c for c in self.collectibles if (c.q, c.r) == (tile.q, tile.r)), None)
        if collected_item:
            print(f"[CollectibleManager] ✅ Player {player.player_id} collected an item.")
            self.audio_manager.play_sfx(blacklist=["game_over_cartoon_2.wav", "error.wav", "try_again.wav", "earn_points.wav", "secret_area_unlock_1", "soft_fail"])
            player.gain_evolution_points()
            collected_item.cleanup(self.notebook, self.tween_manager)
            self.collectibles.remove(collected_item)
            self.event_bus.post("REQUEST_HAZARD_EVENT", {"trigger": "collectible"})

    def on_active_player_changed(self, player):
        """Updates the internal reference to the current active player."""
        self.active_player = player

    def _find_nearest_collectible(self):
        """Finds the active player's nearest collectible."""
        if not self.collectibles:
            return None

        return min(
            self.collectibles,
            key=lambda c: axial_distance(self.active_player.q, self.active_player.r, c.q, c.r)
        )

    def _update_nearest_collectible_indicator(self):
        """Calculates the angle to the nearest collectible and updates the drawable."""
        indicator_key = "collectible_indicator"
        player = self.active_player
        player_token = self.notebook.get(player.token_key)
        nearest_collectible = self._find_nearest_collectible()

        if not nearest_collectible or not player_token:
            if indicator_key in self.notebook:
                del self.notebook[indicator_key]
            return
            
        world_variable_state = {"var_current_zoom": 1.0, "var_render_offset": (0,0)}

        if 'pixel_pos' in player_token: 
            player_pos = player_token['pixel_pos'] 
        else: 
            player_pos = hex_to_pixel(player.q, player.r, self.persistent_state, world_variable_state)

        target_pos = hex_to_pixel(nearest_collectible.q, nearest_collectible.r, self.persistent_state, world_variable_state)
 
        dx = target_pos[0] - player_pos[0]
        dy = target_pos[1] - player_pos[1]
        angle_deg = math.degrees(math.atan2(-dy, dx))

        z_formula = self.persistent_state["pers_z_formulas"]["indicator"]
        self.notebook[indicator_key] = {
            "type": "indicator", "q": player.q, "r": player.r,
            "anchor_world_pos": player_pos, "angle": angle_deg, "z": z_formula(player.r)
        }

# ──────────────────────────────────────────────────
# 🏭 Seeding Function
# ──────────────────────────────────────────────────
def seed_collectibles(persistent_state, tile_objects, notebook, tween_manager, players):
    """
    Finds valid locations and creates an instance of a Collectible for each one.
    This acts as a "factory" for all collectibles at the start of the game.
    """
    # 🏞️ Setup and Data Acquisition
    # Safely get the region map from the persistent state.
    region_map = persistent_state.get("pers_region_map", {})
    if not region_map:
        print("[Collectible] ❌ 'pers_region_map' not found. Cannot spawn collectibles.")
        return []

    # 🗺️ Identify Player Regions to Exclude
    # Create a reverse lookup map for coordinates to find their region key.
    coord_to_region_map = {
        coord: region_key
        for region_key, coords_list in region_map.items()
        for coord in coords_list
    }
    
    # Find the unique set of regions occupied by players.
    player_start_regions = set()
    for player in players:
        player_coord = (player.q, player.r)
        region = coord_to_region_map.get(player_coord)
        if region:
            player_start_regions.add(region)
        else:
            print(f"[Collectible] ⚠️ Could not find region for player at {player_coord}.")

    # 🎯 Select Target Regions for Spawning
    # Get a list of all available region identifiers.
    # Filter out the regions where players have started.
    spawnable_regions = [
        key for key in region_map.keys() if key not in player_start_regions
    ]
    
    # Calculate how many region to select (half of the total, rounded down).
    num_to_select = len(spawnable_regions) // 2
    
    # Use random.sample to get a unique list of region to spawn in.
    selected_regions = random.sample(spawnable_regions, num_to_select)

    # ✨ Create a list to hold the new instances.
    collectible_instances = []

    # 📌 Select One Tile Per Region and Create an Instance
    # Iterate through each of the randomly chosen region.
    for region_key in selected_regions:
        
        # Get the list of all tile coordinates belonging to the current region.
        coords_in_region = region_map[region_key]

        # ✅ FIX 1: Check for the tile's `passable` attribute directly.
        passable_tiles = [
            tile for coord in coords_in_region 
            if (tile := tile_objects.get(coord)) and getattr(tile, 'passable', False)
        ]

        # If at least one passable tile exists in the region...
        if passable_tiles:
            
            # ...select one tile at random from the filtered list.
            chosen_tile = random.choice(passable_tiles)
            q, r = chosen_tile.q, chosen_tile.r
            
            # ...create a new, self-contained Collectible instance for this location.
            new_collectible = Collectible(q, r, persistent_state, notebook, tween_manager)
            collectible_instances.append(new_collectible)
        else:
            # ✅ FIX 2: Add a failure-aware debug print if no suitable tile is found.
            print(f"[Collectible] ⚠️ Could not place collectible in region '{region_key}': No passable tiles found.")

    print(f"[Collectible] ✅ Seeded {len(collectible_instances)} collectibles on the map.")
    return collectible_instances

# ──────────────────────────────────────────────────
# 💎 Collectible Class
# ──────────────────────────────────────────────────
class Collectible:
    """
    Represents a single collectible item on the board. It manages its own
    graphics, animations, and cleanup logic.
    """
    def __init__(self, q, r, persistent_state, notebook, tween_manager):
        # ⚙️ Store core state
        self.q = q
        self.r = r
        
        # 🎨 Create Drawables in the Notebook
        # Define unique keys for all visual components.
        self.shadow_key = f"collectible_shadow_{self.q}_{self.r}"
        self.glow_key = f"collectible_glow_{self.q}_{self.r}"
        self.icon_key = f"collectible_icon_{self.q}_{self.r}"
        
        # Get the z-layering formulas from the renderer's state.
        z_formulas = persistent_state["pers_z_formulas"]

        # Create the drawable dictionary for the shadow.
        notebook[self.shadow_key] = {
            "type": "artwork",
            "asset_category": "collectible_assets",
            "asset_key": "shadow",
            "q": self.q, "r": self.r,
            "z": z_formulas["collectible_shadow"](self.r)
        }
        # Create the drawable dictionary for the glow.
        notebook[self.glow_key] = {
            "type": "artwork",
            "asset_category": "collectible_assets",
            "asset_key": "glow",
            "q": self.q, "r": self.r,
            "z": z_formulas["collectible_glow"](self.r)
        }
        # Create the drawable dictionary for the icon.
        notebook[self.icon_key] = {
            "type": "artwork",
            "asset_category": "collectible_assets",
            "asset_key": "icon",
            "q": self.q, "r": self.r,
             "z": z_formulas["collectible_icon"](self.r)
        }
        
        # 🤸 Start Bobbing Animations
        # Get direct references to the drawables that need animating.
        glow_drawable = notebook[self.glow_key]
        icon_drawable = notebook[self.icon_key]

        # Add a subtle bob tween for the glow.
        tween_manager.add_tween(
            target_dict=glow_drawable, animation_type='bob', drawable_type='generic',
            amplitude=2, period=1.8, on_complete=None
        )
        # Add a more prominent bob tween for the icon.
        tween_manager.add_tween(
            target_dict=icon_drawable, animation_type='bob', drawable_type='generic',
            amplitude=4, period=1.5, on_complete=None
        )

    def cleanup(self, notebook, tween_manager):
        """Removes all of this collectible's visuals and animations from the game."""
        # 🛑 Stop Animations
        # Get the drawables that are being animated.
        glow_drawable = notebook.get(self.glow_key)
        icon_drawable = notebook.get(self.icon_key)

        # Tell the TweenManager to remove any tweens targeting these drawables.
        if glow_drawable:
            tween_manager.remove_tweens_by_target(glow_drawable)
        if icon_drawable:
            tween_manager.remove_tweens_by_target(icon_drawable)
            
        # 🗑️ Delete Drawables
        # Safely delete the keys from the notebook to remove them from the renderer.
        if self.shadow_key in notebook:
            del notebook[self.shadow_key]
        if self.glow_key in notebook:
            del notebook[self.glow_key]
        if self.icon_key in notebook:
            del notebook[self.icon_key]
            
        print(f"[Collectible] ✅ Cleaned up collectible at ({self.q}, {self.r}).")