from fastapi import FastAPI, Request  # FastAPI to build API routes
from spotipy import Spotify, SpotifyOAuth  # Spotipy for Spotify API usage
from dotenv import load_dotenv  # For loading environment variables
import os
load_dotenv()  # Load environment variables from .env file

app = FastAPI()# Initialize FastAPI app

# Set up Spotify authentication manager
auth_manager = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-modify-playback-state,user-read-playback-state"
)

# Create Spotify client using the auth manager
sp = Spotify(auth_manager=auth_manager)

@app.get("/")
def root():
    # Health check endpoint
    return {"msg": "🎧 Spotify AI Agent is up and vibing with The Weeknd!"}

@app.post("/command")
async def handle_command(request: Request):
    # Handle natural language music commands like "play", "pause", "next", etc.
    data = await request.json()
    prompt = data.get("prompt", "").lower().strip()

    if not sp:
        return {"error": "❌ Not authenticated with Spotify."}

    # Play command: searches and plays the requested track
    if prompt.startswith("play"):
        song = prompt.replace("play", "", 1).strip()
        if not song:
            return {"error": "You said play, but didn’t say what. 🎵"}

        results = sp.search(q=song, type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            uri = track["uri"]
            sp.start_playback(uris=[uri])
            return {"response": f"🎶 Now playing: {track['name']} by {track['artists'][0]['name']}"}
        else:
            return {"error": "🔍 Couldn't find that track."}

    # Pause command: pauses current playback
    elif "pause" in prompt:
        sp.pause_playback()
        return {"response": "⏸️ Paused. Chill for a sec."}

    # Resume command: resumes playback
    elif "resume" in prompt or "continue" in prompt:
        sp.start_playback()
        return {"response": "▶️ Resumed. Back to the jam."}

    # Skip to next track
    elif "next" in prompt:
        sp.next_track()
        return {"response": "⏭️ Skipped. Next one might be a banger."}

    # Go back to previous track
    elif "previous" in prompt:
        sp.previous_track()
        return {"response": "⏮️ Back to the last jam."}

    # Increase volume by 10%
    elif "volume up" in prompt:
        current = sp.current_playback()
        if current and current.get("device"):
            new_volume = min(current["device"]["volume_percent"] + 10, 100)
            sp.volume(new_volume)
            return {"response": f"🔊 Volume up to {new_volume}%"}
        return {"error": "Couldn’t change volume."}

    # Decrease volume by 10%
    elif "volume down" in prompt:
        current = sp.current_playback()
        if current and current.get("device"):
            new_volume = max(current["device"]["volume_percent"] - 10, 0)
            sp.volume(new_volume)
            return {"response": f"🔉 Volume down to {new_volume}%"}
        return {"error": "Couldn’t change volume."}

    # Fallback response for unknown commands
    return {"msg": "Command received, but I didn't quite get the vibe."}
