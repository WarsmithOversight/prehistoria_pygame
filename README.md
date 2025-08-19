# Prehistoria Pi Game – To-Do List

## 1. Map Generation
- [ ] Add constant `USE_NATURAL_TERRAIN = True/False` to toggle between natural vs. boardgame tiles  
- [ ] Replace placeholder/dev tiles with authentic 37-hex Region Tiles  

## 2. Quickstart Mode
- [ ] Add constant `QUICKSTART_MODE = True/False`  
- [ ] Skip menus/startup when enabled  
- [ ] Default to “demo map” for testing  
- [ ] Add `QUICKSTART_PRESET = "default_test_map"` for future scenarios  

## 3. Hazard Wheel
- [ ] Implement “slot machine” style highlight animation (tick-tick-tick-CLUNK)  
- [ ] Define wheel as rotating conditions (e.g. “enter region → trigger hazard”)  
- [ ] Decide: single condition per round vs. multiple  

## 4. AI Context Management
- [ ] Add **Dependency Headers** to each script:  
  - External Functions  
  - External State  
  - Notes/assumptions  
- [ ] Use **Dependency Auditor Prompt** to generate Missing Context Checklists  
- [ ] Copy results into headers so files become permanently “AI-ready”  
