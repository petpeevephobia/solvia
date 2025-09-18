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

// Make available globally for spa-router.js to use
window.SolviaUtils = {
    ApiUtils,
    DomUtils,
    StorageUtils
};