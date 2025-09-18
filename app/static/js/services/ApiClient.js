/**
 * ApiClient - Centralized API communication service
 * Handles all HTTP requests with auth, error handling, and retries
 */
import eventBus from '../core/EventBus.js';

export class ApiClient {
    constructor() {
        this.baseURL = '';
        this.token = localStorage.getItem('jwt_token');
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
        this.retryAttempts = 3;
        this.retryDelay = 1000;
    }

    /**
     * Set authentication token
     * @param {string} token - JWT token
     */
    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('jwt_token', token);
        } else {
            localStorage.removeItem('jwt_token');
        }
    }

    /**
     * Get authentication headers
     * @returns {Object} Headers object
     */
    getAuthHeaders() {
        const headers = { ...this.defaultHeaders };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    /**
     * Make HTTP request with retry logic
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @param {number} attempt - Current attempt number
     * @returns {Promise} Response promise
     */
    async request(url, options = {}, attempt = 1) {
        const config = {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            // Handle authentication errors
            if (response.status === 401) {
                eventBus.emit('auth:expired');
                throw new Error('Authentication expired');
            }

            // Handle rate limiting
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After') || 60;
                eventBus.emit('api:rate-limited', { retryAfter });
                throw new Error(`Rate limited. Retry after ${retryAfter} seconds`);
            }

            // Handle server errors with retry
            if (response.status >= 500 && attempt < this.retryAttempts) {
                await this.delay(this.retryDelay * attempt);
                return this.request(url, options, attempt + 1);
            }

            // Parse response
            const contentType = response.headers.get('content-type');
            let data;

            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw new ApiError(response.status, data.message || data.error || 'Request failed', data);
            }

            return data;

        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }

            // Network errors
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                throw new ApiError(0, 'Network error. Please check your connection.', null);
            }

            throw new ApiError(0, error.message, null);
        }
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @param {Object} params - Query parameters
     */
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });

        return this.request(url.toString(), {
            method: 'GET'
        });
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body
     */
    async post(endpoint, data = {}) {
        return this.request(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body
     */
    async put(endpoint, data = {}) {
        return this.request(`${this.baseURL}${endpoint}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     */
    async delete(endpoint) {
        return this.request(`${this.baseURL}${endpoint}`, {
            method: 'DELETE'
        });
    }

    /**
     * Upload file
     * @param {string} endpoint - API endpoint
     * @param {FormData} formData - Form data with file
     */
    async upload(endpoint, formData) {
        const headers = { ...this.getAuthHeaders() };
        delete headers['Content-Type']; // Let browser set boundary

        return this.request(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers,
            body: formData
        });
    }

    /**
     * Download file
     * @param {string} endpoint - API endpoint
     * @param {string} filename - Download filename
     */
    async download(endpoint, filename) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            headers: this.getAuthHeaders()
        });

        if (!response.ok) {
            throw new ApiError(response.status, 'Download failed', null);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    /**
     * Delay helper for retries
     * @param {number} ms - Milliseconds to delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
    constructor(status, message, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

// Export singleton instance
export default new ApiClient();