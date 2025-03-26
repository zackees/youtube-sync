import subprocess
import os
import shutil

PORT = str(os.environ.get("PORT", "80"))

def main() -> None:
    """Main function."""

    # COPY yt_pot_extractor.py /etc/yt-dlp-plugins/
    os.makedirs("/etc/yt-dlp-plugins/", exist_ok=True)

    shutil.copy("yt_pot_extractor.py", "/etc/yt-dlp-plugins/")
    proc = subprocess.Popen(["uv", "run", "-m", "http.server", PORT], cwd="www")
    with proc:
        subprocess.run(["uv", "run", "-m", "youtube_sync.cli.sync_multiple", "--config", "config.json"])

if __name__ == "__main__":
    main()
