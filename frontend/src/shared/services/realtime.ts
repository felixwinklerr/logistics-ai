/**
 * Real-time service for Server-Sent Events integration
 * Handles live updates for order status changes and notifications
 */

import { QueryClient } from '@tanstack/react-query';
import { orderKeys } from '@/features/orders/hooks/useOrders';
import { Order } from '@/features/orders/types';

export interface RealtimeEvent {
  type: 'order_update' | 'order_status_change' | 'assignment_update';
  data: {
    order_id: string;
    order?: Partial<Order>;
    status?: string;
    timestamp: string;
  };
}

export class RealtimeService {
  private eventSource: EventSource | null = null;
  private queryClient: QueryClient;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second

  constructor(queryClient: QueryClient) {
    this.queryClient = queryClient;
  }

  connect(token?: string): void {
    if (this.eventSource) {
      this.disconnect();
    }

    try {
      const url = new URL('/api/events', window.location.origin);
      if (token) {
        url.searchParams.set('token', token);
      }

      this.eventSource = new EventSource(url.toString());
      
      this.eventSource.onopen = this.handleOpen;
      this.eventSource.onmessage = this.handleMessage;
      this.eventSource.onerror = this.handleError;

      console.log('🔄 Real-time connection established');
    } catch (error) {
      console.error('Failed to establish real-time connection:', error);
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.reconnectAttempts = 0;
      console.log('🔌 Real-time connection closed');
    }
  }

  private handleOpen = (): void => {
    console.log('✅ Real-time connection opened');
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
  };

  private handleMessage = (event: MessageEvent): void => {
    try {
      const realtimeEvent: RealtimeEvent = JSON.parse(event.data);
      this.processRealtimeEvent(realtimeEvent);
    } catch (error) {
      console.error('Failed to parse real-time event:', error);
    }
  };

  private handleError = (error: Event): void => {
    console.error('Real-time connection error:', error);
    
    if (this.eventSource?.readyState === EventSource.CLOSED) {
      this.attemptReconnect();
    }
  };

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
      
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('❌ Max reconnection attempts reached. Real-time updates disabled.');
    }
  }

  private processRealtimeEvent(event: RealtimeEvent): void {
    const { type, data } = event;

    switch (type) {
      case 'order_update':
        this.handleOrderUpdate(data);
        break;
      case 'order_status_change':
        this.handleOrderStatusChange(data);
        break;
      case 'assignment_update':
        this.handleAssignmentUpdate(data);
        break;
      default:
        console.warn('Unknown real-time event type:', type);
    }
  }

  private handleOrderUpdate(data: RealtimeEvent['data']): void {
    const { order_id, order } = data;
    
    if (order) {
      // Update the specific order in cache
      this.queryClient.setQueryData(
        orderKeys.detail(order_id),
        (oldOrder: Order | undefined) => {
          if (!oldOrder) return oldOrder;
          return { ...oldOrder, ...order, updated_at: data.timestamp };
        }
      );

      // Invalidate order lists to trigger refetch
      this.queryClient.invalidateQueries({ 
        queryKey: orderKeys.lists(),
        refetchType: 'none' // Don't refetch immediately, just mark as stale
      });

      console.log(`🔄 Order ${order_id.slice(0, 8)} updated via real-time`);
    }
  }

  private handleOrderStatusChange(data: RealtimeEvent['data']): void {
    const { order_id, status } = data;
    
    if (status) {
      // Update order status in cache
      this.queryClient.setQueryData(
        orderKeys.detail(order_id),
        (oldOrder: Order | undefined) => {
          if (!oldOrder) return oldOrder;
          return { 
            ...oldOrder, 
            order_status: status as any,
            updated_at: data.timestamp 
          };
        }
      );

      // Invalidate order lists
      this.queryClient.invalidateQueries({ 
        queryKey: orderKeys.lists(),
        refetchType: 'none'
      });

      console.log(`🔄 Order ${order_id.slice(0, 8)} status changed to ${status}`);
    }
  }

  private handleAssignmentUpdate(data: RealtimeEvent['data']): void {
    const { order_id } = data;
    
    // For assignment updates, we need to refetch the full order
    // as subcontractor data might have changed
    this.queryClient.invalidateQueries({ 
      queryKey: orderKeys.detail(order_id) 
    });
    
    this.queryClient.invalidateQueries({ 
      queryKey: orderKeys.lists(),
      refetchType: 'none'
    });

    console.log(`🔄 Order ${order_id.slice(0, 8)} assignment updated`);
  }

  getConnectionState(): 'connecting' | 'open' | 'closed' {
    if (!this.eventSource) return 'closed';
    
    switch (this.eventSource.readyState) {
      case EventSource.CONNECTING:
        return 'connecting';
      case EventSource.OPEN:
        return 'open';
      case EventSource.CLOSED:
        return 'closed';
      default:
        return 'closed';
    }
  }
}

// Singleton instance
let realtimeService: RealtimeService | null = null;

export const getRealtimeService = (queryClient: QueryClient): RealtimeService => {
  if (!realtimeService) {
    realtimeService = new RealtimeService(queryClient);
  }
  return realtimeService;
};

export default RealtimeService; 