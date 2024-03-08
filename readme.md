# Spotify Library Helper

This was a simple project to transfer all of my local CDs to Spotify. It matches the Aritist and Album to the most likely Spotify candidate, then automatically follows the artists and likes the albums.

## Configuration
First, you will need to set up a Spotify developer account at [developer.spotify.com](https://developer.spotify.com). Create a new app and indicate that you plan to use the Web API. Once the app is created, you will have access to a Client ID, Client Secret, and Redirect URI.

Copy `.env.example` to `.env` and set the variables as needed.

## Scripts

`1-parse_local_albums.py` - This script parses local folders into an artist / album name CSV. This only works if you have folders named `{artist} - {album}`

`2-match_and_like.py` - Interacts with the Spotify API in a variety of ways. I ran this script manually, once, and then tried to polish it up a bit -- but it is not very well tested overall.

1. Query against spotify to identify the artist id.
2. Follow any artists that were not previously followed.
3. Query Spotify to retrieve all albums for those artists.
4. Fuzzy match the album name to retrieve an ID.
5. Save any albums to Spotify that were not previously saved
