import React, { useState } from 'react';
import { 
  Search, 
  Filter, 
  Download, 
  ChevronLeft, 
  ChevronRight,
  MapPin,
  Package,
  AlertTriangle,
  LayoutGrid,
  List as ListIcon
} from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Card, CardContent } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/shared/components/ui/dialog';
import { Order, OrderStatus } from '@/features/orders/types';
import { OrderCard } from './OrderCard';

// Status display configuration matching Romanian freight forwarder workflow
const statusConfig: Record<OrderStatus, { 
  label: string; 
  color: string; 
  priority: number; 
}> = {
  pending: { 
    label: 'Pending Assignment', 
    color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    priority: 1 
  },
  assigned: { 
    label: 'Assigned to Carrier', 
    color: 'bg-blue-100 text-blue-800 border-blue-300',
    priority: 2 
  },
  in_transit: { 
    label: 'In Transit', 
    color: 'bg-purple-100 text-purple-800 border-purple-300',
    priority: 4 
  },
  awaiting_documents: { 
    label: 'Awaiting POD', 
    color: 'bg-orange-100 text-orange-800 border-orange-300',
    priority: 6 
  },
  documents_received: { 
    label: 'Documents Received', 
    color: 'bg-teal-100 text-teal-800 border-teal-300',
    priority: 7 
  },
  documents_validated: { 
    label: 'Documents Valid', 
    color: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    priority: 8 
  },
  client_invoiced: { 
    label: 'Client Invoiced', 
    color: 'bg-cyan-100 text-cyan-800 border-cyan-300',
    priority: 9 
  },
  payment_received: { 
    label: 'Payment Received', 
    color: 'bg-lime-100 text-lime-800 border-lime-300',
    priority: 10 
  },
  subcontractor_paid: { 
    label: 'Carrier Paid', 
    color: 'bg-green-100 text-green-800 border-green-300',
    priority: 11 
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-slate-100 text-slate-800 border-slate-300',
    priority: 12 
  },
  cancelled: { 
    label: 'Cancelled', 
    color: 'bg-red-100 text-red-800 border-red-300',
    priority: 0 
  },
  disputed: { 
    label: 'Disputed', 
    color: 'bg-red-100 text-red-800 border-red-300',
    priority: 0 
  }
};

// Search and filter interface
interface OrderFilters {
  searchTerm: string;
  status: OrderStatus | 'all';
  dateFrom: string;
  dateTo: string;
  urgentOnly: boolean;
}

interface OrderListProps {
  orders: Order[];
  isLoading: boolean;
  onOrderSelect: (orderId: string) => void;
  onCreateOrder: () => void;
  onAssignSubcontractor: (orderId: string) => void;
  totalCount: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onFiltersChange: (filters: Partial<OrderFilters>) => void;
  onExport: () => void;
}

