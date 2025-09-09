# game_manager.py
# This class orchestrates the game's state, including turns and active players.

import random, math
from shared_helpers import axial_distance, hex_to_pixel

DEBUG = True

class GameManager:
    """Manages the overall game state, turn progression, and active player."""

    def __init__(self, players, camera_controller, tile_objects, event_bus, notebook, persistent_state, tween_manager, hazard_manager):
        
        # Stores references to the core game systems
        self.players = players
        self.camera_controller = camera_controller
        self.tile_objects = tile_objects
        self.event_bus = event_bus
        self.tween_manager = tween_manager
        self.hazard_manager = hazard_manager

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
        # ✨ The GameManager now listens for when a move is completed to apply consequences.
        self.event_bus.subscribe("PLAYER_LANDED_ON_TILE", self.on_player_landed)
        self.event_bus.subscribe("PLAYER_EXTINCT", self.on_player_extinct)
        self.event_bus.subscribe("REQUEST_TILE_CONSEQUENCE", self.on_tile_consequence_requested)
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)

        # Initializes variables for player selection and movement
        self.selected_player = None
        self.is_player_moving = False

        # Stores the active migration event for the turn
        self.active_migration_event = None

    def update(self, dt):
        """The main update loop for the GameManager, called every frame."""
        pass # The GameManager currently has no per-frame updates.

    @property
    def active_player(self):
        """A convenient property to get the current active player object."""
        # Returns the player object at the current active player index
        return self.players[self.active_player_index]

    def _setup_turn_for_player(self, player):
        """A centralized helper to prepare a player's state at the start of their turn."""
        # ✨ This method's only remaining job is to select the new active player.
        # Movement calculation is now fully delegated to the MovementManager.
        self._select_player(self.active_player)

    def _start_first_turn(self):
        """Handles the sequence of events to begin the first turn of the game."""
        
        # 🎥 Announce that the camera should center on the starting player.
        self.event_bus.post("CENTER_CAMERA_ON_TILE", {
            "q": self.active_player.q, "r": self.active_player.r, "animated": True
        })

        # 📢 Announce that the first turn has officially begun.
        self.event_bus.post("TURN_STARTED", {"player": self.active_player})
        print(f"[GameManager] ✅ Game Start! Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn.")

        # ✨ Set the initial glow state for the first player.
        self.on_active_player_changed(self.active_player)

        # ✨ Select the player *after* the TURN_STARTED event has been posted.
        self._setup_turn_for_player(self.active_player)

    def advance_turn(self):
        """Advances to the next player's turn and updates the turn counter."""

        # 🛑 Guard Clause: Do not advance the turn if a hazard is active.
        if self.hazard_manager.is_active:
            print("[GameManager] ⚠️ Cannot advance turn while a hazard event is active.")
            return

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
        self.event_bus.post("TURN_STARTED", {"player": self.active_player})

        # Increment the main turn counter only when a full round is complete
        if self.active_player_index == 0:
            self.turn_counter += 1
        
        # Announce the new turn, but wait for the migration event before setting up movement.
        print(f"[GameManager] ✅ Turn {self.turn_counter}, Player {self.active_player.player_id}'s turn beginning...")

        # 🎥 Announce that the camera should center on the new active player.
        self.event_bus.post("CENTER_CAMERA_ON_TILE", {
            "q": self.active_player.q, "r": self.active_player.r, "animated": True
        })

        # ✨ This is the crucial fix: set up the new player at the start of their turn.
        self._setup_turn_for_player(self.active_player)

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

    def on_player_extinct(self, data):
        """Pauses the game when a player goes extinct."""
        print("[GameManager] ⏸️ Player has gone extinct. Pausing game.")
        self.is_paused = True

    def on_active_player_changed(self, new_player):
        """
        A listener that updates the persistent screen glow based on the new active
        player's state. This centralizes control of the glow.
        """
        glow_drawable = self.notebook.get('SCREEN_GLOW')
        if not glow_drawable: return
 
        # 🛑 Cancel any existing tweens (like a damage pulse) to ensure a clean state change.
        self.tween_manager.remove_tweens_by_target(glow_drawable)
 
        # 🎯 Determine the target alpha based on the new player's health.
        target_alpha = 0
        if new_player.current_population == 1:
            target_alpha = 70 # The persistent low-health glow value
        
        # ✨ Gently fade the glow to its new state for the current turn.
        self.tween_manager.add_tween(
            target_dict=glow_drawable, animation_type='value',
            key_to_animate='alpha',
            start_val=glow_drawable['alpha'],
            end_val=target_alpha,
            duration=0.5
        )

    def evolve_player_to_next_stage(self, player):
            """
            Evolves a player to the next species in their defined lineage.
            This method now just "pokes" the player to handle its own evolution.
            """
            print(f"[GameManager] ✅ Triggering evolution for Player {player.player_id}...")
            was_successful = player.evolve()
            
            if not was_successful:
                return

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

        # --- Consequence 2: Apply Movement Penalties ---
        interaction = player.get_interaction_for_tile(tile)
        if interaction == "bad":
            player.remaining_movement = 0
            print(f"[GameManager] ❌ Player landed on 'bad' terrain. Movement set to 0 and 1 damage taken.")
            player.take_population_damage(1)
        elif interaction == "medium":
            player.remaining_movement = 0
            print(f"[GameManager] ⚠️ Player landed on 'medium' terrain. Movement set to 0.")
        else: # This handles 'good' and None interactions
            player.remaining_movement -= path_cost

    def on_tile_consequence_requested(self, data):
        """
        Applies consequences like population damage when requested by another system.
        This keeps the GameManager as the sole arbiter of player stats.
        """
        player = data["player"]
        consequence = data["consequence"]

        if consequence == "population_damage":
            amount = data.get("amount", 1)
            print(f"[GameManager] ❌ Applying population damage to Player {player.player_id}.")
            player.take_population_damage(amount)

