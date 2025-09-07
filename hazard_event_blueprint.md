Blueprint: The Hazard Event System (Revised)

This document outlines the final architecture of the Hazard Event system, serving as a guide for any future development. The system is designed to be a robust, data-driven, and visually dynamic feature that is decoupled from other core game systems.

1. The Core Principle: A Tightly-Coupled "Power Tool & Battery"

The Hazard Event feature is a deliberate and practical exception to our "Company Memo" principle. It consists of two primary components that work as a single, integrated unit:

    hazard_manager.py (The 🔋 Battery): This specialist class contains all game logic and state. It knows the rules, manages the card decks and the 3-card queue, calculates outcomes, and decides what happens and when.

    scenes/game_scene/ui/hazard_view.py (The 🎨 Power Tool): This specialist class handles all visual presentation and animation. It receives data and commands directly from the HazardManager and decides how to display information to the player.

These two components have direct references to each other, allowing for simple and efficient communication for their complex, interdependent tasks.

2. The "Game Board" Architecture

To achieve complete animation freedom, the HazardView is architected like a physical game board with separate, independent pieces.

    Visual Trays: The view contains purely visual backdrops (HazardQueueTray, StatTray, DiscardTray). These are static BasePanel objects with decorative borders that serve as visual anchors for the interactive elements. Their dimensions are calculated dynamically to perfectly fit the slots they hold.

    Independent Slots: The actual "game pieces" are UIDataSlot instances. These are independent, tweenable objects that are rendered on top of the trays but are not part of the tray surfaces.

    The Puppeteer (HazardView): The HazardView class acts as the master orchestrator. It is responsible for creating synchronized tweens for both a tray and all the slots on it, making them appear to move together as one cohesive unit (e.g., when toggling visibility).

3. The UIDataSlot: A Data-Driven Component

The system is built upon a single, versatile, and reusable component that perfectly embodies our "Turn Logic into Data" principle.

    A "Dumb Expert": The UIDataSlot class has no game logic. Its single specialty is rendering a structured list of styled text fragments.

    Data-Driven: Its primary method, update_data(line_data), accepts a list of dictionaries prepared by the view. This data structure dictates the text, style, and layout, allowing the HazardManager to control the display without knowing anything about fonts or colors. For example:
    Python

    # Data prepared to show a stat with a positive modifier
    stat_data = [
        {"text": "Fight 5", "style": "default"},
        {"text": " (+1)",  "style": "modifier_good"}
    ]

    Self-Contained: Each UIDataSlot has a fixed size and uses the background_panel_helper to create its own clean, textured background, ensuring text is always readable and that the slot is a distinct visual object ready for animation.

4. Communication Flow

The interaction between the game, the manager, and the view follows a clear, efficient sequence:

    Request (Decoupled): Any system (e.g., GameManager) posts a generic REQUEST_HAZARD_EVENT to the EventBus. This is the system's only interaction with the global event bus.

    Initiation (Direct Call): The HazardManager catches the request and calls a public method on its HazardView instance (e.g., hazard_view.start_hazard_sequence()).

    Player Action (Callback): When the player clicks a UIDataSlot, a callback directly calls a public method on the HazardManager (e.g., hazard_manager.on_card_selected(data)).

    Conclusion (Direct Call): After resolving the outcome, the HazardManager calls a final method on the HazardView (e.g., hazard_view.end_hazard_sequence()) to reset the UI.

This architecture ensures the Hazard Event system is a self-contained, robust, and easily maintainable feature.