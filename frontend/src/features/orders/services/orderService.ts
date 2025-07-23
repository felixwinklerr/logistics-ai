import api from '@/shared/services/api';
import { 
  Order, 
  OrderCreateRequest, 
  OrderUpdateRequest,
  OrderStatusUpdateRequest,
  OrderListResponse,
  OrderDetailResponse,
  OrderSearchParams,
  OrderStatus,
  SubcontractorAssignment,
  SubcontractorRecommendation
} from '../types';

// API endpoints configuration
const ENDPOINTS = {
  ORDERS: '/api/v1/orders',
  ORDER_BY_ID: (id: string) => `/api/v1/orders/${id}`,
  ORDER_STATUS: (id: string) => `/api/v1/orders/${id}/status`,
  ORDER_ASSIGN: (id: string) => `/api/v1/orders/${id}/assign`,
  ORDER_RECOMMENDATIONS: (id: string) => `/api/v1/orders/${id}/recommendations`,
  ORDER_DOCUMENTS: (id: string) => `/api/v1/orders/${id}/documents`,
} as const;

/**
 * Order Service - Handles all order-related API operations
 * Includes Romanian business logic and error handling
 */
export class OrderService {
  /**
   * Get orders with filtering, sorting, and pagination
   */
  static async getOrders(params: OrderSearchParams = {}): Promise<OrderListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      // Add search query
      if (params.query) {
        searchParams.append('q', params.query);
      }
      
      // Add filters
      if (params.filters) {
        const { filters } = params;
        
        if (filters.status && filters.status.length > 0) {
          filters.status.forEach(status => searchParams.append('status', status));
        }
        
        if (filters.client_company) {
          searchParams.append('client_company', filters.client_company);
        }
        
        if (filters.date_from) {
          searchParams.append('date_from', filters.date_from);
        }
        
        if (filters.date_to) {
          searchParams.append('date_to', filters.date_to);
        }
        
        if (filters.pickup_city) {
          searchParams.append('pickup_city', filters.pickup_city);
        }
        
        if (filters.delivery_city) {
          searchParams.append('delivery_city', filters.delivery_city);
        }
        
        if (filters.min_price) {
          searchParams.append('min_price', filters.min_price.toString());
        }
        
        if (filters.max_price) {
          searchParams.append('max_price', filters.max_price.toString());
        }
        
        if (filters.subcontractor_id) {
          searchParams.append('subcontractor_id', filters.subcontractor_id);
        }
      }
      
      // Add sorting
      if (params.sort_by) {
        searchParams.append('sort_by', params.sort_by);
      }
      
      if (params.sort_order) {
        searchParams.append('sort_order', params.sort_order);
      }
      
      // Add pagination
      if (params.page) {
        searchParams.append('page', params.page.toString());
      }
      
