# sk_plugins_media.py
# ====================
# God Mode: Spotify + YouTube Control
# Requires: pip install spotipy pywhatkit

import os
from typing import Annotated
from semantic_kernel.functions import kernel_function


# ============================================
# SPOTIFY CREDENTIALS - USER MUST FILL THESE
# ============================================
# Go to https://developer.spotify.com/dashboard
# Create an app, get your credentials
# Add redirect URI: http://localhost:8888/callback

SPOTIFY_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
SPOTIFY_CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"


# ============================================
# Spotify Plugin - Full Playback Control
# ============================================

class SpotifyPlugin:
    """
    Control Spotify playback - play, pause, like, search.
    Requires Premium account for playback control.
    """
    
    def __init__(self):
        self.sp = None
        self._init_spotify()
    
    def _init_spotify(self):
        """Initialize Spotify client with OAuth."""
        if SPOTIFY_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
            print("[SPOTIFY] Not configured - set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
            return
        
        try:
            from spotipy import Spotify
            from spotipy.oauth2 import SpotifyOAuth
            
            scope = "user-modify-playback-state user-read-currently-playing user-read-playback-state user-library-modify"
            
            auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=scope
            )
            
            self.sp = Spotify(auth_manager=auth_manager)
            print("[SPOTIFY] Connected successfully!")
            
        except ImportError:
            print("[SPOTIFY] spotipy not installed - run: pip install spotipy")
        except Exception as e:
            print("[SPOTIFY] Auth failed:", str(e)[:50])
    
    @kernel_function(
        name="spotify_play_track",
        description="Play a song on Spotify. Use when user says 'play X on Spotify'"
    )
    def play_track(
        self,
        track_name: Annotated[str, "Name of the song/artist to play on Spotify"]
    ) -> str:
        """Aggressive Spotify Link Hunter - tries 3 different strategies."""
        from duckduckgo_search import DDGS
        import webbrowser
        
        queries = [
            f"{track_name} spotify track",          # Specific
            f"{track_name} spotify",                # General
            f"site:open.spotify.com {track_name}"   # Site specific
        ]
        
        print(f"[ARCH] Spotify Hunt started for: {track_name}")
        
        for q in queries:
            print(f"[ARCH] Trying: {q}")
            try:
                results = DDGS().text(q, max_results=3)
                for res in results:
                    url = res.get('href', '')
                    # Validate it's a real track link
                    if 'open.spotify.com/track' in url:
                        print(f"[ARCH] FOUND: {url}")
                        webbrowser.open(url)
                        return f"SUCCESS: Playing {track_name}"
            except:
                continue  # Try next query
        
        return "FAILURE: Tried 3 search strategies but could not find a Spotify track link."
    
    @kernel_function(
        name="spotify_pause_resume",
        description="Pause or resume Spotify playback"
    )
    def pause_resume(self) -> str:
        """Toggle Spotify playback."""
        if self.sp is None:
            return "Spotify not configured"
        
        try:
            current = self.sp.current_playback()
            
            if current is None:
                return "Nothing playing on Spotify"
            
            if current["is_playing"]:
                self.sp.pause_playback()
                return "Spotify paused"
            else:
                self.sp.start_playback()
                return "Spotify resumed"
                
        except Exception as e:
            return "Spotify error: " + str(e)
    
    @kernel_function(
        name="spotify_next",
        description="Skip to next track on Spotify"
    )
    def next_track(self) -> str:
        """Skip to next track."""
        if self.sp is None:
            return "Spotify not configured"
        
        try:
            self.sp.next_track()
            return "Skipped to next track"
        except Exception as e:
            return "Spotify error: " + str(e)
    
    @kernel_function(
        name="spotify_previous",
        description="Go to previous track on Spotify"
    )
    def previous_track(self) -> str:
        """Go to previous track."""
        if self.sp is None:
            return "Spotify not configured"
        
        try:
            self.sp.previous_track()
            return "Went to previous track"
        except Exception as e:
            return "Spotify error: " + str(e)
    
    @kernel_function(
        name="spotify_like_song",
        description="Add current song to Liked Songs. Use when user says 'I love this song' or 'like this'"
    )
    def add_to_liked(self) -> str:
        """Add currently playing song to Liked Songs."""
        if self.sp is None:
            return "Spotify not configured"
        
        try:
            current = self.sp.current_playback()
            
            if current is None or current.get("item") is None:
                return "Nothing playing on Spotify"
            
            track_id = current["item"]["id"]
            track_name = current["item"]["name"]
            
            self.sp.current_user_saved_tracks_add([track_id])
            
            return "Added '" + track_name + "' to your Liked Songs!"
            
        except Exception as e:
            return "Spotify error: " + str(e)
    
    @kernel_function(
        name="spotify_now_playing",
        description="Get the currently playing song on Spotify"
    )
    def now_playing(self) -> str:
        """Get currently playing track info."""
        if self.sp is None:
            return "Spotify not configured"
        
        try:
            current = self.sp.current_playback()
            
            if current is None or current.get("item") is None:
                return "Nothing playing on Spotify"
            
            track = current["item"]
            name = track["name"]
            artist = track["artists"][0]["name"]
            is_playing = "Playing" if current["is_playing"] else "Paused"
            
            return is_playing + ": '" + name + "' by " + artist
            
        except Exception as e:
            return "Spotify error: " + str(e)


