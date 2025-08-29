// Dashboard JavaScript - 100% Match with Figma Design
// CACHE BUST v2.1 - 2025-08-26 - Chat alignment fixes active

// Global variables
let currentUser = null;
let selectedWebsite = null;
let chatHistory = [];

// Handle chat keypress events  
function handleChatKeypress(event) {
    // Enter without shift sends message
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
    // Shift+Enter adds a new line (default textarea behavior)
}

// Format message with markdown-like formatting
function formatMessage(text) {
    // Convert markdown-like syntax to HTML
    let formatted = text;
    
    // Headers
    formatted = formatted.replace(/^### (.*$)/gim, '<h4 style="margin: 10px 0 5px 0; font-weight: 600; font-size: 15px;">$1</h4>');
    formatted = formatted.replace(/^## (.*$)/gim, '<h3 style="margin: 12px 0 6px 0; font-weight: 600; font-size: 16px;">$1</h3>');
    formatted = formatted.replace(/^# (.*$)/gim, '<h2 style="margin: 15px 0 8px 0; font-weight: 700; font-size: 18px;">$1</h2>');
    
    // Bold and italic
    formatted = formatted.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Bullet points and numbered lists - improved regex
    let lines = formatted.split('\n');
    let inList = false;
    let listType = '';
    let processedLines = [];
    
    for (let line of lines) {
        if (line.match(/^\d+\. /)) {
            if (!inList || listType !== 'ol') {
                if (inList) processedLines.push(`</${listType}>`);
                processedLines.push('<ol style="margin: 10px 0; padding-left: 20px;">');
                inList = true;
                listType = 'ol';
            }
            processedLines.push(`<li>${line.replace(/^\d+\. /, '')}</li>`);
        } else if (line.match(/^[\s]*[-•] /)) {
            if (!inList || listType !== 'ul') {
                if (inList) processedLines.push(`</${listType}>`);
                processedLines.push('<ul style="margin: 10px 0; padding-left: 20px;">');
                inList = true;
                listType = 'ul';
            }
            processedLines.push(`<li>${line.replace(/^[\s]*[-•] /, '')}</li>`);
        } else {
            if (inList) {
                processedLines.push(`</${listType}>`);
                inList = false;
            }
            processedLines.push(line);
        }
    }
    if (inList) processedLines.push(`</${listType}>`);
    
    formatted = processedLines.join('\n');
    
    // Line breaks (but preserve HTML tags)
    formatted = formatted.replace(/\n\n/g, '<br><br>');
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Code blocks
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; margin: 10px 0;"><code>$1</code></pre>');
    
    // Inline code  
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: #f4f4f4; padding: 2px 4px; border-radius: 3px; font-family: monospace;">$1</code>');
    
    return formatted;
}

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', async () => {
    // Show dashboard immediately first with skeleton loading
    document.body.style.opacity = '1';
    
    // Show skeleton for both metrics and issues independently
    showMetricsSkeleton();
    showIssuesSkeleton();
    
    await checkAuth();
    
    // Load metrics and issues independently (progressive loading)
    // This allows each section to show as soon as its data is ready
    const loadPromises = [
        loadOverviewMetrics(),  // Fast - GSC metrics
        loadCurrentIssues()     // Slower - Issues analysis
    ];
    
    // Execute in parallel but don't wait for all to complete
    Promise.allSettled(loadPromises).then(() => {
        console.log('All dashboard sections loaded');
    });
    
    setupEventListeners();
    loadChatHistory();
    
    // Add loaded class after initial setup
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
});

// Check authentication
async function checkAuth() {
    try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }
        
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
            return;
        }
        
        currentUser = await response.json();
        
        // Update user name in greeting
        const userName = document.getElementById('userName');
        if (currentUser.name) {
            // Get first name only
            const firstName = currentUser.name.split(' ')[0];
            userName.textContent = firstName;
        } else if (currentUser.email) {
            const emailName = currentUser.email.split('@')[0];
            userName.textContent = emailName.charAt(0).toUpperCase() + emailName.slice(1);
        }
        
        // Update user info in sidebar
        const userEmail = document.getElementById('userEmail');
        const userAvatar = document.getElementById('userAvatar');
        if (currentUser.email) {
            userEmail.textContent = currentUser.email;
            // Update avatar with first letter of email/name
            const avatarLetter = currentUser.name 
                ? currentUser.name.charAt(0).toUpperCase()
                : currentUser.email.charAt(0).toUpperCase();
            userAvatar.textContent = avatarLetter;
        }
        
        // Get selected website
        const websiteResponse = await fetch('/auth/gsc/selected-website', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (websiteResponse.ok) {
            const data = await websiteResponse.json();
            console.log('Selected website API response:', data);
            selectedWebsite = data.selected_website;
            
            // Update website URL in greeting
            const websiteUrl = document.getElementById('websiteUrl');
            if (selectedWebsite) {
                // Remove protocol and www
                let displayDomain = selectedWebsite
                    .replace(/^https?:\/\//, '')
                    .replace(/^www\./, '')
                    .replace(/^sc-domain:/, '')
                    .replace(/\/$/, ''); // Remove trailing slash
                websiteUrl.textContent = displayDomain;
                console.log('Updated website display:', displayDomain);
            } else {
                console.log('No selected website found');
            }
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login';
    }
}

// Load Overview metrics independently
async function loadOverviewMetrics() {
    try {
        // Show skeleton loading for metrics (if not already shown)
        showMetricsSkeleton();
        
        // Track start time for minimum skeleton display
        const startTime = Date.now();
        
        // Load GSC metrics (real data)
        const token = localStorage.getItem('auth_token');
        const metricsResponse = await fetch('/auth/gsc/metrics?days=30', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        // Ensure minimum display time (500ms) to prevent flashing
        const elapsedTime = Date.now() - startTime;
        const minimumDisplayTime = 500; // milliseconds
        if (elapsedTime < minimumDisplayTime) {
            await new Promise(resolve => setTimeout(resolve, minimumDisplayTime - elapsedTime));
        }
        
        if (metricsResponse.ok) {
            const metrics = await metricsResponse.json();
            updateOverviewMetrics(metrics);
            
            // Hide skeleton and show real metrics
            hideMetricsSkeleton();
        } else if (metricsResponse.status === 401) {
            // Handle credentials error - check if it's Google OAuth issue
            const errorData = await metricsResponse.json().catch(() => ({}));
            if (errorData.detail && errorData.detail.includes('Google Search Console credentials not found')) {
                console.log('GSC credentials lost, showing re-authentication message');
                showCredentialsError();
                hideMetricsSkeleton(); // Hide skeleton on error
                return;
            }
            // Other 401 errors redirect to login
            console.log('Authentication failed, redirecting to login');
            hideMetricsSkeleton(); // Hide skeleton on error
            window.location.href = '/login';
        } else {
            // Other errors - hide skeleton and show default values
            hideMetricsSkeleton();
            console.log('Failed to load metrics, showing defaults');
        }
    } catch (error) {
        console.error('Failed to load overview metrics:', error);
        hideMetricsSkeleton();
    }
}

// Load dashboard data (both sections) - kept for backward compatibility
async function loadDashboardData() {
    // Load both sections in parallel
    await Promise.allSettled([
        loadOverviewMetrics(),
        loadCurrentIssues()
    ]);
}

// Update overview metrics with real GSC data
function updateOverviewMetrics(metrics) {
    // SEO Score
    const seoScore = document.getElementById('seoScore');
    const seoChange = document.getElementById('seoChange');
    if (metrics.seo_score !== undefined && metrics.seo_score !== null) {
        seoScore.textContent = `${Math.round(metrics.seo_score)}/100`;
        
        // Change indicator based on real data
        if (metrics.seo_score_change !== undefined && metrics.seo_score_change !== 0) {
            const change = metrics.seo_score_change;
            const percentChange = Math.abs(change).toFixed(1);
            seoChange.textContent = `${change >= 0 ? '↑' : '↓'} ${percentChange} pts from last month`;
            seoChange.className = `metric-change ${change >= 0 ? '' : 'negative'}`;
        } else if (selectedWebsite) {
            // We have a website selected, show monitoring status
            seoChange.textContent = 'Currently monitoring';
            seoChange.className = 'metric-change';
        } else {
            seoChange.textContent = 'No comparison data';
            seoChange.className = 'metric-change';
        }
    } else if (!selectedWebsite) {
        // No website selected
        seoScore.textContent = '0/100';
        seoChange.textContent = 'Connect your website to start tracking';
        seoChange.className = 'metric-change';
    } else {
        // Website selected but no data yet
        seoScore.textContent = '25/100';
        seoChange.textContent = 'Base score - run audit for accurate data';
        seoChange.className = 'metric-change';
    }
    
    // Organic Traffic (Clicks from GSC)
    const organicTraffic = document.getElementById('organicTraffic');
    const trafficChange = document.getElementById('trafficChange');
    if (metrics.organic_traffic !== undefined || metrics.clicks !== undefined) {
        const clicks = metrics.organic_traffic || metrics.clicks || 0;
        organicTraffic.textContent = formatNumber(clicks);
        
        if (metrics.clicks_change !== undefined) {
            const change = metrics.clicks_change;
            const percentChange = clicks > 0 ? ((change / clicks) * 100).toFixed(1) : '0.0';
            trafficChange.textContent = `${change >= 0 ? '↑' : '↓'} ${Math.abs(percentChange)}% from last month`;
            trafficChange.className = `metric-change ${change >= 0 ? '' : 'negative'}`;
        } else if (clicks === 0) {
            trafficChange.textContent = 'No clicks recorded';
            trafficChange.className = 'metric-change negative';
        } else {
            trafficChange.textContent = 'No comparison data';
            trafficChange.className = 'metric-change';
        }
    } else {
        organicTraffic.textContent = '0';
        trafficChange.textContent = 'No traffic data yet - run your first audit';
        trafficChange.className = 'metric-change';
    }
    
    // Average Position
    const avgPosition = document.getElementById('avgPosition');
    const positionChange = document.getElementById('positionChange');
    if (metrics.avg_position !== undefined && metrics.avg_position > 0) {
        avgPosition.textContent = metrics.avg_position.toFixed(1);
        
        if (metrics.position_change !== undefined) {
            const change = metrics.position_change;
            // Lower position is better (negative change is improvement)
            positionChange.textContent = `${change <= 0 ? '↑' : '↓'} ${Math.abs(change.toFixed(1))} positions`;
            positionChange.className = `metric-change ${change <= 0 ? '' : 'negative'}`;
        } else {
            positionChange.textContent = 'No comparison data';
            positionChange.className = 'metric-change';
        }
    } else {
        avgPosition.textContent = '0.0';
        positionChange.textContent = 'No rankings found';
        positionChange.className = 'metric-change negative';
    }
    
    // Backlinks approximation - GSC doesn't provide this, using impressions as proxy
    const backlinks = document.getElementById('backlinks');
    const backlinksChange = document.getElementById('backlinksChange');
    if (metrics.impressions !== undefined && metrics.impressions > 0) {
        // Use impressions as a proxy for backlink potential (simplified)
        const estimatedBacklinks = Math.floor(metrics.impressions / 1000) || 1;
        backlinks.textContent = estimatedBacklinks.toString();
        
        if (metrics.impressions_change !== undefined) {
            const change = Math.floor(metrics.impressions_change / 1000);
            if (change !== 0) {
                backlinksChange.textContent = `${change >= 0 ? '↑' : '↓'} ${Math.abs(change)} est. this month`;
                backlinksChange.className = `metric-change ${change >= 0 ? '' : 'negative'}`;
            } else {
                backlinksChange.textContent = 'No significant change';
                backlinksChange.className = 'metric-change';
            }
        } else {
            backlinksChange.textContent = 'No comparison data';
            backlinksChange.className = 'metric-change';
        }
    } else {
        backlinks.textContent = '0';
        backlinksChange.textContent = 'No impression data';
        backlinksChange.className = 'metric-change negative';
    }
}

// Update current issues section
function updateCurrentIssues(issuesData) {
    console.log('updateCurrentIssues called with:', issuesData);
    const skeleton = document.getElementById('issuesSkeleton');
    const realIssues = document.getElementById('realIssues');
    
    console.log('Elements found - skeleton:', skeleton, 'realIssues:', realIssues);
    
    // Hide skeleton and show real issues container
    if (skeleton) {
        skeleton.classList.add('hidden');
        console.log('Skeleton hidden by adding hidden class');
    }
    if (realIssues) {
        realIssues.style.display = 'contents';
        console.log('Real issues shown');
    }
    
    if (!issuesData || !issuesData.has_issues || !issuesData.issues || issuesData.issues.length === 0) {
        // No real issues - show beautiful empty state
        console.log('No real issues found, showing empty state');
        if (realIssues) {
            realIssues.innerHTML = `
                <div class="no-issues-message">
                    <span class="emoji">🎉</span>
                    <h3>Great News! No Critical Issues Found</h3>
                    <p>Your website appears to be performing well. Run a comprehensive audit to get detailed insights and discover optimization opportunities.</p>
                    <button class="action-btn" onclick="runNewAudit()">Run Full Audit</button>
                </div>
            `;
        }
        return;
    }
    
    // Clear existing issues and replace with real ones
    realIssues.innerHTML = '';
    
    // Display only top 1-2 HIGH severity issues as per spec
    const highSeverityIssues = issuesData.issues.filter(issue => 
        issue.severity === 'critical' || issue.severity === 'high'
    ).slice(0, 2); // Max 2 issues
    
    highSeverityIssues.forEach(issue => {
        const severityClass = 
            issue.severity === 'critical' ? 'critical' :
            issue.severity === 'high' ? 'warning' :
            'warning'; // Default to warning for medium/low
        
        // Get appropriate SVG icon based on severity
        const iconSVG = issue.severity === 'critical' 
            ? `<svg class="issue-icon critical" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
               </svg>`
            : `<svg class="issue-icon warning" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
               </svg>`;
        
        // Prepare descriptions with progressive disclosure (2025 UX best practices)
        const fullDescription = issue.description || issue.impact || 'This issue may impact your SEO performance.';
        const shortDescription = fullDescription.length > 120 ? fullDescription.substring(0, 120) + '...' : fullDescription;
        
        // Create enhanced detailed content with business impact and actionable insights
        const detailedContent = createDetailedContent(issue);
        const hasDetailedContent = detailedContent.length > 0;
        const cardId = `card-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        // Add impact tag if available
        const impactTag = issue.impact && issue.impact.includes('%') 
            ? `<span class="impact-tag" style="
                display: inline-block;
                padding: 2px 8px;
                background: ${issue.severity === 'critical' ? '#FEE2E2' : '#FEF3C7'};
                color: ${issue.severity === 'critical' ? '#DC2626' : '#D97706'};
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                margin-left: 8px;
              ">${issue.impact.match(/-?\d+%/)?.[0] || 'High Impact'}</span>`
            : '';
        
        const card = document.createElement('div');
        card.className = `issue-card ${severityClass}`;
        card.innerHTML = `
            <div class="issue-header">
                ${iconSVG}
                <div class="issue-title">${issue.title}${impactTag}</div>
            </div>
            <div class="issue-description">
                <div class="issue-description-short" id="short-${cardId}">
                    ${shortDescription}
                </div>
                <div class="issue-description-full" id="full-${cardId}">
                    ${detailedContent}
                </div>
                <button class="issue-expand-btn" onclick="toggleIssueDescription('${cardId}')">
                    Show more details →
                </button>
            </div>
            <div class="issue-fix">
                <strong>Fix:</strong> ${issue.recommendation || 'Review and address this issue to improve your SEO score.'}
            </div>
        `;
        
        realIssues.appendChild(card);
    });
    
    // Store all issues in window for access (do this ALWAYS, not just conditionally)
    window.allIssuesData = issuesData.issues || [];
    console.log('Stored all issues data:', window.allIssuesData.length, 'issues');
    
    // Add "View All Issues" button if there are more issues
    if (issuesData.issues.length > 2 || issuesData.issues.length > highSeverityIssues.length) {
        const viewAllContainer = document.createElement('div');
        viewAllContainer.style.cssText = 'grid-column: 1 / -1; text-align: center; margin-top: 20px;';
        viewAllContainer.innerHTML = `
            <button class="view-all-btn" onclick="showAllIssues()" style="
                padding: 10px 24px;
                background: white;
                color: #EC6019;
                border: 1px solid #EC6019;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
            "
            onmouseover="this.style.background='#EC6019'; this.style.color='white';"
            onmouseout="this.style.background='white'; this.style.color='#EC6019';">
                View All Issues →
            </button>
        `;
        realIssues.appendChild(viewAllContainer);
    }
    
    console.log(`Updated issues section with ${highSeverityIssues.length} high-severity issues (of ${issuesData.issues.length} total)`);
}

// Show loading skeleton for issues
function showIssuesSkeleton() {
    console.log('showIssuesSkeleton called');
    const skeleton = document.getElementById('issuesSkeleton');
    const realIssues = document.getElementById('realIssues');
    
    console.log('Skeleton element:', skeleton);
    console.log('Real issues element:', realIssues);
    
    if (skeleton) {
        skeleton.classList.remove('hidden');
        console.log('Skeleton shown by removing hidden class');
    } else {
        console.error('Skeleton element not found!');
    }
    
    if (realIssues) {
        realIssues.style.display = 'none';
        console.log('Real issues hidden');
    } else {
        console.error('Real issues element not found!');
    }
    
    console.log('Issues loading skeleton should now be visible');
}

// Create detailed content for progressive disclosure
function createDetailedContent(issue) {
    const issueDetails = {
        "Low Organic Traffic": {
            analysis: "Your website is receiving fewer visitors from search engines than it should. This typically indicates problems with SEO fundamentals like content optimization, keyword targeting, or technical SEO issues.",
            businessImpact: "Low organic traffic means missed opportunities for customer acquisition. Every potential visitor not finding your site represents lost revenue and brand awareness.",
            metrics: "Target: Increase organic traffic by 40-60% within 3 months",
            nextSteps: [
                "Conduct keyword research for your industry",
                "Optimize existing pages for target keywords",
                "Create content around high-value search terms",
                "Improve page loading speed and mobile experience"
            ]
        },
        "Minimal Search Visibility": {
            analysis: "Your website has very low visibility in search engine results. This means search engines may not be properly indexing your content, or your content isn't optimized for relevant search queries.",
            businessImpact: "Poor search visibility directly impacts your ability to attract new customers. If people can't find you in search results, they'll find your competitors instead.",
            metrics: "Target: Get indexed in Google and appear for 100+ relevant keywords",
            nextSteps: [
                "Submit XML sitemap to Google Search Console",
                "Verify site is crawlable by search engines",
                "Create targeted content for key business terms",
                "Build authoritative backlinks to improve rankings"
            ]
        },
        "Poor Click-Through Rate": {
            analysis: "Your pages appear in search results but users aren't clicking through to your website. This indicates your meta titles and descriptions aren't compelling enough or don't match search intent.",
            businessImpact: "Low CTR means wasted opportunities - you're visible but not converting searchers into visitors. This also signals to Google that your content may not be relevant.",
            metrics: "Target: Improve CTR to 3-5% (industry average)",
            nextSteps: [
                "Rewrite meta titles to be more compelling",
                "Create engaging meta descriptions with clear value propositions",
                "A/B test different title approaches",
                "Ensure titles match actual search intent"
            ]
        }
    };

    const details = issueDetails[issue.title] || issueDetails["Low Organic Traffic"]; // Fallback
    
    return `
        <div style="background: #F8FAFC; padding: 16px; border-radius: 8px; margin-top: 12px;">
            <div style="margin-bottom: 12px;">
                <strong style="color: #1F2937;">📊 Detailed Analysis</strong>
                <p style="margin: 6px 0 0 0; color: #4B5563; font-size: 13px; line-height: 1.4;">
                    ${details.analysis}
                </p>
            </div>
            
            <div style="margin-bottom: 12px;">
                <strong style="color: #1F2937;">💼 Business Impact</strong>
                <p style="margin: 6px 0 0 0; color: #4B5563; font-size: 13px; line-height: 1.4;">
                    ${details.businessImpact}
                </p>
            </div>
            
            <div style="margin-bottom: 12px;">
                <strong style="color: #1F2937;">🎯 Success Metrics</strong>
                <p style="margin: 6px 0 0 0; color: #4B5563; font-size: 13px; line-height: 1.4;">
                    ${details.metrics}
                </p>
            </div>
            
            <div>
                <strong style="color: #1F2937;">✅ Next Steps</strong>
                <ul style="margin: 6px 0 0 16px; color: #4B5563; font-size: 13px; line-height: 1.4;">
                    ${details.nextSteps.map(step => `<li style="margin: 4px 0;">${step}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
}

// Show all issues in a beautiful modal
function showAllIssues() {
    // Get the stored issues data
    const allIssues = window.allIssuesData || [];
    console.log('ShowAllIssues called, issues available:', allIssues.length);
    
    if (allIssues.length === 0) {
        // Show beautiful no issues modal
        showNoIssuesModal();
        return;
    }
    
    // Show all issues in a proper modal
    showAllIssuesModal(allIssues);
}

// Show beautiful no issues modal
function showNoIssuesModal() {
    const modalHTML = `
        <div id="noIssuesModal" style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        ">
            <div style="
                background: white;
                border-radius: 16px;
                padding: 32px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                animation: slideUp 0.3s ease;
            ">
                <div style="
                    width: 64px;
                    height: 64px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 20px;
                ">
                    <svg width="32" height="32" fill="white" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-3a1 1 0 00-2 0v3a1 1 0 002 0V7zm-1 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <h3 style="
                    font-size: 20px;
                    font-weight: 600;
                    color: #1F2937;
                    margin: 0 0 12px 0;
                ">No Additional Issues Available</h3>
                <p style="
                    color: #6B7280;
                    font-size: 14px;
                    line-height: 1.5;
                    margin: 0 0 24px 0;
                ">All current issues are already displayed on the dashboard. Run a new comprehensive audit to discover more optimization opportunities.</p>
                <button onclick="document.getElementById('noIssuesModal').remove()" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    Got it
                </button>
            </div>
        </div>
    `;
    
    // Add modal to body
    const div = document.createElement('div');
    div.innerHTML = modalHTML;
    document.body.appendChild(div.firstElementChild);
}

// Show all issues in a beautiful modal
function showAllIssuesModal(allIssues) {
    // Create beautiful modal
    const modalHTML = `
        <div id="allIssuesModal" style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        ">
            <div style="
                background: white;
                border-radius: 16px;
                max-width: 900px;
                width: 90%;
                max-height: 80vh;
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                animation: slideUp 0.3s ease;
            ">
                <!-- Header -->
                <div style="
                    padding: 24px 32px;
                    border-bottom: 1px solid #E5E7EB;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <h2 style="
                            font-size: 24px;
                            font-weight: 700;
                            color: #1F2937;
                            margin: 0;
                        ">All SEO Issues (${allIssues.length})</h2>
                        <p style="
                            color: #6B7280;
                            font-size: 14px;
                            margin: 4px 0 0 0;
                        ">Complete list of issues found in your latest audit</p>
                    </div>
                    <button onclick="document.getElementById('allIssuesModal').remove()" style="
                        background: transparent;
                        border: none;
                        cursor: pointer;
                        padding: 8px;
                    ">
                        <svg width="24" height="24" fill="#6B7280" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </button>
                </div>
                
                <!-- Content -->
                <div style="
                    padding: 24px 32px;
                    overflow-y: auto;
                    flex: 1;
                ">
                    <div style="
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                        gap: 20px;
                    " id="modalIssuesGrid">
                        <!-- Issues will be inserted here -->
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="
                    padding: 20px 32px;
                    border-top: 1px solid #E5E7EB;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div style="color: #6B7280; font-size: 14px;">
                        Showing all ${allIssues.length} issues from your latest SEO audit
                    </div>
                    <button onclick="document.getElementById('allIssuesModal').remove(); runNewAudit()" style="
                        background: linear-gradient(135deg, #EC6019 0%, #F7931E 100%);
                        color: white;
                        padding: 10px 24px;
                        border: none;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: transform 0.2s;
                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        Run New Audit
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    const div = document.createElement('div');
    div.innerHTML = modalHTML;
    document.body.appendChild(div.firstElementChild);
    
    // Get the grid container
    const grid = document.getElementById('modalIssuesGrid');
    
    // Display ALL issues in modal
    allIssues.forEach((issue, index) => {
        const severityClass = 
            issue.severity === 'critical' ? 'critical' :
            issue.severity === 'high' ? 'warning' :
            'warning';
        
        const severityColor = 
            issue.severity === 'critical' ? '#DC2626' :
            issue.severity === 'high' ? '#F59E0B' :
            '#6B7280';
        
        const cardHTML = `
            <div style="
                background: ${issue.severity === 'critical' ? '#FEF2F2' : issue.severity === 'high' ? '#FFFBEB' : '#F9FAFB'};
                border: 1px solid ${issue.severity === 'critical' ? '#FCA5A5' : issue.severity === 'high' ? '#FCD34D' : '#E5E7EB'};
                border-radius: 12px;
                padding: 20px;
            ">
                <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
                    <svg width="24" height="24" fill="${severityColor}" viewBox="0 0 20 20">
                        ${issue.severity === 'critical' 
                            ? '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>'
                            : '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>'}
                    </svg>
                    <div style="flex: 1;">
                        <h4 style="
                            font-size: 15px;
                            font-weight: 600;
                            color: #1F2937;
                            margin: 0 0 4px 0;
                        ">${issue.title}</h4>
                        <span style="
                            display: inline-block;
                            padding: 2px 8px;
                            background: ${severityColor}20;
                            color: ${severityColor};
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 600;
                            text-transform: uppercase;
                        ">${issue.severity}</span>
                    </div>
                </div>
                <p style="
                    color: #4B5563;
                    font-size: 13px;
                    line-height: 1.5;
                    margin: 0 0 12px 0;
                ">${issue.description || 'This issue needs attention.'}</p>
                <div style="
                    border-top: 1px solid ${issue.severity === 'critical' ? '#FCA5A5' : issue.severity === 'high' ? '#FCD34D' : '#E5E7EB'};
                    padding-top: 12px;
                    margin-top: 12px;
                ">
                    <strong style="color: #1F2937; font-size: 12px;">Recommended Action:</strong>
                    <p style="
                        color: #4B5563;
                        font-size: 12px;
                        line-height: 1.4;
                        margin: 4px 0 0 0;
                    ">${issue.recommendation || 'Review and address this issue.'}</p>
                </div>
            </div>
        `;
        
        const cardDiv = document.createElement('div');
        cardDiv.innerHTML = cardHTML;
        grid.appendChild(cardDiv.firstElementChild);
    });
    
    // Add CSS animations if not already added
    if (!document.getElementById('modalAnimations')) {
        const style = document.createElement('style');
        style.id = 'modalAnimations';
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideUp {
                from { 
                    opacity: 0;
                    transform: translateY(20px);
                }
                to { 
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// Progressive disclosure function for issue descriptions (2025 UX best practice)
function toggleIssueDescription(cardId) {
    const shortDiv = document.getElementById(`short-${cardId}`);
    const fullDiv = document.getElementById(`full-${cardId}`);
    const btn = event.target;
    
    if (fullDiv.style.display === 'none' || fullDiv.style.display === '') {
        // Show full description
        shortDiv.style.display = 'none';
        fullDiv.style.display = 'block';
        btn.textContent = '← Show less details';
        console.log('Expanded issue description for card:', cardId);
    } else {
        // Show short description
        shortDiv.style.display = 'block';
        fullDiv.style.display = 'none';
        btn.textContent = 'Show more details →';
        console.log('Collapsed issue description for card:', cardId);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Sidebar navigation
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            if (!this.classList.contains('active')) {
                // Dashboard navigation is primary interface
                console.log('Navigation to other pages coming soon');
            }
        });
    });
}

// Chat functionality
function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        // Check if message is requesting an audit
        const auditKeywords = ['audit', 'analyze', 'check', 'scan', 'review', 'assess', 'seo'];
        const isAuditRequest = auditKeywords.some(keyword => 
            message.toLowerCase().includes(keyword)
        );
        
        if (isAuditRequest) {
            // Trigger audit
            await triggerAudit(message);
        } else {
            // Regular chat with Solvia
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/agent/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) throw new Error('Chat request failed');
            
            const data = await response.json();
            
            // Remove typing indicator
            hideTypingIndicator();
            
            // Add AI response - FIX: API returns 'message' not 'response'
            addMessageToChat('ai', data.message);
            
            // If response includes audit trigger - FIX: API returns 'audit_triggered'
            if (data.audit_triggered) {
                await triggerAudit('Running comprehensive SEO audit...');
            }
            
            // Add action buttons if provided
            if (data.action_buttons && data.action_buttons.length > 0) {
                displayActionButtons(data.action_buttons);
            }
        }
    } catch (error) {
        console.error('Failed to send message:', error);
        hideTypingIndicator();
        addMessageToChat('ai', 'I apologize, but I need you to be logged in to help with your SEO. Please login first.');
    }
}

// Send suggestion message
function sendSuggestion(suggestion) {
    document.getElementById('chatInput').value = suggestion;
    sendMessage();
}

// Run new audit with progress tracking
async function runNewAudit() {
    const auditBtn = document.getElementById('auditBtn');
    auditBtn.disabled = true;
    auditBtn.textContent = 'Starting audit...';
    
    // Show progress modal
    showAuditProgress();
    
    // Add initial message
    addMessageToChat('ai', 'Starting a comprehensive SEO audit for your website... 🔍');
    
    try {
        const token = localStorage.getItem('auth_token');
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
        
        if (!response.ok) throw new Error('Failed to start audit');
        
        const data = await response.json();
        const auditId = data.audit_id;
        
        console.log('MODAL AUDIT RESPONSE DEBUG:', data);
        console.log('Modal Audit ID from response:', auditId);
        
        // Start progress tracking with SSE
        await trackAuditProgress(auditId);
        
        // Audit completed
        auditBtn.disabled = false;
        auditBtn.textContent = 'Run a new audit';
        
        // Enhanced success message with RAG insights
        const enhancedInsights = data.enhanced_insights || {};
        const ragEnhanced = data.rag_enhanced || false;
        
        let enhancedMessage = `✅ SEO Audit Complete!
            
SEO Score: ${Math.round(data.seo_score)}/100
            
${data.issues_count.critical > 0 ? `⚠️ Found ${data.issues_count.critical} critical issues` : ''}
${data.issues_count.high > 0 ? `🔸 Found ${data.issues_count.high} high priority issues` : ''}
${data.issues_count.medium > 0 ? `📋 Found ${data.issues_count.medium} medium priority issues` : ''}`;

        if (ragEnhanced) {
            enhancedMessage += `

🤖 **Enhanced AI Analysis Results:**
${enhancedInsights.evidence_backed_issues > 0 ? `🔍 ${enhancedInsights.evidence_backed_issues} issues backed by evidence` : ''}
${enhancedInsights.pattern_detected_issues > 0 ? `📊 ${enhancedInsights.pattern_detected_issues} patterns detected in your data` : ''}
${enhancedInsights.high_confidence_issues > 0 ? `✨ ${enhancedInsights.high_confidence_issues} high-confidence recommendations` : ''}`;
        }

        enhancedMessage += `

Your detailed report has been ${data.email_sent ? 'emailed to you' : 'generated'}.

I've updated the dashboard with your latest SEO insights.${ragEnhanced ? ' This audit was enhanced with our latest AI intelligence for more accurate results.' : ''}`;

        addMessageToChat('ai', enhancedMessage);
        
        // Reload dashboard data
        await loadDashboardData();
        
    } catch (error) {
        console.error('Audit failed:', error);
        auditBtn.disabled = false;
        auditBtn.textContent = 'Run a new audit';
        hideAuditProgress();
        addMessageToChat('ai', '❌ Audit failed. Please check your connection and try again.');
    }
}

// Trigger audit
async function triggerAudit(prompt) {
    showTypingIndicator();
    
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch('/agent/trigger-audit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                prompt,
                website_url: selectedWebsite || window.location.hostname,
                date_range_days: 30,
                report_format: 'both',
                delivery_method: 'email',
                include_recommendations: true
            })
        });
        
        if (!response.ok) throw new Error('Audit request failed');
        
        const audit = await response.json();
        
        console.log('AUDIT RESPONSE DEBUG:', audit);
        console.log('Audit ID from response:', audit.audit_id);
        
        hideTypingIndicator();
        
        // Add audit completion message with download buttons
        const auditMessage = `✅ SEO Audit Complete!
            
SEO Score: ${Math.round(audit.seo_score)}/100

I've analyzed your website and identified ${audit.critical_issues || 0} critical issues that need attention.

Dashboard has been updated with latest results.

<div style="margin-top: 12px; display: flex; gap: 8px;">
<button onclick="downloadAuditPDF('${audit.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; padding: 10px 16px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📄 Download PDF</span></button>
<button onclick="downloadAuditJSON('${audit.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; padding: 10px 16px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📊 Download JSON</span></button>
</div>`;
        
        addMessageToChat('ai', auditMessage);
        
        // Refresh dashboard data
        await loadDashboardData();
        
    } catch (error) {
        console.error('Audit failed:', error);
        hideTypingIndicator();
        addMessageToChat('ai', 'Please login first to run an SEO audit. I need access to your Google Search Console data.');
    }
}

