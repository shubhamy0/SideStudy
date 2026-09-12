"""Window arrangement using wmctrl.

Manages the positioning and resizing of the study window and
gameplay window to create the split-screen layout.
"""

import subprocess
import re
from dataclasses import dataclass

from src.config import Config
from src.logger import get_logger

log = get_logger("arranger")


@dataclass
class WindowGeometry:
    """Saved window geometry for restoration.

    Attributes:
        window_id: X11 window ID (hex string).
        x: X position.
        y: Y position.
        width: Window width.
        height: Window height.
    """
    window_id: str
    x: int
    y: int
    width: int
    height: int

    def __str__(self) -> str:
        return f"Geometry({self.window_id}: {self.width}x{self.height}+{self.x}+{self.y})"


class WindowArranger:
    """Arranges windows for the study/gameplay split-screen layout.

    Uses wmctrl to resize and reposition windows. Saves original
    geometry so layout can be restored when study mode ends.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the window arranger.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._saved_geometry: WindowGeometry | None = None
        self._is_arranged = False

        # Check wmctrl availability
        self._wmctrl_available = self._check_wmctrl()
        if not self._wmctrl_available:
            log.error("wmctrl not found! Install it: sudo apt install wmctrl")

    def _check_wmctrl(self) -> bool:
        """Check if wmctrl is available."""
        try:
            result = subprocess.run(
                ["wmctrl", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0 or "wmctrl" in result.stdout + result.stderr
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _get_screen_geometry(self) -> tuple[int, int]:
        """Get the usable screen area (excluding taskbar/panels).

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
                    parts = line.strip().split()
                    res = parts[0].split("x")
                    return int(res[0]), int(res[1])
        except Exception as e:
            log.warning("Could not detect screen size: %s", e)
        return 1920, 1080

    def _get_desktop_work_area(self) -> tuple[int, int, int, int]:
        """Get the desktop work area (usable space minus panels).

        Uses wmctrl -d to get the work area geometry.

        Returns:
            Tuple of (x, y, width, height) of the work area.
        """
        try:
            result = subprocess.run(
                ["wmctrl", "-d"],
                capture_output=True, text=True, timeout=5,
            )
            # Output looks like: 0  * DG: 1920x1080  VP: 0,0  WA: 0,0 1920x1053  N/A
            for line in result.stdout.splitlines():
                if "*" in line:  # Current desktop
                    # Parse WA: x,y WxH
                    wa_match = re.search(r'WA:\s*(\d+),(\d+)\s+(\d+)x(\d+)', line)
                    if wa_match:
                        x, y, w, h = map(int, wa_match.groups())
                        log.debug("Work area: %dx%d+%d+%d", w, h, x, y)
                        return x, y, w, h
        except Exception as e:
            log.warning("Could not get work area: %s", e)

        screen_w, screen_h = self._get_screen_geometry()
        return 0, 0, screen_w, screen_h

    def _get_window_geometry(self, window_id_hex: str) -> WindowGeometry | None:
        """Get the current geometry of a window.

        Args:
            window_id_hex: Hex window ID (e.g., "0x12345678").

        Returns:
            WindowGeometry or None if detection fails.
        """
        try:
            result = subprocess.run(
                ["wmctrl", "-l", "-G"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 7 and parts[0] == window_id_hex:
                    return WindowGeometry(
                        window_id=parts[0],
                        x=int(parts[2]),
                        y=int(parts[3]),
                        width=int(parts[4]),
                        height=int(parts[5]),
                    )
        except Exception as e:
            log.warning("Could not get window geometry: %s", e)
        return None

    def _move_resize_window(
        self,
        window_id_hex: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bool:
        """Move and resize a window using wmctrl.

        Args:
            window_id_hex: Hex window ID.
            x, y: New position.
            width, height: New size.

        Returns:
            True if successful.
        """
        try:
            # First, remove maximized state so we can resize
            subprocess.run(
                ["wmctrl", "-i", "-r", window_id_hex,
                 "-b", "remove,maximized_vert,maximized_horz"],
                capture_output=True, timeout=5,
            )

            # Move and resize using mvarg: gravity,x,y,width,height
            # gravity 0 = use default
            cmd = [
                "wmctrl", "-i", "-r", window_id_hex,
                "-e", f"0,{x},{y},{width},{height}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                log.error("wmctrl move failed: %s", result.stderr)
                return False

            log.debug("Moved window %s to %dx%d+%d+%d",
                       window_id_hex, width, height, x, y)
            return True

        except Exception as e:
            log.error("Error moving window: %s", e)
            return False

    def arrange(self, study_window_id: int) -> bool:
        """Arrange the study window for split-screen layout.

        Resizes the study window to occupy the left portion of the screen,
        leaving space for the gameplay panel on the right.

        Args:
            study_window_id: X11 window ID of the study window.

        Returns:
            True if arrangement was successful.
        """
        if not self._wmctrl_available:
            log.error("Cannot arrange: wmctrl not available")
            return False

        if self._is_arranged:
            log.debug("Already arranged, skipping")
            return True

        window_id_hex = f"0x{study_window_id:08x}"
        log.info("Arranging study window: %s", window_id_hex)

        # Save current geometry for restoration
        current = self._get_window_geometry(window_id_hex)
        if current:
            self._saved_geometry = current
            log.info("Saved original geometry: %s", current)
        else:
            log.warning("Could not save original geometry for restoration")

        # Calculate split layout
        wa_x, wa_y, wa_w, wa_h = self._get_desktop_work_area()
        gameplay_pct = self._config.gameplay.width_percent
        study_width = int(wa_w * (100 - gameplay_pct) / 100)

        # Position study window on the left
        success = self._move_resize_window(
            window_id_hex,
            x=wa_x,
            y=wa_y,
            width=study_width,
            height=wa_h,
        )

        if success:
            self._is_arranged = True
            log.info("Study window arranged: %dx%d (gameplay space: %dpx)",
                     study_width, wa_h, wa_w - study_width)

        return success

    def get_gameplay_geometry(self) -> tuple[int, int, int, int]:
        """Get the target geometry for the gameplay window.

        Returns:
            Tuple of (x, y, width, height) for the gameplay panel.
        """
        wa_x, wa_y, wa_w, wa_h = self._get_desktop_work_area()
        gameplay_pct = self._config.gameplay.width_percent
        gameplay_width = int(wa_w * gameplay_pct / 100)
        gameplay_x = wa_x + wa_w - gameplay_width

        return gameplay_x, wa_y, gameplay_width, wa_h

    def restore(self) -> bool:
        """Restore the study window to its original geometry.

        Returns:
            True if restoration was successful.
        """
        if not self._is_arranged:
            log.debug("Not arranged, nothing to restore")
            return True

        if self._saved_geometry is None:
            log.warning("No saved geometry to restore")
            self._is_arranged = False
            return False

        log.info("Restoring window to: %s", self._saved_geometry)
        success = self._move_resize_window(
            self._saved_geometry.window_id,
            self._saved_geometry.x,
            self._saved_geometry.y,
            self._saved_geometry.width,
            self._saved_geometry.height,
        )

        self._is_arranged = False
        self._saved_geometry = None

        if success:
            log.info("Window restored to original position")
        else:
            log.warning("Failed to restore window geometry")

        return success

    @property
    def is_arranged(self) -> bool:
        """Whether windows are currently in split-screen arrangement."""
        return self._is_arranged

    def update_config(self, config: Config) -> None:
        """Update configuration.

        Args:
            config: New configuration.
        """
        self._config = config
