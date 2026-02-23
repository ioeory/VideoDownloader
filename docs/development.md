# 🛠️ Development & Build Guide

This guide covers setup, testing, and distribution of VideoDownloader.

## Setup Environment

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/your-username/VideoDownloader.git
    cd VideoDownloader
    pip install -e .
    ```
2.  **External Dependencies**:
    *   **ffmpeg**: Required for merging video and audio tracks.
    *   **Node.js**: Recommended for solving YouTube's signature challenges.

## Testing

The project uses a simple test suite located in the root:
*   `test.py`: Runs basic functional tests on core modules.
*   `test_logger.py`: Verifies the i18n log injection.
*   `test_undo.py`: Tests the rollback/cleanup logic after failed downloads.

To run all tests:
```bash
python test.py
```

## Build Standalone Executables

We use `PyInstaller` to create Windows `.exe` files.

1.  **Prepare**: Ensure you have `pyinstaller` installed.
2.  **Run Build Script**:
    ```bash
    python build_exe.py
    ```
3.  **Output**: The resulting executable will be in the `dist/` directory.

### `.spec` File
For advanced build configurations (adding hidden imports, icons), modify `VideoDownloader.spec`.

## Release Workflow

1.  Update version in `videodownloader/__init__.py`.
2.  Run `python rebuild_i18n.py` to ensure translations are up to date.
3.  Run `build_exe.py`.
4.  Commit and tag in Git.
