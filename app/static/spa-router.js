// SPA Router for Solvia Dashboard
// Handles client-side routing and content loading

class SolviaRouter {
    constructor() {
        this.routes = {
            'dashboard': {
                title: 'Dashboard - Solvia',
                loadContent: this.loadDashboard.bind(this)
            },
            'audit-history': {
                title: 'Audit History - Solvia',
                loadContent: this.loadAuditHistory.bind(this)
            },
            'settings': {
                title: 'Settings - Solvia',
                loadContent: this.loadSettings.bind(this)
            }
        };

        this.currentRoute = null;
        this.isAuthChecking = false; // Prevent multiple auth checks
        this.hasAuthError = false; // Track if we've already had an auth error
        this.init();
    }

    init() {
        // Check for token first
        const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
        if (!token) {
            console.log('⚠️ SPA: No token found during init, redirecting to login...');
            window.location.href = '/login';
            return;
        }

        // Initialize logo state
        this.initializeLogo();

        // Handle browser back/forward
        window.addEventListener('popstate', this.handlePopState.bind(this));

        // Handle navigation clicks
        document.addEventListener('click', this.handleNavClick.bind(this));

        // Load initial route
        this.loadInitialRoute();

        // Load user info once
        this.loadUserInfo();

        // Show app
        document.body.classList.add('loaded');
    }

    // Initialize logo based on sidebar state
    initializeLogo() {
        const sidebar = document.getElementById('sidebar');
        const logoImg = document.getElementById('logo-img');

        console.log('🔧 SPA: Initialize Logo - sidebar:', sidebar, 'logoImg:', logoImg);

        if (!logoImg) {
            console.error('❌ Logo img element not found!');
            return;
        }

        // Set initial logo based on sidebar state
        if (sidebar && sidebar.classList.contains('expanded')) {
            console.log('🔄 Setting logo to logo_v2.png (expanded)');
            logoImg.src = '/static/logo_v2.png?' + Date.now();
        } else {
            console.log('🔄 Setting logo to orange-svg-emblem-40px.svg (collapsed)');
            logoImg.src = '/static/orange-svg-emblem-40px.svg?' + Date.now();
        }
    }

