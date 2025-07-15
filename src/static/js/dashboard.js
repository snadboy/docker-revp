// Dashboard JavaScript
class Dashboard {
    constructor() {
        this.currentTab = 'summary';
        this.containers = [];
        this.healthData = {};
        this.summaryData = {};
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.expandedRows = new Set(); // Track expanded rows
        this.resizing = false;
        this.currentResizer = null;
        this.startX = 0;
        this.startWidth = 0;
        this.globalResizeListenersAdded = false;
        
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
            case 'health':
                await this.loadHealthData();
                break;
            case 'version':
                await this.loadVersionData();
                break;
        }
    }

    async refreshCurrentTab() {
        // Store expanded state before refresh
        if (this.currentTab === 'containers') {
            this.storeExpandedState();
        }
        
        await this.loadTabData(this.currentTab);
        
        // Restore expanded state after refresh
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
            const response = await fetch('/containers');
            if (!response.ok) {
                console.warn('Containers API not available:', response.status);
                this.containers = [];
            } else {
                const data = await response.json();
                // Handle error responses from the API
                if (data.detail && data.detail.includes('not initialized')) {
                    console.warn('Docker monitor not initialized, using empty container list');
                    this.containers = [];
                } else {
                    this.containers = Array.isArray(data) ? data : [];
                }
            }
            
            this.updateContainersDisplay();
            this.setupContainerFilters();
            // Only set up table sorting if not already initialized
            if (!this.sortingInitialized) {
                this.setupTableSorting();
                this.setupColumnResizing();
                this.sortingInitialized = true;
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
            
            const domain = container.has_revp_config && container.labels['snadboy.revp.domain']
                ? container.labels['snadboy.revp.domain']
                : '-';
            
            const backend = container.has_revp_config && container.labels['snadboy.revp.backend-port']
                ? `${container.labels['snadboy.revp.backend-proto'] || 'https'}://${container.host}:${container.labels['snadboy.revp.backend-port']}`
                : '-';
            
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
        
        // Set up expand/collapse functionality
        this.setupExpandableRows();
        
        // Restore expanded state after updating display
        this.restoreExpandedState();
    }
    
    generateLabelsContent(container) {
        let labelsHtml = '<div class="labels-content">';
        
        if (container.has_revp_config && Object.keys(container.labels).length > 0) {
            labelsHtml += '<h4>RevP Labels</h4><div class="labels-grid">';
            
            Object.entries(container.labels).forEach(([key, value]) => {
                if (key.startsWith('snadboy.revp.')) {
                    labelsHtml += `
                        <div class="label-item">
                            <span class="label-key">${key}:</span>
                            <span class="label-value">${value || '(empty)'}</span>
                        </div>
                    `;
                }
            });
            
            labelsHtml += '</div>';
        }
        
        // Add a placeholder for all other labels if we had access to them
        labelsHtml += '<p style="margin-top: 1rem; color: var(--text-secondary); font-size: 0.875rem;">Only RevP labels are currently displayed. Other Docker labels are not included in the API response.</p>';
        
        labelsHtml += '</div>';
        
        return labelsHtml;
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
    
    setupTableSorting() {
        const sortableHeaders = document.querySelectorAll('th.sortable');
        
        // Remove existing event listeners to prevent duplicates
        sortableHeaders.forEach(header => {
            header.replaceWith(header.cloneNode(true));
        });
        
        // Get fresh references after cloning
        const freshHeaders = document.querySelectorAll('th.sortable');
        
        freshHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const sortKey = header.dataset.sort;
                
                // Close all open dropdown tables before sorting
                this.closeAllExpandedRows();
                
                // Update sort direction
                if (this.sortColumn === sortKey) {
                    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortColumn = sortKey;
                    this.sortDirection = 'asc';
                }
                
                // Update header classes
                freshHeaders.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                header.classList.add(this.sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
                
                // Re-render table
                this.updateContainersDisplay();
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
                    aValue = a.has_revp_config && a.labels['snadboy.revp.domain'] ? a.labels['snadboy.revp.domain'] : '';
                    bValue = b.has_revp_config && b.labels['snadboy.revp.domain'] ? b.labels['snadboy.revp.domain'] : '';
                    break;
                case 'backend':
                    aValue = a.has_revp_config && a.labels['snadboy.revp.backend-port'] ? a.labels['snadboy.revp.backend-port'] : '';
                    bValue = b.has_revp_config && b.labels['snadboy.revp.backend-port'] ? b.labels['snadboy.revp.backend-port'] : '';
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

    setupColumnResizing() {
        const table = document.querySelector('#containers-table');
        if (!table) {
            return;
        }
        
        // Remove existing resizers first
        const existingResizers = table.querySelectorAll('.column-resizer');
        existingResizers.forEach(resizer => resizer.remove());
        
        // Skip first column (expand button) and last column for resizing
        const headers = table.querySelectorAll('th:not(:first-child):not(:last-child)');
        
        headers.forEach((header, index) => {
            // Add resizer element
            const resizer = document.createElement('div');
            resizer.className = 'column-resizer';
            header.appendChild(resizer);
            
            // Add resize event listeners
            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.startResize(e, header, resizer);
            });
        });
        
        // Only add global mouse event listeners once
        if (!this.globalResizeListenersAdded) {
            document.addEventListener('mousemove', (e) => this.doResize(e));
            document.addEventListener('mouseup', () => this.stopResize());
            this.globalResizeListenersAdded = true;
        }
    }
    
    startResize(e, header, resizer) {
        this.resizing = true;
        this.currentResizer = resizer;
        this.currentHeader = header;
        this.startX = e.pageX;
        this.startWidth = parseInt(document.defaultView.getComputedStyle(header).width, 10);
        
        const table = header.closest('table');
        const allHeaders = Array.from(table.querySelectorAll('th'));
        const targetColumnIndex = allHeaders.indexOf(header);
        
        // Lock widths for ALL columns to the LEFT of the target column
        // This prevents them from changing during resize
        for (let i = 0; i < targetColumnIndex; i++) {
            const leftHeader = allHeaders[i];
            const currentWidth = parseInt(document.defaultView.getComputedStyle(leftHeader).width, 10);
            leftHeader.style.width = currentWidth + 'px';
            
            // Also lock corresponding td widths
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cell = row.children[i];
                if (cell) {
                    cell.style.width = currentWidth + 'px';
                }
            });
        }
        
        // Set initial width for the target column
        header.style.width = this.startWidth + 'px';
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cell = row.children[targetColumnIndex];
            if (cell) {
                cell.style.width = this.startWidth + 'px';
            }
        });
        
        // Do NOT set explicit widths for columns to the RIGHT
        // They will automatically adjust to fill remaining space
        
        resizer.classList.add('resizing');
        document.querySelector('.table-container').classList.add('resizing');
        
        // Prevent sorting when resizing
        e.stopPropagation();
    }
    
    doResize(e) {
        if (!this.resizing || !this.currentResizer || !this.currentHeader) return;
        
        const deltaX = e.pageX - this.startX;
        const newWidth = this.startWidth + deltaX;
        const minWidth = 80;
        
        // Apply minimum width constraint
        if (newWidth < minWidth) {
            return; // Don't resize below minimum
        }
        
        // Update ONLY the target column width
        // Columns to the left are locked (from startResize)
        // Columns to the right will automatically adjust to fill remaining space
        this.currentHeader.style.width = newWidth + 'px';
        
        // Update corresponding td elements for the target column only
        const table = this.currentHeader.closest('table');
        const allHeaders = Array.from(table.querySelectorAll('th'));
        const targetColumnIndex = allHeaders.indexOf(this.currentHeader);
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const cell = row.children[targetColumnIndex];
            if (cell) {
                cell.style.width = newWidth + 'px';
            }
        });
    }
    
    stopResize() {
        if (!this.resizing) return;
        
        this.resizing = false;
        
        if (this.currentResizer) {
            this.currentResizer.classList.remove('resizing');
            this.currentResizer = null;
        }
        
        this.currentHeader = null;
        document.querySelector('.table-container').classList.remove('resizing');
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
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});