// Helper function to format relative time
function getRelativeTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
    const weeks = Math.floor(days / 7);
    if (weeks < 4) return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
}

// Add message to chat with timestamp
function addMessageToChat(type, text, timestamp = null) {
    const messagesContainer = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    
    // Create proper SVG icons
    const userIcon = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
    </svg>`;
    
    const robotIcon = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"/>
    </svg>`;
    
    const avatar = type === 'user' ? userIcon : robotIcon;
    const avatarClass = type === 'user' ? 'user' : 'ai';
    const contentClass = type === 'user' ? 'user' : 'ai';
    
    // Format AI messages with markdown, keep user messages with basic line breaks
    const displayText = type === 'ai' ? formatMessage(text) : text.replace(/\n/g, '<br>');
    
    // Get relative time
    const relativeTime = getRelativeTime(timestamp || new Date());
    
    // Create proper message structure - let CSS handle the layout
    messageDiv.innerHTML = `
        <div class="message-avatar ${avatarClass}">${avatar}</div>
        <div class="message-content ${contentClass}">
            <div class="message-text">${displayText}</div>
        </div>
    `;
    
    // Add timestamp below the entire message
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-timestamp';
    timeDiv.style.cssText = `
        width: 100%;
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 0;
        margin-bottom: 10px;
        opacity: 0.7;
        text-align: ${type === 'user' ? 'right' : 'left'};
        padding: 0 44px;
    `;
    timeDiv.textContent = relativeTime;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.appendChild(timeDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in chat history
    chatHistory.push({ type, text, timestamp: new Date() });
}

// Show typing indicator
// Get random typing text for variety
function getRandomTypingText() {
    const typingTexts = [
        'Thinking...',
        'Examining your SEO data...',
        'Analyzing metrics...',
        'Processing...',
        'Checking performance...',
        'Reviewing your site...',
        'Gathering insights...',
        'Evaluating SEO health...'
    ];
    return typingTexts[Math.floor(Math.random() * typingTexts.length)];
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    
    // Check if typing indicator already exists
    if (document.getElementById('typingIndicator')) return;
    
    const robotIcon = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"/>
    </svg>`;
    
    const typingText = getRandomTypingText();
    
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'chat-message';
    typingDiv.innerHTML = `
        <div class="message-avatar ai">${robotIcon}</div>
        <div class="message-content ai">
            <div class="message-text">${typingText}</div>
        </div>
    `;
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Check for latest audit and show PDF button
async function checkLatestAuditButton() {
    try {
        const token = localStorage.getItem('auth_token');
        
        // Fetch audit history to get the latest audit
        const response = await fetch('/agent/history?limit=10', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            console.log('Failed to fetch audit history');
            return;
        }
        
        const data = await response.json();
        console.log('Audit history response:', data);
        
        // The response is likely an array directly, not nested
        const audits = Array.isArray(data) ? data : (data.audits || []);
        
        if (audits.length > 0) {
            const latestAudit = audits[0]; // Most recent audit
            
            console.log('LATEST AUDIT CHECK:', latestAudit.audit_id, latestAudit.created_at);
            
            // Remove all existing download buttons first (clean slate)
            const allDownloadElements = document.querySelectorAll('button[onclick*="downloadAuditPDF"], a[onclick*="downloadAuditPDF"]');
            let hasOldButton = false;
            let buttonExists = false;
            
            allDownloadElements.forEach(element => {
                const onclickStr = element.getAttribute('onclick') || '';
                if (!onclickStr.includes(latestAudit.audit_id)) {
                    // This is an old button with different audit ID - remove it
                    console.log('Removing old download button with onclick:', onclickStr);
                    element.remove();
                    hasOldButton = true;
                } else {
                    buttonExists = true;
                }
            });
            
            // Always add the latest audit button if one exists and not already present
            if (latestAudit.audit_id && !buttonExists) {
                console.log('Adding audit completion message with download buttons');
                const auditTimeStr = getRelativeTime(latestAudit.created_at);
                const persistMessage = `✅ Your recent SEO audit is ready!

SEO Score: ${Math.round(latestAudit.seo_score)}/100
Run ${auditTimeStr}

<div style="margin-top: 12px; display: flex; gap: 8px;">
<button onclick="downloadAuditPDF('${latestAudit.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 8px 12px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📄 Download PDF</span></button>
<button onclick="downloadAuditJSON('${latestAudit.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 8px 12px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📊 Download JSON</span></button>
</div>`;
                    
                // Add to chat as an AI message
                addMessageToChat('ai', persistMessage);
            }
        }
    } catch (error) {
        console.error('Failed to check latest audit:', error);
    }
}

// Fix any existing broken PDF buttons with the latest audit ID
async function fixBrokenPDFButtons() {
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch('/agent/history?limit=1', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.length > 0) {
            const latestAudit = data[0];
            
            console.log('FIXING BROKEN PDF BUTTONS - Latest audit ID:', latestAudit.audit_id);
            
            // Find all PDF download buttons and update them with the latest audit ID
            const allDownloadElements = document.querySelectorAll('a[onclick*="downloadAuditPDF"], button[onclick*="downloadAuditPDF"]');
            
            allDownloadElements.forEach(element => {
                const currentOnclick = element.getAttribute('onclick') || '';
                if (!currentOnclick.includes(latestAudit.audit_id)) {
                    console.log('Updating broken PDF button from:', currentOnclick);
                    const newOnclick = `downloadAuditPDF('${latestAudit.audit_id}'); return false;`;
                    element.setAttribute('onclick', newOnclick);
                    console.log('Updated to:', newOnclick);
                }
            });
        }
    } catch (error) {
        console.error('Failed to fix broken PDF buttons:', error);
    }
}

// Load chat history
async function loadChatHistory() {
    try {
        const token = localStorage.getItem('auth_token');
        
        // Show skeleton loading
        const chatSkeleton = document.getElementById('chatSkeleton');
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (chatSkeleton) chatSkeleton.style.display = 'flex';
        if (welcomeMessage) welcomeMessage.style.display = 'none';
        
        const response = await fetch('/auth/chat/history?limit=10', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        // Hide skeleton loading
        if (chatSkeleton) chatSkeleton.style.display = 'none';
        
        if (!response.ok) {
            // Show welcome message on error
            if (welcomeMessage) welcomeMessage.style.display = 'flex';
            return;
        }
        
        const data = await response.json();
        const messages = data.messages || [];
        
        // Clear and populate messages
        if (messages.length > 0) {
            document.getElementById('chatMessages').innerHTML = '';
            
            messages.forEach(msg => {
                const type = msg.message_type || (msg.sender_name === 'User' ? 'user' : 'ai');
                
                // Debug logging
                if (type === 'ai' && msg.message_content.includes('audit')) {
                    console.log('Found audit-related message:', msg.message_content.substring(0, 100));
                }
                
                // Check if this is an audit completion message and enhance it
                if (type === 'ai' && (msg.message_content.includes('Audit Complete') || msg.message_content.includes('audit ID'))) {
                    console.log('Detected audit completion message');
                    // Extract audit_id if present in the message
                    const auditIdMatch = msg.message_content.match(/audit ID[:\s]+([a-f0-9-]+)/i);
                    console.log('Audit ID match result:', auditIdMatch);
                    
                    if (auditIdMatch) {
                        const auditId = auditIdMatch[1];
                        console.log('Extracted audit ID:', auditId);
                        // Add enhanced message with download buttons
                        const enhancedMessage = msg.message_content + `

<div style="margin-top: 12px; display: flex; gap: 8px;">
<button onclick="downloadAuditPDF('${auditId}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 8px 12px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📄 Download PDF</span></button>
<button onclick="downloadAuditJSON('${auditId}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 8px 12px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📊 Download JSON</span></button>
</div>`;
                        addMessageToChat(type, enhancedMessage, msg.created_at);
                    } else {
                        addMessageToChat(type, msg.message_content, msg.created_at);
                    }
                } else {
                    addMessageToChat(type, msg.message_content, msg.created_at);
                }
            });
        } else {
            // Show welcome message if no history
            if (welcomeMessage) welcomeMessage.style.display = 'flex';
        }
        
        // Check for latest audit and show PDF button if available
        // Only run this after successful chat history load
        await checkLatestAuditButton();
        
        // Also fix any existing broken PDF buttons
        await fixBrokenPDFButtons();
    } catch (error) {
        console.error('Failed to load chat history:', error);
        // Hide skeleton and show welcome message on error
        const chatSkeleton = document.getElementById('chatSkeleton');
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (chatSkeleton) chatSkeleton.style.display = 'none';
        if (welcomeMessage) welcomeMessage.style.display = 'flex';
    }
}

// Chat with specific agent
function chatWithAgent(agentName) {
    if (agentName === 'kenji') {
        addMessageToChat('ai', "Hi! I'm Kenji, your keyword specialist. I can help you find untapped keyword opportunities. What topics are you interested in ranking for?");
    }
}

// Coming soon message
function comingSoon() {
    alert('Myer agent is coming soon! For now, chat with Solvia or Kenji.');
}

// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('expanded');
}

function toggleAgents(element) {
    const sidebar = document.getElementById('sidebar');
    
    // Only work if sidebar is expanded
    if (!sidebar.classList.contains('expanded')) {
        return;
    }
    
    element.classList.toggle('expanded');
}

function selectAgent(agentName) {
    if (agentName === 'kenji') {
        addMessageToChat('ai', "Hi! I'm Kenji, your keyword specialist. I can help you find untapped keyword opportunities. What topics are you interested in ranking for?");
    } else if (agentName === 'myer') {
        addMessageToChat('ai', "Hi! I'm Myer, your metadata specialist. I can help optimize your meta titles, descriptions, and structured data. What would you like to improve?");
    }
}

// Logout functionality
async function logout() {
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        // Clear stored token
        localStorage.removeItem('auth_token');
        
        // Redirect to login regardless of response
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        // Still redirect to login on error
        window.location.href = '/login';
    }
}

// Send chat message function (called from HTML button)
function sendChatMessage() {
    sendMessage();
}

// Send suggestion function 
function sendSuggestion(suggestion) {
    document.getElementById('chatInput').value = suggestion;
    sendMessage();
}

// Display action buttons from API response
function displayActionButtons(buttons) {
    const suggestionsContainer = document.querySelector('.chat-suggestions');
    if (!suggestionsContainer) return;
    
    // Clear existing suggestions
    suggestionsContainer.innerHTML = '';
    
    // Add new buttons
    buttons.forEach(buttonText => {
        const btn = document.createElement('button');
        btn.className = 'suggestion-btn';
        btn.textContent = buttonText;
        btn.onclick = () => sendSuggestion(buttonText);
        suggestionsContainer.appendChild(btn);
    });
}

// Run new audit function with modal
async function runNewAudit() {
    // Show the modal
    showAuditModal();
    
    // Also add to chat for context
    addMessageToChat('ai', 'Starting a comprehensive SEO audit for your website...');
    
    // Trigger audit with progress tracking
    await triggerAuditWithModal('User requested a new audit via button');
}

// Chat with specific agent
function chatWithAgent(agentName) {
    if (agentName === 'kenji') {
        addMessageToChat('ai', "Hi! I'm Kenji, your keyword specialist. I can help you find untapped keyword opportunities. What topics are you interested in ranking for?");
    }
}

// Show credentials error with re-authentication option
function showCredentialsError() {
    // Update the current issues section to show re-authentication needed
    const issuesContainer = document.getElementById('currentIssues');
    if (issuesContainer) {
        issuesContainer.innerHTML = `
            <div class="issue-card critical">
                <div class="issue-header">
                    <span class="issue-severity critical">Critical</span>
                    <h4>Google Search Console Access Lost</h4>
                </div>
                <p class="issue-description">Your Google Search Console credentials have expired. Please re-authenticate to continue accessing your SEO data.</p>
                <div class="issue-actions">
                    <button onclick="reauthorizeGoogle()" class="btn-primary" style="background: #4285f4;">
                        🔄 Re-authenticate with Google
                    </button>
                </div>
            </div>
        `;
    }
    
    // Also show a message in chat
    addMessageToChat('ai', '⚠️ I lost access to your Google Search Console data. This can happen when your authentication expires. Please click "Re-authenticate with Google" above to restore access and continue monitoring your SEO performance.');
}

// Trigger Google OAuth re-authorization
function reauthorizeGoogle() {
    const token = localStorage.getItem('auth_token');
    if (token) {
        // Generate state parameter with current token for seamless re-auth
        const state = btoa(JSON.stringify({ token, return_url: '/dashboard' }));
        window.location.href = `/auth/google/authorize?state=${encodeURIComponent(state)}`;
    } else {
        // No token, redirect to login
        window.location.href = '/login';
    }
}

// Load and display latest audit info in dashboard
async function loadLatestAuditInfo() {
    try {
        const token = localStorage.getItem('auth_token');
        console.log('Loading latest audit info...');
        
        const response = await fetch('/agent/history?limit=1', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            console.log('Failed to fetch latest audit info:', response.status);
            return;
        }
        
        const data = await response.json();
        console.log('Latest audit data:', data);
        
        // Handle both array and object responses
        const audits = Array.isArray(data) ? data : (data.audits || []);
        
        if (audits.length > 0) {
            const latestAudit = audits[0];
            console.log('Displaying latest audit card for:', latestAudit.audit_id);
            displayLatestAuditCard(latestAudit);
        } else {
            console.log('No audits found to display');
        }
    } catch (error) {
        console.error('Failed to load latest audit info:', error);
    }
}

// Display latest audit info inline with Overview header
function displayLatestAuditCard(audit) {
    // Update inline audit info in Overview header instead of creating a card
    const inlineAuditInfo = document.getElementById('inline-audit-info');
    const auditTimeSpan = document.getElementById('audit-time');
    
    if (inlineAuditInfo && auditTimeSpan && audit) {
        // Calculate time since audit
        const auditTime = getRelativeTime(audit.created_at || audit.updated_at);
        
        // Update the audit time
        auditTimeSpan.textContent = auditTime;
        
        // Store audit ID globally for download functions
        window.currentAuditId = audit.audit_id;
        
        // Show the inline audit info
        inlineAuditInfo.style.display = 'flex';
        inlineAuditInfo.style.alignItems = 'center';
    }
    
    // Remove any old audit card if it exists
    const oldCard = document.getElementById('latest-audit-info');
    if (oldCard) {
        oldCard.remove();
    }
}

// Toggle download dropdown menu
function toggleDownloadMenu(event) {
    event.stopPropagation();
    const menu = document.getElementById('download-menu');
    
    if (menu) {
        const isVisible = menu.style.display === 'block';
        menu.style.display = isVisible ? 'none' : 'block';
        
        // Rotate arrow icon
        const arrow = event.currentTarget.querySelector('svg');
        if (arrow) {
            arrow.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
        }
        
        // Close menu when clicking outside
        if (!isVisible) {
            document.addEventListener('click', closeDownloadMenu);
        } else {
            document.removeEventListener('click', closeDownloadMenu);
        }
    }
}

function closeDownloadMenu() {
    const menu = document.getElementById('download-menu');
    if (menu) {
        menu.style.display = 'none';
        // Reset arrow rotation
        const button = menu.previousElementSibling;
        if (button) {
            const arrow = button.querySelector('svg');
            if (arrow) {
                arrow.style.transform = 'rotate(0deg)';
            }
        }
    }
    document.removeEventListener('click', closeDownloadMenu);
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Show skeleton immediately while loading
        showIssuesSkeleton();
        
        await checkAuth();
        await loadDashboardData();
        await loadLatestAuditInfo();  // Load latest audit info
        setupEventListeners();
        loadChatHistory();
        
        // Show the page once loaded
        document.body.classList.add('loaded');
    } catch (error) {
        console.error('Dashboard initialization failed:', error);
    }
});

// Audit Progress Tracking with SSE
async function trackAuditProgress(auditId) {
    const token = localStorage.getItem('auth_token');
    const eventSource = new EventSource(`/agent/progress/stream/${auditId}?token=${token}`);
    
    return new Promise((resolve, reject) => {
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateProgressUI(data);
                
                // Check if completed
                if (data.stage === 'completed' || data.stage === 'error') {
                    eventSource.close();
                    hideAuditProgress();
                    
                    if (data.stage === 'completed') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message));
                    }
                }
            } catch (e) {
                console.error('Progress parsing error:', e);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            eventSource.close();
            hideAuditProgress();
            reject(error);
        };
    });
}

// Show audit progress modal
function showAuditProgress() {
    // Remove existing modal if any
    const existing = document.getElementById('auditProgressModal');
    if (existing) existing.remove();
    
    // Create progress modal
    const modal = document.createElement('div');
    modal.id = 'auditProgressModal';
    modal.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 32px;
        border-radius: 16px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        z-index: 1000;
        min-width: 400px;
        max-width: 500px;
    `;
    
    modal.innerHTML = `
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
            <div style="width: 48px; height: 48px; background: #FEF3E7; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EC6019" stroke-width="2">
                    <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
            </div>
            <div>
                <h3 style="margin: 0; font-size: 20px; font-weight: 600; color: #1F2937;">Analyzing Your Website</h3>
                <p style="margin: 4px 0 0 0; font-size: 14px; color: #6B7280;">This usually takes 30-60 seconds</p>
            </div>
        </div>
        
        <div style="margin-bottom: 20px;">
            <div style="background: #F3F4F6; border-radius: 8px; height: 8px; overflow: hidden;">
                <div id="progressBar" style="background: linear-gradient(90deg, #EC6019, #F59E0B); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                <span id="progressPercent" style="font-size: 14px; color: #EC6019; font-weight: 600;">0%</span>
                <span id="progressStage" style="font-size: 13px; color: #6B7280;">Initializing...</span>
            </div>
        </div>
        
        <div id="progressMessages" style="max-height: 200px; overflow-y: auto; padding: 16px; background: #F9FAFB; border-radius: 8px; font-size: 13px; color: #4B5563;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2">
                    <path d="M5 12l5 5L20 7"></path>
                </svg>
                <span>Starting audit process...</span>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add overlay
    const overlay = document.createElement('div');
    overlay.id = 'auditProgressOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 999;
    `;
    document.body.appendChild(overlay);
}

// Update progress UI
function updateProgressUI(data) {
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressStage = document.getElementById('progressStage');
    const progressMessages = document.getElementById('progressMessages');
    
    if (progressBar) progressBar.style.width = `${data.progress}%`;
    if (progressPercent) progressPercent.textContent = `${data.progress}%`;
    
    // Enhanced stage text for improved user experience
    const stageTexts = {
        'initializing': '🚀 Getting ready...',
        'fetching_gsc_data': '📊 Fetching search data...',
        'analyzing_metrics': '🤖 Enhanced AI analysis...',
        'detecting_issues': '🔍 Finding critical issues...',
        'generating_recommendations': '💡 Creating smart recommendations...',
        'creating_report': '📋 Generating comprehensive report...',
        'finalizing': '✨ Finishing up...',
        'completed': '✅ Complete!',
        'error': '❌ Error occurred'
    };
    
    if (progressStage) progressStage.textContent = stageTexts[data.stage] || data.stage;
    
    // Add message to log
    if (progressMessages && data.message) {
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-top: 8px;';
        
        const icon = data.stage === 'error' ? '❌' : '✅';
        messageDiv.innerHTML = `
            <span>${icon}</span>
            <span>${data.message}</span>
        `;
        
        progressMessages.appendChild(messageDiv);
        progressMessages.scrollTop = progressMessages.scrollHeight;
    }
}

// Hide audit progress modal
function hideAuditProgress() {
    const modal = document.getElementById('auditProgressModal');
    const overlay = document.getElementById('auditProgressOverlay');
    
    if (modal) modal.remove();
    if (overlay) overlay.remove();
}

// Utility functions
function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toLocaleString();
}

