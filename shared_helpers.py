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
            1: {"name": "NE", "vector": (0.8660254, -0.5)},
            2: {"name": "SE", "vector": (0.8660254, 0.5)},
            3: {"name": "S",  "vector": (0.0, 1.0)},
            4: {"name": "SW", "vector": (-0.8660254, 0.5)},
            5: {"name": "NW", "vector": (-0.8660254, -0.5)}
        },
        "edges": {
            # ✅ FIX: Re-ordered to match the verified bitmask/asset convention.
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

    # ✅ UNIFIED: The single, verified order for ALL operations.
    verified_order = ["NW", "NE", "E", "SE", "SW", "W"]
    persistent_state["pers_neighbor_order"] = verified_order
    persistent_state["pers_bitmask_neighbor_order"] = verified_order # Kept for clarity in rendering code

    # Map edges → neighbor directions (pointy-top convention)
    persistent_state["pers_edge_to_neighbor"] = {
        "NW": "NW", "NE": "NE", "E": "E",
        "SE": "SE", "SW": "SW", "W": "W"
    }
    
    # ... (rest of the file is unchanged) ...
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

def a_star_pathfind(tiledata, start_coord, end_coord, persistent_state, min_dist_from_ocean=0):
    frontier = [(0, start_coord)]
    came_from = {start_coord: None}
    cost_so_far = {start_coord: 0}
    while frontier:
        _, current_coord = heapq.heappop(frontier)
        if current_coord == end_coord: break
        for next_coord in get_neighbors(current_coord[0], current_coord[1], persistent_state):
            tile = tiledata.get(next_coord)
            if not tile or not tile.get("passable"): continue
            if tile.get("dist_from_ocean", 0) < min_dist_from_ocean: continue
            new_cost = cost_so_far[current_coord] + 1
            if next_coord not in cost_so_far or new_cost < cost_so_far[next_coord]:
                cost_so_far[next_coord] = new_cost
                q1, r1 = next_coord
                q2, r2 = end_coord
                priority = new_cost + axial_distance(q1, r1, q2, r2)
                heapq.heappush(frontier, (priority, next_coord))
                came_from[next_coord] = current_coord
    path = []
    current = end_coord
    while current != start_coord:
        path.append(current)
        current = came_from.get(current)
        if current is None: return []
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

def hex_to_pixel(q: int, r: int, persistent_state, variable_state):
    tile_hex_w = persistent_state["pers_tile_hex_w"]
    tile_hex_h = persistent_state["pers_tile_hex_h"]
    scale = variable_state.get("var_current_zoom", 1.0)
    horiz_spacing = tile_hex_w * scale
    vert_spacing = tile_hex_h * 0.75 * scale
    x = q * horiz_spacing + (horiz_spacing / 2 if r & 1 else 0)
    y = r * vert_spacing
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

# In shared_helpers.py

import math # Make sure math is imported

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
    # ──────────────────────────────────────────────────
    # ⚙️ Setup
    # ──────────────────────────────────────────────────
    points = []
    center_q, center_r = center_coord

    # Ensure tag_values is a list for a consistent check
    if not isinstance(tag_values, list):
        tag_values = [tag_values]

    # ──────────────────────────────────────────────────
    # 📐 Find Points and Calculate Geometry
    # ──────────────────────────────────────────────────
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

    print(f"[helpers] ✅ Found {len(points)} points with tag '{tag_key}' and calculated their geometry.")
    return points