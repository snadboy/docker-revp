# API Specification: Docker RevP Dashboard

## 1. Overview

### 1.1 API Description
The Docker RevP Dashboard API provides RESTful endpoints for container monitoring, health checks, and reverse proxy configuration management. This specification defines all API endpoints, request/response formats, authentication mechanisms, and error handling.

### 1.2 Base URL
```
Production: https://revp-dashboard.example.com/api
Development: http://localhost:8000/api
```

### 1.3 API Version
Current Version: `v1`

## 2. Authentication

### 2.1 API Key Authentication
All API requests require authentication via API key in the request header.

```http
Authorization: Bearer {API_KEY}
X-API-Key: {API_KEY}
```

### 2.2 Authentication Errors
```json
{
    "status": "error",
    "message": "Unauthorized",
    "code": "AUTH_001",
    "timestamp": "2024-01-14T12:00:00Z"
}
```

## 3. Common Standards

### 3.1 Request Headers
```http
Content-Type: application/json
Accept: application/json
X-Request-ID: {UUID}
```

### 3.2 Response Headers
```http
Content-Type: application/json
X-Request-ID: {UUID}
X-Rate-Limit-Limit: 1000
X-Rate-Limit-Remaining: 999
X-Rate-Limit-Reset: 1642176000
```

### 3.3 Standard Response Format
```json
{
    "status": "success|error",
    "data": {},
    "message": "Human-readable message",
    "timestamp": "2024-01-14T12:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3.4 Pagination
```json
{
    "data": [],
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total_pages": 10,
        "total_items": 500,
        "has_next": true,
        "has_prev": false
    }
}
```

### 3.5 Error Response Format
```json
{
    "status": "error",
    "error": {
        "code": "ERR_001",
        "message": "Validation failed",
        "details": {
            "field": "container_id",
            "reason": "Invalid format"
        }
    },
    "timestamp": "2024-01-14T12:00:00Z"
}
```

## 4. Endpoints

### 4.1 Container Management

#### 4.1.1 List All Containers
```yaml
GET /api/v1/containers

Description: Retrieve all containers across monitored hosts

Query Parameters:
  - host: string (optional) - Filter by specific host
  - status: string (optional) - Filter by status (running|stopped|paused)
  - revp_enabled: boolean (optional) - Filter RevP-enabled containers
  - search: string (optional) - Search in container names
  - page: integer (optional, default: 1) - Page number
  - per_page: integer (optional, default: 50) - Items per page

