import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useAuthStore, useAuthTokenRefresh } from '../stores/authStore';
import { User } from '../services/authService';

interface AuthContextType {
  // Authentication state
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginError: string | null;
  
  // Authentication actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  
  // Romanian business role helpers
  canManageOrders: boolean;
  canViewFinancials: boolean;
  isAdmin: boolean;
  hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  // Zustand store integration
  const {
    user,
    isAuthenticated,
    isLoading,
    loginError,
    accessToken,
    refreshToken,
    login: storeLogin,
    logout: storeLogout,
    setLoading,
    setLoginError,
    getCurrentUser,
    canManageOrders: storeCanManageOrders,
    canViewFinancials: storeCanViewFinancials,
    isAdmin: storeIsAdmin,
    hasRole: storeHasRole,
    updateLastActivity,
  } = useAuthStore();

  // Token refresh functionality
  const { ensureValidToken } = useAuthTokenRefresh();

  // Local state for UI management
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize authentication state on app start
  useEffect(() => {
    const initializeAuth = async () => {
      setLoading(true);
      
      try {
        // If we have tokens but no user, fetch current user
        if (isAuthenticated && accessToken && !user) {
          await getCurrentUser();
        }
        
        // If we have tokens, ensure they're valid
        if (isAuthenticated && accessToken && refreshToken) {
          try {
            await ensureValidToken();
          } catch (error) {
            console.error('Token validation failed during initialization:', error);
            // Clear invalid authentication state
            await storeLogout();
          }
        }
      } catch (error) {
        console.error('Authentication initialization failed:', error);
        // Clear authentication state on initialization failure
        await storeLogout();
      } finally {
        setLoading(false);
        setIsInitialized(true);
      }
    };

    initializeAuth();
  }, []);

  // Automatic token refresh
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    const interval = setInterval(async () => {
      try {
        await ensureValidToken();
        updateLastActivity();
      } catch (error) {
        console.error('Automatic token refresh failed:', error);
        // Logout on refresh failure
        await storeLogout();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [isAuthenticated, accessToken, ensureValidToken, updateLastActivity, storeLogout]);

  // Cross-tab authentication synchronization
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'auth-storage') {
        // Force re-render when auth state changes in another tab
        window.location.reload();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Update activity on user interaction
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleUserActivity = () => {
      updateLastActivity();
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, handleUserActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleUserActivity, true);
      });
    };
  }, [isAuthenticated, updateLastActivity]);

  // Authentication actions with UI state management
  const login = useCallback(async (email: string, password: string): Promise<void> => {
    try {
      await storeLogin(email, password);
    } catch (error) {
      // Error is already handled in store
      throw error;
    }
  }, [storeLogin]);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await storeLogout();
    } catch (error) {
      console.error('Logout failed:', error);
      // Continue with logout even if it fails
    }
  }, [storeLogout]);

  const clearError = useCallback((): void => {
    setLoginError(null);
  }, [setLoginError]);

  // Romanian business role helpers (computed from store)
  const canManageOrders = storeCanManageOrders();
  const canViewFinancials = storeCanViewFinancials();
  const isAdmin = storeIsAdmin();

  // Memoize hasRole function to prevent recreation
  const hasRole = useCallback((role: string) => storeHasRole(role), [storeHasRole]);

  const value: AuthContextType = {
    // Authentication state
    user,
    isAuthenticated,
    isLoading: isLoading || !isInitialized,
    loginError,
    
    // Authentication actions
    login,
    logout,
    clearError,
    
    // Romanian business role helpers
    canManageOrders,
    canViewFinancials,
    isAdmin,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default useAuth;
