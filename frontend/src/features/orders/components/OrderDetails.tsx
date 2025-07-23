import React, { useState } from 'react';
import { 
  ArrowLeft, 
  Edit3, 
  UserPlus, 
  MapPin, 
  Package, 
  Truck, 
  Euro, 
  FileText, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Download,
  Upload,
  Mail,
  Building
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { 
  Order, 
  OrderStatus, 
  ORDER_STATUS_CONFIG,
  formatCurrency,
  formatDate,
  formatDateTime,
  type OrderDetailsProps
} from '../types';

export const OrderDetails: React.FC<OrderDetailsProps> = ({
  orderId,
  order,
  loading = false,
  error,
  onEdit,
  onAssignSubcontractor,
  onUpdateStatus,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'documents' | 'financial'>('overview');
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Error Loading Order</h3>
        <p className="text-slate-600">{error}</p>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Order Not Found</h3>
        <p className="text-slate-600">Order with ID {orderId} could not be found.</p>
      </div>
    );
  }

  const statusConfig = ORDER_STATUS_CONFIG[order.order_status];
  const hasProfit = order.profit_margin !== undefined && order.profit_margin !== null;
  const isProfitable = hasProfit && order.profit_margin! > 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => window.history.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Orders
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Order #{order.order_id.slice(0, 8)}
            </h1>
            <p className="text-slate-600 mt-1">{order.client_company_name}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge 
            variant="secondary" 
            className={`${statusConfig.color} ${statusConfig.bgColor} border font-medium px-4 py-2`}
          >
            {statusConfig.label}
          </Badge>
          
          {onEdit && (
            <Button variant="outline" onClick={onEdit}>
              <Edit3 className="w-4 h-4 mr-2" />
              Edit Order
            </Button>
          )}
          
          {order.order_status === OrderStatus.PENDING && onAssignSubcontractor && (
            <Button onClick={onAssignSubcontractor} className="bg-blue-600 hover:bg-blue-700">
              <UserPlus className="w-4 h-4 mr-2" />
              Assign Subcontractor
            </Button>
          )}
        </div>
      </div>

      {/* Status Progress Bar */}
      <OrderStatusTimeline currentStatus={order.order_status} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        {/* Left Column - Order Details */}
        <div className="lg:col-span-2">
          {/* Tab Navigation */}
          <div className="border-b border-slate-200 mb-6">
            <nav className="flex space-x-8">
              {[
                { id: 'overview', label: 'Overview', icon: Package },
                { id: 'timeline', label: 'Timeline', icon: Clock },
                { id: 'documents', label: 'Documents', icon: FileText },
                { id: 'financial', label: 'Financial', icon: Euro },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex items-center gap-2 py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="space-y-6">
            {activeTab === 'overview' && <OverviewTab order={order} />}
            {activeTab === 'timeline' && <TimelineTab order={order} />}
            {activeTab === 'documents' && <DocumentsTab order={order} />}
            {activeTab === 'financial' && <FinancialTab order={order} />}
          </div>
        </div>

        {/* Right Column - Quick Actions & Summary */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {getQuickActions(order, onUpdateStatus).map((action, index) => (
                <Button
                  key={index}
                  variant={action.variant as any}
                  className="w-full justify-start"
                  onClick={action.onClick}
                  disabled={action.disabled}
                >
                  <action.icon className="w-4 h-4 mr-2" />
                  {action.label}
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Financial Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Financial Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-slate-600">Client Price</span>
                  <span className="font-semibold text-emerald-600">
                    {formatCurrency(order.client_offered_price)}
                  </span>
                </div>
                
                {order.subcontractor_price && (
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Subcontractor Cost</span>
                    <span className="font-semibold text-slate-900">
                      {formatCurrency(order.subcontractor_price)}
                    </span>
                  </div>
                )}
                
                {hasProfit && (
                  <>
                    <div className="border-t border-slate-200 pt-4">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Profit Margin</span>
                        <span className={`font-bold ${isProfitable ? 'text-emerald-600' : 'text-red-600'}`}>
                          {formatCurrency(order.profit_margin!)}
                        </span>
                      </div>
                      {order.profit_percentage && (
                        <div className="flex justify-between items-center mt-2">
                          <span className="text-slate-600">Profit %</span>
                          <span className={`font-semibold ${isProfitable ? 'text-emerald-600' : 'text-red-600'}`}>
                            {order.profit_percentage.toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Order Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Order Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <span className="text-slate-500">Created:</span>
                <p className="font-medium">{formatDateTime(order.created_at)}</p>
              </div>
              <div>
                <span className="text-slate-500">Last Updated:</span>
                <p className="font-medium">{formatDateTime(order.updated_at)}</p>
              </div>
              {order.uit_code && (
                <div>
                  <span className="text-slate-500">UIT Code:</span>
                  <p className="font-mono font-medium">{order.uit_code}</p>
                </div>
              )}
              {order.extraction_confidence && (
                <div>
                  <span className="text-slate-500">AI Confidence:</span>
                  <p className="font-medium">{(order.extraction_confidence * 100).toFixed(1)}%</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// Status Timeline Component
const OrderStatusTimeline: React.FC<{ currentStatus: OrderStatus }> = ({ currentStatus }) => {
  const allStatuses = [
    OrderStatus.PENDING,
    OrderStatus.ASSIGNED,
    OrderStatus.IN_TRANSIT,
    OrderStatus.AWAITING_DOCUMENTS,
    OrderStatus.DOCUMENTS_RECEIVED,
    OrderStatus.DOCUMENTS_VALIDATED,
    OrderStatus.CLIENT_INVOICED,
    OrderStatus.PAYMENT_RECEIVED,
    OrderStatus.SUBCONTRACTOR_PAID,
    OrderStatus.COMPLETED,
  ];

  const currentIndex = allStatuses.indexOf(currentStatus);
  const isCompleted = (index: number) => index <= currentIndex;
  const isCurrent = (index: number) => index === currentIndex;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Order Progress</h3>
      <div className="flex items-center justify-between">
        {allStatuses.map((status, index) => {
          const config = ORDER_STATUS_CONFIG[status];
          const completed = isCompleted(index);
          const current = isCurrent(index);
          
          return (
            <div key={status} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full border-2 flex items-center justify-center transition-colors ${
                    completed
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'bg-white border-slate-300 text-slate-400'
                  } ${current ? 'ring-4 ring-blue-100' : ''}`}
                >
                  {completed ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <span className="text-xs font-medium">{index + 1}</span>
                  )}
                </div>
                <span className={`text-xs mt-2 text-center max-w-20 ${
                  completed ? 'text-slate-900 font-medium' : 'text-slate-500'
                }`}>
                  {config.label}
                </span>
              </div>
              {index < allStatuses.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 ${
                    completed ? 'bg-blue-600' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Tab Components
const OverviewTab: React.FC<{ order: Order }> = ({ order }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    {/* Client Information */}
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building className="w-5 h-5" />
          Client Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className="text-sm text-slate-500">Company Name</label>
          <p className="font-medium">{order.client_company_name}</p>
        </div>
        <div>
          <label className="text-sm text-slate-500">VAT Number</label>
          <p className="font-medium">{order.client_vat_number}</p>
        </div>
        {order.client_contact_email && (
          <div>
            <label className="text-sm text-slate-500">Contact Email</label>
            <p className="font-medium">{order.client_contact_email}</p>
          </div>
        )}
        {order.client_payment_terms && (
          <div>
            <label className="text-sm text-slate-500">Payment Terms</label>
            <p className="font-medium">{order.client_payment_terms}</p>
          </div>
        )}
      </CardContent>
    </Card>

    {/* Route Information */}
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="w-5 h-5" />
          Route Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm text-slate-500 flex items-center gap-1">
            <MapPin className="w-3 h-3 text-blue-500" />
            Pickup Location
          </label>
          <p className="font-medium">{order.pickup_address}</p>
          {(order.pickup_city || order.pickup_postcode) && (
            <p className="text-sm text-slate-600">
              {[order.pickup_city, order.pickup_postcode, order.pickup_country].filter(Boolean).join(', ')}
            </p>
          )}
          {order.pickup_date_start && (
            <p className="text-sm text-slate-600 mt-1">
              Date: {formatDate(order.pickup_date_start)}
              {order.pickup_date_end && order.pickup_date_end !== order.pickup_date_start && 
                ` - ${formatDate(order.pickup_date_end)}`}
            </p>
          )}
        </div>
        
        <div>
          <label className="text-sm text-slate-500 flex items-center gap-1">
            <MapPin className="w-3 h-3 text-red-500" />
            Delivery Location
          </label>
          <p className="font-medium">{order.delivery_address}</p>
          {(order.delivery_city || order.delivery_postcode) && (
            <p className="text-sm text-slate-600">
              {[order.delivery_city, order.delivery_postcode, order.delivery_country].filter(Boolean).join(', ')}
            </p>
          )}
          {order.delivery_date_start && (
            <p className="text-sm text-slate-600 mt-1">
              Date: {formatDate(order.delivery_date_start)}
              {order.delivery_date_end && order.delivery_date_end !== order.delivery_date_start && 
                ` - ${formatDate(order.delivery_date_end)}`}
            </p>
          )}
        </div>
      </CardContent>
    </Card>

    {/* Cargo Information */}
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Package className="w-5 h-5" />
          Cargo Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {order.cargo_pallets && (
          <div className="flex justify-between">
            <span className="text-slate-600">Pallets</span>
            <span className="font-medium">{order.cargo_pallets}</span>
          </div>
        )}
        {order.cargo_weight_kg && (
          <div className="flex justify-between">
            <span className="text-slate-600">Weight</span>
            <span className="font-medium">{order.cargo_weight_kg} kg</span>
          </div>
        )}
        {order.cargo_ldm && (
          <div className="flex justify-between">
            <span className="text-slate-600">Loading Meters</span>
            <span className="font-medium">{order.cargo_ldm} LDM</span>
          </div>
        )}
        {order.cargo_description && (
          <div>
            <label className="text-sm text-slate-500">Description</label>
            <p className="font-medium">{order.cargo_description}</p>
          </div>
        )}
        {order.special_requirements && (
          <div>
            <label className="text-sm text-slate-500">Special Requirements</label>
            <p className="font-medium text-amber-700 bg-amber-50 p-2 rounded">
              {order.special_requirements}
            </p>
          </div>
        )}
      </CardContent>
    </Card>

    {/* Subcontractor Information */}
    {order.subcontractor_company && (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Truck className="w-5 h-5" />
            Subcontractor
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm text-slate-500">Company</label>
            <p className="font-medium">{order.subcontractor_company}</p>
          </div>
          {order.truck_plate && (
            <div>
              <label className="text-sm text-slate-500">Truck Plate</label>
              <p className="font-medium">{order.truck_plate}</p>
            </div>
          )}
          {order.driver_contact && (
            <div>
              <label className="text-sm text-slate-500">Driver Contact</label>
              <p className="font-medium">{order.driver_contact}</p>
            </div>
          )}
          {order.subcontractor_price && (
            <div>
              <label className="text-sm text-slate-500">Agreed Price</label>
              <p className="font-medium text-lg">{formatCurrency(order.subcontractor_price)}</p>
            </div>
          )}
        </CardContent>
      </Card>
    )}
  </div>
);

const TimelineTab: React.FC<{ order: Order }> = ({ order: _ }) => (
  <div className="space-y-4">
    <div className="text-center text-gray-500 py-8">
      Order timeline feature coming soon
    </div>
  </div>
);

const DocumentsTab: React.FC<{ order: Order }> = ({ order: _ }) => (
  <div className="space-y-4">
    <div className="text-center text-gray-500 py-8">
      Document management feature coming soon
    </div>
  </div>
);

const FinancialTab: React.FC<{ order: Order }> = ({ order }) => (
  <Card>
    <CardHeader>
      <CardTitle>Financial Details</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <label className="text-slate-500">Client Offered Price</label>
            <p className="text-xl font-bold text-emerald-600">
              {formatCurrency(order.client_offered_price)}
            </p>
          </div>
          {order.subcontractor_price && (
            <div>
              <label className="text-slate-500">Subcontractor Cost</label>
              <p className="text-xl font-bold">
                {formatCurrency(order.subcontractor_price)}
              </p>
            </div>
          )}
        </div>
        
        {order.profit_margin !== undefined && (
          <div className="border-t pt-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label className="text-slate-500">Profit Margin</label>
                <p className={`text-xl font-bold ${order.profit_margin >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {formatCurrency(order.profit_margin)}
                </p>
              </div>
              {order.profit_percentage !== undefined && (
                <div>
                  <label className="text-slate-500">Profit Percentage</label>
                  <p className={`text-xl font-bold ${order.profit_percentage >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {order.profit_percentage.toFixed(2)}%
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </CardContent>
  </Card>
);

// Helper function for quick actions
const getQuickActions = (order: Order, onUpdateStatus?: (status: OrderStatus) => void) => {
  const actions = [];
  
  switch (order.order_status) {
    case OrderStatus.PENDING:
      actions.push({
        label: 'Mark as Assigned',
        icon: UserPlus,
        variant: 'default',
        onClick: () => onUpdateStatus?.(OrderStatus.ASSIGNED),
        disabled: false,
      });
      break;
    case OrderStatus.ASSIGNED:
      actions.push({
        label: 'Start Transit',
        icon: Truck,
        variant: 'default',
        onClick: () => onUpdateStatus?.(OrderStatus.IN_TRANSIT),
        disabled: false,
      });
      break;
    case OrderStatus.IN_TRANSIT:
      actions.push({
        label: 'Mark Delivered',
        icon: CheckCircle,
        variant: 'default',
        onClick: () => onUpdateStatus?.(OrderStatus.AWAITING_DOCUMENTS),
        disabled: false,
      });
      break;
    case OrderStatus.AWAITING_DOCUMENTS:
      actions.push({
        label: 'Upload Documents',
        icon: Upload,
        variant: 'default',
        onClick: () => {},
        disabled: false,
      });
      break;
    default:
      break;
  }

  // Common actions
  actions.push(
    {
      label: 'Download POD',
      icon: Download,
      variant: 'outline',
      onClick: () => {},
      disabled: !order.pod_pdf_path,
    },
    {
      label: 'Contact Client',
      icon: Mail,
      variant: 'outline',
      onClick: () => {},
      disabled: !order.client_contact_email,
    }
  );

  return actions;
};
