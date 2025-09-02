# player.py
# Contains the Player class that manages a player's state.

import random
from shared_helpers import hex_to_pixel

DEBUG: True

class Player:
    """
    Represents a single player, holding their state, stats, and
    managing their token on the board.
    """
    def __init__(self, player_id, lineage_name, all_species_data, tile_objects, notebook, assets_state, persistent_state):

        # ⚙️ Core State & Data
        self.player_id = player_id
        self.all_species_data = all_species_data
        self.token_key = f"player_token_{self.player_id}" 
        
        def _find_starter_species_for_lineage(lineage_name, all_species_data):
            """Finds the species name that is the starter for a given lineage."""
            for species_name, species_data in all_species_data.items():
                if species_data.get("lineage") == lineage_name and species_data.get("is_starter"):
                    return species_name
            return None

        # Find the specific starter species from the requested lineage
        starter_species_name = _find_starter_species_for_lineage(lineage_name, all_species_data)
        if not starter_species_name:
            raise ValueError(f"Could not find a starter species for lineage '{lineage_name}'")

        # ✨ FIX: Call the correctly renamed function.
        self._update_species_data(starter_species_name, all_species_data)
        
        # Find a valid starting location
        start_coord = self._find_start_location(tile_objects, persistent_state)
        if not start_coord:
            raise RuntimeError(f"Could not find a valid starting tile for player {player_id} ({self.species_name})")
            
        self.q, self.r = start_coord

        # Initialize a pixel position for smooth movement
        self.pixel_pos = hex_to_pixel(self.q, self.r, persistent_state, {"var_current_zoom": 1.0, "var_render_offset": (0,0)})
        
        # Create the visual token in the game's notebook
        self._create_token_drawable(notebook, assets_state, persistent_state)
        print(f"[Player] ✅ Player {self.player_id} ({self.species_name}) created at {self.q},{self.r}.")

    def _update_species_data(self, species_name, all_species_data):
        """A helper to set or refresh all stats from a species data block."""
        self.species_name = species_name
        self.species_data = all_species_data[self.species_name]
        pathfinding_data = self.species_data.get("pathfinding", {})
        
        # Refresh core stats
        self.movement_points = self.species_data["base_movement"]
        self.remaining_movement = self.movement_points 
        self.turn_movement_modifier = 0

        # Parse all pathfinding rules directly into the player object.
        self.pathfinding_profiles = pathfinding_data.get("profiles", [])
        self.movement_overrules = pathfinding_data.get("overrules", {})
        
        # Compile the terrain interactions into a simple lookup dictionary.
        self.terrain_interactions = {}
        interactions = pathfinding_data.get("interactions", {})
        for interaction_type, terrain_list in interactions.items():
            for terrain in terrain_list:
                self.terrain_interactions[terrain] = interaction_type
       
        print(f"[Player] ✅ Player {self.player_id} is now a {self.species_name}.")

    # ✨ NEW: Add the helper method for GameManager.
    def get_interaction_for_tile(self, tile):
        """
        Determines the consequential interaction type for a tile, respecting overrides.
        This allows the GameManager to query the player's rules without needing to
        know the internal implementation.
        """
        # The `riverine` profile overrides all other interactions for river tiles.
        if "riverine" in self.pathfinding_profiles and getattr(tile, 'river_data', None):
            return "good"
        
        # Otherwise, look up the tile's base terrain interaction.
        return self.terrain_interactions.get(tile.terrain)

    def _find_start_location(self, tile_objects, persistent_state):
            """
            Finds a valid starting tile using a tiered search logic, prioritizing
            optional tags and primary biomes.
            """
            
            # Get starting location rules directly from the player's species data.
            rules = self.species_data.get("pathfinding", {}).get("starting_location", {})
            search_biomes = rules.get("search_biomes", [])
            preferred_terrain = rules.get("preferred_terrain", [])
            optional_tags = rules.get("optional_tags", [])
            biome_map = persistent_state.get("pers_biome_map", {})

            # Ensure we have at least one biome to search in
            if not search_biomes:
                print(f"[Player] ❌ No search_biomes defined for {self.species_name}.")
                return None

            primary_biome = search_biomes[0]
            secondary_biome = search_biomes[1] if len(search_biomes) > 1 else None

            # This helper function will find matching tiles for a given set of criteria
            def find_matches(biome_name, check_tags):
                matches = []
                if not biome_name: return matches
                
                candidate_coords = biome_map.get(biome_name, [])
                for coord in candidate_coords:
                    tile = tile_objects.get(coord)

                    # A starting tile must be passable and have a defined interaction.
                    if not tile or not tile.passable or tile.terrain not in self.terrain_interactions:
                        continue

                    # Must match preferred terrain
                    if tile.terrain not in preferred_terrain:
                        continue
                    # If required, must have all optional tags
                    if check_tags and not all(getattr(tile, tag, False) for tag in optional_tags):
                        continue
                    
                    matches.append(coord)
                return matches

            # Tier 1: Check primary biome with preferred terrain AND optional tags
            best_tiles = find_matches(primary_biome, check_tags=True)
            if best_tiles:
                return random.choice(best_tiles)

            # Tier 2: Check secondary biome with preferred terrain AND optional tags
            if secondary_biome:
                better_tiles = find_matches(secondary_biome, check_tags=True)
                if better_tiles:
                    return random.choice(better_tiles)
            
            # Tier 3: Widen search to primary biome with just preferred terrain
            good_tiles = find_matches(primary_biome, check_tags=False)
            if good_tiles:
                return random.choice(good_tiles)

            # Tier 4: Final fallback to secondary biome with just preferred terrain
            if secondary_biome:
                okay_tiles = find_matches(secondary_biome, check_tags=False)
                if okay_tiles:
                    return random.choice(okay_tiles)

            # If all checks fail, we fail loudly as requested.
            print(f"[Player] ❌ No suitable starting tile found for {self.species_name} after all checks.")
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

    def evolve(self):
        """
        Evolves the player to the next species in its lineage.
        Returns True if evolution was successful, False otherwise.
        """
        next_species_name = self.species_data.get("evolves_to")

        if not next_species_name or next_species_name not in self.all_species_data:
            print(f"[Player] ⚠️ {self.species_name} is at the end of its lineage.")
            return False

        # ✨ FIX: Call the correctly renamed function.
        self._update_species_data(next_species_name, self.all_species_data)
        return True