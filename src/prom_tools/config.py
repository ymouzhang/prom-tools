"""
Configuration management for prom-tools.
"""

import os
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from .exceptions import ConfigurationError


@dataclass
class PrometheusConfig:
    """Prometheus configuration."""
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit: Optional[int] = None
    verify_ssl: bool = True


@dataclass
class GrafanaConfig:
    """Grafana configuration."""
    url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    org_id: Optional[int] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit: Optional[int] = None
    verify_ssl: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class Config:
    """Main configuration class."""
    prometheus: Optional[PrometheusConfig] = None
    grafana: Optional[GrafanaConfig] = None
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        config = cls()

        if "prometheus" in data:
            config.prometheus = PrometheusConfig(**data["prometheus"])

        if "grafana" in data:
            config.grafana = GrafanaConfig(**data["grafana"])

        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])

        return config

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "Config":
        """Load config from file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise ConfigurationError(f"Config file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == ".json":
                    import json
                    data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported config file format: {file_path.suffix}")

                return cls.from_dict(data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {file_path}: {str(e)}")

    @classmethod
    def from_env(cls, prefix: str = "PROM_TOOLS") -> "Config":
        """Load config from environment variables."""
        config = cls()

        # Prometheus config
        prometheus_url = os.getenv(f"{prefix}_PROMETHEUS_URL")
        if prometheus_url:
            config.prometheus = PrometheusConfig(
                url=prometheus_url,
                username=os.getenv(f"{prefix}_PROMETHEUS_USERNAME"),
                password=os.getenv(f"{prefix}_PROMETHEUS_PASSWORD"),
                token=os.getenv(f"{prefix}_PROMETHEUS_TOKEN"),
                timeout=int(os.getenv(f"{prefix}_PROMETHEUS_TIMEOUT", "30")),
                max_retries=int(os.getenv(f"{prefix}_PROMETHEUS_MAX_RETRIES", "3")),
                rate_limit=int(os.getenv(f"{prefix}_PROMETHEUS_RATE_LIMIT") or 0) or None,
                verify_ssl=os.getenv(f"{prefix}_PROMETHEUS_VERIFY_SSL", "true").lower() == "true",
            )

        # Grafana config
        grafana_url = os.getenv(f"{prefix}_GRAFANA_URL")
        if grafana_url:
            config.grafana = GrafanaConfig(
                url=grafana_url,
                api_key=os.getenv(f"{prefix}_GRAFANA_API_KEY"),
                username=os.getenv(f"{prefix}_GRAFANA_USERNAME"),
                password=os.getenv(f"{prefix}_GRAFANA_PASSWORD"),
                org_id=int(os.getenv(f"{prefix}_GRAFANA_ORG_ID") or 0) or None,
                timeout=int(os.getenv(f"{prefix}_GRAFANA_TIMEOUT", "30")),
                max_retries=int(os.getenv(f"{prefix}_GRAFANA_MAX_RETRIES", "3")),
                rate_limit=int(os.getenv(f"{prefix}_GRAFANA_RATE_LIMIT") or 0) or None,
                verify_ssl=os.getenv(f"{prefix}_GRAFANA_VERIFY_SSL", "true").lower() == "true",
            )

        # Logging config
        config.logging = LoggingConfig(
            level=os.getenv(f"{prefix}_LOG_LEVEL", "INFO"),
            format=os.getenv(f"{prefix}_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=os.getenv(f"{prefix}_LOG_FILE"),
        )

        return config

    def validate(self) -> None:
        """Validate configuration."""
        if self.prometheus:
            if not self.prometheus.url:
                raise ConfigurationError("Prometheus URL is required")

            if not (self.prometheus.token or (self.prometheus.username and self.prometheus.password)):
                raise ConfigurationError("Prometheus authentication is required (token or username/password)")

        if self.grafana:
            if not self.grafana.url:
                raise ConfigurationError("Grafana URL is required")

            if not (self.grafana.api_key or (self.grafana.username and self.grafana.password)):
                raise ConfigurationError("Grafana authentication is required (api_key or username/password)")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = {}

        if self.prometheus:
            result["prometheus"] = {
                "url": self.prometheus.url,
                "username": self.prometheus.username,
                "password": self.prometheus.password,
                "token": self.prometheus.token,
                "timeout": self.prometheus.timeout,
                "max_retries": self.prometheus.max_retries,
                "rate_limit": self.prometheus.rate_limit,
                "verify_ssl": self.prometheus.verify_ssl,
            }

        if self.grafana:
            result["grafana"] = {
                "url": self.grafana.url,
                "api_key": self.grafana.api_key,
                "username": self.grafana.username,
                "password": self.grafana.password,
                "org_id": self.grafana.org_id,
                "timeout": self.grafana.timeout,
                "max_retries": self.grafana.max_retries,
                "rate_limit": self.grafana.rate_limit,
                "verify_ssl": self.grafana.verify_ssl,
            }

        result["logging"] = {
            "level": self.logging.level,
            "format": self.logging.format,
            "file": self.logging.file,
        }

        return result

    def save(self, file_path: Union[str, Path]) -> None:
        """Save config to file."""
        file_path = Path(file_path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                if file_path.suffix.lower() in [".yaml", ".yml"]:
                    yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
                elif file_path.suffix.lower() == ".json":
                    import json
                    json.dump(self.to_dict(), f, indent=2)
                else:
                    raise ConfigurationError(f"Unsupported config file format: {file_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {file_path}: {str(e)}")


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    from_env: bool = True,
    prefix: str = "PROM_TOOLS",
) -> Config:
    """
    Load configuration from file and/or environment variables.

    Args:
        config_path: Path to config file (YAML or JSON)
        from_env: Whether to load from environment variables
        prefix: Environment variable prefix

    Returns:
        Config object
    """
    config = Config()

    # Load from file first
    if config_path:
        config = Config.from_file(config_path)

    # Override with environment variables if enabled
    if from_env:
        env_config = Config.from_env(prefix)

        # Merge configurations (env variables take precedence)
        if env_config.prometheus:
            config.prometheus = env_config.prometheus
        if env_config.grafana:
            config.grafana = env_config.grafana
        if env_config.logging:
            config.logging = env_config.logging

    # Validate configuration
    config.validate()

    return config


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging based on configuration."""
    import logging

    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(config.format)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if config.file:
        file_handler = logging.FileHandler(config.file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)