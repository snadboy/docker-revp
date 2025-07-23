"""Configuration management for Docker Reverse Proxy."""
import os
from pathlib import Path
from typing import List, Tuple, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

from .hosts_config import HostsConfig, load_hosts_config


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # SSH configuration (for backward compatibility, but not used with hosts.yml)
    ssh_private_key_path: str = "/home/app/.ssh/docker_monitor_key"
    
    # Caddy configuration
    caddy_api_url: str = "http://caddy:2019"
    
    # Monitoring configuration
    reconcile_interval: int = 300  # seconds
    
    # Logging configuration
    log_level: str = "INFO"
    log_max_size: int = 10  # MB
    log_backup_count: int = 5
    log_file_path: str = "/var/log/docker-revp/monitor.log"
    
    # API configuration
    api_bind: str = "0.0.0.0:8080"
    
    # Static routes configuration
    static_routes_file: str = "/app/config/static-routes.yml"
    
    # Hosts configuration
    hosts_config_file: str = "/app/config/hosts.yml"
    
    # Cloudflare API configuration
    cloudflare_api_token: str = ""
    
    @field_validator('api_bind')
    def validate_api_bind(cls, v):
        """Validate API bind format is HOST:PORT."""
        if ':' not in v:
            raise ValueError(f"API_BIND must be in HOST:PORT format, got: {v}")
        
        parts = v.split(':')
        if len(parts) != 2:
            raise ValueError(f"API_BIND must be in HOST:PORT format, got: {v}")
        
        try:
            port = int(parts[1])
            if not 1 <= port <= 65535:
                raise ValueError(f"Port must be between 1 and 65535, got: {port}")
        except ValueError:
            raise ValueError(f"Invalid port number in API_BIND: {parts[1]}")
        
        return v
    
    # Version configuration
    app_version: str = "unknown"
    build_date: str = "unknown"
    git_commit: str = "unknown"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_version_info()
        self._hosts_config: Optional[HostsConfig] = None
    
    def _load_version_info(self) -> None:
        """Load version information from environment or VERSION file."""
        # Try environment variables first (set by Docker)
        self.app_version = os.getenv("APP_VERSION", self.app_version)
        self.build_date = os.getenv("BUILD_DATE", self.build_date)
        self.git_commit = os.getenv("GIT_COMMIT", self.git_commit)
        
        # If still unknown, try to read from VERSION file
        if self.app_version == "unknown":
            try:
                version_file = Path(__file__).parent.parent / "VERSION"
                if version_file.exists():
                    self.app_version = version_file.read_text().strip()
            except Exception:
                pass
    
    def load_hosts_config(self) -> HostsConfig:
        """Load hosts configuration from hosts.yml file."""
        if self._hosts_config is not None:
            return self._hosts_config
        
        hosts_file = Path(self.hosts_config_file)
        self._hosts_config = load_hosts_config(hosts_file)
        return self._hosts_config
    
    def get_hosts_config(self) -> Optional[HostsConfig]:
        """Get cached hosts configuration."""
        return self._hosts_config
    
    def has_hosts_config(self) -> bool:
        """Check if hosts.yml configuration is available and loaded."""
        if self._hosts_config is not None:
            return True
        
        # Try to load it
        try:
            config = self.load_hosts_config()
            return config is not None
        except Exception:
            return False
    
    def get_docker_hosts(self) -> List[Tuple[str, str, int]]:
        """Get Docker hosts from hosts.yml configuration.
        
        Returns list of (alias, hostname, port) tuples.
        """
        hosts_config = self.load_hosts_config()
        return hosts_config.to_docker_hosts_format()
    
    def validate(self) -> None:
        """Validate required settings."""
        errors = []
        
        # Validate hosts.yml configuration
        try:
            hosts_config = self.load_hosts_config()
            if not hosts_config.get_enabled_hosts():
                errors.append("No enabled hosts found in hosts.yml configuration")
        except Exception as e:
            errors.append(f"hosts.yml configuration required but failed to load: {e}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))


# Global settings instance
settings = Settings()