// ========================================
// NEW AUDIT MODAL FUNCTIONS
// ========================================

let currentAuditId = null;
let auditStartTime = null;
let backgroundAuditData = null;
let currentAuditProgress = {
    progress: 0,
    stage: 'initializing',
    message: 'Starting...',
    isRunning: false
};

// Time update interval
let timeUpdateInterval = null;

// Start updating time elapsed
function startTimeUpdate() {
    // Clear any existing interval
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
    }
    
    // Update every second
    timeUpdateInterval = setInterval(() => {
        if (auditStartTime && currentAuditProgress.isRunning) {
            const elapsed = Math.floor((Date.now() - auditStartTime) / 1000);
            const progressTime = document.getElementById('progressTime');
            if (progressTime) {
                progressTime.textContent = `${elapsed}s elapsed`;
            }
        } else {
            clearInterval(timeUpdateInterval);
        }
    }, 1000);
}

// Stop time update
function stopTimeUpdate() {
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
        timeUpdateInterval = null;
    }
}

// Show audit modal
function showAuditModal(isResuming = false) {
    const modal = document.getElementById('auditModal');
    if (modal) {
        modal.style.display = 'block';
        
        // If resuming from background, restore progress instead of resetting
        if (isResuming && currentAuditProgress.isRunning) {
            restoreModalProgress();
            startTimeUpdate(); // Resume time updates
        } else if (!isResuming) {
            // Only reset if we're starting a NEW audit (not resuming)
            auditStartTime = Date.now();
            resetModalProgress();
            startTimeUpdate(); // Start time updates
        }
    }
}

