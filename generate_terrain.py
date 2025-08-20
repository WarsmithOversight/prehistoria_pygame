
import random, math
from shared_helpers import axial_distance, get_neighbors, get_neighbor_in_direction, get_tiles_bordering_tag
# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True

# ⚙️ World Generation Weights and Cutoffs
# These variables control the size and distribution of terrain features.
MOUNTAIN_FACTOR = 20                    # The percentage of all land tiles that will be tagged as mountains.
HIGHLANDS_RANGE = 1                     # The hex distance from a mountain for a tile to be considered 'highlands'.

# Set to a number to override, or None to calculate dynamically.
# These fallbacks are based on sqrt(region_count) to scale with the map's "radius".
LOWLANDS_DISTANCE_STEPS = None             # Defines the N farthest distance tiers that become lowlands
CENTRAL_DESERT_DISTANCE_STEPS = None       # The N most inland distance tiers will become desert.
# ──────────────────────────────────────────────────
# 🏞️ Terrain Assignment Rulebook
# ──────────────────────────────────────────────────
# This list defines the priority order for assigning terrain to a tile.
# The generator will check rules from top to bottom and stop at the first match.

TERRAIN_TAG_PRIORITY = [
    ("is_mountain",),
    ("is_lake",),
    ("is_coast", "windward"),
    ("is_coast", "highlands"),
    ("is_coast", "lowlands"),
    ("is_coast",),
    ("windward", "leeward"),
    ("windward", "central_desert"),
    ("central_desert",),
    ("windward",),
    ("adjacent_scrubland",),
    ("leeward",),
    ("highlands",),
    ("lowlands",),
    ("is_ocean",),
]

# ──────────────────────────────────────────────────
# 🎨 Terrain Tag-to-Sprite Recipe Book
# ──────────────────────────────────────────────────
# This dictionary maps the terrain tags (from the priority list) to the
# specific art assets or terrain types that should be assigned to them.
TERRAIN_TAG_TERRAIN = {
    ("is_mountain",):               ["Mountain"],
    ("windward",):                  ["Woodlands", "Hills"],
    ("leeward",):                   ["Scrublands"],
    ("highlands",):                 ["Scrublands", "Highlands"],
    ("is_coast",):                  ["Plains"],
    ("lowlands",):                  ["Marsh"],
    ("central_desert",):            ["DesertDunes"],
    ("adjacent_scrubland",):        ["Scrublands"],
    ("windward", "central_desert"): ["Scrublands"],
    ("is_ocean",):                  ["OceanCalm"],
    ("is_coast", "highlands"):      ["Hills"],
    ("is_coast", "windward"):       ["Woodlands"],
    ("windward", "leeward"):        ["Plains"],
    ("is_coast", "lowlands"):       ["Marsh"],
    ("is_lake",):                   ["Lake"],
}

# ──────────────────────────────────────────────────
# 🌊 Generate Ocean and 🏝️ Coast
# ──────────────────────────────────────────────────

def tag_initial_ocean(tiledata, variable_state):
    """
    Uses the var_bounds list to tag the initial ocean tiles.
    These tiles are marked as both 'water_tile' and 'is_ocean'.
    """

    # 🌊 Retrieve Ocean Coordinates
    # Get the list of all impassable tiles from the world normalization step.
    ocean_coords = variable_state.get("var_bounds", [])
    
    # 🏷️ Apply Ocean Tags
    # Iterate through the list and apply the 'water_tile' and 'is_ocean' tags.
    for coord in ocean_coords:
        tile = tiledata.get(coord)
        if tile:
            tile["water_tile"] = True
            tile["is_ocean"] = True

    if DEBUG:
        # Report the number of tiles that were successfully tagged.
        print(f"[ocean] ✅ {len(ocean_coords)} initial ocean tiles tagged.")

def tag_ocean_coastline(tiledata, persistent_state):
    """
    Finds all non-water tiles adjacent to an 'is_ocean' tile
    and tags them with 'is_coast' for gameplay logic.
    """
    count = 0

    # First, find all ocean tiles to check against
    ocean_tiles = {coord for coord, tile in tiledata.items() if tile.get("is_ocean")}

    for (q, r), tile in tiledata.items():

        # We only care about non-water tiles
        if not tile.get("water_tile"):

            # Check if any neighbor is in our set of ocean coordinates
            neighbors = get_neighbors(q, r, persistent_state)
            if any(neighbor_coord in ocean_tiles for neighbor_coord in neighbors):
                tile["is_coast"] = True
                count += 1
    
    if DEBUG:
        # Report the number of tiles that were successfully tagged.
        print(f"[ocean] ✅ {count} 'is_coast' gameplay tags assigned.")

