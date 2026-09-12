"""Study Companion — Main entry point.

Runs the activity detection loop, polling the active window
and classifying it as study or non-study.

Usage:
    python3 -m src.main [--config PATH] [--debug]
"""

import argparse
import signal
import sys
import time

from src.config import load_config
from src.detector import WindowDetector
from src.classifier import ActivityClassifier, ClassificationResult
from src.logger import setup_logger, get_logger, _Colors


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="study-companion",
        description="Study Companion — Detect study activities on your desktop",
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
    return parser.parse_args()


def format_status(result: ClassificationResult, window_title: str, wm_class: str) -> str:
    """Format a colorful status line for console output.

    Args:
        result: Classification result.
        window_title: Active window title.
        wm_class: Active window WM_CLASS.

    Returns:
        Formatted status string with ANSI colors.
    """
    c = _Colors

    if result.is_study:
        status = f"{c.GREEN}{c.BOLD}  ✅ STUDY MODE ON{c.RESET}"
        activity = f"{c.GREEN}{result.activity_name}{c.RESET}"
        source = f"{c.DIM}(via {result.source.value}){c.RESET}"
    else:
        status = f"{c.DIM}  ❌ Not studying{c.RESET}"
        activity = f"{c.DIM}{result.activity_name}{c.RESET}"
        source = ""

    # Truncate long titles
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


def main() -> None:
    """Run the Study Companion detection loop."""
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    log_level = "DEBUG" if args.debug else config.logging.level
    setup_logger(level=log_level, log_file=config.logging.file)
    log = get_logger("main")

    log.info("Study Companion v0.1.0 starting...")
    log.info("Poll interval: %.1fs, Debounce: %d polls",
             config.general.poll_interval, config.general.debounce_count)

    # Initialize components
    detector = WindowDetector()
    if not detector.is_connected:
        log.error("Cannot connect to X11 display. Is X11 running?")
        sys.exit(1)

    classifier = ActivityClassifier(config)

    # Track state
    last_result: ClassificationResult | None = None
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False
        print(f"\n{_Colors.YELLOW}Shutting down...{_Colors.RESET}")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    c = _Colors
    print(f"\n{c.BOLD}{c.CYAN}╔══════════════════════════════════════════════════╗{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}║         📚 Study Companion — Detection Mode      ║{c.RESET}")
    print(f"{c.BOLD}{c.CYAN}╚══════════════════════════════════════════════════╝{c.RESET}")
    print(f"{c.DIM}  Monitoring active window... (Ctrl+C to stop){c.RESET}\n")

    try:
        while running:
            # Detect active window
            window = detector.get_active_window()

            # Classify the activity
            result = classifier.classify(window)

            # Only print when the status changes
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

    except Exception as e:
        log.error("Unexpected error in main loop: %s", e)
        raise
    finally:
        detector.close()
        log.info("Study Companion stopped.")


if __name__ == "__main__":
    main()
