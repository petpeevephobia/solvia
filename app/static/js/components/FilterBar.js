/**
 * FilterBar Component - Google Search Console Style Filter UI
 *
 * Features:
 * - Quick date range buttons (24h, 7d, 28d, 3mo, Custom)
 * - Search type dropdown (Web, Image, Video, etc.)
 * - Add filter button
 * - Active filter pills
 * - Reset filters
 *
 * Matches Solvia design system (#EC6019 orange theme)
 */

class FilterBar {
    constructor(containerId, onFilterChange) {
        this.containerId = containerId;
        this.onFilterChange = onFilterChange;

        // Current filter state
        this.currentFilters = {
            datePreset: '28d',  // Default to 28 days like current implementation
            startDate: null,
            endDate: null,
            searchType: 'web',
            dimensionFilters: [],
            comparisonEnabled: false,
            comparisonStartDate: null,
            comparisonEndDate: null
        };

        this.isLoading = false;
    }

    /**
     * Render the filter bar HTML
     */
    render() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`FilterBar: Container ${this.containerId} not found`);
            return;
        }

        container.innerHTML = `
            <div class="filter-bar" id="gsc-filter-bar">
                <!-- Single Row Filter Content -->
                <div class="filter-content">
                    <!-- Left Side: Filter Controls -->
                    <div class="filter-controls-left">
                        <!-- Quick Date Range Buttons -->
                        <div class="date-quick-buttons">
                            <button class="filter-btn" data-preset="24h" title="Last 24 hours">
                                24h
                            </button>
                            <button class="filter-btn" data-preset="7d" title="Last 7 days">
                                7d
                            </button>
                            <button class="filter-btn active" data-preset="28d" title="Last 28 days">
                                28d
                            </button>
                            <button class="filter-btn" data-preset="3mo" title="Last 3 months">
                                3mo
                            </button>
                            <button class="filter-btn filter-btn-custom" data-preset="custom" title="Custom date range">
                                <span>Custom</span>
                                <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20" style="margin-left: 4px;">
                                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Right Side: Last Update Info -->
                    <div class="filter-meta">
                        <span class="filter-meta-text" id="filterMetaText">Last update: Just now</span>
                    </div>
                </div>

                <!-- Filter Pills (Active Filters) -->
                <div class="filter-pills" id="filterPills">
                    <!-- Pills will be dynamically added here -->
                </div>

                <!-- Loading Overlay -->
                <div class="filter-loading-overlay hidden" id="filterLoadingOverlay">
                    <div class="filter-loading-spinner"></div>
                    <span>Applying filters...</span>
                </div>
            </div>
        `;

        this.attachEventListeners();

        // Apply default filters on initialization
        this.applyFilters();
    }

    /**
     * Attach event listeners to filter controls
     */
    attachEventListeners() {
        // Quick date buttons
        const dateButtons = document.querySelectorAll('.date-quick-buttons .filter-btn');
        dateButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleDatePresetClick(e));
        });

        // Reset filters button
        const resetFiltersBtn = document.getElementById('resetFiltersBtn');
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', () => this.handleResetFilters());
        }
    }

    /**
     * Handle quick date preset button click
     */
    async handleDatePresetClick(e) {
        const preset = e.currentTarget.dataset.preset;

        if (preset === 'custom') {
            // Open custom date modal
            this.openCustomDateModal();
            return;
        }

        // Update active button state
        document.querySelectorAll('.date-quick-buttons .filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        e.currentTarget.classList.add('active');

        // Update current filters
        this.currentFilters.datePreset = preset;
        this.currentFilters.startDate = null;
        this.currentFilters.endDate = null;

        // Apply filters
        await this.applyFilters();
    }

    /**
     * Handle reset filters
     */
    async handleResetFilters() {
        // Reset to default state
        this.currentFilters = {
            datePreset: '28d',
            startDate: null,
            endDate: null,
            searchType: 'web',
            dimensionFilters: [],
            comparisonEnabled: false,
            comparisonStartDate: null,
            comparisonEndDate: null
        };

        // Reset UI
        document.querySelectorAll('.date-quick-buttons .filter-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.preset === '28d') {
                btn.classList.add('active');
            }
        });

        document.querySelectorAll('.search-type-option').forEach(opt => {
            opt.classList.remove('active');
            opt.querySelector('svg').setAttribute('fill', 'transparent');
            if (opt.dataset.type === 'web') {
                opt.classList.add('active');
                opt.querySelector('svg').setAttribute('fill', '#EC6019');
            }
        });

        document.getElementById('searchTypeLabel').textContent = 'Web';
        document.getElementById('resetFiltersBtn')?.classList.add('hidden');

        // Apply default filters
        await this.applyFilters();
    }

    /**
     * Open custom date range modal
     */
    openCustomDateModal() {
        // Initialize DateRangeModal if not exists
        if (!window.dateRangeModal) {
            window.dateRangeModal = new DateRangeModal((dateRange) => {
                this.handleCustomDateRange(dateRange);
            });
        }
        window.dateRangeModal.open();
    }

    /**
     * Handle custom date range selection
     */
    async handleCustomDateRange(dateRange) {
        console.log('[FilterBar] Custom date range selected:', dateRange);

        // Update current filters
        this.currentFilters.startDate = dateRange.startDate;
        this.currentFilters.endDate = dateRange.endDate;
        this.currentFilters.datePreset = null;

        if (dateRange.comparisonEnabled) {
            this.currentFilters.comparisonEnabled = true;
            this.currentFilters.comparisonStartDate = dateRange.comparisonStartDate;
            this.currentFilters.comparisonEndDate = dateRange.comparisonEndDate;
        } else {
            this.currentFilters.comparisonEnabled = false;
            this.currentFilters.comparisonStartDate = null;
            this.currentFilters.comparisonEndDate = null;
        }

        // Update active button state
        document.querySelectorAll('.date-quick-buttons .filter-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.preset === 'custom') {
                btn.classList.add('active');
            }
        });

        // Apply filters
        await this.applyFilters();
    }

    /**
     * Apply current filters and fetch data
     */
    async applyFilters() {
        if (this.isLoading) {
            console.log('[FilterBar] Already loading, skipping...');
            return;
        }

        try {
            this.isLoading = true;
            this.showLoading(true);

            console.log('[FilterBar] Applying filters:', this.currentFilters);

            // Calculate date range
            let dateRange;
            if (this.currentFilters.startDate && this.currentFilters.endDate) {
                // Custom date range
                dateRange = {
                    start_date: this.currentFilters.startDate,
                    end_date: this.currentFilters.endDate
                };
            } else {
                // Calculate preset date range on frontend
                dateRange = this.calculatePresetDates(this.currentFilters.datePreset);
            }

            // Build filter request
            const filterRequest = {
                start_date: dateRange.start_date,
                end_date: dateRange.end_date,
                search_type: this.currentFilters.searchType,
                dimensions: ['date'],
                comparison_enabled: false  // Comparison removed for now
            };

            console.log('[FilterBar] Filter request:', filterRequest);

            // Call API
            const apiResponse = await fetch('/auth/gsc/filter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getToken()}`
                },
                body: JSON.stringify(filterRequest)
            });

            if (!apiResponse.ok) {
                throw new Error(`API error: ${apiResponse.statusText}`);
            }

            const result = await apiResponse.json();
            console.log('[FilterBar] Filter result:', result);

            // Update meta text
            const dateRangeText = `${dateRange.start_date} to ${dateRange.end_date}`;
            this.updateMetaText(dateRangeText, this.currentFilters.searchType);

            // Trigger callback with filtered data AND date range
            if (this.onFilterChange) {
                this.onFilterChange({
                    metrics: result.metrics,
                    dateRange: dateRange
                });
            }

        } catch (error) {
            console.error('[FilterBar] Error applying filters:', error);
            ModalUtils.error(
                'Failed to apply filters. Please try again or refresh the page.',
                { title: 'Filter Error' }
            );
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    /**
     * Calculate date range for presets
     */
    calculatePresetDates(preset) {
        const today = new Date();
        const endDate = new Date(today);
        endDate.setDate(endDate.getDate() - 1); // Yesterday (GSC has 1-day delay)

        let startDate = new Date(endDate);

        switch(preset) {
            case '24h':
                startDate.setDate(startDate.getDate() - 1);
                break;
            case '7d':
                startDate.setDate(startDate.getDate() - 7);
                break;
            case '28d':
                startDate.setDate(startDate.getDate() - 28);
                break;
            case '3mo':
                startDate.setMonth(startDate.getMonth() - 3);
                break;
            default:
                startDate.setDate(startDate.getDate() - 28);
        }

        return {
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0]
        };
    }

    /**
     * Show/hide loading overlay
     */
    showLoading(show) {
        const overlay = document.getElementById('filterLoadingOverlay');
        if (overlay) {
            if (show) {
                overlay.classList.remove('hidden');
            } else {
                overlay.classList.add('hidden');
            }
        }
    }

    /**
     * Update meta text with current filter info
     */
    updateMetaText(dateRange, searchType) {
        const metaText = document.getElementById('filterMetaText');
        if (metaText) {
            let text = `${dateRange}`;
            if (searchType && searchType !== 'web') {
                text += ` • ${searchType.charAt(0).toUpperCase() + searchType.slice(1)} search`;
            }
            metaText.textContent = text;
        }
    }

    /**
     * Get authentication token
     */
    getToken() {
        return localStorage.getItem('auth_token') || localStorage.getItem('token') || '';
    }
}

// Make FilterBar globally available
window.FilterBar = FilterBar;
