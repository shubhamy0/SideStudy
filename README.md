# 📚 Study Companion

A lightweight desktop productivity app that detects study activities and plays passive gameplay videos alongside your study content — inspired by the split-screen study/gameplay format popular in short-form videos.

```
┌───────────────────────────────────────┬──────────────┐
│                                       │              │
│             STUDY CONTENT             │   GAMEPLAY   │
│                                       │              │
│      YouTube lecture / PDF /          │  Minecraft   │
│      LeetCode / Codeforces / IDE     │   Parkour    │
│                                       │              │
└───────────────────────────────────────┴──────────────┘
                  ~75%                       ~25%
```

## How It Works

1. **Detects** when you're doing study-related activities (browsing LeetCode, coding in VS Code, reading PDFs, etc.)
2. **Automatically arranges** your screen with study content on the left and a passive gameplay video on the right
3. **Stops** when you switch to non-study activities, restoring your layout

## Supported Study Activities

### Browser-Based (Firefox, Chrome, Chromium, Brave, Edge)
- LeetCode
- Codeforces
- PDF documents
- YouTube (with Study Mode toggle)
- *Easily extensible via configuration*

### IDEs
- VS Code / VS Code Insiders
- JetBrains (PyCharm, IntelliJ IDEA, WebStorm, CLion)
- Sublime Text
- Neovide (Neovim GUI)

## Gameplay

Gameplay consists of pre-recorded local video files — no actual games are running. Supported categories include:
- Minecraft parkour
- Subway Surfers
- GTA driving
- Temple Run
- Any satisfying gameplay videos

**You must supply your own legally obtained gameplay videos.** See [Adding Gameplay Videos](#adding-gameplay-videos) below.

## Platform

Currently developed for **Linux** (X11/Cinnamon). Architecture is designed to be extensible to other platforms.

### Requirements

- Python 3.10+
- X11 display server
- `wmctrl` (window management)
- `mpv` (video playback)

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd study-companion

# 2. Install system dependencies
sudo apt install wmctrl mpv xdotool

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Add gameplay videos (see below)

# 5. Run Study Companion
python3 -m src.main
```

## Adding Gameplay Videos

Create a `gameplay/` directory structure:

```
gameplay/
├── minecraft/
│   ├── parkour1.mp4
│   └── parkour2.mp4
├── subway/
│   └── subway1.mp4
└── gta/
    └── gta1.mp4
```

Videos should be:
- MP4, MKV, or WebM format
- Vertical/portrait orientation preferred (for the side panel)
- No copyrighted content in the repository

## Configuration

Copy the default config and customize:

```bash
cp config.default.yaml config.yaml
```

Edit `config.yaml` to:
- Add/remove study websites
- Enable/disable IDE detection
- Set gameplay width (15-40% of screen)
- Toggle YouTube Study Mode
- Choose gameplay category
- Configure volume and autoplay

## Architecture

```
src/
├── main.py          # Entry point, main detection loop
├── detector.py      # X11 active window detection
├── classifier.py    # Study activity classification
├── player.py        # mpv video playback controller
├── arranger.py      # Window arrangement (wmctrl)
├── config.py        # Configuration management
├── tray.py          # System tray integration
└── logger.py        # Logging setup
```

## Development

```bash
# Run in detection-only mode (no video playback)
python3 -m src.main

# Run tests
python3 -m pytest tests/ -v
```

## Known Limitations

- **X11 only** — Wayland support is not yet implemented
- **Active tab only** — detects the currently visible browser tab, not background tabs
- **YouTube classification** — MVP uses a simple toggle; no content-based classification yet
- **IDE detection** — triggers for all coding activity, not specific projects

## License

MIT
