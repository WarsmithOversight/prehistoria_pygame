# rivers.py

from shared_helpers import get_neighbors, get_direction_bit

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

RIVER_DENSITY_FACTOR = 5.0                  # Sets the base number of rivers per 100 land tiles.
RIVER_CANDIDATES_PER_FINAL_RIVER = 4.0      # For each final river, generate this many candidates and pick the best.
MEANDER_THRESHOLD = 0.4                     # The normalized distance from the ocean at which rivers can start to meander.

# ──────────────────────────────────────────────────
# 🌊 River Generation
# ──────────────────────────────────────────────────


def _generate_river_paths(tiledata, persistent_state):
    """
    Selects the best N river sources based on elevation and generates
    a path for each, then culls the shortest results.
    """
    
    # 🏞️ Determine Target River Counts
    # Calculate the target number of final rivers based on the number of land tiles
    land_tile_count = persistent_state.get("pers_land_count", 0)
    target_final_river_count = max(1, int((land_tile_count / 100) * RIVER_DENSITY_FACTOR))

    # Calculate the number of candidate rivers to generate, which is greater than the final target
    target_candidate_count = int(target_final_river_count * RIVER_CANDIDATES_PER_FINAL_RIVER)
    print(f"[rivers] ✅ Final Target: {target_final_river_count} rivers. Generating {target_candidate_count} candidates.")

    # ✍️ Select River Sources
    # Get all valid land tiles
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    all_land_tiles = [
        tiledata[coord] for coord in land_coords 
        if 'final_elevation' in tiledata[coord]
    ]
    
    # Sort the list of tiles from highest to lowest elevation
    all_land_tiles.sort(key=lambda x: x['final_elevation'], reverse=True)

    # Initialize the required buckets
    river_sources = []
    occupied_coords = set()

    # Generate valid candidates until target numer is met
    for tile in all_land_tiles:
        if len(river_sources) >= target_candidate_count:
            break

        # Skip candidates that are coast or adjacent to an earlier candidate
        coord = tile['coord']
        if tile.get("is_coast") or coord in occupied_coords:
            continue

        # Add the tile to our candidates list
        river_sources.append(tile)

        # Save its neighbors as occupied
        occupied_coords.add(coord)
        for neighbor_coord in get_neighbors(coord[0], coord[1], persistent_state):
            occupied_coords.add(neighbor_coord)

    print(f"[rivers] ✅ Selected {len(river_sources)} highest, non-adjacent, non-coastal tiles as sources.")

    # 💧 Generate River Paths
    all_river_paths = []

    for source_tile in river_sources:

        # Generate a single river path for each source tile
        path = _generate_single_river(source_tile, tiledata, persistent_state)

        # Add the generated path to the list if it's long enough to be a river
        if len(path) > 1:
            all_river_paths.append(path)
    
    # ✂️ Cull Shorter Paths
    # Check if any river paths were generated
    if all_river_paths:

        def get_effective_length(path):
            dest_tile = tiledata.get(path[-1])
            # Give a bonus to rivers that terminate in lowlands (marshes).
            if dest_tile and dest_tile.get("lowlands"):
                return len(path) + 1
            return len(path)

        # Sort all generated paths by their length
        all_river_paths.sort(key=get_effective_length)

        # Determine the number of longest rivers to keep
        num_to_keep = min(target_final_river_count, len(all_river_paths))

        # Slice the list to keep only the longest paths
        final_paths = all_river_paths[-num_to_keep:]
        
        print(f"[rivers] ✅ From {len(all_river_paths)} candidates, selected {len(final_paths)} longest rivers.")
        
        return final_paths
        
    print(f"[rivers] ⚠️ No rivers were successfully generated.")

    return []

def _generate_single_river(source_tile, tiledata, persistent_state):
    """
    REFACTORED: Generates a single river path from a given source tile.
    Contains the core pathfinding logic.
    """

    # Initialize the path with the starting tile
    current_path = [source_tile['coord']]
    current_coord = source_tile['coord']
    
    # Iterate to grow the river, with a safety limit
    for _ in range(150): 
        current_tile = tiledata[current_coord]
        current_elevation = current_tile.get('final_elevation', -1)
        
        # Find all neighboring tiles and filter for valid paths
        neighbors = get_neighbors(current_coord[0], current_coord[1], persistent_state)
        eligible_neighbors = []

        for n_coord in neighbors:

            # Skip if the tile is already in the current path
            if n_coord in current_path: continue
            neighbor_tile = tiledata.get(n_coord)
            if not neighbor_tile: continue

            # Always flow into lowlands and ocean, if adjacent
            if neighbor_tile.get("is_ocean") or neighbor_tile.get("lowlands"):
                eligible_neighbors.append({'coord': n_coord, 'elevation': -1.0})
                continue

            # Add the neighbor if its elevation is low enough to flow into
            n_elev = neighbor_tile.get('final_elevation', -1)
            if n_elev >= 0 and n_elev <= current_elevation:
                eligible_neighbors.append({'coord': n_coord, 'elevation': n_elev})

        next_coord = None

        if eligible_neighbors:
            eligible_neighbors.sort(key=lambda x: x['elevation'])

            # Check if the river should meander instead of taking the steepest path
            if _get_meander_decision(current_tile, eligible_neighbors):
                
                # If true, take the second-best path to create a meander
                next_coord = eligible_neighbors[1]['coord']
            else:
                # If false, take the absolute steepest path
                next_coord = eligible_neighbors[0]['coord']

        # Continue the path with the chosen neighbor
        if next_coord:
            current_path.append(next_coord)
            current_coord = next_coord

            # Stop if the river has reached a terminal point (ocean or lowland)
            if tiledata[current_coord].get("is_ocean") or tiledata[current_coord].get("lowlands"):
                break
        else:
            # Stop if no eligible neighbor can be found
            break 
            
    return current_path

