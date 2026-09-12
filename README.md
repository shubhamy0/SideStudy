# Study Companion

Automatically splits your monitor to play passive gameplay videos (Minecraft parkour, Subway Surfers, GTA) on the side whenever you study or code on Linux.

```text
┌───────────────────────────────────────┬──────────────┐
│                                       │              │
│            STUDY CONTENT              │   GAMEPLAY   │
│                                       │              │
│    VS Code / LeetCode / PDFs / etc.   │  Minecraft   │
│                                       │   Parkour    │
│                                       │              │
└───────────────────────────────────────┴──────────────┘
                  ~75%                        ~25%
```

## Why I Built This

I built this because I focus better when there's satisfying, passive visual stimulation playing in my peripheral vision (the short-form split-screen format). Instead of manually opening a video and arranging windows every time I study or code, **Study Companion** runs in the background and does it automatically.

Also, there's actual cognitive science research backing this format: a 2026 study on PubMed ([PMID: 41880123](https://pubmed.ncbi.nlm.nih.gov/41880123/), *Schuetze et al.*) found that split-screen secondary video presentations do **not** impair memory, comprehension, or increase cognitive load. Viewers adapt to the visual input naturally.

---

## Features

- **Auto-Detection:** Detects when you open study sites (LeetCode, Codeforces, arXiv, PDFs) or coding IDEs (VS Code, PyCharm, IntelliJ, Sublime, Neovide).
- **Auto-Tiling & Restore:** Uses `wmctrl` to snap your study window to ~75% screen width and spawns an `mpv` player on the right. When you switch away from study content, your original window layout is instantly restored.
- **System Tray Control:** Runs quietly in the Linux system tray (`AyatanaAppIndicator3`) so you can toggle it on/off, switch gameplay categories on the fly, or toggle YouTube study mode.
- **Lightweight:** Low CPU overhead using native X11 window events and hardware-accelerated `mpv`.

---

## Quick Start

### 1. Install System Dependencies (Linux / X11)

```bash
sudo apt update
sudo apt install -y wmctrl mpv x11-utils python3-gi python3-gi-cairo gir1.2-ayatanaappindicator3-0.1
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python3 -m src.main
```

Useful command-line flags:
* `python3 -m src.main --detect-only` — Test window detection in terminal without playing video
* `python3 -m src.main --play-only` — Launch gameplay player standalone

---

## Adding Your Own Gameplay Videos

Drop your video files (`.mp4`, `.mkv`, `.webm`) into category subdirectories inside `gameplay/`:

```text
gameplay/
├── minecraft/
│   └── parkour.mp4
├── subway/
│   └── subway.mp4
└── gta/
    └── gta.mp4
```

To switch video categories:
- **System Tray:** Right-click the tray icon → **🎮 Gameplay Category** → choose your category.
- **Config File:** Edit `config.yaml` or `config.default.yaml` (`gameplay.category: "minecraft"`).

---

## Configuration

Copy `config.default.yaml` to `config.yaml` to customize:

```bash
cp config.default.yaml config.yaml
```

Key config options:
- `detection.detect_ides`: `true` / `false`
- `study_sites.keywords`: add custom domain keywords
- `youtube.study_mode`: toggle YouTube detection
- `gameplay.width_percent`: side panel width (e.g. `25` for 25% of screen)
- `gameplay.volume`: `0` for muted, `100` for max volume

---

## Science & Reference

> **Schuetze, B. A. et al. (2026).** *Split-screen distraction: the role of extraneous visual demands in learning from video.*  
> **Journal:** *Cognitive Research: Principles and Implications*, 11(1).  
> **Link:** [PubMed PMID: 41880123](https://pubmed.ncbi.nlm.nih.gov/41880123/) | **DOI:** [10.1186/s41235-026-00720-2](https://doi.org/10.1186/s41235-026-00720-2) | **PMCID:** [PMC13018501](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC13018501/)

---

## License

[MIT](LICENSE)
