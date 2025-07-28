import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { OrderList } from '@/features/orders/components/OrderList';
import { useOrders, useExportOrders, useAssignSubcontractor } from '@/features/orders/hooks/useOrders';
import { OrderStatus, OrderListResponse } from '@/features/orders/types';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { useToast } from '@/shared/hooks/useToast';

interface OrderFilters {
  searchTerm: string;
  status: OrderStatus | 'all';
  dateFrom: string;
  dateTo: string;
  urgentOnly: boolean;
}

interface AssignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: string | null;
  onAssign: (assignment: any) => void;
}

const AssignmentModal: React.FC<AssignmentModalProps> = ({ isOpen, onClose, orderId, onAssign }) => {
  const [assignment, setAssignment] = useState({
    subcontractor_id: '',
    agreed_price: '',
    payment_terms: '30',
    special_instructions: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment.subcontractor_id || !assignment.agreed_price) {
      return;
    }
    
    onAssign({
      subcontractor_id: assignment.subcontractor_id,
      agreed_price: parseFloat(assignment.agreed_price),
      payment_terms: assignment.payment_terms,
      special_instructions: assignment.special_instructions || undefined
    });
    
    // Reset form
    setAssignment({
      subcontractor_id: '',
      agreed_price: '',
      payment_terms: '30',
      special_instructions: ''
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Subcontractor</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Subcontractor ID</label>
            <Input
              type="text"
              value={assignment.subcontractor_id}
              onChange={(e) => setAssignment(prev => ({ ...prev, subcontractor_id: e.target.value }))}
              placeholder="Enter subcontractor ID"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Agreed Price (EUR)</label>
            <Input
              type="number"
              step="0.01"
              value={assignment.agreed_price}
              onChange={(e) => setAssignment(prev => ({ ...prev, agreed_price: e.target.value }))}
              placeholder="Enter agreed price"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Payment Terms (days)</label>
            <Input
              type="number"
              value={assignment.payment_terms}
              onChange={(e) => setAssignment(prev => ({ ...prev, payment_terms: e.target.value }))}
              placeholder="Payment terms in days"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Special Instructions</label>
            <textarea
              className="w-full px-3 py-2 border border-slate-300 rounded-md resize-none"
              rows={3}
              value={assignment.special_instructions}
              onChange={(e) => setAssignment(prev => ({ ...prev, special_instructions: e.target.value }))}
              placeholder="Optional special instructions"
            />
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">
              Assign Subcontractor
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export const OrdersPage: React.FC = () => {
  const navigate = useNavigate();
  const exportOrdersMutation = useExportOrders();
  const assignSubcontractorMutation = useAssignSubcontractor();
  const { toast } = useToast();

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

  // Assignment modal state
  const [assignmentModal, setAssignmentModal] = useState<{
    isOpen: boolean;
    orderId: string | null;
  }>({
    isOpen: false,
    orderId: null
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

  // Handle subcontractor assignment - open modal instead of navigation
  const handleAssignSubcontractor = useCallback((orderId: string) => {
    setAssignmentModal({
      isOpen: true,
      orderId: orderId
    });
  }, []);

  // Handle assignment submission
  const handleAssignmentSubmit = useCallback((assignment: any) => {
    if (!assignmentModal.orderId) return;

    assignSubcontractorMutation.mutate({
      orderId: assignmentModal.orderId,
      assignment
    }, {
      onSuccess: () => {
        setAssignmentModal({ isOpen: false, orderId: null });
        toast({
          title: 'Subcontractor Assigned',
          description: 'The subcontractor has been successfully assigned to the order.',
          variant: 'default',
        });
      },
      onError: (error: any) => {
        toast({
          title: 'Assignment Failed',
          description: error.message || 'Failed to assign subcontractor. Please try again.',
          variant: 'destructive',
        });
      }
    });
  }, [assignmentModal.orderId, assignSubcontractorMutation, toast]);

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
      
      <AssignmentModal
        isOpen={assignmentModal.isOpen}
        onClose={() => setAssignmentModal({ isOpen: false, orderId: null })}
        orderId={assignmentModal.orderId}
        onAssign={handleAssignmentSubmit}
      />
    </div>
  );
}; 