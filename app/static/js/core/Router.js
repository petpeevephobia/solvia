/**
 * Router - Lightweight SPA routing system
 * Handles client-side navigation and history management
 */
import eventBus from './EventBus.js';

export class Router {
    constructor() {
        this.routes = new Map();
        this.currentRoute = null;
        this.beforeHooks = [];
        this.afterHooks = [];
        this.init();
    }

    /**
     * Initialize the router
     */
    init() {
        // Handle browser back/forward navigation
        window.addEventListener('popstate', () => {
            this.handleRoute();
        });

        // Handle initial route
        document.addEventListener('DOMContentLoaded', () => {
            this.handleRoute();
        });

        // Intercept all internal links
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href^="#"]');
            if (link) {
                e.preventDefault();
                const route = link.getAttribute('href').substring(1) || 'dashboard';
                this.navigate(route);
            }
        });
    }

    /**
     * Register a route
     * @param {string} path - Route path
     * @param {Object} config - Route configuration
     */
    register(path, config) {
        this.routes.set(path, {
            path,
            title: config.title || 'Solvia',
            component: config.component,
            guard: config.guard,
            meta: config.meta || {}
        });
    }

    /**
     * Navigate to a route
     * @param {string} path - Route path
     * @param {Object} params - Route parameters
     */
    async navigate(path, params = {}) {
        const route = this.routes.get(path);

        if (!route) {
            console.error(`Route not found: ${path}`);
            this.navigate('dashboard'); // Fallback to dashboard
            return;
        }

        // Run before hooks
        for (const hook of this.beforeHooks) {
            const proceed = await hook(route, this.currentRoute);
            if (!proceed) return;
        }

        // Check route guard
        if (route.guard) {
            const canActivate = await route.guard(route, params);
            if (!canActivate) {
                console.log(`Access denied to route: ${path}`);
                return;
            }
        }

        // Update URL and history
        const url = `#${path}`;
        if (window.location.hash !== url) {
            window.history.pushState({ path, params }, route.title, url);
        }

        // Update current route
        const previousRoute = this.currentRoute;
        this.currentRoute = { ...route, params };

        // Update document title
        document.title = `${route.title} - Solvia`;

        // Load route component
        try {
            await this.loadComponent(route, params);

            // Emit route change event
            eventBus.emit('route:change', {
                current: this.currentRoute,
                previous: previousRoute
            });

            // Run after hooks
            for (const hook of this.afterHooks) {
                await hook(this.currentRoute, previousRoute);
            }

            // Update active nav items
            this.updateActiveNav(path);

        } catch (error) {
            console.error(`Failed to load route component:`, error);
            eventBus.emit('route:error', { route, error });
        }
    }

    /**
     * Load route component
     * @param {Object} route - Route configuration
     * @param {Object} params - Route parameters
     */
    async loadComponent(route, params) {
        const container = document.getElementById('app-content');
        const loadingIndicator = document.getElementById('contentLoading');

        if (!container) {
            throw new Error('App content container not found');
        }

        // Show loading
        if (loadingIndicator) {
            loadingIndicator.classList.remove('hidden');
        }
        container.classList.remove('loaded');

        try {
            // Load component
            const content = await route.component(params);

            // Update content
            container.innerHTML = content;

            // Hide loading and show content
            if (loadingIndicator) {
                loadingIndicator.classList.add('hidden');
            }
            container.classList.add('loaded');

            // Emit component loaded event
            eventBus.emit('component:loaded', { route, params });

        } catch (error) {
            throw new Error(`Component loading failed: ${error.message}`);
        }
    }

    /**
     * Handle route from URL
     */
    handleRoute() {
        const hash = window.location.hash.substring(1) || 'dashboard';
        const [path, ...paramParts] = hash.split('/');
        const params = this.parseParams(paramParts.join('/'));
        this.navigate(path, params);
    }

    /**
     * Parse route parameters
     * @param {string} paramString - Parameter string
     * @returns {Object} Parsed parameters
     */
    parseParams(paramString) {
        const params = {};
        if (!paramString) return params;

        const parts = paramString.split('/');
        for (let i = 0; i < parts.length; i += 2) {
            if (parts[i] && parts[i + 1]) {
                params[parts[i]] = decodeURIComponent(parts[i + 1]);
            }
        }
        return params;
    }

    /**
     * Update active navigation items
     * @param {string} path - Current route path
     */
    updateActiveNav(path) {
        // Remove all active classes
        document.querySelectorAll('.nav-item, .sidebar-footer-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current route
        const activeItem = document.querySelector(`.nav-item[data-route="${path}"], .sidebar-footer-item[data-route="${path}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }

    /**
     * Add before navigation hook
     * @param {Function} hook - Hook function
     */
    beforeEach(hook) {
        this.beforeHooks.push(hook);
    }

    /**
     * Add after navigation hook
     * @param {Function} hook - Hook function
     */
    afterEach(hook) {
        this.afterHooks.push(hook);
    }

    /**
     * Get current route
     * @returns {Object} Current route
     */
    getCurrentRoute() {
        return this.currentRoute;
    }

    /**
     * Check if route exists
     * @param {string} path - Route path
     * @returns {boolean} Route exists
     */
    hasRoute(path) {
        return this.routes.has(path);
    }
}

// Export singleton instance
export default new Router();