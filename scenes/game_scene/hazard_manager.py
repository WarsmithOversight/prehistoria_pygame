# scenes/game_scene/hazard_manager.py

# ──────────────────────────────────────────────────
# 🎨 Imports & Global Variables
# ──────────────────────────────────────────────────
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal

# Define literal types for better type hinting and validation
HazardType = Literal["Predator", "Rival", "Climate"]
PredatorType = Literal["Apex", "Seeker", "Ambusher"]
# 📝 Note: We use 'climate' in the UI for brevity, but 'climate_resistance' is the actual player stat.
StatType = Literal["fight", "flight", "freeze", "territoriality", "climate_resistance"]
EmpowermentConditionType = Literal["terrain"]

# ──────────────────────────────────────────────────
# 🎨 Data Class Definitions
# ──────────────────────────────────────────────────
@dataclass
class HazardCard:
    """A data class to hold all information about a single hazard card."""
    # 🆔 Core card identity
    name: str
    hazard_type: HazardType

    # 🎲 Gameplay stats
    base_difficulty: int
    eligible_stats: List[StatType]

    # ✨ Special rules (optional)
    predator_type: Optional[PredatorType] = None
    empowerment_condition: Optional[Dict[EmpowermentConditionType, List[str]]] = None

    # 📖 UI/Flavor text
    description: str = ""

    def __post_init__(self):
        """Validate the card data after initialization to enforce data integrity."""
        # 🎨 This dictionary maps each hazard type to the EXACT set of stats it's allowed to have.
        # This aligns with our "Turn Logic into Data" principle.
        VALID_STATS_MAP = {
            "Predator": {"fight", "flight", "freeze"},
            "Rival": {"territoriality"},
            "Climate": {"climate_resistance"},
        }
 
        # 1. First, check Predator-specific rules (predator_type must exist).
        if self.hazard_type == "Predator" and not self.predator_type:
            raise ValueError(f"'{self.name}': Predators must have a predator_type.")
 
        # 2. Get the required set of stats for this card's type from our rules dictionary.
        required_stats = VALID_STATS_MAP.get(self.hazard_type)
 
        # 3. Use a single, clear set comparison to ensure the card's stats are exactly correct.
        if not required_stats or set(self.eligible_stats) != required_stats:
            raise ValueError(
                f"'{self.name}' ({self.hazard_type}): Invalid stats. "
                f"Expected exactly {list(required_stats or [])}, but got {self.eligible_stats}."
            )

# ──────────────────────────────────────────────────
# 🏭 Hazard Card Factory
# ──────────────────────────────────────────────────
class HazardCardFactory:
    """
    Defines the blueprint for all hazard cards and can generate randomized
    "dummy" cards for testing and fallback purposes.
    """
    def __init__(self):
        # ✨ Specific name lists for different hazard types.
        self.PREDATOR_RIVAL_NAMES = [
            "Fluffysaurus", "Bouncysaurus", "Calamitasaurus",
            "Doofusaurus", "Gobblesaurus", "Wobblydocus", "Scampysaurus",
            "Snifflesaurus", "Plumpasaurus", "Munchosaurus", "Chonkylobodon",
            "Fartosaurus", "Quackadactylus", "Honkasaurus", "Goofydactylus"
        ]
        self.CLIMATE_NAMES = [
            "Sandstorm", "Superheated Winds", "Droughtfront", "Flash Flood",
            "Sudden Frost", "Monsoon", "Extended Drought", "Wildfire"
        ]
        
        # 🗺️ A comprehensive list of all possible terrains for empowerment conditions.
        self.TERRAIN_TYPES = [
            "Marsh", "Woodlands", "River", "Highlands", "Scrublands",
            "DesertDunes", "Plains", "ForestBroadleaf", "Hills"
        ]

    def create_random_card(self) -> HazardCard:
        """Creates a single, randomized dummy card based on the defined blueprints."""
        # 🎲 --- Determine Card Type & Base Stats ---
        hazard_type: HazardType = random.choice(["Predator", "Rival", "Climate"])
        final_name = "" # Initialize empty name
        
        eligible_stats = []
        predator_type = None

        if hazard_type == "Predator":
            eligible_stats = ["fight", "flight", "freeze"]
            predator_type = random.choice(["Apex", "Seeker", "Ambusher"])
            final_name = random.choice(self.PREDATOR_RIVAL_NAMES)
        elif hazard_type == "Rival":
            eligible_stats = ["territoriality"]
            final_name = random.choice(self.PREDATOR_RIVAL_NAMES)
        elif hazard_type == "Climate":
            eligible_stats = ["climate_resistance"]
            final_name = random.choice(self.CLIMATE_NAMES)

        # 🎲 --- Determine Empowerment ---
        empowerment_condition = None
        if random.random() < 0.6: # 60% chance for a card to have an empowerment condition
            # Randomly select 1 or 2 terrains for the condition.
            # TODO: It should just be 1 condition
            empower_terrains = random.sample(self.TERRAIN_TYPES, k=random.randint(1, 2))
            empowerment_condition = {"terrain": empower_terrains}

        # 🏗️ --- Assemble and Return the Card Object ---
        return HazardCard(
            name=final_name,
            hazard_type=hazard_type,
            base_difficulty=random.randint(5, 8),
            eligible_stats=eligible_stats,
            predator_type=predator_type,
            empowerment_condition=empowerment_condition,
            description=f"A randomly generated hazard approaches!"
        )

