# game_manager.py
# This class orchestrates the game's state, including turns and active players.

import random
from pathfinding import generate_movement_overlay_data, calculate_movement_path

DEBUG = True

class GameManager:
    """Manages the overall game state, turn progression, and active player."""

    def __init__(self, players, camera_controller, tile_objects, event_bus, tween_manager, notebook, persistent_state, variable_state):
        
        # Stores references to the core game systems
        self.tween_manager = tween_manager
        self.players = players
        self.camera_controller = camera_controller
        self.tile_objects = tile_objects
        self.event_bus = event_bus

        # Stores references to global game state objects
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.notebook = notebook

        # Keeps track of the keys for path drawables in the notebook
        self.path_keys = []
        
        # Initializes the turn and player counters
        self.turn_counter = 1
        self.active_player_index = 0

        # Pauses the game by default at the start
        self.is_paused = True

        # Initializes variables for player selection and movement
        self.selected_player = None
        self.is_player_moving = False

        # Stores the coordinates for the current turn's movement overlay
        self.active_player_move_range = []
        self.last_hovered_coord = None

        # Initializes dictionaries for climate effects
        self.master_climate_effects = {}
        self.active_climate_effect = None

        # Populates the list of all possible climate effects
        self._initialize_climate_effects()

        # Pre-calculates the movement range for the first player at game start
        self._calculate_active_player_movement()

        # Announce the start of the game
        print(f"[GameManager] ✅ Game Start! Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")
        
        # Selects the first climate effect
        self._select_new_climate_effect()
        
    @property
    def active_player(self):
        """A convenient property to get the current active player object."""
        # Returns the player object at the current active player index
        return self.players[self.active_player_index]

    def advance_turn(self):
        """Advances to the next player's turn and updates the turn counter."""
        
        # Exits the function if the game is paused
        if self.is_paused: return
        
        # 🌪️ Select a new climate effect for the turn
        self._select_new_climate_effect()

        # Hides the movement overlay
        self._toggle_movement_overlay(False)

        # Deselects the previously selected player
        if self.selected_player:
            previous_coord = (self.selected_player.q, self.selected_player.r)
            if self.tile_objects.get(previous_coord):
                self.tile_objects[previous_coord].is_selected = False
            self.selected_player = None

        # Advance to the next player in the list
        self.active_player_index = (self.active_player_index + 1) % len(self.players)

        # Increment the main turn counter only when a full round is complete
        if self.active_player_index == 0:
            self.turn_counter += 1
        
        # Center the camera on the new active player
        self.camera_controller.center_on_tile(
            self.active_player.q, self.active_player.r, 
            self.persistent_state, self.variable_state
        )

        # Determine and apply any start-of-turn movement modifiers
        player = self.active_player

        # Reset movement penealties
        player.turn_movement_modifier = 0

        # Check starting tile for new penalties
        start_coord = (player.q, player.r)
        start_tile = self.tile_objects.get(start_coord)

        if start_tile:
            # Ask the player for the interaction type of their starting tile.
            interaction = player.get_interaction_for_tile(start_tile)
             
            # "medium" or "bad" terrain confers a movement penalty.
            if interaction in ["medium", "bad"]:                
                player.turn_movement_modifier = -1
                print(f"[GameManager] ⚠️ Player {player.player_id} ({player.species_name}) starts on difficult terrain. Movement reduced by 1.")
       
        # Sets the player's movement points for the current turn
        player.remaining_movement = player.movement_points + player.turn_movement_modifier

        # Pre-calculates the movement range for the new active player
        self._calculate_active_player_movement()

        # Select the new active player
        self._select_player(self.active_player)

        # Prints a status update for the new turn
        print(f"[GameManager] ✅ Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")

    def unpause(self):
        """Starts the first turn and allows the game to proceed."""
        
        # Exits if the game is not paused
        if not self.is_paused: return

        # Unpauses the game
        self.is_paused = False

        # Centers the camera on the active player
        self.camera_controller.center_on_tile(
            self.active_player.q, self.active_player.r,
            self.persistent_state, self.variable_state
        )

    def handle_click(self, coord):
        """Handles clicks for player selection, deselection, and movement commands."""
        
        # Exits if the game is paused
        if self.is_paused: return

        # Ignore all clicks while the player is animating
        if self.is_player_moving:
            return

        # Did the user click on a player token?
        for player in self.players:
            if (player.q, player.r) == coord:
                # Selects the player and handles the selection logic
                self._select_player(player)
                return

        # If not, was it a valid move command for the selected player?
        clicked_tile = self.tile_objects.get(coord)
        
        # Checks if the clicked tile is a valid move target for the active player
        if (clicked_tile and
                getattr(clicked_tile, 'primary_move_color', None) and
                self.selected_player is self.active_player and
                coord != (self.active_player.q, self.active_player.r)):
            
            # Initiates the player movement
            self.move_player_to(coord)
            return

        # If it's not a player or a move, it's a click on empty space.
        # Deselects whatever is currently selected
        self._select_player(None)

    def _select_player(self, player_to_select):
        """Handles the logic for selecting a player and showing their overlays."""

        # Deselect any currently selected player
        self._toggle_movement_overlay(False)
        if self.selected_player:
            previous_coord = (self.selected_player.q, self.selected_player.r)
            if self.tile_objects.get(previous_coord):
                self.tile_objects[previous_coord].is_selected = False
            self.selected_player = None

        if not player_to_select:
            return

        # If we have a valid player, proceed with selecting them
        self.selected_player = player_to_select
        coord = (player_to_select.q, player_to_select.r)
        if self.tile_objects.get(coord):

            # Sets the is_selected flag for the tile to enable a visual effect
            self.tile_objects[coord].is_selected = True

        # If the selected player is the active one, show the movement overlay
        # Posts an event to the event bus
        if player_to_select is self.active_player:
            self._toggle_movement_overlay(True)
            print(f"[GameManager] ✅ Selected active player {player_to_select.player_id}.")
            self.event_bus.post("ACTIVE_PLAYER_SELECTED", player_to_select)
        else:
            print(f"[GameManager] ✅ Selected non-active player {player_to_select.player_id}.")
            self.event_bus.post("NON_ACTIVE_PLAYER_SELECTED", player_to_select)

    def move_player_to(self, destination_coord):
        """Starts a tween to move the active player along a path to the destination."""
        player = self.active_player
        start_coord = (player.q, player.r)

        # Hide the pathfinding overlay
        self.update_path_overlay(None)

        # Calculates a path from the start to the destination using A*
        path_coords = calculate_movement_path(
            player=player,
            start_coord=start_coord,
            end_coord=destination_coord,
            tile_objects=self.tile_objects,
            persistent_state=self.persistent_state
        )
        # Returns if no valid path was found
        if not path_coords:
            if DEBUG: print(f"[GameManager] ❌ A* pathfinding returned no valid path from {start_coord} to {destination_coord}.")
            return

        # ⚠️ Check if the path triggers a climate hazard
        self._check_climate_trigger_on_path(path_coords)

        # Sets a flag to indicate the player is moving
        self.is_player_moving = True

        def on_move_complete():
            # Get the destination tile to check its properties
            destination_tile = self.tile_objects.get(destination_coord)

             # Check if the destination is a "dead stop" tile by querying the profile
            if destination_tile:

                # Ask the player for the interaction type of their destination.
                interaction = player.get_interaction_for_tile(destination_tile)
                # If it's a "medium" or "bad" tile, landing on it consumes all movement.
                if interaction in ["medium", "bad"]:
                    player.remaining_movement = 0
                # Otherwise, it's a normal move, so subtract the path cost.
                else:
                    path_cost = len(path_coords) - 1
                    player.remaining_movement -= path_cost

            # Sets the player's new coordinates
            player.q, player.r = destination_coord

            # Gets the player's token from the notebook
            token = self.notebook.get(player.token_key)
            if token and 'pixel_pos' in token:

                # Removes the pixel position key to stop the animation
                del token['pixel_pos']

            # Resets the moving flag
            self.is_player_moving = False

            # Refresh the overlay: hide the old one, then calc and show the new one.
            self._toggle_movement_overlay(False)
            self._calculate_active_player_movement()
            self._toggle_movement_overlay(True)

        # Retrieves the player's drawable token from the notebook
        token_to_animate = self.notebook.get(player.token_key)

        # Creates a travel tween to animate the player's movement
        self.tween_manager.add_tween(
            target_dict=token_to_animate,
            animation_type='travel',
            drawable_type='player_token',
            on_complete=on_move_complete,
            path=path_coords,
            speed_hps=3.0
        )
                
    def _calculate_active_player_movement(self):
 
        """Calculates the move range and tags tiles with their movement colors."""
        # Clear the color tags from the previous turn's range
        for coord in self.active_player_move_range:
            tile = self.tile_objects.get(coord)
            if tile:
                # Reset both primary and secondary colors
                tile.primary_move_color = None
                tile.secondary_move_color = None

        player = self.active_player

        # Delegate the entire calculation to the pathfinding module.
        overlay_data = generate_movement_overlay_data(player, self.tile_objects, self.persistent_state)

        # The manager's only job is to apply the results for rendering.
        self.active_player_move_range = list(overlay_data.keys())
        for coord, interaction_type in overlay_data.items():
            tile = self.tile_objects.get(coord)
            if tile:
                # Set the primary color for the movement overlay.
                tile.primary_move_color = interaction_type
                # Set the secondary color for any climate hazards.

                # Checks for any active climate effects
                if self.active_climate_effect:
                    effect = self.active_climate_effect
                    
                    # Checks if the tile's terrain is a trigger for the current effect
                    if effect["trigger_type"] == "enter_terrain" and tile.terrain in effect["trigger_param"]:
                        
                        # Set the secondary color to our "hazard" style
                        tile.secondary_move_color = "hazard"
                                                
    def update_path_overlay(self, hovered_coord):
        """Calculates and updates the path from the active player to the hovered tile."""

        # Optimization: Only do work if the hovered tile has changed.
        if hovered_coord == self.last_hovered_coord:
            return
        
        # Stores the current hovered coordinate
        self.last_hovered_coord = hovered_coord

        # No matter what, if the hover coordinate has changed, the old path is invalid.
        # Clear any old path segments from the notebook.
        for key in self.path_keys:
            if key in self.notebook:

                # Removes the old path from the notebook
                del self.notebook[key]
        self.path_keys.clear()

        # --- From this point on, we only care about drawing a NEW path ---

        # Do not draw a new path if a player is already moving.
        if self.is_player_moving:
            return

        # Ensure the overlay is supposed to be visible and we have a coordinate.
        is_overlay_visible = self.selected_player and self.selected_player is self.active_player
        if not is_overlay_visible or not hovered_coord:
            return

        # Safely check if the hovered tile is a valid move target.
        hovered_tile = self.tile_objects.get(hovered_coord)
        if not hovered_tile or not getattr(hovered_tile, 'primary_move_color', None):
            return

        # If all checks pass, calculate and draw the new path.
        # Sets the starting coordinate for pathfinding
        start_coord = (self.active_player.q, self.active_player.r)
        
        # Calculates the path using A*
        path = calculate_movement_path(
            player=self.active_player,
            start_coord=start_coord,
            end_coord=hovered_coord,
            tile_objects=self.tile_objects,
            persistent_state=self.persistent_state
        )

        # Draws the path if it is valid
        if path and len(path) > 1:
            
            # Retrieves the z-index formula for path curves
            z_formula = self.persistent_state["pers_z_formulas"]['path_curve']
            
            # Iterates through each coordinate in the path
            for i, current_coord in enumerate(path):
                
                # Gets the previous and next coordinates to draw the curve segments
                prev_coord = path[i-1] if i > 0 else None
                next_coord = path[i+1] if i < len(path) - 1 else None
                
                # Calculates the z-value for the current segment
                z_value = z_formula(current_coord[1])
                
                # Creates a unique key for the path segment drawable
                key = f"path_curve_{i}"
                self.notebook[key] = {
                    'type': 'path_curve', 'coord': current_coord,
                    'prev_coord': prev_coord, 'next_coord': next_coord, 'z': z_value
                }

                # Adds the key to the list of path keys
                self.path_keys.append(key)
                
    def _toggle_movement_overlay(self, is_visible):
        """Sets the visibility of the pre-calculated movement overlay."""
        
        # If we're hiding the overlay, also clear the path
        if not is_visible:
            self.update_path_overlay(None)

        # Iterates through all tiles in the movement range
        for coord in self.active_player_move_range:
            tile = self.tile_objects.get(coord)
            if tile:

                # Toggles the movement_overlay flag on each tile
                tile.movement_overlay = is_visible

    def add_resource_to_active_player_tile(self, resource_type="stone"):
        """Adds a resource to the tile the active player is currently on."""
        player = self.active_player

        # Gets the active player's current coordinates
        coord = (player.q, player.r)

        # Retrieves the tile object at the player's coordinates
        tile = self.tile_objects.get(coord)

        if not tile:
            return

        # Ensure the 'resources' key exists in the tilebox dictionary
        if 'resources' not in tile.tilebox:
            tile.tilebox['resources'] = []
        
        # Add the new resource
        tile.tilebox['resources'].append(resource_type)
        
        print(f"[GameManager] ✅ Added '{resource_type}' to tile {coord}. Total: {len(tile.tilebox['resources'])}.")

    # 🌪️ Climate Wheel Methods
    def _initialize_climate_effects(self):
        """Populates the master list of all possible climate effects."""
        
        # Defines a dictionary of all possible climate effects
        self.master_climate_effects = {
            "desert_hazard": {
                "description": "This turn, entering Desert terrain is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["DesertDunes"]
            },
            "scrub_hazard": {
                "description": "This turn, entering Scrublands is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["Scrublands"]
            },
            "marsh_hazard": {
                "description": "This turn, entering a Marsh is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["Marsh"]
            },
            "highland_hazard": {
                "description": "This turn, entering Highlands or Hills is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["Highlands", "Hills"]
            },
            "forest_hazard": {
                "description": "This turn, entering a Forest is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["Woodlands", "ForestBroadleaf"]
            },
            "plains_hazard": {
                "description": "This turn, entering the Plains is hazardous.",
                "trigger_type": "enter_terrain",
                "trigger_param": ["Plains"]
            }
        }
        print(f"[GameManager] ✅ Initialized {len(self.master_climate_effects)} master climate effects.")

    def _select_new_climate_effect(self):
        """Picks a random climate effect for the upcoming turn."""
        
        # Gets a list of all available effects
        available_effects = list(self.master_climate_effects.values())
        
        # Randomly selects one effect
        self.active_climate_effect = random.choice(available_effects)
        
        # Prints a debug message with the selected effect
        print(f"[Climate] 🌪️ This turn's effect: {self.active_climate_effect['description']}")

    def _check_climate_trigger_on_path(self, path):
        """Checks if any tile in a given path triggers the active climate effect."""
        
        # Exits if there is no active climate effect
        if not self.active_climate_effect:
            return

        effect = self.active_climate_effect

        # Gets the list of hazardous terrains for the effect
        hazardous_terrains = effect.get("trigger_param", [])
        
        # Iterates through the path, skipping the starting tile
        for coord in path[1:]: # Iterate through the path, skipping the starting tile
            tile = self.tile_objects.get(coord)

            # Checks if the tile's terrain is a hazardous one
            if tile and tile.terrain in hazardous_terrains:
                if DEBUG: print(f"[Climate] ⚠️ Hazard Triggered! Player entered {tile.terrain} at {coord}.")
                # In the future, you would call self.draw_hazard_card() here
                return # Trigger only once per move
            
    def evolve_player_to_next_stage(self, player):
            """
            Evolves a player to the next species in their defined lineage.
            This method now just "pokes" the player to handle its own evolution.
            """
            print(f"[GameManager] ✅ Triggering evolution for Player {player.player_id}...")
            was_successful = player.evolve()
            
            if not was_successful:
                return

            # Recalculate movement for the current turn with new stats
            self._calculate_active_player_movement()