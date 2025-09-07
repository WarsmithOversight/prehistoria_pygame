best_practices.md
AI Onboarding Guide for the "Prehistoria" Project

Welcome. You are an AI assistant collaborating on "Prehistoria," a Pygame-based prototype for a board game. This document outlines our core development philosophy and architectural maxims. Adhering to these principles is critical for maintaining the project's long-term health and ease of development.
The Core Philosophy: The Single Responsibility Principle Extended

Our primary goal is to create a dynamic system where new features can be added with minimal changes to existing code. The golden rule is:

Minimize the number of files you need to touch to add, change, or fix a single feature.

If adding a new button requires editing seven different files, our architecture has failed.
Architectural Maxims

We have established several "named" principles during development. You must understand and apply them.

1. The "Power Tool & Battery" Principle (High Cohesion)

    Maxim: Code that is used together and changes together must be kept in the same file.

    What it means: When a feature consists of tightly-coupled logic (the "battery") and UI (the "power tool"), they should live together as a single, self-contained unit.

    Good Example: migration_event_panel.py, which contains both the MigrationEventManager logic and the MigrationEventPanel UI class.

    Bad Example: Having a migration_event_manager.py file and a separate migration_event_panel.py file, forcing us to edit both to change one feature.

2. The "Company Memo" Principle (Decoupling with Events)

    Maxim: Major, independent systems must communicate through the central EventBus, not by calling each other's methods directly.

    What it means: A system should announce that something has happened (e.g., "TURN_STARTED") rather than telling another system what to do (e.g., migration_panel.start_animation()). This keeps systems decoupled and "pluggable."

    Good Example: The GameManager posts TURN_STARTED. The MigrationEventPanel listens for this and reacts independently. The GameManager has no direct knowledge of the panel.

    Bad Example: The GameManager having a direct reference self.migration_panel and calling self.migration_panel.start_turn_animation().

3. "Managers Should Delegate, Not Micromanage"

    Maxim: High-level orchestrators (GameManager, UIManager) should manage state and delegate tasks, not implement low-level logic.

    What it means: A manager's job is to receive information and pass it to the correct specialist. It should not be performing detailed calculations or manipulating the visual state of individual components.

    Good Example: GameManager calculates movement data and posts it in an event. The MovementUIManager listens for that event and handles the complex task of coloring tiles and drawing path overlays.

    Bad Example: The GameManager looping through tiles to set their primary_move_color attribute itself.

4. "Turn Logic into Data" (Data-Driven Design)

    Maxim: Game rules, content, and configurations should be represented as simple data objects/classes, not as hard-coded if/elif/else logic.

    What it means: This separates the "what" (the data) from the "how" (the logic). Adding new content should only require adding a new data entry, not changing the code that processes it.

    Good Example: The MigrationEvent class. To add a new event, we just add a new instance of the class to the manager's list. The animation and selection logic handles it automatically.

    Bad Example: Having an if/elif block in the animation code for every single possible migration event.