export const OrderList: React.FC<OrderListProps> = ({
  orders,
  isLoading,
  onOrderSelect,
  onCreateOrder,
  onAssignSubcontractor,
  totalCount,
  currentPage,
  pageSize,
  onPageChange,
  onFiltersChange,
  onExport
}) => {
  // State for view mode and filters
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [filters, setFilters] = useState<OrderFilters>({
    searchTerm: '',
    status: 'all',
    dateFrom: '',
    dateTo: '',
    urgentOnly: false
  });
  const [isFilterDialogOpen, setIsFilterDialogOpen] = useState(false);

  // Calculate pagination
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  // Update filters and notify parent
  const updateFilters = (newFilters: Partial<OrderFilters>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    onFiltersChange(updatedFilters);
  };

  // Check if order is urgent (>2 days pending)
  const isOrderUrgent = (order: Order): boolean => {
    if (order.order_status !== 'pending') return false;
    const createdDate = new Date(order.created_at);
    const now = new Date();
    const daysDiff = (now.getTime() - createdDate.getTime()) / (1000 * 3600 * 24);
    return daysDiff > 2;
  };

  // Format date for display
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ro-RO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format currency for Romanian locale
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  // Get status badge component
  const getStatusBadge = (status: OrderStatus, isUrgent: boolean = false) => {
    const config = statusConfig[status];
    return (
      <div className="flex items-center space-x-2">
        <Badge className={`${config.color} text-xs font-medium px-2 py-1 border`}>
          {config.label}
        </Badge>
        {isUrgent && (
          <AlertTriangle className="w-4 h-4 text-red-500" />
        )}
      </div>
    );
  };

  // Render table header
  const renderTableHeader = () => (
    <thead className="bg-slate-50">
      <tr>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Order Details
        </th>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Route
        </th>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Status
        </th>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Price
        </th>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Carrier
        </th>
        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
          Created
        </th>
        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
          Actions
        </th>
      </tr>
    </thead>
  );

  // Render table row for each order
  const renderTableRow = (order: Order) => {
    const isUrgent = isOrderUrgent(order);
    
    return (
      <tr 
        key={order.order_id} 
        className={`border-b border-slate-200 hover:bg-slate-50 cursor-pointer ${
          isUrgent ? 'bg-red-50 border-red-200' : ''
        }`}
        onClick={() => onOrderSelect(order.order_id)}
      >
        <td className="px-4 py-4">
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-slate-900">
                #{order.order_id.slice(0, 8)}
              </span>
              {isUrgent && <AlertTriangle className="w-4 h-4 text-red-500" />}
            </div>
            <span className="text-sm text-slate-500">{order.client_company_name}</span>
            <span className="text-xs text-slate-400">{order.client_vat_number}</span>
          </div>
        </td>

        <td className="px-4 py-4">
          <div className="flex flex-col space-y-1">
            <div className="flex items-center text-sm text-slate-600">
              <MapPin className="w-3 h-3 mr-1 text-green-500" />
              <span>{order.pickup_city} ({order.pickup_postcode})</span>
            </div>
            <div className="flex items-center text-sm text-slate-600">
              <MapPin className="w-3 h-3 mr-1 text-red-500" />
              <span>{order.delivery_city} ({order.delivery_postcode})</span>
            </div>
          </div>
        </td>

        <td className="px-4 py-4">
          {getStatusBadge(order.order_status, isUrgent)}
        </td>

        <td className="px-4 py-4">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-slate-900">
              {formatCurrency(order.client_offered_price)}
            </span>
            {order.subcontractor_price && (
              <span className="text-xs text-slate-500">
                Cost: {formatCurrency(order.subcontractor_price)}
              </span>
            )}
          </div>
        </td>

        <td className="px-4 py-4">
          <div className="text-sm text-slate-600">
            {order.subcontractor_company || (
              <span className="text-slate-400 italic">Not assigned</span>
            )}
          </div>
        </td>

        <td className="px-4 py-4">
          <div className="text-sm text-slate-600">
            {formatDate(order.created_at)}
          </div>
        </td>

        <td className="px-4 py-4 text-right">
          <div className="flex items-center justify-end space-x-2">
            {order.order_status === 'pending' && (
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onAssignSubcontractor(order.order_id);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                Assign
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                onOrderSelect(order.order_id);
              }}
            >
              View
            </Button>
          </div>
        </td>
      </tr>
    );
  };

  // Main render
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading orders...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with search, filters, and view toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-slate-900">
            Orders ({totalCount})
          </h2>
          
          {/* View Mode Toggle */}
          <div className="flex items-center space-x-1 bg-slate-100 rounded-md p-1">
            <Button
              size="sm"
              variant={viewMode === 'table' ? 'default' : 'ghost'}
              onClick={() => setViewMode('table')}
              className="h-8 px-3"
            >
              <ListIcon className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'cards' ? 'default' : 'ghost'}
              onClick={() => setViewMode('cards')}
              className="h-8 px-3"
            >
              <LayoutGrid className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Button variant="outline" onClick={onExport}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={onCreateOrder}>
            Create Order
          </Button>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
          <Input
            placeholder="Search orders, companies, VAT numbers..."
            value={filters.searchTerm}
            onChange={(e) => updateFilters({ searchTerm: e.target.value })}
            className="pl-10"
          />
        </div>

        <Dialog open={isFilterDialogOpen} onOpenChange={setIsFilterDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline">
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Filter Orders</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div>
                <label className="block text-sm font-medium mb-2">Status</label>
                <select 
                  value={filters.status}
                  onChange={(e) => updateFilters({ status: e.target.value as OrderStatus | 'all' })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md"
                >
                  <option value="all">All Statuses</option>
                  {Object.entries(statusConfig).map(([key, config]) => (
                    <option key={key} value={key}>{config.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-2">Date From</label>
                  <Input
                    type="date"
                    value={filters.dateFrom}
                    onChange={(e) => updateFilters({ dateFrom: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Date To</label>
                  <Input
                    type="date"
                    value={filters.dateTo}
                    onChange={(e) => updateFilters({ dateTo: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="urgentOnly"
                  checked={filters.urgentOnly}
                  onChange={(e) => updateFilters({ urgentOnly: e.target.checked })}
                  className="rounded border-slate-300"
                />
                <label htmlFor="urgentOnly" className="text-sm font-medium">
                  Show only urgent orders (&gt;2 days pending)
                </label>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => {
                    const resetFilters = {
                      searchTerm: '',
                      status: 'all' as const,
                      dateFrom: '',
                      dateTo: '',
                      urgentOnly: false
                    };
                    setFilters(resetFilters);
                    onFiltersChange(resetFilters);
                  }}
                >
                  Clear
                </Button>
                <Button onClick={() => setIsFilterDialogOpen(false)}>
                  Apply
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Orders Content */}
      {orders.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Package className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">No orders found</h3>
            <p className="text-slate-600 mb-4">
              {filters.searchTerm || filters.status !== 'all' ? 
                'Try adjusting your search or filters' : 
                'Get started by creating your first order'
              }
            </p>
            <Button onClick={onCreateOrder}>Create Order</Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Render based on view mode */}
          {viewMode === 'table' ? (
            <Card>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  {renderTableHeader()}
                  <tbody className="bg-white divide-y divide-slate-200">
                    {orders.map(renderTableRow)}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {orders.map((order) => (
                <OrderCard
                  key={order.order_id}
                  order={order}
                  onViewDetails={() => onOrderSelect(order.order_id)}
                  onAssignSubcontractor={() => onAssignSubcontractor(order.order_id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 sm:px-6">
              <div className="flex flex-1 justify-between sm:hidden">
                <Button
                  variant="outline"
                  onClick={() => onPageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => onPageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
              
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-slate-700">
                    Showing <span className="font-medium">{startIndex}</span> to{' '}
                    <span className="font-medium">{endIndex}</span> of{' '}
                    <span className="font-medium">{totalCount}</span> results
                  </p>
                </div>
                <div>
                  <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="rounded-r-none"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + 1;
                      return (
                        <Button
                          key={page}
                          variant={currentPage === page ? "default" : "outline"}
                          size="sm"
                          onClick={() => onPageChange(page)}
                          className="rounded-none"
                        >
                          {page}
                        </Button>
                      );
                    })}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="rounded-l-none"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
