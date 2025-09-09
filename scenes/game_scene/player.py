# scenes/game_scene/player.py
# Contains the Player class that manages a player's state.

import random
from shared_helpers import hex_to_pixel

DEBUG: True

class Player:
    """
    Represents a single player, holding their state, stats, and
    managing their token on the board.
    """
    # ────────────────────────────────────────────────── #
    # ⚙️ Initialization & State Management
    # ──────────────────────────────────────────────────
    def __init__(self, player_id, lineage_name, all_species_data, tile_objects, notebook, assets_state, persistent_state, event_bus, tween_manager, variable_state):

        # ⚙️ Set one-time player attributes that persist through evolutions
        self.player_id = player_id
        self.all_species_data = all_species_data
        self.token_key = f"player_token_{self.player_id}"
        self.evolution_points = 0
        self.event_bus = event_bus
        self.notebook = notebook
        self.persistent_state = persistent_state
        self.variable_state = variable_state
        self.tween_manager = tween_manager
        self.variable_state = variable_state # Or get from wherever it is available
        
        # 🏞️ Define a local helper to find the starting species
        def _find_starter_species_for_lineage(lineage_name, all_species_data):
            """Finds the species name that is the starter for a given lineage."""
            # Iterate through all available species
            for species_name, species_data in all_species_data.items():
                # Check if the species matches the lineage and is marked as a starter
                if species_data.get("lineage") == lineage_name and species_data.get("is_starter"):
                    return species_name
            # Return None if no starter is found
            return None

        # 🐢 Find the specific starter species from the requested lineage
        starter_species_name = _find_starter_species_for_lineage(lineage_name, all_species_data)
        if not starter_species_name:
            raise ValueError(f"Could not find a starter species for lineage '{lineage_name}'")

        # ✨ Apply the initial species data to the player object
        self._update_species_data(starter_species_name)
        
        # ❤️ Initialize population for the first time
        # This is only done once; evolutions will preserve current_population
        self.current_population = float(self.max_population)

        # 🗺️ Find a valid starting location on the game board
        start_coord = self._find_start_location(tile_objects, persistent_state)
        if not start_coord:
            raise RuntimeError(f"Could not find a valid starting tile for player {player_id} ({self.species_name})")
        
        # Set the player's initial axial coordinates
        self.q, self.r = start_coord
        
        # 🎨 Initialize a pixel position for smooth animation
        self.pixel_pos = hex_to_pixel(self.q, self.r, persistent_state, {"var_current_zoom": 1.0, "var_render_offset": (0,0)})
        
        # 🖌️ Create the visual token in the game's notebook
        self._create_token_drawable(notebook, assets_state, persistent_state)

        # Report successful creation
        print(f"[Player] ✅ Player {self.player_id} ({self.species_name}) created at {self.q},{self.r}.")

    def evolve(self):
        """
        Evolves the player to the next species in its lineage. This refreshes
        max_population but preserves current_population.
        Returns True if evolution was successful, False otherwise.
        """
        # 🐢 Get the name of the species to evolve into from the current species data
        next_species_name = self.species_data.get("evolves_to")

        # ❌ Check if the evolution path exists
        if not next_species_name or next_species_name not in self.all_species_data:
            print(f"[Player] ⚠️ {self.species_name} is at the end of its lineage and cannot evolve further.")
            return False
        
        # ✨ Update all species-specific data to the new species
        self._update_species_data(next_species_name)
        
        # Evolution was successful
        return True

    # ────────────────────────────────────────────────── #
    # 헬 Helpers
    # ──────────────────────────────────────────────────
    def _update_species_data(self, species_name):
        """
        A helper to set or refresh all stats derived from a species data block.
        This is called on initialization and each time the player evolves.
        """
        # 🐢 Set the new species name and get its corresponding data block
        self.species_name = species_name
        self.species_data = self.all_species_data[self.species_name]
        
        # ❤️ Refresh core stats from the new species data
        self.max_population = self.species_data.get("max_population")
        self.movement_points = self.species_data["base_movement"]
        self.remaining_movement = self.movement_points 
        self.turn_movement_modifier = 0
        
        # 📊 Refresh hazard resolution stats
        self.fight = int(self.species_data.get("fight", 0))
        self.flight = int(self.species_data.get("flight", 0))
        self.freeze = int(self.species_data.get("freeze", 0))
        self.climate_resistance = int(self.species_data.get("climate_resistance", 0))
        self.territoriality = int(self.species_data.get("territoriality", 0))
        self.climate_resistance = int(self.species_data.get("climate_resistance", 0))

        # 🗺️ Parse all pathfinding rules into quickly accessible attributes
        pathfinding_data = self.species_data.get("pathfinding", {})
        self.pathfinding_profiles = pathfinding_data.get("profiles", [])
        self.movement_overrules = pathfinding_data.get("overrules", {})
        
        # 🧭 Compile the terrain interactions into a simple lookup dictionary for performance
        self.terrain_interactions = {}
        interactions = pathfinding_data.get("interactions", {})
        for interaction_type, terrain_list in interactions.items():
            for terrain in terrain_list:
                self.terrain_interactions[terrain] = interaction_type
       
        # Report the change
        print(f"[Player] ✅ Player {self.player_id} species set to {self.species_name}.")

    def take_population_damage(self, amount):
            """
            Reduces current population by a given amount and posts an event if a
            change occurred.
            """
            # ❤️ Store the population before applying damage to check for changes.
            old_population = self.current_population
    
            # 🛡️ Decrease the current population, ensuring it doesn't go below zero.
            self.current_population = max(0, self.current_population - amount)
    
            # 📢 If the population actually changed, announce it to the event bus.
            if self.current_population != old_population:
                print(f"[Player] 💔 Player {self.player_id} took {amount} damage. Population is now {self.current_population}.")
                
                self.event_bus.post("PLAYER_POPULATION_CHANGED", {
                    "player_id": self.player_id,
                    "species_name": self.species_name,
                    "current_population": self.current_population,
                    "max_population": self.max_population
                })

                # 🎨 Trigger the glow pulse animation via your tween manager
                # ✨ Target the single, shared glow drawable now.
                glow_drawable = self.notebook.get('SCREEN_GLOW')
                if glow_drawable:
                # If population drops to exactly 1, trigger the persistent glow.
                    if self.current_population == 1:
                        # A single tween to fade the glow in and hold it.
                        self.tween_manager.add_tween(
                            target_dict=glow_drawable, animation_type='value',
                            key_to_animate='alpha', start_val=glow_drawable['alpha'], end_val=70, duration=1.5
                        )

                    # If population drops but is not 1 and not 0, trigger a pulse.
                    elif self.current_population > 0:

                        # --- Create a more dramatic two-stage pulse ---
                        def create_slow_fade_out():
                            self.tween_manager.add_tween(
                                target_dict=glow_drawable, animation_type='value',
                                key_to_animate='alpha', start_val=255, end_val=0, duration=0.8
                            )
        
                        # 1. A very fast, bright flash-in.
                        self.tween_manager.add_tween(
                            target_dict=glow_drawable, animation_type='value',
                            key_to_animate='alpha', start_val=glow_drawable['alpha'], end_val=255, duration=0.1,
                            on_complete=create_slow_fade_out
                        )

                        # ✨ NEW: Trigger the screen shake at the same time as the glow pulse.
                        self.trigger_screen_shake()

                    # Optional: If population drops to 0, fade the glow out.
                    else:
                        self.tween_manager.add_tween(
                            target_dict=glow_drawable, animation_type='value',
                            key_to_animate='alpha', start_val=glow_drawable['alpha'], end_val=0, duration=0.5
                        )

            # ✨ Check for extinction after applying damage.
            if self.current_population <= 0:
                print(f"[Player] ☠️ Player {self.player_id} ({self.species_name}) has gone extinct.")
                self.event_bus.post("PLAYER_EXTINCT", {
                    "player": self
                })


    def trigger_screen_shake(self):
        """A helper to create a slight camera shake effect."""
        # The key we want to animate inside the variable_state dictionary
        target_key = 'var_render_offset'
        
        shake_amount = 4 # Pixels - keep this small for a 'slight' shake
        
        # Get the current position tuple
        start_pos = self.variable_state.get(target_key, (0, 0))
        shake_pos = (start_pos[0] + shake_amount, start_pos[1] - shake_amount)

        # This function will be called after the first shake to return the camera to normal
        def shake_back():
            self.tween_manager.add_tween(
                target_dict=self.variable_state, animation_type='value', drawable_type='generic',
                key_to_animate=target_key,
                start_val=shake_pos, end_val=start_pos, duration=0.15
            )

        # Start the first tween to shake the camera
        self.tween_manager.add_tween(
            target_dict=self.variable_state, animation_type='value', drawable_type='generic',
            key_to_animate=target_key,
            start_val=start_pos, end_val=shake_pos, duration=0.1,
            on_complete=shake_back
        )

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
                    # If required, must an optional tags
                    if check_tags and not any(getattr(tile, tag, False) for tag in optional_tags):
                        continue
                    
                    matches.append(coord)
                return matches

            # Tier 1: Check primary biome with preferred terrain AND optional tags
            best_tiles = find_matches(primary_biome, check_tags=True)
            print(f"[Player] 🔬 Found {len(best_tiles)} perfect tiles in '{primary_biome}' biome with optional tags.")
            if best_tiles:
                print(f"[Player] ✅ Found a starting tile for {self.species_name} in {primary_biome} with optional tags.")
                return random.choice(best_tiles)

            # Tier 2: Check secondary biome with preferred terrain AND optional tags
            if secondary_biome:
                better_tiles = find_matches(secondary_biome, check_tags=True)
                print(f"[Player] 🔬 Found {len(better_tiles)} perfect tiles in secondary biome '{secondary_biome}' with optional tags.")
                if better_tiles:
                    print(f"[Player] ✅ Found a starting tile for {self.species_name} in a secondary biome ({secondary_biome}) with optional tags.")
                    return random.choice(better_tiles)
            
            # Tier 3: Widen search to primary biome with just preferred terrain
            good_tiles = find_matches(primary_biome, check_tags=False)
            if good_tiles:
                print(f"[Player] ✅ Found a starting tile for {self.species_name} in {primary_biome} without using optional tags.")
                return random.choice(good_tiles)

            # Tier 4: Final fallback to secondary biome with just preferred terrain
            if secondary_biome:
                okay_tiles = find_matches(secondary_biome, check_tags=False)
                if okay_tiles:
                    print(f"[Player] ✅ Found a starting tile for {self.species_name} in a secondary biome ({secondary_biome}) without optional tags.")
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
            "type": "artwork",
            "asset_category": "player_assets",
            "asset_key": species_sprite_name,
            "q": self.q,
            "r": self.r,      
            "z": z_value,
        }
    
    def gain_evolution_points(self, points=1):
        """
        Increases the player's evolution points by a given amount and prints a confirmation.
        """
        # 📈 Add the specified number of points to the player's current total.
        self.evolution_points += points
        
        # 🔊 Print a success message to the console for confirmation.
        print(f"[Player {self.player_id}] ✅ Gained {points} EP! Total: {self.evolution_points}.")