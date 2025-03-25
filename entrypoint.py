import subprocess
import os

PORT = str(os.environ.get("PORT", "80"))

def main() -> None:
    """Main function."""
    proc_xfvb = subprocess.Popen(["Xvfb", ":1", "-screen", "0", "1024x768x24"])
    proc = subprocess.Popen(["uv", "run", "-m", "http.server", PORT], cwd="www")
    with proc, proc_xfvb:
        subprocess.run(["uv", "run", "-m", "youtube_sync.cli.sync_multiple", "config.json"])

if __name__ == "__main__":
    main()
