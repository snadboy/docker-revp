# Docker Monitor Component Specification

## 1. Component Overview

### 1.1 Purpose
The Docker Monitor is a core service component responsible for discovering, monitoring, and managing Docker containers across multiple hosts. It provides real-time container state tracking, resource monitoring, and RevP label detection.

### 1.2 Key Responsibilities
- Multi-host Docker daemon connectivity
- Container discovery and state monitoring
- RevP label parsing and validation
- Resource usage collection
- Event stream processing
- Health status aggregation

### 1.3 Component Architecture
```
┌─────────────────────────────────────────────────┐
│              Docker Monitor Service              │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐            │
│  │  Host       │  │   Container  │            │
│  │  Manager    │  │   Tracker    │            │
│  └──────┬──────┘  └──────┬───────┘            │
│         │                │                      │
│  ┌──────▼──────┐  ┌──────▼───────┐            │
│  │  Docker     │  │    Event     │            │
│  │  Client     │  │   Processor  │            │
│  │  Factory    │  │              │            │
│  └──────┬──────┘  └──────┬───────┘            │
│         │                │                      │
│  ┌──────▼────────────────▼───────┐            │
│  │        Connection Pool         │            │
│  └────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
                    │
                    ▼
        Docker Daemons (Multiple Hosts)
```

## 2. Technical Architecture

### 2.1 Core Components

#### 2.1.1 Host Manager
```python
class HostManager:
    """Manages Docker host connections and health"""
    
    def __init__(self, hosts: List[HostConfig]):
        self.hosts = hosts
        self.connections = {}
        self.health_status = {}
        
    async def connect_all(self):
        """Establish connections to all configured hosts"""
        
    async def check_host_health(self, host: str) -> HostHealth:
        """Check health status of a specific host"""
        
    def get_active_hosts(self) -> List[str]:
        """Return list of currently active hosts"""
```

#### 2.1.2 Docker Client Factory
```python
class DockerClientFactory:
    """Factory for creating Docker clients with proper configuration"""
    
    @staticmethod
    def create_client(host_config: HostConfig) -> DockerClient:
        """Create Docker client for specific host"""
        
    @staticmethod
    def create_ssh_client(host_config: HostConfig) -> SSHDockerClient:
        """Create SSH-tunneled Docker client"""
        
    @staticmethod
    def create_local_client() -> DockerClient:
        """Create client for local Docker daemon"""
```

#### 2.1.3 Container Tracker
```python
class ContainerTracker:
    """Tracks container states and changes"""
    
    def __init__(self):
        self.containers = {}  # container_id -> ContainerInfo
        self.last_update = {}
        
    async def discover_containers(self, client: DockerClient, host: str):
        """Discover all containers on a host"""
        
    async def update_container_state(self, container_id: str, state: dict):
        """Update state for specific container"""
        
    def get_revp_containers(self) -> List[ContainerInfo]:
        """Get all containers with RevP labels"""
```

#### 2.1.4 Event Processor
```python
class EventProcessor:
    """Processes Docker events in real-time"""
    
    async def start_event_stream(self, client: DockerClient, host: str):
        """Start processing events from Docker daemon"""
        
    async def handle_event(self, event: DockerEvent):
        """Process individual Docker event"""
        
    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type"""
```

### 2.2 Data Models

#### 2.2.1 Host Configuration
```python
@dataclass
class HostConfig:
    hostname: str
    connection_type: Literal["local", "ssh", "tcp"]
    ssh_config: Optional[SSHConfig] = None
    tcp_config: Optional[TCPConfig] = None
    labels: Dict[str, str] = field(default_factory=dict)
    
@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str
    key_path: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    
@dataclass
class TCPConfig:
    host: str
    port: int = 2376
    tls_verify: bool = False
    cert_path: Optional[str] = None
```

#### 2.2.2 Container Information
```python
@dataclass
class ContainerInfo:
    id: str
    name: str
    host: str
    image: str
    status: ContainerStatus
    state: ContainerState
    created: datetime
    started: Optional[datetime]
    labels: Dict[str, str]
    ports: List[PortMapping]
    networks: List[str]
    mounts: List[MountPoint]
    environment: List[str]
    revp_config: Optional[RevPConfig]
    
@dataclass
class ContainerState:
    status: str  # running, paused, stopped
    running: bool
    paused: bool
    restarting: bool
    oom_killed: bool
    dead: bool
    pid: int
    exit_code: int
    error: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
```

#### 2.2.3 RevP Configuration
```python
@dataclass
class RevPConfig:
    enabled: bool
    domain: str
    backend_host: str = "localhost"
    backend_port: int = 80
    backend_scheme: str = "http"
    strip_prefix: bool = False
    load_balancer: Optional[str] = None
    health_check: Optional[HealthCheckConfig] = None
    additional_labels: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_labels(cls, labels: Dict[str, str]) -> Optional['RevPConfig']:
        """Parse RevP config from container labels"""
        prefix = "snadboy.revp"
        if f"{prefix}.domain" not in labels:
            return None
            
        return cls(
            enabled=True,
            domain=labels[f"{prefix}.domain"],
            backend_port=int(labels.get(f"{prefix}.backend-port", 80)),
            backend_scheme=labels.get(f"{prefix}.backend-scheme", "http"),
            # ... parse other labels
        )
```