    loadInitialRoute() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        console.log(`🚀 SPA: Loading initial route: ${hash}`);
        // Force update active nav on initial load even if currentRoute is null
        this.updateActiveNav(hash);
        this.navigateTo(hash, false);
    }

    handlePopState(event) {
        const hash = window.location.hash.slice(1) || 'dashboard';
        this.navigateTo(hash, false);
    }

    handleNavClick(event) {
        const target = event.target.closest('[data-route]');
        if (target) {
            event.preventDefault();
            const route = target.getAttribute('data-route');
            this.navigateTo(route);
        }
    }

    navigateTo(route, pushState = true) {
        if (this.currentRoute === route) return;

        console.log(`🔄 SPA: Navigating to ${route}`);

        // Update URL
        if (pushState) {
            window.history.pushState({ route }, '', `#${route}`);
        }

        // Update active nav item
        this.updateActiveNav(route);

        // Load content
        this.loadRoute(route);
    }

    updateActiveNav(route) {
        console.log(`📍 SPA: Updating active nav for route: ${route}`);

        // Remove active class from all nav items
        document.querySelectorAll('.nav-item, .sidebar-footer-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current route
        const activeItem = document.querySelector(`[data-route="${route}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
            console.log(`✅ SPA: Added active class to ${route}`);
        } else {
            console.warn(`⚠️ SPA: Could not find nav item for route ${route}`);
        }
    }

    async loadRoute(route) {
        const routeConfig = this.routes[route];
        if (!routeConfig) {
            console.error(`Route ${route} not found`);
            return;
        }

        // Show loading
        this.showLoading();

        try {
            // Update page title
            document.title = routeConfig.title;

            // Load content
            await routeConfig.loadContent();

            // Update current route
            this.currentRoute = route;

            console.log(`✅ SPA: Route ${route} loaded successfully`);
        } catch (error) {
            console.error(`❌ SPA: Error loading route ${route}:`, error);
            this.showError(`Error loading ${route}`);
        }
    }

    showLoading() {
        const loadingEl = document.getElementById('contentLoading');
        const contentEl = document.getElementById('app-content');

        if (loadingEl) loadingEl.classList.remove('hidden');
        if (contentEl) {
            contentEl.classList.remove('loaded');
            contentEl.innerHTML = '';
        }
    }

    showContent(html) {
        const loadingEl = document.getElementById('contentLoading');
        const contentEl = document.getElementById('app-content');

        if (loadingEl) loadingEl.classList.add('hidden');
        if (contentEl) {
            contentEl.innerHTML = html;
            contentEl.classList.add('loaded');
        }
    }

    showError(message) {
        const errorHtml = `
            <div style="padding: 32px; text-align: center;">
                <h2 style="color: #EF4444; margin-bottom: 16px;">⚠️ ${message}</h2>
                <p style="color: #6B7280;">Please try refreshing the page or contact support.</p>
            </div>
        `;
        this.showContent(errorHtml);
    }

    // Content Loaders
    async loadDashboard() {
        console.log('📊 Loading Dashboard content...');

        // Dashboard content template
        const dashboardHtml = `
            <div style="padding: 32px;">
                <div class="header" style="margin-bottom: 32px;">
                    <div class="header-content" id="headerContent">
                        <!-- Skeleton loading for header -->
                        <div id="headerSkeleton" style="display: flex; align-items: center; gap: 8px;">
                            <div class="skeleton-text" style="height: 32px; width: 60px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px;"></div>
                            <div class="skeleton-text" style="height: 32px; width: 120px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px;"></div>
                            <div class="skeleton-text" style="height: 32px; width: 150px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px;"></div>
                            <div class="skeleton-text" style="height: 32px; width: 200px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px;"></div>
                        </div>
                        <!-- Real header - hidden initially -->
                        <h1 id="realHeader" style="font-size: 24px; display: none;">Hey, <span id="userName"></span>! We're tracking <span id="websiteUrl" style="color: #EC6019;"></span></h1>
                    </div>
                </div>

                <!-- Overview Section -->

                <section class="overview">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h2 style="margin: 0;">Overview</h2>
                        <div id="inline-audit-info" style="display: none; font-size: 14px; color: #6B7280;">
                            <span style="margin-right: 20px;">Latest Audit: <span id="audit-time" style="color: #1F2937; font-weight: 600;"></span></span>
                            <div style="position: relative; display: inline-block;">
                                <button onclick="toggleDownloadMenu(event)" style="
                                    background: white;
                                    color: #EC6019;
                                    padding: 8px 14px;
                                    border: 1px solid #EC6019;
                                    border-radius: 8px;
                                    font-size: 13px;
                                    font-weight: 500;
                                    cursor: pointer;
                                    display: flex;
                                    align-items: center;
                                    gap: 6px;
                                    transition: all 0.2s;
                                " onmouseover="this.style.background='#EC6019'; this.style.color='white'; this.querySelector('path').setAttribute('stroke', 'white');"
                                   onmouseout="this.style.background='white'; this.style.color='#EC6019'; this.querySelector('path').setAttribute('stroke', '#EC6019');">
                                    <span>📥 Download</span>
                                    <svg width="10" height="10" viewBox="0 0 12 12" fill="none" style="transition: transform 0.2s;">
                                        <path d="M3 4.5L6 7.5L9 4.5" stroke="#EC6019" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    </svg>
                                </button>
                                <div id="download-menu" style="
                                    display: none;
                                    position: absolute;
                                    top: calc(100% + 4px);
                                    right: 0;
                                    background: white;
                                    border: 1px solid #e5e7eb;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                                    overflow: visible;
                                    min-width: 150px;
                                    z-index: 10000;
                                ">
                                    <div onclick="downloadAuditPDF(window.currentAuditId); closeDownloadMenu();" style="
                                        width: 100%;
                                        padding: 10px 16px;
                                        background: white;
                                        color: #1F2937;
                                        font-size: 13px;
                                        font-weight: 500;
                                        cursor: pointer;
                                        display: flex;
                                        align-items: center;
                                        gap: 10px;
                                        transition: background 0.2s;
                                        box-sizing: border-box;
                                    " onmouseover="this.style.background='#FFF5F0'" onmouseout="this.style.background='white'">
                                        <span style="font-size: 16px;">📄</span>
                                        <span>PDF Report</span>
                                    </div>
                                    <div onclick="downloadAuditJSON(window.currentAuditId); closeDownloadMenu();" style="
                                        width: 100%;
                                        padding: 10px 16px;
                                        background: white;
                                        color: #1F2937;
                                        font-size: 13px;
                                        font-weight: 500;
                                        cursor: pointer;
                                        display: flex;
                                        align-items: center;
                                        gap: 10px;
                                        transition: background 0.2s;
                                        border-top: 1px solid #f0f0f0;
                                        box-sizing: border-box;
                                    " onmouseover="this.style.background='#FFF5F0'" onmouseout="this.style.background='white'">
                                        <span style="font-size: 16px;">📊</span>
                                        <span>JSON Data</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="metrics-grid">
                        <!-- Skeleton Loading for Metrics - shown initially -->
                        <div class="metrics-skeleton" id="metricsSkeleton">
                            <!-- SEO Score Skeleton -->
                            <div class="skeleton-metric-card">
                                <div class="skeleton-metric-icon"></div>
                                <div class="skeleton-metric-content">
                                    <div class="skeleton-metric-label"></div>
                                    <div class="skeleton-metric-value"></div>
                                    <div class="skeleton-metric-change"></div>
                                </div>
                            </div>

                            <!-- Organic Traffic Skeleton -->
                            <div class="skeleton-metric-card">
                                <div class="skeleton-metric-icon"></div>
                                <div class="skeleton-metric-content">
                                    <div class="skeleton-metric-label"></div>
                                    <div class="skeleton-metric-value"></div>
                                    <div class="skeleton-metric-change"></div>
                                </div>
                            </div>

                            <!-- Avg. Position Skeleton -->
                            <div class="skeleton-metric-card">
                                <div class="skeleton-metric-icon"></div>
                                <div class="skeleton-metric-content">
                                    <div class="skeleton-metric-label"></div>
                                    <div class="skeleton-metric-value"></div>
                                    <div class="skeleton-metric-change"></div>
                                </div>
                            </div>

                            <!-- Backlinks Skeleton -->
                            <div class="skeleton-metric-card">
                                <div class="skeleton-metric-icon"></div>
                                <div class="skeleton-metric-content">
                                    <div class="skeleton-metric-label"></div>
                                    <div class="skeleton-metric-value"></div>
                                    <div class="skeleton-metric-change"></div>
                                </div>
                            </div>
                        </div>

                        <!-- Real Metrics - Hidden initially -->
                        <div class="real-metrics hidden" id="realMetrics">
                            <div class="metric-card">
                                <div class="metric-icon-container">
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
                                        <path stroke="#EC6019" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                    </svg>
                                </div>
                                <div class="metric-content">
                                    <div class="metric-label">SEO Score</div>
                                    <div class="metric-value" id="seoScore">Loading...</div>
                                    <div class="metric-change neutral" id="seoChange">Based on real GSC data</div>
                                </div>
                            </div>

                            <div class="metric-card">
                                <div class="metric-icon-container">
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
                                        <path stroke="#EC6019" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                                    </svg>
                                </div>
                                <div class="metric-content">
                                    <div class="metric-label">Organic Traffic</div>
                                    <div class="metric-value" id="organicTraffic">Loading...</div>
                                    <div class="metric-change neutral" id="trafficChange">Clicks from last 30 days</div>
                                </div>
                            </div>

                            <div class="metric-card">
                                <div class="metric-icon-container">
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
                                        <path stroke="#EC6019" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                    </svg>
                                </div>
                                <div class="metric-content">
                                    <div class="metric-label">Avg. Keyword Position</div>
                                    <div class="metric-value" id="avgPosition">Loading...</div>
                                    <div class="metric-change neutral" id="positionChange">Search ranking position</div>
                                </div>
                            </div>

                            <div class="metric-card">
                                <div class="metric-icon-container">
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
                                        <path stroke="#EC6019" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                                    </svg>
                                </div>
                                <div class="metric-content">
                                    <div class="metric-label">Backlinks</div>
                                    <div class="metric-value" id="backlinks">Loading...</div>
                                    <div class="metric-change neutral" id="backlinksChange">External sites linking to you</div>
                                </div>
                            </div>
                        </div>
                        <!-- End of real-metrics -->
                    </div>
                </section>

                <!-- Current Issues Section -->
                <section class="current-issues">
                    <div class="current-issues-header">
                        <h2>Current Issues</h2>
                        <button class="run-audit-btn" onclick="runNewAudit()" id="auditBtn">Run a new audit</button>
                    </div>
                    <div class="issues-grid" id="issuesContainer">
                        <!-- Loading Skeleton - shown initially -->
                        <div class="issues-skeleton" id="issuesSkeleton">
                            <div class="skeleton-issue-card">
                                <div class="skeleton-header">
                                    <div class="skeleton-icon"></div>
                                    <div class="skeleton-title"></div>
                                </div>
                                <div class="skeleton-description"></div>
                                <div class="skeleton-description short"></div>
                                <div class="skeleton-fix"></div>
                            </div>

                            <div class="skeleton-issue-card">
                                <div class="skeleton-header">
                                    <div class="skeleton-icon"></div>
                                    <div class="skeleton-title"></div>
                                </div>
                                <div class="skeleton-description"></div>
                                <div class="skeleton-description short"></div>
                                <div class="skeleton-fix"></div>
                            </div>

                            <div class="skeleton-issue-card">
                                <div class="skeleton-header">
                                    <div class="skeleton-icon"></div>
                                    <div class="skeleton-title"></div>
                                </div>
                                <div class="skeleton-description"></div>
                                <div class="skeleton-description short"></div>
                                <div class="skeleton-fix"></div>
                            </div>
                        </div>

                        <!-- Real Issues - Initially hidden, populated by loadCurrentIssues -->
                        <div class="real-issues hidden" id="realIssues">
                            <div id="issuesContainer">
                                <!-- Issues will be dynamically loaded here -->
                            </div>
                        </div>
                    </div>
                </section>

                <!-- Solvia Chat Section -->
                <section class="chat-section">
                    <div class="chat-header">
                        <h2>Solvia</h2>
                        <p>I oversee your entire SEO team. Ask me anything about your SEO performance.</p>
                    </div>
                    <div class="chat-container">
                        <div class="chat-messages" id="chatMessages">
                            <!-- Skeleton Loading for Chat - will be hidden after chat loads -->
                            <div class="chat-skeleton" id="chatSkeleton">
                                <div class="skeleton-message ai">
                                    <div class="skeleton-avatar"></div>
                                    <div class="skeleton-message-content">
                                        <div class="skeleton-message-line" style="width: 60%;"></div>
                                        <div class="skeleton-message-line" style="width: 80%;"></div>
                                    </div>
                                </div>
                                <div class="skeleton-message user">
                                    <div class="skeleton-message-content">
                                        <div class="skeleton-message-line" style="width: 70%;"></div>
                                    </div>
                                    <div class="skeleton-avatar"></div>
                                </div>
                                <div class="skeleton-message ai">
                                    <div class="skeleton-avatar"></div>
                                    <div class="skeleton-message-content">
                                        <div class="skeleton-message-line" style="width: 90%;"></div>
                                        <div class="skeleton-message-line" style="width: 75%;"></div>
                                        <div class="skeleton-message-line" style="width: 40%;"></div>
                                    </div>
                                </div>
                            </div>
                            <!-- Default Welcome Message (hidden during loading) -->
                            <div class="chat-message ai hidden" id="welcomeMessage">
                                <div class="message-avatar ai">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                                    </svg>
                                </div>
                                <div class="message-content ai">
                                    <div class="message-text">Hello! I'm Solvia, your SEO agent. How can I help you today?</div>
                                </div>
                            </div>
                        </div>

                        <div class="chat-input-container">
                            <textarea
                                class="chat-input"
                                id="chatInput"
                                placeholder="Ask about your SEO performance..."
                                rows="1"
                                onkeypress="handleChatKeypress(event)"
                            ></textarea>
                            <button class="chat-send-btn" onclick="sendChatMessage()" id="sendBtn">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                                </svg>
                            </button>
                        </div>

                        <div class="chat-suggestions">
                            <button class="suggestion-btn" onclick="sendSuggestionWithRotation('How was my SEO last week?')">How was my SEO last week?</button>
                            <button class="suggestion-btn" onclick="sendSuggestionWithRotation('Run a new audit')">Run a new audit</button>
                            <button class="suggestion-btn" onclick="sendSuggestionWithRotation('What are my top issues?')">What are my top issues?</button>
                            <button class="suggestion-btn" onclick="sendSuggestionWithRotation('Show me traffic trends')">Show me traffic trends</button>
                        </div>
                    </div>
                </section>
            </div>
        `;

        this.showContent(dashboardHtml);

        // Load all dashboard data components
        try {
            // Load data in parallel for better performance
            await Promise.all([
                this.loadDashboardData(),
                this.loadChatHistory()
            ]);
            console.log('✅ SPA: Dashboard loaded completely');
        } catch (error) {
            console.error('❌ SPA: Error loading dashboard:', error);
        }
    }

    async loadAuditHistory() {
        console.log('📋 Loading Audit History content...');

        // Initialize audit history state
        this.auditHistoryState = {
            audits: [],
            currentPage: 1,
            totalPages: 1,
            pageSize: 10,
            sortBy: 'created_at',
            sortOrder: 'desc',
            filter: 'all',
            loading: false
        };

        // Show skeleton first
        const skeletonHtml = `
            <div style="padding: 32px; min-height: 600px;">
                <div style="margin-bottom: 32px;">
                    <h1 style="font-size: 32px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">Audit History</h1>
                    <p style="font-size: 14px; color: #6B7280;">View and manage all your SEO audit reports with advanced filtering and pagination</p>
                </div>

                <!-- Filter and Controls Section -->
                <div style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); margin-bottom: 24px;" id="auditControls">
                    <div class="loading-skeleton" style="height: 60px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 8px;"></div>
                </div>

                <!-- Audit History Container -->
                <div id="auditHistoryContainer" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
                    <div class="loading-skeleton" style="height: 400px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 8px;"></div>
                </div>

                <!-- Pagination Container -->
                <div id="auditPagination" style="margin-top: 24px;">
                    <div class="loading-skeleton" style="height: 48px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 8px;"></div>
                </div>
            </div>
        `;

        this.showContent(skeletonHtml);

        // Load actual audit history data
        await this.loadAuditHistoryData();
    }

    async loadAuditHistoryData(page = 1, limit = 10, sortBy = 'created_at', sortOrder = 'desc', filter = 'all') {
        try {
            this.auditHistoryState.loading = true;
            this.updateLoadingState(true);

            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const offset = (page - 1) * limit;

            // Build query parameters
            const params = new URLSearchParams({
                limit: limit.toString(),
                offset: offset.toString()
            });

            const response = await fetch(`/agent/history?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const audits = await response.json();
                console.log('📊 SPA: Audit history data received:', audits.length, 'audits');

                // Update state - Fix pagination calculation
                this.auditHistoryState.audits = audits;
                this.auditHistoryState.currentPage = page;

                // Proper pagination: if we got a full page, there might be more
                // If less than limit, we're on the last page
                if (audits.length === limit) {
                    // There might be more pages, estimate based on current data
                    this.auditHistoryState.totalPages = page + 1; // At least one more page
                } else {
                    // This is the last page
                    this.auditHistoryState.totalPages = page;
                }

                this.auditHistoryState.loading = false;

                // Apply client-side filtering and sorting if needed
                let filteredAudits = this.filterAudits(audits, filter);
                filteredAudits = this.sortAudits(filteredAudits, sortBy, sortOrder);

                // Render the complete audit history interface
                this.renderAuditHistoryInterface(filteredAudits);
            } else {
                console.log('❌ SPA: Failed to load audit history, status:', response.status);
                this.renderEmptyState();
            }
        } catch (error) {
            console.error('Error loading audit history:', error);
            this.renderErrorState(error.message);
        }
    }

    filterAudits(audits, filter) {
        if (filter === 'all') return audits;

        const now = new Date();
        return audits.filter(audit => {
            const auditDate = new Date(audit.created_at);
            const daysDiff = (now - auditDate) / (1000 * 60 * 60 * 24);

            switch (filter) {
                case 'week': return daysDiff <= 7;
                case 'month': return daysDiff <= 30;
                case 'high_score': return audit.seo_score >= 80;
                case 'low_score': return audit.seo_score < 50;
                case 'critical_issues': return audit.critical_issues > 0;
                default: return true;
            }
        });
    }

    sortAudits(audits, sortBy, sortOrder) {
        return audits.sort((a, b) => {
            let aVal = a[sortBy];
            let bVal = b[sortBy];

            if (sortBy === 'created_at') {
                aVal = new Date(aVal);
                bVal = new Date(bVal);
            }

            if (sortOrder === 'desc') {
                return bVal > aVal ? 1 : -1;
            } else {
                return aVal > bVal ? 1 : -1;
            }
        });
    }

    renderAuditHistoryInterface(audits) {
        // Render controls
        this.renderAuditControls();

        // Render audit list
        if (audits && audits.length > 0) {
            this.renderAuditList(audits);
        } else {
            this.renderEmptyState();
        }

        // Render pagination
        this.renderPagination();
    }

    renderAuditControls() {
        const controlsContainer = document.getElementById('auditControls');
        if (!controlsContainer) return;

        const controlsHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                <!-- Left side: Filters -->
                <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <label style="font-size: 14px; font-weight: 500; color: #374151;">Filter:</label>
                        <select id="auditFilter" onchange="router.handleFilterChange(this.value)" style="padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 14px; color: #1F2937; background: white;">
                            <option value="all">All Audits</option>
                            <option value="week">Last Week</option>
                            <option value="month">Last Month</option>
                            <option value="high_score">High Score (80+)</option>
                            <option value="low_score">Low Score (<50)</option>
                            <option value="critical_issues">Critical Issues</option>
                        </select>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <label style="font-size: 14px; font-weight: 500; color: #374151;">Sort:</label>
                        <select id="auditSort" onchange="router.handleSortChange(this.value)" style="padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 14px; color: #1F2937; background: white;">
                            <option value="created_at_desc">Newest First</option>
                            <option value="created_at_asc">Oldest First</option>
                            <option value="seo_score_desc">Highest Score</option>
                            <option value="seo_score_asc">Lowest Score</option>
                        </select>
                    </div>
                </div>

                <!-- Right side: Actions -->
                <div style="display: flex; align-items: center; gap: 12px;">
                    <button onclick="router.refreshAuditHistory()" style="padding: 8px 16px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 16px;">🔄</span> Refresh
                    </button>
                </div>
            </div>
        `;

        controlsContainer.innerHTML = controlsHtml;
    }

    renderAuditList(audits) {
        const container = document.getElementById('auditHistoryContainer');
        if (!container) return;

        let auditListHtml = `
            <div style="margin-bottom: 20px;">
                <h3 style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 16px;">
                    Audit Reports (${audits.length} found)
                </h3>
            </div>

            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background: #F9FAFB; border-bottom: 2px solid #E5E7EB;">
                            <th style="padding: 12px; text-align: left; font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; letter-spacing: 0.05em;">Date</th>
                            <th style="padding: 12px; text-align: left; font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; letter-spacing: 0.05em;">Website</th>
                            <th style="padding: 12px; text-align: center; font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; letter-spacing: 0.05em;">SEO Score</th>
                            <th style="padding: 12px; text-align: center; font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; letter-spacing: 0.05em;">Issues</th>
                            <th style="padding: 12px; text-align: center; font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; letter-spacing: 0.05em;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        audits.forEach(audit => {
            const auditDate = new Date(audit.created_at);
            const formattedDate = auditDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            // Score color based on value
            const scoreColor = audit.seo_score >= 80 ? '#10B981' :
                              audit.seo_score >= 60 ? '#F59E0B' : '#EF4444';
            const scoreBg = audit.seo_score >= 80 ? '#D1FAE5' :
                           audit.seo_score >= 60 ? '#FEF3C7' : '#FEE2E2';

            // Issue counts
            const totalIssues = (audit.critical_issues || 0) + (audit.high_issues || 0) +
                               (audit.medium_issues || 0) + (audit.low_issues || 0);

            auditListHtml += `
                <tr style="border-bottom: 1px solid #E5E7EB; transition: background-color 0.2s ease;" onmouseover="this.style.backgroundColor='#F9FAFB'" onmouseout="this.style.backgroundColor='white'">
                    <!-- Date -->
                    <td style="padding: 16px 12px; font-size: 14px; color: #1F2937; white-space: nowrap;">
                        ${formattedDate}
                    </td>

                    <!-- Website -->
                    <td style="padding: 16px 12px; font-size: 14px; color: #6B7280; max-width: 200px; overflow: hidden; text-overflow: ellipsis;">
                        ${audit.website_url || 'Website'}
                    </td>

                    <!-- SEO Score with Donut Chart -->
                    <td style="padding: 16px 12px; text-align: center;">
                        <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
                            <div style="position: relative; width: 40px; height: 40px;">
                                <svg width="40" height="40" viewBox="0 0 40 40" style="transform: rotate(-90deg);">
                                    <!-- Background circle -->
                                    <circle cx="20" cy="20" r="15" fill="none" stroke="#E5E7EB" stroke-width="3"></circle>
                                    <!-- Progress circle -->
                                    <circle cx="20" cy="20" r="15" fill="none" stroke="${scoreColor}" stroke-width="3"
                                            stroke-dasharray="${(Math.round(audit.seo_score || 0) / 100) * 94.2} 94.2"
                                            stroke-linecap="round"></circle>
                                </svg>
                                <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 10px; font-weight: 600; color: ${scoreColor};">
                                    ${Math.round(audit.seo_score || 0)}
                                </span>
                            </div>
                            <span style="font-size: 14px; font-weight: 600; color: ${scoreColor};">
                                ${Math.round(audit.seo_score || 0)}/100
                            </span>
                        </div>
                    </td>

                    <!-- Issues -->
                    <td style="padding: 16px 12px; text-align: center;">
                        ${totalIssues > 0 ? `
                        <div style="display: flex; gap: 4px; justify-content: center; flex-wrap: wrap;">
                            ${audit.critical_issues > 0 ? `<span style="padding: 2px 6px; background: #FEE2E2; color: #DC2626; border-radius: 12px; font-size: 10px; font-weight: 500;">${audit.critical_issues} C</span>` : ''}
                            ${audit.high_issues > 0 ? `<span style="padding: 2px 6px; background: #FEF3C7; color: #D97706; border-radius: 12px; font-size: 10px; font-weight: 500;">${audit.high_issues} H</span>` : ''}
                            ${audit.medium_issues > 0 ? `<span style="padding: 2px 6px; background: #E0E7FF; color: #3730A3; border-radius: 12px; font-size: 10px; font-weight: 500;">${audit.medium_issues} M</span>` : ''}
                        </div>
                        ` : '<span style="font-size: 12px; color: #10B981;">✅ None</span>'}
                    </td>

                    <!-- Actions -->
                    <td style="padding: 16px 12px; text-align: center;">
                        <div style="display: flex; align-items: center; gap: 6px; justify-content: center;">
                            ${audit.pdf_url ? `
                            <button onclick="window.solviaRouter.downloadAuditPDF('${audit.audit_id}')" style="padding: 4px 8px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 4px; font-size: 11px; cursor: pointer;" title="Download PDF">
                                📄
                            </button>
                            ` : ''}
                            <button onclick="window.solviaRouter.viewAuditDetails('${audit.audit_id}')" style="padding: 4px 8px; background: #EC6019; color: white; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;" title="View Details">
                                👁️
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        auditListHtml += `
                    </tbody>
                </table>
            </div>
        `;
        container.innerHTML = auditListHtml;
    }

    renderEmptyState() {
        const container = document.getElementById('auditHistoryContainer');
        if (!container) return;

        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                <div style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">No Audit History</div>
                <div style="font-size: 14px; color: #6B7280; margin-bottom: 24px;">Run your first audit to see detailed SEO analysis and recommendations</div>
            </div>
        `;
    }

    renderErrorState(errorMessage) {
        const container = document.getElementById('auditHistoryContainer');
        if (!container) return;

        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                <div style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">Failed to Load Audit History</div>
                <div style="font-size: 14px; color: #6B7280; margin-bottom: 24px;">${errorMessage}</div>
                <button onclick="router.refreshAuditHistory()" style="padding: 12px 24px; background: #EC6019; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer;">
                    🔄 Try Again
                </button>
            </div>
        `;
    }

    renderPagination() {
        const paginationContainer = document.getElementById('auditPagination');
        if (!paginationContainer) return;

        // Always show pagination if we have audits, even if only 1 page
        if (this.auditHistoryState.audits.length === 0) {
            paginationContainer.innerHTML = '';
            return;
        }

        const currentPage = this.auditHistoryState.currentPage;
        const totalPages = this.auditHistoryState.totalPages;

        let paginationHtml = `
            <div style="display: flex; justify-content: center; align-items: center; gap: 8px; padding: 16px;">
                <button ${currentPage <= 1 ? 'disabled' : ''} onclick="router.goToPage(${currentPage - 1})"
                        style="padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px; background: white; color: #374151; cursor: ${currentPage <= 1 ? 'not-allowed' : 'pointer'}; opacity: ${currentPage <= 1 ? '0.5' : '1'};">
                    ← Previous
                </button>

                <span style="padding: 8px 16px; font-size: 14px; color: #6B7280;">
                    Page ${currentPage} of ${totalPages}
                </span>

                <button ${currentPage >= totalPages ? 'disabled' : ''} onclick="router.goToPage(${currentPage + 1})"
                        style="padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px; background: white; color: #374151; cursor: ${currentPage >= totalPages ? 'not-allowed' : 'pointer'}; opacity: ${currentPage >= totalPages ? '0.5' : '1'};">
                    Next →
                </button>
            </div>
        `;

        paginationContainer.innerHTML = paginationHtml;
    }

    updateLoadingState(loading) {
        // Add loading indicator to controls if needed
        const refreshBtn = document.querySelector('button[onclick="router.refreshAuditHistory()"]');
        if (refreshBtn) {
            if (loading) {
                refreshBtn.innerHTML = '<span style="font-size: 16px;">⏳</span> Loading...';
                refreshBtn.disabled = true;
            } else {
                refreshBtn.innerHTML = '<span style="font-size: 16px;">🔄</span> Refresh';
                refreshBtn.disabled = false;
            }
        }
    }

    // Event handlers
    handleFilterChange(filterValue) {
        this.auditHistoryState.filter = filterValue;
        this.auditHistoryState.currentPage = 1;
        this.loadAuditHistoryData(1, this.auditHistoryState.pageSize, this.auditHistoryState.sortBy, this.auditHistoryState.sortOrder, filterValue);
    }

    handleSortChange(sortValue) {
        const [sortBy, sortOrder] = sortValue.split('_');
        this.auditHistoryState.sortBy = sortBy;
        this.auditHistoryState.sortOrder = sortOrder;
        this.auditHistoryState.currentPage = 1;
        this.loadAuditHistoryData(1, this.auditHistoryState.pageSize, sortBy, sortOrder, this.auditHistoryState.filter);
    }

    refreshAuditHistory() {
        this.loadAuditHistoryData(
            this.auditHistoryState.currentPage,
            this.auditHistoryState.pageSize,
            this.auditHistoryState.sortBy,
            this.auditHistoryState.sortOrder,
            this.auditHistoryState.filter
        );
    }

    goToPage(page) {
        if (page < 1 || page > this.auditHistoryState.totalPages) return;
        this.auditHistoryState.currentPage = page;
        this.loadAuditHistoryData(page, this.auditHistoryState.pageSize, this.auditHistoryState.sortBy, this.auditHistoryState.sortOrder, this.auditHistoryState.filter);
    }

    async triggerNewAudit() {
        // Navigate to dashboard and trigger audit
        this.navigateTo('dashboard');
        // Small delay to ensure dashboard is loaded
        setTimeout(() => {
            const newAuditBtn = document.querySelector('button[onclick="triggerAudit()"]');
            if (newAuditBtn) {
                newAuditBtn.click();
            }
        }, 500);
    }

    async downloadAuditPDF(auditId) {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch(`/agent/report/${auditId}/pdf`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `seo_audit_${auditId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                console.error('Failed to download PDF');
            }
        } catch (error) {
            console.error('Error downloading PDF:', error);
        }
    }

    async viewAuditDetails(auditId) {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch(`/agent/report/${auditId}/json`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const auditData = await response.json();
                this.showAuditDetailsModal(auditData, auditId);
            } else {
                console.error('Failed to load audit details');
            }
        } catch (error) {
            console.error('Error loading audit details:', error);
        }
    }

    showAuditDetailsModal(auditData, auditId) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: flex; align-items: center; justify-content: center; padding: 20px;
        `;

        const modalContent = `
            <div style="background: white; border-radius: 12px; max-width: 800px; width: 100%; max-height: 80vh; overflow-y: auto; padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #E5E7EB;">
                    <h2 style="font-size: 24px; font-weight: 600; color: #1F2937;">Audit Details</h2>
                    <button onclick="this.closest('.modal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #6B7280;">×</button>
                </div>

                <div style="space-y: 16px;">
                    <div style="background: #F9FAFB; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                        <h3 style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">SEO Score: ${Math.round(auditData.seo_score || 0)}/100</h3>
                        <div style="background: #E5E7EB; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="background: #EC6019; height: 100%; width: ${Math.round(auditData.seo_score || 0)}%; transition: width 0.3s ease;"></div>
                        </div>
                    </div>

                    ${auditData.issues && auditData.issues.length > 0 ? `
                    <div>
                        <h3 style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 12px;">Issues Found</h3>
                        <div style="space-y: 8px;">
                            ${auditData.issues.slice(0, 5).map(issue => `
                                <div style="padding: 12px; border: 1px solid #E5E7EB; border-radius: 8px; margin-bottom: 8px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <h4 style="font-size: 14px; font-weight: 600; color: #1F2937;">${issue.title || 'Issue'}</h4>
                                        <span style="padding: 2px 8px; background: ${issue.severity === 'critical' ? '#FEE2E2' : issue.severity === 'high' ? '#FEF3C7' : '#E0E7FF'};
                                                     color: ${issue.severity === 'critical' ? '#DC2626' : issue.severity === 'high' ? '#D97706' : '#3730A3'};
                                                     border-radius: 12px; font-size: 11px; font-weight: 500; text-transform: capitalize;">
                                            ${issue.severity || 'medium'}
                                        </span>
                                    </div>
                                    <p style="font-size: 13px; color: #6B7280;">${issue.description || 'No description available'}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : '<p style="color: #10B981;">No significant issues found!</p>'}

                    <div style="display: flex; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #E5E7EB;">
                        <button onclick="router.downloadAuditPDF('${auditId}')" style="flex: 1; padding: 12px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer;">
                            📄 Download PDF
                        </button>
                        <button onclick="this.closest('.modal').remove()" style="flex: 1; padding: 12px; background: #EC6019; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer;">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;

        modal.className = 'modal';
        modal.innerHTML = modalContent;
        document.body.appendChild(modal);

        // Close modal on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    async loadSettings() {
        console.log('⚙️ Loading Settings content...');

        const settingsHtml = `
            <div style="padding: 32px;">
                <div style="margin-bottom: 40px;">
                    <h1 style="font-size: 32px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">Settings</h1>
                    <p style="font-size: 14px; color: #6B7280;">Manage your Solvia preferences and configuration</p>
                </div>

                <div style="background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); margin-bottom: 24px;">
                    <h2 style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 8px;">Website Configuration</h2>
                    <p style="font-size: 14px; color: #6B7280; margin-bottom: 24px;">Select the Google Search Console property you want Solvia to analyze</p>

                    <!-- Card Selection Grid -->
                    <div id="websiteCards" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 20px;">
                        <!-- Loading state -->
                        <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                            <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #F3F4F6; border-top-color: #EC6019; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            <p style="color: #6B7280; margin-top: 16px;">Loading your websites...</p>
                        </div>
                    </div>

                    <!-- Save Button -->
                    <button id="saveWebsiteBtn" onclick="saveWebsiteSelection()" style="background: #EC6019; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; opacity: 0.5; cursor: not-allowed;" disabled>
                        Save Changes
                    </button>
                </div>

                <!-- CSS for animations -->
                <style>
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }

                    .website-card {
                        background: white;
                        border: 2px solid #E5E7EB;
                        border-radius: 12px;
                        padding: 20px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        position: relative;
                        overflow: hidden;
                    }

                    .website-card:hover {
                        border-color: #EC6019;
                        box-shadow: 0 4px 12px rgba(236, 96, 25, 0.1);
                        transform: translateY(-2px);
                    }

                    .website-card.selected {
                        border-color: #EC6019;
                        background: linear-gradient(135deg, rgba(236, 96, 25, 0.05) 0%, rgba(236, 96, 25, 0.02) 100%);
                        box-shadow: 0 4px 16px rgba(236, 96, 25, 0.15);
                    }

                    .website-card.selected::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 3px;
                        background: linear-gradient(90deg, #EC6019, #FF8040);
                    }

                    .card-check {
                        position: absolute;
                        top: 12px;
                        right: 12px;
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        background: #EC6019;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        opacity: 0;
                        transform: scale(0);
                        transition: all 0.3s ease;
                    }

                    .website-card.selected .card-check {
                        opacity: 1;
                        transform: scale(1);
                    }

                    .card-icon {
                        width: 40px;
                        height: 40px;
                        background: linear-gradient(135deg, #EC6019 0%, #FF8040 100%);
                        border-radius: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-bottom: 16px;
                    }

                    .card-url {
                        font-size: 15px;
                        font-weight: 600;
                        color: #1F2937;
                        margin-bottom: 8px;
                        word-break: break-word;
                    }

                    .card-type {
                        font-size: 13px;
                        color: #6B7280;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                </style>

                <div style="background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
                    <h2 style="font-size: 18px; font-weight: 600; color: #1F2937; margin-bottom: 20px;">Account Information</h2>
                    <div>
                        <label style="display: block; font-size: 14px; font-weight: 500; color: #374151; margin-bottom: 8px;">Email Address</label>
                        <div style="padding: 12px 16px; background: #F9FAFB; border-radius: 8px; font-size: 14px; color: #1F2937;" id="userEmailDisplay">
                            Loading...
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.showContent(settingsHtml);

        // Load GSC properties
        this.loadGSCProperties();

        // Load user email
        this.loadUserEmail();
    }

    async loadGSCProperties() {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');

            // First get the selected website
            const selectedResponse = await fetch('/auth/gsc/selected-website', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            let currentSelected = null;
            if (selectedResponse.ok) {
                const selectedData = await selectedResponse.json();
                currentSelected = selectedData.selected_website;
                console.log('📊 SPA: Current selected website:', currentSelected);
            }

            // Then get all properties
            const response = await fetch('/auth/gsc/properties', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const cardsContainer = document.getElementById('websiteCards');
            if (response.ok && cardsContainer) {
                const data = await response.json();
                cardsContainer.innerHTML = ''; // Clear loading state

                if (data.properties && data.properties.length > 0) {
                    // Store selected website globally for save function
                    window.selectedWebsite = currentSelected;

                    data.properties.forEach(prop => {
                        // Handle both string and object format
                        const propUrl = typeof prop === 'string' ? prop : (prop.siteUrl || prop.url || prop);
                        const isSelected = currentSelected && (propUrl === currentSelected || propUrl === data.selected_website);

                        // Clean URL for display
                        const displayUrl = propUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
                        const isSecure = propUrl.startsWith('https://');

                        // Create card element
                        const card = document.createElement('div');
                        card.className = `website-card ${isSelected ? 'selected' : ''}`;
                        card.dataset.url = propUrl;

                        card.innerHTML = `
                            <!-- Check mark for selected state -->
                            <div class="card-check">
                                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                    <path d="M11.6667 3.5L5.25 9.91667L2.33333 7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>

                            <!-- Website Icon -->
                            <div class="card-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M2 17L12 22L22 17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M2 12L12 17L22 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>

                            <!-- Website URL -->
                            <div class="card-url">${displayUrl}</div>

                            <!-- Website Type/Protocol -->
                            <div class="card-type">
                                ${isSecure ?
                                    '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M10.5 6.41667H3.5C2.85567 6.41667 2.33333 6.939 2.33333 7.58333V11.0833C2.33333 11.7277 2.85567 12.25 3.5 12.25H10.5C11.1443 12.25 11.6667 11.7277 11.6667 11.0833V7.58333C11.6667 6.939 11.1443 6.41667 10.5 6.41667Z" stroke="#10B981" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4.66667 6.41667V4.08333C4.66667 3.33189 4.96548 2.61122 5.49684 2.07986C6.02821 1.5485 6.74888 1.25 7.5 1.25C8.25112 1.25 8.97179 1.5485 9.50316 2.07986C10.0345 2.61122 10.3333 3.33189 10.3333 4.08333V6.41667" stroke="#10B981" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' :
                                    '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="6" stroke="#9CA3AF" stroke-width="1.5"/><path d="M7 4V7L9 9" stroke="#9CA3AF" stroke-width="1.5" stroke-linecap="round"/></svg>'
                                }
                                <span>${isSecure ? 'Secure (HTTPS)' : 'Standard (HTTP)'}</span>
                            </div>
                        `;

                        // Add click handler
                        card.addEventListener('click', function() {
                            // Remove selected from all cards
                            document.querySelectorAll('.website-card').forEach(c => {
                                c.classList.remove('selected');
                            });

                            // Add selected to this card
                            this.classList.add('selected');

                            // Store selected website
                            window.selectedWebsite = propUrl;

                            // Enable save button if selection changed
                            const saveBtn = document.getElementById('saveWebsiteBtn');
                            if (saveBtn) {
                                if (propUrl !== currentSelected) {
                                    saveBtn.disabled = false;
                                    saveBtn.style.opacity = '1';
                                    saveBtn.style.cursor = 'pointer';
                                } else {
                                    saveBtn.disabled = true;
                                    saveBtn.style.opacity = '0.5';
                                    saveBtn.style.cursor = 'not-allowed';
                                }
                            }
                        });

                        cardsContainer.appendChild(card);
                    });
                } else {
                    cardsContainer.innerHTML = `
                        <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style="margin: 0 auto 16px;">
                                <circle cx="32" cy="32" r="32" fill="#F3F4F6"/>
                                <path d="M32 22V34" stroke="#9CA3AF" stroke-width="2" stroke-linecap="round"/>
                                <circle cx="32" cy="42" r="1" fill="#9CA3AF"/>
                            </svg>
                            <p style="color: #6B7280; font-size: 16px; font-weight: 500;">No websites found</p>
                            <p style="color: #9CA3AF; font-size: 14px; margin-top: 8px;">Please connect your Google Search Console account first</p>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('Error loading GSC properties:', error);
            const cardsContainer = document.getElementById('websiteCards');
            if (cardsContainer) {
                cardsContainer.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style="margin: 0 auto 16px;">
                            <circle cx="32" cy="32" r="32" fill="#FEE2E2"/>
                            <path d="M22 22L42 42M42 22L22 42" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                        <p style="color: #EF4444; font-size: 16px; font-weight: 500;">Failed to load websites</p>
                        <p style="color: #9CA3AF; font-size: 14px; margin-top: 8px;">Please try refreshing the page</p>
                    </div>
                `;
            }
        }
    }

    async loadUserEmail() {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch('/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                const emailEl = document.getElementById('userEmailDisplay');
                if (emailEl) {
                    emailEl.textContent = data.email || 'Not available';
                }
            }
        } catch (error) {
            console.error('Error loading user email:', error);
        }
    }

    // Load user info
    async loadUserInfo() {
        // Prevent multiple simultaneous auth checks
        if (this.isAuthChecking) {
            console.log('🔒 SPA: Auth check already in progress, skipping...');
            return;
        }

        // If we already had an auth error, don't keep trying
        if (this.hasAuthError) {
            console.log('🔒 SPA: Previous auth error detected, skipping check...');
            return;
        }

        this.isAuthChecking = true;

        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            if (!token) {
                console.log('⚠️ SPA: No token found, redirecting to login...');
                this.hasAuthError = true;
                window.location.href = '/login';
                return;
            }

            const response = await fetch('/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                const email = data.email;

                // Update sidebar user info
                const userEmailEl = document.getElementById('userEmail');
                const userAvatarEl = document.getElementById('userAvatar');
                const userEmailDisplayEl = document.getElementById('userEmailDisplay');

                if (userEmailEl) {
                    // TOOLTIP SOLUTION: Show full username without ellipsis
                    const emailParts = email.split('@');
                    const username = emailParts[0];

                    // Always show full username without truncation
                    const displayText = username;

                    // Set the display text and tooltip data
                    userEmailEl.textContent = displayText;
                    userEmailEl.setAttribute('data-full-email', email);
                    userEmailEl.setAttribute('title', email); // Fallback tooltip
                    userEmailEl.classList.add('email-tooltip'); // Add tooltip class

                    // Force display properties for tooltip with stronger CSS override
                    userEmailEl.style.position = 'relative';
                    userEmailEl.style.cursor = 'pointer';
                    userEmailEl.style.display = 'block';
                    userEmailEl.style.minHeight = '20px';
                    userEmailEl.style.overflow = 'visible';
                    userEmailEl.style.zIndex = '1';

                    // Force parent containers to allow overflow
                    const navItemText = userEmailEl.closest('.nav-item-text');
                    if (navItemText) {
                        navItemText.style.overflow = 'visible';
                        navItemText.style.position = 'relative';
                    }

                    const navItem = userEmailEl.closest('.nav-item');
                    if (navItem) {
                        navItem.style.overflow = 'visible';
                        navItem.style.position = 'relative';
                    }

                    // Enhanced click and hover listeners for debugging
                    userEmailEl.addEventListener('click', function() {
                        console.log('📧 Email clicked! Classes:', this.className);
                        console.log('📧 Email clicked! Data:', this.getAttribute('data-full-email'));
                        console.log('📧 Computed CSS position:', window.getComputedStyle(this).position);
                        console.log('📧 Computed CSS overflow:', window.getComputedStyle(this).overflow);
                        console.log('📧 Computed CSS z-index:', window.getComputedStyle(this).zIndex);
                        alert('Tooltip test - Data: ' + this.getAttribute('data-full-email') + '\nClick again and try hovering!');
                    });

                    userEmailEl.addEventListener('mouseenter', function() {
                        console.log('🐭 Mouse ENTERED userEmail element');
                        console.log('🐭 Element has data-full-email:', this.getAttribute('data-full-email'));
                        console.log('🐭 Element has class email-tooltip:', this.classList.contains('email-tooltip'));
                    });

                    userEmailEl.addEventListener('mouseleave', function() {
                        console.log('🐭 Mouse LEFT userEmail element');
                    });

                    console.log('📧 SPA: Email tooltip set:', email, '→ Display:', displayText);
                    console.log('📧 SPA: Tooltip classes:', userEmailEl.className);
                    console.log('📧 SPA: Tooltip data-full-email:', userEmailEl.getAttribute('data-full-email'));
                    console.log('📧 SPA: Element final styles - position:', userEmailEl.style.position, 'overflow:', userEmailEl.style.overflow);

                    // Final validation
                    setTimeout(() => {
                        const hasTooltipClass = userEmailEl.classList.contains('email-tooltip');
                        const hasDataAttribute = userEmailEl.getAttribute('data-full-email') === email;
                        const hasCorrectPosition = window.getComputedStyle(userEmailEl).position === 'relative';

                        console.log('✅ VALIDATION - Has tooltip class:', hasTooltipClass);
                        console.log('✅ VALIDATION - Has data attribute:', hasDataAttribute);
                        console.log('✅ VALIDATION - Has relative position:', hasCorrectPosition);

                        if (hasTooltipClass && hasDataAttribute && hasCorrectPosition) {
                            console.log('🎉 TOOLTIP SETUP COMPLETE - Ready for hover test!');
                        } else {
                            console.log('❌ TOOLTIP SETUP INCOMPLETE - Check CSS and data attributes');
                        }
                    }, 100);
                }
                if (userEmailDisplayEl) userEmailDisplayEl.textContent = email;

                if (userAvatarEl) {
                    const initial = email ? email[0].toUpperCase() : 'U';
                    userAvatarEl.textContent = initial;
                }

                console.log('✅ SPA: User info loaded successfully');
                this.hasAuthError = false; // Reset error flag on success
            } else {
                console.log(`⚠️ SPA: Auth check failed with status ${response.status}`);
                // Only redirect if this is a clear auth failure
                if (response.status === 401 || response.status === 403) {
                    this.hasAuthError = true;
                    window.location.href = '/login';
                }
            }
        } catch (error) {
            console.error('Error loading user info:', error);
            // Don't redirect on network errors - user might be offline temporarily
            console.log('⚠️ SPA: Network error during auth check, not redirecting');
        } finally {
            this.isAuthChecking = false;
        }
    }

    // Load dashboard data using existing dashboard_new.js functionality
    async loadDashboardData() {
        console.log('📊 Loading dashboard data...');

        try {
            // Load user website info
            await this.loadUserWebsite();

            // Load dashboard metrics
            await this.loadDashboardMetrics();

            // Load current issues
            await this.loadCurrentIssues();

            console.log('✅ Dashboard data loaded successfully');
        } catch (error) {
            console.error('❌ Error loading dashboard data:', error);
        }
    }

    // Load user website information
    async loadUserWebsite() {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');

            // First get the user's name from /auth/me
            const userResponse = await fetch('/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            let userName = 'there';
            if (userResponse.ok) {
                const userData = await userResponse.json();
                // Extract name from email or use the name field
                if (userData.name) {
                    userName = userData.name.split(' ')[0]; // Get first name
                } else if (userData.email) {
                    userName = userData.email.split('@')[0]; // Use email prefix as name
                    // Capitalize first letter
                    userName = userName.charAt(0).toUpperCase() + userName.slice(1);
                }
            }

            // Then get the selected website
            const response = await fetch('/auth/gsc/selected-website', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('📊 SPA: Website data received:', data);

                const userNameEl = document.getElementById('userName');
                const websiteUrlEl = document.getElementById('websiteUrl');

                if (userNameEl && websiteUrlEl) {
                    userNameEl.textContent = userName;
                    console.log('✅ SPA: Updated username to:', userName);

                    // Clean up the website URL for display - handle both website_url and selected_website
                    let websiteDisplay = data.selected_website || data.website_url || 'your website';
                    // Remove protocol for cleaner display
                    websiteDisplay = websiteDisplay.replace(/^https?:\/\//, '').replace(/\/$/, '');
                    websiteUrlEl.textContent = websiteDisplay;
                    console.log('✅ SPA: Updated website to:', websiteDisplay);

                    // Hide skeleton and show real header
                    const headerSkeleton = document.getElementById('headerSkeleton');
                    const realHeader = document.getElementById('realHeader');
                    if (headerSkeleton) headerSkeleton.style.display = 'none';
                    if (realHeader) realHeader.style.display = 'block';
                }
            } else {
                console.log('❌ SPA: Failed to load website data, status:', response.status);
                // Still update the username even if website fails
                const userNameEl = document.getElementById('userName');
                const websiteUrlEl = document.getElementById('websiteUrl');

                if (userNameEl) userNameEl.textContent = userName;
                if (websiteUrlEl) websiteUrlEl.textContent = 'your website';

                // Hide skeleton and show real header even on error
                const headerSkeleton = document.getElementById('headerSkeleton');
                const realHeader = document.getElementById('realHeader');
                if (headerSkeleton) headerSkeleton.style.display = 'none';
                if (realHeader) realHeader.style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading user website:', error);
            // Show default values on error
            const userNameEl = document.getElementById('userName');
            const websiteUrlEl = document.getElementById('websiteUrl');

            if (userNameEl) userNameEl.textContent = 'there';
            if (websiteUrlEl) websiteUrlEl.textContent = 'your website';

            // Hide skeleton and show real header even on error
            const headerSkeleton = document.getElementById('headerSkeleton');
            const realHeader = document.getElementById('realHeader');
            if (headerSkeleton) headerSkeleton.style.display = 'none';
            if (realHeader) realHeader.style.display = 'block';
        }
    }

    // Load dashboard metrics
    async loadDashboardMetrics() {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch('/auth/gsc/metrics?days=30', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('📊 SPA: Metrics data received:', data);

                // Update metrics using correct IDs
                const seoScoreEl = document.getElementById('seoScore');
                const organicTrafficEl = document.getElementById('organicTraffic');
                const avgPositionEl = document.getElementById('avgPosition');
                const backlinksEl = document.getElementById('backlinks');

                // Update change elements
                const seoChangeEl = document.getElementById('seoChange');
                const trafficChangeEl = document.getElementById('trafficChange');
                const positionChangeEl = document.getElementById('positionChange');
                const backlinksChangeEl = document.getElementById('backlinksChange');

                // Update values
                if (seoScoreEl) seoScoreEl.textContent = data.seo_score ? `${Math.round(data.seo_score)}/100` : '25/100';
                if (organicTrafficEl) organicTrafficEl.textContent = data.clicks || '0';
                if (avgPositionEl) avgPositionEl.textContent = data.avg_position ? Math.round(data.avg_position * 10) / 10 : '-';
                if (backlinksEl) backlinksEl.textContent = data.impressions ? Math.round(data.impressions / 10) : '0';

                // Update change text with dynamic colors and realistic data
                if (seoChangeEl) {
                    const score = data.seo_score || 25;
                    if (score >= 70) {
                        seoChangeEl.textContent = 'Good SEO performance';
                        seoChangeEl.className = 'metric-change';
                    } else if (score <= 30) {
                        seoChangeEl.textContent = 'Needs improvement';
                        seoChangeEl.className = 'metric-change negative';
                    } else {
                        seoChangeEl.textContent = 'Based on real GSC data';
                        seoChangeEl.className = 'metric-change neutral';
                    }
                }

                if (trafficChangeEl) {
                    const clicks = data.clicks || 0;
                    if (clicks > 100) {
                        trafficChangeEl.textContent = 'Strong organic traffic';
                        trafficChangeEl.className = 'metric-change';
                    } else if (clicks < 10) {
                        trafficChangeEl.textContent = 'Low traffic volume';
                        trafficChangeEl.className = 'metric-change negative';
                    } else {
                        trafficChangeEl.textContent = 'Clicks from last 30 days';
                        trafficChangeEl.className = 'metric-change neutral';
                    }
                }

                if (positionChangeEl) {
                    const position = data.avg_position || 0;
                    if (position > 0 && position <= 5) {
                        positionChangeEl.textContent = 'Excellent rankings';
                        positionChangeEl.className = 'metric-change';
                    } else if (position > 10) {
                        positionChangeEl.textContent = 'Ranking needs work';
                        positionChangeEl.className = 'metric-change negative';
                    } else {
                        positionChangeEl.textContent = 'Search ranking position';
                        positionChangeEl.className = 'metric-change neutral';
                    }
                }

                if (backlinksChangeEl) {
                    const impressions = data.impressions || 0;
                    if (impressions > 1000) {
                        backlinksChangeEl.textContent = 'Good search visibility';
                        backlinksChangeEl.className = 'metric-change';
                    } else if (impressions < 100) {
                        backlinksChangeEl.textContent = 'Limited visibility';
                        backlinksChangeEl.className = 'metric-change negative';
                    } else {
                        backlinksChangeEl.textContent = 'External sites linking to you';
                        backlinksChangeEl.className = 'metric-change neutral';
                    }
                }

                // Show real metrics and hide skeleton
                const metricsSkeletonEl = document.getElementById('metricsSkeleton');
                const realMetricsEl = document.getElementById('realMetrics');

                if (metricsSkeletonEl) metricsSkeletonEl.classList.add('hidden');
                if (realMetricsEl) realMetricsEl.classList.remove('hidden');

                console.log('✅ SPA: Dashboard metrics updated successfully');
            }
        } catch (error) {
            console.error('❌ SPA: Error loading dashboard metrics:', error);
        }
    }

    // Load current issues
    async loadCurrentIssues() {
        // Get skeleton and real issues elements
        const issuesSkeletonEl = document.getElementById('issuesSkeleton');
        const realIssuesEl = document.getElementById('realIssues');

        // Skeleton should already be visible from HTML, ensure real issues hidden
        if (realIssuesEl) realIssuesEl.classList.add('hidden');

        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch('/agent/current-issues', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('📊 SPA: Issues data received:', data);

                const issuesContainer = document.getElementById('issuesContainer');

                if (issuesContainer && data.issues && data.issues.length > 0) {
                    // Replace with proper issue-card structure (1:1 with original dashboard)
                    issuesContainer.innerHTML = data.issues.map((issue, index) => {
                        const severityClass = this.getSeverityClass(issue.severity);
                        const iconSVG = this.getSeverityIcon(issue.severity);
                        const cardId = `issue-${index}`;

                        return `
                            <div class="issue-card ${severityClass}">
                                <div class="issue-header">
                                    ${iconSVG}
                                    <div class="issue-title">${issue.title}</div>
                                </div>
                                <div class="issue-description">
                                    <div class="issue-description-short" id="short-${cardId}">
                                        <div class="issue-description-text">${issue.description}</div>
                                    </div>
                                    <div class="issue-description-full" id="full-${cardId}">
                                        <div class="issue-description-text">
                                            <strong>Detailed Analysis:</strong><br>
                                            ${issue.detailed_description || issue.description}
                                            ${issue.impact ? `<br><br><strong>Business Impact:</strong><br>${issue.impact}` : ''}
                                        </div>
                                    </div>
                                    <button class="issue-expand-btn" onclick="toggleIssueDescription('${cardId}')">
                                        Show more details →
                                    </button>
                                </div>
                                <div class="issue-fix">
                                    <strong>Fix:</strong> ${issue.recommendation || 'Review and address this issue to improve your SEO score.'}
                                </div>
                            </div>
                        `;
                    }).join('');
                    // Hide skeleton and show real issues
                    if (issuesSkeletonEl) issuesSkeletonEl.classList.add('hidden');
                    if (realIssuesEl) realIssuesEl.classList.remove('hidden');

                    console.log('✅ SPA: Issues loaded and displayed');
                } else {
                    // Show no issues message
                    if (issuesContainer) {
                        issuesContainer.innerHTML = `
                            <div class="no-issues-message">
                                <span class="emoji">🎉</span>
                                <h3>All Good!</h3>
                                <p>No critical issues found. Your website is performing well! Run a new audit to get the latest insights.</p>
                                <button class="action-btn" onclick="runNewAudit()">Run New Audit</button>
                            </div>
                        `;
                    }
                    console.log('✅ SPA: No issues found, showing empty state');
                }
            }
        } catch (error) {
            console.error('Error loading current issues:', error);
        }
    }

    // Get severity class for issues (matches original dashboard)
    getSeverityClass(severity) {
        switch (severity?.toLowerCase()) {
            case 'high':
            case 'critical': return 'critical';
            case 'medium':
            case 'warning': return 'medium';
            case 'low': return 'warning';
            default: return 'medium';
        }
    }

    // Get severity icon SVG (matches original dashboard)
    getSeverityIcon(severity) {
        switch (severity?.toLowerCase()) {
            case 'high':
            case 'critical':
                return `<svg class="issue-icon critical" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>`;
            case 'medium':
            case 'warning':
                return `<svg class="issue-icon warning" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>`;
            default:
                return `<svg class="issue-icon warning" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                </svg>`;
        }
    }

    // Load chat history
    async loadChatHistory() {
        try {
            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch('/auth/chat/history', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const chatSkeleton = document.getElementById('chatSkeleton');
            const welcomeMessage = document.getElementById('welcomeMessage');
            const chatMessages = document.getElementById('chatMessages');

            if (response.ok) {
                const data = await response.json();
                console.log('📜 SPA: Chat history data received:', data);

                // Hide skeleton
                if (chatSkeleton) chatSkeleton.style.display = 'none';

                // Check if we have actual chat messages
                if (data.messages && data.messages.length > 0) {
                    console.log(`📜 SPA: Loading ${data.messages.length} chat messages`);

                    // Hide welcome message since we have history
                    if (welcomeMessage) {
                        welcomeMessage.style.display = 'none';
                        welcomeMessage.classList.add('hidden');
                    }

                    // Render chat history
                    const historyHtml = data.messages.map(msg => {
                        const isUser = msg.message_type === 'user' || msg.sender_name !== 'Solvia';
                        let messageContent = msg.message_content || msg.content || '';

                        // Apply audit formatting if this is an AI message containing audit content
                        if (!isUser && (messageContent.includes('audit ID') || messageContent.includes('SEO score') || messageContent.includes('I\'ve started a comprehensive SEO audit'))) {
                            messageContent = formatAuditResponse(messageContent);
                        }

                        messageContent = convertMarkdownToHTML(messageContent);

                        if (isUser) {
                            return `
                                <div class="chat-message user">
                                    <div class="message-content user">
                                        <div class="message-text">${messageContent}</div>
                                    </div>
                                    <div class="message-avatar user">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="#EC6019">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"></path>
                                        </svg>
                                    </div>
                                </div>
                            `;
                        } else {
                            return `
                                <div class="chat-message ai">
                                    <div class="message-avatar ai">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                                        </svg>
                                    </div>
                                    <div class="message-content ai">
                                        <div class="message-text">${messageContent}</div>
                                    </div>
                                </div>
                            `;
                        }
                    }).join('');

                    // Insert chat history into messages container
                    if (chatMessages) {
                        chatMessages.innerHTML = historyHtml;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        console.log('✅ SPA: Chat history displayed successfully');
                    }
                } else {
                    console.log('📜 SPA: No chat history found, showing welcome message');
                    // Show welcome message if no history
                    if (welcomeMessage) {
                        welcomeMessage.style.display = 'flex';
                        welcomeMessage.classList.remove('hidden');
                    }
                }

                console.log('✅ SPA: Chat loaded successfully');
            } else {
                console.log('❌ SPA: Failed to load chat history, status:', response.status);
                // On error, still hide skeleton and show welcome
                if (chatSkeleton) chatSkeleton.style.display = 'none';
                if (welcomeMessage) {
                    welcomeMessage.style.display = 'flex';
                    welcomeMessage.classList.remove('hidden');
                }
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            // Hide skeleton and show welcome on error
            const chatSkeleton = document.getElementById('chatSkeleton');
            const welcomeMessage = document.getElementById('welcomeMessage');
            if (chatSkeleton) chatSkeleton.style.display = 'none';
            if (welcomeMessage) {
                welcomeMessage.style.display = 'flex';
                welcomeMessage.classList.remove('hidden');
            }
        }
    }
}

// Global Functions
function toggleSidebar() {
    console.log('🔧 SPA: toggleSidebar function called!');

    const sidebar = document.getElementById('sidebar');
    const logoImg = document.getElementById('logo-img');

    if (!sidebar || !logoImg) {
        console.error('❌ Missing elements - sidebar:', !!sidebar, 'logoImg:', !!logoImg);
        return;
    }

    const isExpanding = !sidebar.classList.contains('expanded');
    console.log('🔄 Toggle action - isExpanding:', isExpanding);

    sidebar.classList.toggle('expanded');

    // Switch logo based on sidebar state
    if (isExpanding) {
        console.log('🔄 Expanding: Setting logo to logo_v2.png');
        logoImg.src = '/static/logo_v2.png?' + Date.now();
    } else {
        console.log('🔄 Collapsing: Setting logo to orange-svg-emblem-40px.svg');
        logoImg.src = '/static/orange-svg-emblem-40px.svg?' + Date.now();
    }

    console.log('🔄 Logo src after toggle:', logoImg.src);
}

async function logout() {
    try {
        const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
        if (token) {
            await fetch('/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
        }

        // Clear tokens
        localStorage.removeItem('auth_token');
        localStorage.removeItem('token');
        localStorage.removeItem('cachedMetrics');
        localStorage.removeItem('cachedIssues');

        // Redirect to login
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        // Still redirect to login on error
        window.location.href = '/login';
    }
}

// Save website selection in Settings
async function saveWebsiteSelection() {
    try {
        const selectedWebsite = window.selectedWebsite;
        if (!selectedWebsite) {
            alert('Please select a website');
            return;
        }

        const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
        const response = await fetch('/auth/gsc/select-property', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ website_url: selectedWebsite })
        });

        if (response.ok) {
            alert('Website selection saved successfully!');
            // Clear cached data
            localStorage.removeItem('cachedMetrics');
            localStorage.removeItem('cachedIssues');
            // Navigate to dashboard
            window.solviaRouter.navigateTo('dashboard');
        } else {
            alert('Failed to save website selection');
        }
    } catch (error) {
        console.error('Error saving website selection:', error);
        alert('Error saving website selection');
    }
}

// Toggle issue description visibility
function toggleIssueDescription(cardId) {
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
}

// Run new audit
async function runNewAudit() {
    console.log('🚀 Starting new SEO audit...');

    // Get audit button and disable it
    const auditBtn = document.getElementById('auditBtn');
    if (auditBtn) {
        auditBtn.disabled = true;
        auditBtn.textContent = 'Starting audit...';
    }

    // Send chat message to indicate audit started
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer && window.solviaRouter && window.solviaRouter.sendChatMessage) {
        // Add user message to show audit was triggered
        const userMessageHtml = `
            <div class="chat-message user">
                <div class="message-content user">
                    <div class="message-text">🚀 Run a comprehensive SEO audit</div>
                    <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
            </div>`;
        chatContainer.innerHTML += userMessageHtml;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Start the audit
    await triggerAudit();
}

// Enhanced progress interface helper functions
function minimizeAuditProgress() {
    const overlay = document.getElementById('auditProgressOverlay');
    const details = document.getElementById('auditProgressDetails');
    const btn = document.getElementById('minimizeAuditBtn');

    if (overlay && details && btn) {
        const isCollapsed = details.style.display === 'none';

        if (isCollapsed) {
            // Expand: show details, change to minus icon
            details.style.display = 'block';
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5"/></svg>';
            btn.title = 'Minimize';
            console.log('🚀 ENHANCED: Progress details expanded');
        } else {
            // Collapse: hide details, change to plus icon
            details.style.display = 'none';
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>';
            btn.title = 'Expand';
            console.log('🚀 ENHANCED: Progress details collapsed');
        }
    }
}

function runAuditInBackground() {
    console.log('🔥 DEBUG: runAuditInBackground() function called!');

    const overlay = document.getElementById('auditProgressOverlay');
    console.log('🔥 DEBUG: overlay found:', !!overlay, 'display:', overlay ? overlay.style.display : 'N/A');

    // Check if already in background mode
    const existingIndicator = document.getElementById('auditBackgroundIndicator');
    console.log('🔥 DEBUG: existing indicator:', !!existingIndicator);

    if (existingIndicator) {
        console.log('🚀 ENHANCED: Already in background mode');
        return;
    }

    if (overlay) {
        console.log('🚀 ENHANCED: Moving audit to background...');

        // Immediately hide overlay with animation
        overlay.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        overlay.style.transform = 'translateY(-100%)';

        // Hide completely after animation
        setTimeout(() => {
            if (overlay.style.transform === 'translateY(-100%)') {
                overlay.style.display = 'none';
                console.log('🚀 ENHANCED: Progress overlay hidden');
            }
        }, 450);

        // Create background indicator immediately
        const indicator = document.createElement('div');
        indicator.id = 'auditBackgroundIndicator';
        indicator.style.cssText = `
            position: fixed !important;
            top: 20px !important;
            left: 20px !important;
            z-index: 60000 !important;
            background: linear-gradient(135deg, #f97316, #ea580c) !important;
            color: white !important;
            padding: 10px 16px !important;
            border-radius: 25px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            box-shadow: 0 6px 20px rgba(249, 115, 22, 0.4) !important;
            transition: all 0.3s ease !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            border: none !important;
            outline: none !important;
        `;
        indicator.innerHTML = '🔍 <span>SEO Audit Running...</span>';

        // Click to restore full progress view
        indicator.onclick = () => {
            console.log('🚀 ENHANCED: Restoring full progress view...');
            overlay.style.display = 'block';
            overlay.style.transform = 'translateY(0)';
            indicator.remove();
        };

        // Add hover effect
        indicator.onmouseenter = () => {
            indicator.style.transform = 'scale(1.05)';
            indicator.style.boxShadow = '0 8px 25px rgba(249, 115, 22, 0.5)';
        };
        indicator.onmouseleave = () => {
            indicator.style.transform = 'scale(1)';
            indicator.style.boxShadow = '0 6px 20px rgba(249, 115, 22, 0.4)';
        };

        document.body.appendChild(indicator);
        console.log('🚀 ENHANCED: Background indicator created');
    }
}

function hideSuccessToast() {
    const toast = document.getElementById('auditSuccessToast');
    if (toast) {
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => toast.style.display = 'none', 400);
    }
}

// Show audit modal
function showAuditModal() {
    // Check if modal already exists
    let modal = document.getElementById('auditModalSPA');

    if (!modal) {
        // Create modal HTML with larger size
        const modalHTML = `
            <div id="auditModalSPA" class="modal" style="display: none;">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🔍 Running SEO Audit</h3>
                        <span class="modal-close" onclick="closeAuditModal()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="audit-progress-container">
                            <div class="progress-icon">
                                <div class="spinner"></div>
                            </div>
                            <div class="progress-info">
                                <h4 id="auditStatusTitle">Analyzing your website...</h4>
                                <p id="auditStatusMessage">Starting comprehensive SEO audit for your website</p>
                                <div class="progress-bar">
                                    <div class="progress-fill" id="progressBar" style="width: 0%"></div>
                                </div>
                                <div class="progress-text">
                                    <span id="progressPercent">0%</span>
                                    <span id="progressTime">Starting...</span>
                                </div>
                            </div>
                        </div>
                        <div class="audit-steps">
                            <div class="step" id="step-initializing">
                                <span class="step-icon">🔄</span>
                                <span class="step-text">Initializing audit</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-fetching">
                                <span class="step-icon">📊</span>
                                <span class="step-text">Fetching Google Search Console data</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-analyzing">
                                <span class="step-icon">🧠</span>
                                <span class="step-text">Analyzing metrics with AI</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-detecting">
                                <span class="step-icon">🔍</span>
                                <span class="step-text">Detecting SEO issues</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-recommendations">
                                <span class="step-icon">💡</span>
                                <span class="step-text">Generating recommendations</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-report">
                                <span class="step-icon">📄</span>
                                <span class="step-text">Creating PDF report</span>
                                <span class="step-status pending">pending</span>
                            </div>
                            <div class="step" id="step-completed">
                                <span class="step-icon">✅</span>
                                <span class="step-text">Audit completed</span>
                                <span class="step-status pending">pending</span>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" onclick="runAuditInBackground()">Run in Background</button>
                        <button class="btn-primary" id="viewResultsBtn" onclick="viewAuditResults()" style="display: none;">View Results</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHTML;
        document.body.appendChild(modalDiv.firstElementChild);
        modal = document.getElementById('auditModalSPA');
    }

    // Show modal
    if (modal) {
        modal.style.display = 'block';
        // Reset progress
        resetModalProgress();
    }
}

