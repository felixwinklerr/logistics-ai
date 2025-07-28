import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/shared/stores/authStore'
import { useUIStore } from '@/shared/stores/uiStore'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState()
    
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    const { addNotification } = useUIStore.getState()
    const { logout } = useAuthStore.getState()
    
    // Handle different error scenarios
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as any
      
      switch (status) {
        case 401:
          // Unauthorized - logout user
          logout()
          addNotification({
            type: 'error',
            title: 'Authentication Error',
            message: 'Your session has expired. Please sign in again.',
          })
          break
          
        case 403:
          // Forbidden
          addNotification({
            type: 'error',
            title: 'Access Denied',
            message: 'You do not have permission to perform this action.',
          })
          break
          
        case 404:
          // Not found
          addNotification({
            type: 'error',
            title: 'Not Found',
            message: data?.message || 'The requested resource was not found.',
          })
          break
          
        case 422:
          // Validation error
          addNotification({
            type: 'error',
            title: 'Validation Error',
            message: data?.message || 'Please check your input and try again.',
          })
          break
          
        case 500:
          // Server error
          addNotification({
            type: 'error',
            title: 'Server Error',
            message: 'An internal server error occurred. Please try again later.',
          })
          break
          
        default:
          // Generic error
          addNotification({
            type: 'error',
            title: 'Error',
            message: data?.message || 'An unexpected error occurred.',
          })
      }
    } else if (error.request) {
      // Network error
      addNotification({
        type: 'error',
        title: 'Network Error',
        message: 'Unable to connect to the server. Please check your internet connection.',
      })
    } else {
      // Request setup error
      addNotification({
        type: 'error',
        title: 'Request Error',
        message: 'An error occurred while setting up the request.',
      })
    }
    
    return Promise.reject(error)
  }
)

// API helper functions
export const apiClient = {
  get: <T = any>(url: string, config?: AxiosRequestConfig) => 
    api.get<T>(url, config),
    
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => 
    api.post<T>(url, data, config),
    
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => 
    api.put<T>(url, data, config),
    
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => 
    api.patch<T>(url, data, config),
    
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => 
    api.delete<T>(url, config),
}

export default api 