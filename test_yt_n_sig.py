import yt_dlp

ydl_opts = {
    "quiet": False,
    # 强制不屏蔽 web client，并且使用 phantomjs/JS 引擎或者最新策略
    "extractor_args": {"youtube": {"player_client": ["web"]}}
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info("https://www.youtube.com/watch?v=sCYYgtYK0bY", download=False)