// Close audit modal
function closeAuditModal() {
    const modal = document.getElementById('auditModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal and run in background
function runAuditInBackground() {
    // Store current audit data
    backgroundAuditData = {
        id: currentAuditId,
        startTime: auditStartTime,
        isRunning: true
    };
    
    // IMPORTANT: Do NOT reset currentAuditProgress.isRunning
    // The audit continues in the background and we need to track it
    
    // Close modal
    closeAuditModal();
    
    // Add background audit indicator
    showBackgroundAuditIndicator();
    
    // Continue the audit process in background
    // The triggerAuditWithModal will complete and update results
}

// Download audit JSON
async function downloadAuditJSON(auditId) {
    try {
        console.log('Downloading JSON for audit:', auditId);
        
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
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seo_audit_${auditId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Failed to download JSON:', error);
        alert(`Failed to download JSON: ${error.message}`);
    }
}

// Reset modal progress
function resetModalProgress() {
    // Reset progress state
    currentAuditProgress = {
        progress: 0,
        stage: 'initializing',
        message: 'Starting...',
        isRunning: false
    };
    
    // Reset progress bar
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressTime = document.getElementById('progressTime');
    
    if (progressBar) progressBar.style.width = '0%';
    if (progressPercent) progressPercent.textContent = '0%';
    if (progressTime) progressTime.textContent = 'Starting...';
    
    // Reset all steps to pending
    const steps = document.querySelectorAll('.step');
    steps.forEach(step => {
        const status = step.querySelector('.step-status');
        if (status) {
            status.textContent = 'pending';
            status.className = 'step-status pending';
        }
    });
    
    // Hide view results button
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    if (viewResultsBtn) viewResultsBtn.style.display = 'none';
}

// Restore modal progress when reopening from background
function restoreModalProgress() {
    // Restore the saved progress state
    const { progress, stage, message } = currentAuditProgress;
    
    // Update progress bar
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressTime = document.getElementById('progressTime');
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    if (progressPercent) {
        progressPercent.textContent = `${progress}%`;
    }
    
    // Time elapsed is updated by interval, no need to update here
    
    // Update status messages
    const statusTitle = document.getElementById('auditStatusTitle');
    const statusMessage = document.getElementById('auditStatusMessage');
    
    const stageTitles = {
        'initializing': 'Starting audit...',
        'fetching_gsc_data': 'Connecting to Google Search Console...',
        'analyzing_metrics': 'Analyzing your SEO metrics...',
        'detecting_issues': 'Detecting critical issues...',
        'generating_recommendations': 'Creating smart recommendations...',
        'creating_report': 'Generating PDF report...',
        'completed': '✅ Audit completed successfully!'
    };
    
    if (statusTitle) {
        statusTitle.textContent = stageTitles[stage] || 'Processing...';
    }
    if (statusMessage) {
        statusMessage.textContent = message || 'Audit in progress...';
    }
    
    // Restore step statuses
    const stageOrder = ['initializing', 'fetching_gsc_data', 'analyzing_metrics', 'detecting_issues', 'generating_recommendations', 'creating_report', 'completed'];
    const currentIndex = stageOrder.indexOf(stage);
    
    stageOrder.forEach((stepStage, index) => {
        if (index < currentIndex) {
            updateStepStatus(stepStage, 'completed');
        } else if (index === currentIndex) {
            updateStepStatus(stepStage, 'running');
        } else {
            updateStepStatus(stepStage, 'pending');
        }
    });
}

// Update modal progress
function updateModalProgress(progress, stage, message) {
    // Save current progress state
    currentAuditProgress = {
        progress: progress,
        stage: stage,
        message: message,
        isRunning: true
    };
    
    // Update progress bar
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressTime = document.getElementById('progressTime');
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    if (progressPercent) {
        progressPercent.textContent = `${progress}%`;
    }
    
    // Time elapsed is updated by interval, no need to update here
    
    // Update status messages
    const statusTitle = document.getElementById('auditStatusTitle');
    const statusMessage = document.getElementById('auditStatusMessage');
    
    const stageTitles = {
        'initializing': 'Starting audit...',
        'fetching_gsc_data': 'Connecting to Google Search Console...',
        'analyzing_metrics': 'Analyzing your SEO metrics...',
        'detecting_issues': 'Detecting critical issues...',
        'generating_recommendations': 'Creating smart recommendations...',
        'creating_report': 'Generating PDF report...',
        'completed': '✅ Audit completed successfully!'
    };
    
    if (statusTitle) {
        statusTitle.textContent = stageTitles[stage] || 'Processing...';
    }
    if (statusMessage) {
        statusMessage.textContent = message || 'Please wait while we analyze your website...';
    }
    
    // Update step status
    updateStepStatus(stage, 'running');
    
    // Mark previous steps as completed
    const stageOrder = ['initializing', 'fetching_gsc_data', 'analyzing_metrics', 'detecting_issues', 'generating_recommendations', 'creating_report', 'completed'];
    const currentIndex = stageOrder.indexOf(stage);
    
    stageOrder.forEach((stepStage, index) => {
        if (index < currentIndex) {
            updateStepStatus(stepStage, 'completed');
        }
    });
}

// Update step status
function updateStepStatus(stage, status) {
    const stepElement = document.getElementById(`step-${stage}`);
    if (stepElement) {
        const statusElement = stepElement.querySelector('.step-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `step-status ${status}`;
        }
    }
}

// Complete audit in modal
async function completeAuditModal(auditResult) {
    console.log('COMPLETE AUDIT MODAL DEBUG:', auditResult);
    console.log('Final Audit ID:', auditResult.audit_id);
    
    currentAuditId = auditResult.audit_id;
    
    // Update to completed state with 100% progress
    updateModalProgress(100, 'completed', `SEO Score: ${auditResult.seo_score}/100 - Found ${auditResult.issues_count.critical + auditResult.issues_count.high + auditResult.issues_count.medium} issues`);
    
    // Mark audit as no longer running
    currentAuditProgress.isRunning = false;
    
    // Mark completed step as completed
    updateStepStatus('completed', 'completed');
    
    // Replace spinner with checkmark
    const progressIcon = document.querySelector('.progress-icon');
    if (progressIcon) {
        progressIcon.innerHTML = '<div style="color: #10B981; font-size: 48px; animation: scaleIn 0.3s ease;">✓</div>';
    }
    
    // Stop time updates
    stopTimeUpdate();
    
    // Show view results button
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    if (viewResultsBtn) {
        viewResultsBtn.style.display = 'inline-block';
    }
    
    // Hide Run in Background button since audit is complete
    const runInBackgroundBtn = document.getElementById('runInBackgroundBtn');
    if (runInBackgroundBtn) {
        runInBackgroundBtn.style.display = 'none';
    }
    
    // Update final status
    const statusTitle = document.getElementById('auditStatusTitle');
    if (statusTitle) {
        statusTitle.textContent = '🎉 Audit completed successfully!';
    }
    
    // Refresh dashboard data to show updated metrics and issues
    await refreshDashboardAfterAudit();
    
    // Hide background indicator if it exists
    hideBackgroundAuditIndicator();
    
    // Refresh dashboard data with new audit results
    await refreshDashboardAfterAudit();
    
    // Add results to chat with PDF download button
    const issuesCount = auditResult.issues_count.critical + auditResult.issues_count.high + auditResult.issues_count.medium + auditResult.issues_count.low;
    const auditCompleteMessage = `✅ **Audit Complete!** 

**SEO Score: ${auditResult.seo_score}/100**
- Found ${issuesCount} issues (${auditResult.issues_count.critical} critical)
- Dashboard has been updated with latest results

Your audit ID: ${auditResult.audit_id}

<div style="margin-top: 12px; display: flex; gap: 8px;">
<button onclick="downloadAuditPDF('${auditResult.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; padding: 10px 16px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📄 Download PDF</span></button>
<button onclick="downloadAuditJSON('${auditResult.audit_id}')" style="background: white; color: #EC6019; border: 1px solid #EC6019; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; padding: 10px 16px; flex: 1; transition: all 0.2s;" onmouseover="this.style.background='#EC6019'; this.style.color='white';" onmouseout="this.style.background='white'; this.style.color='#EC6019';"><span>📊 Download JSON</span></button>
</div>`;
    
    addMessageToChat('ai', auditCompleteMessage);
}

// Download audit PDF
async function downloadAuditPDF(auditId) {
    try {
        console.log('Downloading PDF for audit:', auditId);
        
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
                console.error('Audit not found, getting latest audit...');
                alert('This audit report is no longer available. Please run a new audit.');
                // Remove all old download buttons
                const oldButtons = document.querySelectorAll('a[onclick*="downloadAuditPDF"]');
                oldButtons.forEach(button => button.style.display = 'none');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || errorData.message}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seo_audit_${auditId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Failed to download PDF:', error);
        alert('Failed to download PDF report. The audit might be outdated. Please run a new audit.');
    }
}

// Refresh dashboard after audit completion
async function refreshDashboardAfterAudit() {
    try {
        // Reload GSC metrics
        await loadDashboardData();
        
        // Reload current issues
        await loadCurrentIssues();
        
        // Load latest audit info with download buttons
        await loadLatestAuditInfo();
        
        console.log('Dashboard refreshed after audit completion');
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
    }
}

// View audit results
async function viewAuditResults() {
    if (currentAuditId) {
        // Close modal
        closeAuditModal();
        
        // Hide background indicator if present
        hideBackgroundAuditIndicator();
        
        // Refresh current issues with new audit data
        await loadCurrentIssues();
        
        // Scroll to issues section
        const issuesSection = document.getElementById('currentIssues');
        if (issuesSection) {
            issuesSection.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Show success message
        addMessageToChat('ai', `✅ Audit results are now displayed in the "Current Issues" section above. Your SEO score and priority issues have been updated with the latest data.`);
    }
}

// Load current issues from the API
async function loadCurrentIssues() {
    try {
        // Show skeleton for issues if not already shown
        showIssuesSkeleton();
        
        // Track start time for minimum skeleton display
        const startTime = Date.now();
        
        const token = localStorage.getItem('auth_token');
        const issuesResponse = await fetch('/agent/current-issues', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        // Ensure minimum display time (800ms for issues - usually slower)
        const elapsedTime = Date.now() - startTime;
        const minimumDisplayTime = 800; // milliseconds
        if (elapsedTime < minimumDisplayTime) {
            await new Promise(resolve => setTimeout(resolve, minimumDisplayTime - elapsedTime));
        }
        
        if (issuesResponse.ok) {
            const issues = await issuesResponse.json();
            updateCurrentIssues(issues);
            // Hide skeleton is already called inside updateCurrentIssues
        } else {
            console.error('Failed to load current issues:', issuesResponse.status);
            hideIssuesSkeleton(); // Hide skeleton on error
        }
    } catch (error) {
        console.error('Error loading current issues:', error);
        hideIssuesSkeleton(); // Hide skeleton on error
    }
}

// Enhanced trigger audit with modal progress
async function triggerAuditWithModal(prompt) {
    try {
        const token = localStorage.getItem('auth_token');
        
        // Mark audit as running
        currentAuditProgress.isRunning = true;
        
        // Start progress simulation and API call concurrently
        const progressPromise = simulateAuditProgress();
        
        const apiPromise = fetch('/agent/trigger-audit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                prompt,
                website_url: selectedWebsite || window.location.hostname,
                date_range_days: 30,
                report_format: 'both',
                delivery_method: 'email',
                include_recommendations: true
            })
        }).then(async (response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        });
        
        // Wait for both to complete
        const [_, result] = await Promise.all([progressPromise, apiPromise]);
        
        // Complete the modal with 100% progress
        await completeAuditModal(result);
        
        return result;
        
    } catch (error) {
        console.error('Failed to trigger audit:', error);
        
        // Mark audit as no longer running on error
        currentAuditProgress.isRunning = false;
        
        // Show error in modal
        const statusTitle = document.getElementById('auditStatusTitle');
        const statusMessage = document.getElementById('auditStatusMessage');
        
        if (statusTitle) statusTitle.textContent = '❌ Audit failed';
        if (statusMessage) statusMessage.textContent = error.message || 'An error occurred during the audit';
        
        // Hide background indicator on error
        hideBackgroundAuditIndicator();
        
        addMessageToChat('ai', `❌ Audit failed: ${error.message || 'Please try again later.'}`);
        
        throw error;
    }
}

// Simulate audit progress for better UX
async function simulateAuditProgress() {
    const stages = [
        { stage: 'initializing', progress: 10, delay: 500, message: 'Preparing audit engine...' },
        { stage: 'fetching_gsc_data', progress: 25, delay: 2000, message: 'Retrieving search console data...' },
        { stage: 'analyzing_metrics', progress: 50, delay: 3000, message: 'Running AI analysis...' },
        { stage: 'detecting_issues', progress: 70, delay: 4000, message: 'Identifying critical issues...' },
        { stage: 'generating_recommendations', progress: 85, delay: 2000, message: 'Creating recommendations...' },
        { stage: 'creating_report', progress: 95, delay: 1000, message: 'Generating PDF report...' }
    ];
    
    for (const stageData of stages) {
        updateModalProgress(stageData.progress, stageData.stage, stageData.message);
        await new Promise(resolve => setTimeout(resolve, stageData.delay));
    }
}

// Click outside modal to close
document.addEventListener('click', (event) => {
    const modal = document.getElementById('auditModal');
    if (event.target === modal) {
        closeAuditModal();
    }
});

// ESC key to close modal
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeAuditModal();
    }
});