// Reset modal progress
function resetModalProgress() {
    // Reset progress bar
    const progressBar = document.getElementById('progressBar');
    if (progressBar) progressBar.style.setProperty('width', '0%', 'important');

    // Reset progress text
    const progressPercent = document.getElementById('progressPercent');
    if (progressPercent) progressPercent.textContent = '0%';

    const progressTime = document.getElementById('progressTime');
    if (progressTime) progressTime.textContent = 'Starting...';

    // Reset all steps to pending
    document.querySelectorAll('.step .step-status').forEach(status => {
        status.textContent = 'pending';
        status.className = 'step-status pending';
    });

    // Reset status messages
    const statusTitle = document.getElementById('auditStatusTitle');
    if (statusTitle) statusTitle.textContent = 'Analyzing your website...';

    const statusMessage = document.getElementById('auditStatusMessage');
    if (statusMessage) statusMessage.textContent = 'Starting comprehensive SEO audit for your website';
}

// Close audit modal
function closeAuditModal() {
    const modal = document.getElementById('auditModalSPA');
    if (modal) {
        modal.style.display = 'none';
    }
}

// OLD DUPLICATE FUNCTION REMOVED - using enhanced version above

// View audit results
function viewAuditResults() {
    console.log('Viewing audit results...');
    closeAuditModal();
    // Refresh dashboard to show new results
    if (window.solviaRouter) {
        window.solviaRouter.navigateTo('dashboard');
    }
}

