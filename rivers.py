# rivers.py

import random
from shared_helpers import get_neighbors, get_neighbor_in_direction

# --- Configuration ---
RIVER_DENSITY_FACTOR = 5.0
OVERGENERATION_FACTOR = 2.0
CULL_PERCENTAGE = 50
CANDIDATE_POOL_MULTIPLIER = 4
UPHILL_FLOW_TOLERANCE = 0.0
MEANDER_THRESHOLD = 0.4 # Meander if normalized distance from ocean > 40%

# In rivers.py (replace the existing function)

def _generate_river_paths(tiledata, persistent_state):
    """
    Generates river paths using a unified pathfinding system with
    probabilistic meandering for inland tiles.
    """
    print("🌊 Generating linear river paths...")
    
    land_tile_count = persistent_state.get("pers_land_count", 0)
    base_river_count = max(1, int((land_tile_count / 100) * RIVER_DENSITY_FACTOR))
    num_rivers_to_generate = int(base_river_count * OVERGENERATION_FACTOR)
    print(f"   -> Base target: {base_river_count} rivers. Overgenerating to {num_rivers_to_generate}.")

    land_tiles = [
        data for data in tiledata.values() 
        if not data.get("is_ocean") and 'final_elevation' in data
    ]
    if not land_tiles:
        print("   -> ⚠️ No valid land tiles found for river sources.")
        return []
    land_tiles.sort(key=lambda x: x['final_elevation'], reverse=True)
    
    source_candidates = [t for t in land_tiles if not t.get("lowlands") and not t.get("is_coast")]
    if not source_candidates:
        print("   -> ⚠️ No valid non-lowland, non-coastal tiles found for river sources.")
        return []
    
    river_sources = [source_candidates[0]]
    occupied_coords = {source_candidates[0]['coord']}
    for n_coord in get_neighbors(source_candidates[0]['coord'][0], source_candidates[0]['coord'][1], persistent_state):
        occupied_coords.add(n_coord)
    print(f"   -> Forcing highest point {source_candidates[0]['coord']} as a river source.")
    
    target_pool_size = min(int(num_rivers_to_generate * CANDIDATE_POOL_MULTIPLIER), len(source_candidates))
    final_candidate_pool = source_candidates[1:target_pool_size]
    random.shuffle(final_candidate_pool)

    for candidate in final_candidate_pool:
        if len(river_sources) >= num_rivers_to_generate: break
        if candidate['coord'] in occupied_coords: continue
        river_sources.append(candidate)
        occupied_coords.add(candidate['coord'])
        for n_coord in get_neighbors(candidate['coord'][0], candidate['coord'][1], persistent_state):
            occupied_coords.add(n_coord)
    print(f"   -> Selected {len(river_sources)} total sources.")
    
    all_river_paths = []
    for source_tile in river_sources:
        current_path = [source_tile['coord']]
        current_coord = source_tile['coord']
        
        for _ in range(150): 
            current_tile = tiledata[current_coord]
            current_elevation = current_tile.get('final_elevation', -1)
            
            neighbors = get_neighbors(current_coord[0], current_coord[1], persistent_state)
            eligible_neighbors = []

            for n_coord in neighbors:
                if n_coord in current_path: continue
                neighbor_tile = tiledata.get(n_coord)
                if not neighbor_tile: continue

                if neighbor_tile.get("is_ocean") or neighbor_tile.get("lowlands"):
                    eligible_neighbors.append({'coord': n_coord, 'elevation': -1.0})
                    continue

                n_elev = neighbor_tile.get('final_elevation', -1)
                if n_elev >= 0 and n_elev <= current_elevation + UPHILL_FLOW_TOLERANCE:
                    eligible_neighbors.append({'coord': n_coord, 'elevation': n_elev})

            next_coord = None
            if eligible_neighbors:
                eligible_neighbors.sort(key=lambda x: x['elevation'])
                
                # ✅ Call your new helper function to decide if we should meander.
                if _get_meander_decision(current_tile, eligible_neighbors):
                    # If True, take the second-best path.
                    next_coord = eligible_neighbors[1]['coord']
                else:
                    # If False, take the absolute best path.
                    next_coord = eligible_neighbors[0]['coord']
            
            if next_coord:
                current_path.append(next_coord)
                current_coord = next_coord
                if tiledata[current_coord].get("is_ocean") or tiledata[current_coord].get("lowlands"):
                    break
            else:
                break 
                
        if len(current_path) > 1:
            all_river_paths.append(current_path)

    if CULL_PERCENTAGE > 0 and all_river_paths:
        all_river_paths.sort(key=len)
        num_to_keep = int(len(all_river_paths) * (1 - (CULL_PERCENTAGE / 100.0)))
        culled_paths = all_river_paths[-num_to_keep:]
        print(f"   -> Culled {len(all_river_paths) - len(culled_paths)} rivers. Keeping {len(culled_paths)} longest paths.")
        return culled_paths
        
    print(f"   -> Successfully generated {len(all_river_paths)} river paths (no culling).")
    return all_river_paths

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
    norm_dist = current_tile.get('norm_dist_from_ocean', 0.0)
    
    # Rule 3: Return True only if the distance is greater than the threshold.
    return norm_dist > MEANDER_THRESHOLD

