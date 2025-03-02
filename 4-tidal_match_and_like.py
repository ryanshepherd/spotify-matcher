"""
This script takes in a CSV data/albums.csv, that contains my album collection.
It just has the columns artist, album.

The script is meant to be run interactively using a Jupyter kernel.

Here are the steps:
1. Load the CSV into a dataframe.
2. Follow all artists:
    a. Get a distinct list of artists.
    b. Query Tidal to get the best match artist ID for each artist and add the name
    and ID to the dataframe.
    c. User has an opportunity to manually review the results and fix any errors.
    d. Follow all the artists on Tidal (skipping artists that are already followed).
3. Follow all albums:
    a. Query Tidal to get all albums for each artist.
    b. Find a best match on album name and save the ID to the dataframe
    c. Save the dataframe to CSV.
    d. User has an opportunity to manually review the results and fix any errors.
    e. Add all the albums to Tidal favorites (skipping albums that are already saved).
"""

#%%
import os
import time
import difflib
from typing import Dict, List
import tidalapi
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

DELAY = .2

# Initialize Tidal session
session = tidalapi.Session()

# Try to load existing session
if os.path.exists('.tidal_session.txt'):
    with open('.tidal_session.txt', 'r') as f:
        lines = f.readlines()
        if len(lines) >= 4:
            token_type = lines[0].strip()
            access_token = lines[1].strip()
            refresh_token = lines[2].strip()
            from datetime import datetime
            expiry_time = datetime.strptime(lines[3].strip(), "%Y-%m-%d %H:%M:%S.%f").timestamp()

            # Check if session is valid or can be refreshed
            if session.load_oauth_session(token_type, access_token, refresh_token, expiry_time):
                print("Loaded existing Tidal session")
            else:
                print("Existing session expired, need to login again")
                session.login_oauth_simple()

                # Save the new session
                with open('tidal_session.txt', 'w') as f:
                    f.write(f"{session.token_type}\n")
                    f.write(f"{session.access_token}\n")
                    f.write(f"{session.refresh_token}\n")
                    f.write(f"{session.expiry_time}\n")
        else:
            print("Invalid session file, need to login again")
            session.login_oauth_simple()

            # Save the new session
            with open('tidal_session.txt', 'w') as f:
                f.write(f"{session.token_type}\n")
                f.write(f"{session.access_token}\n")
                f.write(f"{session.refresh_token}\n")
                f.write(f"{session.expiry_time}\n")
else:
    print("No existing session found, starting login process...")
    session.login_oauth_simple()

    # Save the session for future use
    with open('tidal_session.txt', 'w') as f:
        f.write(f"{session.token_type}\n")
        f.write(f"{session.access_token}\n")
        f.write(f"{session.refresh_token}\n")
        f.write(f"{session.expiry_time}\n")

if not session.check_login():
    print("Failed to login to Tidal")
    exit(1)
else:
    print(f"Logged in as {session.user.username}")

#%%
##############################
# Define some functions
##############################

# Get all followed artists
def get_all_favorited_artists() -> List[Dict]:
    favorites = session.user.favorites
    artists = favorites.artists()
    return [{"id": artist.id, "name": artist.name} for artist in artists]

def get_all_favorited_albums() -> List[Dict]:
    favorites = session.user.favorites
    albums = favorites.albums()
    return [{
        "id": album.id,
        "name": album.name,
        "artist_id": album.artist.id,
        "artist_name": album.artist.name,
    } for album in albums]

def get_all_albums_for_artists(artists: List[str]):
    artist_albums = []
    for i, artist_id in enumerate(artists):
        print(f"Retrieving albums for artists {i} / {len(artists)}: {artist_id}...", end="")

        try:
            artist = session.artist(artist_id)
            albums = artist.get_albums()

            if len(albums) > 0:
                album_data = [{
                    "tidal_artist_id": artist_id,
                    "tidal_album_id": album.id,
                    "artist_name": artist.name,
                    "album_name": album.name,
                    "tidal_url": f"https://tidal.com/browse/album/{album.id}"
                } for album in albums]

                print(f"{len(albums)} records. Samples: {', '.join([item['album_name'] for item in album_data[0:3]])}")

                artist_albums += album_data
            else:
                print("None found.")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(DELAY)

    return pd.DataFrame(artist_albums)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#%%
###################################
# Get Tidal Artist ID from Artist Name
# (save the top 3 matches)
###################################

# Retrieve just the distinct artist names from our pre-configured CSV
artists = pd.read_csv("data/albums.csv", usecols=["artist"]).drop_duplicates().sort_values("artist").reset_index(drop=True)
artists["artist_id"] = pd.Series(dtype=pd.Int32Dtype())

