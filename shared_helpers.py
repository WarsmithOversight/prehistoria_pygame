# shared_helpers.py
# Includes various helper modules shared by various scripts

import math
import heapq

DEBUG = True

# ──────────────────────────────────────────────────
# 🌐 Shared State Initializer
# ──────────────────────────────────────────────────
def initialize_shared_helper_states(persistent_state):
    """
    Sets up shared geometry naming for corners, edges, and neighbor offsets.
    Call this once from main after creating persistent_state.
    """

    # ── Pointy-top hex anatomy ───────────────────────────────────────────
    persistent_state["pers_hex_anatomy"] = {
        "corners": {
            0: {"name": "N",  "vector": (0.0, -1.0)},
            1: {"name": "NE", "vector": (1.0, -0.5)},
            2: {"name": "SE", "vector": (1.0, 0.5)},
            3: {"name": "S",  "vector": (0.0, 1.0)},
            4: {"name": "SW", "vector": (-1.0, 0.5)},
            5: {"name": "NW", "vector": (-1.0, -0.5)}
        },
        "edges": {
            0: {"name": "NW", "corner_pair": (5, 0)},
            1: {"name": "NE", "corner_pair": (0, 1)},
            2: {"name": "E",  "corner_pair": (1, 2)},
            3: {"name": "SE", "corner_pair": (2, 3)},
            4: {"name": "SW", "corner_pair": (3, 4)},
            5: {"name": "W",  "corner_pair": (4, 5)}
        }
    }

    # Lookup for name→index (This will update automatically)
    persistent_state["pers_corner_index"] = {
        info["name"]: idx
        for idx, info in persistent_state["pers_hex_anatomy"]["corners"].items()
    }
    persistent_state["pers_edge_index"] = {
        info["name"]: idx
        for idx, info in persistent_state["pers_hex_anatomy"]["edges"].items()
    }

    # ── Neighbor offsets for odd-r layout ────────────────────────────────
    persistent_state["pers_neighbor_offsets"] = {
        "oddr": {
            "even": {  # r % 2 == 0
                "E":  (+1,  0), "NE": ( 0, -1), "NW": (-1, -1),
                "W":  (-1,  0), "SW": (-1, +1), "SE": ( 0, +1),
            },
            "odd": {   # r % 2 == 1
                "E":  (+1,  0), "NE": (+1, -1), "NW": ( 0, -1),
                "W":  (-1,  0), "SW": ( 0, +1), "SE": (+1, +1),
            }
        }
    }

    verified_order = ["NW", "NE", "E", "SE", "SW", "W"]
    persistent_state["pers_neighbor_order"] = verified_order
    persistent_state["pers_bitmask_neighbor_order"] = verified_order

    # Map edges → neighbor directions (pointy-top convention)
    persistent_state["pers_edge_to_neighbor"] = {
        "NW": "NW", "NE": "NE", "E": "E",
        "SE": "SE", "SW": "SW", "W": "W"
    }
    
    persistent_state["pers_axial_dirs"] = {
        0: (+1,  0), 1: (+1, -1), 2: ( 0, -1),
        3: (-1,  0), 4: (-1, +1), 5: ( 0, +1)
    }

# ──────────────────────────────────────────────
# 📐 Coordinate & Distance Math
# ──────────────────────────────────────────────

