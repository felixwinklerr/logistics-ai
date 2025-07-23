// Order Management Types for Romanian Freight Forwarder System

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
  order_id: string
  created_at: string
  updated_at: string
  
  // Client Information
  client_company_name: string
  client_vat_number: string
  client_contact_email?: string
  client_payment_terms?: string
  client_offered_price: number
  
  // Route Information
  pickup_address: string
  pickup_postcode?: string
  pickup_city?: string
  pickup_country?: string
  pickup_coordinates?: string
  pickup_date_start?: string
  pickup_date_end?: string
  
  delivery_address: string
  delivery_postcode?: string
  delivery_city?: string
  delivery_country?: string
  delivery_coordinates?: string
  delivery_date_start?: string
  delivery_date_end?: string
  
  // Cargo Information
  cargo_ldm?: number
  cargo_weight_kg?: number
  cargo_pallets?: number
  cargo_description?: string
  special_requirements?: string
  
  // Subcontractor Information
  subcontractor_id?: string
  subcontractor_company?: string
  subcontractor_price?: number
  subcontractor_payment_terms?: string
  truck_plate?: string
  driver_contact?: string
  
  // Financial Tracking
  profit_margin?: number
  profit_percentage?: number
  
  // Status Management
  order_status: OrderStatus
  uit_code?: string
  
  // Document References
  original_pdf_path?: string
  generated_order_pdf_path?: string
  invoice_pdf_path?: string
  pod_pdf_path?: string
  
  // Metadata
  extraction_confidence?: number
  manual_review_required?: boolean
  notes?: string
}

export interface OrderCreateRequest {
  client_company_name: string
  client_vat_number: string
  client_contact_email?: string
  client_offered_price: number
  pickup_address: string
  pickup_postcode?: string
  pickup_city?: string
  pickup_country?: string
  delivery_address: string
  delivery_postcode?: string
  delivery_city?: string
  delivery_country?: string
  cargo_ldm?: number
  cargo_weight_kg?: number
  cargo_pallets?: number
  cargo_description?: string
  special_requirements?: string
}

export interface OrderUpdateRequest {
  client_contact_email?: string
  client_payment_terms?: string
  pickup_date_start?: string
  pickup_date_end?: string
  delivery_date_start?: string
  delivery_date_end?: string
  cargo_description?: string
  special_requirements?: string
  notes?: string
}

export interface OrderFilters {
  status?: OrderStatus[]
  client_company?: string
  pickup_city?: string
  delivery_city?: string
  date_from?: string
  date_to?: string
  search?: string
}

export interface OrderListResponse {
  orders: Order[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface Subcontractor {
  id: string
  company_name: string
  vat_number: string
  contact_person?: string
  phone?: string
  email: string
  address?: string
  total_orders: number
  successful_orders: number
  average_rating?: number
  preferred_payment_terms?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SubcontractorAssignmentRequest {
  order_id: string
  subcontractor_id: string
  agreed_price: number
  payment_terms?: string
  truck_plate?: string
  driver_contact?: string
  pickup_date?: string
  delivery_date?: string
  special_instructions?: string
}

// UI State Types
export type ViewMode = 'table' | 'card'

export interface OrderListState {
  viewMode: ViewMode
  filters: OrderFilters
  sortBy: keyof Order
  sortOrder: 'asc' | 'desc'
  selectedOrders: string[]
} 