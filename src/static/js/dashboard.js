// Sortable Resizable Table Widget
class SortableResizableTable {
    constructor(tableSelector, options = {}) {
        this.tableSelector = tableSelector;
        this.table = document.querySelector(tableSelector);
        this.options = {
            hasExpandColumn: options.hasExpandColumn || false,
            sortCallback: options.sortCallback || null,
            columns: options.columns || [],
            ...options
        };
        
        // State
        this.currentSort = { column: null, direction: 'asc' };
        this.isResizing = false;
        this.currentResizer = null;
        this.currentHeader = null;
        this.startX = 0;
        this.startWidth = 0;
        
        // Register this instance
        SortableResizableTable.instances.push(this);
        
        this.init();
    }
    
    init() {
        if (!this.table) {
            console.warn(`Table not found: ${this.tableSelector}`);
            return;
        }
        
        this.setupSorting();
        this.setupResizing();
    }
    
    setupSorting() {
        const sortableHeaders = this.table.querySelectorAll('th.sortable');
        
        sortableHeaders.forEach(header => {
            header.addEventListener('click', (e) => {
                // Don't sort if we're clicking on a resizer
                if (e.target.classList.contains('column-resizer')) return;
                
                const sortKey = header.dataset.sort;
                if (!sortKey) return;
                
                // Update sort direction
                if (this.currentSort.column === sortKey) {
                    this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    this.currentSort.column = sortKey;
                    this.currentSort.direction = 'asc';
                }
                
                this.updateSortIndicators();
                
                // Call the sort callback
                if (this.options.sortCallback) {
                    this.options.sortCallback(this.currentSort.column, this.currentSort.direction);
                }
            });
        });
    }
    
    updateSortIndicators() {
        const headers = this.table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (header.dataset.sort === this.currentSort.column) {
                header.classList.add(this.currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    }
    
    setSortState(column, direction = 'asc') {
        this.currentSort.column = column;
        this.currentSort.direction = direction;
        this.updateSortIndicators();
        
        // Call the sort callback if provided
        if (this.options.sortCallback) {
            this.options.sortCallback(this.currentSort.column, this.currentSort.direction);
        }
    }
    
    setupResizing() {
        // Remove existing resizers
        const existingResizers = this.table.querySelectorAll('.column-resizer');
        existingResizers.forEach(resizer => resizer.remove());
        
        // Determine which headers to make resizable
        let selector = 'th:not(:last-child)'; // All except last column
        if (this.options.hasExpandColumn) {
            selector = 'th:not(:first-child):not(:last-child)'; // Skip first and last
        }
        
        const headers = this.table.querySelectorAll(selector);
        
        headers.forEach(header => {
            const resizer = document.createElement('div');
            resizer.className = 'column-resizer';
            header.appendChild(resizer);
            
            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.startResize(e, header, resizer);
            });
        });
        
        // Add global mouse events (only once)
        if (!SortableResizableTable.globalEventsAdded) {
            document.addEventListener('mousemove', (e) => this.handleGlobalMouseMove(e));
            document.addEventListener('mouseup', () => this.handleGlobalMouseUp());
            SortableResizableTable.globalEventsAdded = true;
        }
    }
    
    startResize(e, header, resizer) {
        this.isResizing = true;
        this.currentResizer = resizer;
        this.currentHeader = header;
        this.startX = e.pageX;
        this.startWidth = parseInt(document.defaultView.getComputedStyle(header).width, 10);
        
        const allHeaders = Array.from(this.table.querySelectorAll('th'));
        const targetColumnIndex = allHeaders.indexOf(header);
        
        // Lock widths for columns to the left
        for (let i = 0; i < targetColumnIndex; i++) {
            const leftHeader = allHeaders[i];
            const currentWidth = parseInt(document.defaultView.getComputedStyle(leftHeader).width, 10);
            leftHeader.style.width = currentWidth + 'px';
            
            // Also lock corresponding td widths
            const rows = this.table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cell = row.children[i];
                if (cell) {
                    cell.style.width = currentWidth + 'px';
                }
            });
        }
        
        // Set initial width for target column
        header.style.width = this.startWidth + 'px';
        const rows = this.table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cell = row.children[targetColumnIndex];
            if (cell) {
                cell.style.width = this.startWidth + 'px';
            }
        });
        
        resizer.classList.add('resizing');
        this.table.closest('.table-container').classList.add('resizing');
    }
    
    handleGlobalMouseMove(e) {
        // Find the active table widget
        const activeWidget = SortableResizableTable.instances.find(widget => widget.isResizing);
        if (activeWidget) {
            activeWidget.doResize(e);
        }
    }
    
    handleGlobalMouseUp() {
        // Find the active table widget and stop resizing
        const activeWidget = SortableResizableTable.instances.find(widget => widget.isResizing);
        if (activeWidget) {
            activeWidget.stopResize();
        }
    }
    
    doResize(e) {
        if (!this.isResizing || !this.currentHeader) return;
        
        const deltaX = e.pageX - this.startX;
        const newWidth = this.startWidth + deltaX;
        const minWidth = 80;
        
        if (newWidth < minWidth) return;
        
        this.currentHeader.style.width = newWidth + 'px';
        
        // Update corresponding td elements
        const allHeaders = Array.from(this.table.querySelectorAll('th'));
        const targetColumnIndex = allHeaders.indexOf(this.currentHeader);
        const rows = this.table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const cell = row.children[targetColumnIndex];
            if (cell) {
                cell.style.width = newWidth + 'px';
            }
        });
    }
    
    stopResize() {
        if (!this.isResizing) return;
        
        this.isResizing = false;
        
        if (this.currentResizer) {
            this.currentResizer.classList.remove('resizing');
            this.currentResizer = null;
        }
        
        this.currentHeader = null;
        this.table.closest('.table-container').classList.remove('resizing');
    }
    
    // Public methods
    setSortState(column, direction) {
        this.currentSort = { column, direction };
        this.updateSortIndicators();
    }
    
    getSortState() {
        return { ...this.currentSort };
    }
}

// Static properties for managing instances
SortableResizableTable.globalEventsAdded = false;
SortableResizableTable.instances = [];

// Dashboard JavaScript
class Dashboard {
    constructor() {
        this.currentTab = 'summary';
        this.containers = [];
        this.staticRoutes = [];
        this.healthData = {};
        this.summaryData = {};
        this.staticRoutesData = [];
        this.staticRoutesFileInfo = {};
        this.sortColumn = 'host'; // Default sort by host initially
        this.sortDirection = 'asc';
        this.expandedRows = new Set(); // Track expanded rows
        this.staticRoutesSortColumn = null;
        this.staticRoutesSortDirection = 'asc';
        
        // Table widgets
        this.containersTable = null;
        this.staticRoutesTable = null;
        this.hostsTable = null;
        
        // Hosts sorting state
        this.hostsSortColumn = null;
        this.hostsSortDirection = 'asc';
        
        this.init();
    }

