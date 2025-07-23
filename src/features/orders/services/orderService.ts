import { apiClient } from '@/shared/services/api'
import type { 
  Order, 
  OrderCreateRequest, 
  OrderUpdateRequest, 
  OrderListResponse, 
  OrderFilters,
  Subcontractor,
  SubcontractorAssignmentRequest 
} from '../types'

export class OrderService {
  private readonly baseUrl = '/api/v1'

  // Order CRUD Operations
  async getOrders(
    page: number = 1, 
    perPage: number = 20, 
    filters?: OrderFilters
  ): Promise<OrderListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    })

    // Add filters to params
    if (filters) {
      if (filters.status?.length) {
        filters.status.forEach(status => params.append('status', status))
      }
      if (filters.client_company) {
        params.append('client_company', filters.client_company)
      }
      if (filters.pickup_city) {
        params.append('pickup_city', filters.pickup_city)
      }
      if (filters.delivery_city) {
        params.append('delivery_city', filters.delivery_city)
      }
      if (filters.date_from) {
        params.append('date_from', filters.date_from)
      }
      if (filters.date_to) {
        params.append('date_to', filters.date_to)
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
    }

    const response = await apiClient.get<OrderListResponse>(
      `${this.baseUrl}/orders?${params.toString()}`
    )
    return response.data
  }

  async getOrder(orderId: string): Promise<Order> {
    const response = await apiClient.get<Order>(`${this.baseUrl}/orders/${orderId}`)
    return response.data
  }

  async createOrder(orderData: OrderCreateRequest): Promise<Order> {
    const response = await apiClient.post<Order>(`${this.baseUrl}/orders`, orderData)
    return response.data
  }

  async updateOrder(orderId: string, orderData: OrderUpdateRequest): Promise<Order> {
    const response = await apiClient.put<Order>(`${this.baseUrl}/orders/${orderId}`, orderData)
    return response.data
  }

  async deleteOrder(orderId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/orders/${orderId}`)
  }

  // Order Status Management
  async updateOrderStatus(orderId: string, status: string): Promise<Order> {
    const response = await apiClient.patch<Order>(
      `${this.baseUrl}/orders/${orderId}/status`, 
      { status }
    )
    return response.data
  }

  // Subcontractor Operations
  async getSubcontractors(): Promise<Subcontractor[]> {
    const response = await apiClient.get<Subcontractor[]>(`${this.baseUrl}/subcontractors`)
    return response.data
  }

  async assignSubcontractor(assignmentData: SubcontractorAssignmentRequest): Promise<Order> {
    const response = await apiClient.post<Order>(
      `${this.baseUrl}/orders/${assignmentData.order_id}/assign-subcontractor`,
      assignmentData
    )
    return response.data
  }

  // Analytics and Reporting
  async getOrderMetrics(): Promise<{
    total_orders: number
    orders_by_status: Record<string, number>
    total_revenue: number
    total_profit: number
    average_margin: number
  }> {
    const response = await apiClient.get(`${this.baseUrl}/orders/metrics`)
    return response.data
  }

  // Real-time tracking
  async trackOrderByUitCode(uitCode: string): Promise<{
    order_id: string
    status: string
    pickup_address: string
    delivery_address: string
    estimated_delivery?: string
    last_updated: string
  }> {
    const response = await apiClient.get(`${this.baseUrl}/track/${uitCode}`)
    return response.data
  }
}

// Export singleton instance
export const orderService = new OrderService() 