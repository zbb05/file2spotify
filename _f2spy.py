"""
folder_to_spotify.py
Turn a folder of local music files into a real Spotify playlist.

Setup (one time):
  1. pip install spotipy mutagen
  2. Go to https://developer.spotify.com/dashboard -> Create App
     - Redirect URI: http://127.0.0.1:8888/callback
  3. Fill in CLIENT_ID and CLIENT_SECRET below (from the app's settings page)

Run:
  python folder_to_spotify.py "/path/to/your/music/folder" "My Playlist Name"

The first run opens a browser window asking you to log in to Spotify and
authorize the app. After that it's cached locally (.cache file).
"""

import os
import sys
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mutagen import File as MutagenFile

CLIENT_ID = "500861a055c24264a2658ce83c06cee2"
CLIENT_SECRET = "25f982e7aeda45de92664bcf4634a939"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav", ".wma", ".aac"}

# Junk commonly found in downloaded filenames, stripped before searching
FILENAME_JUNK = re.compile(
    r"\(official.*?\)|\[official.*?\]|\(audio\)|\[audio\]|\(lyrics?\)|\[lyrics?\]"
    r"|\(hd\)|\[hd\]|\(hq\)|\[hq\]|official video|official audio|lyric video",
    re.IGNORECASE,
)


def get_track_info(path):
    """Return (artist, title) from tags if available, else best guess from filename."""
    try:
        audio = MutagenFile(path, easy=True)
        if audio and audio.tags:
            artist = (audio.tags.get("artist") or [None])[0]
            title = (audio.tags.get("title") or [None])[0]
            if title:
                return artist, title
    except Exception:
        pass  # fall through to filename parsing

    # Fallback: clean up the filename
    name = os.path.splitext(os.path.basename(path))[0]
    name = FILENAME_JUNK.sub("", name)
    name = re.sub(r"^\d+[\s._-]+", "", name)       # leading track numbers
    name = name.replace("_", " ").strip(" -.")
    if " - " in name:                               # "Artist - Title" pattern
        artist, title = name.split(" - ", 1)
        return artist.strip(), title.strip()
    return None, name


def search_track(sp, artist, title):
    """Search Spotify, trying a precise query first, then a looser one."""
    queries = []
    if artist:
        queries.append(f"track:{title} artist:{artist}")
        queries.append(f"{artist} {title}")
    queries.append(title)

    for q in queries:
        results = sp.search(q=q, type="track", limit=1)
        items = results["tracks"]["items"]
        if items:
            return items[0]
    return None


def find_existing_playlist(sp, user_id, name):
    """Return the user's playlist with this name, or None."""
    offset = 0
    while True:
        page = sp.current_user_playlists(limit=50, offset=offset)
        for pl in page["items"]:
            if pl["owner"]["id"] == user_id and pl["name"].lower() == name.lower():
                return pl
        if page["next"] is None:
            return None
        offset += 50


def get_playlist_track_uris(sp, playlist_id):
    """Return the set of track URIs already in the playlist."""
    uris = set()
    offset = 0
    while True:
        page = sp.playlist_items(
            playlist_id, fields="items(track(uri)),next", limit=100, offset=offset
        )
        for item in page["items"]:
            if item.get("track") and item["track"].get("uri"):
                uris.add(item["track"]["uri"])
        if page["next"] is None:
            return uris
        offset += 100


def main():
    if len(sys.argv) < 2:
        print('Usage: python folder_to_spotify.py "/path/to/music" ["Playlist Name"]')
        sys.exit(1)

    folder = sys.argv[1]
    playlist_name = sys.argv[2] if len(sys.argv) > 2 else "My Local Music"

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="playlist-modify-private playlist-modify-public playlist-read-private",
        )
    )
    user_id = sp.current_user()["id"]

    # Collect audio files (walks subfolders too)
    files = []
    for root, _dirs, names in os.walk(folder):
        for n in sorted(names):
            if os.path.splitext(n)[1].lower() in AUDIO_EXTENSIONS:
                files.append(os.path.join(root, n))

    if not files:
        print(f"No audio files found in {folder}")
        sys.exit(1)

    # Reuse the playlist if it already exists, and note what's already in it
    playlist = find_existing_playlist(sp, user_id, playlist_name)
    already_in_playlist = set()
    if playlist:
        already_in_playlist = get_playlist_track_uris(sp, playlist["id"])
        print(f"Playlist '{playlist['name']}' already exists "
              f"with {len(already_in_playlist)} tracks — will only add new songs.\n")

    print(f"Found {len(files)} audio files. Searching Spotify...\n")

    found_uris, misses = [], []
    seen = set(already_in_playlist)  # skip anything already in the playlist
    skipped = 0
    for path in files:
        artist, title = get_track_info(path)
        track = search_track(sp, artist, title)
        label = f"{artist} - {title}" if artist else title
        if track:
            if track["uri"] in seen:
                skipped += 1
                print(f"  SKIP   {label}  (already in playlist)")
            else:
                seen.add(track["uri"])
                found_uris.append(track["uri"])
                print(f"  FOUND  {label}  ->  {track['artists'][0]['name']} - {track['name']}")
        else:
            misses.append(label)
            print(f"  MISS   {label}")

    if not found_uris:
        if skipped:
            print(f"\nAll matched songs are already in the playlist ({skipped} skipped). Nothing to add.")
        else:
            print("\nNo tracks matched — nothing to add.")
        sys.exit(0)

    if playlist is None:
        playlist = sp.user_playlist_create(
            user_id, playlist_name, public=False,
            description="Imported from local files",
        )

    # Spotify caps additions at 100 tracks per request
    for i in range(0, len(found_uris), 100):
        sp.playlist_add_items(playlist["id"], found_uris[i:i + 100])

    print(f"\nDone! Added {len(found_uris)} new tracks to '{playlist_name}'"
          f" ({skipped} already there, skipped).")
    print(f"Open it here: {playlist['external_urls']['spotify']}")

    if misses:
        print(f"\n{len(misses)} tracks couldn't be matched (add these manually):")
        for m in misses:
            print(f"  - {m}")


if __name__ == "__main__":
    main()