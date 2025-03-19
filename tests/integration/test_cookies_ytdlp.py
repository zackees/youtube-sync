from youtube_sync.ytdlp import YtDlp

# cookies: Cookies = Cookies.from_browser("https://youtube.com")
# print(f"Found {len(cookies)} cookies.")

# for cookie in cookies:
#     print(cookie)


# print(f"Generated cookies.txt:\n{cookies.cookies_txt}")
# print("done")


# with tempfile.TemporaryDirectory() as temp_dir:
#     out: Path = Path(temp_dir) / "cookies.pkl"
#     cookies.save(out)
#     print(f"Saved cookies to {out}")
#     cookies2 = Cookies.load(out)
#     print(f"Loaded cookies from {out}")
#     print(cookies2)
#     print("done")

yt = YtDlp()
info = yt.fetch_channel_url("https://www.youtube.com/@supirorguy5086")
print(info)

vidinfo: dict = yt.fetch_video_info("https://www.youtube.com/watch?v=XfELJU1mRMg")
print(vidinfo)

print("done")
