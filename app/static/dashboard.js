// ... all JavaScript code from the <script>...</script> block of dashboard.html ... 
// Global chart instances
let organicTrafficChart = null;
let impressionsChart = null;
let isRefreshingToken = false; // Flag to prevent multiple refresh attempts

// Global variables for metric data
window.metricsData = {
    summary: {}
};
let refreshAttempts = 0; // Track refresh attempts to prevent infinite loops
const MAX_REFRESH_ATTEMPTS = 3; // Maximum number of refresh attempts
let lastRefreshTime = 0; // Track when we last attempted a refresh
let isRedirecting = false; // Flag to prevent multiple redirects
let consecutiveFailures = 0; // Track consecutive API failures

const METRIC_GROUPS = [
    { key: 'organic_impressions', label: 'Organic Traffic & Impressions' },
    { key: 'visibility', label: 'Visibility Performance' },
    { key: 'ai', label: 'AI Analysis' }
];
let metricsLoadingState = {};

// Check if we're in an infinite loop situation
function checkForInfiniteLoop() {
    if (consecutiveFailures > 5) {
        clearInvalidToken();
        return true;
    }
    return false;
}

function isValidTokenFormat(token) {
    if (!token || typeof token !== 'string') {
        return false;
    }
    
    // Check if token has the correct JWT format (3 parts separated by dots)
    const parts = token.split('.');
    
    if (parts.length !== 3) {
        return false;
    }
    
    // Try to decode the payload to check if it's valid JSON
    try {
        const payload = JSON.parse(atob(parts[1]));
        
        // Check for required fields
        if (!payload || typeof payload !== 'object') {
            return false;
        }
        
        // Check for required JWT fields
        if (!payload.sub) {
            return false;
        }
        
        if (!payload.exp) {
            return false;
        }
        
        // Check expiration
        const currentTime = Math.floor(Date.now() / 1000);
        const isExpired = payload.exp < currentTime;
        
        return true;
    } catch (error) {
        return false;
    }
}

function clearInvalidToken() {
    const oldToken = localStorage.getItem('auth_token');
    localStorage.removeItem('auth_token');
    if (!isRedirecting) {
        isRedirecting = true;
        window.location.href = '/ui';
    }
}

function checkAuth() {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
        if (!isRedirecting) {
            isRedirecting = true;
        window.location.href = '/ui';
        }
        return false;
    }

    // First, validate token format
    if (!isValidTokenFormat(token)) {
        clearInvalidToken();
        return false;
    }

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const userEmail = payload.email || payload.sub || 'user@example.com';
        const userName = userEmail.includes('@') ? userEmail.split('@')[0] : userEmail;
        
        // Check if token is expired
        const currentTime = Math.floor(Date.now() / 1000);
        const timeSinceLastRefresh = currentTime - lastRefreshTime;
        
        if (payload.exp && payload.exp < currentTime) {
            
            // Prevent rapid refresh attempts - wait at least 5 seconds between attempts
            if (timeSinceLastRefresh < 5) {
                if (!isRedirecting) {
                    isRedirecting = true;
                    window.location.href = '/ui';
                }
                return false;
            }
            
            if (!isRefreshingToken && refreshAttempts < MAX_REFRESH_ATTEMPTS) {
                lastRefreshTime = currentTime;
                refreshToken();
            } else {
                if (!isRedirecting) {
                    isRedirecting = true;
                    window.location.href = '/ui';
                }
            }
            return false;
        }
        
        document.getElementById('userEmail').textContent = userEmail;
        document.getElementById('userAvatar').textContent = userName.charAt(0).toUpperCase();
        
        // Update mobile menu user info
        document.getElementById('mobileMenuEmail').textContent = userEmail;
        document.getElementById('mobileMenuAvatar').textContent = userName.charAt(0).toUpperCase();
        
        return true; // Authentication successful
    } catch (error) {
        console.error('[TOKEN DEBUG] Error decoding token:', error);
        clearInvalidToken();
        return false; // Authentication failed
    }
}

async function refreshToken() {
    if (isRefreshingToken) {
        console.log('Token refresh already in progress, skipping...');
        return;
    }
    
    if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
        console.log('Max refresh attempts reached, redirecting to login');
        if (!isRedirecting) {
            isRedirecting = true;
        window.location.href = '/ui';
        }
        return;
    }
    
    isRefreshingToken = true;
    refreshAttempts++;
    
    try {
        const token = localStorage.getItem('auth_token');
        
        // Validate token format before attempting refresh
        if (!isValidTokenFormat(token)) {
            console.log('Invalid token format in refreshToken, clearing token');
            clearInvalidToken();
            return;
        }
        
        const response = await fetch('/auth/refresh-token', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('auth_token', data.access_token);
            refreshAttempts = 0; // Reset attempts on success
            lastRefreshTime = 0; // Reset last refresh time
            
            // Verify the new token is not expired
            try {
                const newPayload = JSON.parse(atob(data.access_token.split('.')[1]));
                const currentTime = Math.floor(Date.now() / 1000);
                
                if (newPayload.exp && newPayload.exp < currentTime) {
                    console.log('New token is also expired, redirecting to login');
                    if (!isRedirecting) {
                        isRedirecting = true;
                        window.location.href = '/ui';
                    }
                    return;
                }
                
                // Update UI with the user info from the new token
                const userEmail = newPayload.email || newPayload.sub || 'user@example.com';
                const userName = userEmail.includes('@') ? userEmail.split('@')[0] : userEmail;
                
                document.getElementById('userEmail').textContent = userEmail;
                document.getElementById('userAvatar').textContent = userName.charAt(0).toUpperCase();
                document.getElementById('mobileMenuEmail').textContent = userEmail;
                document.getElementById('mobileMenuAvatar').textContent = userName.charAt(0).toUpperCase();
            } catch (error) {
                console.error('Error updating UI after token refresh:', error);
            }
        } else {
            console.error('Failed to refresh token');
            clearInvalidToken();
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
        clearInvalidToken();
    } finally {
        isRefreshingToken = false;
    }
}

async function apiCall(url, options = {}) {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        if (!isRedirecting) {
            isRedirecting = true;
            window.location.href = '/ui';
        }
        return;
    }

    // Validate token format before making API calls
    if (!isValidTokenFormat(token)) {
        console.log('[TOKEN DEBUG] Invalid token format in apiCall, clearing token');
        clearInvalidToken();
        return;
    }

    // Check for infinite loop before making the call
    if (checkForInfiniteLoop()) {
        return;
    }

    // Add authorization header
    options.headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    try {
        const response = await fetch(url, options);
        
        // Reset consecutive failures on success
        if (response.ok) {
            consecutiveFailures = 0;
        }
        
        // If token is expired, try to refresh and retry
        if (response.status === 401) {
            consecutiveFailures++;
            console.log('[TOKEN DEBUG] 401 error, consecutive failures:', consecutiveFailures);
            
            // Check for infinite loop
            if (checkForInfiniteLoop()) {
                return;
            }
            
            console.log('Token expired, refreshing...');
            
            // Prevent multiple refresh attempts
            if (isRefreshingToken) {
                console.log('Token refresh already in progress, redirecting to login');
                if (!isRedirecting) {
                    isRedirecting = true;
                    window.location.href = '/ui';
                }
                return;
            }
            
            // Check if we've exceeded max attempts
            if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
                console.log('Max refresh attempts reached in apiCall, redirecting to login');
                if (!isRedirecting) {
                    isRedirecting = true;
                    window.location.href = '/ui';
                }
                return;
            }
            
            // Check if we've tried to refresh too recently
            const currentTime = Math.floor(Date.now() / 1000);
            if (currentTime - lastRefreshTime < 5) {
                console.log('Too soon since last refresh attempt, redirecting to login');
                if (!isRedirecting) {
                    isRedirecting = true;
                    window.location.href = '/ui';
                }
                return;
            }
            
            isRefreshingToken = true;
            refreshAttempts++;
            lastRefreshTime = currentTime;
            
            try {
                const refreshResponse = await fetch('/auth/refresh-token', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (refreshResponse.ok) {
                    const data = await refreshResponse.json();
                    localStorage.setItem('auth_token', data.access_token);
                    refreshAttempts = 0; // Reset on success
                    lastRefreshTime = 0; // Reset last refresh time
                    consecutiveFailures = 0; // Reset failures on successful refresh
                    
                    // Verify the new token is not expired
                    try {
                        const newPayload = JSON.parse(atob(data.access_token.split('.')[1]));
                        const currentTime = Math.floor(Date.now() / 1000);
                        
                        if (newPayload.exp && newPayload.exp < currentTime) {
                            console.log('New token is also expired, redirecting to login');
                            if (!isRedirecting) {
                                isRedirecting = true;
                                window.location.href = '/ui';
                            }
                            return;
                        }
                    } catch (error) {
                        console.error('Error verifying new token:', error);
                        if (!isRedirecting) {
                            isRedirecting = true;
                            window.location.href = '/ui';
                        }
                        return;
                    }
                    
                    // Retry the original request with new token
                    options.headers['Authorization'] = `Bearer ${data.access_token}`;
                    return await fetch(url, options);
                } else {
                    // Refresh failed, clear token and redirect to login
                    console.log('Token refresh failed, clearing token and redirecting to login');
                    clearInvalidToken();
                    return;
                }
            } finally {
                isRefreshingToken = false;
            }
        }
        
        return response;
    } catch (error) {
        consecutiveFailures++;
        console.error('API call error:', error);
        console.log('[TOKEN DEBUG] API call failed, consecutive failures:', consecutiveFailures);
        
        // Check for infinite loop
        if (checkForInfiniteLoop()) {
            return;
        }
        
        throw error;
    }
}

