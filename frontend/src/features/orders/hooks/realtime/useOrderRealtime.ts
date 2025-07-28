/**
 * Real-time Order Updates Hook
 * Implements order-specific real-time functionality with Romanian context
 */

import { useEffect, useCallback, useState } from 'react';
import { useWebSocketConnection } from './useWebSocketConnection';
import { WorkflowStage } from '../../components/workflow/WorkflowProgress';

export interface OrderUpdateEvent {
  orderId: string;
  type: 'status_change' | 'field_update' | 'pricing_update' | 'assignment_update';
  data: any;
  timestamp: string;
  userId?: string;
  username?: string;
}

export interface OrderCollaborationEvent {
  orderId: string;
  userId: string;
  username: string;
  action: 'joined' | 'left' | 'editing';
  field?: string;
  timestamp: string;
}

export interface UseOrderRealtimeProps {
  orderId?: string;
  enableCollaboration?: boolean;
  enableStatusUpdates?: boolean;
  enablePricingUpdates?: boolean;
}

export interface UseOrderRealtimeReturn {
  // Connection status
  isConnected: boolean;
  connectionStatus: string;
  
  // Order updates
  lastUpdate: OrderUpdateEvent | null;
  orderStatus: WorkflowStage | null;
  
  // Collaboration
  activeUsers: Array<{
    userId: string;
    username: string;
    editingField?: string;
  }>;
  
  // Actions
  joinOrder: (orderId: string) => void;
  leaveOrder: () => void;
  updateField: (field: string, value: any) => void;
  broadcastEditing: (field: string) => void;
  stopEditing: () => void;
  
  // Fallback mode
  isFallbackMode: boolean;
  triggerPolling: () => void;
}