// Trigger the actual audit
async function triggerAudit() {
    console.log('🚀 Starting audit trigger...');
    const startTime = Date.now();
    const steps = [
        { id: 'initializing', progress: 15, message: 'Initializing audit engine...' },
        { id: 'fetching', progress: 30, message: 'Fetching GSC data...' },
        { id: 'analyzing', progress: 50, message: 'Analyzing with AI...' },
        { id: 'detecting', progress: 70, message: 'Detecting issues...' },
        { id: 'recommendations', progress: 85, message: 'Generating recommendations...' },
        { id: 'report', progress: 95, message: 'Creating report...' },
        { id: 'completed', progress: 100, message: 'Audit completed!' }
    ];

    let currentStepIndex = 0;
    let progressInterval = null;
    let auditTimeoutId = null;
    let auditStartTime = Date.now();

    // Timeout handler function
    const handleAuditTimeout = () => {
        console.warn('⚠️ AUDIT TIMEOUT: Auto-cleaning up after 30+ seconds...');

        // Clear progress interval
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        // Clean up UI elements
        const overlay = document.getElementById('auditProgressOverlay');
        const backgroundIndicator = document.getElementById('auditBackgroundIndicator');

        if (backgroundIndicator) {
            // Remove background indicator
            backgroundIndicator.remove();
        } else if (overlay) {
            // Hide progress overlay
            overlay.style.transform = 'translateY(-100%)';
            setTimeout(() => overlay.style.display = 'none', 400);
        }

        // Re-enable audit button
        const auditBtn = document.getElementById('auditBtn');
        if (auditBtn) {
            auditBtn.disabled = false;
            auditBtn.textContent = 'Run a new audit';
        }

        // Show timeout notification
        const timeoutToast = document.createElement('div');
        timeoutToast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 60000;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white; padding: 16px 20px; border-radius: 12px;
            box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
            max-width: 350px; transform: translateX(400px);
            transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        timeoutToast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 24px;">⏰</div>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Audit Timeout</div>
                    <div style="font-size: 13px; opacity: 0.9;">The audit took longer than expected and was stopped.</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()"
                        style="background: none; border: none; color: white; opacity: 0.7; cursor: pointer; padding: 4px; margin-left: auto;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(timeoutToast);

        // Show toast with slide-in animation
        setTimeout(() => timeoutToast.style.transform = 'translateX(0)', 100);

        // Auto-hide after 7 seconds
        setTimeout(() => {
            timeoutToast.style.transform = 'translateX(400px)';
            setTimeout(() => timeoutToast.remove(), 400);
        }, 7000);

        console.log('🚀 TIMEOUT: Cleanup completed');
    };

    // Update progress function
    const updateProgress = (stepId, progress, message) => {
        console.log(`📊 Updating progress: ${stepId} - ${progress}% - ${message}`);

        // Note: No longer resetting timeout on each progress update
        // Timeout is set once at API call start and only cleared on success/error

        // ===== ENHANCED PROGRESS INTERFACE =====
        const overlay = document.getElementById('auditProgressOverlay');
        if (overlay) {
            // Show with slide-down animation
            overlay.style.display = 'block';
            overlay.style.transform = 'translateY(0)';
            overlay.style.animation = 'slideInDown 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        }

        // Update progress bar
        const enhancedProgressFill = document.getElementById('auditProgressFill');
        if (enhancedProgressFill) {
            enhancedProgressFill.style.width = `${progress}%`;
            console.log(`🚀 ENHANCED: Set width to ${progress}%`);
        }

        // Update percentage badge
        const enhancedProgressPercent = document.getElementById('auditProgressPercent');
        if (enhancedProgressPercent) {
            enhancedProgressPercent.textContent = `${progress}%`;
        }

        // Update status text
        const enhancedProgressText = document.getElementById('auditProgressText');
        if (enhancedProgressText) {
            enhancedProgressText.textContent = message;
        }

        // Update time estimate
        const enhancedTimeEstimate = document.getElementById('auditTimeEstimate');
        if (enhancedTimeEstimate) {
            const remainingTime = Math.max(0, Math.round((100 - progress) * 0.6));
            enhancedTimeEstimate.textContent = remainingTime > 0 ? `~${remainingTime}s remaining` : 'Almost done!';
        }

        // Update step status in enhanced interface
        const stepMap = {
            'initializing': 1,
            'fetching': 1,
            'analyzing': 2,
            'detecting': 3,
            'recommendations': 4,
            'report': 4,
            'completed': 4
        };

        const currentStep = stepMap[stepId] || 1;

        // Mark current step as running
        for (let i = 1; i <= 4; i++) {
            const stepEl = document.getElementById(`auditStep${i}`);
            const statusEl = stepEl ? stepEl.querySelector('.step-status') : null;

            if (stepEl && statusEl) {
                if (i < currentStep) {
                    // Mark as completed
                    stepEl.className = 'audit-step completed';
                    statusEl.className = 'step-status completed';
                    statusEl.textContent = 'COMPLETED';
                } else if (i === currentStep) {
                    // Mark as running
                    stepEl.className = 'audit-step running';
                    statusEl.className = 'step-status running';
                    statusEl.textContent = 'RUNNING';
                } else {
                    // Keep as pending
                    stepEl.className = 'audit-step';
                    statusEl.className = 'step-status';
                    statusEl.textContent = 'PENDING';
                }
            }
        }
        // ===== END ENHANCED INTERFACE =====

        // Update progress bar
        const progressBar = document.getElementById('progressBar');
        console.log(`🔍 Progress bar element found:`, progressBar);

        // Check if modal is visible
        const modal = document.getElementById('auditModalSPA');
        console.log(`🔍 Modal visibility:`, modal ? window.getComputedStyle(modal).display : 'Modal not found');
        console.log(`🔍 Modal found:`, modal ? 'YES' : 'NO');
        if (progressBar) {
            console.log(`🔧 Setting width to: ${progress}%`);

            // SIMPLE SOLUTION: Just set the width percentage
            progressBar.style.width = `${progress}%`;
            console.log(`✅ Set width to ${progress}%`);

            console.log(`✅ Final element rect:`, progressBar.getBoundingClientRect());

            // Debug parent chain
            const parent = progressBar.parentElement;
            console.log(`🔍 Parent (.progress-bar) rect:`, parent ? parent.getBoundingClientRect() : 'No parent');
            const grandParent = parent ? parent.parentElement : null;
            console.log(`🔍 GrandParent (.progress-info) rect:`, grandParent ? grandParent.getBoundingClientRect() : 'No grandparent');
            const greatGrandParent = grandParent ? grandParent.parentElement : null;
            console.log(`🔍 GreatGrandParent (.audit-progress-container) rect:`, greatGrandParent ? greatGrandParent.getBoundingClientRect() : 'No greatgrandparent');
        } else {
            console.error('❌ Progress bar element not found!');
            // Try to find any progress bar elements
            const allProgressBars = document.querySelectorAll('.progress-fill, #progressBar');
            console.log('🔍 All progress bar elements found:', allProgressBars);
        }

        // Update progress text
        const progressPercent = document.getElementById('progressPercent');
        if (progressPercent) progressPercent.textContent = `${progress}%`;

        // Update time
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const progressTime = document.getElementById('progressTime');
        if (progressTime) progressTime.textContent = `${elapsed}s elapsed`;

        // Update status message
        const statusMessage = document.getElementById('auditStatusMessage');
        if (statusMessage) statusMessage.textContent = message;

        // Update step status
        const stepElement = document.getElementById(`step-${stepId}`);
        if (stepElement) {
            console.log(`✅ Found step element: step-${stepId}`);
            const statusEl = stepElement.querySelector('.step-status');
            if (statusEl) {
                console.log(`✅ Found status element, current text: "${statusEl.textContent}", updating to 'running'`);
                statusEl.textContent = 'running';
                statusEl.className = 'step-status running';
                console.log(`✅ Status updated, new text: "${statusEl.textContent}", new class: "${statusEl.className}"`);
            } else {
                console.error(`❌ Status element not found in step: step-${stepId}`);
                console.log(`🔍 Step element HTML:`, stepElement.innerHTML);
            }
        } else {
            console.error(`❌ Step element not found: step-${stepId}`);
        }

        // Mark previous steps as completed
        for (let i = 0; i < currentStepIndex; i++) {
            const prevStep = document.getElementById(`step-${steps[i].id}`);
            if (prevStep) {
                const prevStatus = prevStep.querySelector('.step-status');
                if (prevStatus) {
                    prevStatus.textContent = 'completed';
                    prevStatus.className = 'step-status completed';
                }
            }
        }
    };

    try {
        const token = localStorage.getItem('auth_token') || localStorage.getItem('token');

        // Initialize timeout tracking
        auditStartTime = Date.now();
        console.log('🔄 Starting audit with 90s timeout safety...');

        // Show initial progress immediately but DON'T set timeout yet
        console.log('🔄 Setting initial progress...');
        const overlay = document.getElementById('auditProgressOverlay');
        if (overlay) {
            // Show with slide-down animation
            overlay.style.display = 'block';
            overlay.style.transform = 'translateY(0)';
            overlay.style.animation = 'slideInDown 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        }

        // Update initial step without triggering timeout
        const stepElement = document.getElementById('step-initializing');
        if (stepElement) {
            const statusElement = stepElement.querySelector('.step-status');
            const progressBar = stepElement.querySelector('.progress-bar');
            const messageElement = stepElement.querySelector('.step-message');

            if (statusElement) statusElement.textContent = 'running';
            if (progressBar) progressBar.style.width = '10%';
            if (messageElement) messageElement.textContent = 'Starting audit...';
        }

        currentStepIndex = 1; // Start from the second step in the interval

        // Start progress simulation immediately
        progressInterval = setInterval(() => {
            if (currentStepIndex < steps.length) {
                const step = steps[currentStepIndex];
                console.log(`⏰ Interval update: step ${currentStepIndex}/${steps.length}`);
                updateProgress(step.id, step.progress, step.message);
                currentStepIndex++;
            } else {
                console.log('⏹️ Stopping progress interval');
                if (progressInterval) clearInterval(progressInterval);
            }
        }, 2000); // Update every 2 seconds

        // Set timeout ONLY when API call starts (90 seconds for audit completion)
        auditTimeoutId = setTimeout(handleAuditTimeout, 90000);
        console.log('⏰ TIMEOUT: Set 90s timeout for API call');

        // Make API call
        const response = await fetch('/agent/trigger-audit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                date_range_days: 30,
                report_format: 'both',
                delivery_method: 'email',
                include_recommendations: true
            })
        });

        if (progressInterval) clearInterval(progressInterval);

        if (response.ok) {
            const data = await response.json();
            console.log('✅ Audit completed successfully:', data);
            console.log('📧 Email delivery status:', {
                email_sent: data.email_sent,
                pdf_generated: data.pdf_generated,
                audit_id: data.audit_id,
                delivery_method: data.delivery_method || 'unknown',
                user_email: data.user_email || 'not provided'
            });

            if (data.email_sent === false) {
                console.warn('⚠️ Email was not sent! Check backend email configuration.');
            }

            // Clear timeout since audit completed successfully
            if (auditTimeoutId) {
                clearTimeout(auditTimeoutId);
                auditTimeoutId = null;
                console.log('🚀 TIMEOUT: Cleared on successful completion');
            }

            // Update to 100% complete
            updateProgress('completed', 100, 'Audit completed successfully!');

            // Show success toast and cleanup progress interface
            setTimeout(() => {
                // Check if in background mode
                const backgroundIndicator = document.getElementById('auditBackgroundIndicator');

                if (backgroundIndicator) {
                    // In background mode - remove indicator and show toast
                    console.log('🚀 ENHANCED: Removing background indicator on completion');
                    backgroundIndicator.remove();
                } else {
                    // In full view mode - hide progress overlay
                    const overlay = document.getElementById('auditProgressOverlay');
                    if (overlay) {
                        overlay.style.transform = 'translateY(-100%)';
                        setTimeout(() => overlay.style.display = 'none', 400);
                    }
                }

                // Show success toast
                const toast = document.getElementById('auditSuccessToast');
                if (toast) {
                    toast.style.display = 'block';
                    toast.style.transform = 'translateX(0)';
                    toast.style.animation = 'slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';

                    // Auto-hide toast after 5 seconds
                    setTimeout(() => {
                        if (toast.style.transform !== 'translateX(400px)') {
                            toast.style.transform = 'translateX(400px)';
                            setTimeout(() => toast.style.display = 'none', 400);
                        }
                    }, 5000);
                }

                // Re-enable audit button
                const auditBtn = document.getElementById('auditBtn');
                if (auditBtn) {
                    auditBtn.disabled = false;
                    auditBtn.textContent = 'Run a new audit';
                }

                console.log('🚀 ENHANCED: Audit complete - interface cleaned up, toast shown');
            }, 2000);

            // Mark all steps as completed
            steps.forEach(step => {
                const stepEl = document.getElementById(`step-${step.id}`);
                if (stepEl) {
                    const statusEl = stepEl.querySelector('.step-status');
                    if (statusEl) {
                        statusEl.textContent = 'completed';
                        statusEl.className = 'step-status completed';
                    }
                }
            });

            // Show view results button
            const viewResultsBtn = document.getElementById('viewResultsBtn');
            if (viewResultsBtn) {
                viewResultsBtn.style.display = 'inline-block';
            }

            // Store audit ID if available
            if (data.audit_id) {
                window.currentAuditId = data.audit_id;
            }

            // Re-enable audit button with correct text
            const auditBtn = document.getElementById('auditBtn');
            if (auditBtn) {
                auditBtn.disabled = false;
                auditBtn.textContent = 'Run a new audit';
            }

            // Auto-close after 3 seconds and refresh
            setTimeout(() => {
                closeAuditModal();
                // Force reload dashboard data
                if (window.solviaRouter) {
                    window.solviaRouter.loadDashboardData();
                }
            }, 3000);

        } else {
            throw new Error(`Audit failed: ${response.status}`);
        }

    } catch (error) {
        console.error('❌ Audit failed:', error);
        if (progressInterval) clearInterval(progressInterval);

        // Clear timeout since audit failed
        if (auditTimeoutId) {
            clearTimeout(auditTimeoutId);
            auditTimeoutId = null;
            console.log('🚀 TIMEOUT: Cleared on error');
        }

        // Update status to show error
        const statusTitle = document.getElementById('auditStatusTitle');
        if (statusTitle) statusTitle.textContent = 'Audit Failed';

        const statusMessage = document.getElementById('auditStatusMessage');
        if (statusMessage) {
            statusMessage.textContent = 'Failed to complete audit. Please try again.';
            statusMessage.style.color = '#DC2626';
        }

        // Re-enable audit button
        const auditBtn = document.getElementById('auditBtn');
        if (auditBtn) {
            auditBtn.disabled = false;
            auditBtn.textContent = 'Run a new audit';
        }

        // Auto-close modal after 3 seconds on error
        setTimeout(() => {
            closeAuditModal();
        }, 3000);
    }
}

