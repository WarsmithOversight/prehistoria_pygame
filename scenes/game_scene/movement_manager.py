# scenes/game_scene/movement_manager.py
# A consolidated, self-contained "Power Tool & Battery" for the entire Movement System.

import pygame
import heapq
from shared_helpers import pixel_to_hex, axial_distance, get_neighbors

# ────────────────────────────────────────────────── #
# 🎨 Movement View (The "Power Tool")
# ────────────────────────────────────────────────── #

class MovementView:
    """A dedicated class to handle all visual feedback for player movement."""
    def __init__(self, notebook, tile_objects, persistent_state):
        # ⚙️ Store references to game objects
        self.notebook = notebook
        self.tile_objects = tile_objects
        self.persistent_state = persistent_state
        
        # 🚩 State Management
        self.active_player_move_range = []
        self.path_keys = []
        self.is_visible = False
        self.last_path_target = None

    def set_overlay_data(self, overlay_data):
        """Receives movement data from the MovementManager and applies the tile colors."""
        # 🧹 Clear old color tags from the previous overlay
        for coord in self.active_player_move_range:
            if tile := self.tile_objects.get(coord):
                tile.primary_move_color = None
                tile.secondary_move_color = None
        
        # 💾 Store the new range and apply new colors
        self.active_player_move_range = list(overlay_data.keys())
        for coord, data in overlay_data.items():
            if tile := self.tile_objects.get(coord):
                tile.primary_move_color = data["primary"]
                tile.secondary_move_color = data.get("secondary")

    def toggle_visibility(self, is_visible):
        """Sets the visibility of the pre-calculated movement overlay."""
        self.is_visible = is_visible
        # 🧹 Hide the path preview line when the main overlay is hidden
        if not is_visible:
            self.update_path_overlay(None)

        # ✨ Apply the visibility flag to all tiles in the current range
        for coord in self.active_player_move_range:
            if tile := self.tile_objects.get(coord):
                tile.movement_overlay = is_visible

    def update_path_overlay(self, path):
        """Receives a final, calculated path and creates the drawable objects for it."""
        # 🧹 Clear any old path segments from the notebook.
        for key in self.path_keys:
            if key in self.notebook:
                del self.notebook[key]
        self.path_keys.clear()

        # 🎨 If a valid path is provided, create the new drawables.
        if path and len(path) > 1:
            z_formula = self.persistent_state["pers_z_formulas"]['path_curve']
            for i, current_coord in enumerate(path):
                prev_coord = path[i-1] if i > 0 else None
                next_coord = path[i+1] if i < len(path) - 1 else None
                key = f"path_curve_{i}"
                self.notebook[key] = {
                    'type': 'path_curve', 'coord': current_coord,
                    'prev_coord': prev_coord, 'next_coord': next_coord, 
                    'z': z_formula(current_coord[1])
                }
                self.path_keys.append(key)


# ────────────────────────────────────────────────── #
# ⚙️ Movement Manager (The "Battery")
# ────────────────────────────────────────────────── #

