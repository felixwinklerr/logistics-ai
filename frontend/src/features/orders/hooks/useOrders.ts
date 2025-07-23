import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/shared/hooks/useToast';
import { 
  Order, 
  OrderCreateRequest, 
  OrderUpdateRequest,
  OrderStatus
} from '@/features/orders/types';
import { OrderService } from '@/features/orders/services/orderService';

// Query keys for order management
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters: string) => [...orderKeys.lists(), { filters }] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
  search: (term: string) => [...orderKeys.all, 'search', term] as const,
  export: () => [...orderKeys.all, 'export'] as const,
};

// Orders list query with filtering and pagination
export function useOrders(filters?: {
  page?: number;
  limit?: number;
  status?: OrderStatus;
  search?: string;
  date_from?: string;
  date_to?: string;
  urgent_only?: boolean;
}) {
  return useQuery({
    queryKey: orderKeys.list(JSON.stringify(filters || {})),
    queryFn: () => OrderService.getOrders(filters),
    staleTime: 30000, // 30 seconds
    gcTime: 300000, // 5 minutes (was cacheTime)
  });
}

// Single order query
export function useOrder(orderId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => OrderService.getOrderById(orderId),
    enabled: enabled && !!orderId,
    staleTime: 60000, // 1 minute
    gcTime: 300000, // 5 minutes (was cacheTime)
  });
}

// Create order mutation
export function useCreateOrder() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (orderData: OrderCreateRequest) => OrderService.createOrder(orderData),
    onSuccess: (newOrder: Order) => {
      // Invalidate and refetch orders list
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      
      // Add the new order to cache
      queryClient.setQueryData(orderKeys.detail(newOrder.order_id), newOrder);
      
      toast({
        title: 'Order created successfully',
        description: `Order #${newOrder.order_id.slice(0, 8)} has been created`,
        variant: 'default',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error creating order',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// Update order mutation
export function useUpdateOrder() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ orderId, data }: { orderId: string; data: OrderUpdateRequest }) => 
      OrderService.updateOrder(orderId, data),
    onSuccess: (updatedOrder: Order) => {
      // Update the order in cache
      queryClient.setQueryData(orderKeys.detail(updatedOrder.order_id), updatedOrder);
      
      // Invalidate lists to reflect changes
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      
      toast({
        title: 'Order updated successfully',
        description: `Order #${updatedOrder.order_id.slice(0, 8)} has been updated`,
        variant: 'default',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error updating order',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// Update order status mutation
export function useUpdateOrderStatus() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: OrderStatus }) => 
      OrderService.updateOrderStatus(orderId, status),
    onMutate: async ({ orderId, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: orderKeys.detail(orderId) });

      // Snapshot the previous value
      const previousOrder = queryClient.getQueryData<Order>(orderKeys.detail(orderId));

      // Optimistically update to the new status
      if (previousOrder) {
        queryClient.setQueryData<Order>(orderKeys.detail(orderId), {
          ...previousOrder,
          order_status: status,
          updated_at: new Date().toISOString(),
        });
      }

      // Return a context object with the snapshotted value
      return { previousOrder };
    },
    onError: (error: Error, { orderId }, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousOrder) {
        queryClient.setQueryData(orderKeys.detail(orderId), context.previousOrder);
      }
      
      toast({
        title: 'Error updating order status',
        description: error.message,
        variant: 'destructive',
      });
    },
    onSettled: (updatedOrder) => {
      if (updatedOrder) {
        // Always refetch after error or success to sync with server
        queryClient.invalidateQueries({ queryKey: orderKeys.detail(updatedOrder.order_id) });
        queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      }
    },
    onSuccess: (updatedOrder: Order) => {
      toast({
        title: 'Status updated successfully',
        description: `Order #${updatedOrder.order_id.slice(0, 8)} status changed to ${updatedOrder.order_status}`,
        variant: 'default',
      });
    },
  });
}

// Assign subcontractor mutation
export function useAssignSubcontractor() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ orderId, assignment }: {
      orderId: string;
      assignment: {
        subcontractor_id: string;
        agreed_price: number;
        payment_terms: string;
        special_instructions?: string;
      };
    }) => OrderService.assignSubcontractor(orderId, assignment),
    onSuccess: (updatedOrder: Order) => {
      // Update the order in cache
      queryClient.setQueryData(orderKeys.detail(updatedOrder.order_id), updatedOrder);
      
      // Invalidate lists to reflect changes
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      
      toast({
        title: 'Subcontractor assigned successfully',
        description: `Order #${updatedOrder.order_id.slice(0, 8)} has been assigned`,
        variant: 'default',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error assigning subcontractor',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// Export orders mutation
export function useExportOrders() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: (filters?: any) => OrderService.exportOrders(filters),
    onSuccess: (blob: Blob) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `orders-export-${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: 'Export completed',
        description: 'Orders have been exported successfully',
        variant: 'default',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Export failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
} 