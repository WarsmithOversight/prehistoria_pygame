# player.py
# Contains the Player class that manages a player's state.

import random

class Player:
    """
    Represents a single player, holding their state, stats, and
    managing their token on the board.
    """
    def __init__(self, player_id, species_name, all_species_data, tile_objects, notebook, assets_state, persistent_state):
        # ──────────────────────────────────────────────────
        # ⚙️ Core State & Data
        # ──────────────────────────────────────────────────
        self.player_id = player_id
        self.species_name = species_name
        self.species_data = all_species_data[species_name]
        
        # Extract stats from the loaded species data
        self.movement_points = self.species_data["base_movement"]
        
        # Find a valid starting location
        start_coord = self._find_start_location(tile_objects)
        if not start_coord:
            raise RuntimeError(f"Could not find a valid starting tile for player {player_id} ({species_name})")
            
        self.q, self.r = start_coord
        
        # Create the visual token in the game's notebook
        self._create_token_drawable(notebook, assets_state, persistent_state)
        print(f"[Player] ✅ Player {self.player_id} ({self.species_name}) created at {self.q},{self.r}.")

    def _find_start_location(self, tile_objects):
        """
        Finds a valid, random starting tile based on species preferences.
        """
        # Get this species' preferred biomes and movement costs
        preferences = self.species_data["starting_region_preference"]
        movement_costs = self.species_data["movement_costs"]

        # Search for a valid tile, respecting preference order
        for biome_tag in preferences:
            possible_tiles = []
            for coord, tile in tile_objects.items():
                # Check if the tile is in the preferred biome
                if getattr(tile, biome_tag, False):
                    # Check if the terrain is passable for this species
                    terrain_cost = movement_costs.get(tile.terrain, movement_costs["default"])
                    if terrain_cost > 0:
                        possible_tiles.append(coord)
            
            # If we found any valid tiles in this biome, pick one and we're done
            if possible_tiles:
                return random.choice(possible_tiles)
        
        # Fallback if no preferred tiles are found (should be rare)
        return None

    def _create_token_drawable(self, notebook, assets_state, persistent_state):
        """
        Creates the drawable dictionary for the player's token
        and adds it to the notebook for rendering.
        """
        token_key = f"player_token_{self.player_id}"
        species_sprite_name = self.species_data["sprite"]
        asset = assets_state["player_assets"][species_sprite_name]
        
        # Get the Z-value from the renderer's formula
        z_formula = persistent_state["pers_z_formulas"]["player_token"]
        z_value = z_formula(self.r)

        # Create the dictionary that the renderer will use to draw the token
        notebook[token_key] = {
            "type": "player_token",
            "coord": (self.q, self.r),
            "sprite": asset["sprite"],
            "scale": asset["scale"],
            "blit_offset": asset["blit_offset"],
            "z": z_value,
        }