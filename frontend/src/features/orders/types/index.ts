// Romanian Freight Forwarder Order Management Types
// Comprehensive TypeScript definitions with Romanian business compliance

export enum OrderStatus {
  PENDING = 'pending',
  ASSIGNED = 'assigned',
  IN_TRANSIT = 'in_transit',
  AWAITING_DOCUMENTS = 'awaiting_documents',
  DOCUMENTS_RECEIVED = 'documents_received',
  DOCUMENTS_VALIDATED = 'documents_validated',
  CLIENT_INVOICED = 'client_invoiced',
  PAYMENT_RECEIVED = 'payment_received',
  SUBCONTRACTOR_PAID = 'subcontractor_paid',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  DISPUTED = 'disputed'
}

export interface Order {
  order_id: string;
  created_at: string;
  updated_at: string;
  
  // Client Information
  client_company_name: string;
  client_vat_number: string;
  client_contact_email?: string;
  client_payment_terms?: string;
  client_offered_price: number;
  
  // Route Information
  pickup_address: string;
  pickup_postcode?: string;
  pickup_city?: string;
  pickup_country?: string;
  pickup_date_start?: string;
  pickup_date_end?: string;
  
  delivery_address: string;
  delivery_postcode?: string;
  delivery_city?: string;
  delivery_country?: string;
  delivery_date_start?: string;
  delivery_date_end?: string;
  
  // Cargo Information
  cargo_ldm?: number;
  cargo_weight_kg?: number;
  cargo_pallets?: number;
  cargo_description?: string;
  special_requirements?: string;
  
  // Subcontractor Information
  subcontractor_id?: string;
  subcontractor_company?: string;
  subcontractor_price?: number;
  subcontractor_payment_terms?: string;
  truck_plate?: string;
  driver_contact?: string;
  
  // Financial Tracking
  profit_margin?: number;
  profit_percentage?: number;
  
  // Status Management
  order_status: OrderStatus;
  uit_code?: string;
  
  // Document References
  original_pdf_path?: string;
  generated_order_pdf_path?: string;
  invoice_pdf_path?: string;
  pod_pdf_path?: string;
  
  // Metadata
  extraction_confidence?: number;
  manual_review_required?: boolean;
  notes?: string;
}

export interface OrderCreateRequest {
  client_company_name: string;
  client_vat_number: string;
  client_contact_email?: string;
  client_offered_price: number;
  pickup_address: string;
  pickup_postcode?: string;
  pickup_city?: string;
  pickup_country?: string;
  pickup_date_start?: string;
  pickup_date_end?: string;
  delivery_address: string;
  delivery_postcode?: string;
  delivery_city?: string;
  delivery_country?: string;
  delivery_date_start?: string;
  delivery_date_end?: string;
  cargo_ldm?: number;
  cargo_weight_kg?: number;
  cargo_pallets?: number;
  cargo_description?: string;
  special_requirements?: string;
}

export interface OrderUpdateRequest {
  client_company_name?: string;
  client_vat_number?: string;
  client_contact_email?: string;
  client_offered_price?: number;
  pickup_address?: string;
  pickup_postcode?: string;
  pickup_city?: string;
  pickup_country?: string;
  pickup_date_start?: string;
  pickup_date_end?: string;
  delivery_address?: string;
  delivery_postcode?: string;
  delivery_city?: string;
  delivery_country?: string;
  delivery_date_start?: string;
  delivery_date_end?: string;
  cargo_ldm?: number;
  cargo_weight_kg?: number;
  cargo_pallets?: number;
  cargo_description?: string;
  special_requirements?: string;
  notes?: string;
}

export interface OrderStatusUpdateRequest {
  order_status: OrderStatus;
  notes?: string;
}

