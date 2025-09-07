Project File Manifest & Responsibilities for "Prehistoria"

This document provides a high-level overview of the codebase, explaining the purpose of each major file and directory. It is designed to quickly orient any collaborator (human or AI) to the project's architecture.
Core Systems (Root Directory)

These are the global, project-wide systems that orchestrate the entire application.

    main.py: Entry Point. Initializes Pygame, the main game loop, and the SceneManager.

    renderer.py: Global Rendering Engine. Contains the render_giant_z_pot function, the single entry point for all drawing.

    tween_manager.py: Global Animation System. The central manager for all animations.

    ui_manager.py: Global UI Orchestrator. Manages all non-gameplay-critical UI panels like the Family Portrait and Migration Event panel.

Scene Management (scenes/)

This directory manages the different states of the game.

    scenes/scene_manager.py: Scene Switchboard. Handles transitions between different scenes.

    scenes/loading_screen/ & scenes/main_menu/: Self-Contained Scenes.

    scenes/game_scene/: The Core Gameplay Loop.

The Game Scene (scenes/game_scene/)

This is the heart of the project.

    scene.py: Game Scene Orchestrator. Creates all major manager instances (GameManager, HazardManager, MapInteractor, etc.) and routes events and updates between them.

    game_manager.py: Primary Game Logic Manager. The brain for game rules, turn progression, and player state. Delegates details to specialists.

    event_bus.py: The "Company Memo" System. The central switchboard for decoupled communication.

    map_interactor.py: The Map Interaction Specialist. Handles all direct user interaction with the hex grid (hovering, panning, clicking). It owns the MovementUIManager specialist, which handles all visual feedback for movement.

    hazard_manager.py: Hazard Logic Specialist (The "Battery"). Contains all game rules and state management for Hazard Events. Decides what happens and when. Works in a tightly-coupled pair with the HazardView.

    player.py: Player Data Object. A data-rich class representing a player's state.

    pathfinding.py: Stateless Pathfinding Service. A pure, stateless module that provides pathfinding algorithms.

Shared UI Framework (ui/ & scenes/game_scene/ui/)

This top-level directory contains the generic, reusable "toolkit" for building all UI.

    ui/ui_font_and_styles.py: Central Style Guide. The single source of truth for loading all fonts and defining all text styles (e.g., "highlight", "disabled").

    ui/ui_dimensions.py: The Layout Engine. The single source of truth for calculating the size and position of all UI elements and handling text wrapping.

    ui/ui_base_panel_components.py & ui/ui_button_components.py: Procedural Style Generators. Creates our unique "carved wood" and "chipped stone" UI style.

    ui/ui_generic_components.py: Basic Building Blocks. Contains simple, reusable component classes like UITextBlock.

    scenes/game_scene/ui/hazard_view.py: Hazard UI Specialist (The "Power Tool"). Manages all visual presentation for the Hazard Event. Decides how to display information but contains no game logic. It is tightly coupled with the HazardManager.

    scenes/game_scene/ui/: Other UI Panels. Contains other feature-specific "Power Tool & Battery" components, like migration_event_panel.py.

Data & Assets

    species.json: Data-Driven Design Example. Defines all species stats and rules.

    load_assets.py, load_ui_assets.py, load_tile_assets.py: Asset Pipelines. Responsible for loading images and creating procedural assets on startup.