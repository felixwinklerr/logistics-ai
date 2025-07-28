import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { useOrder } from '../hooks/useOrders';
import { useOrderActions } from '../hooks/useOrderActions';
import { OrderDetails } from '../components/OrderDetails';
import { Order } from '../types';

export const OrderDetailsPage: React.FC = () => {
  const { id: orderId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: order, isLoading, error } = useOrder(orderId || '');
  const { updateStatus } = useOrderActions();

  if (!orderId) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Order not found</h2>
        <p className="text-gray-600 mt-2">The order ID is missing from the URL.</p>
        <Button onClick={() => navigate('/orders')} className="mt-4">
          Back to Orders
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-red-600">Error loading order</h2>
        <p className="text-gray-600 mt-2">{error.message}</p>
        <Button onClick={() => navigate('/orders')} className="mt-4">
          Back to Orders
        </Button>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Order not found</h2>
        <p className="text-gray-600 mt-2">The requested order could not be found.</p>
        <Button onClick={() => navigate('/orders')} className="mt-4">
          Back to Orders
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => navigate('/orders')}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Orders
        </Button>
      </div>

      <OrderDetails
        orderId={orderId}
        order={order as Order}
        onUpdateStatus={(status) => updateStatus(orderId, status)}
        onEdit={() => navigate(`/orders/${orderId}/edit`)}
      />
    </div>
  );
}; 