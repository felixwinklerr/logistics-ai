import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AuthService, User, LoginResponse } from '../services/authService';

interface AuthState {
  // Authentication state
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  lastActivity: number;
  
  // UI state
  loginError: string | null;
  
  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshTokens: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string | null, refreshToken: string | null) => void;
  setLoading: (loading: boolean) => void;
  setLoginError: (error: string | null) => void;
  clearAuth: () => void;
  updateLastActivity: () => void;
  
  // Romanian business role helpers
  canManageOrders: () => boolean;
  canViewFinancials: () => boolean;
  isAdmin: () => boolean;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      lastActivity: Date.now(),
      loginError: null,

      // Authentication actions
      login: async (email: string, password: string) => {
        set({ isLoading: true, loginError: null });
        
        try {
          const response: LoginResponse = await AuthService.login(email, password);
          
          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            lastActivity: Date.now(),
            loginError: null,
          });
        } catch (error: any) {
          set({
            isLoading: false,
            loginError: error.message || 'Login failed. Please try again.',
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        
        try {
          // Call backend logout endpoint
          await AuthService.logout();
        } catch (error) {
          console.error('Logout API call failed:', error);
          // Continue with local logout even if API fails
        } finally {
          // Clear all authentication state
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            lastActivity: Date.now(),
            loginError: null,
          });
        }
      },

      refreshTokens: async () => {
        const { refreshToken, accessToken } = get();
        
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        // Check if current token needs refresh
        if (accessToken && !AuthService.isTokenExpiringSoon(accessToken)) {
          return; // Token is still valid
        }

        try {
          const response = await AuthService.refreshToken(refreshToken);
          
          set({
            accessToken: response.access_token,
            lastActivity: Date.now(),
          });
        } catch (error: any) {
          console.error('Token refresh failed:', error);
          // Clear auth state on refresh failure
          get().clearAuth();
          throw error;
        }
      },

      getCurrentUser: async () => {
        try {
          const user = await AuthService.getCurrentUser();
          set({ user, lastActivity: Date.now() });
        } catch (error: any) {
          console.error('Get current user failed:', error);
          // Clear auth state if user fetch fails
          get().clearAuth();
          throw error;
        }
      },

      // State setters
      setUser: (user) => set({ user, lastActivity: Date.now() }),
      
      setTokens: (accessToken, refreshToken) => set({ 
        accessToken, 
        refreshToken, 
        isAuthenticated: !!(accessToken && refreshToken),
        lastActivity: Date.now()
      }),
      
      setLoading: (isLoading) => set({ isLoading }),
      
      setLoginError: (loginError) => set({ loginError }),
      
      clearAuth: () => set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        loginError: null,
        lastActivity: Date.now(),
      }),

      updateLastActivity: () => set({ lastActivity: Date.now() }),

      // Romanian business role helpers
      canManageOrders: () => {
        const { user } = get();
        return user ? AuthService.hasPermission(user.role, 'manage_orders') : false;
      },

      canViewFinancials: () => {
        const { user } = get();
        return user ? AuthService.hasPermission(user.role, 'view_financials') : false;
      },

      isAdmin: () => {
        const { user } = get();
        return user?.role === 'admin' || false;
      },

      hasRole: (role: string) => {
        const { user } = get();
        return user?.role === role || false;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        lastActivity: state.lastActivity,
      }),
    }
  )
);

// Token refresh middleware - automatically refresh tokens when needed
let refreshPromise: Promise<void> | null = null;

export const useAuthTokenRefresh = () => {
  const store = useAuthStore();

  const ensureValidToken = async (): Promise<void> => {
    const { accessToken, refreshToken, isAuthenticated } = store;

    if (!isAuthenticated || !accessToken || !refreshToken) {
      throw new Error('User not authenticated');
    }

    // Check if token needs refresh
    if (AuthService.isTokenExpiringSoon(accessToken)) {
      // Prevent multiple simultaneous refresh attempts
      if (!refreshPromise) {
        refreshPromise = store.refreshTokens().finally(() => {
          refreshPromise = null;
        });
      }
      await refreshPromise;
    }
  };

  return { ensureValidToken };
};

export default useAuthStore;
