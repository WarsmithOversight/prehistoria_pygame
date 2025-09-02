# pathfinding.py
# A stateless module that provides pathfinding services using a
# "pre-compiled rules" engine for clarity and scalability.

import heapq
from shared_helpers import axial_distance, get_neighbors

# ────────────────────────────────────────────────── #
# 🏛️ Public API / Orchestrators
# ────────────────────────────────────────────────── #

def generate_movement_overlay_data(player, tile_objects, persistent_state):
    """
    Purpose: To create the complete dataset needed to render the player's
    visual movement overlay.
    """
    # Step 1: Build a validation function tailored to this player's specific rules.
    move_validator = _build_active_player_movement_rules(player)

    # Step 2: Run the generic Dijkstra search with the custom validator.
    reachable_coords = _Dijkstra_search(
        player=player, # Pass the player object down to the search
        start_coord=(player.q, player.r),
        max_movement=player.remaining_movement,
        move_validator=move_validator,
        tile_objects=tile_objects,
        persistent_state=persistent_state
    )
    
    # Step 3: Determine the interaction "color" for each reachable tile.
    results_with_color = {}
    for coord in reachable_coords:
        tile = tile_objects.get(coord)
        if tile:
            results_with_color[coord] = _get_tile_interaction(player, tile)

    return results_with_color

def calculate_movement_path(player, start_coord, end_coord, tile_objects, persistent_state):
    """
    Purpose: To find a single, valid, and efficient path for a player's
    specific action, such as moving or generating a preview line.
    """
    # Step 1: Build the specific validation function.
    move_validator = _build_active_player_movement_rules(player)

    # Step 2: Run the generic A* search with the custom validator.
    path = _Astar_search(
        start_coord=start_coord,
        end_coord=end_coord,
        move_validator=move_validator,
        tile_objects=tile_objects,
        persistent_state=persistent_state
    )
    return path

# ────────────────────────────────────────────────── #
# ⚙️ Rule Builder
# ────────────────────────────────────────────────── #

def _build_active_player_movement_rules(player):
    """
    Purpose: To "factory" a specific validation function (a closure)
    that contains the entire rule pipeline for the player. This is the
    first step in any pathfinding request.
    """
    # This function's sole job is to call the builder that contains
    # the cascade of specificity, and return the result.
    validator_function = _build_specific_tile_validator(player)
    return validator_function

# ────────────────────────────────────────────────── #
# 🌊 The Core Logic Cascade
# ────────────────────────────────────────────────── #

def _build_specific_tile_validator(player):
    """
    Purpose: To construct and return the actual validation function, which
    is built according to a strict "cascade of specificity."
    """
    def is_valid_step_for_player(tile, is_destination):
        """
        This is the custom-built validator. It runs a tile through a
        pipeline of checks in order of most specific to most general.
        """
        # --- The Cascade of Specificity ---

        # --- High-Priority Aerial Check ---
        # An aerial unit moving to an intermediate tile can ignore all other rules.
        if "aerial" in player.pathfinding_profiles and not is_destination:
            return True

        # Gate 1: Custom Overrules: "Is there any custom rule that overrules everything?"
        if not _apply_custom_overrules(player, tile, is_destination):
            return False

        # Gate 2: Map Rules: "Is there any general map rule that makes this tile impassable?"
        if not _apply_map_rules(player, tile):
            return False

        # Gate 3: Pathing Style: "Do I need to worry about intermediate tiles?"
        if not _apply_pathing_style_rules(player, tile, is_destination):
            return False

        # Gate 4: Interaction Logic: "Is this tile good, bad, medium, or undefined?"
        interaction = _get_tile_interaction(player, tile)
        if interaction is None:
            return False # Undefined terrain is impassable for this species.

        # If the tile passes all gates, the step is valid.
        return True

    return is_valid_step_for_player

# ────────────────────────────────────────────────── #
# 📚 Library of Cascade Stages
# ────────────────────────────────────────────────── #

def _apply_custom_overrules(player, tile, is_destination):
    """
    Purpose: To apply special, high-priority rules like status effects
    or abilities that might override all other logic.
    """
    # This is our dummy function for future mechanics.
    return True

def _apply_map_rules(player, tile):
    """
    Purpose: To enforce the fundamental passability of terrain, accounting
    for exceptions like the `lacustrine` profile.
    """
    # If the tile is not fundamentally passable...
    if not tile.passable:
        # ...check for the `lacustrine` exception on lake tiles.
        if "lacustrine" in player.pathfinding_profiles and getattr(tile, 'is_lake', False):
            return True # The lacustrine profile grants permission.
        # Otherwise, the tile is truly impassable.
        return False
    return True