      if (params.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      
      const url = `${ENDPOINTS.ORDERS}?${searchParams.toString()}`;
      const response = await api.get<OrderListResponse>(url);
      
      return response.data;
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      throw new Error('Failed to load orders. Please try again.');
    }
  }

  /**
   * Get single order by ID with detailed information
   */
  static async getOrderById(orderId: string): Promise<OrderDetailResponse> {
    try {
      const response = await api.get<OrderDetailResponse>(
        ENDPOINTS.ORDER_BY_ID(orderId)
      );
      
      return response.data;
    } catch (error: any) {
      console.error(`Failed to fetch order ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      throw new Error('Failed to load order details. Please try again.');
    }
  }

  /**
   * Create a new order
   */
  static async createOrder(orderData: OrderCreateRequest): Promise<Order> {
    try {
      // Validate Romanian VAT number format
      if (!this.validateRomanianVAT(orderData.client_vat_number)) {
        throw new Error('Invalid Romanian VAT number format. Must be in format RO12345678.');
      }
      
      // Validate price
      if (orderData.client_offered_price <= 0) {
        throw new Error('Order price must be greater than 0.');
      }
      
      // Validate addresses
      if (!orderData.pickup_address.trim() || !orderData.delivery_address.trim()) {
        throw new Error('Both pickup and delivery addresses are required.');
      }
      
      const response = await api.post<Order>(ENDPOINTS.ORDERS, orderData);
      
      return response.data;
    } catch (error: any) {
      console.error('Failed to create order:', error);
      
      if (error.response?.status === 400) {
        const errorMessage = error.response.data?.detail || 'Invalid order data.';
        throw new Error(errorMessage);
      }
      
      if (error.response?.status === 422) {
        const validationErrors = error.response.data?.detail;
        if (Array.isArray(validationErrors)) {
          const errorMessages = validationErrors.map((err: any) => err.msg).join(', ');
          throw new Error(`Validation error: ${errorMessages}`);
        }
      }
      
      throw error.message ? new Error(error.message) : new Error('Failed to create order. Please try again.');
    }
  }

  /**
   * Update an existing order
   */
  static async updateOrder(orderId: string, orderData: OrderUpdateRequest): Promise<Order> {
    try {
      // Validate VAT number if provided
      if (orderData.client_vat_number && !this.validateRomanianVAT(orderData.client_vat_number)) {
        throw new Error('Invalid Romanian VAT number format. Must be in format RO12345678.');
      }
      
      // Validate price if provided
      if (orderData.client_offered_price !== undefined && orderData.client_offered_price <= 0) {
        throw new Error('Order price must be greater than 0.');
      }
      
      const response = await api.put<Order>(
        ENDPOINTS.ORDER_BY_ID(orderId),
        orderData
      );
      
      return response.data;
    } catch (error: any) {
      console.error(`Failed to update order ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      if (error.response?.status === 400) {
        const errorMessage = error.response.data?.detail || 'Invalid order data.';
        throw new Error(errorMessage);
      }
      
      if (error.response?.status === 422) {
        const validationErrors = error.response.data?.detail;
        if (Array.isArray(validationErrors)) {
          const errorMessages = validationErrors.map((err: any) => err.msg).join(', ');
          throw new Error(`Validation error: ${errorMessages}`);
        }
      }
      
      throw error.message ? new Error(error.message) : new Error('Failed to update order. Please try again.');
    }
  }

  /**
   * Update order status
   */
  static async updateOrderStatus(
    orderId: string, 
    status: OrderStatus, 
    notes?: string
  ): Promise<Order> {
    try {
      const statusUpdate: OrderStatusUpdateRequest = {
        order_status: status,
        notes
      };
      
      const response = await api.patch<Order>(
        ENDPOINTS.ORDER_STATUS(orderId),
        statusUpdate
      );
      
      return response.data;
    } catch (error: any) {
      console.error(`Failed to update order status ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      if (error.response?.status === 400) {
        const errorMessage = error.response.data?.detail || 'Invalid status update.';
        throw new Error(errorMessage);
      }
      
      throw new Error('Failed to update order status. Please try again.');
    }
  }

  /**
   * Delete/Cancel an order
   */
  static async cancelOrder(orderId: string, reason?: string): Promise<void> {
    try {
      await this.updateOrderStatus(orderId, OrderStatus.CANCELLED, reason);
    } catch (error) {
      console.error(`Failed to cancel order ${orderId}:`, error);
      throw error;
    }
  }

  /**
   * Get subcontractor recommendations for an order
   */
  static async getSubcontractorRecommendations(
    orderId: string
  ): Promise<SubcontractorRecommendation[]> {
    try {
      const response = await api.get<SubcontractorRecommendation[]>(
        ENDPOINTS.ORDER_RECOMMENDATIONS(orderId)
      );
      
      return response.data;
    } catch (error: any) {
      console.error(`Failed to get recommendations for order ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      throw new Error('Failed to load subcontractor recommendations. Please try again.');
    }
  }

  /**
   * Assign subcontractor to order
   */
  static async assignSubcontractor(
    orderId: string,
    assignment: Omit<SubcontractorAssignment, 'id' | 'order_id' | 'assignment_date' | 'subcontractor'>
  ): Promise<Order> {
    try {
      // Validate assignment data
      if (!assignment.subcontractor_id) {
        throw new Error('Subcontractor ID is required.');
      }
      
      if (assignment.agreed_price <= 0) {
        throw new Error('Agreed price must be greater than 0.');
      }
      
      const response = await api.post<Order>(
        ENDPOINTS.ORDER_ASSIGN(orderId),
        assignment
      );
      
      return response.data;
    } catch (error: any) {
      console.error(`Failed to assign subcontractor to order ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      if (error.response?.status === 400) {
        const errorMessage = error.response.data?.detail || 'Invalid assignment data.';
        throw new Error(errorMessage);
      }
      
      throw new Error('Failed to assign subcontractor. Please try again.');
    }
  }

  /**
   * Upload documents for an order
   */
  static async uploadDocuments(
    orderId: string,
    files: { type: string; file: File }[]
  ): Promise<void> {
    try {
      const formData = new FormData();
      
      files.forEach(({ type, file }) => {
        formData.append(`${type}_file`, file);
      });
      
      await api.post(ENDPOINTS.ORDER_DOCUMENTS(orderId), formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    } catch (error: any) {
      console.error(`Failed to upload documents for order ${orderId}:`, error);
      
      if (error.response?.status === 404) {
        throw new Error(`Order ${orderId} not found.`);
      }
      
      if (error.response?.status === 413) {
        throw new Error('File size too large. Please reduce file size and try again.');
      }
      
      throw new Error('Failed to upload documents. Please try again.');
    }
  }

  /**
   * Export orders to CSV
   */
  static async exportOrders(params: OrderSearchParams = {}): Promise<Blob> {
    try {
      const searchParams = new URLSearchParams();
      
      // Add all search parameters
      if (params.query) searchParams.append('q', params.query);
      if (params.filters?.status) {
        params.filters.status.forEach(status => searchParams.append('status', status));
      }
      // ... add other filters as needed
      
      searchParams.append('format', 'csv');
      
      const response = await api.get(`${ENDPOINTS.ORDERS}/export?${searchParams.toString()}`, {
        responseType: 'blob',
      });
      
      return response.data;
    } catch (error) {
      console.error('Failed to export orders:', error);
      throw new Error('Failed to export orders. Please try again.');
    }
  }

  /**
   * Validate Romanian VAT number format
   */
  private static validateRomanianVAT(vatNumber: string): boolean {
    const romanianVATPattern = /^RO\d{2,10}$/;
    return romanianVATPattern.test(vatNumber);
  }

  /**
   * Calculate profit metrics
   */
  static calculateProfitMetrics(clientPrice: number, subcontractorPrice: number) {
    const margin = clientPrice - subcontractorPrice;
    const percentage = clientPrice > 0 ? (margin / clientPrice) * 100 : 0;
    
    return {
      margin,
      percentage,
      isProfitable: margin > 0,
    };
  }

  /**
   * Format Romanian currency
   */
  static formatRomanianCurrency(amount: number, currency: 'EUR' | 'RON' = 'EUR'): string {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  /**
   * Validate Romanian postcode
   */
  static validateRomanianPostcode(postcode: string): boolean {
    const romanianPostcodePattern = /^\d{6}$/;
    return romanianPostcodePattern.test(postcode);
  }

  /**
   * Get order status progression
   */
  static getStatusProgression(currentStatus: OrderStatus): OrderStatus[] {
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
    if (currentIndex === -1) return [];
    
    return allStatuses.slice(currentIndex + 1);
  }

  /**
   * Check if order is overdue
   */
  static isOrderOverdue(order: Order): boolean {
    if (order.order_status === OrderStatus.COMPLETED || order.order_status === OrderStatus.CANCELLED) {
      return false;
    }
    
    const now = new Date();
    const createdDate = new Date(order.created_at);
    const daysSinceCreation = Math.floor((now.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
    
    // Consider orders overdue if pending for more than 2 days or in transit for more than 7 days
    if (order.order_status === OrderStatus.PENDING && daysSinceCreation > 2) {
      return true;
    }
    
    if (order.order_status === OrderStatus.IN_TRANSIT && daysSinceCreation > 7) {
      return true;
    }
    
    return false;
  }

  /**
   * Get order urgency level
   */
  static getOrderUrgency(order: Order): 'low' | 'medium' | 'high' | 'critical' {
    if (order.order_status === OrderStatus.COMPLETED || order.order_status === OrderStatus.CANCELLED) {
      return 'low';
    }
    
    const now = new Date();
    const createdDate = new Date(order.created_at);
    const daysSinceCreation = Math.floor((now.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
    
    // Check pickup date urgency
    if (order.pickup_date_start) {
      const pickupDate = new Date(order.pickup_date_start);
      const daysUntilPickup = Math.floor((pickupDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysUntilPickup < 0) return 'critical'; // Past pickup date
      if (daysUntilPickup <= 1) return 'high';
      if (daysUntilPickup <= 3) return 'medium';
    }
    
    // Check status-based urgency
    if (order.order_status === OrderStatus.PENDING && daysSinceCreation > 2) {
      return 'high';
    }
    
    if (order.order_status === OrderStatus.AWAITING_DOCUMENTS && daysSinceCreation > 5) {
      return 'medium';
    }
    
    return 'low';
  }
} 