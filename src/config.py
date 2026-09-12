"""Configuration management for Study Companion.

Loads settings from YAML config files with fallback to defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.logger import get_logger

log = get_logger("config")

# Project root directory (where config files live)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.default.yaml"
USER_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass
class StudySitePattern:
    """A pattern for matching study websites in browser titles."""
    name: str
    match: str


@dataclass
class IDEClass:
    """A WM_CLASS entry for matching IDEs."""
    name: str
    wm_class: str


@dataclass
class StudySitesConfig:
    """Configuration for browser-based study site detection."""
    enabled: bool = True
    patterns: list[StudySitePattern] = field(default_factory=list)


@dataclass
class YouTubeConfig:
    """YouTube-specific configuration."""
    study_mode: bool = False


@dataclass
class IDEDetectionConfig:
    """Configuration for IDE detection."""
    enabled: bool = True
    classes: list[IDEClass] = field(default_factory=list)


@dataclass
class GameplayConfig:
    """Configuration for gameplay video playback."""
    directory: str = "gameplay"
    category: str = "minecraft"
    width_percent: int = 25
    volume: int = 0
    loop: bool = True
    autoplay: bool = True


@dataclass
class GeneralConfig:
    """General application settings."""
    enabled: bool = True
    poll_interval: float = 1.0
    debounce_count: int = 3


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str | None = None


@dataclass
class Config:
    """Top-level application configuration."""
    general: GeneralConfig = field(default_factory=GeneralConfig)
    study_sites: StudySitesConfig = field(default_factory=StudySitesConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    ide_detection: IDEDetectionConfig = field(default_factory=IDEDetectionConfig)
    gameplay: GameplayConfig = field(default_factory=GameplayConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _parse_study_sites(data: dict) -> StudySitesConfig:
    """Parse study_sites section from raw config dict."""
    patterns = [
        StudySitePattern(name=p["name"], match=p["match"])
        for p in data.get("patterns", [])
    ]
    return StudySitesConfig(
        enabled=data.get("enabled", True),
        patterns=patterns,
    )


def _parse_ide_detection(data: dict) -> IDEDetectionConfig:
    """Parse ide_detection section from raw config dict."""
    classes = [
        IDEClass(name=c["name"], wm_class=c["wm_class"])
        for c in data.get("classes", [])
    ]
    return IDEDetectionConfig(
        enabled=data.get("enabled", True),
        classes=classes,
    )


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from YAML files.

    Priority:
      1. Explicit config_path (if provided)
      2. config.yaml (user overrides)
      3. config.default.yaml (defaults)

    Args:
        config_path: Optional explicit path to a config file.

    Returns:
        Parsed Config dataclass.
    """
    # Start with defaults
    raw = {}

    if DEFAULT_CONFIG_PATH.exists():
        log.debug("Loading defaults from %s", DEFAULT_CONFIG_PATH)
        with open(DEFAULT_CONFIG_PATH) as f:
            raw = yaml.safe_load(f) or {}

    # Override with user config
    user_path = Path(config_path) if config_path else USER_CONFIG_PATH
    if user_path.exists():
        log.info("Loading user config from %s", user_path)
        with open(user_path) as f:
            user_raw = yaml.safe_load(f) or {}
        # Shallow merge: user config overrides top-level sections
        for key, value in user_raw.items():
            if isinstance(value, dict) and isinstance(raw.get(key), dict):
                raw[key].update(value)
            else:
                raw[key] = value
    else:
        log.info("No user config found, using defaults")

    # Parse into dataclasses
    general_data = raw.get("general", {})
    youtube_data = raw.get("youtube", {})
    gameplay_data = raw.get("gameplay", {})
    logging_data = raw.get("logging", {})

    config = Config(
        general=GeneralConfig(
            enabled=general_data.get("enabled", True),
            poll_interval=general_data.get("poll_interval", 1.0),
            debounce_count=general_data.get("debounce_count", 3),
        ),
        study_sites=_parse_study_sites(raw.get("study_sites", {})),
        youtube=YouTubeConfig(
            study_mode=youtube_data.get("study_mode", False),
        ),
        ide_detection=_parse_ide_detection(raw.get("ide_detection", {})),
        gameplay=GameplayConfig(
            directory=gameplay_data.get("directory", "gameplay"),
            category=gameplay_data.get("category", "minecraft"),
            width_percent=gameplay_data.get("width_percent", 25),
            volume=gameplay_data.get("volume", 0),
            loop=gameplay_data.get("loop", True),
            autoplay=gameplay_data.get("autoplay", True),
        ),
        logging=LoggingConfig(
            level=logging_data.get("level", "INFO"),
            file=logging_data.get("file"),
        ),
    )

    log.debug("Config loaded: %d study site patterns, %d IDE classes",
              len(config.study_sites.patterns),
              len(config.ide_detection.classes))

    return config
