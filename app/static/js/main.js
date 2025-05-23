// Universal Policy Checker - Main JavaScript

// Global utilities and functions
class PolicyChecker {
    constructor() {
        this.apiBase = window.location.origin;
        this.init();
    }
    
    init() {
        this.setupGlobalEventListeners();
        this.setupTooltips();
        this.setupAlerts();
    }
    
    setupGlobalEventListeners() {
        // Global form validation
        document.addEventListener('submit', this.handleFormSubmission.bind(this));
        
        // Global error handling
        window.addEventListener('error', this.handleGlobalError.bind(this));
        
        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal.show');
                modals.forEach(modal => {
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) modalInstance.hide();
                });
            }
        });
    }
    
    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    setupAlerts() {
        // Auto-dismiss alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                const alertInstance = new bootstrap.Alert(alert);
                alertInstance.close();
            }, 5000);
        });
    }
    
    handleFormSubmission(e) {
        const form = e.target;
        if (!form.classList.contains('needs-validation')) return;
        
        if (!form.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        form.classList.add('was-validated');
    }
    
    handleGlobalError(error) {
        console.error('Global error:', error);
        this.showAlert('An unexpected error occurred. Please try again.', 'danger');
    }
    
    // API Methods
    async apiCall(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };
        
        try {
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.indexOf('application/json') !== -1) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
    
    async get(endpoint) {
        return this.apiCall(endpoint, { method: 'GET' });
    }
    
    async post(endpoint, data) {
        return this.apiCall(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async postForm(endpoint, formData) {
        return this.apiCall(endpoint, {
            method: 'POST',
            headers: {}, // Let browser set content-type for FormData
            body: formData
        });
    }
    
    // UI Helper Methods
    showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alertId = 'alert-' + Date.now();
        
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${alertId}">
                <i class="fas fa-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('afterbegin', alertHtml);
        
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const alertInstance = new bootstrap.Alert(alert);
                    alertInstance.close();
                }
            }, duration);
        }
    }
    
    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle',
            'primary': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showLoading(element, text = 'Loading...') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (!element) return;
        
        const loadingHtml = `
            <div class="loading-overlay">
                <div class="text-center">
                    <div class="spinner-border text-primary mb-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="small text-muted">${text}</div>
                </div>
            </div>
        `;
        
        element.style.position = 'relative';
        element.insertAdjacentHTML('beforeend', loadingHtml);
    }
    
    hideLoading(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (!element) return;
        
        const loadingOverlay = element.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }
    
    showModal(title, content, options = {}) {
        const modalId = 'dynamic-modal-' + Date.now();
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog ${options.size || 'modal-lg'}">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
        
        // Remove modal from DOM when hidden
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
        
        return modal;
    }
    
    // Utility Methods
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showAlert('Copied to clipboard!', 'success', 2000);
            }).catch(err => {
                this.showAlert('Failed to copy to clipboard', 'danger');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                this.showAlert('Copied to clipboard!', 'success', 2000);
            } catch (err) {
                this.showAlert('Failed to copy to clipboard', 'danger');
            }
            document.body.removeChild(textArea);
        }
    }
    
    downloadJSON(data, filename = 'data.json') {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Validation Helpers
    validateJSON(text) {
        try {
            JSON.parse(text);
            return { valid: true };
        } catch (error) {
            return { valid: false, error: error.message };
        }
    }
    
    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    validateURL(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }
    
    // Local Storage Helpers
    saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Failed to save to storage:', error);
            return false;
        }
    }
    
    loadFromStorage(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error('Failed to load from storage:', error);
            return null;
        }
    }
    
    removeFromStorage(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Failed to remove from storage:', error);
            return false;
        }
    }
}

// Initialize PolicyChecker
const policyChecker = new PolicyChecker();

// Global helper functions
window.showAlert = (message, type, duration) => policyChecker.showAlert(message, type, duration);
window.showLoading = (element, text) => policyChecker.showLoading(element, text);
window.hideLoading = (element) => policyChecker.hideLoading(element);
window.showModal = (title, content, options) => policyChecker.showModal(title, content, options);
window.copyToClipboard = (text) => policyChecker.copyToClipboard(text);
window.downloadJSON = (data, filename) => policyChecker.downloadJSON(data, filename);

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PolicyChecker;
}

// Auto-refresh functionality for development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    let lastHeartbeat = Date.now();
    
    setInterval(async () => {
        try {
            await fetch('/');
            lastHeartbeat = Date.now();
        } catch (error) {
            // Server might be restarting
            if (Date.now() - lastHeartbeat > 10000) { // 10 seconds
                showAlert('Server connection lost. Refreshing page...', 'warning');
                setTimeout(() => window.location.reload(), 2000);
            }
        }
    }, 5000);
}