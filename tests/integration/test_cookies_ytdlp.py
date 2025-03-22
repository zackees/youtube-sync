from youtube_sync import Source
from youtube_sync.ytdlp.ytdlp import YtDlp

yt = YtDlp(source=Source.YOUTUBE)
info = yt.fetch_channel_url("https://www.youtube.com/@supirorguy5086")
print(info)

vidinfo: dict = yt.fetch_video_info("https://www.youtube.com/watch?v=XfELJU1mRMg")
print(vidinfo)

print("done")
