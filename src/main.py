"""Study Companion — Main entry point.

Runs the full Study Companion loop:
  1. Detect the active window
  2. Classify it as study/non-study
  3. If study: arrange windows + start gameplay
  4. If not study: stop gameplay + restore layout

The system tray runs on the GTK main thread, while detection
runs in a background thread.

Usage:
    python3 -m src.main [--config PATH] [--debug] [--detect-only] [--play-only] [--no-tray]
"""

import argparse
import signal
import sys
import threading
import time

from src.config import load_config, Config
from src.detector import WindowDetector
from src.classifier import ActivityClassifier, ClassificationResult
from src.player import GameplayPlayer
from src.arranger import WindowArranger
from src.logger import setup_logger, get_logger, _Colors


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="study-companion",
        description="Study Companion — Detect study activities and play gameplay alongside",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--detect-only", action="store_true",
        help="Only detect study activity, don't arrange windows or play videos",
    )
    parser.add_argument(
        "--play-only", action="store_true",
        help="Only play gameplay video (for testing the player)",
    )
    parser.add_argument(
        "--no-tray", action="store_true",
        help="Run without the system tray icon",
    )
    return parser.parse_args()


def format_status(result: ClassificationResult, window_title: str, wm_class: str) -> str:
    """Format a colorful status line for console output."""
    c = _Colors

    if result.is_study:
        status = f"{c.GREEN}{c.BOLD}  ✅ STUDY MODE ON{c.RESET}"
        activity = f"{c.GREEN}{result.activity_name}{c.RESET}"
        source = f"{c.DIM}(via {result.source.value}){c.RESET}"
    else:
        status = f"{c.DIM}  ❌ Not studying{c.RESET}"
        activity = f"{c.DIM}{result.activity_name}{c.RESET}"
        source = ""

    display_title = window_title[:60] + "..." if len(window_title) > 60 else window_title

    lines = [
        f"\r{c.BOLD}{'━' * 70}{c.RESET}",
        f"  {c.CYAN}Window:{c.RESET}  {display_title}",
        f"  {c.CYAN}Class:{c.RESET}   {wm_class}",
        f"  {c.CYAN}Activity:{c.RESET} {activity} {source}",
        status,
        f"{c.BOLD}{'━' * 70}{c.RESET}",
    ]
    return "\n".join(lines)


def run_play_only(config: Config) -> None:
    """Test mode: just play a gameplay video and wait."""
    log = get_logger("main")
    c = _Colors

    print(f"\n{c.BOLD}{c.MAGENTA}🎮 Play-Only Mode — Testing Gameplay Player{c.RESET}")
    print(f"{c.DIM}  Press Ctrl+C to stop{c.RESET}\n")

    player = GameplayPlayer(config)
    arranger = WindowArranger(config)

    gx, gy, gw, gh = arranger.get_gameplay_geometry()
    print(f"  Gameplay area: {gw}x{gh} at +{gx}+{gy}")

    success = player.start(x=gx, y=gy, width=gw, height=gh)
    if not success:
        log.error("Failed to start gameplay. Check that videos exist in gameplay/ dir.")
        return

    print(f"  {c.GREEN}Playing! Switch to other windows to verify it doesn't steal focus.{c.RESET}\n")

    running = True
    def handle_signal(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running and player.is_playing:
        time.sleep(1)

    player.stop()
    print(f"\n{c.YELLOW}Playback stopped.{c.RESET}")


def run_detect_only(config: Config) -> None:
    """Detection-only mode: just print what's detected."""
    log = get_logger("main")
    c = _Colors

    detector = WindowDetector()
    if not detector.is_connected:
        log.error("Cannot connect to X11 display. Is X11 running?")
        sys.exit(1)

    classifier = ActivityClassifier(config)
    last_result: ClassificationResult | None = None
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False
        print(f"\n{c.YELLOW}Shutting down...{c.RESET}")
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"\n{c.BOLD}{c.CYAN}╔══════════════════════════════════════════════════╗{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}║       📚 Study Companion — Detection Mode        ║{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}╚══════════════════════════════════════════════════╝{c.RESET}")
    print(f"{c.DIM}  Monitoring active window... (Ctrl+C to stop){c.RESET}\n")

    try:
        while running:
            window = detector.get_active_window()
            result = classifier.classify(window)

            changed = (
                last_result is None
                or result.is_study != last_result.is_study
                or result.activity_name != last_result.activity_name
            )
            if changed:
                title = window.title if window else "(none)"
                wm_class = window.wm_class if window else "(none)"
                print(format_status(result, title, wm_class))
                last_result = result

            time.sleep(config.general.poll_interval)
    finally:
        detector.close()
        log.info("Study Companion stopped.")


