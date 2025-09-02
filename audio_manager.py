# audio_manager.py
# A dedicated controller for managing all game audio, including music and sound effects.

# Replace the entire contents of audio_manager.py with this new code.

import pygame
import os
import random

DEBUG = True

class AudioManager:
    """Handles loading and playback of music and a directory of sound effects."""
    def __init__(self):
        try:
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16) 
            self.music_channel = pygame.mixer.Channel(0)
            print("[AudioManager] ✅ Mixer initialized successfully.")
        except pygame.error as e:
            if DEBUG: print(f"[AudioManager] ❌ Mixer failed to initialize: {e}")
            self.music_channel = None

        self.music_volume = 0.5
        self.sfx_volume = 0.7
        self.current_music = None
        self.sfx_cache = {}

    def load_sfx_directory(self, directory_path):
        """Loads all .wav and .ogg files from a directory into the SFX cache."""
        if not os.path.isdir(directory_path):
            if DEBUG: print(f"[AudioManager] ❌ SFX directory not found: {directory_path}")
            return

        for filename in os.listdir(directory_path):
            if filename.endswith((".wav", ".ogg")):
                full_path = os.path.join(directory_path, filename)
                try:
                    # The filename itself is used as the key.
                    self.sfx_cache[filename] = pygame.mixer.Sound(full_path)
                except pygame.error as e:
                    if DEBUG: print(f"[AudioManager] ❌ Failed to load SFX '{filename}': {e}")
        
        print(f"[AudioManager] ✅ Loaded {len(self.sfx_cache)} sound effects from '{directory_path}'.")

    def play_sfx(self, whitelist=None, blacklist=None):
        """
        Plays a random SFX, optionally filtered by a whitelist or blacklist of filenames.
        """
        # 🎛️ Start with a list of all available sound filenames.
        candidate_sfx = list(self.sfx_cache.keys())
        if not candidate_sfx:
            if DEBUG: print("[AudioManager] ⚠️ No sound effects loaded to play.")
            return

        # ✅ Apply whitelist if one is provided.
        if whitelist:
            candidate_sfx = [sfx for sfx in candidate_sfx if sfx in whitelist]
        # ❌ Apply blacklist if no whitelist was provided.
        elif blacklist:
            candidate_sfx = [sfx for sfx in candidate_sfx if sfx not in blacklist]

        # 🔊 Check if any sounds matched the criteria.
        if not candidate_sfx:
            if DEBUG: print("[AudioManager] ⚠️ No sound effects matched the filter criteria.")
            return

        # 🎲 Select a random sound from the filtered list.
        chosen_sfx_key = random.choice(candidate_sfx)
        sound = self.sfx_cache[chosen_sfx_key]
        sound.set_volume(self.sfx_volume)
        sound.play()

        # 📢 Print the chosen filename to the console for easy debugging.
        print(f"[Audio] ▶️ Played SFX: {chosen_sfx_key}")

    def play_music(self, filepath, loops=-1):
        """Loads and plays looping background music on its dedicated channel."""
        if not self.music_channel:
            if DEBUG: print("[AudioManager] ❌ Music channel not available.")
            return
        if not os.path.exists(filepath):
            if DEBUG: print(f"[AudioManager] ❌ Music file not found: {filepath}")
            return
            
        try:
            self.music_channel.stop()
            music_sound = pygame.mixer.Sound(filepath)
            self.current_music = music_sound
            self.music_channel.set_volume(self.music_volume)
            self.music_channel.play(self.current_music, loops=loops)
            print(f"[AudioManager] ✅ Now playing: {filepath}")
        except pygame.error as e:
            if DEBUG: print(f"[AudioManager] ❌ Failed to play music: {e}")