function logout() {
    localStorage.removeItem('auth_token');
    window.location.href = '/ui';
}

function generateLast30DaysData() {
    const dates = [];
    for (let i = 29; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(`Day ${30 - i}`);
    }
    return dates;
}

function createMergedTrendsChart(metrics) {
    
    const rootStyles = getComputedStyle(document.documentElement);
    const primaryColor = rootStyles.getPropertyValue('--color-primary').trim();
    const secondaryColor = '#6366F1'; // Indigo for impressions
    const timeSeries = metrics.time_series || {};
    const dates = timeSeries.dates || [];
    const clicksData = timeSeries.clicks || [];
    const impressionsData = timeSeries.impressions || [];

    // Generate complete 30-day date range including missing dates with zero values
    let completeDates = [];
    let completeClicksData = [];
    let completeImpressionsData = [];

    if (dates.length > 0) {
        // Get the first and last dates from the data
        const firstDate = new Date(dates[0]);
        const lastDate = new Date(dates[dates.length - 1]);
        
        // Create a map of existing data for quick lookup
        const dataMap = {};
        dates.forEach((dateStr, index) => {
            dataMap[dateStr] = {
                clicks: clicksData[index] || 0,
                impressions: impressionsData[index] || 0
            };
        });
        
        // Generate all dates in the 30-day range
        const currentDate = new Date(firstDate);
        while (currentDate <= lastDate) {
            const dateStr = currentDate.toISOString().split('T')[0]; // YYYY-MM-DD format
            completeDates.push(dateStr);
            
            if (dataMap[dateStr]) {
                // Use real data if available
                completeClicksData.push(dataMap[dateStr].clicks);
                completeImpressionsData.push(dataMap[dateStr].impressions);
            } else {
                // Missing dates get zero values
                completeClicksData.push(0);
                completeImpressionsData.push(0);
            }
            
            // Move to next day
            currentDate.setDate(currentDate.getDate() + 1);
        }
    }

    // Use complete data if available, otherwise fall back to original data
    const finalDates = completeDates.length > 0 ? completeDates : dates;
    const finalClicksData = completeClicksData.length > 0 ? completeClicksData : clicksData;
    const finalImpressionsData = completeImpressionsData.length > 0 ? completeImpressionsData : impressionsData;

    // Format dates to readable format like "1 Jun 2025"
    const formattedDates = finalDates.map(dateStr => {
        const date = new Date(dateStr);
        const day = date.getDate();
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = monthNames[date.getMonth()];
        const year = date.getFullYear();
        return `${day} ${month} ${year}`;
    });

    if (window.mergedTrendsChart && typeof window.mergedTrendsChart.destroy === 'function') {
        window.mergedTrendsChart.destroy();
    }

    const ctx = document.getElementById('mergedTrendsChart').getContext('2d');
    window.mergedTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [
                {
                    label: 'Clicks',
                    data: finalClicksData,
                    borderColor: primaryColor,
                    backgroundColor: 'rgba(249, 115, 22, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Impressions',
                    data: finalImpressionsData,
                    borderColor: secondaryColor,
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
        responsive: true,
        maintainAspectRatio: false,
            plugins: { legend: { display: true } },
        scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(0, 0, 0, 0.05)' } },
            x: { grid: { display: false }, ticks: {
                callback: function(value, index, values) {
                    const label = this.getLabelForValue(value);
                    // Show first, middle, and last dates for better readability
                    if (label === formattedDates[0] || label === formattedDates[Math.floor(formattedDates.length/2)] || label === formattedDates[formattedDates.length-1]) {
                        return label;
                    }
                    return null;
                }
            } }
            }
        }
    });
}

function updateDashboardMetrics(hasGSC = false) {
    if (hasGSC) {
        // Update overall score
        document.getElementById('seoScore').textContent = '65';
        document.getElementById('seoScoreChange').textContent = '+5%';
        document.getElementById('seoScoreChange').className = 'score-change positive';

        // Update visibility performance
        document.getElementById('impressionsValue').textContent = '0';
        document.getElementById('clicksValue').textContent = '0';
        document.getElementById('ctrValue').textContent = '0.0%';
        document.getElementById('ctrChange').textContent = '+0.0%';
        document.getElementById('ctrChange').className = 'metric-change positive';
        document.getElementById('avgPositionValue').textContent = '0.0';
        document.getElementById('avgPositionChange').textContent = '+0.0';
        document.getElementById('avgPositionChange').className = 'metric-change positive';
        document.getElementById('visibilityInsights').innerHTML = '<p>Visiblity metrics will appear when connected</p>';



    } else {
        // Reset all metrics to empty state
        document.getElementById('seoScore').textContent = '0';
        document.getElementById('seoScoreChange').textContent = '+0%';
        
        // Reset visibility performance
        document.getElementById('impressionsValue').textContent = '0';
        document.getElementById('clicksValue').textContent = '0';
        document.getElementById('ctrValue').textContent = '0%';
        document.getElementById('ctrChange').textContent = '+0%';
        document.getElementById('avgPositionValue').textContent = 'N/A';
        document.getElementById('avgPositionChange').textContent = '+0.0';
        document.getElementById('visibilityInsights').innerHTML = '<p>Connect Google Search Console to see visibility insights</p>';



    }
}

function showErrorMessage(message) {
    // Create or update error banner
    let errorBanner = document.getElementById('errorBanner');
    if (!errorBanner) {
        errorBanner = document.createElement('div');
        errorBanner.id = 'errorBanner';
        errorBanner.className = 'error-banner';
        errorBanner.innerHTML = `
            <div class="banner-content">
                <div class="banner-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                </div>
                <div class="banner-text">
                    <h3>Data Loading Error</h3>
                    <p id="errorMessage">${message}</p>
                </div>
                <div class="banner-actions">
                    <button onclick="hideErrorMessage()" class="btn-dismiss">Dismiss</button>
                    <button onclick="location.reload()" class="btn-retry">Retry</button>
                </div>
            </div>
        `;
        
        // Insert after GSC banner
        const gscBanner = document.getElementById('gscBanner');
        if (gscBanner && gscBanner.nextSibling) {
            gscBanner.parentNode.insertBefore(errorBanner, gscBanner.nextSibling);
        } else {
            document.querySelector('.dashboard-container').insertBefore(errorBanner, document.querySelector('.dashboard-header'));
        }
    } else {
        document.getElementById('errorMessage').textContent = message;
    }
    
    errorBanner.classList.remove('hidden');
}

function hideErrorMessage() {
    const errorBanner = document.getElementById('errorBanner');
    if (errorBanner) {
        errorBanner.classList.add('hidden');
    }
}

