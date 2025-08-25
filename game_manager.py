# game_manager.py
# This class orchestrates the game's state, including turns and active players.

from shared_helpers import get_tiles_in_range, a_star_pathfind, hex_to_pixel

class GameManager:
    """Manages the overall game state, turn progression, and active player."""

    def __init__(self, players, camera_controller, tile_objects, event_bus, tween_manager, notebook, persistent_state, variable_state):
        # ──────────────────────────────────────────────────
        # ⚙️ Core State
        # ──────────────────────────────────────────────────
        self.tween_manager = tween_manager
        self.players = players
        self.camera_controller = camera_controller
        self.tile_objects = tile_objects
        self.event_bus = event_bus

        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.notebook = notebook
        self.path_keys = [] # Keep track of our path drawables
        
        self.turn_counter = 1
        self.active_player_index = 0
        self.selected_player = None
        self.is_player_moving = False

        self.active_player_move_range = [] # Stores coords for the current turn's overlay

        # Pre-calculate the movement range for the first player
        self._calculate_active_player_movement()


        # Announce the start of the game
        print(f"[GameManager] ✅ Game Start! Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")
        # Center on the first player to begin
        # Pass the required arguments in the call
        self.camera_controller.center_on_tile(
            self.active_player.q, self.active_player.r, 
            self.persistent_state, self.variable_state
        )

    @property
    def active_player(self):
        """A convenient property to get the current active player object."""
        return self.players[self.active_player_index]

    def advance_turn(self):
        """Advances to the next player's turn and updates the turn counter."""

        # 🧽 Clean up the previous turn's state 
        # Hide the movement overlay if it was visible
        self._toggle_movement_overlay(False)

        # Deselect any player that was left selected
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

        # Pre-calculate the movement range for the new active player
        self._calculate_active_player_movement()

        # Print a status update
        print(f"[GameManager] ✅ Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")

    def handle_click(self, coord):
        """Handles a click on the map, processing player selection and posting events."""
        
        if self.is_player_moving:
            return
        
        # Check if the click is on a valid move destination
        clicked_tile = self.tile_objects.get(coord)
        if clicked_tile and clicked_tile.move_color and self.selected_player is self.active_player:
            self.move_player_to(coord)
            return

        # On any click, first hide the movement overlay and deselect the current player
        self._toggle_movement_overlay(False)
        if self.selected_player:
            previous_coord = (self.selected_player.q, self.selected_player.r)
            if self.tile_objects.get(previous_coord):
                self.tile_objects[previous_coord].is_selected = False
            self.selected_player = None


        # Now, check if the click was on a new player
        for player in self.players:
            if (player.q, player.r) == coord:
                # Select the new player and turn on their tile's selection glow
                self.selected_player = player
                if self.tile_objects.get(coord):
                    self.tile_objects[coord].is_selected = True

                # If the selected player is the active one, show the movement overlay
                if player is self.active_player:
                    self._toggle_movement_overlay(True)
                    print(f"[GameManager] ✅ Selected active player {player.player_id}.")
                    self.event_bus.post("ACTIVE_PLAYER_SELECTED", player)
                else:
                    print(f"[GameManager] ✅ Selected non-active player {player.player_id}.")
                    self.event_bus.post("NON_ACTIVE_PLAYER_SELECTED", player)
                return

    def move_player_to(self, destination_coord):
        """Starts a tween to move the active player along a path to the destination."""
        player = self.active_player
        start_coord = (player.q, player.r)

        path_coords = a_star_pathfind(
            self.tile_objects, start_coord, destination_coord, self.persistent_state, player
        )

        if not path_coords:
            return

        self.is_player_moving = True
        
        def on_move_complete():
            # Update the player object's official state
            player.q, player.r = destination_coord
            
            # Snap the drawable's final q,r back to integers for perfect alignment
            token = self.notebook.get(player.token_key)
            if token and 'pixel_pos' in token:
                del token['pixel_pos']

            self.is_player_moving = False
                            
        # Get the player's drawable "buddy" from the notebook
        token_to_animate = self.notebook.get(player.token_key)
        z_formula = self.persistent_state["pers_z_formulas"]["player_token"]   

        # Call the new tweener with the hex path
        self.tween_manager.add_tween(
            target_dict=token_to_animate,
            animation_type='travel',
            drawable_type='player_token',
            on_complete=on_move_complete,
            path=path_coords,
            speed_hps=3.0
        )
        
    def _calculate_active_player_movement(self):
        """Calculates the move range and tags tiles with their movement color."""
        # Clear the color tags from the previous turn's range
        for coord in self.active_player_move_range:
            tile = self.tile_objects.get(coord)
            if tile:
                tile.move_color = None

        player = self.active_player

        # Get all tiles within the player's movement point radius
        tiles_in_range = get_tiles_in_range(
            (player.q, player.r),
            player.movement_points,
            self.tile_objects,
            self.persistent_state
        )

        # Store the new range and tag the tiles within it with the correct color
        self.active_player_move_range = list(tiles_in_range)
        for coord in self.active_player_move_range:
            tile = self.tile_objects.get(coord)
            if tile:
                # If the player has the river movement ability, treat river tiles as "good"
                if "river_movement" in player.special_abilities and getattr(tile, 'river_data', None):
                    tile.move_color = "good"
                else:
                    # Otherwise, use the standard terrain-based color
                    terrain_label = player.terrain_movement_map.get(tile.terrain, None) # if no movement rule exists, the species treats it as impassable
                    tile.move_color = terrain_label

    def update_path_overlay(self, hovered_coord):
        """Calculates and updates the path from the active player to the hovered tile."""
        
        # Clear any old path segments from the notebook
        for key in self.path_keys:
            if key in self.notebook:
                del self.notebook[key]
        self.path_keys.clear()

        # Ensure the active player is selected and the hovered tile is valid
        is_overlay_visible = self.selected_player and self.selected_player is self.active_player
        if not is_overlay_visible or not hovered_coord:
            return

        # Check if the hovered tile is a valid move target (it has a move_color)
        hovered_tile = self.tile_objects.get(hovered_coord)
        if not hovered_tile or not hovered_tile.move_color:
            return

        # Calculate the path using A*
        start_coord = (self.active_player.q, self.active_player.r)
        path = a_star_pathfind(
            self.tile_objects,
            start_coord,
            hovered_coord,
            self.persistent_state,
            self.active_player
        )

        # If a path was found, create a drawable curve for each tile in the path
        if path and len(path) > 1:

            z_formula = self.persistent_state["pers_z_formulas"]['path_curve']

            for i, current_coord in enumerate(path):
                prev_coord = path[i-1] if i > 0 else None
                next_coord = path[i+1] if i < len(path) - 1 else None
                
                z_value = z_formula(current_coord[1])
                
                key = f"path_curve_{i}"
                self.notebook[key] = {
                    'type': 'path_curve',
                    'coord': current_coord,
                    'prev_coord': prev_coord,
                    'next_coord': next_coord,
                    'z': z_value
                }
                self.path_keys.append(key)

    def _toggle_movement_overlay(self, is_visible):
        """Sets the visibility of the pre-calculated movement overlay."""
        # If we're hiding the overlay, also clear the path
        if not is_visible:
            self.update_path_overlay(None)

        for coord in self.active_player_move_range:
            tile = self.tile_objects.get(coord)
            if tile:
                tile.movement_overlay = is_visible