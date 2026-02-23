# 🔌 Platform Plugin Guide

VideoDownloader uses a plugin architecture to handle different websites. All plugins inherit from `BasePlugin`.

## Existing Plugins

| Name | Class | Supported Domains | Key Features |
|------|-------|-------------------|--------------|
| `generic_ytdlp` | `GenericYtdlpPlugin` | `*` (Any) | Fallback for any URL; supports playlist ranges. |
| `harvard` | `HarvardPlugin` | `cs50.harvard.edu`, `edx.org` | Downloads MP4, PDFs, and Zip sources. |
| `deeplearning` | `DeepLearningPlugin` | `learn.deeplearning.ai` | Handles auth, session cookies, and week selection. |
| `coursera` | `CourseraPlugin` | `coursera.org` | High-quality stream extraction with subtitles. |
| `kodekloud` | `KodeKloudPlugin` | `learn.kodekloud.com` | Specialized for tech course platforms. |
| `skillsgoogle`| `SkillsGooglePlugin` | `skills.google` | Enterprise training platform support. |

## How to Implement a New Plugin

1.  **Inherit `BasePlugin`**: Create a new file in `videodownloader/plugins/` (e.g., `new_platform.py`).
2.  **Define Metadata**:
    ```python
    class NewPlatformPlugin(BasePlugin):
        name = "new_platform"
        description = "Description of the platform"
        domains = ["newplatform.com", "api.newplatform.com"]
    ```
3.  **Implement `get_download_tasks`**:
    This is the core method. It should return a list of `DownloadTask` objects.
    ```python
    def get_download_tasks(self, url_or_id, output_dir, cookies=None, **kwargs):
        # 1. Parse the URL
        # 2. Extract metadata (titles, direct links)
        # 3. Create DownloadTask objects
        tasks = [
            DownloadTask(url="...", filename=output_dir / "video1.mp4")
        ]
        return tasks
    ```
4.  **Register the Plugin**:
    Import and initialize your plugin in `videodownloader/main.py`.

## Direct Link Extraction vs. yt-dlp
*   **Direct Link**: If you can find the `.mp4` or `.m3u8` link via scraping, use it directly in `DownloadTask`. It's faster.
*   **yt-dlp**: When the URL requires complex extraction (e.g., YouTube), let the engine handle it by passing the URL to `DownloadTask` and setting `use_ytdlp=True`.