### 2.3 Connection Management

#### 2.3.1 Connection Pool
```python
class ConnectionPool:
    """Manages Docker client connections with pooling"""
    
    def __init__(self, max_connections: int = 10):
        self.pool = {}
        self.semaphore = asyncio.Semaphore(max_connections)
        
    async def get_connection(self, host: str) -> DockerClient:
        """Get connection from pool or create new"""
        
    async def release_connection(self, host: str, client: DockerClient):
        """Return connection to pool"""
        
    async def close_all(self):
        """Close all connections in pool"""
```

#### 2.3.2 SSH Tunnel Management
```python
class SSHTunnelManager:
    """Manages SSH tunnels for remote Docker access"""
    
    async def create_tunnel(self, ssh_config: SSHConfig) -> SSHTunnel:
        """Create SSH tunnel to remote Docker daemon"""
        
    async def get_docker_client(self, tunnel: SSHTunnel) -> DockerClient:
        """Get Docker client through SSH tunnel"""
        
    async def close_tunnel(self, tunnel: SSHTunnel):
        """Close SSH tunnel and cleanup"""
```

### 2.4 Monitoring Operations

#### 2.4.1 Container Discovery
```python
async def discover_all_containers(self) -> List[ContainerInfo]:
    """Discover containers across all hosts"""
    tasks = []
    for host in self.host_manager.get_active_hosts():
        client = await self.connection_pool.get_connection(host)
        tasks.append(self._discover_host_containers(client, host))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return self._merge_container_results(results)

async def _discover_host_containers(self, client: DockerClient, host: str):
    """Discover containers on specific host"""
    containers = await client.containers.list(all=True)
    return [self._parse_container(c, host) for c in containers]
```

#### 2.4.2 Real-time Monitoring
```python
async def start_monitoring(self):
    """Start real-time monitoring of all hosts"""
    for host in self.host_manager.get_active_hosts():
        asyncio.create_task(self._monitor_host(host))
    
async def _monitor_host(self, host: str):
    """Monitor single host for events"""
    client = await self.connection_pool.get_connection(host)
    async for event in client.events.stream():
        await self.event_processor.handle_event(event, host)
```

#### 2.4.3 Resource Monitoring
```python
async def collect_container_stats(self, container_id: str) -> ContainerStats:
    """Collect resource usage statistics for container"""
    container = await self.get_container(container_id)
    stats = await container.stats(stream=False)
    
    return ContainerStats(
        cpu_usage=self._calculate_cpu_percent(stats),
        memory_usage=stats['memory_stats']['usage'],
        memory_limit=stats['memory_stats']['limit'],
        network_rx=sum(v['rx_bytes'] for v in stats['networks'].values()),
        network_tx=sum(v['tx_bytes'] for v in stats['networks'].values()),
        block_io_read=self._sum_block_io(stats['blkio_stats'], 'read'),
        block_io_write=self._sum_block_io(stats['blkio_stats'], 'write')
    )
```

### 2.5 Event Processing

#### 2.5.1 Event Types
```python
class DockerEventType(Enum):
    # Container events
    CONTAINER_CREATE = "container.create"
    CONTAINER_START = "container.start"
    CONTAINER_STOP = "container.stop"
    CONTAINER_RESTART = "container.restart"
    CONTAINER_KILL = "container.kill"
    CONTAINER_DIE = "container.die"
    CONTAINER_PAUSE = "container.pause"
    CONTAINER_UNPAUSE = "container.unpause"
    CONTAINER_DELETE = "container.delete"
    
    # Image events
    IMAGE_PULL = "image.pull"
    IMAGE_PUSH = "image.push"
    IMAGE_DELETE = "image.delete"
    
    # Network events
    NETWORK_CREATE = "network.create"
    NETWORK_DELETE = "network.delete"
    NETWORK_CONNECT = "network.connect"
    NETWORK_DISCONNECT = "network.disconnect"
```

#### 2.5.2 Event Handlers
```python
class EventHandlers:
    """Container for Docker event handlers"""
    
    async def handle_container_start(self, event: DockerEvent):
        """Handle container start event"""
        container_id = event['id']
        await self.container_tracker.update_container_state(
            container_id, 
            {'status': 'running', 'started_at': event['time']}
        )
        await self.notify_listeners('container.started', container_id)
    
    async def handle_container_die(self, event: DockerEvent):
        """Handle container die event"""
        container_id = event['id']
        exit_code = event['Actor']['Attributes'].get('exitCode', -1)
        await self.container_tracker.update_container_state(
            container_id,
            {'status': 'stopped', 'exit_code': exit_code}
        )
```

