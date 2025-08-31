# audio_manager.py
# A dedicated controller for managing all game audio, including music and sound effects.

import pygame
import os

DEBUG = True

class AudioManager:
    """Handles loading and playback of music and sound effects."""
    def __init__(self):
        try:
            # Use a high-quality preset for the mixer
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            pygame.mixer.init()

            # Set aside channels for different sound types
            pygame.mixer.set_num_channels(16) 
            self.music_channel = pygame.mixer.Channel(0)
            print("[AudioManager] ✅ Mixer initialized successfully.")

        except pygame.error as e:
            if DEBUG: print(f"[AudioManager] ❌ Mixer failed to initialize: {e}")
            self.music_channel = None

        self.music_volume = 0.5 # Default music volume
        self.sfx_volume = 0.8   # Default SFX volume
        self.current_music = None # Holds a reference to the playing sound

    def play_music(self, filepath, loops=-1):
        """Loads and plays looping background music on its dedicated channel."""
        if not self.music_channel:
            if DEBUG: print("[AudioManager] ❌ Music channel not available.")
            return

        # Check if the file exists before trying to load it
        if not os.path.exists(filepath):
            if DEBUG: print(f"[AudioManager] ❌ Music file not found: {filepath}")
            return
            
        try:
            # Stop any music that might already be playing.
            self.music_channel.stop()

            # Load the music and play it on a loop
            music_sound = pygame.mixer.Sound(filepath)
            self.current_music = music_sound # ✨ FIX: Store a reference
            self.music_channel.set_volume(self.music_volume)
            self.music_channel.play(self.current_music, loops=loops)
            print(f"[AudioManager] ✅ Now playing: {filepath}")
        except pygame.error as e:
            if DEBUG: print(f"[AudioManager] ❌ Failed to play music: {e}")