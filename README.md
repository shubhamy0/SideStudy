# 📚 Study Companion

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Linux%20(X11)-orange?style=for-the-badge&logo=linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
![Research](https://img.shields.io/badge/Research-PubMed%2041880123-purple?style=for-the-badge&logo=pubmed)

**An intelligent desktop productivity assistant that automatically tiles your workspace and plays passive gameplay visual stimulations (Minecraft Parkour, Subway Surfers, GTA) alongside your study content.**

[Key Features](#-key-features) • [Scientific Basis](#-scientific-basis--cognitive-research) • [Installation](#-quick-start) • [Adding Videos](#-adding--playing-your-custom-videos) • [Configuration](#-configuration)

---

</div>

## 📺 Overview

**Study Companion** brings the popular split-screen short-form video concept directly to your desktop workspace. Built specifically for students, developers, and researchers, the application detects active study or coding sessions and instantly splits your monitor:

```text
┌───────────────────────────────────────────────────┬──────────────────────┐
│                                                   │                      │
│                STUDY WORKSPACE                    │  PASSIVE GAMEPLAY    │
│                     (~75%)                        │        (~25%)        │
│                                                   │                      │
│   • LeetCode / Codeforces                         │  • Minecraft Parkour │
│   • VS Code / PyCharm / IntelliJ                  │  • Subway Surfers    │
│   • Research PDFs & Documentation                 │  • GTA V Driving     │
│   • YouTube Lectures (Study Mode)                 │  • Custom MP4/MKV    │
│                                                   │                      │
└───────────────────────────────────────────────────┴──────────────────────┘
```

When you focus on study tasks, the app smoothly tiles your active window to the left and launches borderless, muted, or customizable audio gameplay on the right. Switching to non-study activities immediately restores your window geometry and pauses video playback.

---

## 🔬 Scientific Basis & Cognitive Research

Recent cognitive science research validates that passive split-screen visual stimuli do **not** impair learning or overload cognitive capacity:

> 📖 **Reference:**  
> **"Split-screen distraction: the role of extraneous visual demands in learning from video."**  
> *Schuetze, B. A. et al.* (2026). *Cognitive Research: Principles and Implications*, 11(1).  
> **PubMed ID:** [41880123](https://pubmed.ncbi.nlm.nih.gov/41880123/) | **DOI:** [10.1186/s41235-026-00720-2](https://doi.org/10.1186/s41235-026-00720-2) | **PMCID:** [PMC13018501](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC13018501/)

### Key Research Takeaways:
* **Adaptation over Distraction:** Preregistered within-person studies demonstrated no strong evidence that simultaneous split-screen video presentation impairs comprehension or memory retention.
* **Cognitive Load Neutral:** Subjective and behavioral measures showed no increase in cognitive load or attentional difficulty when secondary visual streams were present.
* **Stimulus Regulation:** Viewers adapt effectively to extraneous visual inputs, allowing secondary dynamic streams (such as passive gameplay footage) to serve as background stimulation while maintaining focus on primary educational materials.

---

## ✨ Key Features

- 🎯 **Automatic Window Detection:** Monitors active X11 windows in real-time (`_NET_WM_NAME` and `WM_CLASS`) without heavy CPU usage.
- 📐 **Dynamic Window Tiling & Restoration:** Integrates with `wmctrl` to resize study windows to ~75% screen width and restores exact original window geometries upon exiting study mode.
- 🎬 **Seamless mpv Player Integration:** Subprocess controller for `mpv` rendering hardware-accelerated, borderless, non-focused, looping vertical video playback.
- 💻 **Extensive IDE & Browser Support:**
  - **Browsers:** Firefox, Google Chrome, Chromium, Brave, Microsoft Edge.
  - **Study Sites:** LeetCode, Codeforces, Kaggle, arXiv, PDF Viewers, YouTube (with toggle).
  - **IDEs:** VS Code, VS Code Insiders, PyCharm, IntelliJ IDEA, WebStorm, CLion, Sublime Text, Neovide.
- 🎛️ **Native System Tray Integration:** Built with `AyatanaAppIndicator3` / GTK3 for quick toggles, active activity status, category switching, and YouTube mode.

---

## 🚀 Quick Start

### 1. Prerequisites (Linux / X11)

Install native system tools and hardware accelerated media dependencies:

```bash
sudo apt update
sudo apt install -y wmctrl mpv x11-utils python3-gi python3-gi-cairo gir1.2-ayatanaappindicator3-0.1
```

### 2. Installation

Clone the repository and install Python dependencies:

```bash
git clone https://github.com/your-username/study-companion.git
cd study-companion
pip install -r requirements.txt
```

### 3. Running Study Companion

```bash
# Launch full application (Detection + Auto-Tiling + Gameplay Player + Tray)
python3 -m src.main

# CLI Options:
python3 -m src.main --detect-only   # Run in debug detection mode (log activities)
python3 -m src.main --play-only     # Launch gameplay player standalone
```

---

## 🎮 Adding & Playing Your Custom Videos

You can easily supply your own gameplay clips (`.mp4`, `.mkv`, `.webm`, `.mov`):

### Directory Structure

Place video files into category subdirectories inside `gameplay/`:

```text
gameplay/
├── minecraft/
│   ├── parkour_01.mp4
│   └── parkour_02.mp4
├── subway/
│   └── subway_surfers_01.mp4
├── gta/
│   └── gta5_stunt_01.mp4
└── custom_category/
    └── my_cool_video.mp4
```

### How to Select Which Video Plays

1. **Via System Tray:** Right-click the **Study Companion** tray icon → **🎮 Gameplay Category** → select your category (e.g. *Minecraft*, *Subway*, *Gta*, or *Custom_category*).
2. **Via Config File:** Edit `config.yaml` or `config.default.yaml`:
   ```yaml
   gameplay:
     category: "minecraft"  # Matches folder name in gameplay/
     width_percent: 25      # Screen width percentage for gameplay
     volume: 0              # 0 for muted, 1-100 for audio
     loop: true
   ```
> *Note: The player automatically selects the video in the active category folder.*

---

## ⚙️ Configuration Guide

Copy `config.default.yaml` to `config.yaml` to customize your setup:

```bash
cp config.default.yaml config.yaml
```

```yaml
general:
  enabled: true
  check_interval: 1.0     # Detection frequency in seconds

detection:
  match_mode: "contains"
  detect_ides: true       # Enable/disable IDE window classification
  browser_classes:
    - "firefox"
    - "google-chrome"
    - "chromium"
    - "brave-browser"

study_sites:
  keywords:
    - "leetcode"
    - "codeforces"
    - "arxiv"
    - ".pdf"
    - "docs.python.org"

youtube:
  study_mode: false       # Set true to classify YouTube as a study site
  keywords:
    - "youtube"

gameplay:
  directory: "gameplay"
  category: "minecraft"
  width_percent: 25
  volume: 0               # Muted by default
  loop: true
```

---

## 🏗️ Project Architecture

```text
study-companion/
├── config.default.yaml      # Default system configuration
├── requirements.txt         # Python package dependencies
├── src/
│   ├── __main__.py          # CLI entry point module
│   ├── main.py              # Main orchestrator loop
│   ├── detector.py          # X11 Window detector (python-xlib)
│   ├── classifier.py        # Activity classifier engine
│   ├── player.py            # mpv subprocess window controller
│   ├── arranger.py          # Window geometry tiler (wmctrl)
│   ├── tray.py              # AyatanaAppIndicator system tray
│   ├── config.py            # YAML configuration loader
│   └── logger.py            # Colored logging system
├── tests/
│   └── test_classifier.py   # Unit test suite (28 tests)
└── gameplay/                # Local gameplay video directories
```

---

## 🧪 Testing

Run the automated test suite with `pytest`:

```bash
python3 -m pytest tests/ -v
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