async function updateDashboardMetricsWithRealData(metrics) {
    
    // Validate input data
    if (!metrics) {
        console.error('[ERROR] No metrics data provided to updateDashboardMetricsWithRealData');
        return;
    }
    
    const summary = metrics.summary || {};
    
    // Validate summary data structure
    if (Object.keys(summary).length === 0) {
        console.warn('[WARNING] Empty summary data received');
    }
    
    // Store summary data globally
    window.metricsData = window.metricsData || {};
    window.metricsData.summary = summary;
    
    // Extract individual values with detailed logging
    const impressionsValue = summary.total_impressions;
    const clicksValue = summary.total_clicks;
    const ctrValue = summary.avg_ctr;
    const positionValue = summary.avg_position;
    
    // Calculate SEO score based on real metrics with fallback
    let seoScore = 0;
    try {
        seoScore = calculateSEOScore(summary);
        if (isNaN(seoScore) || seoScore < 0 || seoScore > 100) {
            console.warn('[WARNING] Invalid SEO score calculated:', seoScore, 'using fallback');
            seoScore = 0;
        }
    } catch (error) {
        console.error('[ERROR] Failed to calculate SEO score:', error);
        seoScore = 0;
    }
    
    // Calculate SEO score change using backend-provided 30-day comparison
    const seoScoreChange = summary.seo_score_change !== undefined ? summary.seo_score_change : 0;
    
    // Update overall score with validation
    const seoScoreElement = document.getElementById('seoScore');
    if (seoScoreElement) {
        seoScoreElement.textContent = seoScore;
    } else {
        console.error('[ERROR] seoScore element not found');
    }
    updateSEOScoreChange(seoScoreChange);

    // Safely update DOM elements with extensive logging
    const elements = {
        'impressionsValue': (impressionsValue || 0).toLocaleString(),
        'clicksValue': (clicksValue || 0).toLocaleString(),
        'ctrValue': `${((ctrValue || 0) * 100).toFixed(2)}%`,
        'avgPositionValue': positionValue > 0 ? positionValue.toFixed(1) : 'N/A'
    };
    
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.error(`[ERROR] Element not found: ${id}`);
        }
    });
    
    // Also check if the elements are visible
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            const style = window.getComputedStyle(element);
        }
    });
    
    // Update change indicators - all use backend-provided 30-day comparisons
    const impressionsChange = summary.impressions_change !== undefined ? summary.impressions_change : 0;
    const clicksChange = summary.clicks_change !== undefined ? summary.clicks_change : 0;
    const ctrChange = summary.ctr_change !== undefined ? summary.ctr_change : 0;
    const positionChange = summary.position_change !== undefined ? summary.position_change : 0;
    
    updateChangeIndicator('impressionsChange', impressionsChange, '', true);
    updateChangeIndicator('clicksChange', clicksChange, '', true);
    updateChangeIndicator('ctrChange', ctrChange, '%', true);
    updateChangeIndicator('avgPositionChange', positionChange, '', false);
    
    // Generate insights based on real data
    try {
        await generateVisibilityInsights(summary);
        setMetricLoadingState('ai', 'done');
    } catch (error) {
        console.error('[ERROR] Failed to generate insights:', error);
    }
}

// 30-day comparison is now handled by the backend
// All growth indicators compare today's data vs exactly 30 days ago

function calculateChange(metricKey, currentValue) {
    // This function is now only used as a fallback when backend doesn't provide comparison data
    return 0; // Default to no change when backend comparison is unavailable
}

function updateChangeIndicator(elementId, value, unit = '', higherIsBetter = true) {
    const element = document.getElementById(elementId);
    if (value === undefined || value === null) {
        element.textContent = 'N/A';
        element.className = 'metric-change neutral';
        element.style.color = '#6B7280'; // Grey for N/A
        return;
    }

    // Handle loading state
    if (value === 'loading' || value === '...') {
        element.textContent = '...';
        element.className = 'metric-change neutral';
        element.style.color = '#6B7280'; // Grey for loading
        return;
    }

    // Handle categorical changes (business type, target market)
    if (elementId.includes('businessType') || elementId.includes('targetMarket')) {
        let class_name = 'metric-change';
        let displayText = '';
        if (value === 0) {
            class_name += ' neutral';
            displayText = 'No Change';
            element.style.color = '#6B7280'; // Grey for no change
        } else {
            class_name += ' positive'; // Show changes as positive (informational)
            displayText = 'Updated';
            element.style.color = ''; // Reset to CSS default
        }
        element.className = class_name;
        element.textContent = displayText;
        return;
    }

    const isPositive = higherIsBetter ? value > 0 : value < 0;
    const isNegative = higherIsBetter ? value < 0 : value > 0;
    const isZero = value === 0 || Math.abs(value) < 0.001; // Consider very small values as zero
    
    let class_name = 'metric-change';
    if (isZero) {
        class_name += ' neutral';
        element.style.color = '#6B7280'; // Grey for zero/no change
    } else if (isPositive) {
        class_name += ' positive';
        element.style.color = ''; // Reset to CSS default
    } else if (isNegative) {
        class_name += ' negative';
        element.style.color = ''; // Reset to CSS default
    }

    element.className = class_name;
    
    // Format the display value
    let displayText;
    if (isZero) {
        displayText = unit === '%' ? '0%' : '0';
    } else {
        const prefix = value > 0 ? '+' : '';
    const formattedValue = unit === '%' ? (value * 100).toFixed(2) : value.toFixed(1);
        displayText = `${prefix}${formattedValue}${unit}`;
    }
    
    element.textContent = displayText;
}

function updateSEOScoreChange(change) {
    const element = document.getElementById('seoScoreChange');
    if (change === undefined || change === null) {
        element.textContent = 'N/A';
        element.className = 'score-change';
        return;
    }

    const isPositive = change > 0;
    const isNegative = change < 0;
    const isZero = change === 0 || Math.abs(change) < 0.001; // Consider very small values as zero
    
    let class_name = 'score-change';
    if (isZero) {
        class_name += ' neutral';
        element.style.color = '#6B7280'; // Grey for no change
    } else if (isPositive) {
        class_name += ' positive';
        element.style.color = ''; // Reset to CSS default (green)
    } else if (isNegative) {
        class_name += ' negative';
        element.style.color = ''; // Reset to CSS default (red)
    }

    element.className = class_name;
    
    // Format the display value
    let displayText;
    if (isZero) {
        displayText = '0';
    } else {
        const prefix = change > 0 ? '+' : '';
        displayText = `${prefix}${change}`;
    }
    element.textContent = displayText;
}

// Global variable to store AI insights
let cachedAIInsights = null;

async function fetchAIInsights() {
    try {
        // First try to get cached AI insights
        const response = await apiCall('/auth/benchmark/insights');
        if (response.ok) {
            const insights = await response.json();
            // Update both local and global cache
            cachedAIInsights = insights;
            window.cachedAIInsights = insights;

            return insights;
        } else {

            // No cache found - automatically generate fresh AI insights
            const freshResponse = await apiCall('/auth/benchmark/insights?explicit_ai=true');
            if (freshResponse.ok) {
                const insights = await freshResponse.json();
                // Update both local and global cache
                cachedAIInsights = insights;
                window.cachedAIInsights = insights;

                return insights;
            } else {

                return null;
            }
        }
    } catch (error) {
        console.error('[DEBUG] Error fetching AI insights:', error);
        return null;
    }
}

async function fetchExplicitAIInsights() {
    try {
        // Explicitly generate fresh AI insights
        const response = await apiCall('/auth/benchmark/insights?explicit_ai=true');
        if (response.ok) {
            const insights = await response.json();
            // Update both local and global cache
            cachedAIInsights = insights;
            window.cachedAIInsights = insights;

            return insights;
        } else {

            return null;
        }
    } catch (error) {
        console.error('[DEBUG] Error fetching AI insights:', error);
        return null;
    }
}

async function generateVisibilityInsights(summary) {
    try {
        // Use cached insights if available, otherwise fetch
        const insights = cachedAIInsights || await fetchAIInsights();
        window.lastInsights = insights;
        
        if (insights && insights.visibility_performance && insights.visibility_performance.metrics) {
            // Update individual metric analyses
            Object.entries(insights.visibility_performance.metrics).forEach(([metric, data]) => {
                
                let analysis = '';
                // Handle different possible data structures
                if (typeof data === 'string') {
                    analysis = data;
                } else if (data && typeof data === 'object') {
                    // Check if analysis is an object with text content
                    if (data.analysis && typeof data.analysis === 'object') {
                        // Create a meaningful summary from the analysis object
                        const analysisObj = data.analysis;
                        const parts = [];
                        
                        if (analysisObj.current_performance) {
                            parts.push(`${analysisObj.current_performance} performance`);
                        }
                        if (analysisObj.root_cause) {
                            parts.push(analysisObj.root_cause);
                        }
                        if (analysisObj.industry_context) {
                            parts.push(analysisObj.industry_context);
                        }
                        
                        // Clean up any double periods and ensure proper formatting
                        analysis = parts.join('. ').replace(/\.\.+/g, '.').replace(/\.\s*\./g, '. ').trim();
                    } else {
                        // Try different possible field names
                        analysis = data.analysis || data.summary || data.assessment || data.description || data.value || JSON.stringify(data);
                    }
                }
                
                // Map metric names to element IDs
                const metricElementMap = {
                    'impressions': 'impressionsAnalysis',
                    'clicks': 'clicksAnalysis',
                    'ctr': 'ctrAnalysis',
                    'average_position': 'avgPositionAnalysis'
                };
                
                const elementId = metricElementMap[metric];
                if (elementId && analysis) {
                    const element = document.getElementById(elementId);
                    if (element) {
                        element.textContent = analysis;
                        element.style.display = 'block';
                    }
                }
            });
            
            renderAIOverallAnalysis(insights);
        } else {
            console.log('[ERROR] No visibility insights available');
        }
    } catch (error) {
        console.error('Error generating visibility insights:', error);
    }
}

















