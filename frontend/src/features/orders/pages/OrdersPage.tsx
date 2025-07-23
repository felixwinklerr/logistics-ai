import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { OrderList } from '@/features/orders/components/OrderList';
import { useOrders, useExportOrders } from '@/features/orders/hooks/useOrders';
import { OrderStatus, OrderListResponse } from '@/features/orders/types';

interface OrderFilters {
  searchTerm: string;
  status: OrderStatus | 'all';
  dateFrom: string;
  dateTo: string;
  urgentOnly: boolean;
}

export const OrdersPage: React.FC = () => {
  const navigate = useNavigate();
  const exportOrdersMutation = useExportOrders();

  // State for pagination and filters
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [filters, setFilters] = useState<OrderFilters>({
    searchTerm: '',
    status: 'all',
    dateFrom: '',
    dateTo: '',
    urgentOnly: false
  });

  // Build query parameters for API
  const queryParams = {
    page: currentPage,
    limit: pageSize,
    ...(filters.status !== 'all' && { status: filters.status }),
    ...(filters.searchTerm && { search: filters.searchTerm }),
    ...(filters.dateFrom && { date_from: filters.dateFrom }),
    ...(filters.dateTo && { date_to: filters.dateTo }),
    ...(filters.urgentOnly && { urgent_only: true }),
  };

  // Fetch orders with current filters
  const { data: ordersResponse, isLoading, error } = useOrders(queryParams);

  // Extract data with defaults - fix type issues
  const typedResponse = ordersResponse as OrderListResponse | undefined;
  const orders = typedResponse?.orders || [];
  const totalCount = typedResponse?.total || 0;

  // Handle navigation to order details
  const handleOrderSelect = useCallback((orderId: string) => {
    navigate(`/orders/${orderId}`);
  }, [navigate]);

  // Handle creating new order
  const handleCreateOrder = useCallback(() => {
    navigate('/orders/new');
  }, [navigate]);

  // Handle subcontractor assignment
  const handleAssignSubcontractor = useCallback((orderId: string) => {
    // TODO: Open subcontractor assignment modal/page
    console.log('Assign subcontractor to order:', orderId);
    navigate(`/orders/${orderId}/assign`);
  }, [navigate]);

  // Handle filter changes
  const handleFiltersChange = useCallback((newFilters: Partial<OrderFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setCurrentPage(1); // Reset to first page when filters change
  }, []);

  // Handle page changes
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  // Handle export
  const handleExport = useCallback(() => {
    const exportFilters = {
      ...(filters.status !== 'all' && { status: filters.status }),
      ...(filters.searchTerm && { search: filters.searchTerm }),
      ...(filters.dateFrom && { date_from: filters.dateFrom }),
      ...(filters.dateTo && { date_to: filters.dateTo }),
      ...(filters.urgentOnly && { urgent_only: true }),
    };
    
    exportOrdersMutation.mutate(exportFilters);
  }, [filters, exportOrdersMutation]);

  // Error handling
  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">
          <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <h3 className="text-lg font-medium text-slate-900 mb-2">Error loading orders</h3>
          <p className="text-slate-600">{error.message}</p>
        </div>
        <button 
          onClick={() => window.location.reload()} 
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <OrderList
        orders={orders}
        isLoading={isLoading}
        onOrderSelect={handleOrderSelect}
        onCreateOrder={handleCreateOrder}
        onAssignSubcontractor={handleAssignSubcontractor}
        totalCount={totalCount}
        currentPage={currentPage}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        onFiltersChange={handleFiltersChange}
        onExport={handleExport}
      />
    </div>
  );
}; 