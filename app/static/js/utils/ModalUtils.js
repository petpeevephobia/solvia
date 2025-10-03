/**
 * Global Modal Utility
 * Beautiful modal component to replace browser alerts
 */

class ModalUtils {
    /**
     * Show a modal with custom options
     * @param {Object} options - Modal configuration
     * @param {string} options.title - Modal title
     * @param {string} options.message - Modal message
     * @param {string} options.type - Modal type: 'success', 'error', 'warning', 'info'
     * @param {string} options.buttonText - Button text (default: 'OK')
     * @param {Function} options.onClose - Callback when modal closes
     */
    static show(options = {}) {
        const {
            title = 'Success',
            message = '',
            type = 'success',
            buttonText = 'OK',
            onClose = null
        } = options;

        const modal = document.getElementById('globalModal');
        const modalIcon = document.getElementById('globalModalIcon');
        const modalTitle = document.getElementById('globalModalTitle');
        const modalMessage = document.getElementById('globalModalMessage');
        const modalBtn = document.getElementById('globalModalBtn');

        if (!modal) {
            console.error('Global modal not found');
            return;
        }

        // Set icon based on type
        const icons = {
            success: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>`,
            error: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>`,
            warning: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>`,
            info: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`
        };

        // Update modal content
        modalIcon.innerHTML = icons[type] || icons.info;
        modalIcon.className = `global-modal-icon ${type}`;
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalBtn.textContent = buttonText;

        // Store callback
        modal._onCloseCallback = onClose;

        // Show modal
        modal.classList.add('show');

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close the modal
     */
    static close() {
        const modal = document.getElementById('globalModal');
        if (!modal) return;

        // Hide modal
        modal.classList.remove('show');

        // Restore body scroll
        document.body.style.overflow = '';

        // Execute callback if exists
        if (typeof modal._onCloseCallback === 'function') {
            modal._onCloseCallback();
            modal._onCloseCallback = null;
        }
    }

    /**
     * Show success modal
     */
    static success(message, options = {}) {
        this.show({
            title: options.title || 'Success',
            message,
            type: 'success',
            ...options
        });
    }

    /**
     * Show error modal
     */
    static error(message, options = {}) {
        this.show({
            title: options.title || 'Error',
            message,
            type: 'error',
            ...options
        });
    }

    /**
     * Show warning modal
     */
    static warning(message, options = {}) {
        this.show({
            title: options.title || 'Warning',
            message,
            type: 'warning',
            ...options
        });
    }

    /**
     * Show info modal
     */
    static info(message, options = {}) {
        this.show({
            title: options.title || 'Information',
            message,
            type: 'info',
            ...options
        });
    }
}

// Global function for closing modal (used in onclick attribute)
function closeGlobalModal() {
    ModalUtils.close();
}

// Make ModalUtils globally accessible
window.ModalUtils = ModalUtils;
