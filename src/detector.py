"""Active window detection via X11.

Uses python-xlib to read the active window's title, WM_CLASS, and PID
from the X11 window manager properties.
"""

from dataclasses import dataclass

from Xlib import X, display, error as xerror
from Xlib.protocol.rq import Event

from src.logger import get_logger

log = get_logger("detector")


@dataclass
class WindowInfo:
    """Information about the currently active window.

    Attributes:
        window_id: X11 window ID.
        title: Window title (_NET_WM_NAME or WM_NAME).
        wm_class: Window class (WM_CLASS instance and class names).
        pid: Process ID of the window's application (may be 0 if unknown).
    """
    window_id: int
    title: str
    wm_class: str
    pid: int

    def __str__(self) -> str:
        return (
            f"WindowInfo(id=0x{self.window_id:x}, "
            f"title={self.title!r}, "
            f"class={self.wm_class!r}, "
            f"pid={self.pid})"
        )


class WindowDetector:
    """Detects the currently active window using X11 properties.

    This class maintains an X11 display connection and provides methods
    to query the active window's metadata.
    """

    def __init__(self) -> None:
        """Initialize the X11 display connection."""
        self._display: display.Display | None = None
        self._root = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to the X11 display server."""
        try:
            self._display = display.Display()
            self._root = self._display.screen().root
            log.info("Connected to X11 display: %s", self._display.get_display_name())
        except Exception as e:
            log.error("Failed to connect to X11 display: %s", e)
            self._display = None
            self._root = None

    @property
    def is_connected(self) -> bool:
        """Check if we have a valid X11 connection."""
        return self._display is not None and self._root is not None

    def _get_property(self, window, prop_name: str) -> str | None:
        """Read a string property from an X11 window.

        Args:
            window: The X11 window object.
            prop_name: The property name (e.g., '_NET_WM_NAME').

        Returns:
            The property value as a string, or None if not found.
        """
        try:
            atom = self._display.intern_atom(prop_name)
            prop = window.get_full_property(atom, 0)
            if prop is None:
                return None
            value = prop.value
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value)
        except Exception:
            return None

    def _get_wm_class(self, window) -> str:
        """Read the WM_CLASS property from an X11 window.

        WM_CLASS typically has two null-separated values:
        instance name and class name. We return the class name
        (second value), which is more useful for identification.

        Args:
            window: The X11 window object.

        Returns:
            The WM_CLASS class name, or empty string if not found.
        """
        try:
            wm_class = window.get_wm_class()
            if wm_class:
                # wm_class returns (instance, class) tuple
                return wm_class[0] if wm_class[0] else ""
            return ""
        except Exception:
            return ""

    def _get_pid(self, window) -> int:
        """Read the _NET_WM_PID property from an X11 window.

        Args:
            window: The X11 window object.

        Returns:
            The PID of the window's process, or 0 if not found.
        """
        try:
            atom = self._display.intern_atom("_NET_WM_PID")
            prop = window.get_full_property(atom, 0)
            if prop is not None and prop.value:
                return int(prop.value[0])
            return 0
        except Exception:
            return 0

    def get_active_window(self) -> WindowInfo | None:
        """Get information about the currently active (focused) window.

        Returns:
            WindowInfo with the active window's metadata,
            or None if detection fails.
        """
        if not self.is_connected:
            log.warning("Not connected to X11, attempting reconnect...")
            self._connect()
            if not self.is_connected:
                return None

        try:
            # Get the active window ID from the root window
            atom = self._display.intern_atom("_NET_ACTIVE_WINDOW")
            prop = self._root.get_full_property(atom, 0)

            if prop is None or not prop.value:
                log.debug("No active window found")
                return None

            window_id = int(prop.value[0])

            if window_id == 0:
                log.debug("Active window ID is 0 (desktop)")
                return None

            # Get the window object
            window = self._display.create_resource_object("window", window_id)

            # Read window properties
            # Prefer _NET_WM_NAME (UTF-8) over WM_NAME (Latin-1)
            title = self._get_property(window, "_NET_WM_NAME")
            if not title:
                title = self._get_property(window, "WM_NAME")
            if not title:
                title = ""

            wm_class = self._get_wm_class(window)
            pid = self._get_pid(window)

            return WindowInfo(
                window_id=window_id,
                title=title,
                wm_class=wm_class,
                pid=pid,
            )

        except xerror.BadWindow:
            log.debug("Active window disappeared (BadWindow error)")
            return None
        except Exception as e:
            log.error("Error detecting active window: %s", e)
            return None

    def close(self) -> None:
        """Close the X11 display connection."""
        if self._display:
            try:
                self._display.close()
            except Exception:
                pass
            self._display = None
            self._root = None
            log.debug("X11 display connection closed")
