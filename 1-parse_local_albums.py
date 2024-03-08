"""
This script is pretty specific to my music library, which is organized like: /Artist - Album/01 - Track.mp3

The goal is to export a CSV of all the albums in my library, so that I can use that to query the Spotify API for album ID's.
"""

#%%
import os
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

local_music_dir = os.environ["LOCAL_MUSIC_PATH"]

#%%
# First: I need to get all the artists and albums in my music library
# I'll just parse the directory names

albums = os.listdir(local_music_dir)
albums_df = pd.DataFrame(albums, columns=["folder"])

albums_df["artist"] = albums_df["folder"].apply(lambda x: x.split("-")[0].strip())
albums_df["album"] = albums_df.apply(lambda x: x["folder"][len(x["artist"]) + 2:].strip(), axis=1)

albums_df

#%%

# Clean up ", The" albums
mask = albums_df["artist"].str.endswith(", The")
albums_df.loc[mask, "artist"] = "The " + albums_df.loc[mask]["artist"].str.replace(", The", "")

albums_df


#%%
# Save "Albums" csv
albums_df.to_csv("data/albums.csv", index=False)