export const useOrderRealtime = ({
  orderId,
  enableCollaboration = true,
  enableStatusUpdates = true,
  enablePricingUpdates = true
}: UseOrderRealtimeProps): UseOrderRealtimeReturn => {
  const [lastUpdate, setLastUpdate] = useState<OrderUpdateEvent | null>(null);
  const [orderStatus, setOrderStatus] = useState<WorkflowStage | null>(null);
  const [activeUsers, setActiveUsers] = useState<Array<{
    userId: string;
    username: string;
    editingField?: string;
  }>>([]);
  const [currentOrderId, setCurrentOrderId] = useState<string | null>(orderId || null);

  const {
    connectionStatus,
    isConnected,
    sendMessage,
    subscribe
  } = useWebSocketConnection();

  const isFallbackMode = connectionStatus === 'fallback';

  // Handle order status updates
  useEffect(() => {
    if (!enableStatusUpdates) return;

    const unsubscribe = subscribe('order:status_changed', (data: OrderUpdateEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setLastUpdate(data);
        if (data.data.status) {
          setOrderStatus(data.data.status as WorkflowStage);
        }
        
        console.log('Order status updated:', data);
      }
    });

    return unsubscribe;
  }, [subscribe, currentOrderId, enableStatusUpdates]);

  // Handle order field updates
  useEffect(() => {
    const unsubscribe = subscribe('order:updated', (data: OrderUpdateEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setLastUpdate(data);
        console.log('Order updated:', data);
      }
    });

    return unsubscribe;
  }, [subscribe, currentOrderId]);

  // Handle pricing updates
  useEffect(() => {
    if (!enablePricingUpdates) return;

    const unsubscribe = subscribe('order:pricing_updated', (data: OrderUpdateEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setLastUpdate(data);
        console.log('Order pricing updated:', data);
      }
    });

    return unsubscribe;
  }, [subscribe, currentOrderId, enablePricingUpdates]);

  // Handle AI processing updates
  useEffect(() => {
    const unsubscribe = subscribe('order:ai_processing', (data: {
      orderId: string;
      progress: number;
      stage: string;
      confidence?: number;
    }) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setLastUpdate({
          orderId: data.orderId,
          type: 'status_change',
          data: {
            aiProgress: data.progress,
            aiStage: data.stage,
            confidence: data.confidence
          },
          timestamp: new Date().toISOString()
        });
        
        console.log('AI processing update:', data);
      }
    });

    return unsubscribe;
  }, [subscribe, currentOrderId]);

  // Handle collaboration events
  useEffect(() => {
    if (!enableCollaboration) return;

    const handleUserJoined = (data: OrderCollaborationEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setActiveUsers(prev => {
          const filtered = prev.filter(user => user.userId !== data.userId);
          return [...filtered, {
            userId: data.userId,
            username: data.username
          }];
        });
      }
    };

    const handleUserLeft = (data: OrderCollaborationEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setActiveUsers(prev => prev.filter(user => user.userId !== data.userId));
      }
    };

    const handleUserEditing = (data: OrderCollaborationEvent) => {
      if (currentOrderId && data.orderId === currentOrderId) {
        setActiveUsers(prev => 
          prev.map(user => 
            user.userId === data.userId 
              ? { ...user, editingField: data.field }
              : user
          )
        );
      }
    };

    const unsubscribeJoined = subscribe('user:joined_order', handleUserJoined);
    const unsubscribeLeft = subscribe('user:left_order', handleUserLeft);
    const unsubscribeEditing = subscribe('user:editing', handleUserEditing);

    return () => {
      unsubscribeJoined();
      unsubscribeLeft();
      unsubscribeEditing();
    };
  }, [subscribe, currentOrderId, enableCollaboration]);

  // Join order room
  const joinOrder = useCallback((newOrderId: string) => {
    if (currentOrderId) {
      // Leave current order first
      sendMessage({
        type: 'leave_order',
        payload: { orderId: currentOrderId },
        timestamp: new Date().toISOString()
      });
    }

    setCurrentOrderId(newOrderId);
    setActiveUsers([]);
    setLastUpdate(null);

    if (isConnected) {
      sendMessage({
        type: 'join_order',
        payload: { orderId: newOrderId },
        timestamp: new Date().toISOString()
      });
    }
  }, [currentOrderId, isConnected, sendMessage]);

  // Leave order room
  const leaveOrder = useCallback(() => {
    if (currentOrderId && isConnected) {
      sendMessage({
        type: 'leave_order',
        payload: { orderId: currentOrderId },
        timestamp: new Date().toISOString()
      });
    }

    setCurrentOrderId(null);
    setActiveUsers([]);
    setLastUpdate(null);
  }, [currentOrderId, isConnected, sendMessage]);

  // Update field value
  const updateField = useCallback((field: string, value: any) => {
    if (!currentOrderId || !isConnected) return;

    sendMessage({
      type: 'update_order_field',
      payload: {
        orderId: currentOrderId,
        field,
        value
      },
      timestamp: new Date().toISOString()
    });
  }, [currentOrderId, isConnected, sendMessage]);

  // Broadcast editing status
  const broadcastEditing = useCallback((field: string) => {
    if (!currentOrderId || !isConnected || !enableCollaboration) return;

    sendMessage({
      type: 'user_editing',
      payload: {
        orderId: currentOrderId,
        field
      },
      timestamp: new Date().toISOString()
    });
  }, [currentOrderId, isConnected, enableCollaboration, sendMessage]);

  // Stop editing broadcast
  const stopEditing = useCallback(() => {
    if (!currentOrderId || !isConnected || !enableCollaboration) return;

    sendMessage({
      type: 'user_stop_editing',
      payload: {
        orderId: currentOrderId
      },
      timestamp: new Date().toISOString()
    });
  }, [currentOrderId, isConnected, enableCollaboration, sendMessage]);

  // Fallback polling trigger
  const triggerPolling = useCallback(() => {
    if (isFallbackMode && currentOrderId) {
      console.log('Triggering fallback polling for order:', currentOrderId);
      // In fallback mode, this would trigger REST API polling
      // Implementation would depend on the specific REST API hook
    }
  }, [isFallbackMode, currentOrderId]);

  // Auto-join order when orderId prop changes
  useEffect(() => {
    if (orderId && orderId !== currentOrderId) {
      joinOrder(orderId);
    }
  }, [orderId, currentOrderId, joinOrder]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      leaveOrder();
    };
  }, [leaveOrder]);

  return {
    // Connection status
    isConnected,
    connectionStatus,
    
    // Order updates
    lastUpdate,
    orderStatus,
    
    // Collaboration
    activeUsers,
    
    // Actions
    joinOrder,
    leaveOrder,
    updateField,
    broadcastEditing,
    stopEditing,
    
    // Fallback mode
    isFallbackMode,
    triggerPolling
  };
};

export default useOrderRealtime;
