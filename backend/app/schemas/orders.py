"""Order-related Pydantic schemas"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    AWAITING_DOCUMENTS = "awaiting_documents"
    DOCUMENTS_RECEIVED = "documents_received"
    DOCUMENTS_VALIDATED = "documents_validated"
    CLIENT_INVOICED = "client_invoiced"
    PAYMENT_RECEIVED = "payment_received"
    SUBCONTRACTOR_PAID = "subcontractor_paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class OrderBase(BaseModel):
    """Base order schema"""
    client_company_name: str = Field(..., description="Client company name")
    client_vat_number: Optional[str] = Field(None, description="Client VAT number")
    client_contact_email: Optional[str] = Field(None, description="Client contact email")
    client_offered_price: Decimal = Field(..., description="Price offered by client (EUR)")
    
    pickup_address: str = Field(..., description="Pickup address")
    pickup_postcode: Optional[str] = Field(None, description="Pickup postcode")
    pickup_city: Optional[str] = Field(None, description="Pickup city")
    pickup_country: str = Field("RO", description="Pickup country code")
    
    delivery_address: str = Field(..., description="Delivery address")
    delivery_postcode: Optional[str] = Field(None, description="Delivery postcode")
    delivery_city: Optional[str] = Field(None, description="Delivery city")
    delivery_country: Optional[str] = Field(None, description="Delivery country code")
    
    cargo_ldm: Optional[Decimal] = Field(None, description="Loading meters")
    cargo_weight_kg: Optional[Decimal] = Field(None, description="Weight in kilograms")
    cargo_pallets: Optional[int] = Field(None, description="Number of pallets")
    special_requirements: Optional[str] = Field(None, description="Special requirements")


class OrderCreateRequest(OrderBase):
    """Schema for creating new orders"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_company_name": "Transport Solutions SRL",
                "client_vat_number": "RO12345678",
                "client_contact_email": "office@transportsolutions.ro",
                "client_offered_price": 1500.00,
                "pickup_address": "Str. Industriei 45, Bucuresti",
                "pickup_postcode": "010101",
                "pickup_city": "Bucuresti",
                "pickup_country": "RO",
                "delivery_address": "Str. Fabricii 12, Cluj-Napoca",
                "delivery_postcode": "400001",
                "delivery_city": "Cluj-Napoca",
                "delivery_country": "RO",
                "cargo_ldm": 2.5,
                "cargo_weight_kg": 1000.0,
                "cargo_pallets": 4,
                "special_requirements": "Temperature controlled"
            }
        }
    )


