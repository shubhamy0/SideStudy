"""Study activity classifier.

Classifies the active window as study-related or not, using two methods:
  1. Browser title matching — checks window title against study site patterns
  2. IDE WM_CLASS matching — checks window class against known IDE identifiers
"""

from dataclasses import dataclass
from enum import Enum

from src.config import Config
from src.detector import WindowInfo
from src.logger import get_logger

log = get_logger("classifier")


class ActivitySource(Enum):
    """How the study activity was detected."""
    STUDY_SITE = "study_site"     # Matched a browser study site pattern
    YOUTUBE = "youtube"           # YouTube with study mode enabled
    IDE = "ide"                   # Matched an IDE WM_CLASS
    NONE = "none"                 # Not a study activity


@dataclass
class ClassificationResult:
    """Result of classifying a window's activity.

    Attributes:
        is_study: Whether this window represents a study activity.
        activity_name: Human-readable name of the detected activity (e.g., "LeetCode", "VS Code").
        source: How the activity was detected.
        window_info: The original window info that was classified.
    """
    is_study: bool
    activity_name: str
    source: ActivitySource
    window_info: WindowInfo | None = None

    def __str__(self) -> str:
        if self.is_study:
            return f"✅ STUDY — {self.activity_name} (via {self.source.value})"
        return f"❌ NOT STUDY — {self.activity_name}"


# Known browser WM_CLASS values (instance names)
BROWSER_CLASSES = frozenset({
    "firefox",
    "navigator",        # Firefox sometimes uses this
    "google-chrome",
    "chromium-browser",
    "chromium",
    "brave-browser",
    "microsoft-edge",
    "vivaldi-stable",
    "opera",
})


class ActivityClassifier:
    """Classifies active windows as study or non-study activities.

    Uses configurable patterns for study site detection and
    WM_CLASS matching for IDE detection.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the classifier with configuration.

        Args:
            config: Application configuration containing patterns and settings.
        """
        self._config = config
        log.info(
            "Classifier initialized: %d study patterns, %d IDE classes, "
            "YouTube study mode: %s",
            len(config.study_sites.patterns),
            len(config.ide_detection.classes),
            "ON" if config.youtube.study_mode else "OFF",
        )

    def update_config(self, config: Config) -> None:
        """Update the classifier's configuration (for live reload).

        Args:
            config: New configuration to apply.
        """
        self._config = config

    def _is_browser(self, wm_class: str) -> bool:
        """Check if the window belongs to a known browser.

        Args:
            wm_class: The WM_CLASS value of the window.

        Returns:
            True if the window is a browser.
        """
        return wm_class.lower() in BROWSER_CLASSES

    def _check_study_sites(self, window: WindowInfo) -> ClassificationResult | None:
        """Check if the window title matches any study site patterns.

        This checks browser windows against the configured study site
        patterns (case-insensitive substring match).

        Args:
            window: Window information to classify.

        Returns:
            ClassificationResult if a match is found, None otherwise.
        """
        if not self._config.study_sites.enabled:
            return None

        title_lower = window.title.lower()

        # Check YouTube first (special handling)
        if self._config.youtube.study_mode and "youtube" in title_lower:
            return ClassificationResult(
                is_study=True,
                activity_name="YouTube (Study Mode)",
                source=ActivitySource.YOUTUBE,
                window_info=window,
            )

        # Check study site patterns
        for pattern in self._config.study_sites.patterns:
            if pattern.match.lower() in title_lower:
                return ClassificationResult(
                    is_study=True,
                    activity_name=pattern.name,
                    source=ActivitySource.STUDY_SITE,
                    window_info=window,
                )

        return None

    def _check_ide(self, window: WindowInfo) -> ClassificationResult | None:
        """Check if the window matches a known IDE via WM_CLASS.

        Args:
            window: Window information to classify.

        Returns:
            ClassificationResult if matched, None otherwise.
        """
        if not self._config.ide_detection.enabled:
            return None

        wm_class_lower = window.wm_class.lower()

        for ide in self._config.ide_detection.classes:
            if ide.wm_class.lower() == wm_class_lower:
                return ClassificationResult(
                    is_study=True,
                    activity_name=ide.name,
                    source=ActivitySource.IDE,
                    window_info=window,
                )

        return None

    def _check_pdf_viewer(self, window: WindowInfo) -> ClassificationResult | None:
        """Check if the window is a PDF viewer (non-browser).

        Detects system PDF viewers (Evince, Okular, etc.) by checking
        if .pdf appears in the window title, even for non-browser apps.

        Args:
            window: Window information to classify.

        Returns:
            ClassificationResult if a PDF is detected, None otherwise.
        """
        if not self._config.study_sites.enabled:
            return None

        title_lower = window.title.lower()
        if ".pdf" in title_lower:
            return ClassificationResult(
                is_study=True,
                activity_name="PDF",
                source=ActivitySource.STUDY_SITE,
                window_info=window,
            )

        return None

    def classify(self, window: WindowInfo | None) -> ClassificationResult:
        """Classify a window as study or non-study activity.

        Classification priority:
          1. IDE detection (WM_CLASS match)
          2. Browser study sites (title pattern match)
          3. PDF viewers (title match for non-browser windows)
          4. Default: not a study activity

        Args:
            window: Window information to classify, or None if no window.

        Returns:
            ClassificationResult with the classification decision.
        """
        if window is None:
            return ClassificationResult(
                is_study=False,
                activity_name="No active window",
                source=ActivitySource.NONE,
            )

        # 1. Check IDE first (most specific — exact WM_CLASS match)
        result = self._check_ide(window)
        if result:
            return result

        # 2. Check browser study sites (title matching)
        if self._is_browser(window.wm_class):
            result = self._check_study_sites(window)
            if result:
                return result
            # Browser but not a study site
            return ClassificationResult(
                is_study=False,
                activity_name=f"Browser ({window.title[:50]}...)"
                    if len(window.title) > 50
                    else f"Browser ({window.title})",
                source=ActivitySource.NONE,
                window_info=window,
            )

        # 3. Check PDF viewers (non-browser)
        result = self._check_pdf_viewer(window)
        if result:
            return result

        # 4. Not a study activity
        return ClassificationResult(
            is_study=False,
            activity_name=window.wm_class or window.title[:30] or "Unknown",
            source=ActivitySource.NONE,
            window_info=window,
        )
