# elevation.py
# A dedicated module to calculate the four-layer proxy elevation model.

import math
from shared_helpers import axial_distance, get_tagged_points_with_angle_dist

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
# This is the "control panel" for tuning your landscape's feel.
ELEVATION_WEIGHTS = {
    "continental": 0,   # 1
    "topographic": 10,
    "coastal":     1,   # 2
    "vertical":    0,   # 2
}

# This prevents coastal land from being at 0 elevation in the continental scale
CONTINENTAL_SCALE_MIN = 0.2

# ──────────────────────────────────────────────────
# ⛰️ Elevation Layer Calculators
# ──────────────────────────────────────────────────

def calculate_continental_scale(tiledata, persistent_state):
    """
    Calculates the continental scale, modeling the large, dome-like shape of a continent.
    Adds the 'continental_scale' key to land tiles in place.
    """
    center_coord = persistent_state.get("pers_map_center")
    if not center_coord:
        if DEBUG: print("[elevation] ⚠️ Center coordinate not found; skipping continental scale.")
        return
    
    # Get all coastal points and their distance and angle from the map center
    coastal_points = get_tagged_points_with_angle_dist(
        tiledata, center_coord, tag_key="is_coast", tag_values=True
    )
    # Handle the edge case where no coastal points exist
    if not coastal_points:
        if DEBUG: print("[elevation] ⚠️ No coastal points found; skipping continental scale.")
        return

    # Sort coastal points by their angle to the center for ordered interpolation
    coastal_points.sort(key=lambda p: p['angle'])

    # Create a dictionary to store the maximum distance for each degree
    distance_map = {}
    for i in range(360):
        # Find the two coastal points that bracket the current angle
        target_angle = float(i)
        p1 = coastal_points[-1]
        p2 = coastal_points[0]
        for point in coastal_points:
            if point['angle'] <= target_angle: p1 = point
            if point['angle'] >= target_angle:
                p2 = point
                break

        # Calculate the angular range between the two points
        angle_range = (p2['angle'] - p1['angle']) % 360

        # Determine the position of the target angle within that range
        target_pos = (target_angle - p1['angle']) % 360

        # Perform linear interpolation to estimate the distance for the current angle
        if angle_range == 0:
            distance_map[i] = p1['dist']
        else:
            interp_ratio = target_pos / angle_range
            distance_map[i] = p1['dist'] * (1 - interp_ratio) + p2['dist'] * interp_ratio

    # Loop through land coords
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])
    for coord in land_coords:
        data = tiledata[coord]

        # Calculate the tile's angle and distance from the map center
        delta_q = coord[0] - center_coord[0]; delta_r = coord[1] - center_coord[1]
        angle = math.degrees(math.atan2(-delta_r, delta_q)) % 360
        dist_from_center = axial_distance(coord[0], coord[1], center_coord[0], center_coord[1])
        
        # Find the max distance for the tile's angle from the interpolated distance map            
        max_dist = distance_map.get(int(angle), 1) or 1
    
        # Calculate a raw proportional distance, capped at 1.0
        raw_proportional_dist = min(1.0, dist_from_center / max_dist)

        # Invert the proportional distance so that the center of the continent is high (1.0)
        raw_value = 1.0 - raw_proportional_dist

        # Scale the raw value to fit within the predefined min/max range, preventing 0 elevation on coasts
        data['continental_scale'] = CONTINENTAL_SCALE_MIN + (raw_value * (1.0 - CONTINENTAL_SCALE_MIN))

    # Log completion for debugging
    if DEBUG:
        print(f"[elevation] ✅ Continental scale calculated.")

def calculate_topographic_scale(tiledata, persistent_state):
    """
    Calculates the topographic scale, modeling valleys and peaks relative to mountains.
    Adds the 'topographic_scale' key to land tiles in place.
    """

    # Isolate all land tiles to work with
    land_tiles = [tiledata[coord] for coord in persistent_state.get("pers_quick_tile_lookup", [])]
    
    # Collect all existing 'dist_to_mountain' values from the land tiles    
    all_topo_dists = [d['dist_to_mountain'] for d in land_tiles if d.get('dist_to_mountain') is not None]

    # Handle the edge case where no mountain distances are available
    if not all_topo_dists:
        if DEBUG: print("[elevation] ⚠️ No mountain distances found; skipping topographic scale.")
        return

    # Find the min and max distances to normalize the range
    min_dist, max_dist = min(all_topo_dists), max(all_topo_dists)
    dist_range = max_dist - min_dist if max_dist > min_dist else 1

    # Normalize and apply the topographic scale to each tile
    for data in land_tiles:
        if data.get('dist_to_mountain') is not None:
            # ✨ Round the final value to 4 decimal places for cleaner data.
            value = 1.0 - ((data['dist_to_mountain'] - min_dist) / dist_range)
            data['topographic_scale'] = round(value, 4)

    # Log completion for debugging
    if DEBUG:
        print(f"[elevation] ✅ Topographic scale calculated.")