# TIDAL QUERY: Loop over artist names and query to get matching ID's
for i in range(0, len(artists)):
    artist = artists.iloc[i]["artist"]
    print(f"Retrieving artist {artist}...", end="")

    # TIDAL QUERY: Search by name
    search_result = session.search(artist, models=[tidalapi.artist.Artist])

    matches = search_result["artists"]
    if len(matches) > 0:
        # Default the artist_id to the first match
        print(f"found. First match: {matches[0].name}")
        artists.at[i, "tidal_artist_id"] = matches[0].id

        # Save the other matches (up to 3)
        for j, match in enumerate(matches[1:3]):
            artists.at[i, f"match_{j}_id"] = match.id
            artists.at[i, f"match_{j}_name"] = match.name
    else:
        print("Not found.")

    time.sleep(DELAY)

#%%
###############################
# Manually Review Artist ID's
###############################

# Save
artists.to_csv("data/tidal_artist_matches.csv", index=False)

#%%
# Manually: Review tidal_artist_matches.csv.
# Put the best id in the "artist_id" column.
# Usually, it will already be there. But sometimes it will be the second or third match.
# And sometimes, you need to manually search for the artist and find the ID. See below:

# TIDAL QUERY: As Needed, manually lookup specific artists that we failed to match

search_result = session.search("violents", models=[tidalapi.artist.Artist])
[(artist.name, artist.id) for artist in search_result["artists"]]

#%%
###############################
# Favorite all artists not already favorited
###############################

# Reload Artists CSV
artists = pd.read_csv("data/tidal_artist_matches.csv")
artists["tidal_artist_id"] = artists["tidal_artist_id"].astype(pd.Int32Dtype())

# TIDAL QUERY: Get already-favorited artists
already_favorited = [item["id"] for item in get_all_favorited_artists()]

# Identify which artists are new
new_favorites = list(set(artists["tidal_artist_id"].dropna().unique()) - set(already_favorited))
new_favorites

#%%
# TIDAL ACTION: Favorite those artists
favorites = session.user.favorites
for _, row in artists[artists["artist_id"].isin(new_favorites)].iterrows():
    artist_id = row["tidal_artist_id"]
    try:
        print(f"Favoriting artist {row['artist']} ({artist_id})")
        favorites.add_artist(artist_id)
        time.sleep(DELAY)
    except Exception as e:
        print(f"Error favoriting artist {artist_id}: {e}")

# %%
###########################################
# Get Album ID's
###########################################

# TIDAL QUERY: Get a lookup of all albums by those artists
album_lookup = get_all_albums_for_artists(artists["tidal_artist_id"].dropna())
album_lookup.head()

#%%
# Stash off this album lookup
album_lookup.to_csv("data/tidal_album_matches.csv", index=False)

#%%

# Load up my original albums list
albums = pd.read_csv("data/albums.csv")
artists = (pd
    .read_csv("data/tidal_artist_matches.csv", usecols=["artist", "tidal_artist_id"])
    .set_index("artist")
)
artists["tidal_artist_id"] = artists["tidal_artist_id"].astype(pd.Int32Dtype())

#%%
# Join artist IDs to albums
albums = albums.join(artists, on="artist")

#%%
# Option: Reload
#album_lookup = pd.read_csv("data/tidal_album_matches.csv")

#%%
# Match the album name to the album ID by doing an exact match on artist_id
# and a fuzzy match on album name

lookup = album_lookup[["tidal_artist_id", "name"]].drop_duplicates()

# Find the best matches based on album name
albums["album_name_best_match"] = albums.dropna(subset=["artist_id"]).apply(
    lambda x: (
        difflib.get_close_matches(
            x["album"],
            lookup.loc[lookup["tidal_artist_id"] == x["tidal_artist_id"]]["name"])),
        axis=1)

# Take just the first match
albums["album_name_best_match"] = albums["album_name_best_match"].apply(
    lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None
)

#%%

# Back on the albums lookup, distinct it down so that each artist + album combo
# only appears once (sometimes, the same album appears multiple times cause
# of re-releases, etc.)
album_lookup_distinct_df = album_lookup.groupby(["tidal_artist_id", "name"]).first()

# Join back to the albums lookup to get the Album ID and other details
album_join = albums.join(album_lookup_distinct_df, on=["tidal_artist_id", "album_name_best_match"], how="left")
album_join

# %%
# Save the results
album_join.to_csv("data/albums_join_tidal.csv")

# Manually review the results.
# Double-check the album match is correct, and fill in any missing album_id's

#%%
###########################################
# Add Albums to Tidal Favorites
###########################################

# Reload
albums = pd.read_csv("data/albums_join_tidal.csv")
albums["tidal_album_id"] = albums["tidal_album_id"].astype(pd.Int32Dtype())

# Filter to only albums that I don't already like
album_ids = albums["tidal_album_id"].dropna().unique()
current_albums = get_all_favorited_albums()
new_albums = list(set(album_ids) - set([item["id"] for item in current_albums]))
new_albums

#%%
# TIDAL ACTION: Save all new albums
favorites = session.user.favorites

for _, row in albums[albums["tidal_album_id"].isin(new_albums)].iterrows():
    album_id = row["tidal_album_id"]
    try:
        print(f"Adding album {row['album']} ({album_id}) to favorites")
        favorites.add_album(album_id)
        time.sleep(DELAY)
    except Exception as e:
        print(f"Error favoriting album {album_id}: {e}")
