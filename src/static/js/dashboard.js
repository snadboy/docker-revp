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
        this.sortColumn = null;
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
            
            // Load certificate data
            await this.loadCertificateData();
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

    // Certificate Status
    async loadCertificateData() {
        try {
            const response = await fetch('/api/certificate/status');
            if (!response.ok) {
                console.warn('Certificate API not available:', response.status);
                return;
            }
            
            const certData = await response.json();
            this.updateCertificateDisplay(certData);
        } catch (error) {
            console.error('Error loading certificate data:', error);
        }
    }
    
    updateCertificateDisplay(data) {
        // Update domain
        const certDomainEl = document.getElementById('cert-domain');
        if (certDomainEl) {
            certDomainEl.textContent = data.domain || '*.snadboy.com';
        }
        
        // Update issuer
        const certIssuerEl = document.getElementById('cert-issuer');
        if (certIssuerEl) {
            certIssuerEl.textContent = data.issuer || 'Unknown';
        }
        
        // Update expiry date
        const certExpiryEl = document.getElementById('cert-expiry');
        if (certExpiryEl) {
            if (data.expiry_date) {
                const expiryDate = new Date(data.expiry_date);
                const formattedDate = expiryDate.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
                
                let displayText = formattedDate;
                if (data.days_until_expiry !== null) {
                    displayText += ` (${data.days_until_expiry} days)`;
                }
                
                certExpiryEl.textContent = displayText;
            } else {
                certExpiryEl.textContent = 'Unknown';
            }
        }
        
        // Update status
        const certStatusEl = document.getElementById('cert-status');
        if (certStatusEl) {
            certStatusEl.textContent = data.status ? data.status.charAt(0).toUpperCase() + data.status.slice(1) : 'Unknown';
            
            // Update status class
            certStatusEl.className = 'cert-status';
            if (data.status === 'valid') {
                certStatusEl.classList.add('valid');
            } else if (data.status === 'expiring') {
                certStatusEl.classList.add('expiring');
            } else if (data.status === 'expired' || data.status === 'error' || data.status === 'missing') {
                certStatusEl.classList.add('expired');
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
            
            if (aValue < bValue) {
                return this.sortDirection === 'asc' ? -1 : 1;
            }
            if (aValue > bValue) {
                return this.sortDirection === 'asc' ? 1 : -1;
            }
            return 0;
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
            const response = await fetch('/api/hosts/status');
            if (!response.ok) {
                console.warn('Hosts API not available:', response.status);
                this.hostsData = {
                    configuration_type: "unknown",
                    hosts: [],
                    total_hosts: 0,
                    enabled_hosts: 0,
                    connection_status: {}
                };
            } else {
                this.hostsData = await response.json();
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
        
        // Update hosts table
        const tableBody = document.getElementById('hosts-table-body');
        if (!tableBody) return;
        
        if (!this.hostsData.hosts || this.hostsData.hosts.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2rem;">
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
            // Determine connection status
            let statusBadge = '<span class="host-status disabled">Unknown</span>';
            
            if (!host.enabled) {
                statusBadge = '<span class="host-status disabled">Disabled</span>';
            } else {
                const connectionInfo = this.hostsData.connection_status[host.hostname];
                if (connectionInfo) {
                    if (connectionInfo.connected) {
                        statusBadge = '<span class="host-status connected">Connected</span>';
                    } else {
                        statusBadge = '<span class="host-status disconnected">Disconnected</span>';
                    }
                }
            }
            
            // Show only the key filename
            const keyFile = host.key_file ? host.key_file.split('/').pop() : 'Not specified';
            
            return `
                <tr ${!host.enabled ? 'style="opacity: 0.6;"' : ''}>
                    <td><strong>${host.alias}</strong></td>
                    <td>${host.hostname}</td>
                    <td>${host.user}</td>
                    <td>${host.port}</td>
                    <td>${statusBadge}</td>
                    <td>${host.description || 'No description'}</td>
                    <td><code style="font-size: 0.8em;">${keyFile}</code></td>
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
        // Update info cards
        const totalRoutesEl = document.getElementById('total-static-routes');
        const fileStatusEl = document.getElementById('file-status');
        const lastModifiedEl = document.getElementById('last-modified');
        
        if (totalRoutesEl) {
            totalRoutesEl.textContent = this.staticRoutesData.length;
        }
        
        if (fileStatusEl) {
            fileStatusEl.textContent = this.staticRoutesFileInfo.exists ? 'OK' : 'Missing';
        }
        
        if (lastModifiedEl) {
            if (this.staticRoutesFileInfo.last_modified) {
                const date = new Date(this.staticRoutesFileInfo.last_modified);
                lastModifiedEl.textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
            } else {
                lastModifiedEl.textContent = 'Unknown';
            }
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
            
            row.innerHTML = `
                <td title="${route.domain}">${route.domain}</td>
                <td title="${route.backend_url}">${route.backend_url}</td>
                <td title="${route.backend_path}">${route.backend_path}</td>
                <td>${sslBadge}</td>
                <td>${wsBadge}</td>
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
            support_websocket: formData.has('support_websocket')
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
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});