// Mobile Menu Functions
function toggleMobileMenu() {
    updateUserMenuInfo();
    const menu = document.getElementById('mobileMenu');
    const overlay = document.getElementById('mobileMenuOverlay');
    
    if (menu.classList.contains('active')) {
        closeMobileMenu();
    } else {
        openMobileMenu();
    }
}

function openMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const overlay = document.getElementById('mobileMenuOverlay');
    
    menu.classList.add('active');
    overlay.classList.add('active');
    
    // Prevent body scroll when menu is open
    document.body.style.overflow = 'hidden';
}

function closeMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const overlay = document.getElementById('mobileMenuOverlay');
    
    menu.classList.remove('active');
    overlay.classList.remove('active');
    
    // Restore body scroll
    document.body.style.overflow = '';
}

// Close menu on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeMobileMenu();
    }
});

async function initDashboard() {
    checkAuth();
    handleOAuthCallback();

    // Check GSC connection status
    await checkGSCConnection();

    // Try to load cached data for today
    const hasCachedData = await loadCachedDashboardData();

    if (!hasCachedData) {
        // No cache for today - automatically refresh metrics and AI insights

        showCacheStatus('No cached data for today - refreshing metrics and AI insights...', 'info');
        
        try {
            // Load fresh metrics
            await loadRealMetrics();
            
            // Load keywords
            await loadKeywords();
            
            // Generate fresh AI insights

            const aiInsights = await fetchAIInsights();
            
            // Cache the fresh data including AI insights
            await cacheDashboardData();
            
            showCacheStatus('Fresh data and AI insights loaded and cached!', 'success');
        } catch (error) {
            console.error('[ERROR] Failed to load fresh data:', error);
            showCacheStatus('Failed to load fresh data', 'warning');
            
            // Show empty state as fallback
            updateDashboardMetrics(false);
            createMergedTrendsChart({});
        }
    }
}

function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const oauthSuccess = urlParams.get('oauth_success');
    const oauthError = urlParams.get('oauth_error');
    
    if (oauthSuccess === 'true') {
        // Clean up URL parameters
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    } else if (oauthError === 'true') {

        // Clean up URL parameters
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
        
        // Show error message
        alert('Failed to connect to Google Search Console. Please try again.');
    }
}



async function checkGSCConnection() {
    try {
        const response = await apiCall('/auth/gsc/properties');

        if (response.status === 401) {

            showGSCBanner();
            return false;
        }
        
        if (response.status === 404) {
            const errorText = await response.text();

            
            // Check if this is the specific "No Google Search Console properties found" error
            // which indicates corrupted credentials
            if (errorText.includes('No Google Search Console properties found')) {

                await handleCorruptedCredentials();
                return false;
            } else {

                showGSCBanner();
                return false;
            }
        }
        
        if (!response.ok) {
            const errorText = await response.text();

            
            // Check if it's a credentials issue
            if (response.status === 500 && errorText.includes('credentials')) {

                showGSCBannerWithReauth();
            } else {

                showGSCBanner();
            }
            return false;
        }

        const properties = await response.json();
        
        if (!properties || properties.length === 0) {

            showGSCBanner();
            return false;
        }

        const isDemoMode = properties.some(p => p.siteUrl.includes('example.com') || p.siteUrl.includes('demo-site.com'));

        
        if (isDemoMode) {

            showGSCBanner();
            return false;
        }

        // Check if a property is already selected
        const selectedResponse = await apiCall('/auth/gsc/selected');
        if (selectedResponse && selectedResponse.ok) {
            const selectedProperty = await selectedResponse.json();
            hideGSCBanner();
            return true;
        } else {

        }

        // Properties available but none selected - show banner to prompt selection

        showGSCBanner();
        return false;
    } catch (error) {

        showGSCBanner();
        return false;
    }
}

async function handleCorruptedCredentials() {
    
    try {
        // Show loading state in banner
        const banner = document.getElementById('gscBanner');
        const bannerText = banner.querySelector('.banner-text p');
        if (bannerText) {
            bannerText.textContent = 'Detected corrupted Google Search Console connection. Cleaning up...';
        }
        banner.classList.remove('hidden');
        
        // Clear the corrupted credentials
        const clearResponse = await apiCall('/auth/gsc/clear-credentials', {
            method: 'POST'
        });
        
        if (clearResponse.ok) {

            // Update banner to instruct user to click Connect GSC
            if (bannerText) {
                bannerText.innerHTML = 'Invalid credentials detected and cleared. Please reconnect your account.';
            }
            // Do NOT auto-redirect to Google OAuth
            return;
        } else {
            console.error('[ERROR] Failed to clear credentials:', clearResponse.status);
            if (bannerText) {
                bannerText.innerHTML = 'Failed to clear corrupted credentials. <button onclick="clearCredentials()" class="btn-link">Click here to try again</button>';
            }
        }
    } catch (error) {
        console.error('[ERROR] Error in handleCorruptedCredentials:', error);
        const banner = document.getElementById('gscBanner');
        const bannerText = banner.querySelector('.banner-text p');
        if (bannerText) {
            bannerText.innerHTML = 'Error cleaning up corrupted connection. <button onclick="clearCredentials()" class="btn-link">Click here to try again</button>';
        }
    }
}

function showGSCBanner() {
    document.getElementById('gscBanner').classList.remove('hidden');
}

function hideGSCBanner() {
    document.getElementById('gscBanner').classList.add('hidden');
}

function showGSCBannerWithReauth() {
    const banner = document.getElementById('gscBanner');
    banner.classList.remove('hidden');
    
    // Update banner content to show re-authentication option
    const bannerText = banner.querySelector('.banner-text p');
    if (bannerText) {
        bannerText.innerHTML = 'Your Google Search Console connection has an issue. <button onclick="clearCredentials()" class="btn-link">Click here to re-authenticate</button> or connect a new account.';
    }
}

async function clearCredentials() {
    try {
        const response = await apiCall('/auth/gsc/clear-credentials', {
            method: 'POST'
        });

        if (response.ok) {
            // Redirect to Google OAuth directly, bypassing setup wizard
            window.location.href = '/auth/google/authorize';
        } else {
            alert('Failed to clear credentials. Please try again.');
        }
    } catch (error) {
        console.error('Error clearing credentials:', error);
        alert('Failed to clear credentials. Please try again.');
    }
}

async function connectGSC() {
    try {
        
        // IMMEDIATE LOADING INDICATOR - Show loading state instantly
        const banner = document.getElementById('gscBanner');
        const bannerText = banner.querySelector('.banner-text p');
        const connectBtn = banner.querySelector('.btn-connect');
        
        // Show banner immediately with loading state
        banner.classList.remove('hidden');
        
        // Update button to show loading
        if (connectBtn) {
            connectBtn.disabled = true;
            connectBtn.innerHTML = '<span class="loading-spinner"></span> Connecting...';
        }
        
        // Update text immediately
        if (bannerText) {
            bannerText.textContent = 'Connecting to Google Search Console...';
        }
        
        // Add loading animation to banner
        banner.classList.add('loading');
        
        // Small delay to ensure UI updates are visible
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Authenticated API call to get the Google OAuth URL
        const response = await apiCall('/auth/google/authorize');
        if (response.ok) {
            const data = await response.json();
            if (data.auth_url) {
                if (bannerText) {
                    bannerText.textContent = 'Redirecting to Google OAuth...';
                }
                if (connectBtn) {
                    connectBtn.innerHTML = '<span class="loading-spinner"></span> Redirecting...';
                }
                setTimeout(() => {
                    window.location.href = data.auth_url;
                }, 500); // Reduced delay for faster redirect
                return;
            }
        }
        // If we get here, something went wrong
        if (bannerText) {
            bannerText.innerHTML = 'Session expired or authentication failed. <button onclick="logout()" class="btn-link">Click here to log in again</button>';
        }
        if (connectBtn) {
            connectBtn.disabled = false;
            connectBtn.innerHTML = 'Connect GSC';
        }
        banner.classList.remove('loading');
        alert('Session expired or authentication failed. Please log in again.');
        logout();
    } catch (error) {
        console.error('[ERROR] Error connecting to GSC:', error);
        const banner = document.getElementById('gscBanner');
        const bannerText = banner.querySelector('.banner-text p');
        const connectBtn = banner.querySelector('.btn-connect');
        
        if (bannerText) {
            bannerText.innerHTML = 'Unable to connect to Google Search Console. <button onclick="connectGSC()" class="btn-link">Click here to try again</button>';
        }
        if (connectBtn) {
            connectBtn.disabled = false;
            connectBtn.innerHTML = 'Connect GSC';
        }
        banner.classList.remove('loading');
        banner.classList.remove('hidden');
    }
}