def axial_to_oddr(x: int, z: int):
    q = x + ((z - (z & 1)) // 2)
    r = z
    return (q, r)

def oddr_to_axial(q: int, r: int):
    x = q - ((r - (r & 1)) // 2)
    z = r
    return (x, z)

def axial_distance(aq, ar, bq, br):
    ax_q, ax_r = oddr_to_axial(aq, ar)
    bx_q, bx_r = oddr_to_axial(bq, br)
    dq = ax_q - bx_q
    dr = ax_r - bx_r
    return (abs(dq) + abs(dq + dr) + abs(dr)) // 2

# ──────────────────────────────────────────────
# 🧭 Grid Topology & Neighbors
# ──────────────────────────────────────────────

def a_star_pathfind(tile_objects, start_coord, end_coord, persistent_state, player):
    # A priority queue to hold nodes to visit, starting with the origin
    frontier = [(0, start_coord)]
    
    # A dictionary to reconstruct the path once the end is found
    came_from = {start_coord: None}
    
    # A dictionary to store the cost of reaching each node
    cost_so_far = {start_coord: 0}
    
    # Process nodes until the frontier is empty
    while frontier:
        # Get the node with the lowest priority (cost + heuristic)
        _, current_coord = heapq.heappop(frontier)
        
        # Exit early if the destination is reached
        if current_coord == end_coord:
            break
        
        # Check all neighbors of the current node
        for next_coord in get_neighbors(current_coord[0], current_coord[1], persistent_state):
            # Get the neighbor's tile object
            tile = tile_objects.get(next_coord)
            
            # Skip this neighbor if it's invalid or impassable
            if not tile or not tile.passable:
                continue

            # 🛑 "Dead Stop" Logic 🛑
            # Check the move color for the neighbor tile, accounting for special abilities.
            move_color = None
            if "river_movement" in player.special_abilities and getattr(tile, 'river_data', None):
                move_color = "good"
            else:
                move_color = player.terrain_movement_map.get(tile.terrain)

            # If the tile is a costly tile, do not consider it as part of a path,
            # unless it is the final destination.
            if move_color in ["medium", "bad"] and next_coord != end_coord:
                continue # Skip this neighbor entirely
                
            # The cost to move to a neighbor is always 1 in this simple model
            new_cost = cost_so_far[current_coord] + 1

            # If the cost to reach this neighbor exceeds the player's movement, skip it
            if new_cost > player.movement_points:
                continue
            
            # If we haven't seen this node before, or found a cheaper path, update it
            if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                cost_so_far[next_coord] = new_cost
                
                # Calculate the priority: total cost so far + estimated distance to the end
                q1, r1 = next_coord
                q2, r2 = end_coord
                priority = new_cost + axial_distance(q1, r1, q2, r2)
                
                # Add the neighbor to the frontier with its new priority
                heapq.heappush(frontier, (priority, next_coord))
                came_from[next_coord] = current_coord
                
    # Reconstruct the path by backtracking from the end node
    path = []
    current = end_coord
    while current != start_coord:
        path.append(current)
        current = came_from.get(current)
        
        # If the path breaks, it means the end was unreachable
        if current is None:
            return [] # Return an empty path
            
    # Add the starting node and reverse the path to the correct order
    path.append(start_coord)
    path.reverse()
    
    return path
def get_neighbors(q, r, persistent_state):
    oddr = persistent_state["pers_neighbor_offsets"]["oddr"]
    parity = "odd" if (r & 1) else "even"
    dir_map = oddr[parity]
    return [(q + dq, r + dr) for d in persistent_state["pers_neighbor_order"] for dq, dr in [dir_map[d]]]

def get_neighbor_in_direction(q, r, direction_name, persistent_state):
    oddr = persistent_state["pers_neighbor_offsets"]["oddr"]
    parity = "odd" if (r & 1) else "even"
    dq, dr = oddr[parity][direction_name]
    return (q + dq, r + dr)

def get_direction_bit(start_coord, end_coord, persistent_state):
    """
    Calculates the bitmask value for a connection from a start_coord 
    to an adjacent end_coord, based on the universal bitmask order.
    """
    # Fetches the order directly from persistent_state
    order = persistent_state.get("pers_bitmask_neighbor_order", [])
    for i, direction in enumerate(order):
        # Finds the neighbor in a given direction
        neighbor = get_neighbor_in_direction(start_coord[0], start_coord[1], direction, persistent_state)
        # If the neighbor matches the target, return the corresponding bit
        if neighbor == end_coord:
            return 1 << (5 - i)
    return 0

def edge_neighbor(q, r, edge_name, persistent_state):
    dir_name = persistent_state["pers_edge_to_neighbor"][edge_name]
    return get_neighbor_in_direction(q, r, dir_name, persistent_state)

# ──────────────────────────────────────────────
# 🗺️ Shape & Region Generation
# ──────────────────────────────────────────────

def get_coords_exactly_distance(q, r, dist):
    aq, ar = oddr_to_axial(q, r)
    results = []
    for dq in range(-dist, dist + 1):
        for dr in range(max(-dist, -dq - dist), min(dist, -dq + dist) + 1):
            if abs(dq) + abs(dr) + abs(-dq - dr) == 2 * dist:
                oq, orr = axial_to_oddr(aq + dq, ar + dr)
                results.append((oq, orr))
    return results

def expand_region_seed(center_q, center_r, R):
    caq, car = oddr_to_axial(center_q, center_r)
    tiles = set()
    for dq in range(-R, R + 1):
        dr_min = max(-R, -dq - R)
        dr_max = min(R, -dq + R)
        for dr in range(dr_min, dr_max + 1):
            aq, ar = caq + dq, car + dr
            oq, orr = axial_to_oddr(aq, ar)
            tiles.add((oq, orr))
    return tiles

# ──────────────────────────────────────────────
# 🎨 Pixel & Render Geometry
# ──────────────────────────────────────────────

def hex_to_pixel(q, r, persistent_state, variable_state):
    # Your original variable names and structure
    tile_hex_w = persistent_state["pers_tile_hex_w"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    scale = variable_state.get("var_current_zoom", 1.0)
    horiz_spacing = tile_hex_w * scale
    vert_spacing = tile_hex_h * 0.75 * scale

    # The one required logic change: use the integer part of 'r' for the odd/even check.
    is_odd_row = int(r) % 2 != 0
    row_indent = horiz_spacing / 2 if is_odd_row else 0

    x = q * horiz_spacing + row_indent
    y = r * vert_spacing
    
    # Your original return structure
    offset_x, offset_y = variable_state.get("var_render_offset", (0, 0))
    return (x + offset_x, y + offset_y)

def hex_geometry(q, r, persistent_state, variable_state):
    anatomy = persistent_state["pers_hex_anatomy"]
    zoom = variable_state.get("var_current_zoom", 1.0)
    cx, cy = hex_to_pixel(q, r, persistent_state, variable_state)
    half_w = (persistent_state["pers_tile_hex_w"] * zoom) / 2
    half_h = (persistent_state["pers_tile_hex_h"] * zoom) / 2
    corners = {}
    for idx, info in anatomy["corners"].items():
        vx, vy = info["vector"]
        corners[idx] = (cx + vx * half_w, cy + vy * half_h)
    edges = {}
    for idx, info in anatomy["edges"].items():
        a, b = info["corner_pair"]
        edges[idx] = (corners[a], corners[b])
    neighbors = {}
    for idx, info in anatomy["edges"].items():
        edge_name = info["name"]
        neighbors[edge_name] = edge_neighbor(q, r, edge_name, persistent_state)
    return {
        "center": (cx, cy), "corners": corners,
        "edges": edges, "neighbors": neighbors
    }

def pixel_to_hex(mouse_pos, persistent_state, variable_state):
    """
    Finds the hex coordinate closest to the given mouse position by checking
    against a pre-calculated grid of hex centers.
    """
    # Get camera state from the variable_state dictionary
    camera_offset = variable_state.get("var_render_offset", (0, 0))
    camera_zoom = variable_state.get("var_current_zoom", 1.0)

    # Get the pre-calculated grid of pixel centers
    pixel_grid = persistent_state.get("pers_hex_pixel_grid", {})
    if not pixel_grid: return None

    # Reverse the camera offset and zoom from the mouse position
    unzoomed_x = (mouse_pos[0] - camera_offset[0]) / camera_zoom
    unzoomed_y = (mouse_pos[1] - camera_offset[1]) / camera_zoom

    closest_coord = None
    min_dist_sq = float('inf')

    # Find the hex center with the smallest squared distance to the mouse
    for coord, center_pos in pixel_grid.items():
        dist_sq = (unzoomed_x - center_pos[0])**2 + (unzoomed_y - center_pos[1])**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_coord = coord
            
    return closest_coord

def get_point_on_bezier_curve(p0, p1, p2, t):
    """
    Calculates a point on a quadratic Bezier curve for a given progress 't' (0.0 to 1.0).
    p0: Start point, p1: Control point, p2: End point.
    """
    x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
    y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
    return (x, y)

# ──────────────────────────────────────────────
# 🔍 Zoom Utilities
# ──────────────────────────────────────────────

def build_zoom_steps(zoom_config):
    min_zoom, max_zoom, step = zoom_config["min_zoom"], zoom_config["max_zoom"], zoom_config["zoom_interval"]
    steps = []
    z = min_zoom
    while z <= max_zoom + 1e-9:
        snapped = round(z / step) * step
        steps.append(snapped)
        z += step
    return steps

def snap_zoom_to_nearest_step(persistent_state, variable_state):
    zoom_config = persistent_state["pers_zoom_config"]
    step, min_zoom, max_zoom = zoom_config["zoom_interval"], zoom_config["min_zoom"], zoom_config["max_zoom"]
    current_zoom = variable_state["var_current_zoom"]
    interval_count = round((current_zoom - min_zoom) / step)
    snap_scale = min_zoom + interval_count * step
    if step < 1.0:
        snap_scale = round(snap_scale / step) * step
    return max(min_zoom, min(max_zoom, snap_scale))

# ──────────────────────────────────────────────
# 💡 Gameplay Helpers
# ──────────────────────────────────────────────

def get_tiles_bordering_tag(tiledata, persistent_state, tag_key, tag_values):
    """
    Finds all tiles that are adjacent to any tile matching the specified tag criteria.
    This is more efficient than iterating through the entire map.

    :param tag_key: The dictionary key for the tag to check (e.g., "terrain", "is_mountain").
    :param tag_values: A list or set of values to match (e.g., ["Mountain"], [True]).
    :return: A set of coordinates for all bordering tiles, excluding the tagged tiles themselves.
    """
    # 1. Find all coordinates of tiles that match the criteria.
    source_coords = {
        coord for coord, tile in tiledata.items()
        if tile.get(tag_key) in tag_values
    }

    if not source_coords:
        return set()

    # 2. Find all unique neighbors of those source tiles.
    bordering_coords = set()
    for q, r in source_coords:
        for neighbor_coord in get_neighbors(q, r, persistent_state):
            # Ensure the neighbor is actually on the map
            if neighbor_coord in tiledata:
                bordering_coords.add(neighbor_coord)

    # 3. Return the set of neighbors, excluding the source tiles themselves.
    return bordering_coords - source_coords

def get_tiles_within_range_of_terrain(tiledata, terrain_list, distance, persistent_state):
    result, visited = set(), set()
    source_tiles = [(q, r) for (q, r), tile in tiledata.items() if tile.get("terrain") in terrain_list]
    for start in source_tiles:
        frontier = [(start, 0)]
        while frontier:
            (q, r), d = frontier.pop(0)
            if (q, r) in visited or d > distance: continue
            visited.add((q, r))
            if d > 0: result.add((q, r))
            for nq, nr in get_neighbors(q, r, persistent_state):
                if (nq, nr) in tiledata:
                    frontier.append(((nq, nr), d + 1))
    return result

def get_tagged_points_with_angle_dist(tiledata, center_coord, tag_key, tag_values):
    """
    Finds all tiles with a specific tag and calculates their angle and distance
    from a central point.

    Args:
        tiledata (dict): The main tiledata dictionary.
        center_coord (tuple): The (q, r) coordinate of the central point.
        tag_key (str): The key to check in each tile's data (e.g., "is_coast").
        tag_values (any or list): The value(s) to match for the given tag_key.
                                  If a list, matches any value in the list.

    Returns:
        list: A list of dictionaries, each with 'angle' and 'dist'.
    """
    # ⚙️ Setup
    points = []
    center_q, center_r = center_coord

    # Ensure tag_values is a list for a consistent check
    if not isinstance(tag_values, list):
        tag_values = [tag_values]

    # 📐 Find Points and Calculate Geometry
    for coord, data in tiledata.items():
        # Check if the tile's tag value is in our list of desired values
        if data.get(tag_key) in tag_values:
            q, r = coord
            delta_q = q - center_q
            delta_r = r - center_r

            # Calculate the angle of the point relative to the map center
            angle = math.degrees(math.atan2(-delta_r, delta_q)) % 360

            # Calculate the hex distance from the center
            dist = axial_distance(q, r, center_q, center_r)
            points.append({'angle': angle, 'dist': dist, 'coord': coord})

    print(f"[geometry] ✅ Found {len(points)} points with tag '{tag_key}' and calculated their geometry.")
    return points

def get_tiles_in_range(start_coord, distance, tile_objects, persistent_state):
    """
    Finds all tile coordinates within a given hex distance from a starting point.

    Args:
        start_coord (tuple): The (q, r) coordinate to start the search from.
        distance (int): The maximum hex distance (radius) to search.
        tile_objects (dict): The main dictionary of all Tile objects.
        persistent_state (dict): The dictionary with shared helper data.

    Returns:
        set: A set of (q, r) coordinates for all tiles within the range.
    """
    # Use a set to automatically handle visited tiles and prevent duplicates
    visited = {start_coord}
    
    # The frontier holds tiles to visit in the current "ring" of the search
    frontier = {start_coord}

    # Expand outward one ring at a time, up to the maximum distance
    for i in range(distance):
        next_frontier = set()
        for coord in frontier:
            # Get all neighbors of the current tile
            q, r = coord
            for neighbor_coord in get_neighbors(q, r, persistent_state):
                # Add the neighbor if it's a valid, unvisited tile
                if neighbor_coord in tile_objects and neighbor_coord not in visited:
                    visited.add(neighbor_coord)
                    next_frontier.add(neighbor_coord)
        # The newly found neighbors become the next ring to expand from
        frontier = next_frontier
        
    return visited