class StudyCompanionApp:
    """Main application class that ties everything together.

    Runs the detection loop in a background thread and optionally
    manages a system tray on the GTK main thread.
    """

    def __init__(self, config: Config, use_tray: bool = True) -> None:
        self._config = config
        self._use_tray = use_tray
        self._log = get_logger("main")
        self._c = _Colors

        # Components
        self._detector = WindowDetector()
        self._classifier = ActivityClassifier(config)
        self._player = GameplayPlayer(config)
        self._arranger = WindowArranger(config)
        self._tray = None

        # State
        self._running = False
        self._study_active = False
        self._debounce_counter = 0
        self._enabled = config.general.enabled
        self._detection_thread: threading.Thread | None = None

    def _on_toggle_enabled(self, enabled: bool) -> None:
        """Handle enable/disable toggle from tray."""
        self._enabled = enabled
        self._log.info("Study Companion %s", "enabled" if enabled else "disabled")
        if not enabled and self._study_active:
            self._end_study()

    def _on_toggle_youtube(self, youtube_on: bool) -> None:
        """Handle YouTube study mode toggle from tray."""
        self._config.youtube.study_mode = youtube_on
        self._classifier.update_config(self._config)
        self._log.info("YouTube Study Mode: %s", "ON" if youtube_on else "OFF")

    def _on_change_category(self, category: str) -> None:
        """Handle gameplay category change from tray."""
        self._config.gameplay.category = category
        self._player.update_config(self._config)
        self._log.info("Gameplay category: %s", category)
        # Restart player with new category if currently playing
        if self._player.is_playing:
            self._player.stop()
            gx, gy, gw, gh = self._arranger.get_gameplay_geometry()
            self._player.start(category=category, x=gx, y=gy, width=gw, height=gh)

    def _on_quit(self) -> None:
        """Handle quit from tray."""
        self._running = False

    def _start_study(self, window) -> None:
        """Activate study mode: arrange windows and start gameplay."""
        self._study_active = True

        if window and self._config.gameplay.autoplay:
            self._arranger.arrange(window.window_id)
            gx, gy, gw, gh = self._arranger.get_gameplay_geometry()
            self._player.start(x=gx, y=gy, width=gw, height=gh)

        if self._tray:
            self._tray.update_status(True, self._current_activity_name)

    def _end_study(self) -> None:
        """Deactivate study mode: stop gameplay and restore layout."""
        self._study_active = False

        if self._player.is_playing:
            self._player.stop()
        if self._arranger.is_arranged:
            self._arranger.restore()

        if self._tray:
            self._tray.update_status(False, "")

    def _detection_loop(self) -> None:
        """Background thread: poll active window and manage study mode."""
        c = self._c
        last_result: ClassificationResult | None = None
        self._current_activity_name = ""

        self._log.info("Detection loop started")

        while self._running:
            try:
                if not self._enabled:
                    time.sleep(self._config.general.poll_interval)
                    continue

                window = self._detector.get_active_window()

                # Skip if the active window is our gameplay window
                if window and window.title == "StudyCompanion-Gameplay":
                    time.sleep(self._config.general.poll_interval)
                    continue

                result = self._classifier.classify(window)

                # Debounce: require consistent state change
                if result.is_study != self._study_active:
                    self._debounce_counter += 1
                    if self._debounce_counter < self._config.general.debounce_count:
                        time.sleep(self._config.general.poll_interval)
                        continue
                else:
                    self._debounce_counter = 0

                # State change (after debounce)
                changed = result.is_study != self._study_active

                if changed:
                    title = window.title if window else "(none)"
                    wm_class = window.wm_class if window else "(none)"
                    print(format_status(result, title, wm_class))

                    if result.is_study and not self._study_active:
                        self._log.info("Study STARTED: %s", result.activity_name)
                        self._current_activity_name = result.activity_name
                        self._start_study(window)

                    elif not result.is_study and self._study_active:
                        self._log.info("Study ENDED")
                        self._current_activity_name = ""
                        self._end_study()

                    self._debounce_counter = 0

                # Activity change within study mode
                elif (
                    last_result is not None
                    and result.activity_name != last_result.activity_name
                ):
                    title = window.title if window else "(none)"
                    wm_class = window.wm_class if window else "(none)"
                    print(format_status(result, title, wm_class))

                    if result.is_study:
                        self._current_activity_name = result.activity_name
                        if self._tray:
                            self._tray.update_status(True, result.activity_name)

                last_result = result

            except Exception as e:
                self._log.error("Detection loop error: %s", e)

            time.sleep(self._config.general.poll_interval)

        self._log.info("Detection loop stopped")

    def _cleanup(self) -> None:
        """Clean shutdown."""
        if self._player.is_playing:
            self._player.stop()
        if self._arranger.is_arranged:
            self._arranger.restore()
        self._detector.close()
        self._log.info("Study Companion stopped.")

    def run(self) -> None:
        """Run the application."""
        c = self._c

        if not self._detector.is_connected:
            self._log.error("Cannot connect to X11 display.")
            sys.exit(1)

        self._running = True

        print(f"\n{c.BOLD}{c.CYAN}╔══════════════════════════════════════════════════╗{c.RESET}")
        print(f"{c.BOLD}{c.CYAN}║         📚 Study Companion v0.1.0                ║{c.RESET}")
        print(f"{c.BOLD}{c.CYAN}╚══════════════════════════════════════════════════╝{c.RESET}")
        mode = "Full Mode + System Tray" if self._use_tray else "Full Mode (no tray)"
        print(f"{c.DIM}  {mode} — Ctrl+C to stop{c.RESET}\n")

        # Start detection in background thread
        self._detection_thread = threading.Thread(
            target=self._detection_loop,
            daemon=True,
            name="detection-loop",
        )
        self._detection_thread.start()

        if self._use_tray:
            try:
                import gi
                gi.require_version("Gtk", "3.0")
                from gi.repository import Gtk, GLib

                from src.tray import SystemTray

                self._tray = SystemTray(
                    config=self._config,
                    on_toggle_enabled=self._on_toggle_enabled,
                    on_toggle_youtube=self._on_toggle_youtube,
                    on_change_category=self._on_change_category,
                    on_quit=self._on_quit,
                )
                self._tray.run()

                # Handle SIGINT/SIGTERM gracefully with GTK
                def signal_handler(signum, frame):
                    self._running = False
                    self._tray.quit()

                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)

                # Run GTK main loop (blocks until quit)
                Gtk.main()

            except Exception as e:
                self._log.warning("System tray failed: %s. Running without tray.", e)
                self._use_tray = False

        if not self._use_tray:
            # No tray mode — just wait for signal
            def signal_handler(signum, frame):
                self._running = False
                print(f"\n{c.YELLOW}Shutting down...{c.RESET}")

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            while self._running:
                time.sleep(0.5)

        # Cleanup
        self._running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=5)
        self._cleanup()


def main() -> None:
    """Entry point."""
    args = parse_args()

    config = load_config(args.config)

    log_level = "DEBUG" if args.debug else config.logging.level
    setup_logger(level=log_level, log_file=config.logging.file)
    log = get_logger("main")

    log.info("Study Companion v0.1.0 starting...")

    if args.play_only:
        run_play_only(config)
    elif args.detect_only:
        run_detect_only(config)
    else:
        app = StudyCompanionApp(config, use_tray=not args.no_tray)
        app.run()


if __name__ == "__main__":
    main()
