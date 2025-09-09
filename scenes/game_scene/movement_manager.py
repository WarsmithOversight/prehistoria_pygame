# scenes/game_scene/movement_manager.py
# A consolidated, self-contained "Power Tool & Battery" for the entire Movement System.

import pygame
import heapq
from shared_helpers import pixel_to_hex, axial_distance, get_neighbors

# ────────────────────────────────────────────────── #
# 🎨 Config & Constants
# ────────────────────────────────────────────────── #

DEBUG = False

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

    def update_path_overlay(self, path, is_gliding=False):
        """Receives a final, calculated path and creates the drawable objects for it."""
        # 🧹 Clear any old path segments from the notebook.
        for key in self.path_keys:
            if key in self.notebook:
                del self.notebook[key]
        self.path_keys.clear()

        # 🎨 If a valid path is provided, create the new drawables.
        if path and len(path) > 1:
            z_formula = self.persistent_state["pers_z_formulas"]['path_curve']

            # ✨ Determine the drawable type based on whether it's a glide path
            drawable_type = 'path_curve_glide' if is_gliding else 'path_curve'

            for i, current_coord in enumerate(path):
                prev_coord = path[i-1] if i > 0 else None
                next_coord = path[i+1] if i < len(path) - 1 else None
                key = f"path_curve_{i}"
                self.notebook[key] = {
                    'type': drawable_type, 'coord': current_coord,
                    'prev_coord': prev_coord, 'next_coord': next_coord, 
                    'z': z_formula(current_coord[1]),
                }
                self.path_keys.append(key)


# ────────────────────────────────────────────────── #
# ⚙️ Movement Manager (The "Battery")
# ────────────────────────────────────────────────── #

