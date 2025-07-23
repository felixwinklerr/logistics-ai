import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { useOrder, useCreateOrder, useUpdateOrder } from '../hooks/useOrders';
import { OrderForm } from '../components/OrderForm';
import { OrderCreateRequest, OrderUpdateRequest } from '../types';

export const OrderFormPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const isEditing = !!orderId;

  // Conditionally fetch order for editing
  const { data: order, isLoading: isLoadingOrder } = useOrder(orderId || '', isEditing);
  
  // Mutations
  const createOrderMutation = useCreateOrder();
  const updateOrderMutation = useUpdateOrder();

  const handleSubmit = async (data: OrderCreateRequest | OrderUpdateRequest) => {
    try {
      if (isEditing && orderId) {
        await updateOrderMutation.mutateAsync({ 
          orderId, 
          data: data as OrderUpdateRequest 
        });
        navigate(`/orders/${orderId}`);
      } else {
        const newOrder = await createOrderMutation.mutateAsync(data as OrderCreateRequest);
        navigate(`/orders/${newOrder.order_id}`);
      }
    } catch (error) {
      console.error('Error saving order:', error);
      // Error handling is done in the mutation hooks via toast
    }
  };

  const handleCancel = () => {
    if (isEditing && orderId) {
      navigate(`/orders/${orderId}`);
    } else {
      navigate('/orders');
    }
  };

  if (isEditing && isLoadingOrder) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={handleCancel}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {isEditing ? 'Back to Order' : 'Back to Orders'}
        </Button>

        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? 'Edit Order' : 'Create New Order'}
        </h1>
      </div>

      <OrderForm
        order={order}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={createOrderMutation.isPending || updateOrderMutation.isPending}
      />
    </div>
  );
}; 