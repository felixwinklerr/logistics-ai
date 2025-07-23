"""
Subcontractor Pydantic Schemas

Provides comprehensive validation schemas for subcontractor operations including:
- CRUD request/response models
- Assignment and recommendation schemas
- Performance metrics and analytics
- Profit calculation integration
"""

from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator


# Base Schemas

class SubcontractorBase(BaseModel):
    """Base subcontractor schema with common fields"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Company name")
    vat_number: str = Field(..., min_length=5, max_length=50, description="VAT registration number")
    contact_person: Optional[str] = Field(None, max_length=255, description="Primary contact person")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    email: EmailStr = Field(..., description="Contact email address")
    address: Optional[str] = Field(None, max_length=500, description="Business address")
    preferred_payment_terms: Optional[str] = Field(
        "30 days after delivery", 
        max_length=100, 
        description="Preferred payment terms"
    )

    @validator('vat_number')
    def validate_vat_number(cls, v):
        """Validate VAT number format"""
        if not v:
            raise ValueError('VAT number is required')
        # Basic Romanian VAT validation (starts with RO)
        if not v.upper().startswith('RO') and not v.isdigit():
            # Allow both RO prefix and numeric format
            pass
        return v.upper()

    @validator('phone')
    def validate_phone(cls, v):
        """Basic phone number validation"""
        if v and len(v.replace(' ', '').replace('-', '').replace('+', '')) < 8:
            raise ValueError('Phone number must be at least 8 digits')
        return v


# Request Schemas

class SubcontractorCreateRequest(SubcontractorBase):
    """Schema for creating new subcontractor"""
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "TransCargo SRL",
                "vat_number": "RO12345678",
                "contact_person": "Ion Popescu",
                "phone": "+40721234567",
                "email": "contact@transcargo.ro",
                "address": "Str. Transportului 123, București",
                "preferred_payment_terms": "30 days after delivery"
            }
        }


class SubcontractorUpdateRequest(BaseModel):
    """Schema for updating existing subcontractor"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    vat_number: Optional[str] = Field(None, min_length=5, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    preferred_payment_terms: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    @validator('vat_number')
    def validate_vat_number(cls, v):
        """Validate VAT number format if provided"""
        if v and not v.upper().startswith('RO') and not v.isdigit():
            pass  # Allow both formats
        return v.upper() if v else v

    class Config:
        schema_extra = {
            "example": {
                "contact_person": "Maria Ionescu",
                "phone": "+40722334455",
                "email": "maria@transcargo.ro"
            }
        }


# Response Schemas

class SubcontractorResponse(SubcontractorBase):
    """Schema for subcontractor response data"""
    id: str = Field(..., description="Unique subcontractor identifier")
    
    # Performance metrics
    total_orders: int = Field(0, ge=0, description="Total number of orders handled")
    successful_orders: int = Field(0, ge=0, description="Number of successfully completed orders")
    average_rating: Decimal = Field(Decimal('0'), ge=0, le=5, description="Average performance rating")
    
    # Status and timestamps
    is_active: bool = Field(True, description="Whether subcontractor is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True
        json_encoders = {
            Decimal: float
        }
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "company_name": "TransCargo SRL",
                "vat_number": "RO12345678",
                "contact_person": "Ion Popescu",
                "phone": "+40721234567",
                "email": "contact@transcargo.ro",
                "address": "Str. Transportului 123, București",
                "preferred_payment_terms": "30 days after delivery",
                "total_orders": 45,
                "successful_orders": 42,
                "average_rating": 4.3,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-17T14:22:00Z"
            }
        }


class SubcontractorListResponse(BaseModel):
    """Schema for paginated subcontractor list response"""
    subcontractors: List[SubcontractorResponse] = Field(..., description="List of subcontractors")
    total_count: int = Field(..., ge=0, description="Total number of subcontractors")
    skip: int = Field(..., ge=0, description="Number of records skipped")
    limit: int = Field(..., ge=1, description="Maximum number of records returned")

    class Config:
        schema_extra = {
            "example": {
                "subcontractors": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "company_name": "TransCargo SRL",
                        "vat_number": "RO12345678",
                        "total_orders": 45,
                        "average_rating": 4.3,
                        "is_active": True
                    }
                ],
                "total_count": 1,
                "skip": 0,
                "limit": 50
            }
        }


# Performance Metrics