def resolve_shoreline_bitmasks(tiledata, persistent_state):
    """
    Finds any WATER tile next to a LAND tile and gives it a 'has_shoreline'
    bitmask, with exceptions for marshes.
    """
    # The order of neighbors used for building the bitmask.    
    bitmask_order = persistent_state.get("pers_bitmask_neighbor_order", [])

    # 🏞️ Find Shoreline Tiles
    count = 0
    for (q, r), tile in tiledata.items():
    
        # Only check water tiles, as land tiles cannot have a shoreline.
        if tile.get("water_tile"):
            bits = []
            is_shoreline = False

            # Check all six neighbors in a specific order to build the bitmask.
            for direction in bitmask_order:
                nq, nr = get_neighbor_in_direction(q, r, direction, persistent_state)
                neighbor = tiledata.get((nq, nr))

                # ⚠️ Check for 'Blocked' Shorelines
                # A shoreline is "blocked" if the adjacent land tile is a certain type, like a marsh.
                is_blocked = False
                if neighbor:

                    # A shoreline is blocked only if the neighbor is a lowland,
                    # but is NOT a central_desert or an adjacent_scrubland.
                    is_blocked = (
                        neighbor.get("lowlands") and 
                        not neighbor.get("central_desert") and 
                        not neighbor.get("adjacent_scrubland")
                    )
                
                # ✍️ Build the Bitmask String
                # If the neighbor is a non-blocked land tile, set the bit to '1'.
                if neighbor and not neighbor.get("water_tile") and not is_blocked:
                    bits.append("1")
                    is_shoreline = True
                else:
                    bits.append("0")
            
            # 💾 Save the Shoreline Bitmask
            if is_shoreline:
                tile["has_shoreline"] = "".join(bits)
                count += 1

    if DEBUG:
        # ✅ Report the total number of tiles that were tagged.
        print(f"[shoreline] ✅ {count} shoreline water tiles assigned a bitmask for rendering.")

# ──────────────────────────────────────────────────
# ⛰️ Generate Mountains
# ──────────────────────────────────────────────────

# Next review: Seed the initial mountains, generate heightmap immediately,
# then use heightmap to add more mountains the the highest ,
# creating more consistent ranges and valleys.
# Seed Mountain, Generate Heightmap, take 40% tiles closest to mountains,
# use only those tiles to randomly distribute remaining mountains.

