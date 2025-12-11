import api, { extractData } from './api'
import type { User } from '@/types'

export interface AuthResponse {
  user: User
  token: string
  expires_at: string
}

export const authService = {
  // Get Google OAuth URL
  async getGoogleAuthUrl(): Promise<{ auth_url: string }> {
    const response = await api.get('/auth/url')
    return extractData(response)
  },

  // Handle OAuth callback
  async handleCallback(code: string, state?: string): Promise<AuthResponse> {
    const response = await api.get('/auth/callback', { params: { code, state } })
    return extractData(response)
  },

  // Get current user
  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/me')
    const data = extractData(response) as { user: User }
    return data.user
  },

  // Refresh token
  async refreshToken(): Promise<AuthResponse> {
    const response = await api.post('/auth/refresh')
    return extractData(response)
  },

  // Logout
  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },
}
