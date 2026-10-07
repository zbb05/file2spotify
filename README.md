# Spotify Library Sync

A command-line tool that turns a folder of local music files into a Spotify playlist. It reads each file's metadata, finds the matching track on Spotify, and adds it to a playlist on your account. Run it again later and it only adds songs that aren't already there.

I built this to move my local `.m4a` library onto Spotify without searching for hundreds of songs by hand. About 96% of tracks in my library matched automatically.

## Features

- **Reads real metadata.** Uses [mutagen](https://mutagen.readthedocs.io/) to pull artist and title tags from `.m4a`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.wav`, `.wma`, and `.aac` files.
- **Falls back to the filename.** If a file has no tags, the tool cleans up the filename (strips track numbers, underscores, and junk like `(Official Video)` or `[HQ]`) and splits on `Artist - Title`.
- **Tiered search.** Tries a precise `track: artist:` query first, then a looser keyword search, then title only.
- **Safe to re-run.** If the playlist already exists, it loads every track already in it and skips those, so repeat runs never create duplicates. Duplicates inside the folder itself are skipped too.
- **Handles large libraries.** Pages through your playlists and playlist items, and adds tracks in batches of 100 to stay within Spotify's API limit.
- **Clear report.** Prints `FOUND`, `SKIP`, or `MISS` for every file, then lists anything that couldn't be matched so you can add it manually.
- **Walks subfolders**, so an `Artist/Album/Track.m4a` layout works out of the box.

## Requirements

- Python 3.8+
- A Spotify account
- A Spotify developer app (free)

## Setup

1. **Clone the repo and install dependencies**

   ```bash
   git clone https://github.com/<your-username>/spotify-library-sync.git
   cd spotify-library-sync
   pip install spotipy mutagen
   ```

2. **Create a Spotify app**

   Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), click **Create app**, and add this redirect URI:

   ```
   http://127.0.0.1:8888/callback
   ```

3. **Set your credentials** as environment variables (copy them from the app's settings page):

   ```bash
   export SPOTIPY_CLIENT_ID="your-client-id"
   export SPOTIPY_CLIENT_SECRET="your-client-secret"
   ```

## Usage

```bash
python folder_to_spotify.py "/path/to/music/folder" "Playlist Name"
```

The playlist name is optional and defaults to `My Local Music`. New playlists are created as private.

The first run opens a browser window to log in to Spotify and authorize the app. The token is cached locally in a `.cache` file, so later runs skip this step.

### Example output

```
Playlist 'Road Trip' already exists with 212 tracks — will only add new songs.

Found 230 audio files. Searching Spotify...

  FOUND  Artist A - Song One  ->  Artist A - Song One
  SKIP   Artist B - Song Two  (already in playlist)
  MISS   Unknown Demo Track

Done! Added 9 new tracks to 'Road Trip' (212 already there, skipped).
Open it here: https://open.spotify.com/playlist/...

1 tracks couldn't be matched (add these manually):
  - Unknown Demo Track
```

## How it works

1. **Scan.** Walks the folder and collects every file with a supported audio extension.
2. **Extract.** For each file, reads the artist and title tags. If there are none, it parses the filename instead.
3. **Match.** Searches Spotify with progressively looser queries and takes the top result.
4. **De-duplicate.** Looks for an existing playlist you own with the same name (case-insensitive). If one exists, it fetches all of its track URIs into a set, and any match already in that set is skipped.
5. **Write.** Creates the playlist if needed, then adds the new tracks in batches of 100.

## Limitations

- Matching uses Spotify's top search result, so a song with many covers or remixes can occasionally match the wrong version.
- Files with no tags and a messy filename are the most likely to miss.
- Only playlists owned by the logged-in user are checked for duplicates.

## Built with

- [spotipy](https://spotipy.readthedocs.io/) for the Spotify Web API and OAuth
- [mutagen](https://mutagen.readthedocs.io/) for audio metadata
