# Docker Reverse Proxy with Caddy Integration

A Python-based Docker container that monitors Docker containers across multiple hosts via SSH and automatically configures Caddy reverse proxy routes based on container labels.

## Features

- **Multi-host Docker monitoring** via SSH
- **Real-time container event monitoring** (start, stop, pause, unpause)
- **Automatic Caddy reverse proxy configuration** via Admin API
- **Static route configuration** via YAML for external services
- **Static routes CRUD management** via web dashboard (add, edit, delete routes)
- **FastAPI health check and metrics endpoints**
- **AI-native MCP (Model Context Protocol) integration** for AI agent access
- **Responsive web dashboard** with real-time container management
- **Advanced table widgets** with sorting, resizing, and filtering
- **WebSocket support** for real-time applications
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
   ```

   **📋 SSH Private Key Setup:**
   
   Create the ssh-keys directory and copy your private key:
   
   ```bash
   # Create directory
   mkdir -p ssh-keys
   
   # Copy your private key (any type: RSA, ed25519, etc.)
   cp ~/.ssh/your_private_key ssh-keys/docker_monitor_key
   
   # Set proper permissions
   chmod 600 ssh-keys/docker_monitor_key
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Check health:**
   ```bash
   curl http://localhost:8080/health/detailed
   ```

4. **Access the dashboard:**
   ```bash
   # Web interface
   open http://localhost:8080
   
   # AI agent MCP endpoint
   curl http://localhost:8080/mcp
   ```

## Web Dashboard

The responsive web dashboard provides comprehensive container and static route management:

### Dashboard Features

- **Summary Tab**: Overview with total containers, hosts, and health status
- **Containers Tab**: Real-time container monitoring with:
  - Sortable columns (Name, Host, Status, Image, Domain, etc.)
  - Resizable columns by dragging
  - Expandable rows showing detailed container labels
  - Filter by RevP containers and hosts
  - Multi-service container support

- **Static Routes Tab**: Full CRUD management for external services:
  - **Add Routes**: Web form with validation for new static routes
  - **Edit Routes**: Click to modify existing route configurations
  - **Delete Routes**: One-click removal with confirmation
  - **Sortable/Resizable**: Same advanced table features as containers
  - **Real-time Updates**: Changes applied immediately to Caddy
  - **File Status**: Shows YAML file health and last modified time

- **Health Tab**: System component monitoring
- **Version Tab**: Build information and changelog

### Dashboard Screenshots

Access the dashboard at `http://localhost:8080` to see:
- Real-time container status updates
- Interactive table management
- Responsive design for mobile/desktop
- Dark/light theme toggle

## AI Integration (MCP)

Docker RevP now includes **Model Context Protocol (MCP)** support, allowing AI agents like Claude to interact directly with your container infrastructure.

### Available MCP Tools

When connected via MCP, AI agents can access:

- **`list_containers`** - Get all monitored containers with filtering options
- **`health_check`** - Check system health status  
- **`detailed_health_check`** - Get detailed component health information
- **`version_info`** - Get version and build information
- **`metrics`** - Get Prometheus-compatible metrics

### Prerequisites

The MCP connection uses `mcp-remote` which is automatically installed via npx, so no manual installation is required.

### Setting Up MCP in Different AI Platforms

#### Claude Desktop

1. **Open Claude Desktop settings**
2. **Navigate to Developer → Model Context Protocol**
3. **Edit the configuration:**

```json
{
  "servers": {
    "docker-revp": {
      "command": "npx",
      "args": [
        "-p",
        "mcp-remote@latest",
        "mcp-remote",
        "http://your-server:8080/mcp"
      ]
    }
  }
}
```

4. **Restart Claude Desktop** to load the MCP server

#### Claude Code (CLI)

1. **Create/edit MCP config file:**
```bash
# Default location
~/.config/claude-code/mcp.json
```

2. **Add your server configuration:**
```json
{
  "servers": {
    "docker-revp": {
      "command": "npx",
      "args": [
        "-p",
        "mcp-remote@latest",
        "mcp-remote",
        "http://your-server:8080/mcp"
      ],
      "env": {
        "DESCRIPTION": "Docker RevP container monitoring"
      }
    }
  }
}
```

