# Technical Design Document: Docker RevP Dashboard

## 1. Document Overview

### 1.1 Purpose
This Technical Design Document (TDD) provides comprehensive technical specifications for the Docker RevP Dashboard implementation. It serves as the authoritative reference for developers, architects, and operations teams.

### 1.2 Scope
This document covers the technical architecture, implementation details, APIs, data models, deployment strategy, and operational considerations for the Docker RevP Dashboard.

### 1.3 Related Documents
- Product Requirements Document (PRD.md)
- API Documentation (/docs, /redoc endpoints)
- README.md

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Browser                           │
│                   (Dashboard Frontend)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend                           │
│                  (Python Application)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   API       │  │    Static    │  │   Dashboard  │      │
│  │  Endpoints  │  │    Files     │  │   Routes     │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Service Layer                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Docker    │  │    Caddy     │  │     SSH      │      │
│  │  Monitor    │  │   Manager    │  │  Connector   │      │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼────────────────┼──────────────────┼──────────────┘
          │                │                  │
          ▼                ▼                  ▼
    Docker Daemon    Caddy Server      Remote Hosts

```

### 2.2 Component Architecture

#### 2.2.1 Frontend Components
- **Static HTML/CSS/JS**: Vanilla JavaScript with no framework dependencies
- **Dashboard.js**: Main application logic and state management
- **Dashboard.css**: Styling with CSS custom properties for theming
- **Service Worker**: Future enhancement for offline capabilities

#### 2.2.2 Backend Components
- **FastAPI Application**: Main web server and API provider
- **Docker Monitor Service**: Container monitoring and management
- **Caddy Manager Service**: Reverse proxy configuration management
- **SSH Connector**: Remote host connectivity
- **Health Check System**: Component health monitoring

### 2.3 Data Flow

```
User Action → Frontend Event → API Call → Backend Service → 
External System → Response → Frontend Update → UI Render
```

## 3. Technology Stack

### 3.1 Frontend Technologies

#### 3.1.1 Core Technologies
- **HTML5**: Semantic markup, Web Components ready
- **CSS3**: Modern layouts with Grid/Flexbox
- **JavaScript (ES6+)**: No transpilation required
- **Web APIs**: Fetch API, LocalStorage, Event API

#### 3.1.2 CSS Architecture
```css
/* CSS Custom Properties for Theming */
:root {
    --primary-color: #2563eb;
    --background-color: #f3f4f6;
    /* ... additional variables */
}

[data-theme="dark"] {
    --primary-color: #3b82f6;
    --background-color: #0f172a;
    /* ... dark theme overrides */
}
```

#### 3.1.3 JavaScript Architecture
```javascript
// Class-based architecture
class Dashboard {
    constructor() {
        this.currentTab = 'summary';
        this.containers = [];
        // ... initialization
    }
    
    async init() {
        this.setupThemeToggle();
        this.setupTabSwitching();
        // ... setup methods
    }
}
```

### 3.2 Backend Technologies

#### 3.2.1 Core Stack
- **Python 3.9+**: Primary programming language
- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and settings management

#### 3.2.2 Dependencies
```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
paramiko==3.3.1
docker==6.1.3
httpx==0.25.1
jinja2==3.1.2
python-multipart==0.0.6
```

#### 3.2.3 Configuration Management
```python
# Environment variables via .env file
REVP_API_KEY=your-api-key
REVP_SSH_KEY_PATH=/path/to/ssh/key
REVP_HOSTS=host1,host2,host3
REVP_MONITORING_ENABLED=true
```

### 3.3 Infrastructure Technologies

#### 3.3.1 Container Platform
- **Docker Engine**: 20.10+
- **Docker Compose**: v2.0+
- **Docker SDK**: Python integration

#### 3.3.2 Reverse Proxy
- **Caddy Server**: v2.0+
- **Caddy API**: RESTful configuration

#### 3.3.3 Monitoring Stack
- **Health Endpoints**: Custom implementation
- **Metrics Collection**: In-memory aggregation
- **Log Aggregation**: Structured logging

## 4. API Design

### 4.1 RESTful API Principles
- **Resource-based URLs**: `/api/containers`, `/api/health`
- **HTTP Methods**: GET for reads, POST/PUT/DELETE for modifications
- **Status Codes**: Proper HTTP status code usage
- **JSON Responses**: Consistent response format

### 4.2 API Endpoints

#### 4.2.1 Container Management
```yaml
GET /api/containers:
  description: List all containers across hosts
  parameters:
    - host: string (optional)
    - status: string (optional)
    - revp_only: boolean (optional)
  response:
    - 200: Container list with metadata
    - 500: Server error

