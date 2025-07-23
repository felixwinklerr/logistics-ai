import React from 'react'
import { Card, CardContent, CardHeader, Badge, Button } from '@/shared/components/ui'
import { MapPin, Truck, Calendar, Euro, User, Package, MoreVertical } from 'lucide-react'
import type { Order, OrderStatus } from '../types'

interface OrderCardProps {
  order: Order
  onViewDetails: (orderId: string) => void
  onAssignSubcontractor?: (orderId: string) => void
  onUpdateStatus?: (orderId: string, status: OrderStatus) => void
  className?: string
}

export const OrderCard: React.FC<OrderCardProps> = ({
  order,
  onViewDetails,
  onAssignSubcontractor,
  onUpdateStatus,
  className = '',
}) => {
  const getStatusColor = (status: OrderStatus): string => {
    const statusColors: Record<OrderStatus, string> = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      assigned: 'bg-blue-100 text-blue-800 border-blue-200',
      in_transit: 'bg-purple-100 text-purple-800 border-purple-200',
      awaiting_documents: 'bg-orange-100 text-orange-800 border-orange-200',
      documents_received: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      documents_validated: 'bg-cyan-100 text-cyan-800 border-cyan-200',
      client_invoiced: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      payment_received: 'bg-green-100 text-green-800 border-green-200',
      subcontractor_paid: 'bg-teal-100 text-teal-800 border-teal-200',
      completed: 'bg-green-100 text-green-800 border-green-200',
      cancelled: 'bg-red-100 text-red-800 border-red-200',
      disputed: 'bg-red-100 text-red-800 border-red-200',
    }
    return statusColors[status] || 'bg-slate-100 text-slate-800 border-slate-200'
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
    if (!dateString) return 'TBD'
    return new Date(dateString).toLocaleDateString('ro-RO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  }

  const canAssignSubcontractor = order.order_status === 'pending' && !order.subcontractor_id
  const profitMargin = order.profit_margin || 0
  const profitPercentage = order.profit_percentage || 0

  return (
    <Card className={`hover:shadow-lg transition-all duration-200 border-slate-200 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-slate-900">
              #{order.order_id.slice(0, 8).toUpperCase()}
            </h3>
            <Badge className={`text-xs font-medium border ${getStatusColor(order.order_status)}`}>
              {formatStatus(order.order_status)}
            </Badge>
          </div>
          
          <div className="text-right space-y-1">
            <div className="flex items-center text-lg font-bold text-emerald-600">
              <Euro className="w-4 h-4 mr-1" />
              {formatCurrency(order.client_offered_price)}
            </div>
            {profitMargin > 0 && (
              <div className="text-sm text-slate-500">
                Profit: {formatCurrency(profitMargin)} ({profitPercentage.toFixed(1)}%)
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Client Information */}
        <div className="space-y-2">
          <div className="flex items-center text-sm">
            <User className="w-4 h-4 mr-2 text-slate-400" />
            <span className="font-medium text-slate-900">{order.client_company_name}</span>
          </div>
          <div className="text-xs text-slate-500 ml-6">
            VAT: {order.client_vat_number}
          </div>
        </div>

        {/* Route Information */}
        <div className="space-y-3">
          <div className="flex items-start text-sm">
            <MapPin className="w-4 h-4 mr-2 text-emerald-500 mt-0.5" />
            <div className="space-y-1">
              <div>
                <span className="font-medium text-slate-700">From:</span>
                <span className="ml-1 text-slate-600">
                  {order.pickup_city ? `${order.pickup_city}, ` : ''}{order.pickup_postcode || 'Romania'}
                </span>
              </div>
              <div className="text-xs text-slate-500">{order.pickup_address}</div>
            </div>
          </div>
          
          <div className="flex items-start text-sm">
            <MapPin className="w-4 h-4 mr-2 text-blue-500 mt-0.5" />
            <div className="space-y-1">
              <div>
                <span className="font-medium text-slate-700">To:</span>
                <span className="ml-1 text-slate-600">
                  {order.delivery_city ? `${order.delivery_city}, ` : ''}{order.delivery_postcode || 'Romania'}
                </span>
              </div>
              <div className="text-xs text-slate-500">{order.delivery_address}</div>
            </div>
          </div>
        </div>

        {/* Cargo Information */}
        {(order.cargo_ldm || order.cargo_weight_kg || order.cargo_pallets) && (
          <div className="flex items-center text-sm text-slate-600 bg-slate-50 p-2 rounded-lg">
            <Package className="w-4 h-4 mr-2 text-slate-400" />
            <div className="flex gap-4 text-xs">
              {order.cargo_ldm && <span>LDM: {order.cargo_ldm}m</span>}
              {order.cargo_weight_kg && <span>Weight: {order.cargo_weight_kg}kg</span>}
              {order.cargo_pallets && <span>Pallets: {order.cargo_pallets}</span>}
            </div>
          </div>
        )}

        {/* Subcontractor Information */}
        {order.subcontractor_company && (
          <div className="flex items-center text-sm">
            <Truck className="w-4 h-4 mr-2 text-slate-400" />
            <div>
              <span className="font-medium text-slate-700">Carrier:</span>
              <span className="ml-1 text-slate-600">{order.subcontractor_company}</span>
              {order.truck_plate && (
                <span className="ml-2 text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                  {order.truck_plate}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Date Information */}
        <div className="flex items-center text-sm text-slate-600">
          <Calendar className="w-4 h-4 mr-2 text-slate-400" />
          <div className="flex gap-4 text-xs">
            <span>Pickup: {formatDate(order.pickup_date_start)}</span>
            {order.delivery_date_start && (
              <span>Delivery: {formatDate(order.delivery_date_start)}</span>
            )}
          </div>
        </div>

        {/* Special Requirements */}
        {order.special_requirements && (
          <div className="text-xs text-amber-700 bg-amber-50 p-2 rounded-lg border border-amber-200">
            <strong>Special Requirements:</strong> {order.special_requirements}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t border-slate-100">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewDetails(order.order_id)}
            className="flex-1"
          >
            View Details
          </Button>
          
          {canAssignSubcontractor && onAssignSubcontractor && (
            <Button
              size="sm"
              onClick={() => onAssignSubcontractor(order.order_id)}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
            >
              Assign Carrier
            </Button>
          )}
          
          {order.order_status !== 'completed' && order.order_status !== 'cancelled' && (
            <Button variant="ghost" size="sm" className="px-2">
              <MoreVertical className="w-4 h-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
} 