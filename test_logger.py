import yt_dlp

class MyLogger:
    def debug(self, msg):
        print("DEBUG:", msg)
    def warning(self, msg):
        print("WARNING:", msg)
    def error(self, msg):
        print("ERROR:", msg)
    def info(self, msg):
        print("INFO:", msg)

opts = {
    'logger': MyLogger(),
    'quiet': False
}
with yt_dlp.YoutubeDL(opts) as ydl:
    try:
        ydl.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc", download=False)
    except Exception:
        pass