// Chat functions
// Format audit response for better readability
function formatAuditResponse(message) {
    let formatted = message;

    // Add proper line breaks and sections
    formatted = formatted.replace(/🚀/g, '\n\n🚀');
    formatted = formatted.replace(/•/g, '\n• ');
    formatted = formatted.replace(/Your audit ID is:/g, '\n\n**Your audit ID is:**');
    formatted = formatted.replace(/Your current SEO score is/g, '\n\n**Your current SEO score is**');
    formatted = formatted.replace(/The report will be emailed/g, '\n\nThe report will be emailed');

    // Clean up excessive line breaks
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    formatted = formatted.trim();

    return formatted;
}

// Convert markdown to HTML for proper formatting
function convertMarkdownToHTML(markdown) {
    let html = markdown;

    // Convert headers (### Header -> <h3>Header</h3>)
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Convert bold text (**text** -> <strong>text</strong>)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Process line by line for more reliable results
    const lines = html.split('\n');
    const processedLines = [];
    let inOrderedList = false;
    let inUnorderedList = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Check for numbered list items (handles both 1. 2. 3. and 1. 1. 1.)
        if (/^\d+\.\s/.test(line)) {
            if (!inOrderedList) {
                processedLines.push('<ol>');
                inOrderedList = true;
            }
            // Close any open unordered list
            if (inUnorderedList) {
                processedLines.push('</ul>');
                inUnorderedList = false;
            }
            // Extract content after the number and period
            const content = line.replace(/^\d+\.\s+/, '');
            processedLines.push(`<li>${content}</li>`);
        }
        // Check for bullet points
        else if (line.startsWith('- ')) {
            if (!inUnorderedList) {
                processedLines.push('<ul>');
                inUnorderedList = true;
            }
            // Close any open ordered list
            if (inOrderedList) {
                processedLines.push('</ol>');
                inOrderedList = false;
            }
            const content = line.replace(/^-\s/, '');
            processedLines.push(`<li>${content}</li>`);
        }
        // Handle empty lines or non-list content
        else {
            // Only close lists if we hit actual content (not just empty lines)
            if (line.trim() !== '') {
                // Close any open lists
                if (inOrderedList) {
                    processedLines.push('</ol>');
                    inOrderedList = false;
                }
                if (inUnorderedList) {
                    processedLines.push('</ul>');
                    inUnorderedList = false;
                }

                // Process regular content
                if (!line.includes('<')) {
                    // Wrap in paragraph if not already HTML
                    processedLines.push(`<p>${line}</p>`);
                } else {
                    // Already HTML (like headers)
                    processedLines.push(line);
                }
            } else {
                // Empty line - add break but keep lists open
                processedLines.push('<br>');
            }
        }
    }

    // Close any remaining open lists
    if (inOrderedList) {
        processedLines.push('</ol>');
    }
    if (inUnorderedList) {
        processedLines.push('</ul>');
    }

    html = processedLines.join('');

    // CRITICAL FIX: Merge consecutive <ol> tags into single lists
    // This fixes the "1. 1. 1." issue by combining separate ordered lists
    html = html.replace(/<\/ol>\s*<ol>/g, '');  // Remove </ol><ol> boundaries
    html = html.replace(/<\/ul>\s*<ul>/g, '');  // Same for unordered lists

    // Clean up formatting
    html = html.replace(/<br><br>/g, '<br>'); // Reduce multiple breaks
    html = html.replace(/<\/p><p>/g, '</p><p>'); // Clean paragraph joins
    html = html.replace(/<p>\s*<\/p>/g, ''); // Remove empty paragraphs
    html = html.replace(/<br><p>/g, '<p>'); // Clean break-paragraph combinations
    html = html.replace(/<\/ol><br>/g, '</ol>'); // Clean list-break combinations
    html = html.replace(/<\/ul><br>/g, '</ul>'); // Clean list-break combinations

    // FINAL AGGRESSIVE FIX: If we still have raw numbered lists, convert them
    // This handles cases where the line-by-line processing missed something
    if (html.includes('1.') && !html.includes('<ol>')) {
        // Emergency fix: find any remaining "number. text" patterns and convert them
        html = html.replace(/(\d+\.\s+[^<\n]*?)(?=\s*\d+\.\s|\s*$|\s*<)/g, function(match, item) {
            const content = item.replace(/^\d+\.\s+/, '');
            return `<li>${content}</li>`;
        });

        // Wrap consecutive <li> tags in <ol>
        html = html.replace(/(<li>.*?<\/li>)(\s*<li>.*?<\/li>)*/g, '<ol>$&</ol>');
    }

    return html;
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const messagesContainer = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('sendBtn');

    if (!input || !input.value.trim()) return;

    // Disable send button and input
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.style.opacity = '0.5';
        sendBtn.style.cursor = 'not-allowed';
    }
    if (input) {
        input.disabled = true;
        input.style.opacity = '0.7';
    }

    const message = input.value.trim();
    input.value = '';

    // Check if user is asking to run an audit
    const auditKeywords = ['run audit', 'new audit', 'run a new audit', 'start audit', 'perform audit', 'trigger audit'];
    const shouldTriggerAudit = auditKeywords.some(keyword => message.toLowerCase().includes(keyword));

    // If audit requested, trigger audit with enhanced progress (no modal)
    if (shouldTriggerAudit) {
        console.log('🚀 Chat audit request detected, starting audit...');
        // OLD MODAL REMOVED - using enhanced header progress instead
        // showAuditModal();
        triggerAudit();
    }

    // Add user message to chat
    const userMessageHtml = `
        <div class="chat-message user">
            <div class="message-content user">
                <div class="message-text">${message}</div>
            </div>
            <div class="message-avatar user">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 18px; height: 18px;">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
            </div>
        </div>
    `;

    // Remove skeleton and welcome message if they exist
    const skeleton = document.getElementById('chatSkeleton');
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (skeleton) skeleton.style.display = 'none';
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
        welcomeMessage.classList.add('hidden');
    }

    // Add to messages
    if (messagesContainer) {
        messagesContainer.insertAdjacentHTML('beforeend', userMessageHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Add loading indicator with fade animation instead of rotation
    const loadingMessages = [
        '🔄 Analyzing your question...',
        '🧠 Searching knowledge base...',
        '📊 Checking your website data...',
        '✍️ Crafting your response...',
        '🧪 Testing insights...',
        '⚙️ Preparing recommendations...',
        '🔍 Analyzing patterns...',
        '📈 Evaluating SEO metrics...',
        '🎯 Optimizing suggestions...',
        '💡 Generating ideas...',
        '📋 Reviewing data quality...',
        '🚀 Finalizing response...'
    ];

    let currentLoadingIndex = 0;
    const loadingHtml = `
        <div class="chat-message ai loading" id="loadingMessage">
            <div class="message-avatar ai">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="loading-fade">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                </svg>
            </div>
            <div class="message-content ai">
                <div class="message-text" id="loadingText">${loadingMessages[0]}</div>
            </div>
        </div>
    `;

    if (messagesContainer) {
        messagesContainer.insertAdjacentHTML('beforeend', loadingHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Animate loading messages
    const loadingInterval = setInterval(() => {
        currentLoadingIndex = (currentLoadingIndex + 1) % loadingMessages.length;
        const loadingTextElement = document.getElementById('loadingText');
        if (loadingTextElement) {
            loadingTextElement.textContent = loadingMessages[currentLoadingIndex];
        }
    }, 30000);

    try {
        const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
        const response = await fetch('/agent/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                message: message
            })
        });

        // Clear loading interval and remove loading message
        clearInterval(loadingInterval);
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.remove();
        }

        if (response.ok) {
            const data = await response.json();
            console.log('Chat response data:', data);

            // Extract the actual message content from the response
            let aiMessage = data.message || data.ai_response || data.response || data.message_content || 'I understand your question. Let me help you with that.';

            // Special formatting for audit responses
            if (data.audit_triggered || shouldTriggerAudit) {
                aiMessage = formatAuditResponse(aiMessage);
            }

            // Convert markdown to HTML for proper formatting
            aiMessage = convertMarkdownToHTML(aiMessage);

            // Check if an audit was triggered
            if (data.audit_triggered || shouldTriggerAudit) {
                // Refresh dashboard data after audit completes
                setTimeout(() => {
                    if (window.solviaRouter) {
                        console.log('🔄 Refreshing dashboard after chat audit...');
                        window.solviaRouter.loadDashboardData();
                    }
                }, 5000); // Wait 5 seconds for audit to complete
            }

            // Check if an audit was triggered and add download buttons
            let downloadButtons = '';
            if (data.audit_triggered && data.audit_id) {
                console.log('✅ SPA: Audit completed! Adding download buttons for audit:', data.audit_id);
                downloadButtons = `
                    <div style="display: flex; gap: 10px; margin-top: 16px;">
                        <button onclick="downloadAuditPDF('${data.audit_id}')" style="
                            background: white;
                            color: #EC6019;
                            border: 1px solid #EC6019;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: 500;
                            cursor: pointer;
                            padding: 10px 16px;
                            flex: 1;
                            transition: all 0.2s;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            gap: 8px;
                        " onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';">
                            <span>📄</span> Download PDF
                        </button>
                        <button onclick="downloadAuditJSON('${data.audit_id}')" style="
                            background: white;
                            color: #EC6019;
                            border: 1px solid #EC6019;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: 500;
                            cursor: pointer;
                            padding: 10px 16px;
                            flex: 1;
                            transition: all 0.2s;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            gap: 8px;
                        " onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';">
                            <span>📊</span> Download JSON
                        </button>
                    </div>
                `;

                // Store audit ID for potential later use
                window.currentAuditId = data.audit_id;
            }

            // Add AI response
            const aiMessageHtml = `
                <div class="chat-message ai">
                    <div class="message-avatar ai">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                        </svg>
                    </div>
                    <div class="message-content ai">
                        <div class="message-text">${aiMessage}${downloadButtons}</div>
                    </div>
                </div>
            `;

            if (messagesContainer) {
                messagesContainer.insertAdjacentHTML('beforeend', aiMessageHtml);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            // Handle suggestion buttons based on audit state
            if (data.audit_triggered) {
                // Hide suggestions during audit
                updateSuggestionButtons(null, true);

                // Show suggestions again after audit completes (estimated 60 seconds)
                setTimeout(() => {
                    updateSuggestionButtons(getRandomSuggestions());
                    console.log('✅ Audit complete - suggestions restored');
                }, 60000);
            } else {
                // Normal chat response - show suggestions
                updateSuggestionButtons(data.action_buttons || getRandomSuggestions());
            }
        } else {
            console.error('Chat API error:', response.status, response.statusText);
            // Try to get error details
            try {
                const errorData = await response.json();
                console.error('Error details:', errorData);

                // Handle GSC credentials expired (401 error)
                if (response.status === 401 || (errorData && errorData.error && errorData.error.includes('credentials expired'))) {
                    const errorMessageHtml = `
                        <div class="chat-message ai error">
                            <div class="message-avatar ai">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
                                </svg>
                            </div>
                            <div class="message-content ai">
                                <div class="message-text">
                                    🔐 <strong>Google Search Console credentials expired.</strong><br><br>
                                    I need fresh access to provide intelligent SEO insights. Please:
                                    <br><br>
                                    <button onclick="reauthorizeGoogle()" style="background: #EC6019; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin: 8px 0;">
                                        ⚡ Refresh Credentials
                                    </button>
                                    <br><br>
                                    Your chat history and settings will be preserved.
                                </div>
                            </div>
                        </div>
                    `;

                    if (messagesContainer) {
                        messagesContainer.insertAdjacentHTML('beforeend', errorMessageHtml);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                } else {
                    // Other errors
                    const genericErrorHtml = `
                        <div class="chat-message ai error">
                            <div class="message-avatar ai">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
                                </svg>
                            </div>
                            <div class="message-content ai">
                                <div class="message-text">I'm having trouble processing your request. Please try again in a moment.</div>
                            </div>
                        </div>
                    `;

                    if (messagesContainer) {
                        messagesContainer.insertAdjacentHTML('beforeend', genericErrorHtml);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                }
            } catch (e) {
                console.error('Could not parse error response');
            }
        }
    } catch (error) {
        console.error('Error sending chat message:', error);

        // Clear loading interval and remove loading message on error
        clearInterval(loadingInterval);
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.remove();
        }

        // Show error message
        const errorHtml = `
            <div class="chat-message ai error">
                <div class="message-avatar ai">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
                    </svg>
                </div>
                <div class="message-content ai">
                    <div class="message-text">Connection error. Please check your internet and try again.</div>
                </div>
            </div>
        `;

        if (messagesContainer) {
            messagesContainer.insertAdjacentHTML('beforeend', errorHtml);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    } finally {
        // Re-enable send button and input
        const sendBtn = document.getElementById('sendBtn');
        const input = document.getElementById('chatInput');
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.style.opacity = '1';
            sendBtn.style.cursor = 'pointer';
        }
        if (input) {
            input.disabled = false;
            input.style.opacity = '1';
        }
    }
}

function handleChatKeypress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

function sendSuggestion(suggestion) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = suggestion;
        sendChatMessage();
    }
}

