/**
 * Version Control System
 * Handles toggling between version 1.0 (posts only) and 2.0 (posts with comments)
 */
const VersionControl = {
    // Current version state
    currentVersion: '2.0',
    
    // Initialize the version control system
    init: function() {
        // Get saved version from localStorage or default to 2.0
        this.currentVersion = localStorage.getItem('siteVersion') || '2.0';
        
        // Apply initial version state
        this.applyVersionState(this.currentVersion);
        
        // Create or update the toggle button
        this.setupToggleButton();
        
        console.log('Version Control initialized with version:', this.currentVersion);
    },
    
    // Set up the version toggle button
    setupToggleButton: function() {
        // Find existing button or create a new one
        let toggleButton = document.getElementById('version-toggle');
        
        if (!toggleButton) {
            // If button doesn't exist in DOM, it might be created by snow.js later
            document.addEventListener('DOMNodeInserted', function(e) {
                if (e.target.id === 'version-toggle') {
                    VersionControl.setupButtonEvents(e.target);
                }
            });
        } else {
            this.setupButtonEvents(toggleButton);
        }
    },
    
    // Set up events for the toggle button
    setupButtonEvents: function(button) {
        // Update button text and style
        button.innerHTML = this.currentVersion;
        this.styleButton(button, this.currentVersion);
        
        // Remove any existing click handlers
        button.replaceWith(button.cloneNode(true));
        
        // Get fresh reference after cloning
        button = document.getElementById('version-toggle');
        
        // Add click handler
        button.addEventListener('click', function() {
            VersionControl.toggleVersion();
        });
    },
    
    // Toggle between versions
    toggleVersion: function() {
        // Toggle version
        const newVersion = this.currentVersion === '2.0' ? '1.0' : '2.0';
        
        // Update server-side session (optional)
        this.updateServerSession(newVersion);
        
        // Update local state
        this.currentVersion = newVersion;
        localStorage.setItem('siteVersion', newVersion);
        
        // Apply version state to UI
        this.applyVersionState(newVersion);
        
        console.log('Version toggled to:', newVersion);
    },
    
    // Apply version state to UI
    applyVersionState: function(version) {
        // Update body class
        if (version === '1.0') {
            document.body.classList.add('v1-mode');
        } else {
            document.body.classList.remove('v1-mode');
        }
        
        // Update button if it exists
        const button = document.getElementById('version-toggle');
        if (button) {
            button.innerHTML = version;
            this.styleButton(button, version);
        }
    },
    
    // Style the button based on version
    styleButton: function(button, version) {
        if (version === '1.0') {
            button.style.background = 'rgba(200, 200, 200, 0.7)';
        } else {
            button.style.background = 'rgba(255, 255, 255, 0.7)';
        }
    },
    
    // Update server session (optional)
    updateServerSession: function(version) {
        fetch('/toggle-version/', {
            method: 'GET',
            headers: {
                'X-Version-Toggle': 'true',
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).catch(error => {
            console.warn('Failed to update server session:', error);
            // Continue anyway since we're using localStorage as source of truth
        });
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    VersionControl.init();
});