// Property selector modal removed - now handled by property_selection.html

// Property selector functions removed - now handled by property_selection.html

async function refreshMetrics() {

    
    // IMMEDIATE POPUP - Show metrics loading popup instantly
    showMetricsLoadingPopup();
    resetMetricsLoadingState();
    
    const refreshBtn = document.getElementById('refreshBtn');
    // Show loading state
    refreshBtn.disabled = true;
    refreshBtn.classList.add('loading');
    
    try {
        const response = await apiCall('/auth/gsc/refresh', {
            method: 'POST'
        });
        if (response.ok) {
            const data = await response.json();
            
            // Set initial loading states
            setMetricLoadingState('visibility', 'loading');
            setMetricLoadingState('organic_impressions', 'loading');
            
            // Reload the dashboard with fresh data
            await loadRealMetrics();
            
            // Load fresh keywords
            await loadKeywords();
            
            // Cache the dashboard data after successful refresh
            await cacheDashboardData();
            
            // Mark all metrics as done after everything is complete
            setMetricLoadingState('visibility', 'done');
            setMetricLoadingState('organic_impressions', 'done');
            setMetricLoadingState('ai', 'done');
            
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to refresh data');
        }
    } catch (error) {
        console.error('Error refreshing metrics:', error);
        
        // Mark all metrics as done even on error
        setMetricLoadingState('visibility', 'done');
        setMetricLoadingState('organic_impressions', 'done');
        setMetricLoadingState('ai', 'done');
        
        // Force the banner to show with a helpful message
        const banner = document.getElementById('gscBanner');
        const bannerText = banner.querySelector('.banner-text p');
        if (bannerText) {
            bannerText.textContent = 'We couldn\'t refresh your data because the connection to Google Search Console was lost. Please reconnect to continue.';
        }
        banner.classList.remove('hidden');
    } finally {
        // Reset button state after a short delay to allow animation to be seen
        setTimeout(() => {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('loading');
        }, 500);
    }
}

async function cacheDashboardData() {
    // Cache the current dashboard data for same-day retrieval
    try {
        
        // Collect all current dashboard data including original API response data
        const dashboardData = {
            metrics: window.metricsData || {},
            // Store original API response data if available
            originalApiData: window.originalApiResponse || null,
            // Include AI insights in cache
            ai_insights: window.cachedAIInsights || cachedAIInsights || null,
            // Include website content in cache
            website_content: window.websiteContent || null,
            timestamp: new Date().toISOString(),
            cached_from: 'dashboard_refresh'
        };
        
        // Get current keywords if available
        let keywords = null;
        const keywordsList = document.getElementById('keywordsList');
        if (keywordsList && keywordsList.children.length > 1) { // More than just the header
            keywords = [];
            const keywordItems = keywordsList.querySelectorAll('.keyword-item');
            keywordItems.forEach(item => {
                const keywordText = item.querySelector('.keyword-text').textContent;
                const position = parseFloat(item.querySelector('.keyword-position').textContent);
                const clicks = parseInt(item.querySelector('.keyword-clicks').textContent);
                const impressions = parseInt(item.querySelector('.keyword-impressions').textContent);
                keywords.push({
                    query: keywordText,
                    position: position,
                    clicks: clicks,
                    impressions: impressions
                });
            });
        }
        
        const response = await apiCall('/auth/dashboard/cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                dashboard_data: dashboardData,
                keywords: keywords
            })
        });

        if (response.ok) {
            const result = await response.json();

        } else {
            console.warn('[CACHE] Failed to cache dashboard data:', response.status);
        }
    } catch (error) {
        console.error('[CACHE] Error caching dashboard data:', error);
    }
}

async function loadCachedDashboardData() {
    try {
        showCacheLoadingPopup();
        const response = await apiCall('/auth/dashboard/cache');
        if (response.ok) {
            const result = await response.json();
            
            if (result.has_cache && result.data) {
                
                // Load the cached data into the dashboard
                if (result.data.metrics) {
                    window.metricsData = result.data.metrics;
                    
                    // Use original API data if available, otherwise reconstruct from cached metrics
                    let metricsObject;
                    if (result.data.originalApiData) {
                        metricsObject = result.data.originalApiData;
                        window.originalApiResponse = result.data.originalApiData;
                    } else {
                        metricsObject = { 
                            summary: result.data.metrics.summary || {},
                            time_series: result.data.metrics.time_series || {},
                            website_url: result.data.metrics.website_url,
                            start_date: result.data.metrics.start_date,
                            end_date: result.data.metrics.end_date
                        };
                    }
                    
                    // Update main dashboard metrics
                    if (result.data.metrics.summary) {
                        await updateDashboardMetricsWithRealData(metricsObject);
                    }
                    
                    // Create charts with cached data
                    createMergedTrendsChart(metricsObject);
                    
                    // Show website info if available
                    if (result.data.metrics.summary) {
                        showWebsiteInfo(metricsObject);
                        showDateRange(metricsObject);
                    }
                    
                    // Load cached AI insights if available
                    if (result.data.ai_insights) {
                        cachedAIInsights = result.data.ai_insights;
                        window.cachedAIInsights = result.data.ai_insights;

                        
                        // Generate visibility insights with cached AI data
                        if (result.data.metrics.summary) {
                            generateVisibilityInsights(result.data.metrics.summary);
                        }
                    }
                    
                    // Load cached keywords if available
                    if (result.data.keywords) {
                        updateKeywordsDisplay(result.data.keywords);
                    } else {
                        // Load fresh keywords if not cached
                        await loadKeywords();
                    }
                    
                    // Load cached website content if available
                    if (result.data.website_content) {
            
                        window.websiteContent = result.data.website_content;
                        updateContentFetchDate(result.data.website_content.fetched_at);
                        updateContentSummary(result.data.website_content);
                    } else {
                        // Load fresh website content if not cached
            
                        await loadWebsiteContent();
                    }
                    
                    // Recalculate score
                    recalculateOverallSEOScore();
                    
                    showCacheStatus('Loaded cached data from today', 'success');
                    hideCacheLoadingPopup();
                    // Hide any previous warning message
                    const cacheStatus = document.getElementById('cacheStatus');
                    if (cacheStatus && cacheStatus.classList.contains('cache-warning')) {
                        cacheStatus.style.display = 'none';
                    }
                    return true; // Successfully loaded cached data
                }
            } else {
                // No cache found - this will trigger automatic refresh in initDashboard

                hideCacheLoadingPopup();
                return false;
            }
    } else {
            console.warn('[CACHE] Failed to check for cached data:', response.status);
            hideCacheLoadingPopup();
            return false;
        }
    } catch (error) {
        console.error('[CACHE] Error loading cached dashboard data:', error);
        hideCacheLoadingPopup();
        return false;
    }
}

function showCacheStatus(message, type = 'info') {
    // Show cache status message to user
    // Create or update cache status element
    let cacheStatus = document.getElementById('cacheStatus');
    if (!cacheStatus) {
        cacheStatus = document.createElement('div');
        cacheStatus.id = 'cacheStatus';
        cacheStatus.className = 'cache-status';
        // Insert after the dashboard header
        const dashboardHeader = document.querySelector('.dashboard-header');
        if (dashboardHeader) {
            dashboardHeader.insertAdjacentElement('afterend', cacheStatus);
        }
    }
    // Set message and type
    cacheStatus.textContent = message;
    cacheStatus.className = `cache-status cache-${type}`;
    cacheStatus.style.display = 'block';
    // Set warning (no cache) to grey
    if (type === 'warning') {
        cacheStatus.style.background = '#f3f4f6'; // light grey
        cacheStatus.style.color = '#6B7280'; // grey text
        cacheStatus.style.border = '1px solid #d1d5db';
    } else {
        cacheStatus.style.background = '';
        cacheStatus.style.color = '';
        cacheStatus.style.border = '';
    }
    // Auto-hide only for info/success
    if (type === 'info' || type === 'success') {
        setTimeout(() => {
            if (cacheStatus) {
                cacheStatus.style.display = 'none';
            }
        }, 5000);
    }
}

function recalculateOverallSEOScore() {
    const seoScore = calculateSEOScore(window.metricsData.summary);
    
    // Calculate and update SEO score change (use backend data if available, otherwise fallback to session-based)
    const seoScoreChange = window.metricsData.summary?.seo_score_change !== undefined ? 
        window.metricsData.summary.seo_score_change : 
        calculateChange('seo_score', seoScore);
    
    document.getElementById('seoScore').textContent = seoScore;
    updateSEOScoreChange(seoScoreChange);
}

