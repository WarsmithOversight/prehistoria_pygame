# biomes.py
# A dedicated module for assigning biomes to regions based on geographic data.
import math
from collections import Counter

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────
DEBUG = True
VACANT_SLOT_BONUS_MULTIPLIER = 1

# ──────────────────────────────────────────────────
# 🛠️ Helpers (Biome Desire Calculators)
# ─────────────────────────────────────────────────

def _calculate_arid_desire(tiledata, persistent_state):
    """Calculates Arid desire for every region."""
    
    # Get the dictionary that maps region_id to its set of tiles
    region_tile_sets = persistent_state.get("pers_region_sets", {})

    # Loop through each region's center data
    for region_data in persistent_state.get("pers_region_centers", []):
        center_coord = (region_data["q"], region_data["r"])
        center_tile = tiledata.get(center_coord)
        region_id = region_data.get("region_id")
        
        if not center_tile or not region_id: continue

        # Get the list of all tiles in this region
        tiles_in_region = region_tile_sets.get(region_id, set())
        
        # Calculate the average 'continental_scale' for all tiles in the region
        total_score = 0
        tile_count = 0
        for tile_coord in tiles_in_region:
            tile = tiledata.get(tile_coord)
            if tile and "continental_scale" in tile:
                total_score += tile["continental_scale"]
                tile_count += 1
        
        # Avoid division by zero and store the final score
        average_score = total_score / tile_count if tile_count > 0 else 0
        center_tile["desire_scores"]["Arid"] = average_score
    
    if DEBUG: print(f"[biomes] ✅ Arid desire calculated for all regions.")

def _calculate_tropical_desire(tiledata, persistent_state):
    """Calculates Tropical desire for every region."""
    
    # Get the dictionary that maps region_id to its set of tiles
    region_tile_sets = persistent_state.get("pers_region_sets", {})

    # Loop through each region's center data
    for region_data in persistent_state.get("pers_region_centers", []):
        center_coord = (region_data["q"], region_data["r"])
        center_tile = tiledata.get(center_coord)
        region_id = region_data.get("region_id")
        
        if not center_tile or not region_id: continue

        # Get the list of all tiles in this region
        tiles_in_region = region_tile_sets.get(region_id, set())
        
        # Calculate the average 'norm_dist_from_q_center' for all tiles in the region
        total_score = 0
        tile_count = 0
        for tile_coord in tiles_in_region:
            tile = tiledata.get(tile_coord)
            if tile and "norm_dist_from_q_center" in tile:
                total_score += tile["norm_dist_from_q_center"]
                tile_count += 1
        
        # Avoid division by zero and store the final score
        average_score = total_score / tile_count if tile_count > 0 else 0
        center_tile["desire_scores"]["Tropical"] = average_score
    
    if DEBUG: print(f"[biomes] ✅ Tropical desire calculated for all regions.")

def _calculate_floodplains_desire(tiledata, persistent_state):
    """Calculates Floodplains desire for every region."""
    
    # Get the dictionary that maps region_id to its set of tiles
    region_tile_sets = persistent_state.get("pers_region_sets", {})

    # Loop through each region's center data
    for region_data in persistent_state.get("pers_region_centers", []):
        center_coord = (region_data["q"], region_data["r"])
        center_tile = tiledata.get(center_coord)
        region_id = region_data.get("region_id")
        
        if not center_tile or not region_id: continue

        # Get the list of all tiles in this region
        tiles_in_region = region_tile_sets.get(region_id, set())
        
        # Calculate the average 'topographic_scale' for all tiles in the region
        total_score = 0
        tile_count = 0
        for tile_coord in tiles_in_region:
            tile = tiledata.get(tile_coord)
            if tile and "topographic_scale" in tile:
                total_score += tile["topographic_scale"]
                tile_count += 1
        
        average_score = total_score / tile_count if tile_count > 0 else 0
        
        # Invert the score: a low topographic_scale (far from mountains) means a high desire for Floodplains.
        final_score = 1.0 - average_score
        
        center_tile["desire_scores"]["Floodplains"] = final_score
    
    if DEBUG: print(f"[biomes] ✅ Floodplains desire calculated for all regions.")

