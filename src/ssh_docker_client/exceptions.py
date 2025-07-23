"""Exception classes for SSH Docker Client."""


class SSHDockerError(Exception):
    """Base exception for all SSH Docker Client errors."""
    pass


class ConfigurationError(SSHDockerError):
    """Raised when there's an error in configuration."""
    pass


class SSHConnectionError(SSHDockerError):
    """Raised when SSH connection fails."""
    pass


class DockerCommandError(SSHDockerError):
    """Raised when Docker command execution fails."""
    pass


class HostNotFoundError(SSHDockerError):
    """Raised when specified host is not found in configuration."""
    pass


class ContainerNotFoundError(SSHDockerError):
    """Raised when specified container is not found."""
    pass