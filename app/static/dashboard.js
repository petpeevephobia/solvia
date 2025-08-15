// Dashboard JavaScript - Clean Canvas Version

// Handle OAuth callback
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
        localStorage.setItem('auth_token', token);
        
        // Store user email from token
        try {
            const tokenData = JSON.parse(atob(token.split('.')[1]));
            const userEmail = tokenData.sub;
            localStorage.setItem('user_email', userEmail);
        } catch (error) {
            console.error('Error parsing token:', error);
        }
        
        // Clean up URL
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
        
        // Reload the page
        window.location.reload();
        return;
    }
}

// Basic authentication check
function checkAuth() {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
        window.location.href = '/ui';
        return false;
    }

    return true;
}

// Logout function
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('selected_domain');
                    window.location.href = '/ui';
}

// Display welcome message with user name and domain
function displayWelcomeMessage() {
    const welcomeMessage = document.getElementById('welcomeMessage');
    const selectedDomain = localStorage.getItem('selected_domain');
    
    try {
        const domainData = JSON.parse(selectedDomain);
        const userEmail = localStorage.getItem('user_email') || 'User';
        
        // Extract first name from email (before the @ symbol)
        const firstName = userEmail.split('@')[0];
        const capitalizedFirstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);
        
        // Convert domain URL to domain.com format
        let displayDomain = domainData.siteUrl;
        
        // Handle sc-domain: format
        if (displayDomain.startsWith('sc-domain:')) {
            displayDomain = displayDomain.replace('sc-domain:', '');
        }
        
        // Handle http/https URLs
        if (displayDomain.startsWith('http://') || displayDomain.startsWith('https://')) {
            try {
                const url = new URL(displayDomain);
                displayDomain = url.hostname;
            } catch (e) {
                // If URL parsing fails, try to extract domain manually
                displayDomain = displayDomain.replace(/^https?:\/\//, '');
            }
        }
        
        // Remove www. prefix if present
        displayDomain = displayDomain.replace(/^www\./, '');
        
        // Display welcome message like in the image
        welcomeMessage.innerHTML = `
            <div class="welcome-text">
                Hey, <span class="user-name">${capitalizedFirstName}</span>! We're tracking <span class="domain-name">${displayDomain}</span>.
            </div>
        `;
        
                    } catch (error) {
        console.error('Error parsing domain data:', error);
        welcomeMessage.innerHTML = `
            <div class="welcome-text">
                Welcome! Please <a href="/domain-selection" style="color: #f97316; text-decoration: none;">select a domain</a> to continue.
            </div>
        `;
    }
}

// Initialize dashboard
function initDashboard() {
    // Handle OAuth callback first
    handleOAuthCallback();
    
    // Check authentication
    if (!checkAuth()) {
        return;
    }

    // Check if user has selected a domain
    const selectedDomain = localStorage.getItem('selected_domain');
    if (!selectedDomain) {
        // No domain selected, redirect to domain selection
        window.location.href = '/domain-selection';
        return;
    }
    
    // Display welcome message
    displayWelcomeMessage();
    
    // Dashboard is ready - add your new functionality here
    console.log('Dashboard initialized successfully');
    
    // Load GSC metrics only if domain is selected
    loadGSCMetrics();
}

// Load Google Search Console metrics
async function loadGSCMetrics() {
    try {
        console.log('Loading GSC metrics...');
        const token = localStorage.getItem('auth_token');
        
        if (!token) {
            console.error('No auth token found');
        return;
    }

        const response = await fetch('/auth/gsc/metrics', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            console.error('Failed to load metrics:', errorData);
            
            // Show user-friendly error message
            if (errorData.detail === 'No website selected. Please select a domain first.') {
                console.log('No website selected, redirecting to domain selection...');
                window.location.href = '/domain-selection';
            return;
            }
                return;
            }
        
            const data = await response.json();
        console.log('GSC metrics loaded:', data);
        
        if (data.success && data.metrics) {
            displayMetrics(data.metrics);
        } else {
            console.error('No metrics data received');
        }
        
    } catch (error) {
        console.error('Error loading GSC metrics:', error);
    }
}

// Display metrics in the dashboard
function displayMetrics(metrics) {
    // SEO Score
    const seoScoreElement = document.getElementById('seoScore');
    const seoScoreChangeElement = document.getElementById('seoScoreChange');
    if (seoScoreElement) {
        seoScoreElement.textContent = `${metrics.seo_score || 0}/100`;
        seoScoreChangeElement.textContent = '5% from last month';
        seoScoreChangeElement.className = 'metric-change positive';
    }
    
    // Impressions
    const impressionsElement = document.getElementById('impressions');
    const impressionsChangeElement = document.getElementById('impressionsChange');
    if (impressionsElement) {
        impressionsElement.textContent = (metrics.impressions || 0).toLocaleString();
        impressionsChangeElement.textContent = '12% from last month';
        impressionsChangeElement.className = 'metric-change positive';
    }
    
    // Average Position
    const avgPositionElement = document.getElementById('avgPosition');
    const avgPositionChangeElement = document.getElementById('avgPositionChange');
    if (avgPositionElement) {
        avgPositionElement.textContent = metrics.avg_position || 0;
        avgPositionChangeElement.textContent = '1.6 positions';
        avgPositionChangeElement.className = 'metric-change positive';
    }
    
    // CTR
    const ctrElement = document.getElementById('ctr');
    const ctrChangeElement = document.getElementById('ctrChange');
    if (ctrElement) {
        ctrElement.textContent = `${(metrics.ctr || 0).toFixed(2)}%`;
        ctrChangeElement.textContent = '0.5% from last month';
        ctrChangeElement.className = 'metric-change positive';
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initDashboard);