export interface OrderListResponse {
  orders: Order[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface OrderDetailResponse extends Order {
  status_history?: OrderStatusHistory[];
  documents?: OrderDocument[];
  assignments?: SubcontractorAssignment[];
}

export interface OrderStatusHistory {
  id: string;
  order_id: string;
  status_from?: OrderStatus;
  status_to: OrderStatus;
  changed_at: string;
  changed_by?: string;
  notes?: string;
}

export interface OrderDocument {
  id: string;
  order_id: string;
  document_type: 'invoice' | 'pod' | 'transport_order' | 'other';
  file_path: string;
  file_name: string;
  file_size: number;
  uploaded_at: string;
  uploaded_by?: string;
  validation_status?: 'pending' | 'valid' | 'invalid';
  validation_errors?: string[];
}

export interface Subcontractor {
  id: string;
  company_name: string;
  vat_number: string;
  contact_person?: string;
  phone?: string;
  email: string;
  address?: string;
  total_orders: number;
  successful_orders: number;
  average_rating?: number;
  preferred_payment_terms?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubcontractorAssignment {
  id: string;
  order_id: string;
  subcontractor_id: string;
  subcontractor: Subcontractor;
  agreed_price: number;
  payment_terms: string;
  truck_plate?: string;
  driver_contact?: string;
  assignment_date: string;
  notes?: string;
}

export interface SubcontractorRecommendation {
  subcontractor: Subcontractor;
  score: number;
  estimated_price: number;
  reasoning: string[];
  past_performance?: {
    completed_orders: number;
    average_rating: number;
    on_time_delivery_rate: number;
  };
}

// UI-specific types
export interface OrderCardProps {
  order: Order;
  onViewDetails: (orderId: string) => void;
  onEdit?: (orderId: string) => void;
  onAssignSubcontractor?: (orderId: string) => void;
  onUpdateStatus?: (orderId: string, status: OrderStatus) => void;
}

export interface OrderListProps {
  orders: Order[];
  loading?: boolean;
  error?: string;
  onOrderSelect?: (orderId: string) => void;
  onRefresh?: () => void;
}

export interface OrderFormProps {
  order?: Order;
  mode: 'create' | 'edit';
  onSubmit: (data: OrderCreateRequest | OrderUpdateRequest) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export interface OrderDetailsProps {
  orderId: string;
  order?: Order;
  loading?: boolean;
  error?: string;
  onEdit?: () => void;
  onAssignSubcontractor?: () => void;
  onUpdateStatus?: (status: OrderStatus) => void;
}

// Filter and search types
export interface OrderFilters {
  status?: OrderStatus[];
  client_company?: string;
  date_from?: string;
  date_to?: string;
  pickup_city?: string;
  delivery_city?: string;
  min_price?: number;
  max_price?: number;
  subcontractor_id?: string;
}

export interface OrderSearchParams {
  query?: string;
  filters?: OrderFilters;
  sort_by?: 'created_at' | 'client_offered_price' | 'pickup_date_start' | 'delivery_date_start';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

// Romanian business validation patterns
export const ROMANIAN_VAT_PATTERN = /^RO\d{2,10}$/;
export const ROMANIAN_POSTCODE_PATTERN = /^\d{6}$/;

// Status display configurations
export const ORDER_STATUS_CONFIG: Record<OrderStatus, { 
  label: string; 
  color: string; 
  bgColor: string; 
  description: string;
  priority: number;
}> = {
  [OrderStatus.PENDING]: {
    label: 'Pending',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50 border-amber-200',
    description: 'Order received, awaiting assignment',
    priority: 1
  },
  [OrderStatus.ASSIGNED]: {
    label: 'Assigned',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 border-blue-200',
    description: 'Subcontractor assigned',
    priority: 2
  },
  [OrderStatus.IN_TRANSIT]: {
    label: 'In Transit',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 border-purple-200',
    description: 'Cargo picked up and in transit',
    priority: 3
  },
  [OrderStatus.AWAITING_DOCUMENTS]: {
    label: 'Awaiting Documents',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 border-orange-200',
    description: 'Delivery complete, documents pending',
    priority: 4
  },
  [OrderStatus.DOCUMENTS_RECEIVED]: {
    label: 'Documents Received',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50 border-indigo-200',
    description: 'Documents uploaded, pending validation',
    priority: 5
  },
  [OrderStatus.DOCUMENTS_VALIDATED]: {
    label: 'Documents Validated',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50 border-teal-200',
    description: 'All documents validated successfully',
    priority: 6
  },
  [OrderStatus.CLIENT_INVOICED]: {
    label: 'Client Invoiced',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50 border-cyan-200',
    description: 'Invoice sent to client',
    priority: 7
  },
  [OrderStatus.PAYMENT_RECEIVED]: {
    label: 'Payment Received',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50 border-emerald-200',
    description: 'Client payment received',
    priority: 8
  },
  [OrderStatus.SUBCONTRACTOR_PAID]: {
    label: 'Subcontractor Paid',
    color: 'text-green-600',
    bgColor: 'bg-green-50 border-green-200',
    description: 'Subcontractor payment completed',
    priority: 9
  },
  [OrderStatus.COMPLETED]: {
    label: 'Completed',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100 border-emerald-300',
    description: 'Order fully completed',
    priority: 10
  },
  [OrderStatus.CANCELLED]: {
    label: 'Cancelled',
    color: 'text-red-600',
    bgColor: 'bg-red-50 border-red-200',
    description: 'Order cancelled',
    priority: 11
  },
  [OrderStatus.DISPUTED]: {
    label: 'Disputed',
    color: 'text-rose-600',
    bgColor: 'bg-rose-50 border-rose-200',
    description: 'Payment or delivery dispute',
    priority: 12
  }
};

// Currency formatting for Romanian business
export const formatCurrency = (amount: number, currency: string = 'EUR'): string => {
  return new Intl.NumberFormat('ro-RO', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

// Date formatting for Romanian locale
export const formatDate = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('ro-RO', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(dateObj);
};

// DateTime formatting for Romanian locale
export const formatDateTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('ro-RO', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dateObj);
};
