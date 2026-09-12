"""System tray integration using AyatanaAppIndicator3.

Provides a system tray icon with:
  - Study mode status indicator
  - Quick enable/disable toggle
  - Gameplay category selection
  - YouTube study mode toggle
  - Settings access
  - Quit option
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import Gtk, GLib, AyatanaAppIndicator3 as AppIndicator

from src.config import Config
from src.logger import get_logger

log = get_logger("tray")


class SystemTray:
    """System tray icon and menu for Study Companion.

    Uses AyatanaAppIndicator3 for native Linux Mint system tray support.
    All GTK operations are dispatched to the main thread via GLib.idle_add.
    """

    def __init__(
        self,
        config: Config,
        on_toggle_enabled: callable = None,
        on_toggle_youtube: callable = None,
        on_change_category: callable = None,
        on_open_settings: callable = None,
        on_quit: callable = None,
    ) -> None:
        """Initialize the system tray.

        Args:
            config: Application configuration.
            on_toggle_enabled: Callback when enabled/disabled is toggled.
            on_toggle_youtube: Callback when YouTube study mode is toggled.
            on_change_category: Callback when gameplay category changes. Receives category name.
            on_open_settings: Callback to open settings window.
            on_quit: Callback to quit the application.
        """
        self._config = config
        self._on_toggle_enabled = on_toggle_enabled
        self._on_toggle_youtube = on_toggle_youtube
        self._on_change_category = on_change_category
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit

        self._indicator: AppIndicator.Indicator | None = None
        self._enabled_item: Gtk.CheckMenuItem | None = None
        self._youtube_item: Gtk.CheckMenuItem | None = None
        self._status_item: Gtk.MenuItem | None = None
        self._category_items: dict[str, Gtk.RadioMenuItem] = {}

        self._is_studying = False
        self._current_activity = "Idle"
        self._enabled = config.general.enabled

    def _create_indicator(self) -> AppIndicator.Indicator:
        """Create the AppIndicator with icon."""
        indicator = AppIndicator.Indicator.new(
            "study-companion",
            "applications-education",  # Use system icon
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        indicator.set_title("Study Companion")
        return indicator

    def _build_menu(self) -> Gtk.Menu:
        """Build the system tray context menu."""
        menu = Gtk.Menu()

        # ── Status header ──
        self._status_item = Gtk.MenuItem(label="📚 Study Companion — Idle")
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Enable/Disable toggle ──
        self._enabled_item = Gtk.CheckMenuItem(label="Enabled")
        self._enabled_item.set_active(self._enabled)
        self._enabled_item.connect("toggled", self._on_enabled_toggled)
        menu.append(self._enabled_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── YouTube Study Mode ──
        self._youtube_item = Gtk.CheckMenuItem(label="YouTube Study Mode")
        self._youtube_item.set_active(self._config.youtube.study_mode)
        self._youtube_item.connect("toggled", self._on_youtube_toggled)
        menu.append(self._youtube_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Gameplay Category ──
        category_label = Gtk.MenuItem(label="🎮 Gameplay Category")
        category_label.set_sensitive(False)
        menu.append(category_label)

        categories = self._get_available_categories()
        group = []
        for cat in categories:
            if group:
                item = Gtk.RadioMenuItem.new_with_label(group, cat.capitalize())
            else:
                item = Gtk.RadioMenuItem.new_with_label([], cat.capitalize())
            group = item.get_group()

            if cat == self._config.gameplay.category:
                item.set_active(True)

            item.connect("toggled", self._on_category_changed, cat)
            self._category_items[cat] = item
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Quit ──
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit_clicked)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _get_available_categories(self) -> list[str]:
        """Get available gameplay categories from the filesystem."""
        from src.config import PROJECT_ROOT

        gameplay_dir = PROJECT_ROOT / self._config.gameplay.directory
        if not gameplay_dir.exists():
            return ["minecraft"]

        categories = sorted([
            d.name for d in gameplay_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

        return categories if categories else ["minecraft"]

    # ── Callbacks ──

    def _on_enabled_toggled(self, widget: Gtk.CheckMenuItem) -> None:
        self._enabled = widget.get_active()
        log.info("Study Companion %s", "enabled" if self._enabled else "disabled")
        if self._on_toggle_enabled:
            self._on_toggle_enabled(self._enabled)
        self._update_status_display()

    def _on_youtube_toggled(self, widget: Gtk.CheckMenuItem) -> None:
        youtube_on = widget.get_active()
        log.info("YouTube Study Mode: %s", "ON" if youtube_on else "OFF")
        if self._on_toggle_youtube:
            self._on_toggle_youtube(youtube_on)

    def _on_category_changed(self, widget: Gtk.RadioMenuItem, category: str) -> None:
        if widget.get_active():
            log.info("Gameplay category changed to: %s", category)
            if self._on_change_category:
                self._on_change_category(category)

    def _on_quit_clicked(self, widget: Gtk.MenuItem) -> None:
        log.info("Quit requested from tray")
        if self._on_quit:
            self._on_quit()
        Gtk.main_quit()

    # ── Public API ──

    def update_status(self, is_studying: bool, activity_name: str = "") -> None:
        """Update the tray status display (thread-safe).

        Args:
            is_studying: Whether study mode is currently active.
            activity_name: Name of the current activity.
        """
        self._is_studying = is_studying
        self._current_activity = activity_name
        GLib.idle_add(self._update_status_display)

    def _update_status_display(self) -> None:
        """Update the status label in the menu (must run on GTK thread)."""
        if self._status_item is None:
            return

        if not self._enabled:
            label = "📚 Study Companion — Disabled"
            icon = "dialog-error"
        elif self._is_studying:
            label = f"✅ Studying — {self._current_activity}"
            icon = "applications-education"
        else:
            label = "📚 Study Companion — Idle"
            icon = "applications-education"

        self._status_item.set_label(label)
        if self._indicator:
            self._indicator.set_icon_full(icon, "Study Companion")

    @property
    def is_enabled(self) -> bool:
        """Whether Study Companion is currently enabled."""
        return self._enabled

    def run(self) -> None:
        """Start the system tray (blocks on GTK main loop).

        This should be called from the main thread.
        """
        log.info("Starting system tray...")
        self._indicator = self._create_indicator()
        menu = self._build_menu()
        self._indicator.set_menu(menu)
        self._update_status_display()
        log.info("System tray running")

    def quit(self) -> None:
        """Quit the GTK main loop (thread-safe)."""
        GLib.idle_add(Gtk.main_quit)
