# game_logic/hazard_deck.py
# Manages the hazard card deck, including drawing and shuffling.

import random

class HazardDeck:
    """
    A container for the hazard deck. For now, it generates dummy cards
    on the fly when requested.
    """
    def __init__(self):
        # 🃏 In the future, this will be initialized with a list of all card data.
        self.cards = [] 
        self.discard_pile = []
        # A counter to ensure each dummy card gets a unique ID.
        self._dummy_id_counter = 0

    def _generate_dummy_card(self):
        """Creates a single, randomized dummy card based on the current data contract."""
        self._dummy_id_counter += 1
        
        # Define the possible types for the dummy card.
        card_types = ["Rival", "Predator", "Climate"]
        
        # Create the card data dictionary.
        card_data = {
            "id": f"dummy_{self._dummy_id_counter}",
            "name": "Dummy Card",
            "type": random.choice(card_types),
            "difficulty": random.randint(5, 8)
        }
        return card_data

    def draw_cards(self, count):
        """
        Draws a specified number of cards. If the deck is empty, it generates
        dummy cards as a fallback.
        """
        drawn_cards = []
        for _ in range(count):
            # 🛡️ If the deck is empty, use the fallback dummy generator.
            if not self.cards:
                card = self._generate_dummy_card()
            #  SNEAK PEEK: In the future, you'd just pop from the real deck.
            # else:
            #     card = self.cards.pop()
            drawn_cards.append(card)
        
        print(f"[HazardDeck] ✅ Drew {len(drawn_cards)} cards.")
        return drawn_cards