def tag_mountains(tiledata, persistent_state):
    """
    Tags a percentage of land tiles as mountains.
    """

    # 🏞️ Determine Placement Targets
    # Retrieve the total count of land tiles from a pre-calculated value.
    land_tile_count = persistent_state.get("pers_land_count", 0)
    if not land_tile_count:
        if DEBUG: print("[tiledata] ⚠️ No land tiles found to place mountains on.")
        return 0

    # Create a list of all coordinates that are part of a continent region.
    eligible = persistent_state.get("pers_quick_tile_lookup", [])
    
    # Determine the number of mountains to place based on a percentage of the total land.
    num_mountains = max(1, int((MOUNTAIN_FACTOR / 100) * land_tile_count))
    
    # Ensure we don't try to place more mountains than there are eligible tiles.
    num_mountains = min(num_mountains, len(eligible) // 2) # Cap at 50% of land

    # ✍️ Place Mountains and Update Tiledata
    # Randomly select a number of tiles and mark them as mountains, making them impassable.
    for coord in random.sample(eligible, num_mountains):
        tile = tiledata[coord]
        tile["is_mountain"] = True
        tile["passable"] = False

    if DEBUG:
        # ✅ Report the number of mountains placed.
        print(f"[mountains] ✅ {num_mountains} mountains tagged out of {land_tile_count} land tiles.")

    # Call a separate function to compute the distance from the newly placed mountains.
    add_distance_from_mountain_to_tiledata(tiledata)

    return num_mountains

def add_distance_from_mountain_to_tiledata(tiledata):
    """
    Calculates the distance from the nearest mountain using the 'is_mountain' flag.\
    """
    # 🏔️ Gather Mountain Locations
    # Find the coordinates of all tiles that have been tagged as mountains.
    mountain_coords = [coord for coord, tile in tiledata.items() if tile.get("is_mountain")]

    # ⚠️ Handle No Mountains Case
    # If no mountains were placed, set the distance for all tiles to 'None' and exit.
    if not mountain_coords:
        if DEBUG:
            print("[tiledata] ⚠️  No mountains found when calculating distance_from_mountain.")
        for tile in tiledata.values():
            tile["dist_to_mountain"] = None
        return

    # 📏 Calculate Distance for Every Tile
    # Iterate through every single tile on the map.
    for (q, r), tile in tiledata.items():

        # A mountain tile's distance to itself is always zero.
        if tile.get("is_mountain"):
            tile["dist_to_mountain"] = 0
        else:
            # For all other tiles, find the hex distance to the *closest* mountain.
            tile["dist_to_mountain"] = min(
                axial_distance(q, r, mq, mr) for (mq, mr) in mountain_coords
            )
    if DEBUG:
        # ✅ Report successful completion.
        print(f"[mountains] ✅  Distance from mountain assigned to {len(tiledata)} tiles.")

# ────────────────────────────────────────────────────────
# 🌾 Tag Lowlands, Highlands, Central Desert
# ────────────────────────────────────────────────────────

def tag_lowlands(tiledata, persistent_state):
    """
    Tags tiles as 'lowlands' based on discrete distance steps from mountains.
    If LOWLANDS_DISTANCE_STEPS is None, it calculates a dynamic value.
    """
    # ⚙️ Determine the number of steps to use.
    num_steps_to_take = LOWLANDS_DISTANCE_STEPS
    if num_steps_to_take is None:

        # Fallback logic: Calculate steps based on the map's scale.
        region_count = persistent_state.get("pers_region_count", 16)
        
        # We divide the result by 2 to keep lowlands less common than deserts.
        num_steps_to_take = max(1, int(math.sqrt(region_count) / 2))

    # 🏞️ Find Eligible Tiles
    # Get all passable land tiles that could potentially be lowlands.
    candidates = [
        tile for tile in tiledata.values()
        if tile.get("passable")
           and tile.get("terrain") is None
           and tile.get("dist_to_mountain") is not None
    ]
    if not candidates:
        if DEBUG: print("[tiledata] ⚠️ No eligible candidates found for lowlands.")
        return

    # 📏 Find Lowland Distance Bands
    # Find all unique discrete distance-to-mountain values on the map, sorted from farthest to nearest.
    unique_distances = sorted(list(set(t["dist_to_mountain"] for t in candidates)), reverse=True)
    
    # Determine which of these distance values qualify as "lowland" distances based on the LOWLANDS_DISTANCE_STEPS constant.
    lowland_distances = set(unique_distances[:num_steps_to_take])

    if not lowland_distances:
        if DEBUG: print("[tiledata] ⚠️ Not enough unique distance steps to define lowlands.")
        return

    # ✍️ Apply Lowlands Tag
    # Tag every tile whose distance matches one of the identified lowland distance bands.
    count = 0
    for tile in candidates:
        if tile["dist_to_mountain"] in lowland_distances:
            tile["lowlands"] = True
            count += 1
            
    if DEBUG:
        print(f"[lowlands] ✅ {count} lowlands tagged (distances: {sorted(list(lowland_distances), reverse=True)}).")

def tag_highlands(tiledata):

    # ✍️ Apply Highlands Tag
    # Loop through every tile on the map to determine if it should be tagged.
    count = 0
    for tile in tiledata.values():

        # A tile is a highland if it's a passable, non-mountain tile within a set
        # hex distance from a mountain.
        if (
            tile["passable"] and
            tile.get("terrain") is None and
            tile.get("dist_to_mountain") is not None and
            tile["dist_to_mountain"] <= HIGHLANDS_RANGE # N
        ):
            tile["highlands"] = True
            count += 1

    if DEBUG:
        print(f"[highlands] ✅ {count} highland tiles tagged (threshold ≤ {HIGHLANDS_RANGE}).")

def tag_central_desert(tiledata, persistent_state):
    """
    Tags tiles as 'central_desert' based on discrete distance steps from the ocean.
    If CENTRAL_DESERT_DISTANCE_STEPS is None, it calculates a dynamic value.
    """
    # ⚙️ Determine the number of steps to use.
    num_steps_to_take = CENTRAL_DESERT_DISTANCE_STEPS
    if num_steps_to_take is None:
        # Fallback logic: Calculate steps based on the map's scale (its effective "radius").
        region_count = persistent_state.get("pers_region_count", 16)
        
        # 🧠 Calculate steps based on the square root of the region count.
        num_steps_to_take = max(1, int(math.sqrt(region_count)))

    # 🏞️ Find Inland Candidates
    # Get all tiles that are passable and have a calculated distance from the ocean.
    candidates = [
        tile for tile in tiledata.values()
        if tile.get("passable") and tile.get("dist_from_ocean") is not None
    ]

    if not candidates:
        if DEBUG: print("[desert] ⚠️ No eligible desert candidates found.")
        return

    # 📏 Find Unique Distance Tiers
    # Create a sorted list of all unique distance-from-ocean values on the map.
    unique_distances = sorted(list(set(t["dist_from_ocean"] for t in candidates)), reverse=True)

    # 🏜️ Select Desert Tiers
    # Take the N most inland distance values to be our desert tiers.
    desert_distances = set(unique_distances[:num_steps_to_take])

    if not desert_distances:
        if DEBUG: print("[desert] ⚠️ Not enough unique distance steps to define a desert.")
        return

    # ✍️ Tag Matching Tiles
    # Tag every tile whose distance from the ocean falls into one of the desert tiers.
    count = 0
    for tile in candidates:
        if tile["dist_from_ocean"] in desert_distances:
            tile["central_desert"] = True
            count += 1

    if DEBUG:
        # ✅ Report the total number of tiles that were tagged.
        print(f"[desert] ✅ Tagged {count} tiles as central desert (distances: {sorted(list(desert_distances), reverse=True)}).")

def tag_adjacent_scrublands(tiledata, persistent_state):
    """
    Finds and tags all passable tiles adjacent to central_desert tiles.
    """
    # 🏞️ Find All Tiles Adjacent to a Desert
    # Use a helper function to efficiently get the coordinates of all tiles
    # that border a tile with the 'central_desert' tag.
    adjacent_coords = get_tiles_bordering_tag(
        tiledata, persistent_state,
        tag_key="central_desert",
        tag_values=[True]
    )

    if not adjacent_coords:
        if DEBUG:
            print("[scrublands] ⚠️ No central_desert tiles found, skipping adjacent_scrubland tagging.")
        return

    # ✍️ Apply the Scrublands Tag
    count = 0
    # Iterate through the returned set of coordinates.
    
    for coord in adjacent_coords:
        tile = tiledata.get(coord)

        # Apply the 'adjacent_scrubland' tag to any passable tile.
        if tile and tile.get("passable"):
            tile["adjacent_scrubland"] = True
            count += 1

    if DEBUG:
        # ✅ Report the number of tiles that were tagged.
        print(f"[scrublands] ✅ {count} adjacent_scrubland tiles tagged.")

# ───────────────────────────────────────────
# PHASE 4: 🌬️ Windward and Leeward
# ───────────────────────────────────────────

def add_windward_and_leeward_tags(tiledata, persistent_state):
    """
    Applies windward and leeward tags based on a tile's position relative
    to same-row mountains.
    """
    for (q, r), tile in tiledata.items():

        # Only process tiles that are in the highlands to optimize the check.
        if not tile.get("highlands"):
            continue

        tile_dist = tile.get("dist_from_center", 999)
        
        # 🏔️ Find Distances to Same-Row Mountains
        mountain_dists_on_row = []

        # Check all neighbors of the current tile.
        for nq, nr in get_neighbors(q, r, persistent_state):

            # If the neighbor is on the same row, and it's a mountain,
            # store its distance from the continent's center.
            if nr == r:
                neighbor = tiledata.get((nq, nr))
                if neighbor and neighbor.get("is_mountain"):
                    mountain_dists_on_row.append(neighbor.get("dist_from_center", 999))
        
        # If there are no mountains on this row to compare against, skip.
        if not mountain_dists_on_row:
            continue


        # ✍️ Apply Windward and Leeward Tags
        # A tile is 'windward' if it's farther from the center than *any* same-row mountain.
        if any(tile_dist > m_dist for m_dist in mountain_dists_on_row):
            tile["windward"] = True
            
        # A tile is 'leeward' if it's closer to the center than *any* same-row mountain.
        if any(tile_dist < m_dist for m_dist in mountain_dists_on_row):
            tile["leeward"] = True

    if DEBUG:
        # ✅ Report successful completion.
        print(f"[windward/leeward] ✅ Windward/leeward tags assigned.")
        
# ───────────────────────────────────────────
# 🏞️ Fill in remaining terrain
# ───────────────────────────────────────────

def fill_in_terrain_from_tags(tiledata):
    """
    Assigns terrain to tiles based on a priority list of rules.
    """
    count = 0
    for tile in tiledata.values():

        # Skip tiles that have already been assigned a terrain type.
        if tile.get("terrain") is not None:
            continue

        # ✍️ Find and Assign Terrain
        # Iterate through the priority list from highest to lowest priority.
        for rule in TERRAIN_TAG_PRIORITY:

            # Check if the tile has ALL the tags required by the current rule.
            if all(tile.get(tag) for tag in rule):

                # If the tags match, get the possible terrain options for this rule.
                options = TERRAIN_TAG_TERRAIN.get(rule)
                if options:

                    # Choose a random terrain from the options and assign it to the tile.                    
                    tile["terrain"] = random.choice(options)
                    count += 1

                    # Stop at the first match to ensure priority is maintained.                    
                    break # Stop at the first (highest priority) matching rule

    if DEBUG:
        print(f"[terrain] ✅ Terrain assigned from tags for {count} tiles.")
