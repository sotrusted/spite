/**
 * Admin Dashboard JavaScript
 * Provides interactive functionality for the admin dashboard
 */

class AdminDashboard {
    constructor() {
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.lastRefreshTime = Date.now();
        this.refreshIntervalMs = 300000; // 5 minutes
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupAutoRefresh();
        this.addNotificationSystem();
        this.setupRealTimeIndicators();
    }
    
    setupEventListeners() {
        // Manual refresh button
        const refreshBtn = document.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
        
        // Auto-refresh toggle
        this.addAutoRefreshToggle();
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                this.refreshData();
            }
        });
    }
    
    addAutoRefreshToggle() {
        const header = document.querySelector('.dashboard-header');
        if (!header) return;
        
        const toggleContainer = document.createElement('div');
        toggleContainer.style.marginTop = '10px';
        
        const toggle = document.createElement('label');
        toggle.style.cssText = `
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            color: #ccc;
            font-size: 0.9rem;
        `;
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = this.autoRefreshEnabled;
        checkbox.style.marginRight = '8px';
        
        checkbox.addEventListener('change', (e) => {
            this.autoRefreshEnabled = e.target.checked;
            if (this.autoRefreshEnabled) {
                this.setupAutoRefresh();
            } else {
                this.clearAutoRefresh();
            }
        });
        
        toggle.appendChild(checkbox);
        toggle.appendChild(document.createTextNode('Auto-refresh (5 min)'));
        toggleContainer.appendChild(toggle);
        header.appendChild(toggleContainer);
    }
    
    setupAutoRefresh() {
        this.clearAutoRefresh();
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                this.refreshData();
            }, this.refreshIntervalMs);
        }
    }
    
    clearAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    addNotificationSystem() {
        // Create notification container
        const notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            max-width: 300px;
        `;
        document.body.appendChild(notificationContainer);
    }
    
    showNotification(message, type = 'info', duration = 3000) {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.style.cssText = `
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#ff6b35'};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
        `;
        
        notification.textContent = message;
        notification.addEventListener('click', () => {
            notification.remove();
        });
        
        container.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }
    }
    
    setupRealTimeIndicators() {
        // Add loading indicator
        const refreshBtn = document.querySelector('.refresh-btn');
        if (!refreshBtn) return;
        
        this.originalRefreshText = refreshBtn.textContent;
        
        // Add connection status indicator
        const statusIndicator = document.createElement('div');
        statusIndicator.id = 'connection-status';
        statusIndicator.style.cssText = `
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #28a745;
            margin-left: 10px;
            animation: pulse 2s infinite;
        `;
        
        const lastUpdated = document.getElementById('lastUpdated');
        if (lastUpdated) {
            lastUpdated.appendChild(statusIndicator);
        }
    }
    
    setRefreshLoading(loading) {
        const refreshBtn = document.querySelector('.refresh-btn');
        const statusIndicator = document.getElementById('connection-status');
        
        if (refreshBtn) {
            if (loading) {
                refreshBtn.textContent = 'Refreshing...';
                refreshBtn.disabled = true;
                refreshBtn.style.opacity = '0.7';
            } else {
                refreshBtn.textContent = this.originalRefreshText;
                refreshBtn.disabled = false;
                refreshBtn.style.opacity = '1';
            }
        }
        
        if (statusIndicator) {
            statusIndicator.style.background = loading ? '#ffc107' : '#28a745';
        }
    }
    
    async refreshData() {
        try {
            this.setRefreshLoading(true);
            
            const response = await fetch('/api/admin-dashboard/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Update metrics with animation
            this.updateMetrics(data);
            
            // Update timestamp
            const timestamp = new Date(data.timestamp).toLocaleString();
            const timestampElement = document.getElementById('timestamp');
            if (timestampElement) {
                timestampElement.textContent = timestamp;
            }
            
            this.lastRefreshTime = Date.now();
            this.showNotification('Dashboard updated successfully', 'success', 2000);
            
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification(`Failed to refresh: ${error.message}`, 'error', 5000);
            
            const statusIndicator = document.getElementById('connection-status');
            if (statusIndicator) {
                statusIndicator.style.background = '#dc3545';
            }
        } finally {
            this.setRefreshLoading(false);
        }
    }
    
    updateMetrics(data) {
        const metrics = [
            { id: 'posts-hour', value: data.posts_metrics.hour },
            { id: 'posts-12h', value: data.posts_metrics.twelve_hours },
            { id: 'posts-day', value: data.posts_metrics.day },
            { id: 'posts-week', value: data.posts_metrics.week },
            { id: 'posts-month', value: data.posts_metrics.month },
            { id: 'comments-hour', value: data.comments_metrics.hour },
            { id: 'comments-12h', value: data.comments_metrics.twelve_hours },
            { id: 'comments-day', value: data.comments_metrics.day },
            { id: 'comments-week', value: data.comments_metrics.week },
            { id: 'comments-month', value: data.comments_metrics.month }
        ];
        
        metrics.forEach(metric => {
            const element = document.getElementById(metric.id);
            if (element) {
                const oldValue = parseInt(element.textContent);
                const newValue = metric.value;
                
                if (oldValue !== newValue) {
                    this.animateValueChange(element, oldValue, newValue);
                }
            }
        });
    }
    
    animateValueChange(element, oldValue, newValue) {
        // Highlight changed values
        element.style.transition = 'all 0.3s ease';
        element.style.background = '#ff6b35';
        element.style.padding = '2px 6px';
        element.style.borderRadius = '4px';
        
        // Animate number change
        const duration = 500;
        const steps = 20;
        const stepValue = (newValue - oldValue) / steps;
        let currentStep = 0;
        
        const animate = () => {
            if (currentStep < steps) {
                const currentValue = Math.round(oldValue + (stepValue * currentStep));
                element.textContent = currentValue;
                currentStep++;
                setTimeout(animate, duration / steps);
            } else {
                element.textContent = newValue;
                
                // Remove highlight after animation
                setTimeout(() => {
                    element.style.background = '';
                    element.style.padding = '';
                    element.style.borderRadius = '';
                }, 1000);
            }
        };
        
        animate();
    }
    
    // Utility method to format large numbers
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    // Method to export dashboard data
    async exportData() {
        try {
            const response = await fetch('/api/admin-dashboard/');
            const data = await response.json();
            
            const exportData = {
                timestamp: data.timestamp,
                posts_metrics: data.posts_metrics,
                comments_metrics: data.comments_metrics,
                exported_at: new Date().toISOString()
            };
            
            const blob = new Blob([JSON.stringify(exportData, null, 2)], {
                type: 'application/json'
            });
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dashboard-data-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            
            URL.revokeObjectURL(url);
            this.showNotification('Data exported successfully', 'success');
            
        } catch (error) {
            console.error('Error exporting data:', error);
            this.showNotification('Failed to export data', 'error');
        }
    }
    
    // Cleanup method
    destroy() {
        this.clearAutoRefresh();
        
        const container = document.getElementById('notification-container');
        if (container) {
            container.remove();
        }
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 currentColor;
        }
        70% {
            box-shadow: 0 0 0 3px transparent;
        }
        100% {
            box-shadow: 0 0 0 0 transparent;
        }
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.adminDashboard = new AdminDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.adminDashboard) {
        window.adminDashboard.destroy();
    }
});
