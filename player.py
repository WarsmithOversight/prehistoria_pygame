# player.py
# Contains the Player class that manages a player's state.

import random
from shared_helpers import oddr_to_axial, axial_to_oddr, hex_to_pixel

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
        self.token_key = f"player_token_{self.player_id}" 
        
        # Extract stats from the loaded species data
        self.movement_points = self.species_data["base_movement"]

       # Load the specific movement rules for this species
        self.terrain_movement_map = self.species_data.get("terrain_movement_map", {"default": "bad"})
        self.special_abilities = self.species_data.get("special_abilities", [])        
        self.remaining_movement = self.movement_points
        self.turn_movement_modifier = 0
        
        # Find a valid starting location
        start_coord = self._find_start_location(tile_objects)
        if not start_coord:
            raise RuntimeError(f"Could not find a valid starting tile for player {player_id} ({species_name})")
            
        self.q, self.r = start_coord

        # Initialize a pixel position for smooth movement
        self.pixel_pos = hex_to_pixel(self.q, self.r, persistent_state, {"var_current_zoom": 1.0, "var_render_offset": (0,0)})
        
        # Create the visual token in the game's notebook
        self._create_token_drawable(notebook, assets_state, persistent_state)
        print(f"[Player] ✅ Player {self.player_id} ({self.species_name}) created at {self.q},{self.r}.")

    def _find_start_location(self, tile_objects):
            """
            Finds a valid, random starting tile, prioritizing "good" tiles
            over "medium" tiles within each preferred biome.
            """
            # Get the species' biome preferences and terrain movement rules
            preferences = self.species_data["starting_region_preference"]
            movement_map = self.terrain_movement_map

            # Search through each preferred biome in order
            for biome_tag in preferences:
                good_tiles = []
                medium_tiles = []

                # Check every tile on the map to find candidates in this biome
                for coord, tile in tile_objects.items():
                    if getattr(tile, biome_tag, False):
                        # Get the movement label for this tile's terrain (e.g., "good")
                        terrain_label = movement_map.get(tile.terrain, "bad")
                        
                        # Sort the tile into the appropriate list
                        if terrain_label == "good":
                            good_tiles.append(coord)
                        elif terrain_label == "medium":
                            medium_tiles.append(coord)
                
                # Prioritize spawning on a "good" tile if one was found
                if good_tiles:
                    return random.choice(good_tiles)
                
                # If no "good" tiles were found, fall back to a "medium" tile
                if medium_tiles:
                    return random.choice(medium_tiles)
            
            # Fallback if no suitable tile is found in any preferred biome
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
            "q": self.q,
            "r": self.r,      
            "sprite": asset["sprite"],
            "scale": asset["scale"],
            "blit_offset": asset["blit_offset"],
            "z": z_value,
        }