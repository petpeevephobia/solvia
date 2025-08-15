// Domain Selection JavaScript

let selectedDomain = null;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check for token in URL first (from OAuth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');
    
    if (tokenFromUrl) {
        // Store the token from URL
        localStorage.setItem('auth_token', tokenFromUrl);
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    const token = localStorage.getItem('auth_token');
    if (!token) {
        console.log('No token found, redirecting to login');
        window.location.href = '/ui';
        return;
    }
    
    console.log('Token found, proceeding with domain loading');
    
    // Store user email from token for later use
    try {
        const tokenData = JSON.parse(atob(token.split('.')[1]));
        const userEmail = tokenData.sub;
        localStorage.setItem('user_email', userEmail);
        console.log('User email stored:', userEmail);
    } catch (error) {
        console.error('Error parsing token:', error);
    }
    
    loadDomains();
});

// Load domains from Google Search Console
async function loadDomains() {
    const domainList = document.getElementById('domainList');
    const refreshBtn = document.getElementById('refreshBtn');
    
    try {
        domainList.innerHTML = '<div class="loading">Loading your domains...</div>';
        refreshBtn.classList.add('loading');
        
        console.log('Fetching domains from /auth/gsc/properties...');
        const token = localStorage.getItem('auth_token');
        console.log('Token available:', !!token);
        console.log('Token preview:', token ? token.substring(0, 50) + '...' : 'No token');
        
        const response = await fetch('/auth/gsc/properties', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Response error:', errorText);
            throw new Error(`Failed to load domains: ${response.status} ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.properties && data.properties.length > 0) {
            console.log('Found properties:', data.properties);
            displayDomains(data.properties);
                 } else {
             console.log('No properties found');
             domainList.innerHTML = `
                 <div class="loading">
                     <p>No domains found in your Google Search Console account.</p>
                     <p>This usually means you need to re-authenticate with Google.</p>
                     <button onclick="reAuthenticate()" class="refresh-btn" style="margin-top: 1rem;">
                         Re-authenticate with Google
                     </button>
                     <p><strong>Debug:</strong> Response: ${JSON.stringify(data)}</p>
                 </div>
             `;
         }
        
    } catch (error) {
        console.error('Error loading domains:', error);
        domainList.innerHTML = `
            <div class="loading">
                <p>Error loading domains. Please try again.</p>
                <p><strong>Error:</strong> ${error.message}</p>
                <p>Check the browser console for more details.</p>
            </div>
        `;
    } finally {
        refreshBtn.classList.remove('loading');
    }
}

// Display domains in the list
function displayDomains(properties) {
    const domainList = document.getElementById('domainList');
    
    domainList.innerHTML = properties.map(property => {
        // Use simple domain naming
        let domainName = property.siteName;
        if (!domainName || domainName === 'Unnamed Site') {
            try {
                const url = new URL(property.siteUrl);
                const domain = url.hostname.replace('www.', '');
                domainName = domain;
            } catch (error) {
                // Fallback: use clean siteUrl
                const cleanUrl = property.siteUrl.replace(/^https?:\/\//, '').replace('www.', '');
                domainName = cleanUrl;
            }
        }
        
        return `
            <div class="domain-item" onclick="selectDomain('${property.siteUrl}', '${domainName}')">
                <div class="domain-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                        <polyline points="9,22 9,12 15,12 15,22"></polyline>
                    </svg>
                </div>
                <div class="domain-info">
                    <div class="domain-name">${domainName}</div>
                    <div class="domain-url">${property.siteUrl}</div>
                </div>
                <div class="select-indicator"></div>
            </div>
        `;
    }).join('');
}

// Select a domain
async function selectDomain(siteUrl, siteName) {
    // Remove previous selection
    document.querySelectorAll('.domain-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Add selection to clicked item
    event.currentTarget.classList.add('selected');
    
    selectedDomain = { siteUrl, siteName };
    
    // Store the selection in localStorage
    localStorage.setItem('selected_domain', JSON.stringify(selectedDomain));
    
    // Also store the selection in the backend database
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch('/auth/gsc/select-property', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                property_url: siteUrl
            })
        });
        
        if (!response.ok) {
            console.error('Failed to store domain selection in database');
        } else {
            console.log('Domain selection stored in database successfully');
        }
    } catch (error) {
        console.error('Error storing domain selection:', error);
    }
    
    // Redirect to dashboard after a brief delay
    setTimeout(() => {
        window.location.href = '/dashboard';
    }, 500);
}

// Refresh domains
function refreshDomains() {
    loadDomains();
}

// Re-authenticate with Google
async function reAuthenticate() {
    try {
        // First, try to clear credentials from backend
        const token = localStorage.getItem('auth_token');
        if (token) {
            await fetch('/auth/gsc/clear-credentials', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        }
    } catch (error) {
        console.log('Could not clear credentials:', error);
    }
    
    // Clear any existing tokens
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_email');
    localStorage.removeItem('selected_domain');
    
    // Redirect to login page to start fresh OAuth flow
    window.location.href = '/ui';
}
