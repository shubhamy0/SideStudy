"""Study Companion — Main entry point.

Runs the full Study Companion loop:
  1. Detect the active window
  2. Classify it as study/non-study
  3. If study: arrange windows + start gameplay
  4. If not study: stop gameplay + restore layout

Usage:
    python3 -m src.main [--config PATH] [--debug] [--detect-only]
"""

import argparse
import signal
import sys
import time

from src.config import load_config
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
        "--config",
        type=str,
        default=None,
        help="Path to config YAML file (default: config.yaml or config.default.yaml)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect study activity, don't arrange windows or play videos",
    )
    parser.add_argument(
        "--play-only",
        action="store_true",
        help="Only play gameplay video (for testing the player)",
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


def run_play_only(config) -> None:
    """Test mode: just play a gameplay video and wait."""
    log = get_logger("main")
    c = _Colors

    print(f"\n{c.BOLD}{c.MAGENTA}🎮 Play-Only Mode — Testing Gameplay Player{c.RESET}")
    print(f"{c.DIM}  Press Ctrl+C to stop{c.RESET}\n")

    player = GameplayPlayer(config)
    arranger = WindowArranger(config)

    # Get gameplay position
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


def run_detect_only(config) -> None:
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

                if result.is_study and (last_result is None or not last_result.is_study):
                    log.info("Study activity STARTED: %s", result.activity_name)
                elif not result.is_study and last_result is not None and last_result.is_study:
                    log.info("Study activity ENDED")

                last_result = result

            time.sleep(config.general.poll_interval)
    finally:
        detector.close()
        log.info("Study Companion stopped.")


def run_full(config) -> None:
    """Full mode: detect → arrange → play → restore."""
    log = get_logger("main")
    c = _Colors

    detector = WindowDetector()
    if not detector.is_connected:
        log.error("Cannot connect to X11 display. Is X11 running?")
        sys.exit(1)

    classifier = ActivityClassifier(config)
    player = GameplayPlayer(config)
    arranger = WindowArranger(config)

    last_result: ClassificationResult | None = None
    study_active = False
    debounce_counter = 0
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False
        print(f"\n{c.YELLOW}Shutting down...{c.RESET}")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"\n{c.BOLD}{c.CYAN}╔══════════════════════════════════════════════════╗{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}║        📚 Study Companion — Full Mode            ║{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}╚══════════════════════════════════════════════════╝{c.RESET}")
    print(f"{c.DIM}  Monitoring & managing windows... (Ctrl+C to stop){c.RESET}\n")

    try:
        while running:
            window = detector.get_active_window()
            result = classifier.classify(window)

            # Debounce: require consistent state for N polls
            if result.is_study != study_active:
                debounce_counter += 1
                if debounce_counter < config.general.debounce_count:
                    time.sleep(config.general.poll_interval)
                    continue
            else:
                debounce_counter = 0

            # State change detected (after debounce)
            changed = result.is_study != study_active

            if changed:
                title = window.title if window else "(none)"
                wm_class = window.wm_class if window else "(none)"
                print(format_status(result, title, wm_class))

                if result.is_study and not study_active:
                    # === STUDY STARTED ===
                    log.info("Study activity STARTED: %s", result.activity_name)
                    study_active = True

                    if window and config.gameplay.autoplay:
                        # Arrange the study window
                        arranger.arrange(window.window_id)

                        # Start gameplay in the right panel
                        gx, gy, gw, gh = arranger.get_gameplay_geometry()
                        player.start(x=gx, y=gy, width=gw, height=gh)

                elif not result.is_study and study_active:
                    # === STUDY ENDED ===
                    log.info("Study activity ENDED")
                    study_active = False

                    # Stop gameplay
                    player.stop()

                    # Restore window layout
                    arranger.restore()

                debounce_counter = 0

            # Also print when activity changes within study mode
            elif (
                last_result is not None
                and result.activity_name != last_result.activity_name
            ):
                title = window.title if window else "(none)"
                wm_class = window.wm_class if window else "(none)"
                print(format_status(result, title, wm_class))

            last_result = result
            time.sleep(config.general.poll_interval)

    except Exception as e:
        log.error("Unexpected error: %s", e)
        raise
    finally:
        # Clean shutdown
        if player.is_playing:
            player.stop()
        if arranger.is_arranged:
            arranger.restore()
        detector.close()
        log.info("Study Companion stopped.")


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
        run_full(config)


if __name__ == "__main__":
    main()
