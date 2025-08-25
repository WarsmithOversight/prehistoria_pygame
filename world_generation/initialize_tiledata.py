# region_seed_assembler.py
# Build a connected blob of N region tiles (radius R disks), then box, normalize, and oceanize.

import random
from shared_helpers import axial_distance, expand_region_seed, get_neighbors, a_star_pathfind, hex_to_pixel

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True

# ──────────────────────────────────────────────────
# ⛰️ Initialize Region Centers
# ──────────────────────────────────────────────────

def initialize_region_seeds(persistent_state, variable_state):
    
    # ──────────────────────────────────────────────────
    # ⚙️ Setup & Dependencies
    # ──────────────────────────────────────────────────

    # How many regions should we generate
    extra_centers_to_add = persistent_state["pers_region_count"]

    # What should our origin point be
    lattice_origin = (100, 100)

    # Adjust our point-to-point step based on row parity
    LATTICE_OFFSETS_EVEN = [
        (0, -7),    # NW-ish
        (+5, -3),   # NE-ish
        (+5, +4),   # E-ish
        (0, +7),    # SE-ish
        (-6, +3),   # SW-ish
        (-5, -4)    # W-ish
    ]

    LATTICE_OFFSETS_ODD = [
        (+1, -7),   # NW-ish
        (+6, -3),   # NE-ish
        (+5, +4),   # E-ish
        (-1, +7),   # SE-ish
        (-5, +3),   # SW-ish
        (-5, -4)    # W-ish
    ]

    # Tells us the radius we need for our region center point grid
    def lattice_rings_for_count(extra_centers_to_add):
        if extra_centers_to_add <= 0:
            return 1
        return 1 + ((extra_centers_to_add + 1) // 2)
    rings_to_add = max(1, lattice_rings_for_count(extra_centers_to_add) - 1)

    # ──────────────────────────────────────────────────
    # #️⃣ Generate Center Point Lattice
    # ──────────────────────────────────────────────────

    # All region center points
    all_points = {lattice_origin}

    # expand out radially
    frontier = {lattice_origin}

    for _ in range(rings_to_add):
        # Prepare to build the next ring of points.
        next_frontier = set()

        # For every point in the current ring, find all its unique neighbors.
        for (q, r) in frontier:
            offsets_to_use = LATTICE_OFFSETS_ODD if (r & 1) else LATTICE_OFFSETS_EVEN
            
            for (dq, dr) in offsets_to_use:
                p = (q + dq, r + dr)
                if p not in all_points:
                    all_points.add(p)
                    next_frontier.add(p)

        # The newly found neighbors become the next ring to expand from.
        frontier = next_frontier

    # Sort the points by r and then q and give each a unique ID.
    lattice_points_sorted = sorted(all_points, key=lambda t: (t[1], t[0]))  # by r, then q
    variable_state["var_lattice_grid"] = [
        {"q": q, "r": r, "lattice_id": idx}
        for idx, (q, r) in enumerate(lattice_points_sorted, start=1)
    ]

    if DEBUG:
        print(f"[regions] ✅ Stored {len(lattice_points_sorted)} points across {rings_to_add+1} rings (incl. origin)")

    # ──────────────────────────────────────────────────
    # 🔗 Build Adjacency Map
    # ──────────────────────────────────────────────────

    # Load all points into an index
    lattice_point_index = {}
    for lattice_point in variable_state["var_lattice_grid"]:
        lattice_point_index[(lattice_point["q"], lattice_point["r"])] = lattice_point

    # Neighbor for-loop
    for lattice_point in variable_state["var_lattice_grid"]:
        q, r = lattice_point["q"], lattice_point["r"]

        # create an empty neighbor list
        neigh_ids = []

        # Choose the correct offset list based on the current point's row parity
        offsets_to_use = LATTICE_OFFSETS_ODD if (r & 1) else LATTICE_OFFSETS_EVEN

        # Now, check for neighbors using the correct set of offsets
        for dq, dr in offsets_to_use:
            # Look for a point at the target coordinate in our index
            hit = lattice_point_index.get((q + dq, r + dr))
            
            # If it exists in our pre-built lattice, it's a neighbor
            if hit:
                neigh_ids.append(hit["lattice_id"])
        
        # Assign the final list of neighbors to the lattice point.
        lattice_point["adjacent_to"] = neigh_ids

    # ──────────────────────────────────────────────────
    # ⛰️ Committ to region centers
    # ──────────────────────────────────────────────────

    # Start with the Origin and First Ring    
    origin_lattice_point = lattice_point_index[lattice_origin]
    first_ring_ids = origin_lattice_point["adjacent_to"]

    origin_lattice_id = 1
    chosen_region_centers_ids = [origin_lattice_id]
    origin_lattice_point = next(lattice_point for lattice_point in variable_state["var_lattice_grid"]
                                if lattice_point["lattice_id"] == origin_lattice_id)
    first_ring_ids = origin_lattice_point["adjacent_to"]

    # Select the origin and a random neighbor from the first ring.
    chosen_region_centers_ids.append(random.choice(first_ring_ids))

    # Grow the Continent Outward from Chosen Centers
    while len(chosen_region_centers_ids) < (2 + extra_centers_to_add):
        eligible_ids = []

        # Identify candidate points that are adjacent to at least two already-chosen points.
        for lattice_point in variable_state["var_lattice_grid"]:
            if lattice_point["lattice_id"] in chosen_region_centers_ids:
                continue

            # Count how many of a candidate's neighbors are already chosen.
            chosen_neighbors = sum(1 for nid in lattice_point["adjacent_to"] if nid in chosen_region_centers_ids)
            
            # A candidate is eligible if it forms a stable connection (2+ chosen neighbors).
            if chosen_neighbors >= 2:
                eligible_ids.append(lattice_point["lattice_id"])

        if not eligible_ids:
            print(f"[region] ⚠️ No eligible lattice points found at "
                  f"{len(chosen_region_centers_ids)}/{2 + extra_centers_to_add}")
            break

        # Pick one of the eligible candidates to add to the chosen set.
        chosen_region_centers_ids.append(random.choice(eligible_ids))

    # Save the Final List of Center Coordinates, including adjacency data
    persistent_state["pers_region_centers"] = [
        lattice_point
        for lattice_point in variable_state["var_lattice_grid"]
        if lattice_point["lattice_id"] in chosen_region_centers_ids
    ]

    for i, region_center_data in enumerate(persistent_state["pers_region_centers"]):
        region_center_data["region_id"] = i + 1

    # Report the number of chosen centers.
    if DEBUG:
        print(f"[region] ✅ Picked {len(persistent_state['pers_region_centers'])} centers")

# ──────────────────────────────────────────────────
# 🌎 Populate Tiledata
# ──────────────────────────────────────────────────

def initialize_tiledata(persistent_state, variable_state):

    # ──────────────────────────────────────────────────
    # 🏞️ Expand Regions
    # ──────────────────────────────────────────────────

    # Get the region radius and a list of all region center coordinates.
    region_radius = 3
    region_centers  = persistent_state.get("pers_region_centers") or []

    if not region_centers:
        raise ValueError("[tiledata] No region centers present. Run initialize_region_seeds first.")

    # minimum padding between playable area and void before boxing to rectangle
    min_padding = 4

    # Create empty dicts to store data for the new regions.
    persistent_state["pers_region_sets"] = {}  # region_id -> set((q,r))
    variable_state["var_regions"] = {}         # This can remain temporary
    all_passable_coords = set()

    # Loop through all region_centers
    for region_index, region_data in enumerate(region_centers, start=1):
        cq, cr = region_data["q"], region_data["r"]

        # Create the set of tiles for each region.
        tiles = set(expand_region_seed(cq, cr, region_radius))

        # Store the tiles and metadata in temporary state.
        persistent_state["pers_region_sets"][region_index] = tiles
        variable_state["var_regions"][region_index] = {
            "center": (cq, cr),
            "radius": region_radius,
        }

        # Add all the new tiles to the master set of passable coordinates.
        all_passable_coords |= tiles

    # ──────────────────────────────────────────────────
    # 🗺️ Normalize World
    # ──────────────────────────────────────────────────

    # Find the min/max coordinates of the entire passable area.
    min_q = min(q for q, _ in all_passable_coords)
    max_q = max(q for q, _ in all_passable_coords)
    min_r = min(r for _, r in all_passable_coords)
    max_r = max(r for _, r in all_passable_coords)

    # Expand the bounds to include a padding margin around the continent.
    min_q -= min_padding
    max_q += min_padding
    min_r -= min_padding
    max_r += min_padding

    # Calculate the offset needed to make the top-left corner (0,0).
    offset_q = -min_q
    offset_r = -min_r
    # Ensure the row offset is even to preserve odd-r hex grid parity.
    if offset_r & 1:
        offset_r += 1

    # Apply the normalization offset to the stored region center coordinates.
    for center_data in persistent_state["pers_region_centers"]:
        center_data["q"] += offset_q
        center_data["r"] += offset_r

    # Normalize the coordinates in our persistent region sets as well.
    normalized_region_sets = {}
    for region_id, tile_set in persistent_state["pers_region_sets"].items():
        normalized_set = {(q + offset_q, r + offset_r) for q, r in tile_set}
        normalized_region_sets[region_id] = normalized_set
    persistent_state["pers_region_sets"] = normalized_region_sets

    if DEBUG:
        print(f"[tiledata] ✅ Region centers normalized.")

    width  = (max_q - min_q) + 1
    height = (max_r - min_r) + 1

    # Calculate and store the final map dimensions.
    persistent_state["pers_map_size"] = {"cols": width, "rows": height}

    # ──────────────────────────────────────────────────
    # 💾 Save Tiledata
    # ──────────────────────────────────────────────────

    # Create the final dictionary that will hold all tile data.
    tiledata = {}
    var_bounds = []

    # Prepare a quick lookup for which region a tile belongs to before normalization.
    coord_to_region = {}
    for rid, tiles in persistent_state["pers_region_sets"].items():
        for c in tiles:
            coord_to_region[c] = rid

    # Iterate through every coordinate in the normalized grid.
    z_formula = persistent_state["pers_z_formulas"]["tile"]
    for r in range(min_r, max_r + 1):
        for q in range(min_q, max_q + 1):

            # Apply the normalization offset.
            nq = q + offset_q
            nr = r + offset_r
            z_value = z_formula(nr) 

            # Determine if the tile is a part of a region (passable) or void (impassable).
            region_id = coord_to_region.get((nq, nr))
            if region_id is not None:

                # This is a land tile.
                tiledata[(nq, nr)] = {
                    "coord": (nq, nr),
                    "z": z_value,
                    "passable": True,
                    "terrain": None,
                    "type": "tile",
                    "region_id": region_id
                }
            else:

                # This is a void tile.
                tiledata[(nq, nr)] = {
                    "coord": (nq, nr),
                    "z": z_value,
                    "passable": False,
                    "terrain": None,
                    "type": "tile"
                }
                var_bounds.append((nq, nr))

    # First, create a quick lookup map of {lattice_id: region_id}
    lattice_to_region_id_map = {
        center_data["lattice_id"]: center_data["region_id"]
        for center_data in persistent_state["pers_region_centers"]
    }

    for region_data in persistent_state["pers_region_centers"]:
        # Find the center tile in the main tiledata dictionary
        center_coord = (region_data["q"], region_data["r"])
        center_tile = tiledata.get(center_coord)

        if center_tile:
            # Translate the adjacent_to list from lattice_ids to region_ids
            adjacent_region_ids = {
                lattice_to_region_id_map[adj_id]
                for adj_id in region_data["adjacent_to"]
                if adj_id in lattice_to_region_id_map
            }
            
            # Now, stamp the data onto the center tile
            center_tile["is_region_center"] = True
            center_tile["adjacent_regions"] = adjacent_region_ids

    # Save the list of impassable tiles for future ocean masking.
    variable_state["var_bounds"] = var_bounds

    # Save all hex centers
    persistent_state["pers_hex_pixel_grid"] = build_hex_pixel_grid(tiledata, persistent_state)

    # Calculate and print a summary of the generated map.
    total_tiles = width * height
    land_tiles  = sum(1 for t in tiledata.values() if t["passable"])
    void_tiles  = total_tiles - land_tiles
    expected_land = 37 * len(region_centers)  # 37 = area of R=3 disk

    # Print the final report.
    print(f"[tiledata] ✅ built rectangle {width}×{height} → {total_tiles} tiles")
    print(f"[tiledata]    passable (land) = {land_tiles}, impassable (void) = {void_tiles}")
    print(f"[tiledata]    expected land (37 × regions) = {expected_land} → delta = {land_tiles - expected_land}")

    # Return the generated tiledata dictionary.
    return tiledata

def build_hex_pixel_grid(tiledata, persistent_state):
    """
    Creates a dictionary mapping hex coordinates to their un-zoomed,
    un-offsetted world pixel centers for fast lookups.
    """
    print("[helpers] ✅ Building hex pixel grid for fast lookups...")
    pixel_grid = {}
    
    # Create a temporary variable_state for the calculation, assuming no zoom or offset
    temp_variable_state = {
        "var_current_zoom": 1.0,
        "var_render_offset": (0, 0)
    }

    for coord, tile in tiledata.items():
        # We use hex_to_pixel from shared_helpers to get the center point
        px, py = hex_to_pixel(tile["coord"][0], tile["coord"][1], persistent_state, temp_variable_state)
        pixel_grid[coord] = (px, py)
        
    return pixel_grid

# ──────────────────────────────────────────────────
# 📏 Calculate World Topology
# ──────────────────────────────────────────────────

def calculate_and_store_map_center(tiledata, persistent_state):
    """
    Calculates the center of mass of the landmass and saves it to persistent_state.
    Also stores the total count and a quick lookup list of land tiles.
    """
    # Create a list of all coordinates for passable (land) tiles.
    land_coords = [
        coord for coord, tile in tiledata.items() if tile.get("passable")
    ]

    # Handle the edge case where there is no land on the map.
    if not land_coords:
        if DEBUG: print("[center] ⚠️ No land tiles found; cannot calculate center.")
        persistent_state["pers_map_center"] = None
        persistent_state["pers_land_count"] = 0
        persistent_state["pers_quick_tile_lookup"] = [] # Ensure lookup is an empty list
        return

    # Save the core data to the persistent state dictionary.
    persistent_state["pers_land_count"] = len(land_coords)
    persistent_state["pers_quick_tile_lookup"] = land_coords

    # Calculate the center of mass for the land tiles.
    sum_q = sum(q for q, r in land_coords)
    sum_r = sum(r for q, r in land_coords)
    
    avg_q = sum_q / len(land_coords)
    avg_r = sum_r / len(land_coords)

    center_q = int(round(avg_q))
    center_r = int(round(avg_r))
    
    # Save the calculated center coordinate.
    center_coord = (center_q, center_r)
    persistent_state["pers_map_center"] = center_coord
    
    # Report success.
    print(f"[tiledata] ✅ Continent center of mass saved as {center_coord}")
    print(f"[tiledata] ✅ Total land tile count saved as {len(land_coords)}")
    print(f"[tiledata] ✅ Quick lookup stored with {len(land_coords)} land tiles.")

def add_distance_from_center_to_tiledata(tiledata, persistent_state):
    """
    Calculates hex distance for every tile from the pre-calculated map center.
    """
    # Get the Map's Center Coordinate
    center_coord = persistent_state.get("pers_map_center")

    # Exit early if the center hasn't been set.
    if not center_coord:
        if DEBUG: print("[center] ⚠️ Map center not found; skipping distance calculation.")
        return

    center_q, center_r = center_coord

    # 📏 Calculate Distance for Every Tile
    for (q, r), tile in tiledata.items():

        # Use the axial distance function to find the hex distance from the center.
        dist = axial_distance(center_q, center_r, q, r)
        # Save the result directly on the tile for later use.
        tile["dist_from_center"] = dist

    if DEBUG:
        # Report the successful completion of the operation.
        print(f"[tiledata] ✅ dist_from_center set (using center at {center_coord})")

def add_distance_from_ocean_to_tiledata(tiledata, persistent_state):
    """
    Uses a breadth-first search (BFS) to calculate the distance of every
    passable tile from the nearest impassable (Ocean) tile.
    """
    
    # 🏞️ Setup for Breadth-First Search (BFS)
    frontier = [] # A list to act as a queue for BFS.
    visited = set() # A set to keep track of tiles we've already processed.

    # 🌊 Initialize Frontier with Ocean Tiles
    # Start the search from all impassable (ocean) tiles, setting their distance to 0.
    for (q, r), tile in tiledata.items():
        if not tile.get("passable"):
            frontier.append(((q, r), 0))
            visited.add((q, r))
            tile["dist_from_ocean"] = 0

    # 🧭 Process the Frontier Queue
    # Expand outward, one layer at a time, to find the distance of every tile.
    head = 0
    while head < len(frontier):
        (q, r), dist = frontier[head]
        head += 1

        # Check each neighbor of the current tile.
        for neighbor_coord in get_neighbors(q, r, persistent_state):

            # Only process unvisited neighbors that are within the map bounds.
            if neighbor_coord not in visited and neighbor_coord in tiledata:
                visited.add(neighbor_coord)
                neighbor_tile = tiledata[neighbor_coord]
                
                # Set the neighbor's distance to one more than the current tile.
                neighbor_tile["dist_from_ocean"] = dist + 1

                # Add the neighbor to the end of the queue for later processing.
                frontier.append((neighbor_coord, dist + 1))

    if DEBUG:
        print(f"[tiledata] ✅ dist_from_ocean calculated for all tiles.")
        print("[tiledata] ✅ Normalized ocean distance calculated for all land tiles.")

def calculate_monsoon_bands(tiledata, persistent_state):
    """
    Calculates east-west bands based on q-coordinate distance from the horizontal center.
    This creates a gradient from the horizontal middle of the continent to the edges.
    
    Adds the following keys to land tiles:
    - `abs_dist_from_q_center`: The absolute distance from the central q-value.
    - `norm_dist_from_q_center`: The normalized distance, from 0.0 (center) to 1.0 (farthest edge).
    """
    # Get all land tile coordinates for processing
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    if not land_coords:
        if DEBUG: print("[elevation] ⚠️ No land tiles found for monsoon bands.")
        return

    # Find the horizontal (q-axis) min, max, and center of the landmass
    all_q_values = [q for q, r in land_coords]
    min_q = min(all_q_values)
    max_q = max(all_q_values)
    center_q = (min_q + max_q) / 2.0

    # Determine the maximum possible q-distance for normalization
    # This is the distance from the center to the farthest edge.
    max_abs_q_dist = max_q - center_q
    if max_abs_q_dist == 0: # Avoid a division-by-zero error on a single-file map
        max_abs_q_dist = 1.0

    # Calculate and store the absolute and normalized distances for each land tile
    for q, r in land_coords:
        tile = tiledata.get((q, r))
        if tile:
            # Calculate the absolute distance from the horizontal center
            abs_dist = abs(q - center_q)
            tile['abs_dist_from_q_center'] = abs_dist
            
            # Normalize the distance to a 0.0-1.0 scale
            norm_dist = abs_dist / max_abs_q_dist
            tile['norm_dist_from_q_center'] = norm_dist
    
    if DEBUG:
        print(f"[elevation] ✅ Monsoon bands (q-distance) calculated.")

def tag_continent_spine(tiledata, persistent_state):
    return
#     """
#     Finds the hub-and-spoke spine and tags each tile on it with rich
#     data: its spoke ID, its distance along the spoke, and the spoke's total length.
#     """
#     # ──────────────────────────────────────────────────
#     # ⚙️ Setup & Dependencies
#     # ──────────────────────────────────────────────────

#     # 🧠 Calculate the minimum distance for a path to be considered "inland".
#     # This is based on the region radius, ensuring spokes stay in the continent's center.
#     region_radius = persistent_state.get("pers_region_radius", 3)
#     min_inland_distance = region_radius + 1

#     # Get the calculated center of the continent to use as the spine's hub.
#     spine_hub_coord = persistent_state.get("pers_map_center")

#     # Check if the calculated center exists and is a passable land tile.
#     if not spine_hub_coord:
#         if DEBUG: print("[tiledata] ⚠️ Map center not found; cannot create spine.")
#         return
        
#     hub_tile = tiledata.get(spine_hub_coord)
#     if not hub_tile or not hub_tile.get("passable"):

#         # If not, find the closest land tile to serve as an alternate hub.
#         if DEBUG: print(f"[tiledata] ⚠️ Center {spine_hub_coord} is not on land. Finding nearest valid tile.")
#         min_dist = float('inf')
#         valid_hub = None
        
#         # Use the pre-calculated land tile lookup for efficiency.
#         for coord in persistent_state.get("pers_quick_tile_lookup", []):
#             dist = axial_distance(spine_hub_coord[0], spine_hub_coord[1], coord[0], coord[1])
#             if dist < min_dist:
#                 min_dist = dist
#                 valid_hub = coord
        
#         spine_hub_coord = valid_hub
#         if DEBUG and spine_hub_coord: print(f"[tiledata]    -> Using {spine_hub_coord} as the spine hub instead.")
    
#     if not spine_hub_coord:
#         if DEBUG: print("[tiledata] ❌ Could not find any valid land tile for spine hub.")
#         return
    
#     centers = persistent_state.get("pers_region_centers", [])
#     spoke_destinations = []

#     for region_data in centers:
#         # Extract the coordinate tuple from the dictionary first
#         center_coord = (region_data["q"], region_data["r"])
#         center_tile = tiledata.get(center_coord)

#         # A destination must be near the coast to ensure spokes radiate outwards.
#         if center_tile and center_tile.get("dist_from_ocean", 0) <= min_inland_distance:
#             if center_coord != spine_hub_coord:
#                 spoke_destinations.append(center_coord) # Now this correctly appends the tuple

#     # Tag the hub tile itself as the origin point of all spokes.
#     if spine_hub_coord in tiledata:
#         tiledata[spine_hub_coord]["spine_data"] = {
#             "spoke_id": 0, "dist_on_spoke": 0, "spoke_max_dist": 0
#         }

#     # Pathfind from the hub to each destination.
#     for i, dest_coord in enumerate(spoke_destinations, start=1):
        
#         # Generate the path, ensuring it stays inland.
#         path = a_star_pathfind(
#             tiledata, spine_hub_coord, dest_coord, persistent_state,
#             min_dist_from_ocean=min_inland_distance
#         )

#         if not path: continue

#         # Tag each tile on the path with rich data about the spoke.
#         path_length = len(path) - 1
#         for dist_on_spoke, coord in enumerate(path):
#             if coord in tiledata:
#                 tiledata[coord]["spine_data"] = {
#                     "spoke_id": i,
#                     "dist_on_spoke": dist_on_spoke,
#                     "spoke_max_dist": path_length
#                 }
    
#     if DEBUG:
#         print(f"[tiledata] ✅ Rich spine data assigned using inland distance of {min_inland_distance}.")