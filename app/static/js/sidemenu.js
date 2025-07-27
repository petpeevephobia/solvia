// Reusable Sidemenu Component
function createSideMenu(activePage = 'dashboard') {
    return `
        <!-- Side Menu -->
        <div class="side-menu">
            <!-- Top Section - Logo -->
            <div class="menu-top">
                <div class="logo-section">
                    <img src="/static/images/text-logo.svg" alt="Solvia Logo" class="menu-logo">
                </div>
            </div>

            <!-- Main Navigation Section -->
            <div class="menu-main">
                <div class="menu-item ${activePage === 'dashboard' ? 'active' : ''}" onclick="navigateToPage('dashboard')">
                    <img src="/static/images/home.svg" alt="Dashboard" class="menu-icon">
                    <span class="menu-text">Dashboard</span>
                </div>
                
                <div class="menu-item agents-item" onclick="toggleAgentsDropdown()">
                    <img src="/static/images/agent.svg" alt="Agents" class="menu-icon">
                    <span class="menu-text">Agents</span>
                    <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none">
                        <polyline points="6,9 12,15 18,9" stroke="#374151" stroke-width="2"/>
                    </svg>
                </div>
                
                <!-- Agents Dropdown -->
                <div class="agents-dropdown" id="agentsDropdown">
                    <div class="dropdown-item">
                        <span class="dropdown-text">Kenji - Keyword Agent</span>
                    </div>
                    <div class="dropdown-item">
                        <span class="dropdown-text">Myer - Metadata Agent</span>
                    </div>
                </div>
                
                <div class="menu-item" onclick="navigateToPage('fixes')">
                    <img src="/static/images/fixes.svg" alt="Fixes" class="menu-icon">
                    <span class="menu-text">Fixes</span>
                </div>
            </div>

            <!-- AI Chat Model Info -->
            <div class="ai-model-info">
                <span class="model-text">AI Chat Model: GPT o4-mini</span>
            </div>

            <!-- Bottom Section - Utilities -->
            <div class="menu-bottom">
                <div class="menu-item notification" onclick="navigateToPage('notifications')">
                    <img src="/static/images/bell.svg" alt="Notifications" class="menu-icon">
                    <span class="menu-text">Notifications</span>
                </div>
                
                <div class="menu-item ${activePage === 'settings' ? 'active' : ''}" onclick="navigateToPage('settings')">
                    <img src="/static/images/settings.svg" alt="Settings" class="menu-icon">
                    <span class="menu-text">Settings</span>
                </div>
                
                <div class="menu-item" onclick="logout()">
                    <img src="/static/images/logout.svg" alt="Log out" class="menu-icon">
                    <span class="menu-text">Log out</span>
                </div>
            </div>

            <!-- User Profile Section -->
            <div class="user-profile">
                <div class="profile-icon">
                    <svg class="menu-icon" viewBox="0 0 24 24" fill="none">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="#EC6019" stroke-width="2"/>
                        <circle cx="12" cy="7" r="4" stroke="#EC6019" stroke-width="2"/>
                    </svg>
                </div>
                <span class="user-email" id="userEmail">Loading...</span>
                <svg class="profile-arrow" viewBox="0 0 24 24" fill="none">
                    <polyline points="9,18 15,12 9,6" stroke="#374151" stroke-width="2"/>
                </svg>
            </div>
        </div>
    `;
}

// Navigation functions
function navigateToPage(page) {
    const accessToken = getAccessToken();
    switch(page) {
        case 'dashboard':
            window.location.href = `/dashboard?access_token=${accessToken}`;
            break;
        case 'settings':
            window.location.href = `/settings?access_token=${accessToken}`;
            break;
        case 'fixes':
            console.log('Fixes page coming soon');
            break;
        case 'notifications':
            console.log('Notifications coming soon');
            break;
    }
}

function toggleAgentsDropdown() {
    const dropdown = document.getElementById('agentsDropdown');
    const agentsItem = document.querySelector('.agents-item');
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
        agentsItem.classList.remove('expanded');
    } else {
        dropdown.classList.add('show');
        agentsItem.classList.add('expanded');
    }
}

async function logout() {
    const accessToken = getAccessToken();
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        window.location.href = '/ui';
    } catch (error) {
        console.error('Error logging out:', error);
        window.location.href = '/ui';
    }
}

function getAccessToken() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('access_token');
}

// Initialize sidemenu
function initSideMenu(activePage = 'dashboard') {
    const sidemenuContainer = document.getElementById('sidemenu-container');
    if (sidemenuContainer) {
        sidemenuContainer.innerHTML = createSideMenu(activePage);
        loadUserData();
    }
}

// Load user data for sidemenu
async function loadUserData() {
    const accessToken = getAccessToken();
    if (!accessToken) return;
    
    try {
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            const userEmailElement = document.getElementById('userEmail');
            if (userEmailElement) {
                userEmailElement.textContent = userData.email;
            }
        }
    } catch (error) {
        console.error('Error loading user data:', error);
    }
} 