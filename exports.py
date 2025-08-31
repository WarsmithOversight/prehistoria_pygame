# exports.py
# A unified script for generating all data and visual asset exports.

import pygame
import math
import json
from renderer import render_giant_z_pot
from shared_helpers import hex_to_pixel

def export_tiledata_json(tiledata):
    """Saves the complete, final tiledata to a JSON file."""
    
    try:

        # Clean the data for JSON serialization, removing any non-standard types
        cleaned = {
            f"{q},{r}": {k: v for k, v in tile.items() if isinstance(v, (int, float, str, list, dict, bool, type(None)))}
            for (q, r), tile in tiledata.items()
        }

        # Open the file and dump the cleaned data
        with open("tiledata_export.json", "w") as f:
            json.dump(cleaned, f, indent=2)
        print("[exports] ✅ Saved tiledata.json.")
    except Exception as e:
        print(f"[exports] ❌ ERROR: Failed to save tiledata.json: {e}")

def run_all_exports(tiledata, persistent_state, assets_state):
    """The main orchestrator function called from third_main.py."""

    # Call the individual export functions in sequence
    export_tiledata_json(tiledata)
