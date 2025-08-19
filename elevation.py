# elevation.py
# A dedicated module to calculate the three-layer proxy elevation model.

import math
from shared_helpers import axial_distance, get_tagged_points_with_angle_dist

# ──────────────────────────────────────────────────
# 🎨 Config & Constants
# ──────────────────────────────────────────────────

DEBUG = True
# This is the "control panel" for tuning your landscape's feel.
ELEVATION_WEIGHTS = {
    "continental": 2,
    "topographic": 10,
    "coastal":     2,
}

# This prevents coastal land from being at 0 elevation in the continental scale
CONTINENTAL_SCALE_MIN = 0.2

# ──────────────────────────────────────────────────
# ⛰️ Elevation Layer Calculators
# ──────────────────────────────────────────────────

def calculate_continental_scale(tiledata, center_coord):
    """
    Calculates the continental scale, modeling the large, dome-like shape of a continent.
    Adds the 'continental_scale' key to land tiles in place.
    """
    # 헬 helper: Interpolate a 360-degree distance map from coastal points.
    coastal_points = get_tagged_points_with_angle_dist(
        tiledata, center_coord, tag_key="is_coast", tag_values=True
    )
    if not coastal_points:
        if DEBUG: print("[elevation] ⚠️ No coastal points found; skipping continental scale.")
        return

    coastal_points.sort(key=lambda p: p['angle'])
    distance_map = {}
    for i in range(360):
        target_angle = float(i)
        p1 = coastal_points[-1]
        p2 = coastal_points[0]
        for point in coastal_points:
            if point['angle'] <= target_angle: p1 = point
            if point['angle'] >= target_angle:
                p2 = point
                break
        angle_range = (p2['angle'] - p1['angle']) % 360
        target_pos = (target_angle - p1['angle']) % 360
        if angle_range == 0:
            distance_map[i] = p1['dist']
        else:
            interp_ratio = target_pos / angle_range
            distance_map[i] = p1['dist'] * (1 - interp_ratio) + p2['dist'] * interp_ratio

    # ✍️ Apply the scale to each land tile.
    for coord, data in tiledata.items():
        if not data.get("is_ocean"):
            delta_q = coord[0] - center_coord[0]; delta_r = coord[1] - center_coord[1]
            angle = math.degrees(math.atan2(-delta_r, delta_q)) % 360
            dist_from_center = axial_distance(coord[0], coord[1], center_coord[0], center_coord[1])
            max_dist = distance_map.get(int(angle), 1) or 1
            raw_proportional_dist = min(1.0, dist_from_center / max_dist)
            raw_value = 1.0 - raw_proportional_dist
            data['continental_scale'] = CONTINENTAL_SCALE_MIN + (raw_value * (1.0 - CONTINENTAL_SCALE_MIN))

    if DEBUG:
        print(f"[elevation] ✅ Continental scale calculated.")

def calculate_topographic_scale(tiledata):
    """
    Calculates the topographic scale, modeling valleys and peaks relative to mountains.
    Adds the 'topographic_scale' key to land tiles in place.
    """
    land_tiles = [d for d in tiledata.values() if not d.get("is_ocean")]
    all_topo_dists = [d['dist_to_mountain'] for d in land_tiles if d.get('dist_to_mountain') is not None]

    if not all_topo_dists:
        if DEBUG: print("[elevation] ⚠️ No mountain distances found; skipping topographic scale.")
        return

    min_dist, max_dist = min(all_topo_dists), max(all_topo_dists)
    dist_range = max_dist - min_dist if max_dist > min_dist else 1

    for data in land_tiles:
        if data.get('dist_to_mountain') is not None:
            data['topographic_scale'] = 1.0 - ((data['dist_to_mountain'] - min_dist) / dist_range)

    if DEBUG:
        print(f"[elevation] ✅ Topographic scale calculated.")

def calculate_coastal_scale(tiledata):
    """
    Calculates the coastal scale, modeling the gradual rise of land from the sea.
    Adds the 'coastal_scale' key to land tiles in place.
    """
    land_tiles = [d for d in tiledata.values() if not d.get("is_ocean")]
    all_coast_dists = [d['dist_from_ocean'] for d in land_tiles if d.get('dist_from_ocean') is not None]

    if not all_coast_dists:
        if DEBUG: print("[elevation] ⚠️ No ocean distances found; skipping coastal scale.")
        return

    min_dist, max_dist = min(all_coast_dists), max(all_coast_dists)
    dist_range = max_dist - min_dist if max_dist > min_dist else 1

    for data in land_tiles:
        if data.get('dist_from_ocean') is not None:
            data['coastal_scale'] = (data['dist_from_ocean'] - min_dist) / dist_range

    if DEBUG:
        print(f"[elevation] ✅ Coastal scale calculated.")

def combine_and_normalize_elevation(tiledata, weights):
    """
    Combines the three scales into a final, normalized elevation value.
    Adds the 'final_elevation' key to land tiles in place.
    """
    land_tiles = [d for d in tiledata.values() if not d.get("is_ocean")]
    total_weight = sum(weights.values()) or 1
    factors = {key: value / total_weight for key, value in weights.items()}

    final_elevations = {}
    for tile in land_tiles:
        final_val = (tile.get('continental_scale', 0.0) * factors['continental'] +
                     tile.get('topographic_scale', 0.0) * factors['topographic'] +
                     tile.get('coastal_scale', 0.0) * factors['coastal'])
        final_elevations[tile["coord"]] = final_val

    if not final_elevations:
        if DEBUG: print("[elevation] ⚠️ No elevation data to combine.")
        return

    min_elev = min(final_elevations.values()); max_elev = max(final_elevations.values())
    range_elev = max_elev - min_elev or 1

    for coord, final_val in final_elevations.items():
        tiledata[coord]['final_elevation'] = (final_val - min_elev) / range_elev

    print(f"[elevation] ✅ Combined and stored final elevation for {len(land_tiles)} tiles.")

# ──────────────────────────────────────────────────
# 🚀 Orchestrator
# ──────────────────────────────────────────────────

def run_elevation_generation(tiledata, persistent_state):
    """
    The main orchestrator function for the elevation model.
    """
    print("[elevation] 📈 Starting elevation calculation.")
    center_coord = persistent_state.get("pers_map_center")
    if not center_coord:
        if DEBUG: print("[elevation] ❌ Center coordinate not found. Aborting.")
        return

    # 1. Calculate each elevation layer
    calculate_continental_scale(tiledata, center_coord)
    calculate_topographic_scale(tiledata)
    calculate_coastal_scale(tiledata)

    # 2. Combine and normalize the layers into the final elevation
    combine_and_normalize_elevation(tiledata, ELEVATION_WEIGHTS)