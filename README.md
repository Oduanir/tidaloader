<h1 align="center">
  <img src="https://raw.githubusercontent.com/RayZ3R0/tidaloader/main/frontend/src/assets/tsunami.svg" width="80" height="80" alt="Tidaloader Logo">
  <br>
  Tidaloader
</h1>

<p align="center">
  <strong>A modern, self-hosted web application for downloading high-quality music from Tidal</strong>
</p>

<p align="center">
  <a href="https://hub.docker.com/repository/docker/rayz3r0/tidaloader/"><img src="https://img.shields.io/badge/docker-package-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Package"></a>
  <a href="https://github.com/RayZ3R0/tidaloader/blob/main/LICENSE"><img src="https://img.shields.io/github/license/RayZ3R0/tidaloader?style=flat-square&color=5D6D7E" alt="License"></a>
  <a href="https://github.com/RayZ3R0/tidaloader/stargazers"><img src="https://img.shields.io/github/stars/RayZ3R0/tidaloader?style=flat-square&color=E67E22" alt="Stars"></a>
  <a href="https://github.com/RayZ3R0/tidaloader/commits/main"><img src="https://img.shields.io/github/last-commit/RayZ3R0/tidaloader?style=flat-square&color=5D6D7E" alt="Last Commit"></a>
  <br>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Preact-673AB7?style=flat-square&logo=preact&logoColor=white" alt="Preact">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#manual-installation">Manual Installation</a>
</p>

---

## Features

### Multi-Format Audio Downloads

| Format | Quality | Details |
|--------|---------|---------|
| FLAC Hi-Res | Up to 24-bit/192kHz | Studio master quality |
| FLAC Lossless | 16-bit/44.1kHz | CD quality |
| Opus | 192kbps VBR | High-efficiency codec |
| MP3 | 256/128 kbps | Universal compatibility |
| AAC | 320/96 kbps | Native Tidal format |

### Comprehensive Search

- **Track Search** — Find individual songs with album art and quality indicators
- **Album Search** — Browse complete albums with track counts and release dates
- **Artist Search** — Explore artist discographies with all albums and EPs
- **Playlist Search** — Discover and download public Tidal playlists
- **Direct URL Support** — Paste Tidal playlist URLs or UUIDs directly in search

### Playlist Integrations

**Spotify Playlists**
- Import any public Spotify playlist via URL
- No 100-track limit — fetches entire playlists using SpotAPI
- Interactive "Fetch → Check → Download" workflow
- Generate `.m3u8` files for Navidrome/Jellyfin/Plex compatibility
- Batch validate and selectively queue tracks

**ListenBrainz Playlists**
- Weekly Jams — Personalized weekly recommendations
- Weekly Exploration — Discover new artists from your listening history
- Year in Review: Discoveries — Your top new finds of the year
- Year in Review: Missed — Popular tracks you might have missed
- Smart Tidal matching with Japanese Romaji title fallback

**Monitored Tidal Playlists**
- Subscribe to any Tidal playlist for automatic syncing
- Set sync frequency: Manual, Daily, Weekly, or Monthly
- Auto-generates `.m3u8` files in your music directory
- Delete downloaded files directly from the UI with safety confirmations

### Local Library Management

- Artist-centric browsing — View your downloaded music organized by artist
- Auto-fetched cover art — Artist pictures loaded from Tidal and cached
- Album/track counts — Quick stats for each artist
- Library scanning — Rescan to detect manual file changes

### Theme Support

Over 20 themes available including Catppuccin (Latte, Frappé, Macchiato, Mocha), Nord, Gruvbox, Dracula, Solarized, Rose Pine, Tokyo Night, One Dark, Everforest, Kanagawa, and more. Quick toggle between light and dark modes with recent themes for fast access.

### Advanced Features

**Rich Metadata Tagging**
- MusicBrainz IDs embedded automatically
- Album artist, track number, release year
- High-quality cover art (up to 1280×1280)
- Organized file structure: `Artist/Album/TrackNumber - Title`

**Lyrics Support**
- Synced lyrics (`.lrc`) via LrcLib
- Plain text lyrics fallback
- Optional FFmpeg-based embedding into audio files

**Beets Integration**
- Optional post-download `beet import` execution
- Custom Tidaloader beets config included

**Queue Management**
- Concurrent downloads (configurable limit)
- Auto-retry on failure
- Persistent queue across restarts
- Real-time progress indicators

### Mobile Responsive

Fully responsive design that works on phones, tablets, and desktops with touch-friendly controls and adaptive layouts.

---

## Screenshots

<table>
  <tr>
    <td align="center">
        <img height="951" alt="image" src="https://github.com/user-attachments/assets/6e628b81-38e9-449d-ab23-0c7a87039acd" />
      <br />
      <b>Spotify Playlist Download</b>
    </td>
    <td align="center">
        <img width="1810" height="1141" alt="image" src="https://github.com/user-attachments/assets/8e554935-dbcb-47d6-8cef-182d8e50d29d" />
      <br />
      <b>Track Search</b>
    </td>
  </tr>
