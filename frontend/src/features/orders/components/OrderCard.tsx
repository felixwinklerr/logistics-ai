import React, { useState } from 'react';
import { Clock, MapPin, Truck, Euro, Calendar, Package, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { 
  OrderStatus, 
  ORDER_STATUS_CONFIG,
  formatCurrency,
  formatDate,
  type OrderCardProps
} from '../types';

export const OrderCard: React.FC<OrderCardProps> = ({
  order,
  onViewDetails,
  onEdit,
  onAssignSubcontractor,
  onUpdateStatus,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  
  const statusConfig = ORDER_STATUS_CONFIG[order.order_status];
  
  const handleAction = async (action: () => void) => {
    setIsLoading(true);
    try {
      await action();
    } finally {
      setIsLoading(false);
    }
  };

  const formatLocation = (address: string, city?: string, postcode?: string): string => {
    const parts = [city, postcode].filter(Boolean);
    return parts.length > 0 ? `${city || ''}, ${postcode || ''}`.replace(/, $/, '') : address;
  };

  const calculateDaysAgo = (date: string): number => {
    const createdDate = new Date(date);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - createdDate.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const isUrgent = order.order_status === OrderStatus.PENDING && calculateDaysAgo(order.created_at) > 2;
  const hasProfit = order.profit_margin !== undefined && order.profit_margin !== null;
  const isProfitable = hasProfit && order.profit_margin! > 0;

  return (
    <Card className={`relative overflow-hidden transition-all duration-200 hover:shadow-lg ${
      isUrgent ? 'border-l-4 border-l-red-500 bg-red-50/30' : 'hover:border-blue-200'
    }`}>
      {/* Urgent indicator */}
      {isUrgent && (
        <div className="absolute top-2 right-2">
          <AlertTriangle className="w-5 h-5 text-red-500" />
        </div>
      )}

      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-semibold text-slate-900 truncate">
                #{order.order_id.slice(0, 8)}
              </h3>
              <Badge 
                variant="secondary" 
                className={`${statusConfig.color} ${statusConfig.bgColor} border font-medium`}
              >
                {statusConfig.label}
              </Badge>
            </div>
            
            <p className="text-sm font-medium text-slate-700 truncate mb-1">
              {order.client_company_name}
            </p>
            
            <p className="text-xs text-slate-500">
              VAT: {order.client_vat_number}
            </p>
          </div>

          <div className="text-right flex-shrink-0">
            <div className="flex items-center text-lg font-bold text-emerald-600 mb-1">
              <Euro className="w-4 h-4 mr-1" />
              {formatCurrency(order.client_offered_price)}
            </div>
            
            {hasProfit && (
              <div className={`text-sm font-medium ${
                isProfitable ? 'text-emerald-600' : 'text-red-600'
              }`}>
                Margin: {formatCurrency(order.profit_margin!)}
                {order.profit_percentage && (
                  <span className="text-xs ml-1">
                    ({order.profit_percentage.toFixed(1)}%)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Route Information */}
        <div className="space-y-3 mb-4">
          <div className="flex items-start gap-2">
            <MapPin className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700">From:</p>
              <p className="text-sm text-slate-600 truncate">
                {formatLocation(order.pickup_address, order.pickup_city, order.pickup_postcode)}
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-2">
            <MapPin className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700">To:</p>
              <p className="text-sm text-slate-600 truncate">
                {formatLocation(order.delivery_address, order.delivery_city, order.delivery_postcode)}
              </p>
            </div>
          </div>
        </div>

        {/* Additional Information */}
        <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
          {order.pickup_date_start && (
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <div>
                <p className="text-slate-500">Pickup:</p>
                <p className="text-slate-700 font-medium">
                  {formatDate(order.pickup_date_start)}
                </p>
              </div>
            </div>
          )}
          
          {(order.cargo_pallets || order.cargo_weight_kg || order.cargo_ldm) && (
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4 text-slate-400" />
              <div>
                <p className="text-slate-500">Cargo:</p>
                <p className="text-slate-700 font-medium">
                  {[
                    order.cargo_pallets && `${order.cargo_pallets} pal`,
                    order.cargo_weight_kg && `${order.cargo_weight_kg}kg`,
                    order.cargo_ldm && `${order.cargo_ldm}ldm`
                  ].filter(Boolean).join(', ')}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Subcontractor Information */}
        {order.subcontractor_company && (
          <div className="flex items-center gap-2 mb-4 p-2 bg-blue-50 rounded-md">
            <Truck className="w-4 h-4 text-blue-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">
                {order.subcontractor_company}
              </p>
              {order.truck_plate && (
                <p className="text-xs text-blue-700">
                  Truck: {order.truck_plate}
                </p>
              )}
            </div>
            {order.subcontractor_price && (
              <div className="text-right">
                <p className="text-sm font-semibold text-blue-900">
                  {formatCurrency(order.subcontractor_price)}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Special Requirements */}
        {order.special_requirements && (
          <div className="mb-4 p-2 bg-amber-50 border border-amber-200 rounded-md">
            <p className="text-xs font-medium text-amber-800 mb-1">Special Requirements:</p>
            <p className="text-xs text-amber-700">
              {order.special_requirements}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-3 border-t border-slate-100">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewDetails(order.order_id)}
            className="flex-1"
            disabled={isLoading}
          >
            View Details
          </Button>
          
          {onEdit && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAction(() => onEdit(order.order_id))}
              disabled={isLoading}
            >
              Edit
            </Button>
          )}

          {order.order_status === OrderStatus.PENDING && onAssignSubcontractor && (
            <Button
              size="sm"
              onClick={() => handleAction(() => onAssignSubcontractor!(order.order_id))}
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isLoading ? 'Assigning...' : 'Assign'}
            </Button>
          )}

          {order.order_status !== OrderStatus.COMPLETED && 
           order.order_status !== OrderStatus.CANCELLED && 
           onUpdateStatus && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // Determine next logical status
                const nextStatus = getNextStatus(order.order_status);
                if (nextStatus) {
                  handleAction(() => onUpdateStatus!(order.order_id, nextStatus));
                }
              }}
              disabled={isLoading}
            >
              {isLoading ? 'Updating...' : getStatusActionLabel(order.order_status)}
            </Button>
          )}
        </div>

        {/* Created timestamp */}
        <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Clock className="w-3 h-3" />
            Created {calculateDaysAgo(order.created_at)} days ago
          </div>
          
          {order.manual_review_required && (
            <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800">
              Manual Review
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Helper functions for status transitions
const getNextStatus = (currentStatus: OrderStatus): OrderStatus | null => {
  const statusProgression: Record<OrderStatus, OrderStatus | null> = {
    [OrderStatus.PENDING]: OrderStatus.ASSIGNED,
    [OrderStatus.ASSIGNED]: OrderStatus.IN_TRANSIT,
    [OrderStatus.IN_TRANSIT]: OrderStatus.AWAITING_DOCUMENTS,
    [OrderStatus.AWAITING_DOCUMENTS]: OrderStatus.DOCUMENTS_RECEIVED,
    [OrderStatus.DOCUMENTS_RECEIVED]: OrderStatus.DOCUMENTS_VALIDATED,
    [OrderStatus.DOCUMENTS_VALIDATED]: OrderStatus.CLIENT_INVOICED,
    [OrderStatus.CLIENT_INVOICED]: OrderStatus.PAYMENT_RECEIVED,
    [OrderStatus.PAYMENT_RECEIVED]: OrderStatus.SUBCONTRACTOR_PAID,
    [OrderStatus.SUBCONTRACTOR_PAID]: OrderStatus.COMPLETED,
    [OrderStatus.COMPLETED]: null,
    [OrderStatus.CANCELLED]: null,
    [OrderStatus.DISPUTED]: null,
  };
  
  return statusProgression[currentStatus];
};

const getStatusActionLabel = (currentStatus: OrderStatus): string => {
  const actionLabels: Record<OrderStatus, string> = {
    [OrderStatus.PENDING]: 'Assign',
    [OrderStatus.ASSIGNED]: 'Start Transit',
    [OrderStatus.IN_TRANSIT]: 'Mark Delivered',
    [OrderStatus.AWAITING_DOCUMENTS]: 'Upload Docs',
    [OrderStatus.DOCUMENTS_RECEIVED]: 'Validate',
    [OrderStatus.DOCUMENTS_VALIDATED]: 'Invoice',
    [OrderStatus.CLIENT_INVOICED]: 'Payment',
    [OrderStatus.PAYMENT_RECEIVED]: 'Pay Carrier',
    [OrderStatus.SUBCONTRACTOR_PAID]: 'Complete',
    [OrderStatus.COMPLETED]: '',
    [OrderStatus.CANCELLED]: '',
    [OrderStatus.DISPUTED]: 'Resolve',
  };
  
  return actionLabels[currentStatus] || 'Update';
}; 