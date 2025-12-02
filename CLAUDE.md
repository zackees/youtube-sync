# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

youtube-sync is a Python library for syncing YouTube and other video platform channels to local/remote storage. It downloads videos as MP3 files and maintains a library.json to track processed videos. Supports YouTube, Rumble, and Brighteon platforms with remote storage via rclone.

## Development Commands

### Setup
```bash
# Install dependencies with uv (includes yt-dlp with curl-cffi for Rumble support)
uv venv
uv pip install -r pyproject.toml
uv pip install -e .

# Install playwright browser
uv run playwright install chromium

# Install rclone binaries
uv run rclone-api-install-bins

# Verify curl-cffi installation (required for Rumble downloads)
uv run yt-dlp --list-impersonate-targets
```

### Running the Application
```bash
# Sync single channel
uv run youtube-sync --channel-name "silverguru" --channel-id "@silverguru" --output "./tmp/output"

# Sync multiple channels from config
uv run youtube-sync-all --config config.json

# Run with download limit
uv run youtube-sync-all --config config.json --download-limit 50

# Dry run (scan only, no downloads)
uv run youtube-sync-all --config config.json --dry-run

# Run once without looping
uv run youtube-sync-all --config config.json --once
```

### Testing
```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit/

# Run integration tests only
uv run pytest tests/integration/

# Run specific test file
uv run pytest tests/unit/test_library.py

# Run with verbose output
uv run pytest -v
```

### Docker
```bash
# Build Docker image
docker build -t youtube-sync .

# Run container (requires config.json)
docker run -v $(pwd)/config.json:/app/config.json youtube-sync
```

### Version Management
```bash
# Update version in pyproject.toml before release
# Version format: "1.2.85"
```

## Architecture

### Core Components

**YouTubeSync** (`src/youtube_sync/__init__.py`)
- Main public API class users interact with
- Wraps YouTubeSyncImpl and handles FSPath initialization
- Entry point: Creates sync instance for a channel

**YouTubeSyncImpl** (`src/youtube_sync/sync.py`)
- Implementation layer between YouTubeSync and source-specific sync classes
- Manages library operations: scan, download, fixup
- Delegates to BaseSync implementations

**BaseSync/YtDlpSync** (`src/youtube_sync/sync_impl.py`)
- Abstract base defining sync interface
- YtDlpSync: Generic yt-dlp implementation for YouTube, Rumble, Brighteon
- Source-specific classes: YouTubeSyncImpl, RumbleSyncImpl, BrighteonSyncImpl
- Factory pattern via `create()` in `src/youtube_sync/create.py`

**Library** (`src/youtube_sync/library.py`)
- Manages library.json file tracking known videos
- Handles video metadata, download state, and file operations
- Thread-safe with FileLock for concurrent access
- Key methods: `load()`, `save()`, `merge()`, `find_missing_downloads()`, `download_missing()`

**Config** (`src/youtube_sync/config.py`)
- Parses config.json or ENV_JSON environment variable
- Defines Channel dataclass with name, source, channel_id
- Handles rclone remote storage configuration
- Validates and auto-fixes channel IDs (e.g., adds @ prefix for YouTube)

### Video Sources

Three supported sources (Source enum in `src/youtube_sync/types.py`):
- **YOUTUBE**: Uses yt-dlp with optional bot scanner fallback
- **RUMBLE**: Uses yt-dlp via RumbleSyncImpl with browser impersonation (chrome-120) to bypass anti-bot protection
- **BRIGHTEON**: Uses ytdlp-brighteon plugin

### Storage Abstraction

Uses `virtual-fs` library (FSPath, Vfs) for unified local/remote file operations:
- **RealFS**: Local filesystem operations
- **RemoteFS**: rclone-based remote storage (B2, S3, etc.)
- **Vfs.begin()**: Context manager for storage initialization

Library and videos stored in: `{output}/{channel_name}/{source}/`

### CLI Entry Points

**youtube-sync** (`src/youtube_sync/cli/sync_one.py`)
- Single channel sync
- Args: --channel-name, --channel-id, --output, --limit-scan, --skip-download, --download-limit, --skip-scan

**youtube-sync-all** (`src/youtube_sync/cli/sync_multiple.py`)
- Multi-channel sync with config.json
- Loops hourly by default (use --once to disable)
- Args: --config, --download-limit (default 300), --dry-run, --once

### Key Implementation Details

**Video Scanning**
- yt-dlp used to scan channel URLs and extract video metadata
- Returns list of VidEntry objects with title, URL, date, video_id
- Cookies managed via Cookies class for authenticated access
- Scan results merged into library.json

**Downloading**
- Downloads best audio format, converts to MP3 via ffmpeg
- Filenames: `YYYY-MM-DD {sanitized_title}.mp3`
- Parallel downloads via ThreadPoolExecutor
- Progress tracked in library.json (download_path field)

**yt-dlp Integration**
- Dynamic binary download/update via `src/youtube_sync/ytdlp/update.py`
- YtDlpCmdRunner manages executable path and version
- Plugin support for non-YouTube sources (Brighteon)
- Cookie handling for YouTube authentication bypass
- Browser impersonation via curl-cffi for Rumble (chrome-120) to bypass anti-bot protection

## Configuration Format

config.json structure:
```json
{
  "output": "dst:Bucket/root/path",
  "rclone": {
    "dst": {
      "type": "b2",
      "account": "****",
      "key": "****"
    }
  },
  "channels": [
    {
      "name": "ChannelName",
      "source": "youtube",
      "channel_id": "@channelhandle"
    }
  ]
}
```

- `output`: rclone remote path or local directory
- `rclone`: rclone remote configuration (passed to virtual-fs)
- `channels`: list of channels to sync
- Channel IDs: YouTube requires @ prefix, others use platform-specific IDs

## Docker/Production

**entrypoint.py**: Production entry point
- Copies yt_pot_extractor.py to /etc/yt-dlp-plugins/ for plugin support
- Starts HTTP server on PORT (default 80) in www/ directory
- Runs youtube-sync-all with config.json

**startup.sh**: Docker startup
- Initializes Xvfb virtual display (for headless browser operations)
- Starts fluxbox window manager
- Launches entrypoint.py via uv

**Environment Variables**
- `PORT`: HTTP server port (default 80)
- `YOUTUBE_SYNC_CONFIG_JSON`: JSON config as string (alternative to config.json file)
- `TMPDIR`: Temp directory for downloads (set to /mytemp in Docker)

## Important Notes

- Line length limit: 200 characters (ruff configuration)
- Python 3.10+ required
- yt-dlp with curl-cffi extras required for Rumble support (installed via pyproject.toml)
- Rumble downloads use browser impersonation (--impersonate chrome-120) to bypass anti-bot protection
- yt-dlp updates automatically on first run
- Library.json uses FileLock for thread-safe concurrent access
- Video dates parsed from upload_date, sorted oldest-first for downloads
- Fixup operations clean video filenames to match expected format (YYYY-MM-DD prefix)
