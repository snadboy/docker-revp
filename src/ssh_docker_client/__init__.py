"""SSH Docker Client - A Python library for managing Docker over SSH."""

from .client import SSHDockerClient
from .config import HostsConfig, load_hosts_config
from .exceptions import (
    SSHDockerError,
    SSHConnectionError,
    DockerCommandError,
    HostNotFoundError,
    ConfigurationError,
)
from .models import HostConfig, HostDefaults
from .ssh_manager import SSHManager

__version__ = "0.1.0"
__all__ = [
    "SSHDockerClient",
    "SSHManager",
    "HostsConfig",
    "HostConfig",
    "HostDefaults",
    "load_hosts_config",
    "SSHDockerError",
    "SSHConnectionError",
    "DockerCommandError",
    "HostNotFoundError",
    "ConfigurationError",
]