def _calculate_temperate_desire(tiledata, persistent_state):
    """Calculates Temperate desire based on the average Arid and Tropical scores of neighboring regions."""
    
    # 1. First, create a quick lookup map from region_id to its center tile
    #    This makes it easy to fetch a neighbor's data.
    region_centers = persistent_state.get("pers_region_centers", [])
    id_to_center_tile_map = {
        region_data["region_id"]: tiledata.get((region_data["q"], region_data["r"]))
        for region_data in region_centers
    }

    # 2. Now, loop through each region to calculate its Temperate score
    for region_data in region_centers:
        center_tile = id_to_center_tile_map.get(region_data["region_id"])
        if not center_tile: continue

        neighbor_ids = center_tile.get("adjacent_regions", set())
        
        # 3. Gather the Arid and Tropical scores from all neighbors
        total_neighbor_arid_score = 0
        total_neighbor_tropical_score = 0
        
        if not neighbor_ids:
            center_tile["desire_scores"]["Temperate"] = 0.0
            continue

        for neighbor_id in neighbor_ids:
            neighbor_tile = id_to_center_tile_map.get(neighbor_id)
            if neighbor_tile and "desire_scores" in neighbor_tile:
                total_neighbor_arid_score += neighbor_tile["desire_scores"].get("Arid", 0.0)
                total_neighbor_tropical_score += neighbor_tile["desire_scores"].get("Tropical", 0.0)
        
        # 4. Calculate the average of all gathered scores
        #    We divide by (number of neighbors * 2) because we are summing two scores per neighbor.
        num_scores = len(neighbor_ids) * 2
        total_score = total_neighbor_arid_score + total_neighbor_tropical_score
        average_score = total_score / num_scores if num_scores > 0 else 0
        
        center_tile["desire_scores"]["Temperate"] = average_score

    if DEBUG: print(f"[biomes] ✅ Temperate desire calculated for all regions.")

