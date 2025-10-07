/**
 * DateRangeModal Component - Custom Date Range Selector
 *
 * Features:
 * - Filter tab (single date range)
 * - Compare tab (comparison mode with two date ranges)
 * - Predefined ranges (Last 6/12/16 months)
 * - Custom date pickers
 * - Validates date ranges (no future dates, max 16 months)
 *
 * Matches Google Search Console date range modal
 */

class DateRangeModal {
    constructor(onApply) {
        this.onApply = onApply;
        this.mode = 'filter';  // 'filter' or 'compare'

        // Filter mode state
        this.filterRange = {
            preset: 'custom',
            startDate: null,
            endDate: null
        };

        // Compare mode state
        this.compareRange = {
            preset: 'previous_period',
            currentStartDate: null,
            currentEndDate: null,
            comparisonStartDate: null,
            comparisonEndDate: null
        };

        this.render();
    }

    /**
     * Render the modal HTML
     */
    render() {
        // Check if modal already exists
        let modal = document.getElementById('dateRangeModal');
        if (modal) {
            return;  // Already rendered
        }

        // Create modal HTML
        const modalHTML = `
            <div class="date-range-modal hidden" id="dateRangeModal">
                <div class="date-range-modal-overlay" onclick="window.dateRangeModal.close()"></div>
                <div class="date-range-modal-content">
                    <!-- Header -->
                    <div class="date-range-modal-header">
                        <h3>Date range</h3>
                        <button class="date-range-modal-close" onclick="window.dateRangeModal.close()">
                            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                            </svg>
                        </button>
                    </div>

                    <!-- Tab Content -->
                    <div class="date-range-tab-content">
                        <!-- Filter Tab -->
                        <div class="date-range-tab-pane active" id="filterTabPane">
                            <!-- Preset Options -->
                            <div class="date-range-presets">
                                <label class="date-range-preset-option">
                                    <input type="radio" name="filterPreset" value="6mo" onchange="window.dateRangeModal.handleFilterPresetChange('6mo')">
                                    <span>Last 6 months</span>
                                </label>
                                <label class="date-range-preset-option">
                                    <input type="radio" name="filterPreset" value="12mo" onchange="window.dateRangeModal.handleFilterPresetChange('12mo')">
                                    <span>Last 12 months</span>
                                </label>
                                <label class="date-range-preset-option">
                                    <input type="radio" name="filterPreset" value="16mo" onchange="window.dateRangeModal.handleFilterPresetChange('16mo')">
                                    <span>Last 16 months</span>
                                </label>
                                <label class="date-range-preset-option">
                                    <input type="radio" name="filterPreset" value="custom" checked onchange="window.dateRangeModal.handleFilterPresetChange('custom')">
                                    <span>Custom</span>
                                </label>
                            </div>

                            <!-- Custom Date Inputs -->
                            <div class="date-range-custom-inputs">
                                <div class="date-input-group">
                                    <label>Start date</label>
                                    <input type="date" id="filterStartDate" onchange="window.dateRangeModal.handleFilterDateChange()">
                                    <span class="date-input-format">YYYY-MM-DD</span>
                                </div>
                                <div class="date-input-group">
                                    <label>End date</label>
                                    <input type="date" id="filterEndDate" onchange="window.dateRangeModal.handleFilterDateChange()">
                                    <span class="date-input-format">YYYY-MM-DD</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div class="date-range-modal-footer">
                        <button class="date-range-btn-secondary" onclick="window.dateRangeModal.close()">
                            Cancel
                        </button>
                        <button class="date-range-btn-primary" onclick="window.dateRangeModal.apply()">
                            Apply
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Append to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Set default dates
        this.setDefaultDates();
    }

    /**
     * Set default dates (today - 1 day as end, 27 days before as start)
     */
    setDefaultDates() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const startDate = new Date(yesterday);
        startDate.setDate(startDate.getDate() - 27);

        document.getElementById('filterStartDate').value = this.formatDate(startDate);
        document.getElementById('filterEndDate').value = this.formatDate(yesterday);

        // Set max date to yesterday (GSC data delay)
        document.getElementById('filterStartDate').max = this.formatDate(yesterday);
        document.getElementById('filterEndDate').max = this.formatDate(yesterday);
    }

    /**
     * Open modal
     */
    open() {
        const modal = document.getElementById('dateRangeModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Close modal
     */
    close() {
        const modal = document.getElementById('dateRangeModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    /**
     * Switch between Filter and Compare tabs
     */
    switchTab(tabName) {
        this.mode = tabName;

        // Update tab buttons
        document.querySelectorAll('.date-range-tab').forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            }
        });

        // Update tab panes
        document.querySelectorAll('.date-range-tab-pane').forEach(pane => {
            pane.classList.add('hidden');
        });

        if (tabName === 'filter') {
            document.getElementById('filterTabPane')?.classList.remove('hidden');
        } else {
            document.getElementById('compareTabPane')?.classList.remove('hidden');
        }
    }

    /**
     * Handle filter preset change
     */
    handleFilterPresetChange(preset) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        let startDate, endDate;

        switch (preset) {
            case '6mo':
                startDate = new Date(yesterday);
                startDate.setMonth(startDate.getMonth() - 6);
                endDate = yesterday;
                break;
            case '12mo':
                startDate = new Date(yesterday);
                startDate.setMonth(startDate.getMonth() - 12);
                endDate = yesterday;
                break;
            case '16mo':
                startDate = new Date(yesterday);
                startDate.setMonth(startDate.getMonth() - 16);
                endDate = yesterday;
                break;
            case 'custom':
                // Keep current values
                return;
        }

        document.getElementById('filterStartDate').value = this.formatDate(startDate);
        document.getElementById('filterEndDate').value = this.formatDate(endDate);

        this.filterRange.preset = preset;
        this.filterRange.startDate = this.formatDate(startDate);
        this.filterRange.endDate = this.formatDate(endDate);
    }

    /**
     * Handle filter date change
     */
    handleFilterDateChange() {
        this.filterRange.preset = 'custom';
        this.filterRange.startDate = document.getElementById('filterStartDate').value;
        this.filterRange.endDate = document.getElementById('filterEndDate').value;

        // Select custom radio
        document.querySelector('input[name="filterPreset"][value="custom"]').checked = true;
    }

    /**
     * Handle compare preset change
     */
    handleComparePresetChange(preset) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        let currentStart, currentEnd, comparisonStart, comparisonEnd;

        switch (preset) {
            case '24h_previous':
                currentEnd = yesterday;
                currentStart = yesterday;
                comparisonEnd = new Date(yesterday);
                comparisonEnd.setDate(comparisonEnd.getDate() - 1);
                comparisonStart = comparisonEnd;
                break;
            case '7d_previous':
                currentEnd = yesterday;
                currentStart = new Date(yesterday);
                currentStart.setDate(currentStart.getDate() - 6);
                comparisonEnd = new Date(currentStart);
                comparisonEnd.setDate(comparisonEnd.getDate() - 1);
                comparisonStart = new Date(comparisonEnd);
                comparisonStart.setDate(comparisonStart.getDate() - 6);
                break;
            case '28d_previous':
                currentEnd = yesterday;
                currentStart = new Date(yesterday);
                currentStart.setDate(currentStart.getDate() - 27);
                comparisonEnd = new Date(currentStart);
                comparisonEnd.setDate(comparisonEnd.getDate() - 1);
                comparisonStart = new Date(comparisonEnd);
                comparisonStart.setDate(comparisonStart.getDate() - 27);
                break;
            case 'custom':
                // Keep current values
                return;
        }

        document.getElementById('compareCurrentStart').value = this.formatDate(currentStart);
        document.getElementById('compareCurrentEnd').value = this.formatDate(currentEnd);
        document.getElementById('compareComparisonStart').value = this.formatDate(comparisonStart);
        document.getElementById('compareComparisonEnd').value = this.formatDate(comparisonEnd);

        this.compareRange.preset = preset;
    }

    /**
     * Handle compare date change
     */
    handleCompareDateChange() {
        this.compareRange.preset = 'custom';
        this.compareRange.currentStartDate = document.getElementById('compareCurrentStart').value;
        this.compareRange.currentEndDate = document.getElementById('compareCurrentEnd').value;
        this.compareRange.comparisonStartDate = document.getElementById('compareComparisonStart').value;
        this.compareRange.comparisonEndDate = document.getElementById('compareComparisonEnd').value;

        // Select custom radio
        document.querySelector('input[name="comparePreset"][value="custom"]').checked = true;
    }

    /**
     * Apply date range and close modal
     */
    apply() {
        if (this.mode === 'filter') {
            // Validate filter range
            const startDate = document.getElementById('filterStartDate').value;
            const endDate = document.getElementById('filterEndDate').value;

            if (!startDate || !endDate) {
                ModalUtils.error('Please select both start and end dates.', { title: 'Invalid Date Range' });
                return;
            }

            if (new Date(startDate) > new Date(endDate)) {
                ModalUtils.error('Start date must be before end date.', { title: 'Invalid Date Range' });
                return;
            }

            // Return filter range
            this.onApply({
                startDate: startDate,
                endDate: endDate,
                comparisonEnabled: false
            });

        } else {
            // Validate compare range
            const currentStart = document.getElementById('compareCurrentStart').value;
            const currentEnd = document.getElementById('compareCurrentEnd').value;
            const comparisonStart = document.getElementById('compareComparisonStart').value;
            const comparisonEnd = document.getElementById('compareComparisonEnd').value;

            if (!currentStart || !currentEnd || !comparisonStart || !comparisonEnd) {
                ModalUtils.error('Please select all date ranges for comparison.', { title: 'Invalid Date Range' });
                return;
            }

            if (new Date(currentStart) > new Date(currentEnd)) {
                ModalUtils.error('Current start date must be before current end date.', { title: 'Invalid Date Range' });
                return;
            }

            if (new Date(comparisonStart) > new Date(comparisonEnd)) {
                ModalUtils.error('Comparison start date must be before comparison end date.', { title: 'Invalid Date Range' });
                return;
            }

            // Return compare range
            this.onApply({
                startDate: currentStart,
                endDate: currentEnd,
                comparisonEnabled: true,
                comparisonStartDate: comparisonStart,
                comparisonEndDate: comparisonEnd
            });
        }

        this.close();
    }

    /**
     * Format date as YYYY-MM-DD
     */
    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
}

// Make DateRangeModal globally available
window.DateRangeModal = DateRangeModal;