# ──────────────────────────────────────────────────
# 🎨 Hazard Manager
# ──────────────────────────────────────────────────
class HazardManager:
    """The 'Power Tool & Battery' for the entire Hazard Event feature."""

    def __init__(self, event_bus, player, tile_objects, master_deck: Optional[List[HazardCard]] = None, hazard_view=None):
        # ⚙️ Store references to core systems
        self.event_bus = event_bus
        self.player = player
        self.tile_objects = tile_objects
        self.hazard_view = hazard_view # Direct reference to the UI

        # 🃏 Deck Management
        self.master_deck = master_deck if master_deck is not None else []
        self.draw_pile = []
        self.discard_pile = []
        self.hazard_queue = [] # The three cards visible to the player in the tray
        
        # 🏭 Instantiate the factory for generating dummy cards if the main deck is empty.
        self.card_factory = HazardCardFactory()

        # Populate the initial deck and draw the first three cards for the queue.
        self._shuffle_deck() # Sets up the draw_pile
        self._fill_queue()   # Draws from draw_pile into hazard_queue

        # 🚩 State for the active event
        self.active_hazard_card: Optional[HazardCard] = None
        self.is_active = False

        # 👂 Register event listeners
        self._register_listeners()
        print("[HazardManager] ✅ Manager initialized and listeners registered.")
        
    def _register_listeners(self):
        """Subscribe to relevant events on the event bus."""
        # This manager is the ONLY one that listens for this request
        self.event_bus.subscribe("REQUEST_HAZARD_EVENT", self.on_hazard_requested)
        self.event_bus.subscribe("ACTIVE_PLAYER_CHANGED", self.on_active_player_changed)

    def _shuffle_deck(self):
        """Resets and shuffles the draw pile."""
        # 🃏 If a master deck was provided, use it.
        if self.master_deck:
            self.draw_pile = self.master_deck.copy()
            random.shuffle(self.draw_pile)
            print(f"[HazardManager] ✅ Shuffled {len(self.draw_pile)} cards from the master deck.")
        # 🏭 Otherwise, generate a new deck using the factory.
        else:
            # Generate a random number of cards for variety in testing.
            num_dummy_cards = random.randint(10, 15)
            self.draw_pile = [self.card_factory.create_random_card() for _ in range(num_dummy_cards)]
            print(f"[HazardManager] ✅ Generated {len(self.draw_pile)} dummy cards from the factory.")
        
        # ♻️ Always clear the discard pile when shuffling.
        self.discard_pile = []

    def _draw_one_card(self) -> Optional[HazardCard]:
        """Draws a single card, handling shuffling the discard pile if needed."""
        # 💡 If the draw pile is empty, try to use the discard pile.
        if not self.draw_pile:
            if self.discard_pile:
                print("[HazardManager] ♻️ Draw pile empty. Shuffling discard pile back in.")
                self.draw_pile = self.discard_pile.copy()
                self.discard_pile.clear()
                random.shuffle(self.draw_pile)
            else:
                # Both piles are empty; regenerate a dummy deck.
                print("[HazardManager] ♻️ All piles empty. Generating a new dummy deck.")
                self._shuffle_deck() # This will create a new draw_pile

        # 🛡️ Final guard to ensure we have cards to draw from.
        if not self.draw_pile:
            print("[HazardManager] ❌ CRITICAL: Could not draw a card. No cards available.")
            return None
  
        return self.draw_pile.pop(0)
 
    def _fill_queue(self):
        """Draws cards until the hazard_queue has 3 cards in it."""
        while len(self.hazard_queue) < 3:
            new_card = self._draw_one_card()
            if new_card:
                self.hazard_queue.append(new_card)
            else:
                break # Stop if we fail to draw a card

    def get_queue_with_empowerment_status(self) -> List[tuple[HazardCard, bool]]:
        """
        Checks each card in the queue for empowerment based on the player's
        current location. This is the crucial data provider for the HazardView.
        """
        # Use our new helper to check each card in the queue.
        return [(card, self._is_card_empowered(card)) for card in self.hazard_queue]

    def _is_card_empowered(self, card: HazardCard) -> bool:
        """
        A helper function to determine if a single card is empowered based on
        the player's current tile terrain.
        """
        # 1. A card can't be empowered if it has no condition.
        if not card.empowerment_condition:
            return False

        # 2. Get the player's current tile from the main tile dictionary.
        player_coord = (self.player.q, self.player.r)
        current_tile = self.tile_objects.get(player_coord)
        
        # 3. If we can't find the tile, it can't be empowered.
        if not current_tile:
            return False

        # 4. Get the list of terrains that empower this card.
        empowering_terrains = card.empowerment_condition.get("terrain", [])
        
        # 5. Return True if the player's current terrain is in the list.
        return current_tile.terrain in empowering_terrains

    def on_hazard_requested(self, event_data):
        """Callback function for when a hazard event is requested."""
        
        # 🛑 Guard Clause: Do not start a new hazard if one is already active.
        if self.is_active:
            print("[HazardManager] ⚠️ Hazard event requested, but one is already active. Request ignored.")
            return
        
        print(f"[HazardManager] ✅ Hazard event requested via '{event_data.get('trigger', 'Unknown Source')}'.")

        # 🎬 Tell the UI to start its sequence using the cards currently in the queue.
        if self.hazard_view:
            # ✨ Refresh the empowerment status right before showing the UI
            queue_data = self.get_queue_with_empowerment_status()
            self.hazard_view.start_hazard_sequence(queue_data)
        else:
            print("[HazardManager] ⚠️ No HazardView assigned to manager. UI will not respond.")

    def on_card_selected(self, chosen_card: HazardCard):
        """Callback from the View when the player has chosen a card from the queue."""
        # 🛡️ Guard clause to prevent multiple hazards from running at once.
        if self.is_active:
            print("[HazardManager] ⚠️ Card selected, but a hazard is already active.")
            return
        print(f"[HazardManager] 👉 Player selected card: {chosen_card.name}")
        self.active_hazard_card = chosen_card
        self.is_active = True
        # The manager now waits for the player to select a stat. The view handles the state transition.

    def on_stat_selected(self, event_data):
        """Event handler for when the player has made their choice. This resolves the outcome."""
        if not self.is_active or not self.active_hazard_card: return

        # Unpack data from the event
        player_stat_name = event_data["stat_name"]
        player_stat_value = event_data["stat_value"]
        
        # 🧠 --- Core Logic: Resolution ---
        # 🎯 1. Get the final difficulty (base + empowerment bonus).
        final_difficulty = self.active_hazard_card.base_difficulty
        if self._is_card_empowered(self.active_hazard_card):
            final_difficulty += 1 # 📝 Simple +1 bonus for now.
            print("[HazardManager] 🔥 Hazard is EMPOWERED! Difficulty increased.")

        # 🎲 2. Roll a d6 and add it to the player's stat.
        roll = random.randint(1, 6)
        player_total = player_stat_value + roll
        
        # ✅ 3. Determine success or failure.
        success = player_total >= final_difficulty

        print(f"[HazardManager] 🎲 Player chose {player_stat_name.upper()}. Player Total: {player_stat_value} + (d6 roll: {roll}) = {player_total}")
        print(f"[HazardManager] 🎯 Final Difficulty: {final_difficulty}. Outcome: {'SUCCESS' if success else 'FAILURE'}")

        # 💔 4. Apply consequences on failure.
        if not success:
            self.player.take_population_damage(1)
            
        # 🎬 Tell the UI to end its sequence. This should happen before replenishing the queue.
        if self.hazard_view:
            self.hazard_view.end_hazard_sequence()

        # 📢 Announce the final result so UI panels can hide themselves.
        self.event_bus.post("HAZARD_EVENT_CONCLUDED", {'success': success})

        # 🃏 Move the used card from the queue to the discard pile and replenish.
        self.discard_pile.append(self.active_hazard_card)
        if self.active_hazard_card in self.hazard_queue:
            self.hazard_queue.remove(self.active_hazard_card)
        self._fill_queue() # Draw a new card to replace the one we just resolved.
 
        # Clean up the manager's state for the next event.
        self.deselect_card()
        
    def deselect_card(self):
        """Cleans up the manager's state after an event concludes."""
        # resetting the active hazard card and active state
        self.active_hazard_card = None
        self.is_active = False

    def on_active_player_changed(self, new_player):
        """Updates the internal reference to the current player."""
        self.player = new_player