// Show background audit indicator
function showBackgroundAuditIndicator() {
    // Remove existing indicator
    const existingIndicator = document.getElementById('backgroundAuditIndicator');
    if (existingIndicator) existingIndicator.remove();
    
    // Create floating indicator
    const indicator = document.createElement('div');
    indicator.id = 'backgroundAuditIndicator';
    indicator.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
    `;
    
    indicator.innerHTML = `
        <div class="spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>
        <div>
            <div style="font-size: 14px; font-weight: 600; color: #1F2937;">Audit Running</div>
            <div style="font-size: 12px; color: #6B7280;">Click to view progress</div>
        </div>
    `;
    
    // Click to show modal again with current progress
    indicator.onclick = () => {
        showAuditModal(true); // Pass true to indicate resuming from background
    };
    
    document.body.appendChild(indicator);
}

// Hide background audit indicator
function hideBackgroundAuditIndicator() {
    const indicator = document.getElementById('backgroundAuditIndicator');
    if (indicator) indicator.remove();
    
    backgroundAuditData = null;
}

// Show metrics skeleton loading
function showMetricsSkeleton() {
    const skeleton = document.getElementById('metricsSkeleton');
    const realMetrics = document.getElementById('realMetrics');
    
    if (skeleton) {
        skeleton.classList.remove('hidden');
    }
    if (realMetrics) {
        realMetrics.classList.add('hidden');
    }
}

// Hide metrics skeleton and show real data
function hideMetricsSkeleton() {
    const skeleton = document.getElementById('metricsSkeleton');
    const realMetrics = document.getElementById('realMetrics');
    
    if (skeleton) {
        skeleton.classList.add('hidden');
    }
    if (realMetrics) {
        realMetrics.classList.remove('hidden');
    }
}

// Add a delay for testing skeleton loading (optional - for demo purposes)
function simulateLoadingDelay(ms = 1500) {
    return new Promise(resolve => setTimeout(resolve, ms));
}