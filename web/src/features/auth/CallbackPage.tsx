import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authService } from '@/services/auth'

export default function CallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setToken, setUser, logout } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleAuth = async () => {
      // Check for error from OAuth
      const errorParam = searchParams.get('error')
      if (errorParam) {
        setError(decodeURIComponent(errorParam))
        return
      }

      // Check for token from successful OAuth
      const token = searchParams.get('token')
      if (!token) {
        setError('No authentication token received')
        return
      }

      try {
        // Store the token first so the API client can use it
        setToken(token)

        // Fetch user info using the token
        const user = await authService.getCurrentUser()

        // Store user data
        setUser(user)

        // Redirect to domain selection (1:1 parity with original)
        navigate('/domain-selection', { replace: true })
      } catch (err) {
        console.error('Failed to fetch user:', err)
        logout()
        setError('Failed to complete authentication. Please try again.')
      }
    }

    handleAuth()
  }, [searchParams, setToken, setUser, logout, navigate])

  if (error) {
    return (
      <div className="text-left">
        {/* Solvia Sun Logo */}
        <div className="mb-10">
          <img
            src="/images/orange-svg-emblem.svg"
            alt="Solvia"
            className="w-14 h-14"
          />
        </div>

        {/* Heading */}
        <h1 className="text-h1 font-heading font-bold text-text-primary mb-4 leading-tight tracking-tight">
          Authentication Error
        </h1>

        {/* Error message */}
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-p2 font-sans text-red-600">
          {error}
        </div>

        {/* Back to login button */}
        <a
          href="/login"
          className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-[#EC6019] hover:bg-[#d85516] text-white font-sans font-semibold text-p1 rounded-xl transition-all duration-200"
        >
          Back to Login
        </a>
      </div>
    )
  }

  return (
    <div className="text-left">
      {/* Solvia Sun Logo */}
      <div className="mb-10">
        <img
          src="/images/orange-svg-emblem.svg"
          alt="Solvia"
          className="w-14 h-14"
        />
      </div>

      {/* Heading */}
      <h1 className="text-h1 font-heading font-bold text-text-primary mb-4 leading-tight tracking-tight">
        Signing you in...
      </h1>

      {/* Loading indicator */}
      <div className="flex items-center gap-3 text-p1 font-sans text-text-secondary">
        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="text-p1 font-sans">Please wait...</span>
      </div>
    </div>
  )
}
