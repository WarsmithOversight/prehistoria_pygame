# game_manager.py
# This class orchestrates the game's state, including turns and active players.

import random, math
from shared_helpers import axial_distance, hex_to_pixel

DEBUG = True

class GameManager:
    """Manages the overall game state, turn progression, and active player."""

    def __init__(self, players, collectibles, camera_controller, tile_objects, event_bus, notebook, persistent_state):
        
        # Stores references to the core game systems
        self.players = players
        self.collectibles = collectibles
        self.camera_controller = camera_controller
        self.tile_objects = tile_objects
        self.event_bus = event_bus

        # Stores references to global game state objects
        self.persistent_state = persistent_state
        self.notebook = notebook
        
        # Initializes the turn and player counters
        self.turn_counter = 1
        self.active_player_index = 0

        # Pauses the game by default at the start
        self.is_paused = True

        # 👂 Subscribe to events
        self.event_bus.subscribe("DEBUG_TRIGGER_HAZARD", self.on_debug_trigger_hazard)
        self.event_bus.subscribe("MIGRATION_EVENT_SELECTED", self.on_migration_event_selected)
        # ✨ The GameManager now listens for when a move is completed to apply consequences.
        self.event_bus.subscribe("PLAYER_LANDED_ON_TILE", self.on_player_landed)


        # Initializes variables for player selection and movement
        self.selected_player = None
        self.is_player_moving = False

        # Stores the active migration event for the turn
        self.active_migration_event = None

        # Stores the coordinate of the nearest collectible for the current turn.
        self.nearest_collectible_coord = None

    def update(self, dt):
        """The main update loop for the GameManager, called every frame."""
        # We only need to update the indicator when the game is active.
        if not self.is_paused:
            self._update_nearest_collectible_indicator()

    @property
    def active_player(self):
        """A convenient property to get the current active player object."""
        # Returns the player object at the current active player index
        return self.players[self.active_player_index]

    def _setup_turn_for_player(self, player):
        """A centralized helper to prepare a player's state at the start of their turn."""
        # 1. Determine and apply any start-of-turn movement modifiers
        player.turn_movement_modifier = 0
        start_coord = (player.q, player.r)
        if start_tile := self.tile_objects.get(start_coord):
            interaction = player.get_interaction_for_tile(start_tile)
            if interaction in ["medium", "bad"]:
                player.turn_movement_modifier = -1
                print(f"[GameManager] ⚠️ Player {player.player_id} starts on difficult terrain. Movement reduced by 1.")
        player.remaining_movement = player.movement_points + player.turn_movement_modifier

        # 2. Find the nearest collectible for the new turn's objective.
        self._find_and_store_nearest_collectible()

        # 3. Select the new active player (which shows the UI)
        self._select_player(self.active_player)

        # 📢 5. Announce that all turn setup is complete and systems can now proceed.
        self.event_bus.post("TURN_READY_FOR_INPUT")

    def _start_first_turn(self):
        """Handles the sequence of events to begin the first turn of the game."""
        
        self._setup_turn_for_player(self.active_player)

        # 🎥 Announce that the camera should center on the starting player.
        self.event_bus.post("CENTER_CAMERA_ON_TILE", {
            "q": self.active_player.q, "r": self.active_player.r, "animated": True
        })

        # 📢 Announce that the first turn has officially begun.
        self.event_bus.post("TURN_STARTED")
        print(f"[GameManager] ✅ Game Start! Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")

    def advance_turn(self):
        """Advances to the next player's turn and updates the turn counter."""
        
        # Exits the function if the game is paused
        if self.is_paused: return

        # Deselects the previously selected player
        if self.selected_player:
            previous_coord = (self.selected_player.q, self.selected_player.r)
            if self.tile_objects.get(previous_coord):
                self.tile_objects[previous_coord].is_selected = False
            self.selected_player = None

        # Advance to the next player in the list
        self.active_player_index = (self.active_player_index + 1) % len(self.players)

        # 📢 Announce that the active player has officially changed.
        self.event_bus.post("ACTIVE_PLAYER_CHANGED", self.active_player)

        # 🌪️ Announce that a new turn has begun for any interested systems.
        self.event_bus.post("TURN_STARTED")

        # Increment the main turn counter only when a full round is complete
        if self.active_player_index == 0:
            self.turn_counter += 1
        
        # Announce the new turn, but wait for the migration event before setting up movement.
        print(f"[GameManager] ✅ Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn beginning...")

        # 🎥 Announce that the camera should center on the new active player.
        self.event_bus.post("CENTER_CAMERA_ON_TILE", {
            "q": self.active_player.q, "r": self.active_player.r, "animated": True
        })

    def unpause(self):
        """Starts the first turn and allows the game to proceed."""
        # 🛡️ Guard clause to prevent this from running more than once.
        if not self.is_paused: return

        # 🟢 Unpause the game state. This is the crucial missing piece.
        self.is_paused = False
        
        # ▶️ Begin the first turn sequence.
        self._start_first_turn()

    def handle_click(self, coord):
        """Handles clicks for player selection, deselection, and movement commands."""
        
        # Exits if the game is paused
        if self.is_paused: return

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
            
            # ✨ Instead of handling the move, the GameManager now just requests it.
            self.event_bus.post("REQUEST_PLAYER_MOVE", {
                "player": self.active_player,
                "destination": coord
            })
            return

        # If it's not a player or a move, it's a click on empty space.
        # Deselects whatever is currently selected
        self._select_player(None)

    def _select_player(self, player_to_select):
        """Handles the logic for selecting a player and showing their overlays."""

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

        # If the selected player is the active one, tell the UI to show the overlay
        if player_to_select is self.active_player:
            print(f"[GameManager] ✅ Selected active player {player_to_select.player_id}.")
            self.event_bus.post("ACTIVE_PLAYER_SELECTED", player_to_select)
        else:
            print(f"[GameManager] ✅ Selected non-active player {player_to_select.player_id}.")
            self.event_bus.post("NON_ACTIVE_PLAYER_SELECTED", player_to_select)

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

    def on_migration_event_selected(self, event_data):
        """Event handler for when the Migration Panel finishes its animation."""
        self.active_migration_event = event_data
        print(f"[GameManager] 🌪️ Received active migration event: {event_data.description}")

        # ✨ This is now the TRUE start of the turn's logic, which we delegate
        # to the centralized helper.
        self._setup_turn_for_player(self.active_player)

        # 5. Final turn message
        print(f"[GameManager] ✅ Player {self.active_player.player_id}'s turn is active.")

    def _check_migration_hazard_trigger_on_path(self, path):
        """Checks if any tile in a path triggers the active migration event's hazard condition."""        
        # Exits if there is no active climate event
        if not self.active_migration_event:
            return

        effect = self.active_migration_event

        # ✨ FIX: Access the attribute directly from the object, not with .get()
        hazardous_terrains = effect.trigger_param

        # Iterates through the path, skipping the starting tile
        for coord in path[1:]: # Iterate through the path, skipping the starting tile
            tile = self.tile_objects.get(coord)

            # Checks if the tile's terrain is a hazardous one
            if tile and tile.terrain in hazardous_terrains:
                if DEBUG: print(f"[GameManager] 📢 Posting REQUEST_HAZARD_EVENT due to entering {tile.terrain}.")
                # Announce the need for a hazard event; do not handle it directly.
                self.event_bus.post("REQUEST_HAZARD_EVENT", {"trigger": "migration_event"})
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

    def _find_and_store_nearest_collectible(self):
        """Finds the active player's nearest collectible and stores its coordinate."""
        player = self.active_player
        self.nearest_collectible_coord = None # Reset first

        if not self.collectibles:
            return

        # Use axial_distance for grid-based distance, which is more accurate here.
        nearest_collectible = min(
            self.collectibles,
            key=lambda c: axial_distance(player.q, player.r, c.q, c.r)
        )
        self.nearest_collectible_coord = (nearest_collectible.q, nearest_collectible.r)
        print(f"[GameManager] ✅ Nearest collectible for Player {player.player_id} is at {self.nearest_collectible_coord}.")

    def _update_nearest_collectible_indicator(self):
        """Calculates the angle to the nearest collectible and updates the drawable."""
        indicator_key = "collectible_indicator"
        player = self.active_player
        player_token = self.notebook.get(player.token_key)

        # 🧹 Cleanup: If there's no target, remove the indicator.
        if not self.nearest_collectible_coord or not player_token:
            if indicator_key in self.notebook:
                del self.notebook[indicator_key]
            return
            
        # 📍 Get Player and Target positions in WORLD coordinates.
        # This consistency is key to fixing the disappearing indicator.
        world_variable_state = {"var_current_zoom": 1.0, "var_render_offset": (0,0)}

        # Prioritize the animated world position if the player is moving.
        if 'pixel_pos' in player_token: 
            player_pos = player_token['pixel_pos'] 
        else: 
            player_pos = hex_to_pixel(player.q, player.r, self.persistent_state, world_variable_state)

        # Get the target's world position.
        target_pos = hex_to_pixel(self.nearest_collectible_coord[0], self.nearest_collectible_coord[1], self.persistent_state, world_variable_state)
 
        # 📐 Calculate Angle
        dx = target_pos[0] - player_pos[0]
        dy = target_pos[1] - player_pos[1]
        angle_deg = math.degrees(math.atan2(-dy, dx))

        # 📔 Update the Notebook
        # The renderer only needs the player's base location and the angle.
        z_formula = self.persistent_state["pers_z_formulas"]["indicator"]
        self.notebook[indicator_key] = {
            "type": "indicator",
            "q": player.q, "r": player.r, # Keep q,r for z-sorting
            "anchor_world_pos": player_pos, # Pass the definitive world position to the renderer
            "angle": angle_deg,
            "z": z_formula(player.r)
        }

    def on_debug_trigger_hazard(self, data=None):
        """Handler for a debug request to start a hazard."""
        if DEBUG: print("[GameManager] 📢 Posting REQUEST_HAZARD_EVENT due to debug trigger.")
        self.event_bus.post("REQUEST_HAZARD_EVENT", {"trigger": "debug_button"})

    def on_player_landed(self, data):
        """
        A listener that reacts to the PLAYER_LANDED_ON_TILE event. This is where
        all post-move consequences are handled by the GameManager.
        """
        player = data["player"]
        tile = data["tile"]
        path_cost = data["path_cost"]

        if not tile: return

        # --- Consequence 1: Check for Collectibles ---
        collected_item = next((c for c in self.collectibles if (c.q, c.r) == (tile.q, tile.r)), None)
        if collected_item:
            self.audio_manager.play_sfx(blacklist=["game_over_cartoon_2.wav", "error.wav", "try_again.wav", "earn_points.wav", "secret_area_unlock_1", "soft_fail"])
            player.gain_evolution_points()
            collected_item.cleanup(self.notebook, self.tween_manager)
            self.collectibles.remove(collected_item)

        # --- Consequence 2: Apply Movement Penalties ---
        interaction = player.get_interaction_for_tile(tile)
        if interaction in ["medium", "bad"]:
            player.remaining_movement = 0
        else:
            player.remaining_movement -= path_cost

        # --- Consequence 3: Check for Migration Hazard Trigger ---
        self._check_migration_hazard_trigger_on_path([(player.q, player.r)])