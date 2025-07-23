import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useUIStore } from '@/shared/stores/uiStore'
import { orderService } from '../services/orderService'
import type { 
  Order, 
  OrderCreateRequest, 
  OrderUpdateRequest, 
  OrderFilters,
  OrderListResponse 
} from '../types'

// Query Keys
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters?: OrderFilters, page?: number, perPage?: number) => 
    [...orderKeys.lists(), { filters, page, perPage }] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
  metrics: () => [...orderKeys.all, 'metrics'] as const,
}

// Orders List Hook
export function useOrders(
  page: number = 1,
  perPage: number = 20,
  filters?: OrderFilters
) {
  return useQuery({
    queryKey: orderKeys.list(filters, page, perPage),
    queryFn: () => orderService.getOrders(page, perPage, filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (renamed from cacheTime)
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

// Single Order Hook
export function useOrder(orderId: string) {
  return useQuery({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => orderService.getOrder(orderId),
    enabled: !!orderId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000,
  })
}

// Order Metrics Hook
export function useOrderMetrics() {
  return useQuery({
    queryKey: orderKeys.metrics(),
    queryFn: () => orderService.getOrderMetrics(),
    staleTime: 5 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
  })
}

// Create Order Mutation
export function useCreateOrder() {
  const queryClient = useQueryClient()
  const { addNotification } = useUIStore()

  return useMutation({
    mutationFn: (orderData: OrderCreateRequest) => orderService.createOrder(orderData),
    onSuccess: (newOrder) => {
      // Invalidate and refetch orders list
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() })
      
      // Add the new order to the cache
      queryClient.setQueryData(orderKeys.detail(newOrder.order_id), newOrder)
      
      // Show success notification
      addNotification({
        type: 'success',
        title: 'Order Created',
        message: `Order ${newOrder.order_id.slice(0, 8)} has been created successfully.`,
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Create Order',
        message: error.response?.data?.message || 'An error occurred while creating the order.',
      })
    },
  })
}

// Update Order Mutation
export function useUpdateOrder() {
  const queryClient = useQueryClient()
  const { addNotification } = useUIStore()

  return useMutation({
    mutationFn: ({ orderId, data }: { orderId: string; data: OrderUpdateRequest }) =>
      orderService.updateOrder(orderId, data),
    onSuccess: (updatedOrder) => {
      // Update the specific order in cache
      queryClient.setQueryData(orderKeys.detail(updatedOrder.order_id), updatedOrder)
      
      // Invalidate orders list to show updated data
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() })
      
      addNotification({
        type: 'success',
        title: 'Order Updated',
        message: 'Order has been updated successfully.',
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Update Order',
        message: error.response?.data?.message || 'An error occurred while updating the order.',
      })
    },
  })
}

// Delete Order Mutation
export function useDeleteOrder() {
  const queryClient = useQueryClient()
  const { addNotification } = useUIStore()

  return useMutation({
    mutationFn: (orderId: string) => orderService.deleteOrder(orderId),
    onSuccess: (_, orderId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: orderKeys.detail(orderId) })
      
      // Invalidate orders list
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() })
      
      addNotification({
        type: 'success',
        title: 'Order Deleted',
        message: 'Order has been deleted successfully.',
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Delete Order',
        message: error.response?.data?.message || 'An error occurred while deleting the order.',
      })
    },
  })
}

// Update Order Status Mutation
export function useUpdateOrderStatus() {
  const queryClient = useQueryClient()
  const { addNotification } = useUIStore()

  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: string }) =>
      orderService.updateOrderStatus(orderId, status),
    onSuccess: (updatedOrder) => {
      // Update the specific order in cache
      queryClient.setQueryData(orderKeys.detail(updatedOrder.order_id), updatedOrder)
      
      // Invalidate orders list and metrics
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() })
      queryClient.invalidateQueries({ queryKey: orderKeys.metrics() })
      
      addNotification({
        type: 'success',
        title: 'Status Updated',
        message: `Order status updated to ${updatedOrder.order_status}.`,
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Update Status',
        message: error.response?.data?.message || 'An error occurred while updating the status.',
      })
    },
  })
}

// Assign Subcontractor Mutation
export function useAssignSubcontractor() {
  const queryClient = useQueryClient()
  const { addNotification } = useUIStore()

  return useMutation({
    mutationFn: (assignmentData: any) => orderService.assignSubcontractor(assignmentData),
    onSuccess: (updatedOrder) => {
      // Update the specific order in cache
      queryClient.setQueryData(orderKeys.detail(updatedOrder.order_id), updatedOrder)
      
      // Invalidate orders list and metrics
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() })
      queryClient.invalidateQueries({ queryKey: orderKeys.metrics() })
      
      addNotification({
        type: 'success',
        title: 'Subcontractor Assigned',
        message: `Subcontractor has been assigned to order ${updatedOrder.order_id.slice(0, 8)}.`,
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Assignment Failed',
        message: error.response?.data?.message || 'Failed to assign subcontractor.',
      })
    },
  })
} 