def _get_meander_decision(current_tile, eligible_neighbors):
    """
    Decides if a river should meander based on a set of rules.
    - Returns False if there's only one path or the best path is a mouth.
    - Returns True if the tile is far enough inland (based on a threshold).
    """
    # Rule 1: Don't meander if there's only one option or the best option is a mouth.
    if len(eligible_neighbors) < 2 or eligible_neighbors[0]['elevation'] == -1.0:
        return False

    # Rule 2: Get the pre-computed normalized distance from the ocean.
    coastal_scale_val = current_tile.get('coastal_scale', 0.0)
    
    # Rule 3: Return True only if the distance is greater than the threshold.
    return coastal_scale_val > MEANDER_THRESHOLD

def _process_river_endpoints(tiledata, river_paths, persistent_state):
    """
    Processes the endpoints of each river path.
    Tags destination tiles as either lakes or with river mouth data for rendering.
    """
    
    # ✍️ Loop Through All River Paths
    # Iterate over each generated river path to process its endpoint
    for path in river_paths:

        # Ensure the path has at least two tiles to be a valid river segment
        if len(path) < 2: continue
        
        # Get the coordinates for the destination tile and the tile just before it
        dest_coord = path[-1]
        mouth_coord = path[-2]

        # Retrieve the tile data for both coordinates
        dest_tile = tiledata.get(dest_coord)
        mouth_tile = tiledata.get(mouth_coord)

        # Skip this path if either tile is invalid
        if not dest_tile or not mouth_tile: continue

        # 🏞️ Handle Delta and Lake Tagging
        # Tag the mouth tile with a temporary link
        # This link ensures the final river segment to the endpoint is rendered correctly
        mouth_tile['river_mouth_deltas'] = [dest_coord]

        # Directly tag the destination tile with its inflow river data
        # Get the bitmask value for the direction of the river's inflow
        inflow_bit = get_direction_bit(dest_coord, mouth_coord, persistent_state)

        # Check if the destination tile already has existing river data (a confluence point)
        if 'river_data' in dest_tile:

            # If so, merge the new inflow bit with the existing bitmask
            existing_mask = int(dest_tile['river_data'].get('bitmask', '0'), 2)
            dest_tile['river_data']['bitmask'] = format(existing_mask | inflow_bit, '06b')
        else:
            # Otherwise, create a new river data entry for the tile
            dest_tile['river_data'] = { "id": 0, "bitmask": format(inflow_bit, '06b') }

        # If the river ended on a lowland, treat it as open water (tiny bay)
        if dest_tile.get("lowlands") and dest_tile.get("is_coast"):
            dest_tile["is_lake"] = True
            dest_tile["water_tile"] = True
            dest_tile["passable"] = False

        # Check if the destination a mouth
        is_delta = dest_tile.get("is_ocean")

        if not is_delta and not dest_tile.get("is_coast"):
            dest_tile["is_lake"] = True
            dest_tile["water_tile"] = True
            dest_tile["passable"] = False

    print(f"[rivers] ✅ Processed river endpoints (deltas and lakes).")

def _tag_river_tiles(tiledata, river_paths, persistent_state):
    """
    REFACTORED: Bakes river data into tiledata, merging bitmasks at confluences.
    The unnecessary second pass has been removed.
    """
    
    # This single loop now handles all river segment tagging.
    for river_id, path in enumerate(river_paths, start=1):
        for i, coord in enumerate(path):
            tile = tiledata.get(coord)
            if not tile: continue

            # Initialize river_data if it doesn't exist
            if 'river_data' not in tile:
                tile['river_data'] = {}
            
            # Tag the source tile
            if i == 0:
                tile['river_data']['is_river_source'] = True

            bitmask_val = 0
            # Add bit for the upstream connection
            if i > 0:
                bitmask_val |= get_direction_bit(coord, path[i-1], persistent_state)
            
            # Add bit for the downstream connection
            if 'river_mouth_deltas' in tile:
                for delta_coord in tile['river_mouth_deltas']:
                    bitmask_val |= get_direction_bit(coord, delta_coord, persistent_state)
            elif i < len(path) - 1:
                bitmask_val |= get_direction_bit(coord, path[i+1], persistent_state)

            # Merge with existing bitmask if this is a confluence point
            existing_mask = int(tile['river_data'].get('bitmask', '0'), 2)
            tile['river_data']['bitmask'] = format(existing_mask | bitmask_val, '06b')

            # Let the current river claim the ID, which is fine for visual purposes
            tile['river_data']['id'] = river_id

    print("[rivers] ✅ Tagged tiles with river data.")

# ──────────────────────────────────────────────────
# 🚀 Orchestrator
# ──────────────────────────────────────────────────

def run_river_generation(tiledata, persistent_state):
    """The main orchestrator function."""

    # Step 1: Generate the raw river paths from source to destination
    river_paths = _generate_river_paths(tiledata, persistent_state)

    # Step 2: Post-process the paths to handle deltas and lakes at endpoints
    _process_river_endpoints(tiledata, river_paths, persistent_state)

    # Step 3: Tag each tile with its river bitmask and ID for rendering
    _tag_river_tiles(tiledata, river_paths, persistent_state)

    print(f"[rivers] ✅ Generated river data for {len(river_paths)} rivers.")
    
    return river_paths