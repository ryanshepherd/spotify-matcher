#%%
import os
import time
import difflib
from typing import Dict, List
import spotipy
import spotipy.util as util
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

username = os.environ["SPOTIFY_USERNAME"]
scope = "user-library-read, user-library-modify, user-follow-modify, user-follow-read"

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

# Get all followed artists
def get_all_followed_artists() -> List[Dict]:
    last_id = None
    CHUNK_SIZE = 50
    existing_follows = []
    while True:
        resp = sp.current_user_followed_artists(limit=CHUNK_SIZE, after=last_id)
        artists = ([{"id": item["id"], "name": item["name"]} for item in resp["artists"]["items"]])
        print(f"Retrieved {len(artists)} artists. Sample: {', '.join([item['name'] for item in artists[0:5]])}")

        existing_follows += artists

        if len(resp["artists"]["items"]) < CHUNK_SIZE:
            break

        last_id = artists[-1]["id"]

        time.sleep(.5)

    return existing_follows

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


def get_all_albums_for_artists(artists: List[str]):
    artist_albums = []
    for i, artist_id in enumerate(artists):
        print(f"Retrieving albums for artists {i} / {len(artists)}: {artist_id}...", end="")

        resp = sp.artist_albums(artist_id, album_type="album",limit=50)

        if len(resp["items"]) > 0:
            albums = [{
                    "artist_id": artist_id,
                    "album_id": item["id"],
                    "name": item["name"],
                    "url": item["external_urls"]["spotify"]
                } for item in resp["items"]]

            print(f"{len(albums)} records. Samples: {', '.join([item['name'] for item in albums[0:3]])}")

            artist_albums += albums
        else:
            print("None found.")

        time.sleep(.5)

    return pd.DataFrame(artist_albums)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


#%%
###################################
# Get Spotify Artist ID from Artist Name
# (save the top 3 matches)
###################################

# Retrieve just the distinct artist names from our pre-configured CSV
artists = pd.read_csv("data/albums.csv", usecols=["artist"]).drop_duplicates()

#%%
# SPOTIFY QUERY: Loop over artist names and query to get matching ID's
for i in range(0, len(artists)):
    artist = artists.iloc[i]["artist"]
    print(f"Retrieving artist {artist}...", end="")

    # SPOTIFY QUERY: Search by name
    resp = sp.search(artist, limit=3, type="artist")

    matches = resp["artists"]["items"]
    if len(matches) > 0:

        # Default the artist_id to the first match
        print(f"found. First match: {matches[0]['name']}")
        artists.at[i, "artist_id"] = matches[0]["id"]

        # Save the other matches
        for j, match in enumerate(matches):
            artists.at[i, f"match_{j}_id"] = match["id"]
            artists.at[i, f"match_{j}_name"] = match["name"]
    else:
        print("Not found.")

    time.sleep(.5)

#%%
###############################
# Manually Review Artist ID's
###############################

# Save
artists.to_csv("data/spotify_artist_matches.csv", index=False)

#
# Manually: Review spotify_artist_matches.csv. Fix ID's where necessary.
#

#%%
# SPOTIFY QUERY: As Needed, manually lookup a specific artist
resp = sp.search("owen", limit=5, type="artist")
[(item["name"], item["id"], item["external_urls"]) for item in resp["artists"]["items"]]

#%%
###############################
# Follow all artists not already followed
###############################

# Reload Artists CSV
artists = pd.read_csv("data/spotify_artist_matches.csv")

# SPOTIFY QUERY: Get already-followed artists
already_followed = [item["id"] for item in get_all_followed_artists()]

# Identify which follows are new
new_follows = list(set(artists["artist_id"].dropna().unique()) - set(already_followed))
new_follows

#%%
# SPOTIFY ACTION: Follow those artists
CHUNK_SIZE = 50
for ids in chunker(new_follows, CHUNK_SIZE):
    print(f"Following {len(ids)} artists.")
    sp.user_follow_artists(ids)
    time.sleep(.5)

# %%
###########################################
# Get Album ID's
###########################################

# Reload albums
albums = pd.read_csv("data/albums.csv")
artists = pd.read_csv("data/spotify_artist_matches.csv", usecols=["artist", "artist_id"]).set_index("artist")

#%%

# SPOTIFY QUERY: Get a lookup of all albums by those artists
album_lookup = get_all_albums_for_artists(artists["artist_id"].dropna())
album_lookup.head()

#%%
# Stash off this album lookup
album_lookup.to_csv("data/spotify_album_matches.csv", index=False)

#%%
# Option: Reload
#album_lookup = pd.read_csv("data/spotify_album_matches.csv")

#%%

# Match the album name to the album ID by doing an exact match on artist_id
# and a fuzzy match on album name

lookup = album_lookup[["artist_id", "name"]].drop_duplicates()

# Find the best match based on album name
albums["album_name_best_match"] = albums.dropna(subset=["artist_id"]).apply(
    lambda x: (
        difflib.get_close_matches(
            x["album"],
            lookup.loc[lookup["artist_id"] == x["artist_id"]]["name"])),
        axis=1)

#%%
# Take just the first match (option: instead, you could explode the matches)
albums["album_name_best_match"] = albums["album_name_best_match"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)

#%%
# Join back to the to albums lookup to get the ID and other details.
# Option: You could join back to the non-distinct df, but you'd need to
# manually review the results to clean them up.

# For some reason, we frequently get multiple ID's for the same album.
# Maybe they're different variations, like remastered or something.
# You could manually steward it, but I'm just gonna take the first one.

album_lookup_distinct_df = album_lookup.groupby(["artist_id", "name"]).first()
album_lookup_distinct_df

album_join = albums.join(album_lookup_distinct_df, on=["artist_id", "album_name_best_match"], how="left")
album_join

# %%
# Save the results
album_join.to_csv("data/albums_join.csv")


#%%
###########################################
# Add Albums to Spotify
###########################################

# Reload
albums = pd.read_csv("data/albums.csv")

# Filter to only albums that I don't already like
album_ids = albums["album_id"].dropna().unique()
current_albums = get_all_saved_albums()
new_albums = list(set(album_ids) - set([item["id"] for item in current_albums]))
new_albums

#%%
# SPOTIFY ACTION: Save all new albums

CHUNK_SIZE = 50
for ids in chunker(new_albums, CHUNK_SIZE):
    print(f"Saving {len(ids)} albums.")
    sp.current_user_saved_albums_add(ids)
    time.sleep(.5)
