let currentUser = null;

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
    document.getElementById('loginAlert').classList.add('hidden');
}

function setLoading(buttonId, isLoading) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    if (isLoading) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span>Loading...';
    } else {
        btn.disabled = false;
        // Restore original text
        if (buttonId === 'googleLoginBtn') {
            btn.innerHTML = `
                <div class="google-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                </div>
                <span class="btn-text">Sign in with Google</span>
            `;
        }
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

// Google OAuth Login Function
async function loginWithGoogle() {
    console.log('loginWithGoogle function called'); // Debug log
    setLoading('googleLoginBtn', true);
    clearAlerts();
    
    try {
        console.log('Redirecting to Google OAuth...'); // Debug log
        // For the new design, we'll redirect directly to Google OAuth
        // The backend will handle the email collection during the OAuth flow
        window.location.href = `/auth/google/authorize`;
        
    } catch (error) {
        console.error('Error in loginWithGoogle:', error); // Debug log
        showAlert('loginAlert', `❌ Error starting Google OAuth: ${error.message}`, 'error');
    } finally {
        setLoading('googleLoginBtn', false);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in on page load
    const token = localStorage.getItem('auth_token');
    if (token) {
        // If user is already logged in, redirect to dashboard
        window.location.href = '/dashboard';
    }
}); 