# ============================================
# YouTube Plugin - Browser Auto-Play
# ============================================

class YouTubePlugin:
    """
    Control YouTube via pywhatkit.
    Opens browser and auto-plays first result.
    """
    
    @kernel_function(
        name="youtube_play",
        description="Play a video on YouTube. Use when user says 'play X on YouTube' or 'watch X'"
    )
    def play_video(
        self,
        topic: Annotated[str, "The video/song to play on YouTube"]
    ) -> str:
        """Open YouTube and play a video."""
        try:
            import pywhatkit
            
            # pywhatkit.playonyt searches and opens direct video URL
            pywhatkit.playonyt(topic)
            
            return "Playing '" + topic + "' on YouTube"
            
        except ImportError:
            # Fallback to browser
            import webbrowser
            import urllib.parse
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(topic)
            webbrowser.open(url)
            return "Opened YouTube search for '" + topic + "' (install pywhatkit for auto-play)"
            
        except Exception as e:
            return "YouTube error: " + str(e)
    
    @kernel_function(
        name="youtube_search",
        description="Search YouTube without auto-playing"
    )
    def search_video(
        self,
        query: Annotated[str, "What to search on YouTube"]
    ) -> str:
        """Open YouTube search results."""
        try:
            import webbrowser
            import urllib.parse
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
            webbrowser.open(url)
            return "Opened YouTube search for '" + query + "'"
        except Exception as e:
            return "Error: " + str(e)


# ============================================
# Media Control Plugin - Universal Controls
# Uses pyautogui for native Windows media keys
# ============================================

class MediaControlPlugin:
    """
    Universal media control using Windows media keys.
    Works with any active media player (YouTube, Spotify, VLC, etc.)
    NO taskkill or force-close - professional approach.
    """
    
    @kernel_function(
        name="stop_media",
        description="Stop/pause any playing media. Use when user says 'stop', 'quiet', 'pause', 'silence'. DO NOT close apps."
    )
    def stop_media(self) -> str:
        """Stop/pause the currently playing media."""
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Media paused"
        except ImportError:
            return "pyautogui not installed. Run: pip install pyautogui"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="play_media",
        description="Resume playing media. Use when user says 'play', 'resume', 'continue'."
    )
    def play_media(self) -> str:
        """Resume playing media."""
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Media resumed"
        except ImportError:
            return "pyautogui not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="next_media",
        description="Skip to next track in any media player."
    )
    def next_media(self) -> str:
        """Skip to next track."""
        try:
            import pyautogui
            pyautogui.press("nexttrack")
            return "Skipped to next track"
        except ImportError:
            return "pyautogui not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="previous_media",
        description="Go to previous track in any media player."
    )
    def previous_media(self) -> str:
        """Go to previous track."""
        try:
            import pyautogui
            pyautogui.press("prevtrack")
            return "Went to previous track"
        except ImportError:
            return "pyautogui not installed"
        except Exception as e:
            return "Error: " + str(e)


# ============================================
# Export
# ============================================

MEDIA_PLUGINS = [
    SpotifyPlugin,
    YouTubePlugin,
    MediaControlPlugin,
]
