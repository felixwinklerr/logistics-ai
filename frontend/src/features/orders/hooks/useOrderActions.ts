import { useUpdateOrder, useUpdateOrderStatus } from './useOrders';

export const useOrderActions = () => {
  const updateOrderMutation = useUpdateOrder();
  const updateStatusMutation = useUpdateOrderStatus();

  const updateOrder = async (orderId: string, data: any) => {
    return updateOrderMutation.mutateAsync({ orderId, data });
  };

  const updateStatus = async (orderId: string, status: any) => {
    return updateStatusMutation.mutateAsync({ orderId, status });
  };

  return {
    updateOrder,
    updateStatus,
    isUpdating: updateOrderMutation.isPending || updateStatusMutation.isPending,
  };
}; 