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

export class ChatUtils {
    static handleChatKeypress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendChatMessage();
        }
    }

    static sendSuggestion(suggestion) {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = suggestion;
            sendChatMessage();
        }
    }

    static getRandomSuggestions(excludeText = null) {
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

        let available = suggestionPool.filter(s => s !== excludeText);
        let shuffled = available.sort(() => Math.random() - 0.5);
        return shuffled.slice(0, 4);
    }

    static sendSuggestionWithRotation(text) {
        // Send the suggestion
        ChatUtils.sendSuggestion(text);

        // Rotate to new random suggestions after a short delay
        setTimeout(() => {
            ChatUtils.updateSuggestionButtons(ChatUtils.getRandomSuggestions(text));
        }, 100);
    }

    static updateSuggestionButtons(actionButtons, hideForAudit = false) {
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
            suggestions = ChatUtils.getRandomSuggestions();
            console.log('🎲 Using random suggestions:', suggestions);
        }

        // Generate suggestion buttons HTML
        const suggestionsHtml = suggestions.map(suggestion =>
            `<button class="suggestion-btn" onclick="sendSuggestionWithRotation('${suggestion.replace(/'/g, "\\'")}')">${suggestion}</button>`
        ).join('');

        // Update the suggestions container
        suggestionsContainer.innerHTML = suggestionsHtml;
    }
}