function calculateSEOScore(summary) {
    // Define core metrics, their weights, and normalization functions
    const metrics = [
        // Visibility Performance (100% weight - only remaining metrics)
        { key: 'avg_ctr', value: summary.avg_ctr, weight: 25, norm: v => Math.min(v / 0.10, 1) },
        { key: 'avg_position', value: summary.avg_position, weight: 25, norm: v => Math.max((10 - v) / 10, 0) },
        { key: 'total_impressions', value: summary.total_impressions, weight: 25, norm: v => Math.min(Math.log10(v + 1) / 6, 1) },
        { key: 'total_clicks', value: summary.total_clicks, weight: 25, norm: v => Math.min(Math.log10(v + 1) / 5, 1) }
    ];

    // Filter out missing metrics
    const present = metrics.filter(m => m.value !== undefined && m.value !== null && !Number.isNaN(m.value));
    const totalWeight = present.reduce((sum, m) => sum + m.weight, 0);
    if (totalWeight === 0) return 0;

    // Dynamically scale weights so total is 100
    let score = 0;
    present.forEach(m => {
        const scaledWeight = m.weight * (100 / totalWeight);
        let normValue = m.norm(m.value);
        normValue = Math.max(0, Math.min(normValue, 1));
        score += normValue * scaledWeight;
    });
    return Math.round(score);
}

function formatDateString(dateStr) {
    // dateStr is in "YYYY-MM-DD" format
    if (!dateStr || dateStr.split('-').length !== 3) {
        return '';
    }
    const [year, month, day] = dateStr.split('-');
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const monthName = monthNames[parseInt(month, 10) - 1];
    return `${monthName} ${parseInt(day, 10)}`;
}

function showDateRange(metrics) {
    const dateRangeInfo = document.getElementById('dateRangeInfo');
    const dateRangeSpan = document.getElementById('dateRange');

    if (metrics && metrics.start_date && metrics.end_date) {
        const startStr = formatDateString(metrics.start_date);
        const endStr = formatDateString(metrics.end_date);
        
        dateRangeSpan.textContent = `${startStr} - ${endStr}`;
        dateRangeInfo.classList.remove('hidden');
    } else {
        hideDateRange();
    }
}

function hideDateRange() {
    document.getElementById('dateRangeInfo').classList.add('hidden');
}