def _resolve_and_stamp_biomes(tiledata, persistent_state):
    """
    Resolves biome conflicts using a "draft" system based on a final score
    and then stamps the final biome on all tiles in each region.
    """
    region_centers = persistent_state.get("pers_region_centers", [])
    region_tile_sets = persistent_state.get("pers_region_sets", {})
    if not region_centers: return

    # 1. PREPARATION: Create ranked lists and lookup tables
    id_to_center_tile_map = {r["region_id"]: tiledata.get((r["q"], r["r"])) for r in region_centers}
    first_tile = next((tile for tile in id_to_center_tile_map.values() if tile), None)
    if not first_tile or "desire_scores" not in first_tile: return
    biome_names = list(first_tile["desire_scores"].keys())
    
    region_ranks, ranked_lists = {}, {}
    for biome in biome_names:
        sorted_regions = sorted(region_centers, key=lambda r: id_to_center_tile_map[r["region_id"]]["desire_scores"].get(biome, 0), reverse=True)
        ranked_lists[biome] = [r["region_id"] for r in sorted_regions]
        for rank, r_data in enumerate(sorted_regions, 1):
            if r_data["region_id"] not in region_ranks: region_ranks[r_data["region_id"]] = {}
            region_ranks[r_data["region_id"]][biome] = rank

    # 2. THE DRAFT: Iteratively assign biomes
    unassigned = {r["region_id"] for r in region_centers}
    final_biomes, draft_report = {}, []

    VACANT_SLOT_BONUS_MULTIPLIER = 1
    
    # Calculate target counts based on the new user-specified method
    num_biomes = len(biome_names)
    total_regions = len(region_centers)

    # Calculate the next multiple of 5
    next_multiple = math.ceil(total_regions / num_biomes) * num_biomes
    slots_per_biome = next_multiple // num_biomes

    # Divide by the number of biomes to get slots per biome
    slots_per_biome = next_multiple // num_biomes

    # Initialize target counts and assigned counts
    target_counts = {biome: slots_per_biome for biome in biome_names}
    assigned_counts = {biome: 0 for biome in biome_names}

    # The main loop starts AFTER the targets have been calculated.
    for round_num in range(1, total_regions + 1):
        best_pick = {"region_id": None, "biome": None, "final_score": -1}

        for biome in biome_names:
            for region_id in ranked_lists[biome]:
                if region_id in unassigned:
                    # Calculate Commitment Score
                    ranks = sorted(region_ranks[region_id].values())
                    commitment = ranks[1] - ranks[0]
                    
                    # Calculate Vacant Slot Bonus
                    slots_needed = target_counts[biome] - assigned_counts[biome]
                    bonus = slots_needed * VACANT_SLOT_BONUS_MULTIPLIER
                    
                    rounded_bonus = round(bonus)

                    final_score = commitment + rounded_bonus

                    if final_score > best_pick["final_score"]:
                        best_pick.update({
                            "region_id": region_id, "biome": biome, "final_score": final_score,
                            "commitment": commitment, "bonus": rounded_bonus, "ranks": region_ranks[region_id]
                        })
                    break

        # Assign the winner for this round
        winner_id, winner_biome = best_pick["region_id"], best_pick["biome"]
        if winner_id:
            final_biomes[winner_id] = winner_biome
            unassigned.remove(winner_id)
            assigned_counts[winner_biome] += 1
            draft_report.append(best_pick)

    # 3. REPORTING: Print the detailed draft results
    if DEBUG:
        print("\n──────────────────────────────────────────────────")
        print("               BIOME DRAFT REPORT")
        print("──────────────────────────────────────────────────")
        for i, pick in enumerate(draft_report):
            ranks_str = " | ".join([f"{b[:4]}:{r:<2}" for b, r in sorted(pick["ranks"].items())])
            print(f"Round {i+1:<2}: Region {pick['region_id']:<2} -> {pick['biome']:<11} "
                  f"(Score: {pick['final_score']:<2} = C:{pick['commitment']:<2} + B:{pick['bonus']:<2}) | [ {ranks_str} ]")
        print("──────────────────────────────────────────────────\n")

        # Count the occurrences of each biome
        biome_counts = Counter(final_biomes.values())
        
        # Find the most and least common biomes
        most_common = biome_counts.most_common(1)[0]
        least_common = biome_counts.most_common()[-1]
        
        # Print the summary
        print(f"Most Common Biome: {most_common[0]} ({most_common[1]} regions)")
        print(f"Most Rare Biome: {least_common[0]} ({least_common[1]} regions)")
        print("──────────────────────────────────────────────────\n")

    # 4. STAMPING: Apply the final biome to all tiles in each region
    for region_id, biome_name in final_biomes.items():
        # Convert the biome name (e.g., "Arid") to a lowercase tag (e.g., "arid")
        biome_tag = biome_name.lower()
        
        for coord in region_tile_sets.get(region_id, set()):
            tile = tiledata.get(coord)
            if tile:
                tile[biome_tag] = True
    
    if DEBUG: print(f"[biomes] ✅ Final biomes resolved and stamped on all tiles.")

# ──────────────────────────────────────────────────
# 🚀 Orchestrator
# ──────────────────────────────────────────────────

def assign_biomes_to_regions(tiledata, persistent_state):
    """Orchestrates the entire biome assignment process."""
    
    # 1. Initialize desire score dictionaries on each region center tile
    for region_data in persistent_state.get("pers_region_centers", []):
        center_coord = (region_data["q"], region_data["r"])
        center_tile = tiledata.get(center_coord)
        if center_tile:
            center_tile["desire_scores"] = {}

    # 2. Calculate base desire scores layer by layer
    _calculate_arid_desire(tiledata, persistent_state)
    _calculate_tropical_desire(tiledata, persistent_state)
    _calculate_floodplains_desire(tiledata, persistent_state)
    
    # 3. Calculate dependent desire scores last
    _calculate_temperate_desire(tiledata, persistent_state)
    
    # 4. Resolve the winning biome and stamp it onto all tiles
    _resolve_and_stamp_biomes(tiledata, persistent_state)

    if DEBUG:
        print(f"[biomes] ✅ Biome assignment process complete.")