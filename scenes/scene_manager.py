# scene_manager.py
# Orchestrates the flow of the game through different scenes (e.g., main menu, loading, in-game).

# The SceneManager only needs to know about the scenes themselves.
# Each scene will be responsible for its own imports.
from .main_menu.scene import MainMenuScene
from .loading_screen.scene import LoadingScene
from .game_scene.scene import GameScene

DEBUG = True
DEV_FADE_OUT_DURATION = 1  # seconds
DEV_FADE_IN_DURATION = 1.5   # seconds

# ──────────────────────────────────────────────────
# 🎬 Scene Manager
# ──────────────────────────────────────────────────

class SceneManager:
    """Orchestrates scene flow using a tween-based fading system."""
    def __init__(self, persistent_state, assets_state, variable_state, notebook, tween_manager):
        
        # Stores references to global game state objects
        self.persistent_state = persistent_state
        self.assets_state = assets_state
        self.variable_state = variable_state
        self.notebook = notebook
        self.tween_manager = tween_manager

        # Sets the main game loop flag to True
        self.running = True

        # A flag to prevent multiple scene transitions at once
        self.is_transitioning = False

        # Initializes all scenes and stores them in a dictionary
        self.scenes = {
            "MAIN_MENU": MainMenuScene(self),
            "LOADING": LoadingScene(self),
            "IN_GAME": GameScene(self)
        }

        # Sets the initial active scene
        self.active_scene_key = "MAIN_MENU"
        self.active_scene = self.scenes[self.active_scene_key]

        # Calls the on_enter method for the first scene
        self.active_scene.on_enter()

       # Kick off the initial fade-in for the very first scene.
        self.tween_manager.add_tween(
            target_dict=self.notebook['FADE'],
            animation_type='value',
            key_to_animate='value',
            start_val=self.notebook['FADE'].get('value', 255),
            end_val=0,
            duration=DEV_FADE_IN_DURATION
        )

    def change_scene(self, new_scene_key, data=None, fade_out_duration=DEV_FADE_OUT_DURATION, fade_in_duration=DEV_FADE_IN_DURATION, on_fade_in_complete=None):
        '''When called, fades out, starts the next scene, and fades it in'''
        # Prevents a new transition if one is already in progress
        if self.is_transitioning: return

        # Sets the flag to indicate a transition is starting
        self.is_transitioning = True

        def on_fade_out_complete():
            # Exits the current scene
            self.active_scene.on_exit()

            # Updates the active scene to the new one
            self.active_scene_key = new_scene_key
            self.active_scene = self.scenes[new_scene_key]

            # Enters the new scene
            self.active_scene.on_enter(data)

            # Create the fade-in tween
            def on_final_transition_complete():

                # Resets the transition flag when the final fade-in is done
                self.is_transitioning = False

                # Calls the optional callback function if provided
                if on_fade_in_complete:
                    on_fade_in_complete()

            # Starts the fade-in animation
            self.tween_manager.add_tween(
                target_dict=self.notebook['FADE'],
                animation_type='value',
                key_to_animate='value',
                start_val=self.notebook['FADE'].get('value', 255), end_val=0, duration=fade_in_duration,
                on_complete=on_final_transition_complete
            )

        # Starts the initial fade-out animation
        self.tween_manager.add_tween(
            target_dict=self.notebook['FADE'],
            animation_type='value',
            key_to_animate='value',
            start_val=self.notebook['FADE'].get('value', 0), end_val=255, duration=fade_out_duration,
            on_complete=on_fade_out_complete
        )

    def handle_events(self, events, mouse_pos):
        '''Delegates event handling to the active scene'''
        self.active_scene.handle_events(events, mouse_pos)

    def update(self, dt):
        '''Delegates the update call to the active scene'''
        self.active_scene.update(dt)

    def quit_game(self):
        '''Sets the running flag to False to exit the main game loop'''
        self.running = False
