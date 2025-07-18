let currentUser = null;

function switchTab(tab) {
    // Update tabs
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    // Update forms
    document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
    if (tab === 'register') {
        document.getElementById('registerForm').classList.add('active');
    } else {
        document.getElementById('loginForm').classList.add('active');
    }

    // Clear alerts
    clearAlerts();
}

function showAlert(alertId, message, type = 'info') {
    const alertDiv = document.getElementById(alertId);
    if (!alertDiv) return;

    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.classList.remove('hidden');

    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.classList.add('hidden');
    }, 5000);
}

function clearAlerts() {
    document.getElementById('registerAlert').classList.add('hidden');
    document.getElementById('loginAlert').classList.add('hidden');
}

function setLoading(buttonId, isLoading) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    if (isLoading) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span>';
    } else {
        btn.disabled = false;
        // Restore original text
        if (buttonId === 'registerBtn') {
            btn.innerHTML = 'Register';
        } else if (buttonId === 'loginBtn') {
            btn.innerHTML = 'Login';
        }
    }
}

function validatePassword(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password)
    };

    // Update requirement indicators
    document.getElementById('req-length').className = `requirement ${requirements.length ? 'met' : 'not-met'}`;
    document.getElementById('req-uppercase').className = `requirement ${requirements.uppercase ? 'met' : 'not-met'}`;
    document.getElementById('req-lowercase').className = `requirement ${requirements.lowercase ? 'met' : 'not-met'}`;
    document.getElementById('req-number').className = `requirement ${requirements.number ? 'met' : 'not-met'}`;

    // Update icons
    document.querySelector('#req-length .requirement-icon').textContent = requirements.length ? '✅' : '⭕';
    document.querySelector('#req-uppercase .requirement-icon').textContent = requirements.uppercase ? '✅' : '⭕';
    document.querySelector('#req-lowercase .requirement-icon').textContent = requirements.lowercase ? '✅' : '⭕';
    document.querySelector('#req-number .requirement-icon').textContent = requirements.number ? '✅' : '⭕';

    return requirements.length && requirements.uppercase && requirements.lowercase && requirements.number;
}

async function register(event) {
    event.preventDefault();
    
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    setLoading('registerBtn', true);
    clearAlerts();

    try {
        const response = await fetch(`/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('registerAlert', '✅ Registration successful! You can now login.', 'success');
            document.getElementById('registerForm').reset();
            // Switch to login tab
            document.querySelectorAll('.tab')[1].click();
        } else {
            // Handle specific error cases with friendly messages
            let errorMessage = data.detail;
            
            if (typeof data.detail === 'string') {
                if (data.detail.includes('Password must be at least 8 characters')) {
                    errorMessage = '🔒 Password must be at least 8 characters long and contain uppercase, lowercase, and number';
                } else if (data.detail.includes('already exists')) {
                    errorMessage = '📧 This email is already registered. Please try logging in instead.';
                } else if (data.detail.includes('Invalid email')) {
                    errorMessage = '📧 Please enter a valid email address.';
                }
            } else if (Array.isArray(data.detail)) {
                errorMessage = data.detail.map(err => err.msg).join(', ');
            }
            
            showAlert('registerAlert', `❌ ${errorMessage}`, 'error');
        }
    } catch (error) {
        showAlert('registerAlert', `❌ Network error: ${error.message}`, 'error');
    } finally {
        setLoading('registerBtn', false);
    }
}

async function login(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    setLoading('loginBtn', true);
    clearAlerts();

    try {
        const response = await fetch(`/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            // Store token
            localStorage.setItem('auth_token', data.access_token);
            currentUser = { email, token: data.access_token };
            
            showAlert('loginAlert', '✅ Login successful! Redirecting to dashboard...', 'success');
            
            // Redirect to dashboard after a short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            // Show the new error format
            let errorMessage = data.detail || data.error || 'Unknown error';
            showAlert('loginAlert', `❌ Login failed: ${errorMessage}`, 'error');
        }
    } catch (error) {
        showAlert('loginAlert', `❌ Network error: ${error.message}`, 'error');
    } finally {
        setLoading('loginBtn', false);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('registerForm').addEventListener('submit', register);
    document.getElementById('loginForm').addEventListener('submit', login);

    // Add password validation on input
    document.getElementById('registerPassword').addEventListener('input', function() {
        const password = this.value;
        const requirementsDiv = document.getElementById('passwordRequirements');
        
        if (password.length > 0) {
            requirementsDiv.classList.remove('hidden');
            validatePassword(password);
        } else {
            requirementsDiv.classList.add('hidden');
        }
    });

    // Check if user is already logged in on page load
    const token = localStorage.getItem('auth_token');
    if (token) {
        // If user is already logged in, redirect to dashboard
        window.location.href = '/dashboard';
    }

    // Check for ?verified=1 in the URL or type=signup in the hash and show a popup if present
    // Check for verified=1 in the main URL parameters
    const params = new URLSearchParams(window.location.search);
    if (params.get('verified') === '1') {
        document.querySelectorAll('.tab')[1].click();
        // Show alert after switching tabs to avoid it being cleared
        setTimeout(() => {
            showAlert('loginAlert', 'Your account is verified. You can now log in.', 'success');
        }, 100);
        return;
    }
    
    // Check for verified=1 in the redirect_to parameter (nested URL)
    const redirectTo = params.get('redirect_to');
    if (redirectTo) {
        try {
            const redirectUrl = new URL(redirectTo);
            const redirectParams = new URLSearchParams(redirectUrl.search);
            if (redirectParams.get('verified') === '1') {
                document.querySelectorAll('.tab')[1].click();
                // Show alert after switching tabs to avoid it being cleared
                setTimeout(() => {
                    showAlert('loginAlert', 'Your account is verified. You can now log in.', 'success');
                }, 100);
                return;
            }
        } catch (e) {
            // Could not parse redirect_to URL
        }
    }
    
    // Check for type=signup in the hash
    if (window.location.hash && window.location.hash.includes('type=signup')) {
        document.querySelectorAll('.tab')[1].click();
        // Show alert after switching tabs to avoid it being cleared
        setTimeout(() => {
            showAlert('loginAlert', 'Your account is verified. You can now log in.', 'success');
        }, 100);
        return;
    }
    
    // Check for error_code=otp_expired in the hash
    if (window.location.hash && window.location.hash.includes('error_code=otp_expired')) {
        document.querySelectorAll('.tab')[1].click();
        // Show alert after switching tabs to avoid it being cleared
        setTimeout(() => {
            showAlert('loginAlert', 'The verification link is invalid or has expired. Please request a new verification email.', 'error');
        }, 100);
        return;
    }
}); 