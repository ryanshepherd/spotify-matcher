"""
Goal: Add all songs from the albums that I like to a "My CDs" playlist. This way
I can shuffle my entire song collection.
"""

#%%
import os
import time
from typing import Dict, List
import spotipy
import spotipy.util as util
import pandas as pd

username = os.environ["SPOTIFY_USERNAME"]
scope = "user-library-read, user-library-modify, user-follow-modify, user-follow-read, playlist-read-private,  playlist-modify-public,  playlist-modify-private"

# Get an auth token
token = util.prompt_for_user_token(username, scope)
if token:
    sp = spotipy.Spotify(auth=token)
else:
    print("Can't get token for", username)



#%%
##############################
# Define some functions
##############################

def get_all_saved_albums() -> List[Dict]:
    offset = 0
    CHUNK_SIZE = 50
    existing_follows = []
    while True:
        resp = sp.current_user_saved_albums(limit=CHUNK_SIZE, offset=offset)
        albums = ([{
            "id": item["album"]["id"],
            "name": item["album"]["name"],
            "artist_id": item["album"]["artists"][0]["id"],
            "artist_name": item["album"]["artists"][0]["name"],
        } for item in resp["items"]])
        print(f"Retrieved {len(albums)} albums. Sample: {', '.join([item['name'] for item in albums[0:5]])}")

        existing_follows += albums

        if len(resp["items"]) < CHUNK_SIZE:
            break

        offset += CHUNK_SIZE
        
        time.sleep(.5)

    return existing_follows

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#%%

# Get list of albums that I like
albums = get_all_saved_albums()

#%%
# For each album, add all songs on the album to the "My CDs" playlist

PLAYLIST_NAME = "My CDs"

# Get the playlist ID
playlists = sp.current_user_playlists()
playlist = [playlist for playlist in playlists["items"] if playlist["name"] == PLAYLIST_NAME][0]

#%%
# Get all track IDs across all albums
track_ids = []
for album in albums:
    print(f"Retrieving tracks for {album['name']} by {album['artist_name']}...")
    resp = sp.album_tracks(album["id"])
    track_ids += [item["id"] for item in resp["items"]]

#%%

len(track_ids)

#%%

# If more than 10k tracks, cut off at 10k
if len(track_ids) > 10000:
    print(f"Warning: More than 10k tracks found ({len(track_ids)}). Truncating to 10k.")
    track_ids = track_ids[:10000]

#%%
# Empty out the playlist
sp.user_playlist_replace_tracks(username, playlist["id"], [])

#%%
# Add 100 tracks at a time
for chunk in chunker(track_ids, 100):
    sp.user_playlist_add_tracks(username, playlist["id"], chunk)

print(f"Added {len(track_ids)} tracks from {album['name']} by {album['artist_name']} to {PLAYLIST_NAME}.")