    async init() {
        // Set up theme toggle
        this.setupThemeToggle();
        
        // Set up tab switching
        this.setupTabSwitching();
        
        // Set up basic event handlers immediately
        this.setupBasicEventHandlers();
        
        // Load initial data
        try {
            await this.loadSummaryData();
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
        
        // Set up periodic refresh
        setInterval(() => this.refreshCurrentTab(), 30000); // Refresh every 30 seconds
    }
    
    setupBasicEventHandlers() {
        // Set up expandable rows (if elements exist)
        const expandButtons = document.querySelectorAll('.expand-button');
        if (expandButtons.length > 0) {
            this.setupExpandableRows();
        }
    }

    // Theme Management
    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        const themeIcon = document.querySelector('.theme-icon');
        
        // Initialize theme based on system preference or saved preference
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        let currentTheme = savedTheme;
        if (!currentTheme) {
            currentTheme = systemPrefersDark ? 'dark' : 'light';
        }
        
        this.setTheme(currentTheme);
        
        // Theme toggle click handler
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                this.setTheme(newTheme);
                localStorage.setItem('theme', newTheme);
            });
        }
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
    
    setTheme(theme) {
        const themeIcon = document.querySelector('.theme-icon');
        document.documentElement.setAttribute('data-theme', theme);
        if (themeIcon) {
            themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }

    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.switchTab(tabName);
            });
        });
    }

    switchTab(tabName) {
        // Update active button
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update active panel
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // Load tab data
        this.currentTab = tabName;
        this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'summary':
                await this.loadSummaryData();
                break;
            case 'containers':
                await this.loadContainersData();
                break;
            case 'static-routes':
                await this.loadStaticRoutesData();
                break;
            case 'hosts':
                await this.loadHostsData();
                break;
            case 'health':
                await this.loadHealthData();
                break;
            case 'version':
                await this.loadVersionData();
                break;
            case 'about':
                await this.loadAboutData();
                break;
        }
    }

    async refreshCurrentTab() {
        // Store state before refresh
        if (this.currentTab === 'containers') {
            this.storeExpandedState();
        }
        
        await this.loadTabData(this.currentTab);
        
        // Restore state after refresh
        if (this.currentTab === 'containers') {
            this.restoreExpandedState();
        }
    }

    // Summary Tab
    async loadSummaryData() {
        try {
            const response = await fetch('/api/dashboard/summary');
            if (!response.ok) {
                console.warn('Summary API not available:', response.status);
                this.summaryData = this.getDefaultSummaryData();
            } else {
                this.summaryData = await response.json();
            }
            
            this.updateSummaryDisplay();
        } catch (error) {
            console.error('Error loading summary data:', error);
            this.summaryData = this.getDefaultSummaryData();
            this.updateSummaryDisplay();
        }
    }
    
    getDefaultSummaryData() {
        return {
            health: { status: 'unknown' },
            containers: { total: 0, with_revp: 0 },
            hosts: []
        };
    }

    updateSummaryDisplay() {
        const data = this.summaryData;
        
        // Update health status
        const healthStatus = document.getElementById('health-status');
        const healthText = document.getElementById('health-text');
        
        if (healthStatus && healthText) {
            const status = data.health?.status || 'unknown';
            healthStatus.className = `status-indicator ${status}`;
            healthText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
        
        // Update container counts
        const totalContainersEl = document.getElementById('total-containers');
        const revpContainersEl = document.getElementById('revp-containers');
        
        if (totalContainersEl) {
            totalContainersEl.textContent = data.containers?.total || 0;
        }
        if (revpContainersEl) {
            revpContainersEl.textContent = data.containers?.with_revp || 0;
        }
        
        // Update hosts list
        const hostsList = document.getElementById('hosts-list');
        if (hostsList) {
            hostsList.innerHTML = '';
            
            if (data.hosts && Array.isArray(data.hosts)) {
                data.hosts.forEach(host => {
                    const hostCard = document.createElement('div');
                    hostCard.className = 'host-card';
                    hostCard.innerHTML = `
                        <h4>${host.hostname}:${host.port}</h4>
                        <div class="host-stats">
                            <span>Total: ${host.container_count}</span>
                            <span>RevP: ${host.revp_count}</span>
                        </div>
                    `;
                    hostsList.appendChild(hostCard);
                });
            }
        }
    }


    // Containers Tab
    async loadContainersData() {
        try {
            const response = await fetch('/containers/all-services');
            if (!response.ok) {
                console.warn('Containers API not available:', response.status);
                this.containers = [];
                this.staticRoutes = [];
            } else {
                const data = await response.json();
                // Handle error responses from the API
                if (data.detail && data.detail.includes('not initialized')) {
                    console.warn('Docker monitor not initialized, using empty data');
                    this.containers = [];
                    this.staticRoutes = [];
                } else {
                    this.containers = Array.isArray(data.containers) ? data.containers : [];
                    this.staticRoutes = Array.isArray(data.static_routes) ? data.static_routes : [];
                }
            }
            
            this.updateContainersDisplay();
            this.setupContainerFilters();
            // Only set up table widget if not already initialized
            if (!this.containersTable) {
                this.containersTable = new SortableResizableTable('#containers-table', {
                    hasExpandColumn: true,
                    sortCallback: (sortKey, sortDirection) => {
                        this.sortColumn = sortKey;
                        this.sortDirection = sortDirection;
                        this.closeAllExpandedRows();
                        this.updateContainersDisplay();
                    }
                });
                
                // Set initial sort by host
                this.containersTable.setSortState('host', 'asc');
            }
        } catch (error) {
            console.error('Error loading containers data:', error);
            this.containers = [];
            this.updateContainersDisplay();
        }
    }

    updateContainersDisplay() {
        const tbody = document.querySelector('#containers-table tbody');
        if (!tbody) {
            console.error('Containers table body not found');
            return;
        }
        
        tbody.innerHTML = '';
        
        // Get filter states
        const filterRevp = document.getElementById('filter-revp');
        const filterNonRevp = document.getElementById('filter-non-revp');
        const hostFilterEl = document.getElementById('host-filter');
        
        const showRevp = filterRevp ? filterRevp.checked : true;
        const showNonRevp = filterNonRevp ? filterNonRevp.checked : true;
        const hostFilter = hostFilterEl ? hostFilterEl.value : '';
        
        // Filter containers
        let filteredContainers = this.containers.filter(container => {
            if (!showRevp && container.has_revp_config) return false;
            if (!showNonRevp && !container.has_revp_config) return false;
            if (hostFilter && container.host !== hostFilter) return false;
            return true;
        });
        
        // Sort containers if a sort column is selected
        if (this.sortColumn) {
            filteredContainers = this.sortContainers(filteredContainers);
        }
        
        // Display containers
        filteredContainers.forEach((container, index) => {
            // Main container row
            const row = document.createElement('tr');
            row.className = 'container-row';
            row.dataset.containerId = container.id;
            
            const revpBadge = container.has_revp_config
                ? '<span class="revp-badge enabled">Enabled</span>'
                : '<span class="revp-badge disabled">Disabled</span>';
            
            // Get domain and backend from services (multi-port support)
            let domain = '-';
            let backend = '-';
            
            if (container.has_revp_config && container.services && container.services.length > 0) {
                // Show the first service's domain and backend URL
                const firstService = container.services[0];
                domain = firstService.domain || '-';
                backend = firstService.backend_url || '-';
                
                // If multiple services, indicate that
                if (container.services.length > 1) {
                    domain += ` (+${container.services.length - 1} more)`;
                    backend += ` (+${container.services.length - 1} more)`;
                }
            }
            
            // Generate a unique ID if container.id is empty
            const containerId = container.id || `${container.name}_${container.host}`.replace(/[^a-zA-Z0-9]/g, '_');
            
            row.innerHTML = `
                <td><button class="expand-button" data-container-id="${containerId}">▶</button></td>
                <td title="${container.name}">${container.name}</td>
                <td title="${container.host}">${container.host}</td>
                <td title="${container.status}">${container.status}</td>
                <td title="${container.image}">${container.image}</td>
                <td>${revpBadge}</td>
                <td title="${domain}">${domain}</td>
                <td title="${backend}">${backend}</td>
            `;
            
            tbody.appendChild(row);
            
            // Labels row (initially hidden)
            const labelsRow = document.createElement('tr');
            labelsRow.className = 'labels-row';
            labelsRow.id = `labels-${containerId}`;
            
            const labelsCell = document.createElement('td');
            labelsCell.colSpan = 8;
            labelsCell.innerHTML = this.generateLabelsContent(container);
            labelsCell.style.padding = '0';
            
            labelsRow.appendChild(labelsCell);
            tbody.appendChild(labelsRow);
        });
        
        // Display static routes
        this.staticRoutes.forEach((route, index) => {
            const row = document.createElement('tr');
            row.className = 'container-row static-route-row';
            row.dataset.containerId = `static-${route.domain}`;
            
            const revpBadge = '<span class="revp-badge static">Static Route</span>';
            
            // Generate a unique ID for static routes
            const routeId = `static-${route.domain}`.replace(/[^a-zA-Z0-9]/g, '_');
            
            row.innerHTML = `
                <td><button class="expand-button" data-container-id="${routeId}">▶</button></td>
                <td title="Static Route">[Static Route]</td>
                <td title="External">External</td>
                <td title="Active">Active</td>
                <td title="Static Configuration">Static Configuration</td>
                <td>${revpBadge}</td>
                <td title="${route.domain}">${route.domain}</td>
                <td title="${route.backend_url}">${route.backend_url}</td>
            `;
            
            tbody.appendChild(row);
            
            // Labels row for static route (initially hidden)
            const labelsRow = document.createElement('tr');
            labelsRow.className = 'labels-row';
            labelsRow.id = `labels-${routeId}`;
            
            const labelsCell = document.createElement('td');
            labelsCell.colSpan = 8;
            labelsCell.innerHTML = this.generateStaticRouteContent(route);
            labelsCell.style.padding = '0';
            
            labelsRow.appendChild(labelsCell);
            tbody.appendChild(labelsRow);
        });
        
        // Set up expand/collapse functionality
        this.setupExpandableRows();
        
        // Restore expanded state after updating display
        this.restoreExpandedState();
    }
    
    generateLabelsContent(container) {
        let labelsHtml = '<div class="labels-content">';
        
        if (container.has_revp_config && container.services && container.services.length > 0) {
            labelsHtml += '<h4>RevP Services</h4>';
            
            container.services.forEach((service, index) => {
                labelsHtml += `<div class="service-section">`;
                labelsHtml += `<h5>Service ${index + 1} (Port ${service.port})</h5>`;
                labelsHtml += `<div class="labels-grid">`;
                
                // Display all service properties
                labelsHtml += `
                    <div class="label-item">
                        <span class="label-key">Domain:</span>
                        <span class="label-value">${service.domain || '(empty)'}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Container Port:</span>
                        <span class="label-value">${service.port}${service.resolved_host_port ? ` → ${service.resolved_host_port} (host)` : ''}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Backend URL:</span>
                        <span class="label-value">${service.backend_url || '-'}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Backend Protocol:</span>
                        <span class="label-value">${service.backend_proto}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Backend Path:</span>
                        <span class="label-value">${service.backend_path}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Force SSL:</span>
                        <span class="label-value">${service.force_ssl ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">WebSocket Support:</span>
                        <span class="label-value">${service.support_websocket ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="label-item">
                        <span class="label-key">Cloudflare Tunnel:</span>
                        <span class="label-value">${service.cloudflare_tunnel ? 'Yes' : 'No'}</span>
                    </div>
                `;

                
                // Show warning if port is not published
                if (!service.resolved_host_port) {
                    labelsHtml += `
                        <div class="label-item" style="color: var(--warning-color);">
                            <span class="label-key">⚠️ Warning:</span>
                            <span class="label-value">Port ${service.port} is not published to host</span>
                        </div>
                    `;
                }
                
                labelsHtml += '</div></div>';
            });
        }
        
        // Add note about multi-port support
        labelsHtml += '<p style="margin-top: 1rem; color: var(--text-secondary); font-size: 0.875rem;">Multi-port containers can expose multiple services with different domains and configurations.</p>';
        
        labelsHtml += '</div>';
        
        return labelsHtml;
    }
    
    generateStaticRouteContent(route) {
        let routeHtml = '<div class="labels-content">';
        
        routeHtml += '<h4>Static Route Configuration</h4>';
        routeHtml += '<div class="labels-grid">';
        
        // Display all static route properties
        routeHtml += `
            <div class="label-item">
                <span class="label-key">Domain:</span>
                <span class="label-value">${route.domain}</span>
            </div>
            <div class="label-item">
                <span class="label-key">Backend URL:</span>
                <span class="label-value">${route.backend_url}</span>
            </div>
            <div class="label-item">
                <span class="label-key">Backend Path:</span>
                <span class="label-value">${route.backend_path}</span>
            </div>
            <div class="label-item">
                <span class="label-key">Force SSL:</span>
                <span class="label-value">${route.force_ssl ? 'Yes' : 'No'}</span>
            </div>
            <div class="label-item">
                <span class="label-key">WebSocket Support:</span>
                <span class="label-value">${route.support_websocket ? 'Yes' : 'No'}</span>
            </div>
            <div class="label-item">
                <span class="label-key">Type:</span>
                <span class="label-value">Static Route</span>
            </div>
        `;
        
        routeHtml += '</div>';
        routeHtml += '<p style="margin-top: 1rem; color: var(--text-secondary); font-size: 0.875rem;">Static routes are configured via YAML file and proxy to external services.</p>';
        routeHtml += '</div>';
        
        return routeHtml;
    }
    
    setupExpandableRows() {
        const expandButtons = document.querySelectorAll('.expand-button');
        
        // Remove existing event listeners by replacing buttons
        expandButtons.forEach((button, index) => {
            button.replaceWith(button.cloneNode(true));
        });
        
        // Get fresh references after cloning
        const freshButtons = document.querySelectorAll('.expand-button');
        
        freshButtons.forEach((button, index) => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const containerId = button.dataset.containerId;
                const labelsRow = document.getElementById(`labels-${containerId}`);
                const containerRow = button.closest('tr');
                
                if (labelsRow && labelsRow.classList.contains('show')) {
                    // Collapse
                    labelsRow.classList.remove('show');
                    button.classList.remove('expanded');
                    containerRow.classList.remove('expanded');
                } else if (labelsRow) {
                    // Expand
                    labelsRow.classList.add('show');
                    button.classList.add('expanded');
                    containerRow.classList.add('expanded');
                }
            });
        });
    }
    
    
    sortContainers(containers) {
        return containers.sort((a, b) => {
            let aValue, bValue;
            
            // Get primary sort values
            switch (this.sortColumn) {
                case 'name':
                    aValue = a.name;
                    bValue = b.name;
                    break;
                case 'host':
                    aValue = a.host;
                    bValue = b.host;
                    break;
                case 'status':
                    aValue = a.status;
                    bValue = b.status;
                    break;
                case 'image':
                    aValue = a.image;
                    bValue = b.image;
                    break;
                case 'revp':
                    aValue = a.has_revp_config ? 1 : 0;
                    bValue = b.has_revp_config ? 1 : 0;
                    break;
                case 'domain':
                    aValue = a.has_revp_config && a.services && a.services.length > 0 ? a.services[0].domain : '';
                    bValue = b.has_revp_config && b.services && b.services.length > 0 ? b.services[0].domain : '';
                    break;
                case 'backend':
                    aValue = a.has_revp_config && a.services && a.services.length > 0 ? a.services[0].backend_url : '';
                    bValue = b.has_revp_config && b.services && b.services.length > 0 ? b.services[0].backend_url : '';
                    break;
                default:
                    return 0;
            }
            
            // Handle string comparison
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                aValue = aValue.toLowerCase();
                bValue = bValue.toLowerCase();
            }
            
            // Primary sort comparison
            let comparison = 0;
            if (aValue < bValue) {
                comparison = this.sortDirection === 'asc' ? -1 : 1;
            } else if (aValue > bValue) {
                comparison = this.sortDirection === 'asc' ? 1 : -1;
            }
            
            // If primary values are equal, do secondary sort
            if (comparison === 0) {
                // Secondary sort by host if not already sorting by host
                if (this.sortColumn !== 'host') {
                    const aHost = a.host.toLowerCase();
                    const bHost = b.host.toLowerCase();
                    if (aHost < bHost) return -1;
                    if (aHost > bHost) return 1;
                }
                
                // Tertiary sort by name if not already sorting by name
                if (this.sortColumn !== 'name') {
                    const aName = a.name.toLowerCase();
                    const bName = b.name.toLowerCase();
                    if (aName < bName) return -1;
                    if (aName > bName) return 1;
                }
            }
            
            return comparison;
        });
    }

    

    setupContainerFilters() {
        // Populate host filter
        const hostFilter = document.getElementById('host-filter');
        const hosts = [...new Set(this.containers.map(c => c.host))];
        
        hostFilter.innerHTML = '<option value="">All Hosts</option>';
        hosts.forEach(host => {
            const option = document.createElement('option');
            option.value = host;
            option.textContent = host;
            hostFilter.appendChild(option);
        });
        
        // Set up filter event listeners
        document.getElementById('filter-revp').addEventListener('change', () => {
            this.updateContainersDisplay();
        });
        
        document.getElementById('filter-non-revp').addEventListener('change', () => {
            this.updateContainersDisplay();
        });
        
        hostFilter.addEventListener('change', () => {
            this.updateContainersDisplay();
        });
    }
    
    storeExpandedState() {
        this.expandedRows.clear();
        document.querySelectorAll('.labels-row.show').forEach(row => {
            const containerId = row.id.replace('labels-', '');
            this.expandedRows.add(containerId);
        });
    }
    
    restoreExpandedState() {
        this.expandedRows.forEach(containerId => {
            const button = document.querySelector(`[data-container-id="${containerId}"]`);
            const labelsRow = document.getElementById(`labels-${containerId}`);
            const containerRow = button?.closest('tr');
            
            if (button && labelsRow && containerRow) {
                labelsRow.classList.add('show');
                button.classList.add('expanded');
                containerRow.classList.add('expanded');
            }
        });
        
        // Also restore sort state for containers table
        if (this.containersTable && this.sortColumn) {
            this.containersTable.setSortState(this.sortColumn, this.sortDirection);
        }
    }
    
    closeAllExpandedRows() {
        // Clear the expanded rows set
        this.expandedRows.clear();
        
        // Close all currently visible dropdown tables
        document.querySelectorAll('.labels-row.show').forEach(row => {
            row.classList.remove('show');
        });
        
        document.querySelectorAll('.expand-button.expanded').forEach(button => {
            button.classList.remove('expanded');
        });
        
        document.querySelectorAll('.container-row.expanded').forEach(row => {
            row.classList.remove('expanded');
        });
    }

    // Hosts Tab
    async loadHostsData() {
        try {
            // Load both hosts data and status data
            const [hostsResponse, statusResponse] = await Promise.all([
                fetch('/api/hosts'),
                fetch('/api/hosts/status')
            ]);
            
            if (!hostsResponse.ok) {
                console.warn('Hosts API not available:', hostsResponse.status);
                this.hostsData = {
                    configuration_type: "unknown",
                    hosts: [],
                    total_hosts: 0,
                    enabled_hosts: 0,
                    connection_status: {}
                };
            } else {
                const hosts = await hostsResponse.json();
                let statusData = { connection_status: {}, dns_verification: {} };
                
                if (statusResponse.ok) {
                    statusData = await statusResponse.json();
                }
                
                // Merge connection status into individual hosts
                const hostsWithStatus = hosts.map(host => {
                    const connectionInfo = statusData.connection_status?.[host.hostname];
                    const dnsInfo = statusData.dns_verification?.[host.alias];
                    
                    return {
                        ...host,
                        // Add connection status fields
                        ssh_connected: connectionInfo ? connectionInfo.connected : null,
                        docker_available: connectionInfo ? connectionInfo.connected : null, // For now, assume Docker is available if SSH is connected
                        connection_error: connectionInfo ? null : 'No connection status available',
                        // Add DNS status fields
                        dns_resolved: dnsInfo ? dnsInfo.dns_resolved : null,
                        ip_address: dnsInfo ? dnsInfo.ip_address : null,
                        dns_errors: dnsInfo ? dnsInfo.errors : [],
                        dns_warnings: dnsInfo ? dnsInfo.warnings : []
                    };
                });
                
                // Merge the current hosts data with status information
                this.hostsData = {
                    configuration_type: statusData.configuration_type || "hosts.yml",
                    hosts: hostsWithStatus,
                    total_hosts: hostsWithStatus.length,
                    enabled_hosts: hostsWithStatus.filter(h => h.enabled).length,
                    connection_status: statusData.connection_status || {},
                    dns_verification: statusData.dns_verification || {}
                };
            }
            
            this.updateHostsDisplay();
            
            // Initialize table widget
            if (!this.hostsTable) {
                this.hostsTable = new SortableResizableTable('#hosts-table', {
                    hasExpandColumn: false,
                    sortCallback: (sortKey, sortDirection) => {
                        this.hostsSortColumn = sortKey;
                        this.hostsSortDirection = sortDirection;
                        this.updateHostsDisplay();
                    }
                });
            }
            
            // Setup hosts event handlers
            this.setupHostsEventHandlers();
            
        } catch (error) {
            console.error('Error loading hosts data:', error);
            this.hostsData = {
                configuration_type: "error",
                hosts: [],
                total_hosts: 0,
                enabled_hosts: 0,
                connection_status: {},
                error: error.message
            };
            this.updateHostsDisplay();
        }
    }
    
    updateHostsDisplay() {
        // Update summary info
        const totalHostsEl = document.getElementById('total-hosts');
        const enabledHostsEl = document.getElementById('enabled-hosts');
        const connectedHostsEl = document.getElementById('connected-hosts');
        
        if (totalHostsEl) {
            totalHostsEl.textContent = this.hostsData.total_hosts || 0;
        }
        
        if (enabledHostsEl) {
            enabledHostsEl.textContent = this.hostsData.enabled_hosts || 0;
        }
        
        // Count connected hosts
        if (connectedHostsEl && this.hostsData.hosts) {
            const connectedCount = this.hostsData.hosts.filter(host => {
                if (!host.enabled) return false;
                const connInfo = this.hostsData.connection_status[host.hostname];
                return connInfo && connInfo.connected;
            }).length;
            connectedHostsEl.textContent = connectedCount;
        }
        
        // Display validation errors if any
        if (this.hostsData.validation_errors && this.hostsData.validation_errors.length > 0) {
            let errorContainer = document.getElementById('hosts-errors');
            if (!errorContainer) {
                // Create error container if it doesn't exist
                const hostsContent = document.querySelector('.hosts-content');
                if (hostsContent) {
                    const errorDiv = document.createElement('div');
                    errorDiv.id = 'hosts-errors';
                    errorDiv.className = 'alert alert-danger';
                    errorDiv.style.marginBottom = '1rem';
                    errorDiv.style.padding = '1rem';
                    errorDiv.style.borderRadius = '4px';
                    errorDiv.style.backgroundColor = 'rgba(220, 53, 69, 0.1)';
                    errorDiv.style.border = '1px solid rgba(220, 53, 69, 0.3)';
                    hostsContent.insertBefore(errorDiv, hostsContent.firstChild);
                    errorContainer = errorDiv;
                }
            }
            if (errorContainer) {
                errorContainer.innerHTML = `
                    <strong style="color: var(--danger-color);">Configuration Errors:</strong>
                    <ul style="margin-bottom: 0; margin-top: 0.5rem; padding-left: 1.5rem;">
                        ${this.hostsData.validation_errors.map(err => `<li style="color: var(--danger-color);">${err}</li>`).join('')}
                    </ul>
                `;
            }
        } else {
            // Remove error container if no errors
            const errorContainer = document.getElementById('hosts-errors');
            if (errorContainer) {
                errorContainer.remove();
            }
        }
        
        // Update hosts table
        const tableBody = document.getElementById('hosts-table-body');
        if (!tableBody) return;
        
        if (!this.hostsData.hosts || this.hostsData.hosts.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem;">
                        ${this.hostsData.error ? 
                            `<span style="color: var(--danger-color);">Error: ${this.hostsData.error}</span>` :
                            'No hosts configured'
                        }
                    </td>
                </tr>
            `;
            return;
        }
        
        // Sort hosts if needed
        let sortedHosts = [...this.hostsData.hosts];
        if (this.hostsSortColumn) {
            sortedHosts = this.sortHosts(sortedHosts);
        }
        
        // Build table rows
        const rows = sortedHosts.map(host => {
            // Determine connection and DNS status
            let statusBadge = '<span class="host-status disabled">Unknown</span>';
            let statusDetails = [];
            
            if (!host.enabled) {
                statusBadge = '<span class="host-status disabled">Disabled</span>';
            } else {
                // Check DNS resolution first
                if (host.dns_resolved === false) {
                    statusBadge = '<span class="host-status disconnected" title="DNS resolution failed">DNS Failed</span>';
                    if (host.dns_errors && host.dns_errors.length > 0) {
                        statusDetails = host.dns_errors;
                    }
                } else if (host.dns_resolved === true) {
                    // DNS resolved, check SSH connection
                    // Try multiple ways to find connection info (hostname, IP, alias)
                    let connectionInfo = this.hostsData.connection_status[host.hostname];
                    if (!connectionInfo && host.ip_address) {
                        connectionInfo = this.hostsData.connection_status[host.ip_address];
                    }
                    if (!connectionInfo) {
                        // Try to find by alias
                        connectionInfo = Object.values(this.hostsData.connection_status || {})
                            .find(conn => conn.alias === host.alias);
                    }
                    
                    if (connectionInfo) {
                        if (connectionInfo.connected) {
                            statusBadge = '<span class="host-status connected">Connected</span>';
                        } else {
                            statusBadge = '<span class="host-status disconnected">SSH Failed</span>';
                        }
                    } else {
                        statusBadge = '<span class="host-status disabled">Not Tested</span>';
                    }
                } else {
                    // DNS status unknown, try to find connection info anyway
                    let connectionInfo = this.hostsData.connection_status[host.hostname];
                    if (!connectionInfo && host.ip_address) {
                        connectionInfo = this.hostsData.connection_status[host.ip_address];
                    }
                    if (!connectionInfo) {
                        connectionInfo = Object.values(this.hostsData.connection_status || {})
                            .find(conn => conn.alias === host.alias);
                    }
                    
                    if (connectionInfo) {
                        if (connectionInfo.connected) {
                            statusBadge = '<span class="host-status connected">Connected</span>';
                        } else {
                            statusBadge = '<span class="host-status disconnected">Disconnected</span>';
                        }
                    }
                }
            }
            
            // Build hostname display with IP if available
            let hostnameDisplay = host.hostname;
            if (host.ip_address) {
                hostnameDisplay += `<br><small style="color: var(--text-secondary);">${host.ip_address}</small>`;
            }
            
            // Add error/warning indicators
            if (host.dns_errors && host.dns_errors.length > 0) {
                hostnameDisplay += `<br><small style="color: var(--danger-color);">${host.dns_errors.join(', ')}</small>`;
            } else if (host.dns_warnings && host.dns_warnings.length > 0) {
                hostnameDisplay += `<br><small style="color: var(--warning-color);">${host.dns_warnings.join(', ')}</small>`;
            }
            
            // Show only the key filename
            const keyFile = host.key_file ? host.key_file.split('/').pop() : 'Not specified';
            
            return `
                <tr ${!host.enabled ? 'style="opacity: 0.6;"' : ''}>
                    <td><strong>${host.alias}</strong></td>
                    <td>${hostnameDisplay}</td>
                    <td>${host.user}</td>
                    <td>${host.port}</td>
                    <td>${statusBadge}</td>
                    <td>${host.description || 'No description'}</td>
                    <td><code style="font-size: 0.8em;">${keyFile}</code></td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-small btn-secondary" onclick="dashboard.editHost('${host.alias}')">
                                Edit
                            </button>
                            <button class="btn btn-small btn-danger" onclick="dashboard.deleteHost('${host.alias}')">
                                Delete
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        tableBody.innerHTML = rows;
    }
    
    sortHosts(hosts) {
        return hosts.sort((a, b) => {
            let aValue, bValue;
            
            switch (this.hostsSortColumn) {
                case 'alias':
                    aValue = a.alias.toLowerCase();
                    bValue = b.alias.toLowerCase();
                    break;
                case 'hostname':
                    aValue = a.hostname.toLowerCase();
                    bValue = b.hostname.toLowerCase();
                    break;
                case 'user':
                    aValue = a.user.toLowerCase();
                    bValue = b.user.toLowerCase();
                    break;
                case 'port':
                    aValue = a.port;
                    bValue = b.port;
                    break;
                case 'status':
                    // Sort by connection status
                    const aConnInfo = this.hostsData.connection_status[a.hostname];
                    const bConnInfo = this.hostsData.connection_status[b.hostname];
                    
                    if (!a.enabled) aValue = 0; // Disabled
                    else if (aConnInfo && aConnInfo.connected) aValue = 2; // Connected
                    else aValue = 1; // Disconnected/Unknown
                    
                    if (!b.enabled) bValue = 0; // Disabled
                    else if (bConnInfo && bConnInfo.connected) bValue = 2; // Connected
                    else bValue = 1; // Disconnected/Unknown
                    break;
                case 'description':
                    aValue = (a.description || '').toLowerCase();
                    bValue = (b.description || '').toLowerCase();
                    break;
                default:
                    return 0;
            }
            
            if (aValue < bValue) {
                return this.hostsSortDirection === 'asc' ? -1 : 1;
            }
            if (aValue > bValue) {
                return this.hostsSortDirection === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }

    // Health Tab
    async loadHealthData() {
        try {
            const response = await fetch('/health/detailed');
            this.healthData = await response.json();
            
            this.updateHealthDisplay();
        } catch (error) {
            console.error('Error loading health data:', error);
        }
    }

    updateHealthDisplay() {
        const components = this.healthData.components || {};
        
        // Update Docker Monitor
        if (components.docker_monitor) {
            this.updateHealthCard('docker-monitor-health', components.docker_monitor);
        }
        
        // Update Caddy Manager
        if (components.caddy_manager) {
            this.updateHealthCard('caddy-manager-health', components.caddy_manager);
        }
        
        // Update SSH Connections
        if (components.ssh_connections) {
            this.updateHealthCard('ssh-connections-health', components.ssh_connections);
        }
        
        // Update error logs (placeholder for now)
        const errorLogs = document.getElementById('error-logs');
        errorLogs.innerHTML = '<p style="color: var(--text-secondary);">No recent errors</p>';
    }

    updateHealthCard(cardId, componentData) {
        const card = document.getElementById(cardId);
        const statusIndicator = card.querySelector('.status-indicator');
        const statusText = card.querySelector('.status-text');
        const details = card.querySelector('.health-details');
        
        statusIndicator.className = `status-indicator ${componentData.status}`;
        statusText.textContent = componentData.status.charAt(0).toUpperCase() + componentData.status.slice(1);
        
        // Build details HTML
        let detailsHtml = '';
        
        if (componentData.error) {
            detailsHtml = `<p style="color: var(--danger-color);">Error: ${componentData.error}</p>`;
        } else {
            if (componentData.total_containers !== undefined) {
                detailsHtml += `<p>Total Containers: ${componentData.total_containers}</p>`;
                detailsHtml += `<p>Monitored Hosts: ${componentData.monitored_hosts}</p>`;
            }
            
            if (componentData.route_count !== undefined) {
                detailsHtml += `<p>Active Routes: ${componentData.route_count}</p>`;
                detailsHtml += `<p>Connected: ${componentData.connected ? 'Yes' : 'No'}</p>`;
            }
            
            if (componentData.healthy_count !== undefined) {
                detailsHtml += `<p>Healthy: ${componentData.healthy_count} / ${componentData.total_count}</p>`;
                
                if (componentData.connections) {
                    detailsHtml += '<div style="margin-top: 0.5rem;">';
                    Object.entries(componentData.connections).forEach(([host, conn]) => {
                        const status = conn.connected ? 'healthy' : 'unhealthy';
                        detailsHtml += `
                            <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                                <span class="status-indicator ${status}" style="width: 8px; height: 8px;"></span>
                                <span>${host}:${conn.port}</span>
                            </div>
                        `;
                    });
                    detailsHtml += '</div>';
                }
            }
        }
        
        details.innerHTML = detailsHtml;
    }

    // Version Tab
    async loadVersionData() {
        try {
            const response = await fetch('/api/changelog');
            const changelog = await response.json();
            
            this.updateVersionDisplay(changelog);
        } catch (error) {
            console.error('Error loading version data:', error);
        }
    }

    updateVersionDisplay(changelog) {
        const container = document.getElementById('changelog');
        container.innerHTML = '';
        
        changelog.forEach(version => {
            const entry = document.createElement('div');
            entry.className = `version-entry ${version.is_current ? 'current' : ''}`;
            
            let changesHtml = '';
            
            if (version.changes.features.length > 0) {
                changesHtml += '<h4>Features</h4><ul>';
                version.changes.features.forEach(feature => {
                    changesHtml += `<li>${feature}</li>`;
                });
                changesHtml += '</ul>';
            }
            
            if (version.changes.fixes.length > 0) {
                changesHtml += '<h4>Bug Fixes</h4><ul>';
                version.changes.fixes.forEach(fix => {
                    changesHtml += `<li>${fix}</li>`;
                });
                changesHtml += '</ul>';
            }
            
            if (version.changes.breaking.length > 0) {
                changesHtml += '<h4>Breaking Changes</h4><ul>';
                version.changes.breaking.forEach(change => {
                    changesHtml += `<li>${change}</li>`;
                });
                changesHtml += '</ul>';
            }
            
            entry.innerHTML = `
                <div class="version-header">
                    <span class="version-number">${version.version}</span>
                    <span class="version-date">${version.date}</span>
                </div>
                <div class="version-changes">
                    ${changesHtml}
                </div>
            `;
            
            container.appendChild(entry);
        });
    }

    // About Tab
    async loadAboutData() {
        try {
            // Load host count
            const response = await fetch('/api/hosts');
            if (response.ok) {
                const hostsData = await response.json();
                const hostCount = hostsData.length;
                document.getElementById('about-host-count').textContent = hostCount;
            }
            
            this.setupAboutEventHandlers();
        } catch (error) {
            console.error('Error loading about data:', error);
            document.getElementById('about-host-count').textContent = 'Error';
        }
    }

    setupAboutEventHandlers() {
        const verifyBtn = document.getElementById('verify-caddy-btn');
        if (verifyBtn) {
            verifyBtn.addEventListener('click', () => this.verifyCaddyConfiguration());
        }
        
        const viewConfigBtn = document.getElementById('view-caddy-config-btn');
        if (viewConfigBtn) {
            viewConfigBtn.addEventListener('click', () => this.viewCaddyConfig());
        }
        
        // Setup modal close handlers
        const modal = document.getElementById('caddy-config-modal');
        const closeBtn = document.getElementById('caddy-config-close');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.remove('show');
                this.clearCaddyConfigSearch();
                this.caddySearchInitialized = false;
                this.cleanupCaddyConfigHandlers();
            });
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.classList.remove('show');
                this.clearCaddyConfigSearch();
                this.caddySearchInitialized = false;
                this.cleanupCaddyConfigHandlers();
            }
        });
        
        // Close modal with ESC key
        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && modal.classList.contains('show')) {
                modal.classList.remove('show');
                this.clearCaddyConfigSearch();
                this.caddySearchInitialized = false;
                this.cleanupCaddyConfigHandlers();
            }
        });
        
        // Setup copy button
        const copyBtn = document.getElementById('caddy-config-copy');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyCaddyConfig());
        }
        
        // Setup download button
        const downloadBtn = document.getElementById('caddy-config-download');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.downloadCaddyConfig());
        }
    }

    async verifyCaddyConfiguration() {
        const btn = document.getElementById('verify-caddy-btn');
        const resultsDiv = document.getElementById('verification-results');
        
        // Show loading state
        btn.disabled = true;
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="verification-item"><span class="verification-status">⏳</span><span class="verification-message">Verifying configuration...</span></div>';
        resultsDiv.className = 'verification-results';

        try {
            // Create verification endpoint request
            const response = await fetch('/api/verify-caddy');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const verification = await response.json();
            this.displayVerificationResults(verification);
            
        } catch (error) {
            console.error('Error verifying Caddy configuration:', error);
            resultsDiv.innerHTML = `
                <div class="verification-item">
                    <span class="verification-status error">❌</span>
                    <span class="verification-message">Verification failed</span>
                </div>
                <div class="verification-details">Error: ${error.message}</div>
            `;
            resultsDiv.className = 'verification-results error';
        } finally {
            btn.disabled = false;
        }
    }

    displayVerificationResults(verification) {
        const resultsDiv = document.getElementById('verification-results');
        let html = '';
        let hasErrors = false;
        let hasWarnings = false;

        // Display summary
        html += `
            <div class="verification-item">
                <span class="verification-status success">✅</span>
                <span class="verification-message">Verification completed</span>
            </div>
        `;

        // Container routes verification
        if (verification.container_routes) {
            const containerRoutes = verification.container_routes;
            const matched = containerRoutes.matched || 0;
            const missing = containerRoutes.missing || 0;
            const orphaned = containerRoutes.orphaned || 0;

            html += `
                <div class="verification-item">
                    <span class="verification-status ${missing > 0 || orphaned > 0 ? 'warning' : 'success'}">
                        ${missing > 0 || orphaned > 0 ? '⚠️' : '✅'}
                    </span>
                    <span class="verification-message">Container Routes: ${matched} matched</span>
                </div>
            `;

            if (missing > 0) {
                html += `<div class="verification-details">⚠️ ${missing} containers with RevP labels missing Caddy routes</div>`;
                hasWarnings = true;
            }

            if (orphaned > 0) {
                html += `<div class="verification-details">⚠️ ${orphaned} orphaned Caddy routes (containers no longer exist)</div>`;
                hasWarnings = true;
            }
        }

        // Static routes verification
        if (verification.static_routes) {
            const staticRoutes = verification.static_routes;
            const matched = staticRoutes.matched || 0;
            const missing = staticRoutes.missing || 0;

            html += `
                <div class="verification-item">
                    <span class="verification-status ${missing > 0 ? 'warning' : 'success'}">
                        ${missing > 0 ? '⚠️' : '✅'}
                    </span>
                    <span class="verification-message">Static Routes: ${matched} matched</span>
                </div>
            `;

            if (missing > 0) {
                html += `<div class="verification-details">⚠️ ${missing} static routes missing Caddy configuration</div>`;
                hasWarnings = true;
            }
        }

        resultsDiv.innerHTML = html;
        
        // Set appropriate styling
        if (hasErrors) {
            resultsDiv.className = 'verification-results error';
        } else if (hasWarnings) {
            resultsDiv.className = 'verification-results warning';
        } else {
            resultsDiv.className = 'verification-results success';
        }
    }
    
    async viewCaddyConfig() {
        const btn = document.getElementById('view-caddy-config-btn');
        const modal = document.getElementById('caddy-config-modal');
        const content = document.getElementById('caddy-config-content');
        
        // Show loading state
        btn.disabled = true;
        btn.querySelector('.btn-text').style.display = 'none';
        btn.querySelector('.btn-loading').style.display = 'inline';
        
        try {
            const response = await fetch('/api/caddy-config');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.config) {
                content.textContent = data.config;
                this.caddyConfigRawContent = data.config; // Store raw content for download and search
                // Don't apply syntax highlighting as it interferes with search
                
                // Generate line numbers
                this.generateLineNumbers();
            } else {
                content.textContent = data.error || 'Failed to load configuration';
                this.caddyConfigRawContent = null;
                // Clear line numbers
                const lineNumbers = document.getElementById('caddy-config-line-numbers');
                if (lineNumbers) lineNumbers.innerHTML = '';
            }
            
            modal.classList.add('show');
            
            // Setup search after modal is shown and content is loaded
            setTimeout(() => {
                this.setupCaddyConfigSearch();
                this.setupCaddyConfigKeyboardShortcuts();
            }, 100);
            
        } catch (error) {
            console.error('Error loading Caddy configuration:', error);
            content.textContent = `Error: ${error.message}`;
            this.caddyConfigRawContent = null;
            modal.classList.add('show');
        } finally {
            btn.disabled = false;
            btn.querySelector('.btn-text').style.display = 'inline';
            btn.querySelector('.btn-loading').style.display = 'none';
        }
    }
    
    setupCaddyConfigSearch() {
        // Don't set up if already initialized
        if (this.caddySearchInitialized) return;
        
        const searchInput = document.getElementById('caddy-config-search');
        const searchPrev = document.getElementById('caddy-config-search-prev');
        const searchNext = document.getElementById('caddy-config-search-next');
        const searchClear = document.getElementById('caddy-config-search-clear');
        const searchStatus = document.getElementById('caddy-config-search-status');
        const content = document.getElementById('caddy-config-content');
        
        if (!searchInput || !content) {
            console.log('Search elements not found');
            return;
        }
        
        this.searchMatches = [];
        this.currentMatchIndex = -1;
        
        const performSearch = () => {
            const searchTerm = searchInput.value.trim();
            if (!searchTerm) {
                this.clearCaddyConfigSearch();
                return;
            }
            
            console.log('Searching for:', searchTerm);
            
            // Get the raw text content
            const contentText = this.caddyConfigRawContent || content.textContent || '';
            console.log('Content length:', contentText.length);
            
            // Find all matches (case insensitive)
            this.searchMatches = [];
            const searchTermLower = searchTerm.toLowerCase();
            const contentLower = contentText.toLowerCase();
            let startIndex = 0;
            
            while (startIndex < contentText.length) {
                const index = contentLower.indexOf(searchTermLower, startIndex);
                if (index === -1) break;
                
                this.searchMatches.push({
                    start: index,
                    end: index + searchTerm.length
                });
                startIndex = index + 1;
            }
            
            console.log('Found matches:', this.searchMatches.length);
            
            // Update status
            if (this.searchMatches.length > 0) {
                // Highlight matches
                let highlightedContent = '';
                let lastIndex = 0;
                
                this.searchMatches.forEach((match, index) => {
                    highlightedContent += this.escapeHtml(contentText.substring(lastIndex, match.start));
                    highlightedContent += `<span class="search-highlight${index === 0 ? ' current-match' : ''}" data-match-index="${index}">${this.escapeHtml(contentText.substring(match.start, match.end))}</span>`;
                    lastIndex = match.end;
                });
                
                highlightedContent += this.escapeHtml(contentText.substring(lastIndex));
                content.innerHTML = highlightedContent;
                
                // Regenerate line numbers after content change
                this.generateLineNumbers();
                
                // Navigate to first match
                this.currentMatchIndex = 0;
                this.navigateToMatch(0);
                this.updateSearchStatus();
            } else {
                // No matches - restore original content
                content.textContent = contentText;
                searchStatus.textContent = 'No matches';
                this.currentMatchIndex = -1;
                
                // Regenerate line numbers
                this.generateLineNumbers();
            }
        };
        
        // Add event listeners
        searchInput.addEventListener('input', performSearch);
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    this.navigateToPreviousMatch();
                } else {
                    this.navigateToNextMatch();
                }
            }
        });
        
        searchPrev.addEventListener('click', () => this.navigateToPreviousMatch());
        searchNext.addEventListener('click', () => this.navigateToNextMatch());
        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            this.clearCaddyConfigSearch();
        });
        
        this.caddySearchInitialized = true;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    navigateToMatch(index) {
        const highlights = document.querySelectorAll('.search-highlight');
        console.log('Navigating to match', index, 'of', highlights.length);
        
        if (highlights.length === 0) return;
        
        // Remove current highlight
        highlights.forEach(el => el.classList.remove('current-match'));
        
        // Add current highlight and scroll to it
        if (index >= 0 && index < highlights.length) {
            const highlight = highlights[index];
            highlight.classList.add('current-match');
            
            // Scroll the highlight into view
            highlight.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'nearest'
            });
            
            console.log('Scrolled to match', index);
        }
    }
    
    navigateToNextMatch() {
        if (this.searchMatches.length === 0) return;
        this.currentMatchIndex = (this.currentMatchIndex + 1) % this.searchMatches.length;
        this.navigateToMatch(this.currentMatchIndex);
        this.updateSearchStatus();
    }
    
    navigateToPreviousMatch() {
        if (this.searchMatches.length === 0) return;
        this.currentMatchIndex = (this.currentMatchIndex - 1 + this.searchMatches.length) % this.searchMatches.length;
        this.navigateToMatch(this.currentMatchIndex);
        this.updateSearchStatus();
    }
    
    updateSearchStatus() {
        const searchStatus = document.getElementById('caddy-config-search-status');
        if (this.searchMatches.length > 0) {
            searchStatus.textContent = `${this.currentMatchIndex + 1} of ${this.searchMatches.length}`;
        } else {
            searchStatus.textContent = '';
        }
    }
    
    clearCaddyConfigSearch() {
        const searchInput = document.getElementById('caddy-config-search');
        const searchStatus = document.getElementById('caddy-config-search-status');
        const content = document.getElementById('caddy-config-content');
        
        if (searchInput) searchInput.value = '';
        if (searchStatus) searchStatus.textContent = '';
        
        // Restore original content if available
        if (this.caddyConfigRawContent && content) {
            content.textContent = this.caddyConfigRawContent;
            // Don't apply syntax highlighting here as it interferes with search
            // Regenerate line numbers
            this.generateLineNumbers();
        }
        
        this.searchMatches = [];
        this.currentMatchIndex = -1;
    }
    
    async copyCaddyConfig() {
        const copyBtn = document.getElementById('caddy-config-copy');
        const btnText = copyBtn.querySelector('.btn-text');
        const btnLoading = copyBtn.querySelector('.btn-loading');
        
        // Check if there's selected text
        const selection = window.getSelection();
        let textToCopy = '';
        
        if (selection && selection.toString().trim()) {
            // Copy selected text
            textToCopy = selection.toString();
        } else if (this.caddyConfigRawContent) {
            // Copy entire config
            textToCopy = this.caddyConfigRawContent;
        } else {
            this.showToast('No configuration to copy', 'error');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(textToCopy);
            
            // Show success state with appropriate message
            const copiedText = selection && selection.toString().trim() ? 'Selection Copied!' : 'Copied!';
            btnText.textContent = copiedText;
            copyBtn.classList.add('btn-success');
            
            setTimeout(() => {
                btnText.textContent = 'Copy';
                copyBtn.classList.remove('btn-success');
            }, 2000);
            
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    }
    
    downloadCaddyConfig() {
        if (!this.caddyConfigRawContent) {
            this.showToast('No configuration to download', 'error');
            return;
        }
        
        const blob = new Blob([this.caddyConfigRawContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `caddy-config-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    generateLineNumbers() {
        const content = document.getElementById('caddy-config-content');
        const lineNumbersDiv = document.getElementById('caddy-config-line-numbers');
        
        if (!content || !lineNumbersDiv) return;
        
        // Count lines in the content
        const lines = (content.textContent || '').split('\n');
        const lineCount = lines.length;
        
        // Generate line numbers
        let lineNumbersHtml = '';
        for (let i = 1; i <= lineCount; i++) {
            lineNumbersHtml += `<div style="line-height: 1.5;">${i}</div>`;
        }
        
        lineNumbersDiv.innerHTML = lineNumbersHtml;
    }
    
    setupCaddyConfigKeyboardShortcuts() {
        const modal = document.getElementById('caddy-config-modal');
        const content = document.getElementById('caddy-config-content');
        
        if (!modal || !content) return;
        
        // Remove any existing listener to avoid duplicates
        if (this.caddyConfigKeyHandler) {
            document.removeEventListener('keydown', this.caddyConfigKeyHandler);
        }
        
        // Create the key handler
        this.caddyConfigKeyHandler = (e) => {
            // Only handle if modal is visible
            if (!modal.classList.contains('show')) return;
            
            // Handle Ctrl+A or Cmd+A
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                // Check if we're in the search input
                const searchInput = document.getElementById('caddy-config-search');
                if (document.activeElement === searchInput) {
                    // Let default behavior work in search input
                    return;
                }
                
                e.preventDefault();
                
                // Select all text in the config content
                const range = document.createRange();
                range.selectNodeContents(content);
                
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
                
                console.log('Selected all config content');
            }
        };
        
        // Add the event listener
        document.addEventListener('keydown', this.caddyConfigKeyHandler);
    }
    
    cleanupCaddyConfigHandlers() {
        // Remove keyboard shortcut handler
        if (this.caddyConfigKeyHandler) {
            document.removeEventListener('keydown', this.caddyConfigKeyHandler);
            this.caddyConfigKeyHandler = null;
        }
    }

    // Static Routes Tab
    async loadStaticRoutesData() {
        try {
            // Load both routes and file info
            const [routesResponse, fileInfoResponse] = await Promise.all([
                fetch('/api/static-routes'),
                fetch('/api/static-routes/info/file')
            ]);
            
            if (routesResponse.ok) {
                this.staticRoutesData = await routesResponse.json();
            } else {
                console.warn('Static routes API not available:', routesResponse.status);
                this.staticRoutesData = [];
            }
            
            if (fileInfoResponse.ok) {
                this.staticRoutesFileInfo = await fileInfoResponse.json();
            } else {
                this.staticRoutesFileInfo = {};
            }
            
            this.updateStaticRoutesDisplay();
            this.setupStaticRoutesEventHandlers();
            
            // Initialize table widget
            if (!this.staticRoutesTable) {
                this.staticRoutesTable = new SortableResizableTable('#static-routes-table', {
                    hasExpandColumn: false,
                    sortCallback: (sortKey, sortDirection) => {
                        this.staticRoutesSortColumn = sortKey;
                        this.staticRoutesSortDirection = sortDirection;
                        this.updateStaticRoutesDisplay();
                    }
                });
            }
            
        } catch (error) {
            console.error('Error loading static routes data:', error);
            this.staticRoutesData = [];
            this.updateStaticRoutesDisplay();
        }
    }

    updateStaticRoutesDisplay() {
        // Calculate DNS status counts
        const workingRoutes = this.staticRoutesData.filter(route => route.dns_resolved === true).length;
        const dnsIssues = this.staticRoutesData.filter(route => route.dns_resolved === false).length;
        
        // Update info cards
        const totalRoutesEl = document.getElementById('total-static-routes');
        const workingRoutesEl = document.getElementById('working-routes');
        const dnsIssuesEl = document.getElementById('dns-issues');
        const fileStatusEl = document.getElementById('file-status');
        
        if (totalRoutesEl) {
            totalRoutesEl.textContent = this.staticRoutesData.length;
        }
        
        if (workingRoutesEl) {
            workingRoutesEl.textContent = workingRoutes;
        }
        
        if (dnsIssuesEl) {
            dnsIssuesEl.textContent = dnsIssues;
        }
        
        if (fileStatusEl) {
            fileStatusEl.textContent = this.staticRoutesFileInfo.exists ? 'OK' : 'Missing';
        }
        
        // Update table
        const tbody = document.querySelector('#static-routes-table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Sort routes if needed
        const sortedRoutes = this.staticRoutesSortColumn 
            ? this.sortStaticRoutes([...this.staticRoutesData])
            : this.staticRoutesData;
        
        sortedRoutes.forEach(route => {
            const row = document.createElement('tr');
            
            const sslBadge = route.force_ssl 
                ? '<span class="badge badge-success">Yes</span>' 
                : '<span class="badge badge-muted">No</span>';
                
            const wsBadge = route.support_websocket 
                ? '<span class="badge badge-success">Yes</span>' 
                : '<span class="badge badge-muted">No</span>';
                
            const tlsSkipBadge = route.tls_insecure_skip_verify 
                ? '<span class="badge badge-warning" title="TLS certificate verification is disabled">Yes</span>' 
                : '<span class="badge badge-muted">No</span>';
            
            // Create DNS status badge
            let dnsStatusBadge = '';
            let dnsTooltip = '';
            
            if (route.dns_resolved === true) {
                dnsStatusBadge = '<span class="badge badge-success">✓ Resolved</span>';
                dnsTooltip = `DNS resolved successfully to ${route.backend_ip || 'IP address'}`;
                if (route.backend_host) {
                    dnsTooltip += ` (${route.backend_host})`;
                }
            } else if (route.dns_resolved === false) {
                dnsStatusBadge = '<span class="badge badge-danger">✗ DNS Error</span>';
                dnsTooltip = route.dns_error || 'DNS resolution failed';
            } else {
                dnsStatusBadge = '<span class="badge badge-muted">? Unknown</span>';
                dnsTooltip = 'DNS status not checked';
            }
            
            row.innerHTML = `
                <td title="${route.domain}">${route.domain}</td>
                <td title="${route.backend_url}">${route.backend_url}</td>
                <td title="${dnsTooltip}">${dnsStatusBadge}</td>
                <td title="${route.backend_path}">${route.backend_path}</td>
                <td>${sslBadge}</td>
                <td>${wsBadge}</td>
                <td>${tlsSkipBadge}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-small btn-secondary" onclick="dashboard.editStaticRoute('${route.domain}')">
                            Edit
                        </button>
                        <button class="btn btn-small btn-danger" onclick="dashboard.deleteStaticRoute('${route.domain}')">
                            Delete
                        </button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }

    sortStaticRoutes(routes) {
        return routes.sort((a, b) => {
            let aValue, bValue;
            
            switch (this.staticRoutesSortColumn) {
                case 'domain':
                    aValue = a.domain.toLowerCase();
                    bValue = b.domain.toLowerCase();
                    break;
                case 'backend_url':
                    aValue = a.backend_url.toLowerCase();
                    bValue = b.backend_url.toLowerCase();
                    break;
                case 'backend_path':
                    aValue = a.backend_path.toLowerCase();
                    bValue = b.backend_path.toLowerCase();
                    break;
                case 'force_ssl':
                    aValue = a.force_ssl ? 1 : 0;
                    bValue = b.force_ssl ? 1 : 0;
                    break;
                case 'support_websocket':
                    aValue = a.support_websocket ? 1 : 0;
                    bValue = b.support_websocket ? 1 : 0;
                    break;
                case 'tls_insecure_skip_verify':
                    aValue = a.tls_insecure_skip_verify ? 1 : 0;
                    bValue = b.tls_insecure_skip_verify ? 1 : 0;
                    break;
                case 'dns_resolved':
                    // Sort by DNS status: resolved first, then unknown, then failed
                    aValue = a.dns_resolved === true ? 2 : (a.dns_resolved === false ? 0 : 1);
                    bValue = b.dns_resolved === true ? 2 : (b.dns_resolved === false ? 0 : 1);
                    break;
                default:
                    return 0;
            }
            
            if (aValue < bValue) {
                return this.staticRoutesSortDirection === 'asc' ? -1 : 1;
            }
            if (aValue > bValue) {
                return this.staticRoutesSortDirection === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }



    setupStaticRoutesEventHandlers() {
        // Add route button
        const addBtn = document.getElementById('add-route-btn');
        if (addBtn) {
            addBtn.onclick = () => this.showRouteModal();
        }
        
        // Recheck DNS button
        const recheckBtn = document.getElementById('recheck-static-routes-btn');
        if (recheckBtn) {
            recheckBtn.onclick = () => this.recheckStaticRoutesDNS();
        }
        
        // Modal event handlers
        this.setupModalEventHandlers();
    }

    setupModalEventHandlers() {
        // Route modal handlers
        const routeModal = document.getElementById('route-modal');
        const routeForm = document.getElementById('route-form');
        const modalClose = document.getElementById('modal-close');
        const modalCancel = document.getElementById('modal-cancel');
        
        // Close modal handlers
        [modalClose, modalCancel].forEach(btn => {
            if (btn) {
                btn.onclick = () => this.hideRouteModal();
            }
        });
        
        // Click outside to close
        if (routeModal) {
            routeModal.onclick = (e) => {
                if (e.target === routeModal) {
                    this.hideRouteModal();
                }
            };
        }
        
        // Form submission
        if (routeForm) {
            routeForm.onsubmit = (e) => {
                e.preventDefault();
                this.saveStaticRoute();
            };
        }
        
        // Confirmation modal handlers
        const confirmModal = document.getElementById('confirm-modal');
        const confirmClose = document.getElementById('confirm-close');
        const confirmCancel = document.getElementById('confirm-cancel');
        const confirmOk = document.getElementById('confirm-ok');
        
        [confirmClose, confirmCancel].forEach(btn => {
            if (btn) {
                btn.onclick = () => this.hideConfirmModal();
            }
        });
        
        if (confirmModal) {
            confirmModal.onclick = (e) => {
                if (e.target === confirmModal) {
                    this.hideConfirmModal();
                }
            };
        }
        
        if (confirmOk) {
            confirmOk.onclick = () => this.executeConfirmAction();
        }
    }

    showRouteModal(route = null) {
        const modal = document.getElementById('route-modal');
        const title = document.getElementById('modal-title');
        const form = document.getElementById('route-form');
        const validation = document.getElementById('form-validation');
        
        // Reset form and validation
        form.reset();
        validation.className = 'form-validation';
        validation.style.display = 'none';
        
        if (route) {
            // Edit mode
            title.textContent = 'Edit Static Route';
            document.getElementById('route-domain').value = route.domain;
            document.getElementById('route-backend-url').value = route.backend_url;
            document.getElementById('route-backend-path').value = route.backend_path;
            document.getElementById('route-force-ssl').checked = route.force_ssl;
            document.getElementById('route-support-websocket').checked = route.support_websocket;
            document.getElementById('route-tls-insecure-skip-verify').checked = route.tls_insecure_skip_verify;
            
            // Store original domain for editing
            form.dataset.originalDomain = route.domain;
        } else {
            // Add mode
            title.textContent = 'Add Static Route';
            document.getElementById('route-backend-path').value = '/';
            document.getElementById('route-force-ssl').checked = true;
            delete form.dataset.originalDomain;
        }
        
        modal.classList.add('show');
    }

    hideRouteModal() {
        const modal = document.getElementById('route-modal');
        modal.classList.remove('show');
    }

    async saveStaticRoute() {
        const form = document.getElementById('route-form');
        const validation = document.getElementById('form-validation');
        const saveBtn = document.getElementById('modal-save');
        
        // Get form data
        const formData = new FormData(form);
        const routeData = {
            domain: formData.get('domain').trim(),
            backend_url: formData.get('backend_url').trim(),
            backend_path: formData.get('backend_path').trim() || '/',
            force_ssl: formData.has('force_ssl'),
            support_websocket: formData.has('support_websocket'),
            tls_insecure_skip_verify: formData.has('tls_insecure_skip_verify')
        };
        
        // Show loading state
        saveBtn.classList.add('btn-loading');
        validation.style.display = 'none';
        
        try {
            let response;
            const originalDomain = form.dataset.originalDomain;
            
            if (originalDomain) {
                // Edit existing route
                response = await fetch(`/api/static-routes/${encodeURIComponent(originalDomain)}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(routeData)
                });
            } else {
                // Create new route
                response = await fetch('/api/static-routes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(routeData)
                });
            }
            
            if (response.ok) {
                validation.className = 'form-validation success';
                validation.textContent = originalDomain ? 'Route updated successfully!' : 'Route created successfully!';
                validation.style.display = 'block';
                
                // Reload data and close modal after short delay
                setTimeout(() => {
                    this.hideRouteModal();
                    this.loadStaticRoutesData();
                }, 1000);
            } else {
                const errorData = await response.json();
                validation.className = 'form-validation error';
                validation.textContent = errorData.detail || 'Failed to save route';
                validation.style.display = 'block';
            }
        } catch (error) {
            console.error('Error saving static route:', error);
            validation.className = 'form-validation error';
            validation.textContent = 'Network error. Please try again.';
            validation.style.display = 'block';
        } finally {
            saveBtn.classList.remove('btn-loading');
        }
    }

    editStaticRoute(domain) {
        const route = this.staticRoutesData.find(r => r.domain === domain);
        if (route) {
            this.showRouteModal(route);
        }
    }

    deleteStaticRoute(domain) {
        this.showConfirmModal(
            'Delete Static Route',
            `Are you sure you want to delete the static route for "${domain}"? This action cannot be undone.`,
            () => this.executeDeleteRoute(domain)
        );
    }

    showConfirmModal(title, message, action) {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        
        titleEl.textContent = title;
        messageEl.textContent = message;
        
        // Store action for later execution
        this.confirmAction = action;
        
        modal.classList.add('show');
    }

    hideConfirmModal() {
        const modal = document.getElementById('confirm-modal');
        modal.classList.remove('show');
        this.confirmAction = null;
    }

    executeConfirmAction() {
        if (this.confirmAction) {
            this.confirmAction();
        }
        this.hideConfirmModal();
    }

    async executeDeleteRoute(domain) {
        const confirmBtn = document.getElementById('confirm-ok');
        
        // Show loading state
        confirmBtn.classList.add('btn-loading');
        
        try {
            const response = await fetch(`/api/static-routes/${encodeURIComponent(domain)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // Reload data after successful deletion
                this.hideConfirmModal();
                this.loadStaticRoutesData();
            } else {
                const errorData = await response.json();
                alert(`Failed to delete route: ${errorData.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting static route:', error);
            alert('Network error. Please try again.');
        } finally {
            confirmBtn.classList.remove('btn-loading');
        }
    }

    setupHostsEventHandlers() {
        // Recheck DNS button
        const recheckBtn = document.getElementById('recheck-hosts-btn');
        if (recheckBtn) {
            recheckBtn.onclick = () => this.recheckHostsDNS();
        }
        
        // Add host button
        const addBtn = document.getElementById('add-host-btn');
        if (addBtn) {
            addBtn.onclick = () => this.showHostModal();
        }
        
        // Host modal event handlers
        this.setupHostModalEventHandlers();
    }

    async recheckStaticRoutesDNS() {
        const btn = document.getElementById('recheck-static-routes-btn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoading = btn.querySelector('.btn-loading');
        
        try {
            // Show loading state
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';
            btn.disabled = true;
            
            const response = await fetch('/api/static-routes/recheck-dns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Static routes DNS recheck completed:', result);
                
                // Reload static routes data to show updated status
                await this.loadStaticRoutesData();
                
                // Show success message
                this.showNotification(`DNS recheck completed: ${result.working_routes} working, ${result.dns_issues} issues`, 'success');
            } else {
                const error = await response.json();
                this.showNotification(`Error rechecking DNS: ${error.detail || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error rechecking static routes DNS:', error);
            this.showNotification('Network error while rechecking DNS', 'error');
        } finally {
            // Reset button state
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            btn.disabled = false;
        }
    }

    async recheckHostsDNS() {
        const btn = document.getElementById('recheck-hosts-btn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoading = btn.querySelector('.btn-loading');
        
        try {
            // Show loading state
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';
            btn.disabled = true;
            
            const response = await fetch('/api/hosts/recheck-dns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Hosts DNS recheck completed:', result);
                
                // Reload hosts data to show updated status
                await this.loadHostsData();
                
                // Show success message
                this.showNotification(`DNS recheck completed: ${result.working_hosts} working, ${result.dns_issues} issues`, 'success');
            } else {
                const error = await response.json();
                this.showNotification(`Error rechecking DNS: ${error.detail || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error rechecking hosts DNS:', error);
            this.showNotification('Network error while rechecking DNS', 'error');
        } finally {
            // Reset button state
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            btn.disabled = false;
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification - could be enhanced with a proper toast system
        console.log(`${type.toUpperCase()}: ${message}`);
        alert(message); // For now, use alert - could be replaced with a toast notification
    }

    // Host Management Methods
    setupHostModalEventHandlers() {
        // Host modal handlers
        const hostModal = document.getElementById('host-modal');
        const hostForm = document.getElementById('host-form');
        const modalClose = document.getElementById('host-modal-close');
        const modalCancel = document.getElementById('host-modal-cancel');
        const testConnectionBtn = document.getElementById('test-host-connection');
        
        // Close modal handlers
        [modalClose, modalCancel].forEach(btn => {
            if (btn) {
                btn.onclick = () => this.hideHostModal();
            }
        });
        
        // Click outside to close
        if (hostModal) {
            hostModal.onclick = (e) => {
                if (e.target === hostModal) {
                    this.hideHostModal();
                }
            };
        }
        
        // Form submission
        if (hostForm) {
            hostForm.onsubmit = (e) => {
                e.preventDefault();
                this.saveHost();
            };
        }
        
        // Test connection button
        if (testConnectionBtn) {
            testConnectionBtn.onclick = () => this.testHostConnection();
        }
    }

    showHostModal(host = null) {
        const modal = document.getElementById('host-modal');
        const title = document.getElementById('host-modal-title');
        const form = document.getElementById('host-form');
        
        if (!modal || !title || !form) return;
        
        // Set modal title and form data
        if (host) {
            title.textContent = 'Edit Host';
            this.populateHostForm(host);
            // Store current host alias for updates
            form.dataset.editingHost = host.alias;
        } else {
            title.textContent = 'Add Host';
            this.clearHostForm();
            delete form.dataset.editingHost;
        }
        
        // Show modal
        modal.classList.add('show');
        
        // Focus first input
        const firstInput = form.querySelector('input[type="text"]');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }

    hideHostModal() {
        const modal = document.getElementById('host-modal');
        const form = document.getElementById('host-form');
        
        if (modal) {
            modal.classList.remove('show');
        }
        
        if (form) {
            delete form.dataset.editingHost;
        }
        
        this.clearHostForm();
        this.clearHostValidation();
    }

    populateHostForm(host) {
        document.getElementById('host-alias').value = host.alias || '';
        document.getElementById('host-hostname').value = host.hostname || '';
        document.getElementById('host-user').value = host.user || 'revp';
        document.getElementById('host-port').value = host.port || 22;
        document.getElementById('host-key-file').value = host.key_file || '/home/app/.ssh/docker_monitor_key';
        document.getElementById('host-description').value = host.description || '';
        document.getElementById('host-enabled').checked = host.enabled !== false;
        
        // Disable alias editing when updating
        document.getElementById('host-alias').disabled = true;
    }

    clearHostForm() {
        document.getElementById('host-alias').value = '';
        document.getElementById('host-hostname').value = '';
        document.getElementById('host-user').value = 'revp';
        document.getElementById('host-port').value = '22';
        document.getElementById('host-key-file').value = '/home/app/.ssh/docker_monitor_key';
        document.getElementById('host-description').value = '';
        document.getElementById('host-enabled').checked = true;
        
        // Enable alias editing when creating
        document.getElementById('host-alias').disabled = false;
        
        // Clear connection test results
        const testResult = document.getElementById('connection-test-result');
        if (testResult) {
            testResult.style.display = 'none';
            testResult.innerHTML = '';
        }
    }

    clearHostValidation() {
        const validation = document.getElementById('host-form-validation');
        if (validation) {
            validation.innerHTML = '';
        }
    }

    async saveHost() {
        const form = document.getElementById('host-form');
        const saveBtn = document.getElementById('host-modal-save');
        const btnText = saveBtn.querySelector('.btn-text');
        const btnLoading = saveBtn.querySelector('.btn-loading');
        
        try {
            // Show loading state
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';
            saveBtn.disabled = true;
            
            // Get form data
            const formData = new FormData(form);
            const hostData = {
                alias: formData.get('alias'),
                hostname: formData.get('hostname'),
                user: formData.get('user'),
                port: parseInt(formData.get('port')),
                key_file: formData.get('key_file'),
                description: formData.get('description'),
                enabled: formData.has('enabled')
            };
            
            // Determine if this is an update or create
            const isUpdate = form.dataset.editingHost;
            const url = isUpdate 
                ? `/api/hosts/${encodeURIComponent(form.dataset.editingHost)}`
                : '/api/hosts';
            const method = isUpdate ? 'PUT' : 'POST';
            
            // For updates, exclude alias from the payload
            if (isUpdate) {
                delete hostData.alias;
            }
            
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(hostData)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log(`Host ${isUpdate ? 'updated' : 'created'} successfully:`, result);
                
                // Reload hosts data
                await this.loadHostsData();
                
                // Close modal
                this.hideHostModal();
                
                // Show success message
                this.showNotification(`Host ${isUpdate ? 'updated' : 'created'} successfully`, 'success');
            } else {
                const error = await response.json();
                this.showHostValidationError(error.detail || 'Unknown error');
            }
        } catch (error) {
            console.error('Error saving host:', error);
            this.showHostValidationError('Network error while saving host');
        } finally {
            // Reset button state
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            saveBtn.disabled = false;
        }
    }

    async testHostConnection() {
        const form = document.getElementById('host-form');
        const testBtn = document.getElementById('test-host-connection');
        const btnText = testBtn.querySelector('.btn-text');
        const btnLoading = testBtn.querySelector('.btn-loading');
        const resultDiv = document.getElementById('connection-test-result');
        
        try {
            // Show loading state
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';
            testBtn.disabled = true;
            
            // For testing, we need to check if we're editing an existing host
            const hostAlias = form.dataset.editingHost || document.getElementById('host-alias').value;
            
            if (!hostAlias) {
                this.showConnectionTestResult({
                    ssh_connected: false,
                    docker_available: false,
                    error: 'Host alias is required for connection testing'
                });
                return;
            }
            
            const response = await fetch(`/api/hosts/${encodeURIComponent(hostAlias)}/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showConnectionTestResult(result);
            } else {
                const error = await response.json();
                this.showConnectionTestResult({
                    ssh_connected: false,
                    docker_available: false,
                    error: error.detail || 'Connection test failed'
                });
            }
        } catch (error) {
            console.error('Error testing host connection:', error);
            this.showConnectionTestResult({
                ssh_connected: false,
                docker_available: false,
                error: 'Network error during connection test'
            });
        } finally {
            // Reset button state
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            testBtn.disabled = false;
        }
    }

    showConnectionTestResult(result) {
        const resultDiv = document.getElementById('connection-test-result');
        if (!resultDiv) return;
        
        let html = '<div class="connection-test-results">';
        
        if (result.error) {
            html += `<div class="test-result test-error">❌ ${result.error}</div>`;
        } else {
            // SSH Status
            html += `<div class="test-result ${result.ssh_connected ? 'test-success' : 'test-error'}">
                ${result.ssh_connected ? '✅' : '❌'} SSH Connection
            </div>`;
            
            // Docker Status
            html += `<div class="test-result ${result.docker_available ? 'test-success' : 'test-error'}">
                ${result.docker_available ? '✅' : '❌'} Docker Available
            </div>`;
            
            // Connection time
            if (result.connection_time_ms) {
                html += `<div class="test-result test-info">
                    ⏱️ Response time: ${Math.round(result.connection_time_ms)}ms
                </div>`;
            }
        }
        
        html += '</div>';
        resultDiv.innerHTML = html;
        resultDiv.style.display = 'block';
    }

    showHostValidationError(message) {
        const validation = document.getElementById('host-form-validation');
        if (validation) {
            validation.innerHTML = `<div class="validation-error">${message}</div>`;
        }
    }

    editHost(alias) {
        const host = this.hostsData.hosts?.find(h => h.alias === alias);
        if (host) {
            this.showHostModal(host);
        }
    }

    deleteHost(alias) {
        // Show confirmation modal
        const confirmModal = document.getElementById('confirm-modal');
        const confirmTitle = document.getElementById('confirm-title');
        const confirmMessage = document.getElementById('confirm-message');
        const confirmOk = document.getElementById('confirm-ok');
        
        if (!confirmModal) return;
        
        confirmTitle.textContent = 'Delete Host';
        confirmMessage.textContent = `Are you sure you want to delete host "${alias}"? This will stop monitoring this host and remove all its container routes.`;
        
        // Remove previous event listeners
        confirmOk.replaceWith(confirmOk.cloneNode(true));
        const newConfirmOk = document.getElementById('confirm-ok');
        
        newConfirmOk.onclick = async () => {
            const confirmBtn = newConfirmOk;
            const btnText = confirmBtn.querySelector('.btn-text');
            const btnLoading = confirmBtn.querySelector('.btn-loading');
            
            try {
                // Show loading state
                btnText.style.display = 'none';
                btnLoading.style.display = 'inline';
                confirmBtn.disabled = true;
                
                const response = await fetch(`/api/hosts/${encodeURIComponent(alias)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log(`Host ${alias} deleted successfully`);
                    
                    // Hide confirmation modal
                    confirmModal.style.display = 'none';
                    
                    // Reload hosts data
                    await this.loadHostsData();
                    
                    // Show success message
                    this.showNotification(`Host "${alias}" deleted successfully`, 'success');
                } else {
                    const errorData = await response.json();
                    alert(`Failed to delete host: ${errorData.detail || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error deleting host:', error);
                alert('Network error. Please try again.');
            } finally {
                confirmBtn.classList.remove('btn-loading');
            }
        };
        
        confirmModal.style.display = 'flex';
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});