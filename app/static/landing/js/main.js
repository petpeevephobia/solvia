/**
 * Solvia Landing Page JavaScript
 * Clean, modular, and performant
 */

class SolviaLanding {
    constructor() {
        this.modal = null;
        this.bookCallButtons = [];
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.setupModal();
        this.setupBookCallButtons();
        this.setupSmoothScrolling();
        this.setupAnimations();
        this.setupFormHandling();
    }

    /**
     * Modal functionality
     */
    setupModal() {
        this.modal = document.getElementById('book-call-modal');
        if (!this.modal) return;

        const closeBtn = this.modal.querySelector('.modal-close');

        // Close modal events
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }

        // Close on backdrop click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('active')) {
                this.closeModal();
            }
        });
    }

    /**
     * Book call button functionality
     */
    setupBookCallButtons() {
        // Find all book call buttons/links
        this.bookCallButtons = document.querySelectorAll('a[href="#book-call"], .btn[href="#book-call"]');

        this.bookCallButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openModal();
            });
        });
    }

    /**
     * Smooth scrolling for anchor links
     */
    setupSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]:not([href="#book-call"])').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);

                if (target) {
                    const headerHeight = document.querySelector('.header')?.offsetHeight || 0;
                    const targetPosition = target.offsetTop - headerHeight - 20;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    /**
     * Scroll-based animations
     */
    setupAnimations() {
        // Intersection Observer for fade-in animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Animate elements on scroll
        const animateElements = document.querySelectorAll('.service-card, .usp-card, .testimonial-content');
        animateElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
            observer.observe(el);
        });

        // Parallax effect for hero section
        this.setupParallax();
    }

    /**
     * Subtle parallax effect
     */
    setupParallax() {
        const heroSection = document.querySelector('.hero');
        if (!heroSection) return;

        let ticking = false;

        const updateParallax = () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;

            heroSection.style.transform = `translateY(${rate}px)`;
            ticking = false;
        };

        const requestParallax = () => {
            if (!ticking) {
                requestAnimationFrame(updateParallax);
                ticking = true;
            }
        };

        window.addEventListener('scroll', requestParallax);
    }

    /**
     * Form handling
     */
    setupFormHandling() {
        const form = document.querySelector('.book-call-form');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmission(form);
        });

        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateInput(input));
            input.addEventListener('input', () => this.clearInputError(input));
        });
    }

    /**
     * Input validation
     */
    validateInput(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Remove previous error styling
        this.clearInputError(input);

        // Required field validation
        if (!value) {
            isValid = false;
            errorMessage = 'This field is required';
        }

        // Email validation
        if (input.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }

        // Show error if invalid
        if (!isValid) {
            this.showInputError(input, errorMessage);
        }

        return isValid;
    }

    /**
     * Show input error
     */
    showInputError(input, message) {
        input.style.borderColor = '#ef4444';
        input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';

        // Create or update error message
        let errorDiv = input.parentNode.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = `
                color: #ef4444;
                font-size: 0.875rem;
                margin-top: 0.25rem;
                display: block;
            `;
            input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    /**
     * Clear input error
     */
    clearInputError(input) {
        input.style.borderColor = '';
        input.style.boxShadow = '';

        const errorDiv = input.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    /**
     * Handle form submission
     */
    async handleFormSubmission(form) {
        const inputs = form.querySelectorAll('input, textarea');
        let isFormValid = true;

        // Validate all inputs
        inputs.forEach(input => {
            if (!this.validateInput(input)) {
                isFormValid = false;
            }
        });

        if (!isFormValid) {
            this.showNotification('Please fix the errors above', 'error');
            return;
        }

        // Collect form data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Sending...';
        submitBtn.disabled = true;

        try {
            // Simulate API call (replace with actual endpoint)
            await this.submitFormData(data);

            this.showNotification('Thank you! We\'ll be in touch soon.', 'success');
            form.reset();
            this.closeModal();

        } catch (error) {
            console.error('Form submission error:', error);
            this.showNotification('Something went wrong. Please try again.', 'error');
        } finally {
            // Restore button state
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    /**
     * Submit form data (replace with actual API call)
     */
    async submitFormData(data) {
        // This would typically be a fetch call to your backend
        return new Promise((resolve) => {
            setTimeout(() => {
                console.log('Form data:', data);
                resolve();
            }, 1000);
        });
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1001;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            color: white;
            font-weight: 500;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            transform: translateX(100%);
            transition: transform 0.3s ease-out;
            max-width: 300px;
        `;

        // Set color based on type
        if (type === 'success') {
            notification.style.backgroundColor = '#10b981';
        } else if (type === 'error') {
            notification.style.backgroundColor = '#ef4444';
        } else {
            notification.style.backgroundColor = '#3b82f6';
        }

        notification.textContent = message;
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Open modal
     */
    openModal() {
        if (this.modal) {
            this.modal.classList.add('active');
            document.body.style.overflow = 'hidden';

            // Focus first input
            const firstInput = this.modal.querySelector('input');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    }

    /**
     * Close modal
     */
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('active');
            document.body.style.overflow = '';

            // Clear form
            const form = this.modal.querySelector('form');
            if (form) {
                form.reset();
                // Clear any error states
                const inputs = form.querySelectorAll('input, textarea');
                inputs.forEach(input => this.clearInputError(input));
            }
        }
    }

    /**
     * Utility method for debouncing
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize when DOM is ready
new SolviaLanding();

// Export for potential testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SolviaLanding;
}