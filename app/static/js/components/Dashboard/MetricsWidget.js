/**
 * MetricsWidget - Displays key SEO metrics
 * Shows SEO score, impressions, clicks, CTR, and position
 */
export class MetricsWidget {
    constructor() {
        this.metrics = null;
    }

    /**
     * Initialize metrics widget
     */
    async init(metrics) {
        this.metrics = metrics;
        this.attachEventListeners();
    }

    /**
     * Render metrics HTML
     */
    render(metrics) {
        if (!metrics) {
            return this.renderEmpty();
        }

        return `
            <div class="overview">
                <h2>Overview</h2>
                <div class="metrics-grid">
                    ${this.renderMetricCard('SEO Score', metrics.seo_score, 100, 'score')}
                    ${this.renderMetricCard('Impressions', metrics.total_impressions, null, 'impressions')}
                    ${this.renderMetricCard('Clicks', metrics.total_clicks, null, 'clicks')}
                    ${this.renderMetricCard('Avg. CTR', metrics.average_ctr, null, 'ctr')}
                    ${this.renderMetricCard('Avg. Position', metrics.average_position, null, 'position')}
                </div>
            </div>
        `;
    }

    /**
     * Render individual metric card
     */
    renderMetricCard(label, value, max, type) {
        const formattedValue = this.formatValue(value, type);
        const changeText = this.getChangeText(type);
        const icon = this.getMetricIcon(type);

        return `
            <div class="metric-card">
                <div class="metric-icon-container">
                    ${icon}
                </div>
                <div class="metric-content">
                    <div class="metric-label">${label}</div>
                    <div class="metric-value">${formattedValue}</div>
                    ${changeText ? `<div class="metric-change">${changeText}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Format metric value based on type
     */
    formatValue(value, type) {
        if (value === null || value === undefined) {
            return '—';
        }

        switch (type) {
            case 'score':
                return `${Math.round(value)}`;
            case 'impressions':
            case 'clicks':
                return this.formatNumber(value);
            case 'ctr':
                return `${(value * 100).toFixed(1)}%`;
            case 'position':
                return value.toFixed(1);
            default:
                return value;
        }
    }

    /**
     * Format large numbers
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return `${(num / 1000000).toFixed(1)}M`;
        } else if (num >= 1000) {
            return `${(num / 1000).toFixed(1)}K`;
        }
        return num.toString();
    }

    /**
     * Get change text for metric
     */
    getChangeText(type) {
        // This could be enhanced to show actual change data
        // For now, returning static text
        switch (type) {
            case 'impressions':
                return '↑ 12% from last period';
            case 'clicks':
                return '↑ 8% from last period';
            default:
                return '';
        }
    }

    /**
     * Get metric icon
     */
    getMetricIcon(type) {
        const icons = {
            score: '<svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>',
            impressions: '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>',
            clicks: '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2z"/></svg>',
            ctr: '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
            position: '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>'
        };

        return icons[type] || '';
    }

    /**
     * Render empty state
     */
    renderEmpty() {
        return `
            <div class="overview">
                <h2>Overview</h2>
                <div style="background: white; border-radius: 12px; padding: 48px; text-align: center;">
                    <p style="color: #6B7280;">No metrics data available</p>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Add any metric-specific event listeners here
    }

    /**
     * Cleanup
     */
    destroy() {
        // Clean up any event listeners or intervals
    }
}

export default MetricsWidget;