class OrderResponse(OrderBase):
    """Schema for order responses"""
    order_id: UUID = Field(..., description="Unique order identifier")
    order_status: OrderStatus = Field(..., description="Current order status")
    uit_code: Optional[str] = Field(None, description="Unique Interaction Token for public access")
    
    subcontractor_id: Optional[UUID] = Field(None, description="Assigned subcontractor ID")
    subcontractor_price: Optional[Decimal] = Field(None, description="Agreed subcontractor price")
    
    profit_margin: Optional[Decimal] = Field(None, description="Calculated profit margin")
    profit_percentage: Optional[Decimal] = Field(None, description="Profit percentage")
    
    pickup_date_start: Optional[date] = Field(None, description="Pickup date range start")
    pickup_date_end: Optional[date] = Field(None, description="Pickup date range end")
    delivery_date_start: Optional[date] = Field(None, description="Delivery date range start")
    delivery_date_end: Optional[date] = Field(None, description="Delivery date range end")
    
    created_at: datetime = Field(..., description="Order creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    extraction_confidence: Optional[Decimal] = Field(None, description="AI extraction confidence score")
    manual_review_required: bool = Field(False, description="Whether manual review is needed")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "order_id": "550e8400-e29b-41d4-a716-446655440000",
                "client_company_name": "Transport Solutions SRL",
                "client_vat_number": "RO12345678",
                "client_contact_email": "office@transportsolutions.ro",
                "client_offered_price": 1500.00,
                "order_status": "pending",
                "uit_code": "UIT-2024-001234",
                "pickup_address": "Str. Industriei 45, Bucuresti",
                "pickup_city": "Bucuresti",
                "pickup_postcode": "010101",
                "delivery_address": "Str. Fabricii 12, Cluj-Napoca", 
                "delivery_city": "Cluj-Napoca",
                "delivery_postcode": "400001",
                "cargo_ldm": 2.5,
                "cargo_weight_kg": 1000.0,
                "cargo_pallets": 4,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "extraction_confidence": 0.95,
                "manual_review_required": False
            }
        }
    )


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order responses with additional information"""
    subcontractor_company_name: Optional[str] = Field(None, description="Subcontractor company name")
    subcontractor_contact_email: Optional[str] = Field(None, description="Subcontractor contact email")
    
    truck_plate: Optional[str] = Field(None, description="Assigned truck plate number")
    driver_contact: Optional[str] = Field(None, description="Driver contact information")
    
    original_pdf_path: Optional[str] = Field(None, description="Path to original order PDF")
    generated_order_pdf_path: Optional[str] = Field(None, description="Path to generated order PDF")
    invoice_pdf_path: Optional[str] = Field(None, description="Path to invoice PDF")
    pod_pdf_path: Optional[str] = Field(None, description="Path to POD PDF")
    
    notes: Optional[str] = Field(None, description="Order notes and comments")
    
    # Geographic coordinates for mapping
    pickup_coordinates: Optional[str] = Field(None, description="Pickup coordinates (WKT format)")
    delivery_coordinates: Optional[str] = Field(None, description="Delivery coordinates (WKT format)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "order_id": "550e8400-e29b-41d4-a716-446655440000",
                "client_company_name": "Transport Solutions SRL",
                "client_vat_number": "RO12345678",
                "client_contact_email": "office@transportsolutions.ro",
                "client_offered_price": 1500.00,
                "order_status": "assigned",
                "uit_code": "UIT-2024-001234",
                "subcontractor_id": "660e8400-e29b-41d4-a716-446655440001",
                "subcontractor_company_name": "Fast Cargo SRL",
                "subcontractor_contact_email": "dispatch@fastcargo.ro",
                "subcontractor_price": 1200.00,
                "profit_margin": 300.00,
                "profit_percentage": 20.00,
                "truck_plate": "B-123-ABC",
                "driver_contact": "+40721234567",
                "pickup_address": "Str. Industriei 45, Bucuresti",
                "pickup_city": "Bucuresti",
                "pickup_postcode": "010101",
                "pickup_coordinates": "POINT(26.1025 44.4268)",
                "delivery_address": "Str. Fabricii 12, Cluj-Napoca",
                "delivery_city": "Cluj-Napoca", 
                "delivery_postcode": "400001",
                "delivery_coordinates": "POINT(23.5986 46.7712)",
                "cargo_ldm": 2.5,
                "cargo_weight_kg": 1000.0,
                "cargo_pallets": 4,
                "special_requirements": "Temperature controlled",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:20:00Z",
                "extraction_confidence": 0.95,
                "manual_review_required": False,
                "notes": "Priority delivery - customer VIP"
            }
        }
    )


class OrderListResponse(BaseModel):
    """Schema for order list responses with pagination"""
    orders: List[OrderResponse] = Field(..., description="List of orders")
    total_count: int = Field(..., description="Total number of orders")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of orders per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orders": [
                    {
                        "order_id": "550e8400-e29b-41d4-a716-446655440000",
                        "client_company_name": "Transport Solutions SRL",
                        "client_vat_number": "RO12345678",
                        "client_offered_price": 1500.00,
                        "order_status": "pending",
                        "pickup_city": "Bucuresti",
                        "delivery_city": "Cluj-Napoca",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total_count": 45,
                "page": 1,
                "page_size": 20,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False
            }
        }
    )


class OrderStatusUpdateRequest(BaseModel):
    """Schema for updating order status with validation"""
    order_status: OrderStatus = Field(..., description="New order status")
    notes: Optional[str] = Field(None, description="Notes for status change")
    
    # Additional fields that can be updated with specific status changes
    subcontractor_id: Optional[UUID] = Field(None, description="Subcontractor ID (for 'assigned' status)")
    subcontractor_price: Optional[Decimal] = Field(None, description="Agreed price (for 'assigned' status)")
    truck_plate: Optional[str] = Field(None, description="Truck plate (for 'assigned' status)")
    driver_contact: Optional[str] = Field(None, description="Driver contact (for 'assigned' status)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_status": "assigned",
                "notes": "Assigned to Fast Cargo SRL - priority delivery",
                "subcontractor_id": "660e8400-e29b-41d4-a716-446655440001",
                "subcontractor_price": 1200.00,
                "truck_plate": "B-123-ABC",
                "driver_contact": "+40721234567"
            }
        }
    )


class OrderUpdateRequest(BaseModel):
    """Schema for updating existing orders"""
    client_company_name: Optional[str] = None
    client_contact_email: Optional[str] = None
    client_offered_price: Optional[Decimal] = None
    
    pickup_date_start: Optional[date] = None
    pickup_date_end: Optional[date] = None
    delivery_date_start: Optional[date] = None
    delivery_date_end: Optional[date] = None
    
    cargo_ldm: Optional[Decimal] = None
    cargo_weight_kg: Optional[Decimal] = None
    cargo_pallets: Optional[int] = None
    special_requirements: Optional[str] = None
    
    order_status: Optional[OrderStatus] = None
    manual_review_required: Optional[bool] = None 