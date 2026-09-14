# BT YouTube Downloader

A modern desktop application for downloading YouTube videos and audio with a clean CustomTkinter user interface and powered by `yt-dlp`.

## Features

- 🎥 **Video & Audio Downloads**: Download full videos in various resolutions or extract audio directly (MP3/M4A).
- 🎨 **Modern GUI**: Built using `customtkinter` with dark/light mode support and smooth status updates.
- ⚡ **High Performance**: Fast downloads powered by `yt-dlp` and `ffmpeg`.
- 📋 **History & Tracking**: Keeps track of recent downloads.

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) (installed and added to PATH or bundled)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sagive/bt-youtube-downloader.git
   cd bt-youtube-downloader
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python youtube_downloader.py
```

## Building the Executable

To build a standalone executable with PyInstaller:

```bash
pyinstaller "YouTube Downloader.spec"
```
