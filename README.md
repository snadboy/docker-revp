# Docker Reverse Proxy with Caddy Integration

A Python-based Docker container that monitors Docker containers across multiple hosts via SSH and automatically configures Caddy reverse proxy routes based on container labels.

## Features

- **Multi-host Docker monitoring** via SSH
- **Real-time container event monitoring** (start, stop, pause, unpause)
- **Automatic Caddy reverse proxy configuration** via Admin API
- **FastAPI health check and metrics endpoints**
- **Comprehensive logging** with rotation
- **Configurable reconciliation** for missed events
- **SSH connection management** with automatic configuration

## Quick Start

1. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your configuration
   nano .env
   ```
   
   **Required variables in .env:**
   ```bash
   DOCKER_HOSTS=server1 server2:2222 localhost
   SSH_USER=your-ssh-user
   SSH_PRIVATE_KEY=your-private-key-content
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Check health:**
   ```bash
   curl http://localhost:8080/health/detailed
   ```

## Versioning

This project uses automatic semantic versioning based on conventional commits:

- `feat:` → Minor version bump (1.0.0 → 1.1.0)
- `fix:` → Patch version bump (1.0.0 → 1.0.1)  
- `BREAKING CHANGE:` → Major version bump (1.0.0 → 2.0.0)

### Development Workflow

```bash
# Development builds
make build              # Auto-detects version from git
make build-dev          # Explicit dev build

# Release builds (requires git tag)
git tag v1.1.0
make build-release

# View version info
make version-info
curl http://localhost:8080/health/version
```

### Automatic Releases

When you push to `main` branch with proper commit messages:

1. **Semantic Release** analyzes commits and determines new version
2. **Updates** VERSION file and creates git tag
3. **Builds** Docker image with proper version tags
4. **Publishes** to GitHub Container Registry
5. **Generates** changelog automatically

Example workflow:
```bash
git commit -m "feat: add container health monitoring"    # → v1.1.0
git commit -m "fix: handle connection timeouts"          # → v1.1.1
git commit -m "feat!: change API response format"        # → v2.0.0
git push origin main                                     # Triggers auto-release
```

## Environment Configuration

### Setup with Makefile
```bash
make dev-setup    # Creates .env from .env.example
nano .env         # Edit your configuration
```

### Manual Setup
```bash
cp .env.example .env
# Edit .env with your settings
```

**Important**: The `.env` file contains sensitive information (SSH keys) and is excluded from git via `.gitignore`.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOCKER_HOSTS` | Yes | - | Space-separated list of Docker hosts (format: `host` or `host:port`) |
| `SSH_USER` | Yes | - | SSH username for all Docker hosts |
| `SSH_PRIVATE_KEY` | Yes | - | SSH private key content |
| `CADDY_API_URL` | No | `http://caddy:2019` | Caddy Admin API endpoint |
| `RECONCILE_INTERVAL` | No | `300` | Reconciliation interval in seconds |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_MAX_SIZE` | No | `10` | Max log file size in MB |
| `LOG_BACKUP_COUNT` | No | `5` | Number of log files to keep |
| `API_PORT` | No | `8080` | Port for health check API |
| `API_HOST` | No | `0.0.0.0` | Host for health check API |

### Container Labels

Add these labels to your Docker containers to enable reverse proxy:

| Label | Required | Default | Description |
|-------|----------|---------|-------------|
| `snadboy.revp.domain` | Yes | - | Incoming domain (e.g., `app.example.com`) |
| `snadboy.revp.backend-port` | Yes | - | Container port to proxy to |
| `snadboy.revp.backend-proto` | No | `https` | Backend protocol (`http` or `https`) |
| `snadboy.revp.backend-path` | No | `/` | Backend path |
| `snadboy.revp.force-ssl` | No | `true` | Force SSL/HTTPS |

### Example Container Labels

```yaml
services:
  webapp:
    image: nginx:alpine
    labels:
      - "snadboy.revp.domain=app.example.com"
      - "snadboy.revp.backend-port=80"
      - "snadboy.revp.backend-proto=http"
      - "snadboy.revp.backend-path=/"
      - "snadboy.revp.force-ssl=true"
