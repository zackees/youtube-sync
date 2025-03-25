

# CMD ["uv", "run", "-m", "youtube_sync.cli.sync_multiple", "config.json"]


import subprocess

import os

PORT = str(os.environ.get("PORT", "80"))

def main() -> None:
    """Main function."""
    proc = subprocess.Popen(["uv", "run", "-m", "http.server", PORT])
    with proc:
        subprocess.run(["uv", "run", "-m", "youtube_sync.cli.sync_multiple", "config.json"])

if __name__ == "__main__":
    main()