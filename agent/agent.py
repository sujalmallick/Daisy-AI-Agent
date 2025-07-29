import random

def process_prompt(prompt: str, sp):
    """ Converts natural language prompts into Spotify API actions using the Spotipy client.
    understands your vibes and controls playback accordingly.
    """

    prompt = prompt.lower()
    response = []
    commands = [c.strip() for c in prompt.split("and")]

    for cmd in commands:

        if cmd.startswith("play album"):
            album = cmd.replace("play album", "").strip()
            result = sp.search(q=album, type="album", limit=1)
            if result['albums']['items']:
                album_id = result['albums']['items'][0]['id']
                tracks = sp.album_tracks(album_id)['items']
                uris = [t['uri'] for t in tracks]
                sp.start_playback(uris=uris)
                response.append(f"🎶 Playing album: {result['albums']['items'][0]['name']}")
            else:
                response.append("🚫 Album not found.")

        elif "liked songs" in cmd or "my likes" in cmd:
            liked = sp.current_user_saved_tracks(limit=50)
            uris = [item['track']['uri'] for item in liked['items']]
            random.shuffle(uris)
            sp.start_playback(uris=uris)
            response.append("💖 Playing your liked songs.")

        elif "vibe session" in cmd:
            genres = ["pop", "hip-hop", "rock", "lo-fi", "edm", "indie"]
            genre = random.choice(genres)
            recs = sp.recommendations(seed_genres=[genre], limit=20)
            uris = [track['uri'] for track in recs['tracks']]
            sp.start_playback(uris=uris)
            response.append(f"🌈 Starting a '{genre}' vibe session.")

        elif cmd.startswith("play "):
            song = cmd.replace("play", "").strip()
            result = sp.search(q=song, type="track", limit=1)
            if result['tracks']['items']:
                uri = result['tracks']['items'][0]['uri']
                sp.start_playback(uris=[uri])
                response.append(f"🎵 Playing: {result['tracks']['items'][0]['name']}")
            else:
                response.append("🚫 Song not found.")

        elif "pause" in cmd:
            sp.pause_playback()
            response.append("⏸️ Music paused.")

        elif "next" in cmd:
            sp.next_track()
            response.append("⏭️ Skipped to next track.")

        elif "volume up" in cmd or "volume down" in cmd:
            current = sp.current_playback()
            if current and current['device']:
                vol = current['device']['volume_percent']
                if "up" in cmd:
                    new_vol = min(vol + 10, 100)
                else:
                    new_vol = max(vol - 10, 0)
                sp.volume(new_vol)
                response.append(f"🔊 Volume set to {new_vol}%")
            else:
                response.append("⚠️ Can't fetch current volume.")

        else:
            response.append(f"🤔 Didn't understand: '{cmd}'")

    return "\n".join(response)