```

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /health/version` - Version and build information
- `GET /health/detailed` - Detailed component status
- `GET /health/metrics` - Prometheus-compatible metrics

### Example Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T00:00:00.000Z",
  "components": {
    "docker_monitor": {
      "status": "healthy",
      "total_containers": 3,
      "monitored_hosts": 2,
      "hosts": {
        "server1": {
          "container_count": 2,
          "domains": ["app1.example.com", "app2.example.com"]
        },
        "localhost": {
          "container_count": 1,
          "domains": ["test.local"]
        }
      }
    },
    "caddy_manager": {
      "status": "healthy",
      "connected": true,
      "route_count": 3,
      "routes": {
        "app1.example.com": "abc123def456",
        "app2.example.com": "def456ghi789",
        "test.local": "ghi789jkl012"
      }
    },
    "ssh_connections": {
      "status": "healthy",
      "healthy_count": 2,
      "total_count": 2,
      "connections": {
        "server1": {"alias": "docker-server1", "port": 22, "connected": true},
        "localhost": {"alias": "docker-localhost", "port": 22, "connected": true}
      }
    }
  }
}
```

## SSH Configuration

The monitor automatically generates SSH configuration in `~/.ssh/config` with entries like:

```
# BEGIN DOCKER MONITOR MANAGED HOSTS
Host docker-server1
    HostName server1
    User your-ssh-user
    Port 22
    IdentityFile ~/.ssh/docker_monitor_key
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ControlMaster auto
    ControlPath ~/.ssh/control-%r@%h:%p
    ControlPersist 10m

Host docker-server2
    HostName server2
    User your-ssh-user
    Port 2222
    IdentityFile ~/.ssh/docker_monitor_key
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ControlMaster auto
    ControlPath ~/.ssh/control-%r@%h:%p
    ControlPersist 10m
# END DOCKER MONITOR MANAGED HOSTS
```

## How It Works

1. **SSH Setup**: Generates SSH configuration and writes private key
2. **Container Discovery**: Connects to each Docker host via SSH and lists containers
3. **Event Monitoring**: Monitors Docker events in real-time for container lifecycle changes
4. **Label Processing**: Extracts `snadboy.revp.*` labels from containers
5. **Caddy Integration**: Creates/updates/removes Caddy routes via Admin API
6. **Reconciliation**: Periodically reconciles state to catch missed events

## Logging

Logs are written to `/var/log/docker-revp/monitor.log` with automatic rotation:

- **Console**: Human-readable format
- **File**: JSON format with structured data
- **Rotation**: By size (default 10MB) with configurable backup count

## Docker Compose Setup

The included `docker-compose.yml` provides:

- **Docker Monitor** service
- **Caddy** reverse proxy with Admin API enabled
- **Test web service** with example labels
- **Persistent volumes** for logs and Caddy data
- **Health checks** and automatic restarts

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH key has correct permissions (600)
   - Check host key acceptance with `StrictHostKeyChecking accept-new`
   - Ensure Docker is accessible via SSH on target hosts

2. **Container Not Detected**
   - Verify container has required labels (`snadboy.revp.domain` and `snadboy.revp.backend-port`)
   - Check Docker events are being received
   - Review logs for container processing errors

3. **Caddy Integration Failed**
   - Verify Caddy Admin API is accessible
   - Check Caddy configuration for conflicts
   - Review Caddy logs for route application errors

### Debugging

1. **Check logs:**
   ```bash
   docker-compose logs docker-revp
   # or using Makefile
   make logs
   ```

2. **Test SSH connections:**
   ```bash
   curl http://localhost:8080/health/detailed
   ```

3. **Verify Caddy routes:**
   ```bash
   curl http://caddy:2019/config/
   ```

## Security Considerations

- SSH private keys are stored with 600 permissions
- Input validation prevents label injection attacks
- Network isolation via Docker networking
- Optional API authentication via environment variables
- No secrets are logged or exposed in health checks

## Performance

- **Multi-threaded**: Monitors multiple hosts concurrently
- **Event-driven**: Real-time container detection
- **Efficient reconciliation**: Configurable interval-based consistency checks
- **Connection pooling**: SSH connection management with persistence
- **Resource monitoring**: Health checks and metrics for observability