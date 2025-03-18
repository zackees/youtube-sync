import tempfile
from pathlib import Path

from youtube_sync.cookies import Cookies

cookies: Cookies = Cookies.from_browser("https://youtube.com")
print(f"Found {len(cookies)} cookies.")

for cookie in cookies:
    print(cookie)


print(f"Generated cookies.txt:\n{cookies.cookies_txt}")
print("done")


with tempfile.TemporaryDirectory() as temp_dir:
    out: Path = Path(temp_dir) / "cookies.pkl"
    cookies.save(out)
    print(f"Saved cookies to {out}")
    cookies2 = Cookies.load(out)
    print(f"Loaded cookies from {out}")
    print(cookies2)
    print("done")
