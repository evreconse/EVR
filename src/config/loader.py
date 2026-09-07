"""
Configuration loader implementations for EVRECONSE.

Supports YAML, .env, Environment Variables, and JSON.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .exceptions import ConfigurationError


class ConfigLoader(ABC):
    """
    Abstract base class for configuration loaders.

    Future implementations (YAML, .env, JSON, Environment Variables)
    will implement this interface. The ConfigurationManager uses this
    interface to load configuration without knowing the source.
    """

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """
        Load configuration from source.

        Returns:
            Raw configuration as dictionary.

        Raises:
            ConfigurationError: If loading fails.
        """
        ...

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get human-readable name of the configuration source.

        Returns:
            Source name (e.g., "YAML file", "Environment variables").
        """
        ...


class YamlConfigLoader(ConfigLoader):
    """
    YAML configuration file loader.

    Loads configuration from a YAML file.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self._file_path}")

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read YAML file: {e}") from e

        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ConfigurationError("YAML root must be a dictionary")

        return data

    def get_source_name(self) -> str:
        return f"YAML file: {self._file_path}"


class JsonConfigLoader(ConfigLoader):
    """
    JSON configuration file loader.

    Loads configuration from a JSON file.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self._file_path}")

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Failed to parse JSON: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read JSON file: {e}") from e

        if not isinstance(data, dict):
            raise ConfigurationError("JSON root must be a dictionary")

        return data

    def get_source_name(self) -> str:
        return f"JSON file: {self._file_path}"


class EnvConfigLoader(ConfigLoader):
    """
    Environment variable configuration loader.

    Loads configuration from environment variables with EVRECONSE_ prefix.
    Supports nested keys using double underscore (__).
    """

    PREFIX = "EVRECONSE_"

    def __init__(self, prefix: str | None = None) -> None:
        self._prefix = prefix or self.PREFIX

    def load(self) -> dict[str, Any]:
        result = {}

        for key, value in os.environ.items():
            if key.startswith(self._prefix):
                # Remove prefix
                config_key = key[len(self._prefix):].lower()

                # Convert double underscore to nested dict
                nested = self._parse_nested(config_key)

                # Convert value to appropriate type
                typed_value = self._convert_value(value)

                # Merge into result
                self._deep_merge(result, nested, typed_value)

        return result

    def _parse_nested(self, key: str) -> dict[str, Any]:
        """Convert key with double underscores to nested dict."""
        parts = key.split("__")
        result = {}
        current = result

        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Last part - will be set by caller
                pass
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Build the full nested structure
        # Actually, we need to return the full path
        current = result
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = None  # Placeholder
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

        return result

    def _deep_merge(self, target: dict[str, Any], source: dict[str, Any], value: Any) -> None:
        """Deep merge source into target, setting the final value."""
        if not source:
            return

        key = next(iter(source))
        rest = source[key]

        if rest is None:
            target[key] = value
        else:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            self._deep_merge(target[key], rest, value)

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]

        # String
        return value

    def get_source_name(self) -> str:
        return f"Environment variables ({self._prefix}*)"


class DotEnvConfigLoader(ConfigLoader):
    """
    .env file configuration loader.

    Loads configuration from a .env file using python-dotenv.
    """

    def __init__(self, file_path: str | Path = ".env") -> None:
        self._file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            return {}

        # Load .env file into environment
        load_dotenv(dotenv_path=self._file_path, override=False)

        # Use EnvConfigLoader to parse
        env_loader = EnvConfigLoader()
        return env_loader.load()

    def get_source_name(self) -> str:
        return f".env file: {self._file_path}"


class MultiSourceConfigLoader(ConfigLoader):
    """
    Multi-source configuration loader.

    Loads from multiple sources in order of priority (highest first):
    1. Environment variables
    2. .env file
    3. YAML/JSON config file
    4. Defaults

    This allows production overrides via ENV while keeping base config in files.
    """

    def __init__(
        self,
        file_path: str | Path | None = None,
        dotenv_path: str | Path = ".env",
        env_prefix: str = "EVRECONSE_",
    ) -> None:
        self._file_path = Path(file_path) if file_path else None
        self._dotenv_path = Path(dotenv_path)
        self._env_prefix = env_prefix

    def load(self) -> dict[str, Any]:
        result = {}

        # 1. Load from config file (lowest priority)
        if self._file_path and self._file_path.exists():
            if self._file_path.suffix in (".yaml", ".yml"):
                loader = YamlConfigLoader(self._file_path)
            elif self._file_path.suffix == ".json":
                loader = JsonConfigLoader(self._file_path)
            else:
                raise ConfigurationError(f"Unsupported config file format: {self._file_path.suffix}")

            file_config = loader.load()
            self._deep_merge(result, file_config)

        # 2. Load from .env file (medium priority)
        if self._dotenv_path.exists():
            dotenv_loader = DotEnvConfigLoader(self._dotenv_path)
            dotenv_config = dotenv_loader.load()
            self._deep_merge(result, dotenv_config)

        # 3. Load from environment variables (highest priority)
        env_loader = EnvConfigLoader(self._env_prefix)
        env_config = env_loader.load()
        self._deep_merge(result, env_config)

        return result

    def _deep_merge(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        """Deep merge source into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def get_source_name(self) -> str:
        sources = []
        if self._file_path and self._file_path.exists():
            sources.append(f"config: {self._file_path}")
        if self._dotenv_path.exists():
            sources.append(f".env: {self._dotenv_path}")
        sources.append(f"env: {self._env_prefix}*")
        return " + ".join(sources)


class StubConfigLoader(ConfigLoader):
    """
    Stub configuration loader for development/testing.

    Returns an AppConfig with defaults.
    This loader will be replaced with real implementations (YAML, .env, etc.)
    without changing ConfigurationManager's public API.
    """

    def load(self) -> dict[str, Any]:
        return {}

    def get_source_name(self) -> str:
        return "stub (defaults)"