class MovementManager:
    """The orchestrator for all movement logic, pathfinding, and UI updates."""
    
    def __init__(self, event_bus, notebook, tile_objects, tween_manager, persistent_state, variable_state, initial_player):
        # ⚙️ Core Systems & State
        self.event_bus = event_bus
        self.notebook = notebook
        self.tile_objects = tile_objects
        self.tween_manager = tween_manager
        self.persistent_state = persistent_state
        self.variable_state = variable_state

        # 🎨 Instantiate its tightly-coupled view
        self.view = MovementView(notebook, tile_objects, persistent_state)

        # 🚩 Player & State Management
        self.active_player = initial_player
        self.is_player_moving = False
        self.active_migration_event = None

        # 🧑‍🍳 This is the "Mise en Place" checklist. It holds all pre-computed
        # movement data for the current player's turn. It is generated once
        # at the start of the turn and after every move.
        self.turn_context_data = {}
        
        # 👂 Event Subscriptions
        self.event_bus.subscribe("REQUEST_PLAYER_MOVE", self.on_move_request)
        self.event_bus.subscribe("HOVERED_HEX_CHANGED", self.on_hover_changed)
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)
        self.event_bus.subscribe("MIGRATION_EVENT_SELECTED", self.on_migration_event_selected)

    # ────────────────────────────────────────────────── #
    # 🎧 Event Handlers
    # ────────────────────────────────────────────────── #

    def on_active_player_changed(self, player):
        """Update the reference to the current active player and clean up old data."""
        self.active_player = player
        self.view.toggle_visibility(False)
        self._clear_turn_context_data() # 🧹 Clean up the previous player's data

    def on_migration_event_selected(self, event_data):
        """
        Stores the active migration event. This is the main trigger for the
        start of a player's turn movement phase.
        """
        # 💾 Store the active player and event for the turn
        self.active_player = event_data["player"]
        self.active_migration_event = event_data["event"]
 
        #  Reset the player's movement points for the new turn.
        self.active_player.remaining_movement = self.active_player.movement_points
        start_coord = (self.active_player.q, self.active_player.r)
        if start_tile := self.tile_objects.get(start_coord):
            interaction = self.active_player.get_interaction_for_tile(start_tile)
            if interaction in ["medium", "bad"]:
                self.active_player.remaining_movement -= 1
                print(f"[MovementManager] ⚠️ Player {self.active_player.player_id} starts on difficult terrain. Movement reduced by 1.")
 
        # 🧑‍🍳 Generate the full "Mise en Place" checklist for the turn and show the overlay.
        self._generate_turn_context_data()
        self._apply_overlay_from_context()
        self.view.toggle_visibility(True)

    def on_hover_changed(self, data):
        """Handles hover events to draw the path preview line."""
        hovered_coord = data["coord"]
        
        # 🛑 Optimization: If the target hasn't changed, do nothing.
        if hovered_coord == self.view.last_path_target:
            return
        self.view.last_path_target = hovered_coord

        # 🛑 Guard Clauses: Only proceed if a path is needed.
        if not self.view.is_visible or not self.active_player or not hovered_coord:
            self.view.update_path_overlay(None)
            return
        
        # 🧠 Read from our pre-computed checklist instead of calculating on the fly.
        target_context = self.turn_context_data.get(hovered_coord)
        if not target_context or not target_context.get("valid_destination"):
            self.view.update_path_overlay(None)
            return

        # ✅ If the destination is valid, calculate and draw the path.
        is_gliding = target_context.get("glidable", False)
        path = self._calculate_movement_path(
            start_coord=(self.active_player.q, self.active_player.r),
            end_coord=hovered_coord,
            is_gliding_move=is_gliding
        )
        self.view.update_path_overlay(path, is_gliding=is_gliding)
        
    def on_move_request(self, data):
        """Initiates a player's move, handling all logic and animation."""
        player = data["player"]
        destination_coord = data["destination"]
        
        if self.is_player_moving: return

        # 🧠 Look up the destination in our checklist to see if it's valid and how to get there.
        target_context = self.turn_context_data.get(destination_coord)
        if not target_context or not target_context.get("valid_destination"):
            print(f"[MovementManager] ⚠️ Click on invalid destination {destination_coord}.")
            return

        is_gliding = target_context.get("glidable", False)
        path_coords = self._calculate_movement_path(
            (player.q, player.r), 
            destination_coord, 
            is_gliding_move=is_gliding
        )
        if not path_coords:
            print(f"[MovementManager] ❌ No valid path from player to {destination_coord}.")
            return

        # 🎨 Hide UI and start animation
        self.view.toggle_visibility(False)
        self.is_player_moving = True

        def on_move_complete():
            # 🦶 Finalize Player State
            player.q, player.r = destination_coord
            self.is_player_moving = False

            # 📢 Announce the move completion
            self.event_bus.post("PLAYER_LANDED_ON_TILE", {
                "player": player,
                "tile": self.tile_objects.get(destination_coord),
                "path_cost": len(path_coords) - 1
            })

            # 🧑‍🍳 Recalculate the movement context from the new position
            self._generate_turn_context_data()
            self._apply_overlay_from_context()
            self.view.toggle_visibility(True)
        
        # 🚀 Execute the tween
        token_to_animate = self.notebook.get(player.token_key)
        self.tween_manager.add_tween(
            target_dict=token_to_animate, animation_type='travel', drawable_type='player_token',
            on_complete=on_move_complete, path=path_coords, speed_hps=3.0
        )
        
    # ────────────────────────────────────────────────── #
    # 🧠 Core Logic: The "Mise en Place" System
    # ────────────────────────────────────────────────── #
    
    def _clear_turn_context_data(self):
        """Clears the pre-computed checklist. Called between turns."""
        self.turn_context_data.clear()


    def _generate_turn_context_data(self):
        """
        The "Mise en Place" engine. Pre-computes all movement-related data for
        the active player's turn from their current position. This version uses
        two efficient Dijkstra searches to calculate ground and glide paths separately.
        """

        # 🧹 1. Clear previous turn's data
        self._clear_turn_context_data()
        player = self.active_player
        start_coord = (player.q, player.r)
        start_tile = self.tile_objects.get(start_coord)
        if not start_tile: return


        # ⚙️ 2. Run the ground-based pathfinding search
        ground_validator = self._build_active_player_movement_rules(player, move_mode='ground')
        ground_costs = self._Dijkstra_search(
            start_coord=start_coord,
            max_movement=player.remaining_movement,
            move_validator=ground_validator
        )

        # ⚙️ 3. Run the glide-based pathfinding search (if the player can glide)
        glide_costs = {}
        if "glide" in player.pathfinding_profiles:
            is_launch_turn = start_tile.terrain in ["Highlands", "Hills"]
            aerial_validator = self._build_active_player_movement_rules(player, move_mode='glide', is_launch_turn=is_launch_turn)
            glide_costs = self._Dijkstra_search(
                start_coord=start_coord,
                max_movement=player.remaining_movement,
                move_validator=aerial_validator
            )

        # 🧑‍🍳 4. Synthesize the final "checklist" from the search results
        report_lines = [] # DEBUG: Initialize a list to hold our report lines.

        # ✨ Get a set of all unique coordinates from both searches
        all_reachable_coords = set(ground_costs.keys()) | set(glide_costs.keys())

        for coord in all_reachable_coords:

            tile = self.tile_objects.get(coord)
            if not tile: continue


            # ✨ Determine the cheapest cost and if gliding is the better/only option
            cost_g = ground_costs.get(coord, float('inf'))
            cost_a = glide_costs.get(coord, float('inf'))
            final_cost = min(cost_g, cost_a)
            is_gliding_path = cost_a <= cost_g

            # ✨ Determine final validity based on the CHEAPEST path's rules
            validator = self._build_active_player_movement_rules(player, 'glide' if is_gliding_path else 'ground')
            valid_destination = validator(None, tile, is_destination=True)

            interaction = self._get_tile_interaction(player, tile)

            self.turn_context_data[coord] = {
                "interaction": interaction,
                "valid_destination": valid_destination,
                "glidable": is_gliding_path,
                "cost": final_cost
            }

            # DEBUG: Format a line for the report and add it to our list.
            report_line = f"  - Tile {str(coord):<8} ({tile.terrain:<12}): Interaction={str(interaction):<8} | Cost={final_cost} | Glide={str(is_gliding_path):<5} | Dest={valid_destination}"
            report_lines.append(report_line)
        
        # DEBUG: Print the entire formatted report at once.
        if DEBUG and report_lines:
            print("\n---------------------------------------------------------------------")
            print("                       Tile Interaction Report                       ")
            print(f"    Player: {player.player_id} ({player.species_name}) at {str(start_coord):<8} | Move Points: {player.remaining_movement}")
            print("---------------------------------------------------------------------")
            # ✨ Sort report by coordinate for consistent output
            print("\n".join(sorted(report_lines, key=lambda x: eval(x.split()[2]))))
            print("--------------------------- End of Report ---------------------------\n")

        print(f"[MovementManager] ✅ Context generated for Player {player.player_id}. {len(self.turn_context_data)} tiles processed.")

    def _apply_overlay_from_context(self):
        """Reads the pre-computed checklist and passes the data to the view for rendering."""
        # 🎨 1. Prepare the data structure for the view.
        overlay_data = {}

        # 🚶 2. Iterate through the pre-computed context.
        for coord, data in self.turn_context_data.items():
            # ✨ Only add tiles that are valid final destinations to the overlay.
            if data.get("valid_destination"):
                interaction_color = data.get("interaction")
                if interaction_color:
                    overlay_data[coord] = {"primary": interaction_color}

        # 🌪️ 3. Add secondary overlays for migration events, if active.
        if self.active_migration_event:
            # ✨ Only check tiles that are already part of the valid move range.
            for coord in overlay_data:
                tile = self.tile_objects.get(coord)
                trigger_type = self.active_migration_event.trigger_type
                trigger_param = self.active_migration_event.trigger_param
                # ✨ Check if the tile's terrain triggers the event condition.
                if tile and trigger_type == "enter_terrain" and tile.terrain in trigger_param:
                    overlay_data[coord]["secondary"] = "hazard"

        # 🚀 4. Send the completed data to the view.
        self.view.set_overlay_data(overlay_data)

    def _calculate_movement_path(self, start_coord, end_coord, is_gliding_move=False):
        """Finds a single, valid path using A*, using the specified move rules."""
        # ✨ We need to know if the player is launching to build the correct validator
        start_tile = self.tile_objects.get(start_coord)
        is_launch_turn = is_gliding_move and start_tile.terrain in ["Highlands", "Hills"]
        move_mode = 'glide' if is_gliding_move else 'ground'
        validator = self._build_active_player_movement_rules(self.active_player, move_mode, is_launch_turn)
        return self._Astar_search(start_coord, end_coord, validator)

    # ────────────────────────────────────────────────── #
    # ⚙️ Rule Builder & Logic Cascade
    # ────────────────────────────────────────────────── #


    def _build_active_player_movement_rules(self, player, move_mode, is_launch_turn=False):
        """
        Factories a validation function that enforces movement rules for a given mode.

        Args:
            player: The active player object.
            move_mode (str): 'ground' or 'glide'.
            is_launch_turn (bool): True if a glider is launching from high ground.
         """


        def is_valid_move(from_tile, to_tile, is_destination):
            # 🛑 UNIVERSAL RULE: Base passability and map rules always apply.
            if not self._apply_map_rules(player, to_tile):
                 return False

            if move_mode == 'glide':
                # 🛑 GLIDE RULE 1: Mountains are impassable obstacles.
                if to_tile.terrain == "Mountains": return False
                
                # 🛑 GLIDE RULE 2: A glide cannot END on high ground.
                if is_destination and to_tile.terrain in ["Highlands", "Hills"]: return False

                # 🧠 GLIDE RULE 3: A glider can pass over anything else during its flight...
                if not is_destination:
                    # ...as long as it's a launch turn OR they are moving downhill.
                    if is_launch_turn: return True
                    from_topo = getattr(from_tile, 'topographic_scale', 0)
                    to_topo = getattr(to_tile, 'topographic_scale', 0)
                    return to_topo <= from_topo

            # 🧠 GROUND RULE / FINAL DESTINATION RULE:
            # A grounded step or the final landing spot requires a valid habitat interaction.
            interaction = self._get_tile_interaction(player, to_tile)
            if interaction is None: return False

            # 🛑 GROUND RULE: Grounded creatures cannot move through difficult terrain.
            if move_mode == 'ground' and not is_destination and interaction in ["medium", "bad"]:
                return False

            return self._apply_custom_overrules(player, to_tile, is_destination)

        return is_valid_move


    def _apply_custom_overrules(self, player, tile, is_destination):
        return True

    def _apply_map_rules(self, player, tile):

        if not tile.passable:
            if "lacustrine" in player.pathfinding_profiles and getattr(tile, 'is_lake', False):
                return True
            return False
        return True

    def _get_tile_interaction(self, player, tile):
        if "riverine" in player.pathfinding_profiles and getattr(tile, 'river_data', None):
            return "good"
        return player.terrain_interactions.get(tile.terrain)

    # ────────────────────────────────────────────────── #
    # 🧭 Pathfinding Algorithms (Unchanged)
    # ────────────────────────────────────────────────── #

    def _Dijkstra_search(self, start_coord, max_movement, move_validator, **kwargs):
        """Finds all reachable tiles and the cost to reach them."""
        # ✨ This version correctly separates the cost to land on a tile (cost_so_far)
        # from the cost to travel through it (cost_to_traverse).
        cost_so_far = {start_coord: 0}
        cost_to_traverse = {start_coord: 0}
        frontier = [(0, start_coord)]
        start_tile = self.tile_objects.get(start_coord) # ✨ Get start tile for validator

        while frontier:
            current_cost, current_coord = heapq.heappop(frontier)
            current_tile = self.tile_objects.get(current_coord)


            # Use cost_to_traverse for the frontier check
            if current_cost > cost_to_traverse.get(current_coord, float('inf')):
                continue

            for next_coord in get_neighbors(current_coord[0], current_coord[1], self.persistent_state):
                next_tile = self.tile_objects.get(next_coord)
                if not next_tile: continue

                new_cost = current_cost + 1
                if new_cost > max_movement:
                    continue

                # 1. Check if the tile is a valid FINAL DESTINATION for pathing
                if move_validator(current_tile, next_tile, is_destination=True):
                    if new_cost < cost_so_far.get(next_coord, float('inf')):
                        cost_so_far[next_coord] = new_cost
                
                # 2. Check if the tile is PASSABLE as an intermediate step
                if move_validator(current_tile, next_tile, is_destination=False):
                    if new_cost < cost_to_traverse.get(next_coord, float('inf')):
                        cost_to_traverse[next_coord] = new_cost
                        heapq.heappush(frontier, (new_cost, next_coord))

        return cost_so_far

    def _Astar_search(self, start_coord, end_coord, move_validator, **kwargs):
        """Finds a single, cheapest path from start to end."""
        frontier = [(0, start_coord)]
        came_from = {start_coord: None}
        cost_so_far = {start_coord: 0}

        while frontier:
            _, current_coord = heapq.heappop(frontier)
            if current_coord == end_coord: break

            current_tile = self.tile_objects.get(current_coord)
            
            for next_coord in get_neighbors(current_coord[0], current_coord[1], self.persistent_state):
                next_tile = self.tile_objects.get(next_coord)
                if not next_tile: continue

                is_final_step = (next_coord == end_coord)
                # Determine if the step is valid based on whether it's the final destination or part of the path
                is_valid = move_validator(current_tile, next_tile, is_destination=is_final_step)
                if not is_valid: continue
                
                new_cost = cost_so_far[current_coord] + 1
                if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                    cost_so_far[next_coord] = new_cost
                    priority = new_cost + axial_distance(*next_coord, *end_coord)
                    heapq.heappush(frontier, (priority, next_coord))
                    came_from[next_coord] = current_coord
        
        if end_coord not in came_from: return None

        path = [] # Reconstruct path
        current = end_coord
        while current is not None:
            path.append(current)
            current = came_from.get(current)
        path.reverse()
        return path