def calculate_coastal_scale(tiledata, persistent_state):
    """
    Calculates the coastal scale, modeling the gradual rise of land from the sea.
    Adds the 'coastal_scale' key to land tiles in place.
    """

    # Isolate all land tiles to work with
    land_tiles = [tiledata[coord] for coord in persistent_state.get("pers_quick_tile_lookup", [])]
    
    # Collect all existing 'dist_from_ocean' values    
    all_coast_dists = [d['dist_from_ocean'] for d in land_tiles if d.get('dist_from_ocean') is not None]

    # Handle the edge case where no ocean distances are available
    if not all_coast_dists:
        if DEBUG: print("[elevation] ⚠️ No ocean distances found; skipping coastal scale.")
        return

    # Find the min and max distances to normalize the range
    min_dist, max_dist = min(all_coast_dists), max(all_coast_dists)
    dist_range = max_dist - min_dist if max_dist > min_dist else 1

    # Normalize and apply the coastal scale to each tile
    for data in land_tiles:
        if data.get('dist_from_ocean') is not None:
            data['coastal_scale'] = (data['dist_from_ocean'] - min_dist) / dist_range

    # Log completion for debugging
    if DEBUG:
        print(f"[elevation] ✅ Coastal scale calculated.")

def calculate_vertical_scale(tiledata, persistent_state):
    """
    Applies a simple top-to-bottom (north-to-south) elevation gradient.
    This encourages rivers to flow south.
    """
    # Get all land tile coordinates for efficient processing
    land_coords = persistent_state.get("pers_quick_tile_lookup", [])

    # Handle the edge case where no land tiles are available
    if not land_coords:
        if DEBUG: print("[elevation] ⚠️ No land tiles found for vertical scale.")
        return

    # Find the min and max row numbers (r-coordinates) for the landmass
    min_r = min(r for q, r in land_coords)
    max_r = max(r for q, r in land_coords)
    range_r = max_r - min_r if max_r > min_r else 1

    # Apply the normalized, inverted vertical scale to each land tile
    for q, r in land_coords:
        # Normalize the row position from 0.0 (top) to 1.0 (bottom)
        norm_r = (r - min_r) / range_r
        # Invert the value so north (top) is high (1.0) and south (bottom) is low (0.0)
        tiledata[(q, r)]['vertical_scale'] = 1.0 - norm_r
    
    # Log completion for debugging
    if DEBUG:
        print(f"[elevation] ✅ Vertical north-to-south scale calculated.")


def combine_and_normalize_elevation(tiledata, persistent_state, weights):
    """
    Combines the three scales into a final, normalized elevation value.
    Adds the 'final_elevation' key to land tiles in place.
    """

    # Isolate all land tiles to work with
    land_tiles = [tiledata[coord] for coord in persistent_state.get("pers_quick_tile_lookup", [])]
    
    # Calculate the total weight to use for normalization    
    total_weight = sum(weights.values()) or 1

    # Create a new dictionary with the factors for each elevation scale
    factors = {key: value / total_weight for key, value in weights.items()}

    # Initialize a dictionary to store the raw, combined elevation values
    final_elevations = {}
    for tile in land_tiles:

        # Sum the weighted values of each scale to get a raw elevation
        final_val = (tile.get('continental_scale', 0.0) * factors['continental'] +
                     tile.get('topographic_scale', 0.0) * factors['topographic'] +
                     tile.get('coastal_scale', 0.0) * factors['coastal'] +
                     tile.get('vertical_scale', 0.0) * factors['vertical'])
        final_elevations[tile["coord"]] = final_val

    # Handle the edge case where no elevation data was calculated
    if not final_elevations:
        if DEBUG: print("[elevation] ⚠️ No elevation data to combine.")
        return

    # Find the min and max of the raw final elevations to prepare for normalization
    min_elev = min(final_elevations.values()); max_elev = max(final_elevations.values())
    range_elev = max_elev - min_elev or 1

    # Normalize each raw elevation value and store it in the tile's data
    for coord, final_val in final_elevations.items():
        normalized_value = (final_val - min_elev) / range_elev
        # ✨ Round the final value to 4 decimal places for cleaner data.
        tiledata[coord]['final_elevation'] = round(normalized_value, 4)

    # Log completion for debugging
    print(f"[elevation] ✅ Combined and stored final elevation for {len(land_tiles)} tiles.")

# ──────────────────────────────────────────────────
# 🚀 Orchestrator
# ──────────────────────────────────────────────────

def run_elevation_generation(tiledata, persistent_state):
    """
    The main orchestrator function for the elevation model.
    """

    # Calculate the large-scale continental dome shape
    calculate_continental_scale(tiledata, persistent_state)

    # Calculate the small-scale peaks and valleys relative to mountains
    calculate_topographic_scale(tiledata, persistent_state)

    # Calculate the gradual slope up from the coastline
    calculate_coastal_scale(tiledata, persistent_state)

    # Apply a north-to-south elevation bias for river flow
    calculate_vertical_scale(tiledata, persistent_state)

    # Combine and normalize the layers into the final elevation
    combine_and_normalize_elevation(tiledata, persistent_state, ELEVATION_WEIGHTS)