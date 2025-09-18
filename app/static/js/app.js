/**
 * Solvia SPA - Main Application Entry Point
 * Bootstraps the modular architecture and initializes core systems
 */

// Import core modules
import router from './core/Router.js';
import eventBus from './core/EventBus.js';
import apiClient from './services/ApiClient.js';

// Import route components
import DashboardController from './components/Dashboard/DashboardController.js';
import AuditHistoryController from './components/AuditHistory/AuditHistoryController.js';
import SettingsController from './components/Settings/SettingsController.js';

// Import services
import { AuditService } from './services/AuditService.js';
import { AuthService } from './services/AuthService.js';

// Global app configuration
const APP_CONFIG = {
    name: 'Solvia',
    version: '2.0.0',
    apiVersion: 'v1'
};

/**
 * Application class
 */
class SolviaApp {
    constructor() {
        this.config = APP_CONFIG;
        this.services = {};
        this.controllers = {};
    }

    /**
     * Initialize application
     */
    async init() {
        console.log(`🚀 ${this.config.name} v${this.config.version} initializing...`);

        try {
            // Initialize services
            this.initializeServices();

            // Register routes
            this.registerRoutes();

            // Setup global event handlers
            this.setupGlobalHandlers();

            // Check authentication
            await this.checkAuth();

            // Initialize sidebar
            this.initializeSidebar();

            // Start router
            router.handleRoute();

            console.log('✅ Application initialized successfully');

        } catch (error) {
            console.error('❌ Application initialization failed:', error);
            this.handleFatalError(error);
        }
    }

    /**
     * Initialize services
     */
    initializeServices() {
        this.services.auth = new AuthService();
        this.services.audit = new AuditService();

        // Make services globally available
        window.solviaServices = this.services;
    }

    /**
     * Register application routes
     */
    registerRoutes() {
        // Dashboard route
        router.register('dashboard', {
            title: 'Dashboard',
            component: async () => {
                const controller = new DashboardController();
                this.controllers.dashboard = controller;
                await controller.init();
                return controller.render();
            }
        });

        // Audit History route
        router.register('audit-history', {
            title: 'Audit History',
            component: async () => {
                const controller = new AuditHistoryController();
                this.controllers.auditHistory = controller;
                await controller.init();
                return controller.render();
            }
        });

        // Settings route
        router.register('settings', {
            title: 'Settings',
            component: async () => {
                const controller = new SettingsController();
                this.controllers.settings = controller;
                await controller.init();
                return controller.render();
            }
        });

        // Add route guards
        router.beforeEach(async (to, from) => {
            // Clean up previous controller
            if (from && this.controllers[from.path]) {
                const controller = this.controllers[from.path];
                if (controller.destroy) {
                    controller.destroy();
                }
                delete this.controllers[from.path];
            }

            // Check authentication for protected routes
            const publicRoutes = ['login', 'register'];
            if (!publicRoutes.includes(to.path)) {
                const isAuthenticated = await this.services.auth.isAuthenticated();
                if (!isAuthenticated) {
                    window.location.href = '/';
                    return false;
                }
            }

            return true;
        });
    }

    /**
     * Setup global event handlers
     */
    setupGlobalHandlers() {
        // Handle authentication expiry
        eventBus.on('auth:expired', () => {
            console.log('Authentication expired');
            this.services.auth.logout();
            window.location.href = '/';
        });

        // Handle API errors
        eventBus.on('api:error', (error) => {
            console.error('API Error:', error);
            this.showNotification('An error occurred. Please try again.', 'error');
        });

        // Handle route errors
        eventBus.on('route:error', ({ route, error }) => {
            console.error(`Route error for ${route.path}:`, error);
            this.showNotification('Failed to load page', 'error');
        });

        // Handle audit completion
        eventBus.on('audit:completed', (data) => {
            this.showNotification('✅ Audit completed successfully!', 'success');
            // Refresh dashboard if on dashboard route
            if (router.getCurrentRoute()?.path === 'dashboard') {
                this.controllers.dashboard?.loadDashboardData();
            }
        });
    }

    /**
     * Check authentication status
     */
    async checkAuth() {
        const token = localStorage.getItem('jwt_token');
        if (token) {
            apiClient.setToken(token);

            // Verify token is still valid
            try {
                const user = await apiClient.get('/api/auth/me');
                this.updateUserInfo(user);
            } catch (error) {
                console.error('Token validation failed:', error);
                localStorage.removeItem('jwt_token');
            }
        }
    }

    /**
     * Initialize sidebar
     */
    initializeSidebar() {
        // Update user info in sidebar
        const userEmail = localStorage.getItem('userEmail');
        if (userEmail) {
            this.updateUserInfo({ email: userEmail });
        }

        // Mark body as loaded for animations
        setTimeout(() => {
            document.body.classList.add('loaded');
        }, 100);
    }

    /**
     * Update user info in UI
     */
    updateUserInfo(user) {
        const userEmailEl = document.getElementById('userEmail');
        if (userEmailEl && user.email) {
            const username = user.email.split('@')[0];
            userEmailEl.textContent = username;
            userEmailEl.setAttribute('data-full-email', user.email);
            userEmailEl.classList.add('email-tooltip');
            localStorage.setItem('userEmail', user.email);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // This could be enhanced with a proper notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#EF4444' : '#10B981'};
            color: white;
            border-radius: 8px;
            z-index: 100000;
            animation: slideInRight 0.3s ease;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Handle fatal errors
     */
    handleFatalError(error) {
        document.getElementById('app-content').innerHTML = `
            <div style="padding: 48px; text-align: center;">
                <h2 style="color: #EF4444; margin-bottom: 16px;">Application Error</h2>
                <p style="color: #6B7280;">${error.message}</p>
                <button onclick="location.reload()"
                        style="margin-top: 24px; padding: 12px 24px;
                               background: #EC6019; color: white; border: none;
                               border-radius: 8px; cursor: pointer;">
                    Reload Application
                </button>
            </div>
        `;
    }
}

// Global functions that need to be accessible from HTML
window.toggleSidebar = function() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('expanded');
    localStorage.setItem('sidebarExpanded', sidebar.classList.contains('expanded'));
};

window.logout = async function() {
    try {
        await apiClient.post('/api/auth/logout');
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        localStorage.clear();
        window.location.href = '/';
    }
};

window.toggleIssueDescription = function(cardId) {
    const shortDiv = document.getElementById(`short-${cardId}`);
    const fullDiv = document.getElementById(`full-${cardId}`);
    const btn = event.target;

    if (fullDiv.style.display === 'none' || fullDiv.style.display === '') {
        shortDiv.style.display = 'none';
        fullDiv.style.display = 'block';
        btn.textContent = '← Show less details';
    } else {
        shortDiv.style.display = 'block';
        fullDiv.style.display = 'none';
        btn.textContent = 'Show more details →';
    }
};

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new SolviaApp();
    app.init();

    // Make app instance globally available for debugging
    window.solviaApp = app;
});