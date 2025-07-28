/**
 * Real-time order updates hook
 * Integrates SSE with TanStack Query for live order updates
 */

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getRealtimeService } from '@/shared/services/realtime';
import { useAuth } from '@/shared/hooks/useAuth';

export interface RealtimeConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  connectionState: 'connecting' | 'open' | 'closed';
  lastEventTime?: Date;
}

export function useOrderRealtime(): RealtimeConnectionState {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [connectionState, setConnectionState] = useState<RealtimeConnectionState>({
    isConnected: false,
    isConnecting: false,
    connectionState: 'closed',
  });

  useEffect(() => {
    // Only connect if user is authenticated
    if (!user) {
      return;
    }

    const realtimeService = getRealtimeService(queryClient);
    
    // Set up connection state monitoring
    const checkConnectionState = () => {
      const state = realtimeService.getConnectionState();
      setConnectionState(prev => ({
        ...prev,
        isConnected: state === 'open',
        isConnecting: state === 'connecting',
        connectionState: state,
        lastEventTime: state === 'open' ? new Date() : prev.lastEventTime,
      }));
    };

    // Monitor connection state periodically
    const stateMonitor = setInterval(checkConnectionState, 1000);
    
    // Initial state check
    checkConnectionState();

    // Connect to real-time service (token will be handled by API client)
    setConnectionState(prev => ({ ...prev, isConnecting: true }));
    realtimeService.connect();

    // Cleanup on unmount or auth change
    return () => {
      clearInterval(stateMonitor);
      realtimeService.disconnect();
      setConnectionState({
        isConnected: false,
        isConnecting: false,
        connectionState: 'closed',
      });
    };
  }, [user, queryClient]);

  return connectionState;
}

/**
 * Hook for components that want to show real-time connection status
 */
export function useRealtimeStatus() {
  const connectionState = useOrderRealtime();
  
  return {
    ...connectionState,
    statusText: getStatusText(connectionState),
    statusColor: getStatusColor(connectionState),
  };
}

function getStatusText(state: RealtimeConnectionState): string {
  if (state.isConnecting) return 'Connecting...';
  if (state.isConnected) return 'Live updates active';
  return 'Offline';
}

function getStatusColor(state: RealtimeConnectionState): 'green' | 'yellow' | 'red' {
  if (state.isConnected) return 'green';
  if (state.isConnecting) return 'yellow';
  return 'red';
}

export default useOrderRealtime; 