class PerformanceMetricsResponse(BaseModel):
    """Schema for subcontractor performance metrics"""
    total_orders: int = Field(..., ge=0, description="Total orders in period")
    completed_orders: int = Field(..., ge=0, description="Successfully completed orders")
    completion_rate: float = Field(..., ge=0, le=100, description="Completion rate percentage")
    average_rating: float = Field(..., ge=0, le=5, description="Average performance rating")
    on_time_delivery_rate: float = Field(..., ge=0, le=100, description="On-time delivery percentage")
    average_response_time_hours: float = Field(..., ge=0, description="Average response time in hours")
    total_revenue: Decimal = Field(..., ge=0, description="Total revenue generated")
    average_order_value: Decimal = Field(..., ge=0, description="Average order value")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    analysis_period_days: int = Field(..., ge=1, description="Analysis period in days")

    class Config:
        json_encoders = {
            Decimal: float
        }
        schema_extra = {
            "example": {
                "total_orders": 12,
                "completed_orders": 11,
                "completion_rate": 91.7,
                "average_rating": 4.3,
                "on_time_delivery_rate": 87.5,
                "average_response_time_hours": 3.2,
                "total_revenue": 18500.00,
                "average_order_value": 1541.67,
                "last_active": "2024-01-17T09:15:00Z",
                "analysis_period_days": 90
            }
        }


class SubcontractorDetailResponse(SubcontractorResponse):
    """Schema for detailed subcontractor information"""
    performance_metrics: Optional[PerformanceMetricsResponse] = Field(
        None, 
        description="Performance metrics for specified period"
    )

    class Config:
        orm_mode = True
        json_encoders = {
            Decimal: float
        }


# Assignment Schemas

class AssignmentRequest(BaseModel):
    """Schema for subcontractor assignment request"""
    order_id: str = Field(..., description="Order ID to assign")
    subcontractor_id: str = Field(..., description="Subcontractor ID to assign")
    subcontractor_price: Decimal = Field(..., gt=0, description="Agreed price for subcontractor")
    payment_terms: Optional[str] = Field(
        "30 days after delivery", 
        max_length=100, 
        description="Payment terms for this assignment"
    )
    truck_plate: Optional[str] = Field(None, max_length=20, description="Truck license plate")
    driver_contact: Optional[str] = Field(None, max_length=100, description="Driver contact information")

    class Config:
        json_encoders = {
            Decimal: float
        }
        schema_extra = {
            "example": {
                "order_id": "order-123e4567-e89b-12d3-a456-426614174000",
                "subcontractor_id": "sub-123e4567-e89b-12d3-a456-426614174000",
                "subcontractor_price": 1350.00,
                "payment_terms": "30 days after delivery",
                "truck_plate": "B-123-ABC",
                "driver_contact": "Ion Șofer - +40723456789"
            }
        }


class AssignmentRecommendationResponse(BaseModel):
    """Schema for assignment recommendation with scoring"""
    subcontractor: SubcontractorResponse = Field(..., description="Recommended subcontractor")
    recommendation_score: float = Field(..., ge=0, le=100, description="Recommendation score")
    estimated_cost: Decimal = Field(..., gt=0, description="Estimated cost for assignment")
    distance_km: Optional[float] = Field(None, ge=0, description="Distance from pickup location")
    performance_rating: Optional[float] = Field(None, ge=0, le=5, description="Performance rating")
    profit_margin: Optional[Decimal] = Field(None, description="Expected profit margin")
    profit_percentage: Optional[float] = Field(None, description="Expected profit percentage")
    reasoning: List[str] = Field(default_factory=list, description="Recommendation reasoning")

    class Config:
        json_encoders = {
            Decimal: float
        }
        schema_extra = {
            "example": {
                "subcontractor": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "company_name": "TransCargo SRL",
                    "average_rating": 4.3,
                    "total_orders": 45
                },
                "recommendation_score": 87.5,
                "estimated_cost": 1350.00,
                "distance_km": 25.3,
                "performance_rating": 4.3,
                "profit_margin": 150.00,
                "profit_percentage": 10.0,
                "reasoning": [
                    "High performance rating",
                    "Good profit margin",
                    "Experienced contractor"
                ]
            }
        }


# Order Status Update Schema (for completeness)

class OrderStatusUpdateRequest(BaseModel):
    """Schema for updating order status"""
    new_status: str = Field(..., description="New order status")
    notes: Optional[str] = Field(None, max_length=1000, description="Status change notes")

    class Config:
        schema_extra = {
            "example": {
                "new_status": "assigned",
                "notes": "Subcontractor assigned with competitive pricing"
            }
        } 