def _apply_pathing_style_rules(player, tile, is_destination):
    """
    Purpose: To apply the core movement logic based on whether the species
    is `grounded` or `aerial`.
    """
    # An aerial unit can always fly OVER intermediate tiles.
    if "aerial" in player.pathfinding_profiles and not is_destination:
        return True

    # A grounded unit cannot path THROUGH "dead stop" tiles.
    if "grounded" in player.pathfinding_profiles and not is_destination:
        interaction = _get_tile_interaction(player, tile)
        if interaction in ["medium", "bad"]:
            return False
            
    return True

def _get_tile_interaction(player, tile):
    """
    Purpose: To determine the consequential interaction type ('good',
    'medium', 'bad') for a tile, respecting the `riverine` override.
    """
    # The `riverine` profile overrides all other interactions for river tiles.
    if "riverine" in player.pathfinding_profiles and getattr(tile, 'river_data', None):
        return "good"
    
    # Otherwise, look up the tile's base terrain interaction.
    return player.terrain_interactions.get(tile.terrain)

# ────────────────────────────────────────────────── #
# 🧭 Generic Pathfinding Algorithms
# ────────────────────────────────────────────────── #

def _Dijkstra_search(player, start_coord, max_movement, move_validator, tile_objects, persistent_state):
    """A generic Dijkstra algorithm that requires a `move_validator` function."""
    # A dictionary to store the cost to reach each tile.
    cost_so_far = {start_coord: 0}
    # A priority queue of tiles to visit, starting with the origin.
    frontier = [(0, start_coord)]

    while frontier:
        # Get the tile with the lowest cost from the frontier.
        current_cost, current_coord = heapq.heappop(frontier)

        # If we've found a longer path to this tile already, skip it.
        if current_cost > cost_so_far[current_coord]:
            continue

        # Explore neighbors.
        for next_coord in get_neighbors(current_coord[0], current_coord[1], persistent_state):
            tile = tile_objects.get(next_coord)
            if not tile:
                continue

            # The cost to move to any valid neighbor is always 1.
            new_cost = current_cost + 1

            # Check if we can afford to land on this tile.
            if new_cost <= max_movement:

                # First, check if the tile is a valid landing spot.
                if move_validator(tile, is_destination=True):

                    # If it is, add it to our results.
                    if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                        cost_so_far[next_coord] = new_cost

                        # A tile is only added to the frontier (for further exploration)
                        # if it's not a "dead stop" for the current player.
                        interaction = _get_tile_interaction(player, tile)
                        is_grounded = "grounded" in player.pathfinding_profiles

                        # Aerial units can explore from any valid tile.
                        # Grounded units can only explore from "good" tiles.
                        if not is_grounded or interaction == "good":
                            heapq.heappush(frontier, (new_cost, next_coord))

    # The final set of reachable tiles are all the keys in our cost map.
    return set(cost_so_far.keys())

def _Astar_search(start_coord, end_coord, move_validator, tile_objects, persistent_state):
    """A generic A* algorithm that requires a `move_validator` function."""
    # A priority queue to hold nodes to visit, starting with the origin.
    frontier = [(0, start_coord)]
    # A dictionary to reconstruct the path once the end is found.
    came_from = {start_coord: None}
    # A dictionary to store the cost of reaching each node.
    cost_so_far = {start_coord: 0}

    while frontier:
        # Get the node with the lowest priority (cost + heuristic).
        _, current_coord = heapq.heappop(frontier)
        
        # Exit early if the destination is reached.
        if current_coord == end_coord:
            break
        
        # Check all neighbors of the current node.
        for next_coord in get_neighbors(current_coord[0], current_coord[1], persistent_state):
            tile = tile_objects.get(next_coord)
            if not tile:
                continue

            # Use our compiled validator to check if this step is legal.
            is_destination = (next_coord == end_coord)
            if not move_validator(tile, is_destination):
                continue
            
            # The cost to move to a neighbor is always 1.
            new_cost = cost_so_far[current_coord] + 1
            
            # If we haven't seen this node before, or found a cheaper path, update it.
            if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                cost_so_far[next_coord] = new_cost
                # Calculate the priority: cost so far + estimated distance to the end.
                priority = new_cost + axial_distance(*next_coord, *end_coord)
                heapq.heappush(frontier, (priority, next_coord))
                came_from[next_coord] = current_coord
    
    # Reconstruct the path by backtracking from the end node.
    if end_coord not in came_from:
        return [] # No path was found.
        
    path = []
    current = end_coord
    while current is not None:
        path.append(current)
        current = came_from.get(current)
            
    # Reverse the path to the correct order (start -> end).
    path.reverse()
    return path