function showWebsiteInfo(metrics) {
    const websiteInfo = document.getElementById('websiteInfo');
    const trackedWebsite = document.getElementById('trackedWebsite');
    const mobileMenuWebsite = document.getElementById('mobileMenuWebsite');

    if (metrics && metrics.website_url) {
        let displayUrl = metrics.website_url;
        if (displayUrl.startsWith('sc-domain:')) {
            // Convert sc-domain:example.com to https://example.com
            const domain = displayUrl.replace('sc-domain:', '');
            displayUrl = `https://${domain}`;
        }
        trackedWebsite.textContent = displayUrl;
        mobileMenuWebsite.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="inline-icon"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>${displayUrl}`;
        websiteInfo.classList.remove('hidden');
    } else {
        hideWebsiteInfo();
    }
}

function hideWebsiteInfo() {
    document.getElementById('websiteInfo').classList.add('hidden');
    document.getElementById('mobileMenuWebsite').textContent = 'No website selected';
}

function changeWebsite() {
    // Redirect to setup wizard to select a different website
    window.location.href = '/setup';
}

function showMetricsLoadingPopup() {
    const popup = document.getElementById('metricsLoadingPopup');
    if (popup) {

        popup.style.display = 'flex';
        popup.classList.remove('metrics-loading-hide');
        popup.classList.add('metrics-loading-visible');
        updateMetricsLoadingList();
    }
}
function hideMetricsLoadingPopup() {
    const popup = document.getElementById('metricsLoadingPopup');
    if (popup) {

        popup.style.display = 'none';
        popup.classList.remove('metrics-loading-visible');
        popup.classList.add('metrics-loading-hide');
    }
}
function showMetricsSuccessPopup() {
    const popup = document.getElementById('metricsSuccessPopup');
    if (popup) {

        popup.style.display = 'flex';
        popup.classList.remove('metrics-success-hide');
        popup.classList.add('metrics-success-visible');
    }
}
function hideMetricsSuccessPopup() {
    const popup = document.getElementById('metricsSuccessPopup');
    if (popup) {

        popup.style.display = 'none';
        popup.classList.remove('metrics-success-visible');
        popup.classList.add('metrics-success-hide');
    }
}
function updateMetricsLoadingList() {
    const orange = '#F97316';
    const list = document.getElementById('metricsLoadingList');
    list.innerHTML = METRIC_GROUPS.map(m => {
        const state = metricsLoadingState[m.key];
        if (state === 'done') {
            // Orange checkmark and regular font
            return `<div style="display:flex;align-items:center;gap:0.5rem;font-weight:400;color:${orange};"><span class="metric-success-icon"><svg width='18' height='18'><polyline points='3,10 8,15 15,4' style='fill:none;stroke:${orange};stroke-width:2;stroke-linecap:round;stroke-linejoin:round;'/></svg></span><span style='color:${orange};'>${m.label}</span></div>`;
        } else if (state === 'loading') {
            // Orange spinner and regular font
            return `<div style="display:flex;align-items:center;gap:0.5rem;font-weight:400;color:${orange};"><span class="metric-loading-spinner"><svg width='18' height='18' viewBox='0 0 50 50'><circle cx='25' cy='25' r='20' fill='none' stroke='${orange}' stroke-width='5' stroke-linecap='round' stroke-dasharray='31.4 31.4' stroke-dashoffset='0'><animateTransform attributeName='transform' type='rotate' from='0 25 25' to='360 25 25' dur='0.8s' repeatCount='indefinite'/></circle></svg></span><span style='color:${orange};'>${m.label}</span></div>`;
        } else {
            // Pending (orange, no animation)
            return `<div style="display:flex;align-items:center;gap:0.5rem;font-weight:400;color:${orange};"><span class="metric-pending-icon"><svg width='18' height='18'><circle cx='9' cy='9' r='7' fill='none' stroke='${orange}' stroke-width='2'/></svg></span><span style='color:${orange};'>${m.label}</span></div>`;
        }
    }).join('');
}
function setMetricLoadingState(key, state) {
    metricsLoadingState[key] = state;
    updateMetricsLoadingList();
    
    // Set loading state for growth indicators
    if (state === 'loading') {
        setGrowthIndicatorsLoading(key);
    }
    
    // If all done, show success popup and hide both after 5s with countdown
    if (METRIC_GROUPS.every(m => metricsLoadingState[m.key] === 'done')) {
        
        
        // Show success popup
        showMetricsSuccessPopup();
        
        let secondsLeft = 5;
        const timerSpan = document.getElementById('metricsSuccessTimer');
        timerSpan.textContent = `(${secondsLeft}s)`;
        timerSpan.style.color = '';
        const interval = setInterval(() => {
            secondsLeft--;
            timerSpan.textContent = `(${secondsLeft}s)`;
            if (secondsLeft <= 0) {
                clearInterval(interval);

                // Hide both popups together
                hideMetricsSuccessPopup();
                hideMetricsLoadingPopup();
            }
        }, 1000);
        
        // Global fallback timer to ensure popups are hidden after 5 seconds
        setTimeout(() => {

            const loadingPopup = document.getElementById('metricsLoadingPopup');
            const successPopup = document.getElementById('metricsSuccessPopup');
            if (loadingPopup) loadingPopup.style.display = 'none';
            if (successPopup) successPopup.style.display = 'none';
        }, 5000);
    } else {
        
    }
}

function setGrowthIndicatorsLoading(section) {
    const indicatorMap = {
        'visibility': [
            'impressionsChange', 'clicksChange', 'ctrChange', 'avgPositionChange'
        ],
        'organic': [
            'impressionsChange', 'clicksChange'
        ],
        'impressions': [
            'impressionsChange'
        ]
    };

    const indicators = indicatorMap[section] || [];
    indicators.forEach(indicatorId => {
        const element = document.getElementById(indicatorId);
        if (element) {
            updateChangeIndicator(indicatorId, 'loading');
        } else {
            console.warn(`[DEBUG] Growth indicator element not found: ${indicatorId}`);
        }
    });
}
function resetMetricsLoadingState() {
    METRIC_GROUPS.forEach((m, i) => {
        metricsLoadingState[m.key] = (i === 0) ? 'loading' : 'pending';
    });
    updateMetricsLoadingList();
}

async function loadRealMetrics() {
    resetMetricsLoadingState();
    
    try {
        // Visibility Performance (GSC metrics)
        setMetricLoadingState('visibility', 'loading');
        const response = await apiCall('/auth/gsc/metrics');
        if (response.ok) {
            const metrics = await response.json();
            
            // Store original API response for caching
            window.originalApiResponse = metrics;
            
            // Validate metrics data structure
            if (!metrics || !metrics.summary) {
                console.error('[ERROR] Invalid metrics data structure:', metrics);
                throw new Error('Invalid metrics data structure received from API');
            }
            
            await updateDashboardMetricsWithRealData(metrics);
            
            createMergedTrendsChart(metrics);
            
            showWebsiteInfo(metrics);
            showDateRange(metrics);
            
            // Mark core metrics as loaded
            setMetricLoadingState('visibility', 'done');
            setMetricLoadingState('organic_impressions', 'done');
            
            // Set AI to loading since insights will be generated
            setMetricLoadingState('ai', 'loading');
            
            // All core metrics are now loaded

            
        } else {
            const errorText = await response.text();
            console.error('[ERROR] Failed to load GSC metrics:', response.status, errorText);
            
            // Set all states to done since we can't fetch data
            setMetricLoadingState('visibility', 'done');
            setMetricLoadingState('organic_impressions', 'done');
            setMetricLoadingState('ai', 'done');
            
            // Show empty state
            updateDashboardMetrics(false);
            createMergedTrendsChart({});
            hideWebsiteInfo();
            hideDateRange();
        }
    } catch (error) {
        console.error('[ERROR] Exception in loadRealMetrics:', error);
        
        // Set all states to done
        setMetricLoadingState('visibility', 'done');
        setMetricLoadingState('organic_impressions', 'done');
        setMetricLoadingState('ai', 'done');
        
        // Show empty state
        updateDashboardMetrics(false);
        createMergedTrendsChart({});
        hideWebsiteInfo();
        hideDateRange();
    } finally {
        // Note: Loading popup will be hidden by setMetricLoadingState when all metrics are done
        // The 5-second countdown timer handles hiding both loading and success popups
    }
}

// Load keywords from Google Search Console
async function loadKeywords() {
    try {

        
        const response = await apiCall('/auth/gsc/keywords');
        if (response.ok) {
            const keywordsData = await response.json();
            
            if (keywordsData && keywordsData.keywords) {
                updateKeywordsDisplay(keywordsData.keywords);
                
                // Cache the keywords
                await cacheKeywords(keywordsData.keywords);
            } else {
                console.error('[ERROR] Invalid keywords data structure:', keywordsData);
                document.getElementById('keywordsList').innerHTML = '<div class="keywords-loading">No keywords data available</div>';
            }
        } else {
            const errorText = await response.text();
            console.error('[ERROR] Failed to load keywords:', response.status, errorText);
            document.getElementById('keywordsList').innerHTML = '<div class="keywords-loading">Failed to load keywords</div>';
        }
    } catch (error) {
        console.error('[ERROR] Exception in loadKeywords:', error);
        document.getElementById('keywordsList').innerHTML = '<div class="keywords-loading">Error loading keywords</div>';
    }
}

// Cache keywords separately
async function cacheKeywords(keywords) {
    try {
        const response = await apiCall('/auth/dashboard/cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                dashboard_data: {},
                keywords: keywords
            })
        });

        if (response.ok) {

        } else {
            console.warn('[CACHE] Failed to cache keywords:', response.status);
        }
    } catch (error) {
        console.error('[CACHE] Error caching keywords:', error);
    }
}

// Analyze keyword performance and return status and indicator
function analyzeKeywordPerformance(keyword) {
    // Define performance thresholds
    const HIGH_POTENTIAL_POSITION = 11; // Position 11-20 (just outside top 10)
    const UNDERPERFORMING_POSITION = 50; // Position 50+ (far from top)
    const LOW_CTR_THRESHOLD = 0.01; // 1% CTR threshold
    const HIGH_IMPRESSIONS_LOW_CLICKS = 100; // High impressions but low clicks
    
    let status = 'normal';
    let indicator = '';
    
    // Check for high potential keywords (good position but could improve)
    if (keyword.position >= HIGH_POTENTIAL_POSITION && keyword.position <= 20) {
        status = 'high-potential';
        indicator = '🔥';
    }
    // Check for underperforming keywords (poor position or low CTR with decent impressions)
    else if (keyword.position > UNDERPERFORMING_POSITION || 
             (keyword.ctr && keyword.ctr < LOW_CTR_THRESHOLD && keyword.impressions > HIGH_IMPRESSIONS_LOW_CLICKS)) {
        status = 'underperforming';
        indicator = '⚠️';
    }
    // Check for high-performing keywords (top 10 with good CTR)
    else if (keyword.position <= 10 && keyword.ctr && keyword.ctr > 0.03) {
        status = 'performing-well';
        indicator = '✅';
    }
    // Check for keywords in top 10 with low CTR (opportunity for improvement)
    else if (keyword.position <= 10 && keyword.impressions > 10 && (!keyword.ctr || keyword.ctr <= 0.03)) {
        status = 'underperforming';
        indicator = '⚠️';
    }
    
    return { status, indicator };
}

// Update keywords display
function updateKeywordsDisplay(keywords) {
    const keywordsList = document.getElementById('keywordsList');
    
    // Create keywords list
    let keywordsHTML = `
        <div class="keywords-header">
            <div class="keyword-number">#</div>
            <div class="keyword-text">Keyword</div>
            <div class="keyword-stats">
                <div class="keyword-position">Position</div>
                <div class="keyword-clicks">Clicks</div>
                <div class="keyword-impressions">Impressions</div>
                <div class="keyword-ctr">CTR</div>
            </div>
            <div class="keyword-indicator-header">Status</div>
        </div>
    `;
    
    // Sort keywords by position (best first)
    const sortedKeywords = keywords.sort((a, b) => a.position - b.position);
    
    // Display top 20 keywords
    const displayKeywords = sortedKeywords.slice(0, 20);
    
    displayKeywords.forEach((keyword, index) => {
        // Analyze keyword performance
        const keywordAnalysis = analyzeKeywordPerformance(keyword);
        
        keywordsHTML += `
            <div class="keyword-item ${keywordAnalysis.status}">
                <div class="keyword-number">${index + 1}</div>
                <div class="keyword-text">${keyword.query}</div>
                <div class="keyword-stats">
                    <div class="keyword-position">${keyword.position.toFixed(1)}</div>
                    <div class="keyword-clicks">${keyword.clicks}</div>
                    <div class="keyword-impressions">${keyword.impressions}</div>
                    <div class="keyword-ctr">${keyword.ctr !== null && keyword.ctr !== undefined ? (keyword.ctr * 100).toFixed(2) + '%' : '0.00%'}</div>
                </div>
                ${keywordAnalysis.indicator ? `<div class="keyword-indicator">${keywordAnalysis.indicator}</div>` : '<div class="keyword-indicator"></div>'}
            </div>
        `;
    });
    
    if (keywords.length > 20) {
        keywordsHTML += `
            <div class="keyword-item" style="text-align: center; color: #6b7280; font-style: italic;">
                ... and ${keywords.length - 20} more keywords
            </div>
        `;
    }
    
    keywordsList.innerHTML = keywordsHTML;
}

document.addEventListener('DOMContentLoaded', initDashboard);

// Hide error banner on page load
document.addEventListener('DOMContentLoaded', function() {
    hideErrorMessage();
});

// Website Content Functions
async function fetchWebsiteContent() {
    try {
        document.getElementById('fetchContentButton').disabled = true;
        
        const response = await apiCall('/auth/website/content/fetch', {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();

            
            if (result && result.success) {
                // Store website content globally for caching
                window.websiteContent = result.content;
                
                updateContentFetchDate();
                updateContentSummary(result.content || {});
            } else {
                console.error('[ERROR] Failed to fetch website content:', result?.message || 'Unknown error');
            }
        } else {
            const errorText = await response.text();
            console.error('[ERROR] Failed to fetch website content:', response.status, errorText);
        }
    } catch (error) {
        console.error('[ERROR] Exception in fetchWebsiteContent:', error);
    } finally {
        document.getElementById('fetchContentButton').disabled = false;
    }
}

async function loadWebsiteContent() {
    try {

        const response = await apiCall('/auth/website/content');

        
        if (response.ok) {
            const result = await response.json();

            
            if (result.success && result.content) {

                // Store website content globally for caching
                window.websiteContent = result.content;
                
                updateContentFetchDate(result.fetched_at);
                updateContentSummary(result.content);
            } else {

            }
        } else {

        }
    } catch (error) {
        console.error('[ERROR] Exception in loadWebsiteContent:', error);
    }
}

function updateContentFetchDate(fetchedAt = null) {
    const fetchDateElement = document.getElementById('contentFetchDateValue');
    if (fetchedAt) {
        const date = new Date(fetchedAt);
        fetchDateElement.textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } else {
        fetchDateElement.textContent = 'Never';
    }
}

function updateContentSummary(content) {
    const summaryElement = document.getElementById('contentSummary');
    if (!content) {
        summaryElement.innerHTML = '<p>No content data available.</p>';
        return;
    }

    let summaryHTML = '<div style="font-size: 0.875rem; color: #374151;">';
    
    // Title tags summary
    if (content.title_tags && Object.keys(content.title_tags).length > 0) {
        summaryHTML += '<p><strong>Title Tags:</strong> ' + Object.keys(content.title_tags).length + ' found</p>';
    }
    
    // Meta descriptions summary
    if (content.meta_descriptions && Object.keys(content.meta_descriptions).length > 0) {
        summaryHTML += '<p><strong>Meta Descriptions:</strong> ' + Object.keys(content.meta_descriptions).length + ' found</p>';
    }
    
    // Page content summary
    if (content.page_content) {
        const pageContent = content.page_content;
        if (pageContent.headings && pageContent.headings.length > 0) {
            summaryHTML += '<p><strong>Headings:</strong> ' + pageContent.headings.length + ' found</p>';
        }
        if (pageContent.links && pageContent.links.length > 0) {
            summaryHTML += '<p><strong>Links:</strong> ' + pageContent.links.length + ' found</p>';
        }
        if (pageContent.main) {
            summaryHTML += '<p><strong>Main Content:</strong> Available</p>';
        }
    }
    
    summaryHTML += '</div>';
    summaryElement.innerHTML = summaryHTML;
}

// Add event listener for fetch content button
document.addEventListener('DOMContentLoaded', function() {
    const fetchContentButton = document.getElementById('fetchContentButton');
    if (fetchContentButton) {
        fetchContentButton.addEventListener('click', fetchWebsiteContent);
    }
    
    // Load existing website content on page load
    loadWebsiteContent();
});









// Duplicate fetchMobileData function removed - using the comprehensive version above
// Duplicate fetchBusinessData function removed - using the enhanced version above with debugging
// Duplicate loadRealMetrics function removed - using the enhanced version above

// Add JS functions to show/hide the cache loading popup
function showCacheLoadingPopup() {
    const popup = document.getElementById('cacheLoadingPopup');
    if (popup) popup.style.display = 'flex';
}
function hideCacheLoadingPopup() {
    const popup = document.getElementById('cacheLoadingPopup');
    if (popup) popup.style.display = 'none';
}

function renderAIOverallAnalysis(insights, timestamp = null) {
    const card = document.getElementById('aiOverallAnalysisCard');
    // Never hide the card, even if insights are missing
    card.style.display = '';
    const summaryElement = document.getElementById('aiOverallSummary');
    const lastUpdatedElement = document.getElementById('aiLastUpdatedValue');
    
    if (!insights || !insights.analysis || Object.keys(insights.analysis).length === 0) {
        summaryElement.innerHTML = '<p>AI insights not available. Please try again later.</p>';
        lastUpdatedElement.textContent = 'Never';
        return;
    }
    
    // Update last updated date - use current time if no timestamp provided
    const updateTime = timestamp ? new Date(timestamp) : new Date();
    lastUpdatedElement.textContent = updateTime.toLocaleDateString() + ' ' + updateTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    // Display summary if available
    if (insights.analysis.summary) {
        summaryElement.innerHTML = `<p>${insights.analysis.summary}</p>`;
    } else if (insights.analysis.overall_assessment) {
        summaryElement.innerHTML = `<p><strong>Overall Assessment:</strong> ${insights.analysis.overall_assessment}</p>`;
    } else {
        summaryElement.innerHTML = '<p>AI analysis completed. Review the individual sections above for detailed insights.</p>';
    }
}

async function generateVisibilityInsights(summary) {
    try {
        // Use cached insights if available, otherwise fetch
        const insights = cachedAIInsights || await fetchAIInsights();
        window.lastInsights = insights;
        
        if (insights && insights.visibility_performance && insights.visibility_performance.metrics) {
            // Update individual metric analyses
            Object.entries(insights.visibility_performance.metrics).forEach(([metric, data]) => {
                
                let analysis = '';
                // Handle different possible data structures
                if (typeof data === 'string') {
                    analysis = data;
                } else if (data && typeof data === 'object') {
                    // Check if analysis is an object with text content
                    if (data.analysis && typeof data.analysis === 'object') {
                        // Create a meaningful summary from the analysis object
                        const analysisObj = data.analysis;
                        const parts = [];
                        
                        if (analysisObj.current_performance) {
                            parts.push(`${analysisObj.current_performance} performance`);
                        }
                        if (analysisObj.root_cause) {
                            parts.push(analysisObj.root_cause);
                        }
                        if (analysisObj.industry_context) {
                            parts.push(analysisObj.industry_context);
                        }
                        
                        // Clean up any double periods and ensure proper formatting
                        analysis = parts.join('. ').replace(/\.\.+/g, '.').replace(/\.\s*\./g, '. ').trim();
                    } else {
                        // Try different possible field names
                        analysis = data.analysis || data.summary || data.assessment || data.description || data.value || JSON.stringify(data);
                    }
                }
                
                // Map metric names to element IDs
                const metricElementMap = {
                    'impressions': 'impressionsAnalysis',
                    'clicks': 'clicksAnalysis',
                    'ctr': 'ctrAnalysis',
                    'average_position': 'avgPositionAnalysis'
                };
                
                const elementId = metricElementMap[metric];
                if (elementId && analysis) {
                    const element = document.getElementById(elementId);
                    if (element) {
                        element.textContent = analysis;
                        element.style.display = 'block';
                    }
                }
            });
            
            renderAIOverallAnalysis(insights);
        } else {
            console.log('[ERROR] No visibility insights available');
        }
    } catch (error) {
        console.error('Error generating visibility insights:', error);
    }
}

function updateUserMenuInfo() {
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const userEmail = payload.email || payload.sub || 'user@example.com';
        const userName = userEmail.includes('@') ? userEmail.split('@')[0] : userEmail;
        document.getElementById('userEmail').textContent = userEmail;
        document.getElementById('userAvatar').textContent = userName.charAt(0).toUpperCase();
        document.getElementById('mobileMenuEmail').textContent = userEmail;
        document.getElementById('mobileMenuAvatar').textContent = userName.charAt(0).toUpperCase();
    } catch (e) {
        // fallback
    }
}

// Move to the next metric after one is done
function setNextMetricLoading(currentKey) {
    const idx = METRIC_GROUPS.findIndex(m => m.key === currentKey);
    if (idx !== -1 && idx < METRIC_GROUPS.length - 1) {
        metricsLoadingState[METRIC_GROUPS[idx + 1].key] = 'loading';
        updateMetricsLoadingList();
    }
}

function showAIAnalysisPopup() {
    const popup = document.getElementById('aiAnalysisLoadingPopup');
    if (popup) {
        popup.style.display = 'flex';
        // Add the visible class after a small delay to trigger the animation
        setTimeout(() => {
            popup.classList.add('metrics-loading-visible');
            popup.classList.remove('metrics-loading-hide');
        }, 10);
    }
}
function hideAIAnalysisPopup() {
    const popup = document.getElementById('aiAnalysisLoadingPopup');
    if (popup) {
        popup.classList.add('metrics-loading-hide');
        popup.classList.remove('metrics-loading-visible');
        // Hide after animation completes
        setTimeout(() => {
            popup.style.display = 'none';
            popup.classList.remove('metrics-loading-hide');
        }, 500);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const regenerateBtn = document.getElementById('regenerateAIButton');
    if (regenerateBtn) {
        const regenBtnContent = regenerateBtn.querySelector('.regen-btn-content');
        const regenBtnIcon = regenerateBtn.querySelector('.regen-btn-icon');
        const regenBtnSpinner = regenerateBtn.querySelector('.regen-btn-spinner');
        
        if (!regenBtnContent || !regenBtnIcon || !regenBtnSpinner) {
            console.error('[ERROR] Regenerate button elements not found');
            return;
        }
        
        regenerateBtn.addEventListener('click', async function() {
            if (!confirm('Regenerating AI analysis will overwrite your previous insights and may disrupt your current SEO implementation progress. Are you sure you want to continue?')) {
                return;
            }
            showAIAnalysisPopup();
            regenerateBtn.disabled = true;
            regenerateBtn.classList.add('loading');
            regenBtnIcon.style.display = 'none';
            regenBtnSpinner.style.display = 'inline-block';
            try {
                const aiData = await fetchExplicitAIInsights();
                if (aiData) {
                    window.cachedAIInsights = aiData;
                    renderAIOverallAnalysis(aiData);
                } else {
                    alert('Failed to regenerate AI analysis. Please try again later.');
                }
            } finally {
                hideAIAnalysisPopup();
                regenerateBtn.disabled = false;
                regenerateBtn.classList.remove('loading');
                regenBtnIcon.style.display = '';
                regenBtnSpinner.style.display = 'none';
            }
        });
    }
});