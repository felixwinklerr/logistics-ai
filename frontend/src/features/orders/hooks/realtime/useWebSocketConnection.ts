/**
 * WebSocket Connection Hook
 * Implements hybrid WebSocket + REST architecture from creative phase
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '@/shared/stores/authStore';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'fallback';

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
  orderId?: string;
}

export interface UseWebSocketConnectionProps {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableFallback?: boolean;
}

export interface UseWebSocketConnectionReturn {
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  sendMessage: (message: WebSocketMessage) => void;
  subscribe: (eventType: string, callback: (data: any) => void) => () => void;
  disconnect: () => void;
  reconnect: () => void;
}

export const useWebSocketConnection = ({
  url = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws`,
  reconnectInterval = 5000,
  maxReconnectAttempts = 5,
  enableFallback = true
}: UseWebSocketConnectionProps = {}): UseWebSocketConnectionReturn => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [isConnected, setIsConnected] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const eventListenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map());
  
  const { token, isAuthenticated } = useAuthStore();

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!isAuthenticated || !token) {
      console.warn('WebSocket: Cannot connect without authentication');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.CONNECTING || 
        wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setConnectionStatus('connecting');
      
      // Add JWT token to WebSocket URL for authentication
      const wsUrl = `${url}?token=${token}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        clearReconnectTimeout();
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setConnectionStatus('disconnected');
        setIsConnected(false);
        
        // Attempt reconnection if not manually closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          scheduleReconnect();
        } else if (enableFallback) {
          setConnectionStatus('fallback');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        
        if (enableFallback && reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setConnectionStatus('fallback');
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      if (enableFallback) {
        setConnectionStatus('fallback');
      }
    }
  }, [url, token, isAuthenticated, maxReconnectAttempts, enableFallback]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      if (enableFallback) {
        setConnectionStatus('fallback');
      }
      return;
    }

    reconnectAttemptsRef.current++;
    console.log(`Scheduling reconnect attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, reconnectInterval * reconnectAttemptsRef.current); // Exponential backoff
  }, [connect, reconnectInterval, maxReconnectAttempts, enableFallback]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    const listeners = eventListenersRef.current.get(message.type);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(message.payload);
        } catch (error) {
          console.error('Error in WebSocket message callback:', error);
        }
      });
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({
          ...message,
          timestamp: new Date().toISOString()
        }));
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
    }
  }, []);

  const subscribe = useCallback((eventType: string, callback: (data: any) => void) => {
    if (!eventListenersRef.current.has(eventType)) {
      eventListenersRef.current.set(eventType, new Set());
    }
    
    eventListenersRef.current.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const listeners = eventListenersRef.current.get(eventType);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          eventListenersRef.current.delete(eventType);
        }
      }
    };
  }, []);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    setConnectionStatus('disconnected');
    setIsConnected(false);
  }, [clearReconnectTimeout, maxReconnectAttempts]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 100); // Small delay before reconnecting
  }, [disconnect, connect]);

  // Initialize connection when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, token, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearReconnectTimeout();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [clearReconnectTimeout]);

  return {
    connectionStatus,
    isConnected,
    sendMessage,
    subscribe,
    disconnect,
    reconnect
  };
};

export default useWebSocketConnection;
