/**
 * DashboardController - Manages dashboard view and data
 * Coordinates between metrics, issues, and chat components
 */
import apiClient from '../../services/ApiClient.js';
import eventBus from '../../core/EventBus.js';
import { MetricsWidget } from './MetricsWidget.js';
import { IssuesWidget } from './IssuesWidget.js';
import { ChatWidget } from './ChatWidget.js';

export class DashboardController {
    constructor() {
        this.website = null;
        this.metricsWidget = new MetricsWidget();
        this.issuesWidget = new IssuesWidget();
        this.chatWidget = new ChatWidget();
        this.refreshInterval = null;
    }

    /**
     * Initialize dashboard
     */
    async init() {
        try {
            // Get selected website
            this.website = await this.getSelectedWebsite();

            if (!this.website) {
                return this.renderWebsiteSelection();
            }

            // Load dashboard data
            await this.loadDashboardData();

            // Setup auto-refresh
            this.startAutoRefresh();

            // Setup event listeners
            this.setupEventListeners();

        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            eventBus.emit('dashboard:error', error);
        }
    }

    /**
     * Get selected website from storage
     */
    async getSelectedWebsite() {
        const stored = localStorage.getItem('selectedWebsite');
        if (stored) {
            return JSON.parse(stored);
        }

        // Fetch user settings
        try {
            const settings = await apiClient.get('/api/auth/user-settings');
            if (settings.selected_website) {
                const website = {
                    url: settings.selected_website,
                    name: settings.selected_website
                };
                localStorage.setItem('selectedWebsite', JSON.stringify(website));
                return website;
            }
        } catch (error) {
            console.error('Failed to fetch user settings:', error);
        }

        return null;
    }

    /**
     * Load dashboard data
     */
    async loadDashboardData() {
        const container = document.getElementById('app-content');

        // Render skeleton
        container.innerHTML = this.renderSkeleton();

        try {
            // Fetch dashboard data
            const dashboardData = await apiClient.post('/api/data_pipeline/dashboard', {
                website_url: this.website.url
            });

            // Render dashboard with data
            container.innerHTML = this.render(dashboardData);

            // Initialize widgets
            await this.metricsWidget.init(dashboardData.metrics);
            await this.issuesWidget.init(dashboardData.current_issues);
            await this.chatWidget.init(this.website.url);

            // Mark as loaded
            document.body.classList.add('loaded');
            eventBus.emit('dashboard:loaded', dashboardData);

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            container.innerHTML = this.renderError(error);
        }
    }

    /**
     * Render dashboard HTML
     */
    render(data) {
        return `
            <div style="padding: 32px; max-width: 1400px; margin: 0 auto;">
                <!-- Header -->
                <div style="margin-bottom: 32px;">
                    <h1 style="font-size: 32px; font-weight: 700; color: #111827; margin-bottom: 8px;">
                        SEO Dashboard
                    </h1>
                    <p style="color: #6B7280; font-size: 16px;">
                        Monitoring ${this.website.name || this.website.url}
                    </p>
                </div>

                <!-- Metrics Section -->
                <div id="metrics-container">
                    ${this.metricsWidget.render(data.metrics)}
                </div>

                <!-- Issues Section -->
                <div id="issues-container">
                    ${this.issuesWidget.render(data.current_issues)}
                </div>

                <!-- Chat Section -->
                <div id="chat-container">
                    ${this.chatWidget.render()}
                </div>
            </div>
        `;
    }

    /**
     * Render skeleton loading state
     */
    renderSkeleton() {
        return `
            <div style="padding: 32px; max-width: 1400px; margin: 0 auto;">
                <!-- Header Skeleton -->
                <div style="margin-bottom: 32px;">
                    <div class="skeleton" style="height: 32px; width: 200px; margin-bottom: 12px;"></div>
                    <div class="skeleton" style="height: 16px; width: 300px;"></div>
                </div>

                <!-- Metrics Skeleton -->
                <div class="metrics-grid">
                    ${[1, 2, 3, 4].map(() => `
                        <div class="skeleton-metric-card">
                            <div class="skeleton-metric-content">
                                <div class="skeleton-metric-label"></div>
                                <div class="skeleton-metric-value"></div>
                                <div class="skeleton-metric-change"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>

                <!-- Issues Skeleton -->
                <div style="margin-top: 32px;">
                    <div class="skeleton" style="height: 24px; width: 150px; margin-bottom: 20px;"></div>
                    <div class="issues-grid">
                        ${[1, 2, 3].map(() => `
                            <div class="skeleton-issue-card">
                                <div class="skeleton-header">
                                    <div class="skeleton-icon"></div>
                                    <div class="skeleton-title"></div>
                                </div>
                                <div class="skeleton-description"></div>
                                <div class="skeleton-description short"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render website selection prompt
     */
    renderWebsiteSelection() {
        const container = document.getElementById('app-content');
        container.innerHTML = `
            <div style="padding: 32px; max-width: 800px; margin: 0 auto; text-align: center;">
                <div style="background: white; border-radius: 16px; padding: 48px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <h2 style="font-size: 24px; font-weight: 600; color: #111827; margin-bottom: 16px;">
                        Welcome to Solvia Dashboard
                    </h2>
                    <p style="color: #6B7280; font-size: 16px; margin-bottom: 32px;">
                        Please select a website to monitor from Settings
                    </p>
                    <button onclick="window.location.hash='settings'"
                            style="background: #EC6019; color: white; padding: 12px 24px;
                                   border: none; border-radius: 8px; font-size: 14px;
                                   font-weight: 500; cursor: pointer;">
                        Go to Settings
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render error state
     */
    renderError(error) {
        return `
            <div style="padding: 32px; max-width: 800px; margin: 0 auto; text-align: center;">
                <div style="background: white; border-radius: 16px; padding: 48px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 48px; margin-bottom: 24px;">⚠️</div>
                    <h2 style="font-size: 24px; font-weight: 600; color: #111827; margin-bottom: 16px;">
                        Failed to Load Dashboard
                    </h2>
                    <p style="color: #6B7280; font-size: 16px; margin-bottom: 32px;">
                        ${error.message || 'An unexpected error occurred'}
                    </p>
                    <button onclick="location.reload()"
                            style="background: #EC6019; color: white; padding: 12px 24px;
                                   border: none; border-radius: 8px; font-size: 14px;
                                   font-weight: 500; cursor: pointer;">
                        Retry
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for audit completion
        eventBus.on('audit:completed', () => {
            this.loadDashboardData();
        });

        // Listen for website change
        eventBus.on('website:changed', () => {
            this.website = JSON.parse(localStorage.getItem('selectedWebsite'));
            this.loadDashboardData();
        });
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        // Refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 5 * 60 * 1000);
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.metricsWidget.destroy();
        this.issuesWidget.destroy();
        this.chatWidget.destroy();
    }
}

// Export for route component
export default DashboardController;