3. **Reload MCP configuration:**
```bash
claude-code --reload-mcp
```

#### Claude Web (claude.ai)

Claude Web doesn't directly support custom MCP servers. However, you can:

1. **Use Claude Projects** with API documentation
2. **Create a Custom GPT** that calls your API
3. **Use browser extensions** that add MCP support (community-driven)

#### VS Code

**Option 1: Claude Dev Extension**

1. **Install "Claude Dev" extension** from VS Code marketplace
2. **Add to VS Code settings.json:**
```json
{
  "claude.mcpServers": {
    "docker-revp": {
      "command": "npx",
      "args": [
        "-p",
        "mcp-remote@latest",
        "mcp-remote",
        "http://your-server:8080/mcp"
      ]
    }
  }
}
```

**Option 2: MCP Client Extension**

1. **Install "Model Context Protocol" extension**
2. **Configure in settings.json:**
```json
{
  "mcp.servers": [
    {
      "name": "docker-revp",
      "url": "http://your-server:8080/mcp",
      "transport": "sse"
    }
  ]
}
```

#### ChatGPT

ChatGPT doesn't natively support MCP, but you can:

1. **Create a Custom GPT** with actions:
   - Go to ChatGPT → Explore → Create a GPT
   - Add Actions → Import OpenAPI schema from `http://your-server:8080/openapi.json`
   - Configure authentication if needed

2. **Use GPT Builder Actions:**
```yaml
openapi: 3.0.0
servers:
  - url: http://your-server:8080
paths:
  /containers:
    get:
      operationId: listContainers
      summary: List all containers
  /health/detailed:
    get:
      operationId: getHealth
      summary: Get system health
```

#### Gemini

Gemini doesn't support MCP directly, but alternatives include:

1. **Google AI Studio Extensions** (when available)
2. **Vertex AI Extensions:**
   - Create a Cloud Function that calls your MCP endpoint
   - Register as Vertex AI extension
3. **API Integration via Code Interpreter:**
   - Provide API documentation in context
   - Use Gemini's code execution to call your API

### MCP Connection Options

**Direct HTTP Connection:**
```json
{
  "command": "mcp-client-http",
  "args": ["--url", "http://your-server:8080/mcp"]
}
```

**With Authentication:**
```json
{
  "command": "npx",
  "args": [
    "-p",
    "mcp-remote@latest", 
    "mcp-remote",
    "http://your-server:8080/mcp"
  ],
  "env": {
    "AUTHORIZATION": "Bearer your-api-key"
  }
}
```

**Docker Network (for local development):**
```json
{
  "command": "npx",
  "args": [
    "-p",
    "mcp-remote@latest",
    "mcp-remote", 
    "http://revp-api:8080/mcp"
  ]
}
```

### Troubleshooting MCP Connections

1. **Test MCP endpoint:**
```bash
curl http://your-server:8080/mcp
```

2. **Verify server is running:**
```bash
docker-compose ps
curl http://your-server:8080/health
```

3. **Check logs for MCP mounting:**
```bash
docker-compose logs revp-api | grep MCP
```

4. **Common issues:**
   - **Connection refused**: Check firewall/port forwarding
   - **404 Not Found**: Ensure FastAPI-MCP is installed
   - **Auth errors**: Verify API key configuration
   - **CORS errors**: May need to configure CORS for browser-based clients

### Example AI Interactions

Once connected, you can ask AI agents:
- *"Show me all running containers on vm-switchboard"*
- *"What's the health status of the Docker RevP system?"*
- *"How many containers are currently monitored?"*
- *"Are there any containers with RevP labels that aren't running?"*

