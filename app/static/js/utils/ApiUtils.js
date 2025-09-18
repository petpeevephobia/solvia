/**
 * ApiUtils - Extracted utility functions from spa-router.js
 * These functions can be used by spa-router.js while maintaining compatibility
 */

export class ApiUtils {
    static async fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem('jwt_token');
        const defaultHeaders = {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };

        return fetch(url, {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        });
    }

    static async handleApiResponse(response) {
        if (!response.ok) {
            if (response.status === 401) {
                // Auth expired
                localStorage.removeItem('jwt_token');
                window.location.href = '/';
                throw new Error('Authentication expired');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Request failed');
        }
        return response.json();
    }

    static async makeApiCall(url, options = {}) {
        try {
            const response = await this.fetchWithAuth(url, options);
            return await this.handleApiResponse(response);
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

export class DomUtils {
    static showElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'block';
            element.classList.remove('hidden');
        }
    }

    static hideElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
            element.classList.add('hidden');
        }
    }

    static toggleElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            if (element.style.display === 'none' || element.classList.contains('hidden')) {
                this.showElement(elementId);
            } else {
                this.hideElement(elementId);
            }
        }
    }

    static updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    static updateElementHtml(elementId, html) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = html;
        }
    }
}

export class StorageUtils {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
        }
    }

    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to read from localStorage:', error);
            return defaultValue;
        }
    }

    static remove(key) {
        localStorage.removeItem(key);
    }

    static clear() {
        localStorage.clear();
    }
}

export class TextUtils {
    static formatAuditResponse(message) {
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

    static convertMarkdownToHTML(markdown) {
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
}

export class AuthUtils {
    static async logout() {
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

    static async saveWebsiteSelection() {
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
}

export class UtilityFunctions {
    static toggleSidebar() {
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

    static toggleIssueDescription(cardId) {
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

    static minimizeAuditProgress() {
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

    static showElement(selector) {
        const element = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (element) {
            element.style.display = 'block';
            element.classList.remove('hidden');
        }
    }

    static hideElement(selector) {
        const element = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (element) {
            element.style.display = 'none';
            element.classList.add('hidden');
        }
    }

    static async saveWebsiteSelection() {
        const websiteSelect = document.getElementById('websiteSelect');
        if (websiteSelect && websiteSelect.value) {
            try {
                StorageUtils.set('selectedWebsite', websiteSelect.value);
                // Trigger refresh of dashboard data
                if (window.location.hash === '#dashboard' || !window.location.hash) {
                    window.location.reload();
                }
            } catch (error) {
                console.error('Error saving website selection:', error);
            }
        }
    }

    static hideSuccessToast() {
        const toast = document.getElementById('auditSuccessToast');
        if (toast) {
            toast.style.transform = 'translateX(400px)';
            setTimeout(() => toast.style.display = 'none', 400);
        }
    }

    static resetModalProgress() {
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

    static closeAuditModal() {
        const modal = document.getElementById('auditModalSPA');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    static viewAuditResults() {
        console.log('Viewing audit results...');
        UtilityFunctions.closeAuditModal();
        // Refresh dashboard to show new results
        if (window.solviaRouter) {
            window.solviaRouter.navigateTo('dashboard');
        }
    }
}

// Make available globally for spa-router.js to use
window.SolviaUtils = {
    ApiUtils,
    DomUtils,
    StorageUtils,
    TextUtils,
    AuthUtils,
    UtilityFunctions
};