"""Unit tests for the ActivityClassifier."""

import pytest

from src.classifier import ActivityClassifier, ActivitySource, ClassificationResult
from src.config import (
    Config,
    GeneralConfig,
    StudySitesConfig,
    StudySitePattern,
    YouTubeConfig,
    IDEDetectionConfig,
    IDEClass,
    GameplayConfig,
    LoggingConfig,
)
from src.detector import WindowInfo


def _make_config(
    study_sites_enabled: bool = True,
    youtube_study_mode: bool = False,
    ide_enabled: bool = True,
) -> Config:
    """Create a test configuration."""
    return Config(
        general=GeneralConfig(),
        study_sites=StudySitesConfig(
            enabled=study_sites_enabled,
            patterns=[
                StudySitePattern(name="LeetCode", match="leetcode"),
                StudySitePattern(name="Codeforces", match="codeforces"),
                StudySitePattern(name="PDF", match=".pdf"),
                StudySitePattern(name="GeeksforGeeks", match="geeksforgeeks"),
                StudySitePattern(name="HackerRank", match="hackerrank"),
            ],
        ),
        youtube=YouTubeConfig(study_mode=youtube_study_mode),
        ide_detection=IDEDetectionConfig(
            enabled=ide_enabled,
            classes=[
                IDEClass(name="VS Code", wm_class="code"),
                IDEClass(name="VS Code Insiders", wm_class="code-insiders"),
                IDEClass(name="PyCharm", wm_class="jetbrains-pycharm"),
                IDEClass(name="IntelliJ IDEA", wm_class="jetbrains-idea"),
                IDEClass(name="Sublime Text", wm_class="sublime_text"),
            ],
        ),
        gameplay=GameplayConfig(),
        logging=LoggingConfig(),
    )


def _make_window(title: str, wm_class: str, pid: int = 1234) -> WindowInfo:
    """Create a test WindowInfo."""
    return WindowInfo(window_id=0x12345, title=title, wm_class=wm_class, pid=pid)


# ============================================================
# Browser study site detection
# ============================================================

class TestBrowserStudySites:
    """Tests for browser-based study site detection."""

    def test_leetcode_firefox(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Two Sum - LeetCode - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "LeetCode"
        assert result.source == ActivitySource.STUDY_SITE

    def test_leetcode_chrome(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Two Sum - LeetCode - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "LeetCode"
        assert result.source == ActivitySource.STUDY_SITE

    def test_leetcode_brave(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Problems - LeetCode - Brave", "brave-browser")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "LeetCode"

    def test_codeforces_firefox(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Codeforces Round #900 - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "Codeforces"
        assert result.source == ActivitySource.STUDY_SITE

    def test_codeforces_chrome(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Dashboard - Codeforces - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "Codeforces"

    def test_pdf_in_browser(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("lecture_notes.pdf - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "PDF"
        assert result.source == ActivitySource.STUDY_SITE

    def test_geeksforgeeks(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Array Data Structure - GeeksforGeeks - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "GeeksforGeeks"

    def test_hackerrank(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Solve Me First | HackerRank - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "HackerRank"

    def test_case_insensitive(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("LEETCODE problems - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "LeetCode"


# ============================================================
# Non-study browser activity
# ============================================================

class TestNonStudyBrowser:
    """Tests for non-study browser activity."""

    def test_instagram_firefox(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Instagram - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is False
        assert result.source == ActivitySource.NONE

    def test_netflix_chrome(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Netflix - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is False

    def test_reddit(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Reddit - Pair Programming - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is False

    def test_twitter_chrome(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("X / Twitter - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is False


# ============================================================
# YouTube detection
# ============================================================

class TestYouTube:
    """Tests for YouTube study mode."""

    def test_youtube_study_mode_on(self):
        config = _make_config(youtube_study_mode=True)
        classifier = ActivityClassifier(config)
        window = _make_window("Linear Algebra Lecture - YouTube - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "YouTube (Study Mode)"
        assert result.source == ActivitySource.YOUTUBE

    def test_youtube_study_mode_off(self):
        config = _make_config(youtube_study_mode=False)
        classifier = ActivityClassifier(config)
        window = _make_window("Funny Cats - YouTube - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is False

    def test_youtube_chrome_study_mode_on(self):
        config = _make_config(youtube_study_mode=True)
        classifier = ActivityClassifier(config)
        window = _make_window("(1) MIT OpenCourseWare - YouTube - Google Chrome", "google-chrome")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.source == ActivitySource.YOUTUBE


# ============================================================
# IDE detection
# ============================================================

class TestIDEDetection:
    """Tests for IDE detection via WM_CLASS."""

    def test_vscode(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("main.py - study-companion - Visual Studio Code", "code")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "VS Code"
        assert result.source == ActivitySource.IDE

    def test_vscode_insiders(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("test.js - project - Visual Studio Code - Insiders", "code-insiders")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "VS Code Insiders"

    def test_pycharm(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("app.py – MyProject – PyCharm", "jetbrains-pycharm")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "PyCharm"
        assert result.source == ActivitySource.IDE

    def test_intellij(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Main.java – MyApp – IntelliJ IDEA", "jetbrains-idea")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "IntelliJ IDEA"

    def test_sublime_text(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("script.py - Sublime Text", "sublime_text")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "Sublime Text"

    def test_ide_disabled(self):
        config = _make_config(ide_enabled=False)
        classifier = ActivityClassifier(config)
        window = _make_window("main.py - Visual Studio Code", "code")
        result = classifier.classify(window)
        assert result.is_study is False


# ============================================================
# PDF viewers (non-browser)
# ============================================================

class TestPDFViewers:
    """Tests for PDF detection in native viewers."""

    def test_evince_pdf(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("lecture_notes.pdf — Document Viewer", "evince")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "PDF"
        assert result.source == ActivitySource.STUDY_SITE

    def test_okular_pdf(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("textbook.pdf – Okular", "okular")
        result = classifier.classify(window)
        assert result.is_study is True
        assert result.activity_name == "PDF"


# ============================================================
# Non-study applications
# ============================================================

class TestNonStudyApps:
    """Tests for non-study applications."""

    def test_terminal(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("shubham@mint: ~/Desktop", "gnome-terminal-server")
        result = classifier.classify(window)
        assert result.is_study is False

    def test_file_manager(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        window = _make_window("Home", "nemo")
        result = classifier.classify(window)
        assert result.is_study is False

    def test_no_active_window(self):
        config = _make_config()
        classifier = ActivityClassifier(config)
        result = classifier.classify(None)
        assert result.is_study is False
        assert result.activity_name == "No active window"

    def test_study_sites_disabled(self):
        config = _make_config(study_sites_enabled=False)
        classifier = ActivityClassifier(config)
        window = _make_window("LeetCode - Mozilla Firefox", "firefox")
        result = classifier.classify(window)
        assert result.is_study is False