GET /api/containers/{container_id}:
  description: Get specific container details
  response:
    - 200: Container details
    - 404: Container not found
```

#### 4.2.2 Health Monitoring
```yaml
GET /health:
  description: Basic health check
  response:
    - 200: {"status": "healthy"}
    - 503: Service unavailable

GET /health/detailed:
  description: Detailed component health
  response:
    - 200: Component health statuses
```

#### 4.2.3 Version Information
```yaml
GET /api/version:
  description: Application version info
  response:
    - 200: Version, build date, git commit
```

### 4.3 Response Format
```json
{
    "status": "success|error",
    "data": {
        // Response payload
    },
    "message": "Human-readable message",
    "timestamp": "2024-01-14T12:00:00Z"
}
```

## 5. Data Models

### 5.1 Container Model
```python
class Container(BaseModel):
    id: str
    name: str
    host: str
    status: str  # running, stopped, paused
    image: str
    created: datetime
    labels: Dict[str, str]
    revp_config: Optional[RevPConfig]
```

### 5.2 RevP Configuration Model
```python
class RevPConfig(BaseModel):
    domain: str
    backend_host: str
    backend_port: int
    backend_scheme: str = "http"
    additional_labels: Dict[str, str]
```

### 5.3 Health Status Model
```python
class HealthStatus(BaseModel):
    component: str
    status: Literal["healthy", "degraded", "unhealthy"]
    last_check: datetime
    message: Optional[str]
    metadata: Dict[str, Any]
```

## 6. Frontend Architecture

### 6.1 Component Structure
```
/static/
├── css/
│   └── dashboard.css    # All styles
├── js/
│   └── dashboard.js     # All JavaScript
├── images/
│   └── favicon.ico
└── index.html          # Main template
```

### 6.2 State Management
```javascript
class Dashboard {
    // Centralized state
    state = {
        currentTab: 'summary',
        containers: [],
        healthData: {},
        filters: {
            showRevP: true,
            showNonRevP: true,
            selectedHost: ''
        },
        theme: 'light'
    };
    
    // State update method
    updateState(updates) {
        this.state = { ...this.state, ...updates };
        this.render();
    }
}
```

### 6.3 Event Handling
```javascript
// Event delegation pattern
document.addEventListener('click', (e) => {
    if (e.target.matches('.tab-button')) {
        this.switchTab(e.target.dataset.tab);
    }
    if (e.target.matches('.expand-button')) {
        this.toggleContainerDetails(e.target);
    }
});
```

## 7. Security Design

### 7.1 Authentication & Authorization
- **API Key Authentication**: Header-based API keys
- **Session Management**: Secure cookie handling
- **CORS Configuration**: Restrictive CORS policies

### 7.2 Input Validation
```python
# Pydantic validation example
class ContainerFilter(BaseModel):
    host: Optional[str] = Field(None, max_length=255)
    status: Optional[Literal["running", "stopped", "paused"]]
    revp_only: Optional[bool] = False
    
    @validator('host')
    def validate_host(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9.-]+$', v):
            raise ValueError('Invalid host format')
        return v
```

### 7.3 Security Headers
```python
# FastAPI middleware for security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

## 8. Performance Considerations