The AI will automatically use the appropriate MCP tools to query your infrastructure and provide real-time information.

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
| SSH Private Key | Yes | - | Mounted from `./ssh-keys/docker_monitor_key` |
| `CADDY_API_URL` | No | `http://caddy:2019` | Caddy Admin API endpoint |
| `RECONCILE_INTERVAL` | No | `300` | Reconciliation interval in seconds |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_MAX_SIZE` | No | `10` | Max log file size in MB |
| `LOG_BACKUP_COUNT` | No | `5` | Number of log files to keep |
| `API_BIND` | No | `0.0.0.0:8080` | API server bind address (HOST:PORT format) |

### Container Labels

Add these port-based labels to your Docker containers to enable reverse proxy. The new format allows multiple services per container by using the container port as an index.

**Label Format:** `snadboy.revp.{PORT}.{PROPERTY}`

| Label | Required | Default | Description |
|-------|----------|---------|-------------|
| `snadboy.revp.{PORT}.domain` | Yes | - | Incoming domain (e.g., `app.example.com`) |
| `snadboy.revp.{PORT}.backend-proto` | No | `http` | Backend protocol (`http` or `https`) |
| `snadboy.revp.{PORT}.backend-path` | No | `/` | Backend path |
| `snadboy.revp.{PORT}.force-ssl` | No | `true` | Force SSL/HTTPS |
| `snadboy.revp.{PORT}.support-websocket` | No | `false` | Enable WebSocket support |

**Key Changes from v1.x:**
- **Port-based indexing**: Use the container port as the index (e.g., `snadboy.revp.80.domain`)
- **Multiple services**: One container can now expose multiple services on different ports
- **Cleaner syntax**: No need for separate `container-port` label
- **Backward compatibility**: Legacy labels are no longer supported (breaking change)

### Example Container Labels

**Single Service Container:**
```yaml
services:
  webapp:
    image: nginx:alpine
    ports:
      - "8080:80"  # Maps host port 8080 to container port 80
    labels:
      - "snadboy.revp.80.domain=app.example.com"
      - "snadboy.revp.80.backend-proto=http"
      - "snadboy.revp.80.backend-path=/"
      - "snadboy.revp.80.force-ssl=true"
      - "snadboy.revp.80.support-websocket=false"
```

**Multi-Service Container:**
```yaml
services:
  multi-app:
    image: my-app:latest
    ports:
      - "8080:80"    # Main app
      - "8081:8000"  # Admin interface
    labels:
      # Main application on port 80
      - "snadboy.revp.80.domain=app.example.com"
      - "snadboy.revp.80.backend-proto=http"
      - "snadboy.revp.80.backend-path=/"
      - "snadboy.revp.80.force-ssl=true"
      
      # Admin interface on port 8000
      - "snadboy.revp.8000.domain=admin.example.com"
      - "snadboy.revp.8000.backend-proto=https"
      - "snadboy.revp.8000.backend-path=/dashboard"
      - "snadboy.revp.8000.force-ssl=true"
      - "snadboy.revp.8000.support-websocket=true"
```

### Static Routes Configuration

For services that aren't running in Docker containers (legacy systems, external APIs, etc.), you can configure static routes using either the **web dashboard** or **YAML file**.

#### Method 1: Web Dashboard (Recommended)

1. **Access the dashboard:** `http://localhost:8080`
2. **Navigate to Static Routes tab**
3. **Add routes:** Click "Add Static Route" button
4. **Edit routes:** Click "Edit" button on any route
5. **Delete routes:** Click "Delete" button with confirmation

**Web Dashboard Features:**
- Form validation with helpful error messages
- Real-time updates to Caddy configuration
- No file editing required
- Automatic YAML file management
- Sortable/resizable table interface

#### Method 2: YAML File Configuration

**Setup:**
1. **Create static routes file:**
   ```bash
   mkdir -p config
   cp static-routes.yml.example config/static-routes.yml
   # Edit config/static-routes.yml with your routes
   ```

2. **YAML Configuration Format:**
   ```yaml
   static_routes:
     # Example legacy API service
     - domain: api.legacy.company.com
       backend_url: http://192.168.1.100:3000
       backend_path: /api/v1
       force_ssl: true
       support_websocket: false

     # Example admin interface
     - domain: admin.internal.company.com
       backend_url: https://192.168.1.101:8443
       backend_path: /dashboard
       force_ssl: true
       support_websocket: true
   ```

3. **Volume Mount (already configured in docker-compose.yml):**
   ```yaml
   volumes:
     # Mount entire config directory for CRUD operations
     - ./config:/app/config
   ```

**Static Route Properties:**

