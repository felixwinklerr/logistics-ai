import { apiClient } from './api'

// Types for authentication
export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'dispatcher' | 'accountant' | 'viewer'
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthError {
  message: string
  code: string
  status?: number
}

// AuthService class for JWT authentication integration
export class AuthService {
  private static readonly AUTH_BASE_URL = '/api/v1/auth'

  /**
   * Authenticate user with email and password
   * Connects to backend JWT /auth/login endpoint
   */
  static async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const loginData: LoginRequest = { email, password }
      
      const response = await apiClient.post<LoginResponse>(
        `${this.AUTH_BASE_URL}/login`,
        loginData
      )

      // Validate response structure
      if (!response.data.access_token || !response.data.user) {
        throw new Error('Invalid login response from server')
      }

      return response.data
    } catch (error: any) {
      // Transform API errors into AuthError format
      if (error.response?.status === 401) {
        throw {
          message: 'Invalid email or password. Please check your credentials.',
          code: 'INVALID_CREDENTIALS',
          status: 401,
        } as AuthError
      }

      if (error.response?.status === 422) {
        throw {
          message: error.response.data?.detail || 'Please check your email and password format.',
          code: 'VALIDATION_ERROR',
          status: 422,
        } as AuthError
      }

      if (error.response?.status >= 500) {
        throw {
          message: 'Authentication service is temporarily unavailable. Please try again later.',
          code: 'SERVER_ERROR',
          status: error.response.status,
        } as AuthError
      }

      // Network or other errors
      throw {
        message: error.message || 'Unable to connect to authentication service.',
        code: 'NETWORK_ERROR',
      } as AuthError
    }
  }

  /**
   * Refresh JWT tokens using refresh token
   * Connects to backend JWT /auth/refresh endpoint
   */
  static async refreshToken(refreshToken: string): Promise<TokenResponse> {
    try {
      const response = await apiClient.post<TokenResponse>(
        `${this.AUTH_BASE_URL}/refresh`,
        { refresh_token: refreshToken }
      )

      // Validate response structure
      if (!response.data.access_token) {
        throw new Error('Invalid refresh response from server')
      }

      return response.data
    } catch (error: any) {
      // Transform refresh errors
      if (error.response?.status === 401) {
        throw {
          message: 'Session expired. Please log in again.',
          code: 'REFRESH_TOKEN_INVALID',
          status: 401,
        } as AuthError
      }

      throw {
        message: error.message || 'Unable to refresh authentication tokens.',
        code: 'REFRESH_ERROR',
      } as AuthError
    }
  }

  /**
   * Get current user profile information
   * Connects to backend JWT /auth/me endpoint
   */
  static async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>(`${this.AUTH_BASE_URL}/me`)

      // Validate user response structure
      if (!response.data.id || !response.data.email) {
        throw new Error('Invalid user profile response from server')
      }

      return response.data
    } catch (error: any) {
      // Transform user profile errors
      if (error.response?.status === 401) {
        throw {
          message: 'Authentication required. Please log in.',
          code: 'AUTHENTICATION_REQUIRED',
          status: 401,
        } as AuthError
      }

      throw {
        message: error.message || 'Unable to retrieve user profile.',
        code: 'PROFILE_ERROR',
      } as AuthError
    }
  }

  /**
   * Logout user and invalidate tokens
   * Connects to backend JWT /auth/logout endpoint
   */
  static async logout(): Promise<void> {
    try {
      await apiClient.post(`${this.AUTH_BASE_URL}/logout`)
    } catch (error: any) {
      // Logout should succeed even if API call fails
      // This ensures local state is always cleared
      console.warn('Logout API call failed, but continuing with local cleanup:', error.message)
    }
  }

  /**
   * Validate JWT token format and expiration
   * Utility method for client-side token validation
   */
  static validateToken(token: string): boolean {
    try {
      if (!token || typeof token !== 'string') {
        return false
      }

      // Basic JWT format validation (3 parts separated by dots)
      const parts = token.split('.')
      if (parts.length !== 3) {
        return false
      }

      // Decode payload to check expiration
      const payload = JSON.parse(atob(parts[1]))
      const currentTime = Math.floor(Date.now() / 1000)
      
      // Check if token is expired
      if (payload.exp && payload.exp < currentTime) {
        return false
      }

      return true
    } catch (error) {
      // Invalid token format
      return false
    }
  }

  /**
   * Parse JWT token payload
   * Utility method to extract user information from token
   */
  static parseTokenPayload(token: string): any {
    try {
      if (!this.validateToken(token)) {
        throw new Error('Invalid token format')
      }

      const parts = token.split('.')
      const payload = JSON.parse(atob(parts[1]))
      
      return payload
    } catch (error) {
      throw new Error('Unable to parse token payload')
    }
  }

  /**
   * Check if token is close to expiration (within 5 minutes)
   * Used for automatic token refresh logic
   */
  static isTokenExpiringSoon(token: string, minutesBeforeExpiry: number = 5): boolean {
    try {
      const payload = this.parseTokenPayload(token)
      const currentTime = Math.floor(Date.now() / 1000)
      const expiryThreshold = payload.exp - (minutesBeforeExpiry * 60)
      
      return currentTime >= expiryThreshold
    } catch (error) {
      // If we can't parse the token, consider it expiring
      return true
    }
  }

  /**
   * Get Romanian business role display name
   * Utility for UI display of user roles
   */
  static getRoleDisplayName(role: User['role']): string {
    const roleNames = {
      admin: 'Administrator',
      dispatcher: 'Dispatcher',
      accountant: 'Accountant',
      viewer: 'Viewer'
    }
    
    return roleNames[role] || 'Unknown Role'
  }

  /**
   * Check if user role has specific permissions
   * Romanian freight forwarding business logic
   */
  static hasPermission(userRole: User['role'], permission: string): boolean {
    const permissions = {
      admin: ['manage_users', 'manage_orders', 'view_financials', 'system_config'],
      dispatcher: ['manage_orders', 'assign_subcontractors', 'view_orders'],
      accountant: ['view_financials', 'manage_invoices', 'view_orders'],
      viewer: ['view_orders', 'view_reports']
    }
    
    return permissions[userRole]?.includes(permission) || false
  }
}

export default AuthService