### 2.6 Health Monitoring

#### 2.6.1 Health Check Implementation
```python
class HealthChecker:
    """Performs health checks on Docker hosts and containers"""
    
    async def check_host_health(self, host: str) -> HostHealth:
        """Check health of Docker host"""
        try:
            client = await self.connection_pool.get_connection(host)
            info = await client.info()
            ping = await client.ping()
            
            return HostHealth(
                host=host,
                status='healthy' if ping else 'unhealthy',
                docker_version=info['ServerVersion'],
                containers_running=info['ContainersRunning'],
                containers_total=info['Containers'],
                response_time_ms=self._measure_response_time()
            )
        except Exception as e:
            return HostHealth(
                host=host,
                status='unhealthy',
                error=str(e)
            )
    
    async def check_container_health(self, container_id: str) -> ContainerHealth:
        """Check health of specific container"""
        container = await self.get_container(container_id)
        
        # Docker health check
        health = container.attrs.get('State', {}).get('Health')
        if health:
            return ContainerHealth(
                container_id=container_id,
                status=health['Status'],
                failing_streak=health.get('FailingStreak', 0),
                log=health.get('Log', [])
            )
        
        # Basic health based on status
        return ContainerHealth(
            container_id=container_id,
            status='healthy' if container.status == 'running' else 'unhealthy'
        )
```

### 2.7 Performance Optimization

#### 2.7.1 Caching Strategy
```python
class ContainerCache:
    """LRU cache for container information"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        
    def get(self, key: str) -> Optional[ContainerInfo]:
        """Get container from cache if not expired"""
        if key in self.cache:
            entry, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return entry
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: ContainerInfo):
        """Add container to cache"""
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
```

#### 2.7.2 Batch Operations
```python
async def batch_container_operations(self, operations: List[ContainerOperation]):
    """Execute container operations in batches"""
    batch_size = 10
    results = []
    
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[self._execute_operation(op) for op in batch],
            return_exceptions=True
        )
        results.extend(batch_results)
    
    return results
```

### 2.8 Error Handling

#### 2.8.1 Error Types
```python
class DockerMonitorError(Exception):
    """Base exception for Docker Monitor"""

class ConnectionError(DockerMonitorError):
    """Failed to connect to Docker daemon"""

class AuthenticationError(DockerMonitorError):
    """Authentication failed"""

class ContainerNotFoundError(DockerMonitorError):
    """Container does not exist"""

class HostUnreachableError(DockerMonitorError):
    """Cannot reach Docker host"""
```

#### 2.8.2 Retry Logic
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ConnectionError)
)
async def connect_with_retry(self, host_config: HostConfig):
    """Connect to Docker host with retry logic"""
    return await self._create_connection(host_config)
```

### 2.9 Configuration

#### 2.9.1 Monitor Configuration
```python
@dataclass
class MonitorConfig:
    # Connection settings
    connection_timeout: int = 30
    max_connections_per_host: int = 5
    connection_pool_size: int = 20
    
    # Monitoring settings
    discovery_interval: int = 60  # seconds
    stats_collection_interval: int = 30
    event_buffer_size: int = 1000
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 300
    cache_max_size: int = 1000
    
    # Performance settings
    batch_size: int = 10
    max_concurrent_operations: int = 50
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 2
    retry_backoff: float = 2.0
```

### 2.10 Monitoring Metrics

#### 2.10.1 Metrics Collection
```python
class MonitorMetrics:
    """Collects and exposes monitoring metrics"""
    
    def __init__(self):
        self.metrics = {
            'containers_discovered': Counter(),
            'events_processed': Counter(),
            'connection_errors': Counter(),
            'api_calls': Histogram(),
            'discovery_duration': Histogram(),
            'active_connections': Gauge()
        }
    
    def record_container_discovered(self, host: str):
        self.metrics['containers_discovered'].inc({'host': host})
    
    def record_api_call(self, endpoint: str, duration: float):
        self.metrics['api_calls'].observe(duration, {'endpoint': endpoint})
```

### 2.11 Integration Points

#### 2.11.1 API Integration
```python
class DockerMonitorAPI:
    """API endpoints for Docker Monitor"""
    
    async def get_containers(self, filters: ContainerFilters) -> List[ContainerInfo]:
        """Get containers matching filters"""
        
    async def get_container_stats(self, container_id: str) -> ContainerStats:
        """Get real-time stats for container"""
        
    async def get_host_status(self, host: str) -> HostHealth:
        """Get health status of specific host"""
```

#### 2.11.2 Event Streaming
```python
class EventStream:
    """WebSocket event streaming"""
    
    async def stream_events(self, websocket: WebSocket, filters: EventFilters):
        """Stream Docker events via WebSocket"""
        async for event in self.event_processor.get_filtered_events(filters):
            await websocket.send_json({
                'type': 'docker_event',
                'data': event
            })
```

---

*This specification defines the complete technical implementation of the Docker Monitor component for the RevP Dashboard system.*