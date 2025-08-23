# game_manager.py
# This class orchestrates the game's state, including turns and active players.

class GameManager:
    """Manages the overall game state, turn progression, and active player."""

    def __init__(self, players, camera_controller, tile_objects, event_bus, persistent_state, variable_state):
        # ──────────────────────────────────────────────────
        # ⚙️ Core State
        # ──────────────────────────────────────────────────
        self.players = players
        self.camera_controller = camera_controller
        self.tile_objects = tile_objects
        self.event_bus = event_bus

        self.persistent_state = persistent_state
        self.variable_state = variable_state
        
        self.turn_counter = 1
        self.active_player_index = 0
        self.selected_player = None

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

        # Print a status update
        print(f"[GameManager] ✅ Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")

    def handle_click(self, coord):
            """Handles a click on the map, processing player selection and posting events."""

            # ──────────────────────────────────────────────────
            # ⚪ Deselect Previous Player
            # ──────────────────────────────────────────────────
            # Check if a player was already selected from a previous click
            if self.selected_player:
                
                # Find the tile the previously selected player was on
                previous_coord = (self.selected_player.q, self.selected_player.r)
                previous_tile = self.tile_objects.get(previous_coord)
                
                # Turn off the glow on that tile
                if previous_tile:
                    previous_tile.is_selected = False
                
                # Clear the selected player state
                self.selected_player = None

            # ──────────────────────────────────────────────────
            # 🟢 Select New Player
            # ──────────────────────────────────────────────────
            # Check if the click was on any player's token
            player_found_at_coord = False
           
            for player in self.players:

                if (player.q, player.r) == coord:

                    player_found_at_coord = True

                    print(f"[GameManager] ✅ Click matches player {player.player_id}'s location.")
                    # Set this player as the currently selected one
                    self.selected_player = player
                    
                    # Find the tile the newly selected player is on
                    newly_selected_tile = self.tile_objects.get(coord)
                    
                    # Turn on the glow for that tile
                    if newly_selected_tile:
                        newly_selected_tile.is_selected = True

                    # ──────────────────────────────────────────────────
                    # 📢 Post Event
                    # ──────────────────────────────────────────────────
                    # Check if the selected player is the active one for this turn
                    if player is self.active_player:
                        # Announce that the ACTIVE player was selected
                        self.event_bus.post("ACTIVE_PLAYER_SELECTED", player)
                    else:
                        # Announce that a NON-ACTIVE player was selected
                        self.event_bus.post("NON_ACTIVE_PLAYER_SELECTED", player)
                    
                    # Stop checking once we've found the clicked player
                    return
                