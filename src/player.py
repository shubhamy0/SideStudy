"""Gameplay video player using mpv.

Manages mpv as a subprocess to play passive gameplay videos
in a borderless, always-on-top window on the right side of the screen.
"""

import os
import signal
import subprocess
import time
from pathlib import Path

from src.config import Config, GameplayConfig, PROJECT_ROOT
from src.logger import get_logger

log = get_logger("player")


class GameplayPlayer:
    """Controls mpv for gameplay video playback.

    Launches mpv as a subprocess with specific window geometry,
    borderless mode, and loop settings. Designed to play passively
    alongside study content without stealing focus.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the gameplay player.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._process: subprocess.Popen | None = None
        self._gameplay_dir = PROJECT_ROOT / config.gameplay.directory
        self._current_video: Path | None = None
        log.info("GameplayPlayer initialized. Video dir: %s", self._gameplay_dir)

    @property
    def is_playing(self) -> bool:
        """Check if mpv is currently running."""
        return self._process is not None and self._process.poll() is None

    def _get_screen_geometry(self) -> tuple[int, int]:
        """Get the screen width and height using xrandr.

        Returns:
            Tuple of (width, height).
        """
        try:
            result = subprocess.run(
                ["xrandr", "--query"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "*" in line:
                    # Parse resolution like "1920x1080     60.05*+"
                    parts = line.strip().split()
                    res = parts[0].split("x")
                    return int(res[0]), int(res[1])
        except Exception as e:
            log.warning("Could not detect screen size: %s. Using 1920x1080", e)

        return 1920, 1080

    def _find_videos(self, category: str | None = None) -> list[Path]:
        """Find video files in the gameplay directory.

        Args:
            category: Subdirectory name (e.g., "minecraft"). If None, uses config.

        Returns:
            List of video file paths.
        """
        cat = category or self._config.gameplay.category

        if not self._gameplay_dir.exists():
            log.warning("Gameplay directory does not exist: %s", self._gameplay_dir)
            return []

        # Look in specific category subdirectory
        cat_dir = self._gameplay_dir / cat
        if cat_dir.is_dir():
            search_dir = cat_dir
        else:
            # Fall back to root gameplay dir
            log.warning("Category '%s' not found, searching all videos", cat)
            search_dir = self._gameplay_dir

        video_extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
        videos = sorted([
            f for f in search_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in video_extensions
        ])

        log.debug("Found %d videos in %s", len(videos), search_dir)
        return videos

    def _build_mpv_args(
        self,
        video_path: Path,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> list[str]:
        """Build the mpv command-line arguments.

        Args:
            video_path: Path to the video file.
            x: X position of the mpv window.
            y: Y position of the mpv window.
            width: Width of the mpv window.
            height: Height of the mpv window.

        Returns:
            List of command-line arguments for mpv.
        """
        args = [
            "mpv",
            str(video_path),
            # Window geometry
            f"--geometry={width}x{height}+{x}+{y}",
            # Borderless window (no decorations)
            "--no-border",
            # Don't steal focus when opening
            "--no-focus-on-open",
            # Keep window on top
            "--ontop",
            # No On-Screen Display (clean playback)
            "--no-osd-bar",
            "--osd-level=0",
            # No terminal output clutter
            "--really-quiet",
            # Video scaling to fit window
            "--keepaspect=no",
            # Window title (for identification)
            "--title=StudyCompanion-Gameplay",
            # Disable input (no keyboard/mouse interaction)
            "--no-input-default-bindings",
            "--input-vo-keyboard=no",
        ]

        # Looping
        if self._config.gameplay.loop:
            args.append("--loop-file=inf")

        # Volume
        vol = self._config.gameplay.volume
        if vol == 0:
            args.append("--mute=yes")
        else:
            args.extend([f"--volume={vol}", "--mute=no"])

        # Hardware acceleration (try auto, fall back to software)
        args.append("--hwdec=auto-safe")

        return args

    def start(
        self,
        category: str | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> bool:
        """Start gameplay video playback.

        Args:
            category: Gameplay category subdirectory. Uses config default if None.
            x: X position for the mpv window. Auto-calculated if None.
            y: Y position for the mpv window. Defaults to 0.
            width: Width of the mpv window. Auto-calculated if None.
            height: Height of the mpv window. Auto-calculated if None.

        Returns:
            True if playback started successfully, False otherwise.
        """
        if self.is_playing:
            log.debug("Already playing, skipping start")
            return True

        # Find videos
        videos = self._find_videos(category)
        if not videos:
            log.error("No gameplay videos found! Add videos to: %s", self._gameplay_dir)
            return False

        # Use first video (playlist support can come later)
        video = videos[0]
        self._current_video = video

        # Calculate window position if not provided
        screen_w, screen_h = self._get_screen_geometry()
        pct = self._config.gameplay.width_percent

        if width is None:
            width = int(screen_w * pct / 100)
        if height is None:
            height = screen_h
        if x is None:
            x = screen_w - width
        if y is None:
            y = 0

        # Build and launch mpv
        args = self._build_mpv_args(video, x, y, width, height)
        log.info("Starting gameplay: %s (%dx%d at +%d+%d)", video.name, width, height, x, y)
        log.debug("mpv args: %s", " ".join(args))

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                # Don't forward signals from parent
                preexec_fn=os.setpgrp,
            )
            # Brief wait to check if mpv started successfully
            time.sleep(0.3)
            if self._process.poll() is not None:
                log.error("mpv exited immediately with code: %d", self._process.returncode)
                self._process = None
                return False

            log.info("Gameplay playing: %s (pid: %d)", video.name, self._process.pid)
            return True

        except FileNotFoundError:
            log.error("mpv not found! Install it: sudo apt install mpv")
            return False
        except Exception as e:
            log.error("Failed to start mpv: %s", e)
            return False

    def stop(self) -> None:
        """Stop gameplay video playback."""
        if not self.is_playing:
            log.debug("Not playing, skipping stop")
            return

        log.info("Stopping gameplay...")
        try:
            # Send SIGTERM for graceful shutdown
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop
                log.warning("mpv didn't stop gracefully, killing...")
                self._process.kill()
                self._process.wait(timeout=2)
        except Exception as e:
            log.error("Error stopping mpv: %s", e)
        finally:
            self._process = None
            self._current_video = None
            log.info("Gameplay stopped")

    def update_config(self, config: Config) -> None:
        """Update configuration (for live reload).

        Args:
            config: New configuration.
        """
        self._config = config
        self._gameplay_dir = PROJECT_ROOT / config.gameplay.directory