class MovementManager:
    """The orchestrator for all movement logic, pathfinding, and UI updates."""
    
    def __init__(self, event_bus, notebook, tile_objects, tween_manager, persistent_state, variable_state, initial_player, audio_manager, collectibles):
        # ⚙️ Core Systems & State
        self.event_bus = event_bus
        self.notebook = notebook
        self.tile_objects = tile_objects
        self.tween_manager = tween_manager
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.audio_manager = audio_manager
        self.collectibles = collectibles

        # 🎨 Instantiate its tightly-coupled view
        self.view = MovementView(notebook, tile_objects, persistent_state)

        # 🚩 Player & State Management
        self.active_player = initial_player
        self.is_player_moving = False
        
        # 👂 Event Subscriptions
        self.event_bus.subscribe("REQUEST_PLAYER_MOVE", self.on_move_request)
        self.event_bus.subscribe("HOVERED_HEX_CHANGED", self.on_hover_changed)
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)
        self.event_bus.subscribe("TURN_READY_FOR_INPUT", self.on_turn_ready)

    # ────────────────────────────────────────────────── #
    # 🎧 Event Handlers
    # ────────────────────────────────────────────────── #

    def on_active_player_changed(self, player):
        """Update the reference to the current active player and hide old UI."""
        self.active_player = player
        self.view.toggle_visibility(False)

    def on_turn_ready(self, event_data=None):
        """Recalculates the overlay at the start of a new turn."""
        self._calculate_and_apply_overlay()
        self.view.toggle_visibility(True)

    def on_hover_changed(self, data):
        """Handles hover events to draw the path preview line."""
        hovered_coord = data["coord"]
        
        # 🛑 Optimization: If the target hasn't changed, do nothing.
        if hovered_coord == self.view.last_path_target:
            return
        self.view.last_path_target = hovered_coord

        # 🛑 Guard Clauses: Only proceed if a path is possible and needed.
        if not self.view.is_visible or not self.active_player or not hovered_coord:
            self.view.update_path_overlay(None) # Ensure path is cleared
            return
        
        hovered_tile = self.tile_objects.get(hovered_coord)
        if not hovered_tile or not getattr(hovered_tile, 'primary_move_color', None):
            self.view.update_path_overlay(None) # Ensure path is cleared
            return

        # ✅ If all checks pass, calculate and draw the new path.
        path = self._calculate_movement_path(
            start_coord=(self.active_player.q, self.active_player.r),
            end_coord=hovered_coord
        )
        self.view.update_path_overlay(path)
        
    def on_move_request(self, data):
        """Initiates a player's move, handling all logic and animation."""
        player = data["player"]
        destination_coord = data["destination"]
        
        # 🛑 Guard against clicks while moving
        if self.is_player_moving:
            return

        # 🗺️ Calculate the path for the move
        start_coord = (player.q, player.r)
        path_coords = self._calculate_movement_path(start_coord, destination_coord)
        if not path_coords:
            print(f"[MovementManager] ❌ No valid path from {start_coord} to {destination_coord}.")
            return

        # 🎨 Hide UI and start animation
        self.view.toggle_visibility(False)
        self.is_player_moving = True

        # ⚙️ Define the completion callback for the tween
        def on_move_complete():
            # 🦶 1. Finalize Player State
            player.q, player.r = destination_coord
            token = self.notebook.get(player.token_key)
            if token and 'pixel_pos' in token:
                del token['pixel_pos']
            self.is_player_moving = False

            # 📢 2. Announce the high-level event that other systems can listen for
            self.event_bus.post("PLAYER_LANDED_ON_TILE", {
                "player": player,
                "tile": self.tile_objects.get(destination_coord),
                "path_cost": len(path_coords) - 1
            })

            # 🎨 3. Recalculate and show the new movement range
            self._calculate_and_apply_overlay()
            self.view.toggle_visibility(True)
        
        # 🚀 Execute the tween
        token_to_animate = self.notebook.get(player.token_key)
        self.tween_manager.add_tween(
            target_dict=token_to_animate,
            animation_type='travel',
            drawable_type='player_token',
            on_complete=on_move_complete,
            path=path_coords,
            speed_hps=3.0
        )
        
    # ────────────────────────────────────────────────── #
    # 🧠 Core Logic & Pathfinding
    # ────────────────────────────────────────────────── #

    def _calculate_and_apply_overlay(self):
        """The main orchestrator for generating and applying the movement overlay."""
        player = self.active_player

        # ⚙️ 1. Build the validation function tailored to this player's specific rules.
        move_validator = self._build_active_player_movement_rules(player)

        # 🗺️ 2. Run the generic Dijkstra search with the custom validator.
        reachable_coords = self._Dijkstra_search(
            start_coord=(player.q, player.r),
            max_movement=player.remaining_movement,
            move_validator=move_validator,
        )
        
        # 🎨 3. Determine the interaction "color" for each reachable tile.
        overlay_data = {}
        for coord in reachable_coords:
            tile = self.tile_objects.get(coord)
            if tile:
                interaction = self._get_tile_interaction(player, tile)
                if interaction:
                    overlay_data[coord] = {"primary": interaction}
        
        # 📢 4. Pass the final data to the view.
        self.view.set_overlay_data(overlay_data)

    def _calculate_movement_path(self, start_coord, end_coord):
        """Finds a single, valid path using A*."""
        move_validator = self._build_active_player_movement_rules(self.active_player)
        return self._Astar_search(start_coord, end_coord, move_validator)

    # ────────────────────────────────────────────────── #
    # ⚙️ Rule Builder & Logic Cascade (from pathfinding.py)
    # ────────────────────────────────────────────────── #

    def _build_active_player_movement_rules(self, player):
        """Factories a validation function that contains the rule pipeline for the player."""
        def is_valid_step(tile, is_destination):
            # 優先度の高い飛行チェック
            if "aerial" in player.pathfinding_profiles and not is_destination:
                return True
            # ゲート1: カスタム上書きルール
            if not self._apply_custom_overrules(player, tile, is_destination):
                return False
            # ゲート2: マップルール
            if not self._apply_map_rules(player, tile):
                return False
            # ゲート3: 経路探索スタイルルール
            if not self._apply_pathing_style_rules(player, tile, is_destination):
                return False
            # ゲート4: インタラクションロジック
            interaction = self._get_tile_interaction(player, tile)
            if interaction is None:
                return False
            return True
        return is_valid_step

    def _apply_custom_overrules(self, player, tile, is_destination):
        return True

    def _apply_map_rules(self, player, tile):
        if not tile.passable:
            if "lacustrine" in player.pathfinding_profiles and getattr(tile, 'is_lake', False):
                return True
            return False
        return True

    def _apply_pathing_style_rules(self, player, tile, is_destination):
        if "aerial" in player.pathfinding_profiles and not is_destination:
            return True
        if "grounded" in player.pathfinding_profiles and not is_destination:
            interaction = self._get_tile_interaction(player, tile)
            if interaction in ["medium", "bad"]:
                return False
        return True

    def _get_tile_interaction(self, player, tile):
        if "riverine" in player.pathfinding_profiles and getattr(tile, 'river_data', None):
            return "good"
        return player.terrain_interactions.get(tile.terrain)

    # ────────────────────────────────────────────────── #
    # 🧭 Pathfinding Algorithms (from pathfinding.py)
    # ────────────────────────────────────────────────── #

    def _Dijkstra_search(self, start_coord, max_movement, move_validator):
        cost_so_far = {start_coord: 0}
        cost_to_traverse = {start_coord: 0}
        frontier = [(0, start_coord)]

        while frontier:
            current_cost, current_coord = heapq.heappop(frontier)
            if current_cost > cost_to_traverse[current_coord]:
                continue

            for next_coord in get_neighbors(current_coord[0], current_coord[1], self.persistent_state):
                tile = self.tile_objects.get(next_coord)
                if not tile: continue

                new_cost = current_cost + 1
                if new_cost > max_movement: continue

                if move_validator(tile, is_destination=True):
                    if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                        cost_so_far[next_coord] = new_cost

                if move_validator(tile, is_destination=False):
                    if next_coord not in cost_to_traverse or new_cost < cost_to_traverse[next_coord]:
                        cost_to_traverse[next_coord] = new_cost
                        heapq.heappush(frontier, (new_cost, next_coord))
        return set(cost_so_far.keys())

    def _Astar_search(self, start_coord, end_coord, move_validator):
        frontier = [(0, start_coord)]
        came_from = {start_coord: None}
        cost_so_far = {start_coord: 0}

        while frontier:
            _, current_coord = heapq.heappop(frontier)
            if current_coord == end_coord: break
            
            for next_coord in get_neighbors(current_coord[0], current_coord[1], self.persistent_state):
                tile = self.tile_objects.get(next_coord)
                if not tile: continue

                is_destination = (next_coord == end_coord)
                if not move_validator(tile, is_destination): continue
                
                new_cost = cost_so_far[current_coord] + 1
                if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                    cost_so_far[next_coord] = new_cost
                    priority = new_cost + axial_distance(*next_coord, *end_coord)
                    heapq.heappush(frontier, (priority, next_coord))
                    came_from[next_coord] = current_coord
        
        if end_coord not in came_from: return []
            
        path = []
        current = end_coord
        while current is not None:
            path.append(current)
            current = came_from.get(current)
        path.reverse()
        return path