export class ChatService {
    static async sendChatMessage() {
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
                    setTimeout(async () => {
                        if (window.solviaRouter) {
                            console.log('🔄 Refreshing dashboard after chat audit...');
                            // Refresh both metrics and issues to ensure consistency
                            await window.solviaRouter.loadDashboardMetrics();
                            await window.solviaRouter.loadCurrentIssues();
                            console.log('✅ Dashboard refresh complete - both metrics and issues updated');
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
}

export class AuditService {
    // Helper function to show audit success modal
    static showAuditSuccessModal() {
        console.log('🎊 Showing success modal...');

        const successToast = document.createElement('div');
        successToast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 60000;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white; padding: 16px 20px; border-radius: 12px;
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
            max-width: 350px; transform: translateX(400px);
            transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        successToast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 24px;">✅</div>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Audit Complete</div>
                    <div style="font-size: 13px; opacity: 0.9;">Your website audit has been completed successfully.</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()"
                        style="background: none; border: none; color: white; opacity: 0.7; cursor: pointer; padding: 4px; margin-left: auto;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(successToast);

        // Show toast with slide-in animation
        setTimeout(() => successToast.style.transform = 'translateX(0)', 100);

        // Auto-hide after 5 seconds
        setTimeout(() => {
            successToast.style.transform = 'translateX(400px)';
            setTimeout(() => successToast.remove(), 400);
        }, 5000);
    }

    // Helper function to cleanup audit UI
    static cleanupAuditUI(auditBtn) {
        console.log('🧹 Cleaning up audit UI...');

        // Remove progress overlay
        const overlay = document.getElementById('auditProgressOverlay');
        if (overlay) {
            overlay.style.transform = 'translateY(-100%)';
            setTimeout(() => overlay.style.display = 'none', 400);
        }

        // Remove background indicator (if it exists - currently disabled)
        const backgroundIndicator = document.getElementById('auditBackgroundIndicator');
        if (backgroundIndicator) {
            backgroundIndicator.style.transform = 'translateX(300px)';
            setTimeout(() => backgroundIndicator.remove(), 400);
        }

        // Re-enable audit button
        if (auditBtn) {
            auditBtn.disabled = false;
            auditBtn.textContent = 'Run a new audit';
        }
    }

    static async triggerAudit() {
        console.log('🚀 Starting audit trigger...');
        const startTime = Date.now();
        const steps = [
            { id: 'initializing', progress: 15, message: 'Initializing audit engine...' },
            { id: 'fetching', progress: 30, message: 'Fetching GSC data...' },
            { id: 'analyzing', progress: 50, message: 'Analyzing with AI...' },
            { id: 'detecting', progress: 70, message: 'Detecting issues...' },
            { id: 'recommendations', progress: 85, message: 'Generating recommendations...' },
            { id: 'processing', progress: 90, message: 'Processing final results...' }
            // Note: Removed 100% step - only show 100% after API confirms success
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
                setTimeout(() => overlay.style.transform = 'translateY(0)', 10);

                // Update progress elements
                const progressBar = overlay.querySelector('.progress-bar');
                const progressText = overlay.querySelector('.progress-text');
                const progressPercent = overlay.querySelector('.progress-percent');

                if (progressBar) {
                    progressBar.style.setProperty('width', `${progress}%`, 'important');
                }

                if (progressText) {
                    progressText.textContent = message;
                }

                if (progressPercent) {
                    progressPercent.textContent = `${progress}%`;
                }

                // Update step statuses correctly - mark completed steps as completed, current as processing, rest as pending
                const allStepStatuses = overlay.querySelectorAll('[data-step]');
                const currentStepIndex = steps.findIndex(step => step.id === stepId);

                allStepStatuses.forEach((stepElement, index) => {
                    const stepData = steps[index];
                    if (!stepData) return;

                    if (index < currentStepIndex) {
                        // Previous steps are completed
                        stepElement.textContent = 'COMPLETED';
                        stepElement.className = 'step-status completed';
                    } else if (index === currentStepIndex) {
                        // Current step is processing
                        stepElement.textContent = 'PROCESSING';
                        stepElement.className = 'step-status processing';
                    } else {
                        // Future steps are pending
                        stepElement.textContent = 'PENDING';
                        stepElement.className = 'step-status pending';
                    }
                });

                console.log(`📊 Progress overlay updated: ${progress}% (Step ${currentStepIndex + 1}/${steps.length})`);
            }

            // ===== BACKGROUND INDICATOR DISABLED =====
            // Since we now have a working top progress bar, disable the duplicate right notification
            // to avoid confusion and duplicate progress indicators
            console.log(`📊 Background indicator disabled (using top progress bar instead)`);

            // ===== UPDATE TOP PROGRESS BAR =====
            // Update the top progress bar elements that were missing
            const topProgressPercent = document.getElementById('auditProgressPercent');
            const topProgressTitle = document.getElementById('auditProgressTitle');
            const topTimeEstimate = document.getElementById('auditTimeEstimate');
            const topProgressFill = document.getElementById('auditProgressFill');
            const topProgressText = document.getElementById('auditProgressText');

            if (topProgressPercent) {
                topProgressPercent.textContent = `${progress}%`;
                console.log(`📊 Top progress percent updated: ${progress}%`);
            }

            if (topProgressTitle) {
                // Update title based on progress
                if (progress >= 100) {
                    topProgressTitle.textContent = 'Audit Complete!';
                } else if (progress >= 90) {
                    topProgressTitle.textContent = 'Almost Complete';
                } else if (progress >= 70) {
                    topProgressTitle.textContent = 'Finalizing Results';
                } else if (progress >= 40) {
                    topProgressTitle.textContent = 'Analyzing Data';
                } else {
                    topProgressTitle.textContent = 'Running SEO Audit';
                }
            }

            if (topTimeEstimate && progress < 100) {
                // Calculate estimated time remaining based on progress
                const remainingPercent = 100 - progress;
                const estimatedSeconds = Math.max(10, Math.round(remainingPercent * 0.6));
                topTimeEstimate.textContent = `~${estimatedSeconds}s remaining`;
            } else if (topTimeEstimate && progress >= 100) {
                topTimeEstimate.textContent = 'Complete!';
            }

            // Update the visual progress bar fill
            if (topProgressFill) {
                topProgressFill.style.width = `${progress}%`;
                console.log(`📊 Top progress fill updated: ${progress}%`);
            }

            // Update the progress message text
            if (topProgressText) {
                topProgressText.textContent = message;
                console.log(`📊 Top progress text updated: ${message}`);
            }

            console.log(`📊 Top progress bar elements updated`);
        };

        // ===== START AUDIT PROCESS =====
        console.log('🔥 Starting enhanced audit process...');

        // Disable audit button immediately
        const auditBtn = document.getElementById('auditBtn');
        if (auditBtn) {
            auditBtn.disabled = true;
            auditBtn.textContent = 'Running audit...';
        }

        // Start progress simulation
        progressInterval = setInterval(() => {
            if (currentStepIndex < steps.length) {
                const step = steps[currentStepIndex];
                updateProgress(step.id, step.progress, step.message);
                currentStepIndex++;
            } else {
                clearInterval(progressInterval);
                progressInterval = null;
            }
        }, 800); // Progress every 800ms

        try {
            // Start 32-second timeout
            auditTimeoutId = setTimeout(handleAuditTimeout, 32000);

            const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
            const response = await fetch('/agent/trigger-audit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    force_refresh: false,
                    include_recommendations: true,
                    date_range_days: 30
                })
            });

            // Clear timeout on response (success or error)
            if (auditTimeoutId) {
                clearTimeout(auditTimeoutId);
                auditTimeoutId = null;
                console.log('✅ Audit timeout cleared on response');
            }

            // Clear progress interval
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Audit API response:', data);

                // Smart progress completion based on actual status
                const auditStatus = data.status || 'unknown';
                const auditId = data.id || data.audit_id;

                // The trigger-audit endpoint runs synchronously and returns 'completed'
                // when the audit is done. No need to poll in that case.
                if (auditStatus === 'completed' || auditStatus === 'success') {
                    // Mark all steps as completed when audit finishes
                    const overlay = document.getElementById('auditProgressOverlay');
                    if (overlay) {
                        const allStepStatuses = overlay.querySelectorAll('[data-step]');
                        allStepStatuses.forEach(stepElement => {
                            stepElement.textContent = 'COMPLETED';
                            stepElement.className = 'step-status completed';
                        });
                    }

                    updateProgress('completed', 100, 'Audit completed!');
                    console.log('🎉 Audit fully completed!');

                    // Show success modal immediately for completed audits
                    setTimeout(() => {
                        AuditService.cleanupAuditUI(auditBtn);
                        AuditService.showAuditSuccessModal();

                        // Refresh dashboard after 2 seconds with targeted updates
                        setTimeout(async () => {
                            if (window.solviaRouter) {
                                console.log('🔄 Refreshing dashboard after audit completion...');
                                // Refresh both metrics and issues to ensure consistency
                                await window.solviaRouter.loadDashboardMetrics();
                                await window.solviaRouter.loadCurrentIssues();
                                console.log('✅ Dashboard refresh complete - both metrics and issues updated');
                            }
                        }, 2000);
                    }, 1000);

                    // Exit early, no need to run the cleanup code below
                    const endTime = Date.now();
                    const duration = (endTime - startTime) / 1000;
                    console.log(`⏱️ Total audit time: ${duration.toFixed(1)}s`);
                    return;

                } else if (auditStatus === 'pending' || auditStatus === 'processing') {
                    // Keep at 90% for pending/processing status
                    updateProgress('processing', 90, 'Audit in progress, please wait...');
                    console.log('⏳ Audit still processing, staying at 90%');

                    // Poll for completion status
                    let pollCount = 0;
                    const maxPolls = 30; // Max 30 polls (60 seconds)

                    const pollInterval = setInterval(async () => {
                        pollCount++;
                        console.log(`🔄 Polling audit status (attempt ${pollCount}/${maxPolls})...`);

                        try {
                            const checkResponse = await fetch(`/agent/progress/status/${auditId}`, {
                                headers: {
                                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                                    'X-Email': email
                                }
                            });

                            if (checkResponse.ok) {
                                const statusData = await checkResponse.json();
                                console.log('📊 Audit status check:', statusData);

                                if (statusData.status === 'completed' || statusData.status === 'success') {
                                    clearInterval(pollInterval);

                                    // Mark all steps as completed when audit finishes
                                    const overlay = document.getElementById('auditProgressOverlay');
                                    if (overlay) {
                                        const allStepStatuses = overlay.querySelectorAll('[data-step]');
                                        allStepStatuses.forEach(stepElement => {
                                            stepElement.textContent = 'COMPLETED';
                                            stepElement.className = 'step-status completed';
                                        });
                                    }

                                    // Update to 100% completion
                                    updateProgress('completed', 100, 'Audit completed!');
                                    console.log('🎉 Audit completed after polling!');

                                    // Show success modal after completion
                                    setTimeout(() => {
                                        AuditService.showAuditSuccessModal();
                                        AuditService.cleanupAuditUI(auditBtn);

                                        // Refresh dashboard after 2 seconds with targeted updates
                                        setTimeout(async () => {
                                            if (window.solviaRouter) {
                                                console.log('🔄 Refreshing dashboard after audit completion...');
                                                // Refresh both metrics and issues to ensure consistency
                                                await window.solviaRouter.loadDashboardMetrics();
                                                await window.solviaRouter.loadCurrentIssues();
                                                console.log('✅ Dashboard refresh complete - both metrics and issues updated');
                                            }
                                        }, 2000);
                                    }, 1000);

                                } else if (statusData.status === 'failed' || statusData.status === 'error') {
                                    clearInterval(pollInterval);
                                    console.error('❌ Audit failed:', statusData.message || 'Unknown error');
                                    AuditService.cleanupAuditUI(auditBtn);
                                }
                            }
                        } catch (error) {
                            console.error('❌ Error polling audit status:', error);
                        }

                        // Stop polling after max attempts
                        if (pollCount >= maxPolls) {
                            clearInterval(pollInterval);
                            console.warn('⚠️ Audit status polling timeout');
                            AuditService.cleanupAuditUI(auditBtn);
                        }
                    }, 2000); // Poll every 2 seconds

                    // Don't clean up UI yet, audit is still running
                    return;
                } else {
                    // Mark all steps as completed for unknown status
                    const overlay = document.getElementById('auditProgressOverlay');
                    if (overlay) {
                        const allStepStatuses = overlay.querySelectorAll('[data-step]');
                        allStepStatuses.forEach(stepElement => {
                            stepElement.textContent = 'COMPLETED';
                            stepElement.className = 'step-status completed';
                        });
                    }

                    // Unknown status, treat as completed for backward compatibility
                    updateProgress('completed', 100, 'Audit completed!');
                    console.log('🔄 Unknown status, assuming completed:', auditStatus);

                    // Show success modal for unknown status (backward compatibility)
                    setTimeout(() => {
                        AuditService.cleanupAuditUI(auditBtn);
                        AuditService.showAuditSuccessModal();

                        // Refresh dashboard after 2 seconds with targeted updates
                        setTimeout(async () => {
                            if (window.solviaRouter) {
                                console.log('🔄 Refreshing dashboard after audit completion...');
                                // Refresh both metrics and issues to ensure consistency
                                await window.solviaRouter.loadDashboardMetrics();
                                await window.solviaRouter.loadCurrentIssues();
                                console.log('✅ Dashboard refresh complete - both metrics and issues updated');
                            }
                        }, 2000);
                    }, 1000);

                    const endTime = Date.now();
                    const duration = (endTime - startTime) / 1000;
                    console.log(`⏱️ Total audit time: ${duration.toFixed(1)}s`);
                }

            } else {
                console.error('❌ Audit trigger failed:', response.status, response.statusText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            console.error('❌ Audit trigger error:', error);

            // Clear timeout on error
            if (auditTimeoutId) {
                clearTimeout(auditTimeoutId);
                auditTimeoutId = null;
            }

            // Clear progress interval
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }

            // Clean up UI
            const overlay = document.getElementById('auditProgressOverlay');
            const backgroundIndicator = document.getElementById('auditBackgroundIndicator');

            if (backgroundIndicator) {
                backgroundIndicator.remove();
            } else if (overlay) {
                overlay.style.transform = 'translateY(-100%)';
                setTimeout(() => overlay.style.display = 'none', 400);
            }

            // Re-enable audit button
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
}

export class UIService {
    static async runNewAudit() {
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
                        <div class="message-text">Run a new audit</div>
                    </div>
                    <div class="message-avatar user">👤</div>
                </div>
            `;

            const messagesContainer = document.getElementById('chatMessages');
            if (messagesContainer) {
                messagesContainer.insertAdjacentHTML('beforeend', userMessageHtml);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        // Start the audit
        await triggerAudit();
    }

    static showAuditModal() {
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
                                    <span class="step-text">Creating report</span>
                                    <span class="step-status pending">pending</span>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button onclick="minimizeAuditProgress()" class="btn-secondary">Minimize</button>
                            <button onclick="closeAuditModal()" class="btn-secondary">Cancel</button>
                        </div>
                    </div>
                </div>
            `;

            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            modal = document.getElementById('auditModalSPA');
        }

        // Show modal
        modal.style.display = 'block';
        // Reset progress
        resetModalProgress();
    }

    static minimizeAuditProgress() {
        const modal = document.getElementById('auditModalSPA');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    static runAuditInBackground() {
        console.log('🔄 Running audit in background...');

        // Hide modal if visible
        const modal = document.getElementById('auditModalSPA');
        if (modal) {
            modal.style.display = 'none';
        }

        // Background indicator disabled - using top progress bar instead
        console.log('🚀 Background indicator disabled (using top progress bar)');
    }

    static hideSuccessToast() {
        const toast = document.getElementById('auditSuccessToast');
        if (toast) {
            toast.style.transform = 'translateX(400px)';
            setTimeout(() => toast.style.display = 'none', 400);
        }
    }
}

export class DownloadUtils {
    static async downloadAuditPDF(auditId) {
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

    static async downloadAuditJSON(auditId) {
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

    static closeDownloadMenu() {
        const menu = document.querySelector('[id*="download-menu"]');
        if (menu) {
            menu.style.display = 'none';
        }
    }

    static reauthorizeGoogle() {
        console.log('Reauthorizing Google credentials...');
        window.location.href = '/auth/google/authorize';
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
    ChatUtils,
    ChatService,
    AuditService,
    UIService,
    DownloadUtils,
    AuthUtils,
    UtilityFunctions
};