def _generate_deltas(tiledata, river_paths, persistent_state):
    """
    Post-processes river paths. Creates single-exit deltas for ocean/coast terminations.
    Tags all other land-terminating river endpoints with 'is_lake'.
    """
    print("🏞️  Generating deltas and tagging lakes...")
    for path in river_paths:
        if len(path) < 2:
            continue
        
        dest_coord = path[-1]
        mouth_coord = path[-2]

        dest_tile = tiledata.get(dest_coord)
        mouth_tile = tiledata.get(mouth_coord)
        if not dest_tile or not mouth_tile: continue

        is_ocean_mouth = dest_tile.get("is_ocean")
        # A true delta is an exit into the ocean or a COASTAL lowland (e.g., salt marsh)
        is_delta = is_ocean_mouth or (dest_tile.get("lowlands") and dest_tile.get("is_coast"))

        if is_delta:
            # This is a delta. Create the visual link for the river to flow out.
            mouth_tile['river_mouth_deltas'] = [dest_coord]
        else:
            # This river terminates on land, so it forms a lake.
            dest_tile["is_lake"] = True
            dest_tile["water_tile"] = True # 👈 Add this line
            mouth_tile['river_mouth_deltas'] = [dest_coord]
            
            # By NOT creating a 'river_mouth_deltas' link, we ensure the river
            # visually stops on the tile *before* the lake, with no overlay on the lake itself.

def _tag_river_tiles(tiledata, river_paths, persistent_state):
    """
    Bakes river data into tiledata, now correctly merging the bitmasks
    at confluence points where multiple rivers meet.
    """
    print("🏷️  Tagging tiles with river data...")
    bitmask_order = persistent_state.get("pers_bitmask_neighbor_order", [])
    
    def get_direction_bit(start_coord, end_coord, order):
        for i, direction in enumerate(order):
            neighbor = get_neighbor_in_direction(start_coord[0], start_coord[1], direction, persistent_state)
            if neighbor == end_coord:
                return 1 << (5 - i)
        return 0

    for river_id, path in enumerate(river_paths, start=1):
        for i, coord in enumerate(path):
            tile = tiledata.get(coord)
            if not tile: continue

            # ✅ Add a flag to the source tile of each river
            if i == 0:
                if 'river_data' not in tile:
                    tile['river_data'] = {}
                tile['river_data']['is_river_source'] = True

            bitmask_val = 0
            # Determine the connections for this segment of the current river
            if i > 0:
                bitmask_val |= get_direction_bit(coord, path[i-1], bitmask_order)
            
            if 'river_mouth_deltas' in tile:
                for delta_coord in tile['river_mouth_deltas']:
                    bitmask_val |= get_direction_bit(coord, delta_coord, bitmask_order)
            elif i < len(path) - 1:
                bitmask_val |= get_direction_bit(coord, path[i+1], bitmask_order)

            # ✅ NEW: Check for existing river data to merge paths
            if 'river_data' in tile:
                # This tile is a confluence point. Combine the bitmasks.
                existing_mask = int(tile['river_data'].get('bitmask', '0'), 2)
                combined_mask = existing_mask | bitmask_val
                tile['river_data']['bitmask'] = format(combined_mask, '06b')
                tile['river_data']['id'] = river_id # Let the current river claim the ID
            else:
                # This is the first river to touch this tile.
                tile['river_data'] = { "id": river_id, "bitmask": format(bitmask_val, '06b') }

    # This second pass is for the delta endpoints, which might also be confluences
    for river_id, path in enumerate(river_paths, start=1):
        if len(path) < 2: continue
        mouth_tile = tiledata.get(path[-2])
        if not mouth_tile or 'river_mouth_deltas' not in mouth_tile: continue

        for delta_coord in mouth_tile['river_mouth_deltas']:
            delta_tile = tiledata.get(delta_coord)
            if delta_tile:
                bitmask_val = get_direction_bit(delta_coord, path[-2], bitmask_order)
                if 'river_data' in delta_tile:
                    existing_mask = int(delta_tile['river_data'].get('bitmask', '0'), 2)
                    combined_mask = existing_mask | bitmask_val
                    delta_tile['river_data']['bitmask'] = format(combined_mask, '06b')
                    delta_tile['river_data']['id'] = river_id
                else:
                    delta_tile['river_data'] = { "id": river_id, "bitmask": format(bitmask_val, '06b') }

def run_river_generation(tiledata, persistent_state):
    """The main orchestrator function."""
    river_paths = _generate_river_paths(tiledata, persistent_state)
    # ✅ Call the new generic delta function
    _generate_deltas(tiledata, river_paths, persistent_state)
    _tag_river_tiles(tiledata, river_paths, persistent_state)
    return river_paths