// Pool of all available suggestions for random rotation
const suggestionPool = [
    'How was my SEO last week?',
    'Run a new audit',
    'What are my top issues?',
    'Show me traffic trends',
    'Suggest keywords for my blog',
    'How to improve my CTR?',
    'What pages need optimization?',
    'Show me my best performing queries',
    'Any pressing issues this month?',
    'What can you help me with?',
    'Analyze my competitors',
    'How to get more impressions?'
];

// Get 4 random suggestions excluding the one just used
function getRandomSuggestions(excludeText = null) {
    let available = suggestionPool.filter(s => s !== excludeText);
    let shuffled = available.sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 4);
}

// Update suggestion buttons with dynamic ones from RAG response
function updateSuggestionButtons(actionButtons, hideForAudit = false) {
    const suggestionsContainer = document.querySelector('.chat-suggestions');
    if (!suggestionsContainer) return;

    // Hide suggestions during audit
    if (hideForAudit) {
        suggestionsContainer.style.display = 'none';
        console.log('🔄 Hiding suggestions during audit...');
        return;
    }

    // Show suggestions container
    suggestionsContainer.style.display = 'flex';

    // Use provided suggestions or get random ones
    let suggestions = [];

    if (actionButtons && Array.isArray(actionButtons) && actionButtons.length > 0) {
        suggestions = actionButtons.slice(0, 4);
        console.log('✅ Using provided suggestions:', suggestions);
    } else {
        // Get random suggestions
        suggestions = getRandomSuggestions();
        console.log('🎲 Using random suggestions:', suggestions);
    }

    // Generate suggestion buttons HTML
    const suggestionsHtml = suggestions.map(suggestion =>
        `<button class="suggestion-btn" onclick="sendSuggestionWithRotation('${suggestion.replace(/'/g, "\\'")}')">${suggestion}</button>`
    ).join('');

    // Update the suggestions container
    suggestionsContainer.innerHTML = suggestionsHtml;
}