### 8.1 Frontend Performance
- **Lazy Loading**: Load tab content on demand
- **Debouncing**: Search and filter inputs
- **Virtual Scrolling**: For large container lists
- **Efficient DOM Updates**: Minimal reflows/repaints

### 8.2 Backend Performance
- **Async Operations**: Non-blocking I/O
- **Connection Pooling**: Reuse SSH/Docker connections
- **Caching Strategy**: In-memory caching for frequent queries
- **Pagination**: Limit response sizes

### 8.3 Optimization Techniques
```python
# Caching example
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_container_data(host: str, cache_time: int):
    # Cache based on host and time window
    return fetch_containers_from_host(host)

# Call with 5-minute cache windows
current_window = int(datetime.now().timestamp() / 300)
data = get_container_data(host, current_window)
```

## 9. Deployment Architecture

### 9.1 Container Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  revp-dashboard:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REVP_API_KEY=${REVP_API_KEY}
      - REVP_HOSTS=${REVP_HOSTS}
    volumes:
      - ./config:/app/config
      - ~/.ssh:/root/.ssh:ro
    restart: unless-stopped
```

### 9.2 Production Configuration
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 10. Monitoring and Observability

### 10.1 Logging Strategy
```python
# Structured logging configuration
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_object = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_object)
```

### 10.2 Metrics Collection
- **Response Times**: API endpoint latencies
- **Error Rates**: 4xx/5xx response tracking
- **Container Metrics**: Count, status distribution
- **Resource Usage**: CPU, memory, connections

### 10.3 Health Monitoring
```python
# Health check implementation
async def detailed_health_check():
    checks = {
        'docker_monitor': check_docker_connectivity(),
        'caddy_manager': check_caddy_health(),
        'ssh_connections': check_ssh_connectivity(),
        'database': check_database_connection()
    }
    
    return {
        'status': 'healthy' if all(checks.values()) else 'degraded',
        'components': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
```

## 11. Testing Strategy

### 11.1 Unit Testing
```python
# Example unit test
import pytest
from src.api.containers import parse_container_labels

def test_parse_revp_labels():
    labels = {
        'snadboy.revp.domain': 'example.com',
        'snadboy.revp.backend-port': '3000'
    }
    result = parse_container_labels(labels)
    assert result.domain == 'example.com'
    assert result.backend_port == 3000
```

### 11.2 Integration Testing
- **API Testing**: Full request/response cycles
- **Service Testing**: Docker/Caddy integration
- **End-to-End Testing**: Frontend to backend flows

### 11.3 Performance Testing
- **Load Testing**: Concurrent user simulation
- **Stress Testing**: Resource limit validation
- **Benchmark Testing**: Response time baselines

## 12. Development Guidelines

### 12.1 Code Style
- **Python**: PEP 8 compliance, type hints
- **JavaScript**: ESLint configuration
- **CSS**: BEM methodology for class naming

### 12.2 Git Workflow
- **Branch Strategy**: Feature branches from main
- **Commit Messages**: Conventional commits format
- **Code Review**: Required for all changes

### 12.3 Documentation Standards
- **Code Comments**: Docstrings for all public methods
- **API Documentation**: OpenAPI/Swagger specs
- **README Updates**: Keep in sync with changes

## 13. Maintenance and Operations

### 13.1 Backup Strategy
- **Configuration Backup**: Version controlled
- **Data Backup**: Container metadata caching
- **Recovery Procedures**: Documented runbooks

### 13.2 Update Procedures
- **Rolling Updates**: Zero-downtime deployments
- **Version Migration**: Database schema updates
- **Rollback Plan**: Previous version restoration

### 13.3 Troubleshooting Guide
- **Common Issues**: Connection failures, permissions
- **Debug Mode**: Enhanced logging activation
- **Support Tools**: Health check scripts

---

*This Technical Design Document provides the comprehensive technical foundation for implementing and maintaining the Docker RevP Dashboard.*