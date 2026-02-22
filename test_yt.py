import yt_dlp
import sys
ydl_opts = {
    "quiet": False,
    "extractor_args": {"youtube": {"player_client": ["android", "ios"]}}
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydi = ydl.extract_info("https://www.youtube.com/watch?v=sCYYgtYK0bY", download=False)
    print("Found formats: ", len(ydi['formats']))