</table>

<details>
  <summary>View Full Page Screenshot of Arist Page</summary>
    <img width="90%" height="2355" alt="image" src="https://github.com/user-attachments/assets/e613c2f9-a3be-4c5c-adf2-e20739cb2548" />
</details>

---

## Quick Start

### Docker (Recommended)

1. **Create a `docker-compose.yml`:**

```yaml
services:
  tidaloader:
    image: ghcr.io/rayz3r0/tidaloader:latest
    container_name: tidaloader
    ports:
      - "8001:8001"
    environment:
      - MUSIC_DIR=/music
      - AUTH_USERNAME=admin
      - AUTH_PASSWORD=changeme
      - MAX_CONCURRENT_DOWNLOADS=3
      - QUEUE_AUTO_PROCESS=true
    volumes:
      - ./music:/music
    restart: unless-stopped
```

2. **Start the container:**
```bash
docker compose up -d
```

3. **Open in browser:** `http://localhost:8001`

---

## Updating

### Docker

To update Tidaloader to the latest version, navigate to the directory containing your `docker-compose.yml` and run:

```bash
docker compose down

# Pull the latest image
docker compose pull

# Recreate the container
docker compose up -d

# (Optional) Clean up old images
docker image prune -f
```

***

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MUSIC_DIR` | Directory for downloaded music inside container | `/music` |
| `AUTH_USERNAME` | Web UI username | `admin` |
| `AUTH_PASSWORD` | Web UI password | `changeme` |
| `MAX_CONCURRENT_DOWNLOADS` | Parallel download limit | `3` |
| `QUEUE_AUTO_PROCESS` | Auto-start queue on boot | `true` |
| `PLAYLISTS_DIR` | Directory for playlist `.m3u8` files | `/music/Playlists` |

### Audio Quality Settings

Configure in the Settings panel:

| Setting | Output Format | Best For |
|---------|---------------|----------|
| Hi-Res FLAC | FLAC 24-bit/192kHz | Audiophile systems |
| FLAC Lossless | FLAC 16-bit/44.1kHz | High-quality archival |
| MP3 256kbps | MP3 | Universal compatibility |
| MP3 128kbps | MP3 | Storage efficiency |
| Opus 192kbps | Opus | Modern players, small size |
| AAC 320kbps | AAC | Mobile devices |
| AAC 96kbps | AAC | Streaming/low bandwidth |

### File Organization Templates

Customize your folder structure:
- `{Artist}/{Album}/{TrackNumber} - {Title}` (Default)
- `{Album}/{TrackNumber} - {Title}`
- `{Artist} - {Title}`
- Custom templates supported

### Optional Features

| Feature | Description |
|---------|-------------|
| Group Compilations | Places "Various Artists" albums in a Compilations folder |
| Beets Integration | Runs `beet import` after each download |
| Embed Lyrics | Uses FFmpeg to embed lyrics into audio files |

---

## Manual Installation

<details>
<summary><strong>Windows</strong></summary>

```powershell
# Clone the repository
git clone https://github.com/RayZ3R0/tidaloader.git
cd tidaloader

# Set up the backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings

# Build the frontend
cd ..\frontend
npm install
npm run build

# Run the server
cd ..\backend
.\start.ps1
```
</details>

<details>
<summary><strong>Linux / macOS</strong></summary>

```bash
# Clone the repository
git clone https://github.com/RayZ3R0/tidaloader.git
cd tidaloader

# Set up the backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings

# Build the frontend
cd ../frontend
npm install
npm run build

# Run the server
cd ../backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```
</details>

<details>
<summary><strong>Android (Termux)</strong></summary>

```bash
# Install Termux from F-Droid (not Play Store)

# Run the setup script
curl -O https://raw.githubusercontent.com/RayZ3R0/tidaloader/main/backend/termux-setup.sh
bash termux-setup.sh

# Start the server
./start-service.sh
```
</details>

---

## Development

| Component | Command | Port |
|-----------|---------|------|
| Backend | `uvicorn api.main:app --reload` | 8001 |
| Frontend | `npm run dev` | 5173 |

---

## Credits

- Inspired by [tidal-ui](https://github.com/uimaxbai/tidal-ui) and [hifi](https://github.com/sachinsenal0x64/hifi)
- Playlist generation powered by [ListenBrainz](https://listenbrainz.org)
- Spotify integration via [SpotAPI](https://github.com/Blastomanie/SpotAPI)
- Lyrics provided by [LrcLib](https://lrclib.net)
- Themes inspired by [Catppuccin](https://github.com/catppuccin/catppuccin)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> [!IMPORTANT]
> **Disclaimer**
>
> This project is intended for educational and personal use only. The developers do not encourage or endorse piracy.
>
> - Users are solely responsible for complying with copyright laws in their jurisdiction.
> - All music rights remain with their respective copyright holders.
> - Users are encouraged to support artists by maintaining a valid Tidal subscription.
> - This tool serves as a interface for personal, non-commercial use.
>
> The Tidaloader Project assumes no responsibility for any misuse or legal violations.