// Send suggestion and rotate suggestions
function sendSuggestionWithRotation(text) {
    // Send the suggestion
    sendSuggestion(text);

    // Rotate to new random suggestions after a short delay
    setTimeout(() => {
        updateSuggestionButtons(getRandomSuggestions(text));
    }, 100);
}

// Reauthorize Google function for GSC credentials refresh
function reauthorizeGoogle() {
    console.log('Reauthorizing Google credentials...');
    window.location.href = '/auth/google/authorize';
}

// Download functions for audit reports
async function downloadAuditPDF(auditId) {
    try {
        console.log('📄 SPA: Downloading PDF for audit:', auditId);

        // Validate audit ID format
        if (!auditId || auditId === 'undefined' || auditId === 'null') {
            console.error('Invalid audit ID:', auditId);
            alert('Invalid audit ID. Please run a new audit.');
            return;
        }

        const authToken = localStorage.getItem('auth_token');
        const response = await fetch(`/agent/report/${auditId}/pdf`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
            if (response.status === 404) {
                console.error('Audit not found');
                alert('This audit report is no longer available. Please run a new audit.');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || errorData.message}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seo_audit_${auditId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log('✅ SPA: PDF downloaded successfully');
    } catch (error) {
        console.error('Failed to download PDF:', error);
        alert('Failed to download PDF report. Please try again.');
    }
}

async function downloadAuditJSON(auditId) {
    try {
        console.log('📊 SPA: Downloading JSON for audit:', auditId);

        // Validate audit ID format
        if (!auditId || auditId === 'undefined' || auditId === 'null') {
            console.error('Invalid audit ID:', auditId);
            alert('Invalid audit ID. Please run a new audit.');
            return;
        }

        const authToken = localStorage.getItem('auth_token');
        const response = await fetch(`/agent/report/${auditId}/json`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
            if (response.status === 404) {
                console.error('Audit not found');
                alert('This audit data is no longer available. Please run a new audit.');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || errorData.message}`);
        }

        const data = await response.json();
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seo_audit_${auditId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log('✅ SPA: JSON downloaded successfully');
    } catch (error) {
        console.error('Failed to download JSON:', error);
        alert(`Failed to download JSON: ${error.message}`);
    }
}

function closeDownloadMenu() {
    const menu = document.querySelector('[id*="download-menu"]');
    if (menu) {
        menu.style.display = 'none';
    }
}


// Initialize SPA when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 SPA: Initializing Solvia SPA Router...');
    window.solviaRouter = new SolviaRouter();
    window.router = window.solviaRouter; // For backward compatibility
});