| Property | Required | Default | Description |
|----------|----------|---------|-------------|
| `domain` | Yes | - | Incoming domain (e.g., `api.example.com`) |
| `backend_url` | Yes | - | Backend service URL (e.g., `http://192.168.1.100:3000`) |
| `backend_path` | No | `/` | Path to append to backend requests |
| `force_ssl` | No | `true` | Force HTTPS redirection |
| `support_websocket` | No | `false` | Enable WebSocket support |

**Features:**
- **Web dashboard CRUD**: Add, edit, delete routes via user-friendly interface
- **Automatic file watching**: Changes to static-routes.yml are detected and applied immediately
- **Real-time updates**: Routes are updated in Caddy without container restart
- **Same features**: Static routes support force-ssl, websocket, and all container label features
- **Dashboard integration**: Static routes appear in the dashboard alongside containers  
- **API access**: Full REST API for programmatic management
- **Form validation**: Prevents invalid configurations and domain conflicts

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /health/version` - Version and build information
- `GET /health/detailed` - Detailed component status
- `GET /health/metrics` - Prometheus-compatible metrics

### Containers & Routes

- `GET /containers` - List all monitored containers
- `GET /containers/static-routes` - List static routes only
- `GET /containers/all-services` - Combined containers and static routes

### Static Routes Management

- `GET /api/static-routes` - List all static routes
- `POST /api/static-routes` - Create a new static route
- `PUT /api/static-routes/{domain}` - Update existing static route
- `DELETE /api/static-routes/{domain}` - Delete static route
- `GET /api/static-routes/info/file` - Get static routes file information

#### Static Routes API Examples

**Create a new route:**
```bash
curl -X POST http://localhost:8080/api/static-routes \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "api.example.com",
    "backend_url": "http://192.168.1.100:3000",
    "backend_path": "/api/v1",
    "force_ssl": true,
    "support_websocket": false
  }'
```

**Update existing route:**
```bash
curl -X PUT http://localhost:8080/api/static-routes/api.example.com \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "api.example.com",
    "backend_url": "http://192.168.1.101:3000",
    "backend_path": "/api/v2",
    "force_ssl": true,
    "support_websocket": true
  }'
```

**Delete route:**
```bash
curl -X DELETE http://localhost:8080/api/static-routes/api.example.com
```

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

## SSH User Requirements

The SSH user specified in `SSH_USER` must have the following permissions on each Docker host:

### Required Permissions

1. **Docker Group Membership**
   ```bash
   # Add user to docker group on each host
   sudo usermod -aG docker your-ssh-user
   ```

2. **Docker Socket Access**
   - The user must be able to access `/var/run/docker.sock`
   - This is typically granted by docker group membership
   - Verify with: `docker ps` (should work without sudo)

3. **SSH Key Authentication**
   - Password authentication is not supported
   - Public key must be in `~/.ssh/authorized_keys` on each host
   - Private key mounted from `./ssh-keys/docker_monitor_key`

4. **Network Access**
   - SSH access to each host (default port 22 or custom port)
   - Ability to connect to Docker daemon (unix socket or TCP)

### Verification Commands

Run these commands on each Docker host to verify permissions:

```bash
# Test Docker access (should work without sudo)
docker ps
docker version

# Test Docker events (used by the monitor)
timeout 5 docker events

# Verify user is in docker group
groups $USER | grep docker

# Test SSH key authentication
ssh-add -l  # Should list your key
```

### Common Issues

- **Permission denied accessing Docker**: Add user to docker group and logout/login
- **Docker daemon not accessible**: Ensure Docker service is running
- **SSH key issues**: Verify key format and permissions (600 for private key)

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
   - Verify container has required labels (`snadboy.revp.{PORT}.domain`)
   - Check Docker events are being received
   - Review logs for container processing errors

3. **Caddy Integration Failed**
   - Verify Caddy Admin API is accessible
   - Check Caddy configuration for conflicts
   - Review Caddy logs for route application errors

4. **Static Routes Issues**
   - Use web dashboard for easier management instead of manual YAML editing
   - Check config directory permissions (should be writable)
   - Verify static routes file syntax via `/api/static-routes/info/file`
   - Look for domain conflicts in dashboard or API responses

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