# ⚙️ Configuration & Advanced Usage

VideoDownloader supports persistent configuration via a YAML file.

## `config.yaml` Reference

Copy `config.example.yaml` to `config.yaml` to enable your custom settings.

```yaml
# 📂 Output Management
output_dir: ./downloads  # Base directory for all downloads
concurrent: 2            # Parallel downloads (Max 3 recommended)

# 🌐 Browser Integration
# Used for automatic cookie extraction.
# Options: chrome, chromium, firefox, edge, brave, safari, opera, vivaldi
browser: chrome

# 🎬 Performance & Quality
quality: best            # Options: best, 4k, 1080p, 720p, 480p, audio

# 🎓 Platform Specifics
deeplearning:
  default_course: ai-for-everyone
  weeks: [1, 2]          # Only download these weeks by default

# 📝 Logging
log_file: download.log   # Detailed logs for troubleshooting
```

## Advanced CLI Tricks

### 1. Playlist Slicing
Use `--playlist-items` to download specific videos from a long list:
```bash
vd download "URL" --playlist-items 1,3,5-10
```

### 2. Manual Cookie Extraction
If automatic browser extraction fails (e.g., in WSL), use a Netscape file:
1.  Use a browser extension to export `cookies.txt`.
2.  Run:
```bash
vd download "URL" --cookies-file path/to/cookies.txt
```

### 3. Debug Mode
Run with `-v` or `--log-level DEBUG` to see the underlying `yt-dlp` commands and network requests.
```bash
vd -v download "URL"
```
