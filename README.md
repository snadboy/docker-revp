# Docker Reverse Proxy with Caddy Integration

A Python-based Docker container that monitors Docker containers across multiple hosts via SSH and automatically configures Caddy reverse proxy routes based on container labels.

## Features

- **Multi-host Docker monitoring** via SSH using [snadboy-ssh-docker](https://pypi.org/project/snadboy-ssh-docker/) library
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

### Option 1: Using Pre-built Image (Recommended for Production)

1. **Create a docker-compose.yml file:**
   ```yaml
   services:
     docker-revp:
       image: ghcr.io/snadboy/docker-revp:latest
       container_name: docker-revp
       user: "1000:1000"
       ports:
         - "8080:8080"
       environment:
         - CADDY_API_URL=http://caddy:2019
         - LOG_LEVEL=INFO
       volumes:
         - ./logs:/var/log/docker-revp
         - ./ssh-keys/docker_monitor_key:/home/app/.ssh/docker_monitor_key:ro
         - ./config:/app/config
       restart: unless-stopped
   ```

2. **Set up SSH key:**
   ```bash
   # Create directory and copy your private key
   mkdir -p ssh-keys
   cp ~/.ssh/your_private_key ssh-keys/docker_monitor_key
   chmod 600 ssh-keys/docker_monitor_key
   ```

3. **Start the service:**
   ```bash
   docker-compose up -d
   ```

### Option 2: Building from Source (Development)

1. **Clone and configure:**
   ```bash
   git clone https://github.com/snadboy/docker-revp.git
   cd docker-revp
   cp .env.example .env
   nano .env  # Configure DOCKER_HOSTS and SSH_USER
   ```

2. **Set up SSH key:**
   ```bash
   mkdir -p ssh-keys
   cp ~/.ssh/your_private_key ssh-keys/docker_monitor_key
   chmod 600 ssh-keys/docker_monitor_key
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### Verify Installation

1. **Check health:**
   ```bash
   curl http://localhost:8080/health/detailed
   ```

2. **Access the dashboard:**
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
- **About Tab**: System information and configuration verification:
  - **System Information**: Version, build date, git commit, and host count
  - **Caddy Verification**: One-click verification of Caddy configuration against:
    - Container routes (matched, missing, orphaned)
    - Static routes (matched, missing)
    - Visual status indicators with detailed results
  - **Resource Links**: Quick access to API docs and GitHub repository

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
| `snadboy.revp.{PORT}.domain` | Yes | - | Domain for the service (e.g., `app.example.com`) |
| `snadboy.revp.{PORT}.backend-proto` | No | `http` | Backend protocol (`http` or `https`) |
| `snadboy.revp.{PORT}.backend-path` | No | `/` | Backend path |
| `snadboy.revp.{PORT}.force-ssl` | No | `true` | Force SSL/HTTPS redirect |
| `snadboy.revp.{PORT}.support-websocket` | No | `false` | Enable WebSocket support |
| `snadboy.revp.{PORT}.cloudflare-tunnel` | No | `false` | Enable Cloudflare tunnel headers (CF-Connecting-IP) |

**Key Changes from v1.x:**
- **Port-based indexing**: Use the container port as the index (e.g., `snadboy.revp.80.domain`)
- **Multiple services**: One container can now expose multiple services on different ports
- **Cleaner syntax**: No need for separate `container-port` label
- **Backward compatibility**: Legacy labels are no longer supported (breaking change)

#### Cloudflare Tunnel Configuration

When using Cloudflare Tunnels with Docker RevP, configure your tunnel to point to Caddy with the proper `httpHostHeader` parameter. This tells Caddy which backend service to route the request to.

**Tunnel Configuration (`~/.cloudflared/config.yml`):**
```yaml
tunnel: your-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  # Each service needs its hostname and httpHostHeader
  - hostname: overseerr.example.com
    service: http://caddy:80  # or http://vm-switchboard:80
    originRequest:
      httpHostHeader: overseerr.example.com  # Must match container's domain label
      
  - hostname: jellyfin.example.com
    service: http://caddy:80
    originRequest:
      httpHostHeader: jellyfin.example.com
      
  # Catch-all rule (required)
  - service: http_status:404
```

**Key Points:**
- **Service URL**: Always use `http://caddy:80` (or your Caddy host)
- **httpHostHeader**: Must match the `domain` label on your container
- **Protocol**: Use HTTP (not HTTPS) - Cloudflare handles TLS termination
- **Container Labels**: Set `cloudflare-tunnel=true` to enable CF headers
- **No DNS Records**: Cloudflare Tunnel handles public DNS automatically

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

**Container with Cloudflare Tunnel Support:**
```yaml
services:
  overseerr:
    image: sctx/overseerr:latest
    ports:
      - "5055:5055"
    labels:
      - "snadboy.revp.5055.domain=overseerr.example.com"
      - "snadboy.revp.5055.backend-proto=http"
      - "snadboy.revp.5055.support-websocket=false"
      - "snadboy.revp.5055.cloudflare-tunnel=true"  # Enable CF headers
      - "snadboy.revp.5055.force-ssl=false"  # Disable HTTPS redirect for tunnel
```

**How it works:**
- Single domain `overseerr.example.com` works for both local and tunnel access
- `cloudflare-tunnel=true` enables proper Cloudflare headers (CF-Connecting-IP)
- `force-ssl=false` prevents HTTPS redirect issues with tunnels
- Cloudflare Tunnel config uses `httpHostHeader` to route to correct service

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
     
     # Example service behind Cloudflare tunnel
     - domain: public.example.com
       backend_url: http://192.168.1.102:8080
       backend_path: /
       force_ssl: true
       cloudflare_tunnel: true  # Enable Cloudflare headers
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
| `tls_insecure_skip_verify` | No | `false` | Skip TLS certificate verification (⚠️ **Security Risk**) |
| `cloudflare_tunnel` | No | `false` | Enable Cloudflare tunnel headers for accurate client IP |

**Features:**
- **Web dashboard CRUD**: Add, edit, delete routes via user-friendly interface
- **Automatic file watching**: Changes to static-routes.yml are detected and applied immediately
- **Real-time updates**: Routes are updated in Caddy without container restart
- **Same features**: Static routes support force-ssl, websocket, and all container label features
- **Dashboard integration**: Static routes appear in the dashboard alongside containers  
- **API access**: Full REST API for programmatic management
- **Form validation**: Prevents invalid configurations and domain conflicts

### 🔒 TLS Security Configuration

#### Overview

The `tls_insecure_skip_verify` option allows RevP to proxy traffic to HTTPS backends that use self-signed or invalid certificates. **This is a security-sensitive feature that should only be used in specific, controlled environments.**

#### When to Use TLS Skip Verify

✅ **Appropriate Use Cases:**
- **Home lab servers** with self-signed certificates (Proxmox, NAS devices, IoT devices)
- **Internal development environments** where certificate validation isn't critical
- **Legacy systems** that can't be updated with proper certificates
- **Local services** on private networks where certificate validation is impractical

❌ **Inappropriate Use Cases:**
- **Production internet-facing services**
- **Third-party APIs** or external services
- **Services handling sensitive data** (payment, personal information)
- **Services where man-in-the-middle attacks are a concern**

#### Security Implications

⚠️ **CRITICAL SECURITY WARNING**

When `tls_insecure_skip_verify: true` is enabled:

1. **Certificate Validation Bypassed**: RevP will accept any certificate, including:
   - Self-signed certificates
   - Expired certificates
   - Certificates with wrong hostnames
   - Certificates from untrusted Certificate Authorities

2. **Man-in-the-Middle Vulnerability**: An attacker on the network could potentially:
   - Intercept and modify traffic between RevP and the backend
   - Present their own certificate without detection
   - Eavesdrop on sensitive communications

3. **No Identity Verification**: RevP cannot verify it's actually connecting to the intended backend server

#### Best Practices for TLS Skip Verify

1. **Network Security**: Only use on trusted, isolated networks:
   ```yaml
   # Good: Internal home network
   - domain: homelab.internal.com
     backend_url: https://192.168.1.100:8006  # Internal IP
     tls_insecure_skip_verify: true
   
   # Bad: External service
   - domain: api.external-service.com
     backend_url: https://api.external-service.com
     tls_insecure_skip_verify: true  # DON'T DO THIS
   ```

2. **Document Usage**: Always document why TLS skip verify is needed:
   ```yaml
   # Example configuration with documentation
   static_routes:
   - domain: proxmox.home.lab
     backend_url: https://192.168.86.100:8006
     tls_insecure_skip_verify: true
     # Reason: Proxmox VE uses self-signed certificate in home lab
     # Risk Assessment: Low (internal network, home environment)
     # Alternative: Could install custom CA but not practical for home use
   ```

3. **Regular Review**: Periodically review all routes with TLS skip verify enabled

4. **Consider Alternatives**: Before using TLS skip verify, consider:
   - Installing a custom Certificate Authority (CA)
   - Using Let's Encrypt with DNS-01 challenge for internal domains
   - Configuring the backend service to use proper certificates
   - Using HTTP instead of HTTPS for truly internal services

#### Configuration Examples

**Home Lab Proxmox Server:**
```yaml
static_routes:
- domain: proxmox.home.lab
  backend_url: https://192.168.1.100:8006
  backend_path: /
  force_ssl: true
  support_websocket: true
  tls_insecure_skip_verify: true  # Self-signed cert in home lab
```

**Secure Production Service (Recommended):**
```yaml
static_routes:
- domain: api.production.com
  backend_url: https://internal-api.production.com
  backend_path: /api/v1
  force_ssl: true
  support_websocket: false
  tls_insecure_skip_verify: false  # Proper certificates required
```

#### Dashboard Warning

When configuring routes through the web dashboard, routes with `tls_insecure_skip_verify: true` will be:
- Marked with a warning badge in the interface
- Include tooltips explaining the security implications
- Display security warnings in the form when enabled

#### Monitoring and Auditing

- All routes with TLS skip verify enabled are logged during startup
- Use the dashboard to regularly audit which routes have this option enabled
- Monitor logs for any TLS-related errors that might indicate certificate issues

## 🌐 Cloudflare Tunnel Integration

### Overview

Docker Reverse Proxy (RevP) fully supports Cloudflare Tunnel (formerly Argo Tunnel) for secure external access to your services without opening firewall ports. This section covers all configuration options and best practices.

### Understanding the Challenge

When using Cloudflare Tunnel with a reverse proxy like Caddy, several challenges arise:

1. **SSL/TLS Termination**: Cloudflare terminates SSL at their edge, then forwards traffic to your tunnel
2. **Host Header Mismatch**: The tunnel may send different Host headers than Caddy expects
3. **Protocol Confusion**: HTTP vs HTTPS routing between tunnel and Caddy
4. **Dual Access**: Supporting both external (tunnel) and internal (direct) access

### Configuration Options

#### Option 1: Container Tunnel Domain Labels (Recommended)

Use container labels to define both primary and tunnel domains. This maintains RevP's dynamic port resolution while supporting Cloudflare tunnels.

**Benefits:**
- ✅ Same public domain for all users
- ✅ Dynamic port resolution (no hard-coded ports)
- ✅ Single source of truth (container labels)
- ✅ Automatic tunnel configuration
- ✅ No static route files needed

**Configuration:**

1. **Add tunnel domain label to your container**:
```yaml
# In your service's docker-compose.yml
services:
  overseerr:
    image: sctx/overseerr:latest
    labels:
      # Primary domain for local access (HTTPS with redirect)
      - "snadboy.revp.5055.domain=overseerr.snadboy.com"
      - "snadboy.revp.5055.force-ssl=true"
      
      # Tunnel domain for Cloudflare access (HTTP without redirect)
      - "snadboy.revp.5055.tunnel-domain=cf-overseerr.snadboy.com"
    ports:
      - "5055:5055"
```

2. **Cloudflare Tunnel configuration**:
```
Public hostname: overseerr.snadboy.com
Service URL: http://cf-overseerr.snadboy.com
HTTP Host Header: (leave default)
Origin Server Name: (leave default)
```

3. **How it works**:
```
External: User → overseerr.snadboy.com → Cloudflare → Tunnel → cf-overseerr.snadboy.com → Caddy:80 → Backend
Internal: User → overseerr.snadboy.com → Split DNS → Caddy:443 (HTTPS) → Backend
```

4. **Automatic behavior**:
   - **Primary domain** (`overseerr.snadboy.com`): HTTPS route + HTTP redirect
   - **Tunnel domain** (`cf-overseerr.snadboy.com`): HTTP route only, no redirect, cloudflare_tunnel=true

#### Option 2: Static Routes for Tunnel Domains

Create separate static routes for tunnel access while keeping container labels for local access.

**Benefits:**
- ✅ Works with existing containers without label changes
- ✅ Clear separation between tunnel and local configuration

**Drawbacks:**
- ❌ Hard-coded ports (breaks if container port mappings change)
- ❌ Additional configuration files to maintain

**Configuration:**

1. **Add static route for tunnel** (`config/static-routes.yml`):
```yaml
static_routes:
  # Tunnel-specific route (not visible to users)
  - domain: cf-overseerr.snadboy.com
    backend_url: http://host.media-arr.snadboy.com:5055  # Hard-coded port
    backend_path: /
    force_ssl: false  # No redirect needed for tunnel
    support_websocket: false
    tls_insecure_skip_verify: false
    cloudflare_tunnel: true  # Enables CF-specific headers

  # Keep the Docker container with original domain for local access
  # The container labels will create: overseerr.snadboy.com → HTTPS with redirect
```

2. **Cloudflare Tunnel configuration**:
```
Public hostname: overseerr.snadboy.com
Service URL: http://cf-overseerr.snadboy.com
HTTP Host Header: (leave default)
Origin Server Name: (leave default)
```

#### Option 3: Host Header Override

Configure the tunnel to send the correct Host header that Caddy expects.

**Configuration:**

1. **Cloudflare Tunnel configuration**:
```
Public hostname: overseerr.snadboy.com
Service URL: https://your-caddy-server.local
HTTP Host Header: overseerr.snadboy.com  ← Critical setting
Origin Server Name: overseerr.snadboy.com
```

2. **Pros/Cons**:
- ✅ No additional routes or labels needed
- ✅ Works with existing container configuration
- ❌ More complex tunnel configuration
- ❌ Potential SSL certificate issues

### The `cloudflare_tunnel` Flag

When `cloudflare_tunnel: true` is set (either via static routes or container labels):

1. **Routing Changes**:
   - Route is added to port 80 (HTTP) without redirect
   - Route is also added to port 443 (HTTPS) for flexibility
   - No HTTP→HTTPS redirect is created

2. **Header Handling**:
   - Uses `CF-Connecting-IP` for real client IP
   - Preserves `X-Forwarded-Proto` as `https`
   - Maintains proper `X-Forwarded-Host` headers

3. **Security Headers**:
   ```json
   {
     "X-Real-IP": "{http.request.header.CF-Connecting-IP}",
     "X-Forwarded-For": "{http.request.header.CF-Connecting-IP}",
     "X-Forwarded-Proto": "https",
     "X-Forwarded-Host": "{http.request.host}"
   }
   ```

### Common Tunnel Errors and Solutions

#### ERR_SSL_PROTOCOL_ERROR

**Cause**: Tunnel is configured to use HTTPS but receives an HTTP redirect.

**Solution**: Use one of the configuration options above to avoid redirects.

#### 502 Bad Gateway

**Cause**: Usually a Host header mismatch - Caddy can't find a matching route.

**Solutions**:
1. Use dedicated tunnel domain (Option 1)
2. Configure HTTP Host Header in tunnel settings (Option 2)
3. Check Caddy logs for the exact Host header being received

#### 521 Web Server Is Down

**Cause**: Cloudflare can't reach your origin server.

**Solutions**:
1. Verify tunnel is running: `cloudflared tunnel list`
2. Check tunnel logs: `cloudflared tunnel logs <tunnel-name>`
3. Ensure Service URL is correct in tunnel configuration

### Best Practices

1. **Use Dedicated Domains for Tunnels**
   - Cleaner configuration
   - Easier troubleshooting
   - No header manipulation needed

2. **Naming Convention**
   ```yaml
   # Good naming pattern
   cf-<service>.domain.com    # For tunnel access
   <service>.domain.com        # For local/direct access
   ```

3. **Security Considerations**
   - Tunnels already provide encryption (tunnel → Cloudflare)
   - Use `force_ssl: false` for tunnel routes to avoid redirect loops
   - Keep `force_ssl: true` for direct/local access routes

4. **Testing Your Configuration**
   ```bash
   # Test tunnel route (from external network)
   curl -I https://service.yourdomain.com
   
   # Test local route (from internal network)
   curl -I https://service.yourdomain.com
   
   # Debug Host headers
   curl -H "Host: cf-service.yourdomain.com" http://your-caddy-ip
   ```

5. **Multiple Services Pattern**
   ```yaml
   static_routes:
     # Overseerr
     - domain: cf-overseerr.snadboy.com
       backend_url: http://host.media-arr.snadboy.com:5055
       cloudflare_tunnel: true
       force_ssl: false
     
     # Sonarr
     - domain: cf-sonarr.snadboy.com
       backend_url: http://host.media-arr.snadboy.com:8989
       cloudflare_tunnel: true
       force_ssl: false
     
     # Radarr
     - domain: cf-radarr.snadboy.com
       backend_url: http://host.media-arr.snadboy.com:7878
       cloudflare_tunnel: true
       force_ssl: false
   ```

### Monitoring Tunnel Routes

1. **Via Dashboard**: Static routes with `cloudflare_tunnel: true` are marked in the UI
2. **Via Logs**: Look for "cloudflare_tunnel" or "CF-" headers in Caddy logs
3. **Via API**: Query `/api/static-routes` to see all tunnel-enabled routes

### Migration Guide

#### From Port Forwarding to Cloudflare Tunnel

**Recommended Approach (Container Labels):**

1. **Add tunnel-domain label** to existing containers:
   ```yaml
   # Before (existing)
   - "snadboy.revp.5055.domain=overseerr.example.com"
   
   # Add this line
   - "snadboy.revp.5055.tunnel-domain=cf-overseerr.example.com"
   ```

2. **Configure Cloudflare tunnel** to use the tunnel domain:
   - Public hostname: `overseerr.example.com`
   - Service URL: `http://cf-overseerr.example.com`

3. **Test and verify**:
   - Internal: `https://overseerr.example.com` (should work locally)
   - External: `https://overseerr.example.com` (should work via tunnel)

**Alternative Approach (Static Routes):**

1. **Keep existing container labels** for local access
2. **Add tunnel-specific static routes** with `cf-` prefix
3. **Configure tunnel** to use the `cf-` domains
4. **Note**: This creates hard-coded port dependencies

**Migration Steps:**
1. **Test thoroughly** before removing port forwards
2. **Monitor logs** for any SSL or routing errors
3. **Verify both local and tunnel access** work correctly

### Troubleshooting Checklist

- [ ] Tunnel is running and connected
- [ ] Service URL in tunnel config is reachable from Caddy
- [ ] Host header matches a configured route in Caddy
- [ ] No HTTPS redirect for tunnel routes (`force_ssl: false`)
- [ ] `cloudflare_tunnel: true` is set for tunnel routes
- [ ] DNS records exist for tunnel domains
- [ ] Backend service is actually running and healthy

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

### Configuration Verification

- `GET /api/verify-caddy` - Verify Caddy configuration against discovered containers and static routes
  - Returns matched, missing, and orphaned routes with detailed status information

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
    "support_websocket": false,
    "tls_insecure_skip_verify": false
  }'
```

**Create route for self-signed certificate (home lab):**
```bash
curl -X POST http://localhost:8080/api/static-routes \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "proxmox.home.lab",
    "backend_url": "https://192.168.1.100:8006",
    "backend_path": "/",
    "force_ssl": true,
    "support_websocket": true,
    "tls_insecure_skip_verify": true
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
    "support_websocket": true,
    "tls_insecure_skip_verify": false
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