Response: 200 OK
{
    "status": "success",
    "data": [
        {
            "id": "abc123def456",
            "name": "web-app",
            "host": "server-01",
            "status": "running",
            "image": "nginx:latest",
            "created": "2024-01-14T10:00:00Z",
            "ports": ["80/tcp", "443/tcp"],
            "labels": {
                "snadboy.revp.domain": "app.example.com",
                "snadboy.revp.backend-port": "3000",
                "snadboy.revp.backend-scheme": "http"
            },
            "revp_config": {
                "enabled": true,
                "domain": "app.example.com",
                "backend": "http://localhost:3000"
            }
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total_pages": 3,
        "total_items": 127
    }
}

Error Responses:
  - 400: Bad Request - Invalid query parameters
  - 401: Unauthorized - Missing or invalid API key
  - 500: Internal Server Error
```

#### 4.1.2 Get Container Details
```yaml
GET /api/v1/containers/{container_id}

Description: Retrieve detailed information about a specific container

Path Parameters:
  - container_id: string (required) - Container ID

Response: 200 OK
{
    "status": "success",
    "data": {
        "id": "abc123def456",
        "name": "web-app",
        "host": "server-01",
        "status": "running",
        "image": "nginx:latest",
        "created": "2024-01-14T10:00:00Z",
        "started": "2024-01-14T10:01:00Z",
        "ports": ["80/tcp", "443/tcp"],
        "environment": [
            "NODE_ENV=production",
            "PORT=3000"
        ],
        "mounts": [
            {
                "source": "/host/path",
                "destination": "/container/path",
                "mode": "rw"
            }
        ],
        "networks": ["bridge", "custom-network"],
        "labels": {
            "snadboy.revp.domain": "app.example.com",
            "snadboy.revp.backend-port": "3000"
        },
        "revp_config": {
            "enabled": true,
            "domain": "app.example.com",
            "backend": "http://localhost:3000",
            "ssl": true,
            "headers": {
                "X-Real-IP": "$remote_addr"
            }
        },
        "stats": {
            "cpu_usage": 15.5,
            "memory_usage": 256,
            "memory_limit": 512,
            "network_rx": 1024000,
            "network_tx": 512000
        }
    }
}

Error Responses:
  - 404: Not Found - Container does not exist
  - 401: Unauthorized
  - 500: Internal Server Error
```

#### 4.1.3 Get Container Logs
```yaml
GET /api/v1/containers/{container_id}/logs

Description: Retrieve container logs

Path Parameters:
  - container_id: string (required)

Query Parameters:
  - tail: integer (optional, default: 100) - Number of lines
  - since: string (optional) - RFC3339 timestamp
  - until: string (optional) - RFC3339 timestamp
  - timestamps: boolean (optional, default: true)
  - stderr: boolean (optional, default: true)
  - stdout: boolean (optional, default: true)

Response: 200 OK
{
    "status": "success",
    "data": {
        "container_id": "abc123def456",
        "logs": [
            {
                "timestamp": "2024-01-14T12:00:00Z",
                "stream": "stdout",
                "message": "Server started on port 3000"
            }
        ],
        "total_lines": 100
    }
}
```

### 4.2 Health Monitoring

#### 4.2.1 Basic Health Check
```yaml
GET /api/v1/health

Description: Simple health check endpoint

Response: 200 OK
{
    "status": "healthy",
    "timestamp": "2024-01-14T12:00:00Z"
}

Error Response: 503 Service Unavailable
{
    "status": "unhealthy",
    "timestamp": "2024-01-14T12:00:00Z"
}
```

#### 4.2.2 Detailed Health Status
```yaml
GET /api/v1/health/detailed

Description: Comprehensive health check of all components

Response: 200 OK
{
    "status": "success",
    "data": {
        "overall_status": "healthy",
        "components": {
            "docker_monitor": {
                "status": "healthy",
                "message": "All Docker hosts responsive",
                "last_check": "2024-01-14T12:00:00Z",
                "details": {
                    "total_hosts": 3,
                    "healthy_hosts": 3,
                    "response_time_ms": 45
                }
            },
            "caddy_manager": {
                "status": "healthy",
                "message": "Caddy API responsive",
                "last_check": "2024-01-14T12:00:00Z",
                "details": {
                    "version": "2.7.0",
                    "uptime_seconds": 86400,
                    "active_routes": 15
                }
            },
            "ssh_connections": {
                "status": "degraded",
                "message": "1 host unreachable",
                "last_check": "2024-01-14T12:00:00Z",
                "details": {
                    "total_hosts": 3,
                    "connected_hosts": 2,
                    "failed_hosts": ["server-03"]
                }
            },
            "api_service": {
                "status": "healthy",
                "message": "API functioning normally",
                "last_check": "2024-01-14T12:00:00Z",
                "details": {
                    "uptime_seconds": 3600,
                    "request_rate": 150,
                    "error_rate": 0.01
                }
            }
        }
    }
}
```

### 4.3 Host Management

#### 4.3.1 List Monitored Hosts
```yaml
GET /api/v1/hosts

Description: Get all monitored Docker hosts

Response: 200 OK
{
    "status": "success",
    "data": [
        {
            "hostname": "server-01",
            "ip_address": "192.168.1.10",
            "status": "online",
            "docker_version": "24.0.5",
            "container_count": 15,
            "revp_container_count": 8,
            "last_seen": "2024-01-14T12:00:00Z",
            "resources": {
                "cpu_usage": 45.2,
                "memory_usage": 8192,
                "memory_total": 16384,
                "disk_usage": 50.5
            }
        }
    ]
}
```

#### 4.3.2 Get Host Details
```yaml
GET /api/v1/hosts/{hostname}

Description: Get detailed information about a specific host

Response: 200 OK
{
    "status": "success",
    "data": {
        "hostname": "server-01",
        "ip_address": "192.168.1.10",
        "status": "online",
        "docker_info": {
            "version": "24.0.5",
            "api_version": "1.43",
            "os": "Ubuntu 22.04",
            "kernel": "5.15.0-88-generic",
            "architecture": "x86_64",
            "total_memory": 16384,
            "cpus": 8
        },
        "containers": {
            "total": 15,
            "running": 12,
            "stopped": 3,
            "paused": 0
        },
        "ssh_config": {
            "port": 22,
            "user": "docker",
            "key_fingerprint": "SHA256:..."
        }
    }
}
```

### 4.4 Configuration Management

#### 4.4.1 Get RevP Configuration
```yaml
GET /api/v1/config/revp

Description: Retrieve current RevP label configuration

Response: 200 OK
{
    "status": "success",
    "data": {
        "label_prefix": "snadboy.revp",
        "supported_labels": [
            {
                "name": "domain",
                "required": true,
                "description": "Domain name for reverse proxy"
            },
            {
                "name": "backend-port",
                "required": false,
                "default": "80",
                "description": "Backend service port"
            },
            {
                "name": "backend-scheme",
                "required": false,
                "default": "http",
                "values": ["http", "https"],
                "description": "Backend protocol"
            }
        ],
        "caddy_template": "..."
    }
}
```

### 4.5 Metrics and Statistics

#### 4.5.1 Get Dashboard Metrics
```yaml
GET /api/v1/metrics

Description: Retrieve dashboard usage and performance metrics

Query Parameters:
  - period: string (optional) - Time period (1h|24h|7d|30d)

Response: 200 OK
{
    "status": "success",
    "data": {
        "period": "24h",
        "container_metrics": {
            "total_containers": 45,
            "revp_enabled": 23,
            "by_status": {
                "running": 40,
                "stopped": 5
            },
            "by_host": {
                "server-01": 15,
                "server-02": 20,
                "server-03": 10
            }
        },
        "api_metrics": {
            "total_requests": 15420,
            "avg_response_time_ms": 125,
            "error_rate": 0.02,
            "requests_by_endpoint": {
                "/api/v1/containers": 8500,
                "/api/v1/health": 5000
            }
        },
        "system_metrics": {
            "uptime_hours": 168,
            "cpu_usage_avg": 25.5,
            "memory_usage_avg": 512
        }
    }
}
```

### 4.6 WebSocket Endpoints

#### 4.6.1 Real-time Container Updates
```yaml
WS /api/v1/ws/containers

Description: WebSocket endpoint for real-time container status updates

Connection:
  URL: ws://localhost:8000/api/v1/ws/containers
  Headers:
    - Authorization: Bearer {API_KEY}

Messages from Server:
{
    "type": "container_update",
    "data": {
        "container_id": "abc123",
        "action": "status_change",
        "old_status": "running",
        "new_status": "stopped",
        "timestamp": "2024-01-14T12:00:00Z"
    }
}

Messages to Server:
{
    "type": "subscribe",
    "filters": {
        "hosts": ["server-01"],
        "status": ["running"]
    }
}
```

## 5. Error Codes

### 5.1 Client Errors (4xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| AUTH_001 | 401 | Missing authentication |
| AUTH_002 | 401 | Invalid API key |
| AUTH_003 | 403 | Insufficient permissions |
| VAL_001 | 400 | Invalid request format |
| VAL_002 | 400 | Missing required parameter |
| VAL_003 | 400 | Invalid parameter value |
| RES_001 | 404 | Resource not found |
| RATE_001 | 429 | Rate limit exceeded |

### 5.2 Server Errors (5xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| SRV_001 | 500 | Internal server error |
| SRV_002 | 502 | Docker daemon unreachable |
| SRV_003 | 502 | SSH connection failed |
| SRV_004 | 503 | Service temporarily unavailable |
| SRV_005 | 504 | Gateway timeout |

## 6. Rate Limiting

### 6.1 Limits
- Default: 1000 requests per hour per API key
- Burst: 50 requests per minute
- WebSocket connections: 10 concurrent per API key

### 6.2 Rate Limit Headers
```http
X-Rate-Limit-Limit: 1000
X-Rate-Limit-Remaining: 999
X-Rate-Limit-Reset: 1642176000
X-Rate-Limit-Burst-Limit: 50
X-Rate-Limit-Burst-Remaining: 49
```

### 6.3 Rate Limit Exceeded Response
```json
{
    "status": "error",
    "error": {
        "code": "RATE_001",
        "message": "Rate limit exceeded",
        "retry_after": 3600
    }
}
```

## 7. API Versioning

### 7.1 Version Strategy
- URL path versioning: `/api/v1/`, `/api/v2/`
- Backward compatibility maintained for 6 months
- Deprecation notices via headers and documentation

### 7.2 Version Header
```http
X-API-Version: v1
X-API-Deprecated: false
X-API-Sunset-Date: 2025-01-14
```

## 8. CORS Configuration

### 8.1 Allowed Origins
```
Production: https://revp-dashboard.example.com
Development: http://localhost:3000
```

### 8.2 CORS Headers
```http
Access-Control-Allow-Origin: https://revp-dashboard.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key
Access-Control-Max-Age: 86400
```

## 9. API Testing

### 9.1 Test Endpoints
```yaml
GET /api/v1/test/echo
POST /api/v1/test/echo
```

### 9.2 Postman Collection
Available at: `/docs/postman-collection.json`

### 9.3 OpenAPI Specification
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

---

*This API Specification serves as the contract between the Docker RevP Dashboard frontend and backend services.*