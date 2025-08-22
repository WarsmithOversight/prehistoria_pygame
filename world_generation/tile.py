# In tile.py

class Tile:
    """Represents a single tile that dynamically accepts any attributes."""
    
    def __init__(self, coord, initial_data):
        self.q, self.r = coord
        for key, value in initial_data.items():
            setattr(self, key, value)

    def __repr__(self):
        terrain = getattr(self, 'terrain', 'Unknown')
        return f"<Tile at {(self.q, self.r)} - Terrain: {terrain}>"

# ──────────────────────────────────────────────────
# 🛠️ Helper Function (Refined)
# ──────────────────────────────────────────────────

def create_tile_objects_from_data(raw_tiledata):
    """
    Converts a dictionary of raw tile data into a dictionary of Tile objects.
    """
    print("[Tile Helper] ✅ Converting raw tiledata to Tile objects...")
    
    # 1. Create a new, empty dictionary right here.
    tile_objects = {}
    
    # 2. Iterate and populate it.
    for coord, data in raw_tiledata.items():
        tile_objects[coord] = Tile(coord, data)
    
    print(f"[Tile Helper] ✅ Successfully created {len(tile_objects)} Tile objects.")
    
    # 3. Return the newly created dictionary.
    return tile_objects