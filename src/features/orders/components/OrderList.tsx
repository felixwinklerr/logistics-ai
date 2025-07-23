import React, { useState } from 'react'
import { Button, Badge, Input } from '@/shared/components/ui'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/shared/components/ui'
import { 
  LayoutGrid, 
  Table as TableIcon, 
  Search, 
  Filter, 
  Plus,
  MapPin,
  Calendar,
  Euro,
  User,
  Truck
} from 'lucide-react'
import { OrderCard } from './OrderCard'
import { useOrders } from '../hooks/useOrders'
import type { Order, OrderStatus, OrderFilters, ViewMode } from '../types'

interface OrderListProps {
  onCreateOrder?: () => void
  onViewOrder?: (orderId: string) => void
  onAssignSubcontractor?: (orderId: string) => void
}

export const OrderList: React.FC<OrderListProps> = ({
  onCreateOrder,
  onViewOrder,
  onAssignSubcontractor,
}) => {
  // State management
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [currentPage, setCurrentPage] = useState(1)
  const [filters, setFilters] = useState<OrderFilters>({})
  const [searchTerm, setSearchTerm] = useState('')

  // Data fetching
  const { data, isLoading, error } = useOrders(currentPage, 20, {
    ...filters,
    search: searchTerm || undefined,
  })

  // Utility functions
  const getStatusColor = (status: OrderStatus): string => {
    const statusColors: Record<OrderStatus, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      assigned: 'bg-blue-100 text-blue-800',
      in_transit: 'bg-purple-100 text-purple-800',
      awaiting_documents: 'bg-orange-100 text-orange-800',
      documents_received: 'bg-indigo-100 text-indigo-800',
      documents_validated: 'bg-cyan-100 text-cyan-800',
      client_invoiced: 'bg-emerald-100 text-emerald-800',
      payment_received: 'bg-green-100 text-green-800',
      subcontractor_paid: 'bg-teal-100 text-teal-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      disputed: 'bg-red-100 text-red-800',
    }
    return statusColors[status] || 'bg-slate-100 text-slate-800'
  }

  const formatStatus = (status: OrderStatus): string => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('ro-RO', {
      day: '2-digit',
      month: '2-digit',
    })
  }

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setCurrentPage(1) // Reset to first page when searching
  }

  const handleViewDetails = (orderId: string) => {
    onViewOrder?.(orderId)
  }

  const handleAssignSubcontractor = (orderId: string) => {
    onAssignSubcontractor?.(orderId)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Failed to load orders. Please try again.</p>
      </div>
    )
  }

  const orders = data?.orders || []
  const totalPages = data?.total_pages || 1

  return (
    <div className="space-y-6">
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Orders</h1>
          <p className="text-slate-600">
            Manage your freight forwarding orders ({data?.total || 0} total)
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {onCreateOrder && (
            <Button onClick={onCreateOrder} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              New Order
            </Button>
          )}
        </div>
      </div>

      {/* Filters and search */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search orders..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10 w-64"
            />
          </div>
          
          <Button variant="outline" size="sm">
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
          <Button
            variant={viewMode === 'table' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('table')}
            className="px-3"
          >
            <TableIcon className="w-4 h-4 mr-1" />
            Table
          </Button>
          <Button
            variant={viewMode === 'card' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('card')}
            className="px-3"
          >
            <LayoutGrid className="w-4 h-4 mr-1" />
            Cards
          </Button>
        </div>
      </div>

      {/* Content based on view mode */}
      {viewMode === 'table' ? (
        /* Table View - Primary interface */
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead className="font-semibold">Order</TableHead>
                <TableHead className="font-semibold">Client</TableHead>
                <TableHead className="font-semibold">Route</TableHead>
                <TableHead className="font-semibold">Status</TableHead>
                <TableHead className="font-semibold">Carrier</TableHead>
                <TableHead className="font-semibold">Dates</TableHead>
                <TableHead className="font-semibold text-right">Value</TableHead>
                <TableHead className="font-semibold">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.map((order) => (
                <TableRow key={order.order_id} className="hover:bg-slate-50">
                  <TableCell>
                    <div>
                      <div className="font-medium text-slate-900">
                        #{order.order_id.slice(0, 8).toUpperCase()}
                      </div>
                      <div className="text-sm text-slate-500">
                        {formatDate(order.created_at)}
                      </div>
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div>
                      <div className="font-medium text-slate-900 max-w-32 truncate">
                        {order.client_company_name}
                      </div>
                      <div className="text-sm text-slate-500">
                        {order.client_vat_number}
                      </div>
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center text-sm">
                        <MapPin className="w-3 h-3 mr-1 text-emerald-500" />
                        <span className="max-w-24 truncate">
                          {order.pickup_city || order.pickup_postcode || 'Romania'}
                        </span>
                      </div>
                      <div className="flex items-center text-sm">
                        <MapPin className="w-3 h-3 mr-1 text-blue-500" />
                        <span className="max-w-24 truncate">
                          {order.delivery_city || order.delivery_postcode || 'Romania'}
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <Badge className={`text-xs ${getStatusColor(order.order_status)}`}>
                      {formatStatus(order.order_status)}
                    </Badge>
                  </TableCell>
                  
                  <TableCell>
                    {order.subcontractor_company ? (
                      <div className="flex items-center text-sm">
                        <Truck className="w-3 h-3 mr-1 text-slate-400" />
                        <span className="max-w-24 truncate">{order.subcontractor_company}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400">Not assigned</span>
                    )}
                  </TableCell>
                  
                  <TableCell>
                    <div className="text-sm">
                      <div className="flex items-center">
                        <Calendar className="w-3 h-3 mr-1 text-slate-400" />
                        {formatDate(order.pickup_date_start)}
                      </div>
                    </div>
                  </TableCell>
                  
                  <TableCell className="text-right">
                    <div className="font-semibold text-emerald-600">
                      {formatCurrency(order.client_offered_price)}
                    </div>
                    {order.profit_margin && order.profit_margin > 0 && (
                      <div className="text-sm text-slate-500">
                        +{formatCurrency(order.profit_margin)}
                      </div>
                    )}
                  </TableCell>
                  
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewDetails(order.order_id)}
                      >
                        View
                      </Button>
                      {order.order_status === 'pending' && !order.subcontractor_id && (
                        <Button
                          size="sm"
                          onClick={() => handleAssignSubcontractor(order.order_id)}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          Assign
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {orders.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-500">No orders found.</p>
            </div>
          )}
        </div>
      ) : (
        /* Card View - Alternative interface */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {orders.map((order) => (
            <OrderCard
              key={order.order_id}
              order={order}
              onViewDetails={handleViewDetails}
              onAssignSubcontractor={onAssignSubcontractor}
            />
          ))}
          
          {orders.length === 0 && (
            <div className="col-span-full text-center py-12">
              <p className="text-slate-500">No orders found.</p>
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          
          <span className="flex items-center px-3 text-sm text-slate-600">
            Page {currentPage} of {totalPages}
          </span>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
} 