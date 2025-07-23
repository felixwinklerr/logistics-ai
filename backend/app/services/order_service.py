"""
Order Service - Core Business Logic for Order Management

Integrates geographic service and profit calculation engine to provide
comprehensive order management functionality including:
- CRUD operations with geographic data
- Status workflow management (12-status transitions)
- UIT generation for public access
- AI document processing integration
- Profit calculations for subcontractor assignments
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_GeomFromText

from app.models.orders import Order, OrderStatus
from app.models.subcontractors import Subcontractor
from app.schemas.orders import OrderCreateRequest, OrderUpdateRequest, OrderResponse
from app.services.geographic_service import (
    GeographicService, Coordinates, CoordinateSystem, 
    SpatialQuery, create_geographic_service
)
from app.services.profit_calculation_service import (
    ProfitCalculationEngine, ProfitCalculationInput, Currency, VATStatus,
    create_profit_calculation_engine
)
from app.core.logging import get_logger
from app.core.exceptions import ValidationError, NotFoundError, BusinessRuleError

logger = get_logger(__name__)


class OrderTransition:
    """Valid order status transitions with business rules"""
    
    VALID_TRANSITIONS = {
        OrderStatus.PENDING: [OrderStatus.ASSIGNED, OrderStatus.CANCELLED],
        OrderStatus.ASSIGNED: [OrderStatus.IN_TRANSIT, OrderStatus.CANCELLED],
        OrderStatus.IN_TRANSIT: [OrderStatus.AWAITING_DOCUMENTS, OrderStatus.DISPUTED],
        OrderStatus.AWAITING_DOCUMENTS: [OrderStatus.DOCUMENTS_RECEIVED, OrderStatus.DISPUTED],
        OrderStatus.DOCUMENTS_RECEIVED: [OrderStatus.DOCUMENTS_VALIDATED, OrderStatus.DISPUTED],
        OrderStatus.DOCUMENTS_VALIDATED: [OrderStatus.CLIENT_INVOICED],
        OrderStatus.CLIENT_INVOICED: [OrderStatus.PAYMENT_RECEIVED, OrderStatus.DISPUTED],
        OrderStatus.PAYMENT_RECEIVED: [OrderStatus.SUBCONTRACTOR_PAID],
        OrderStatus.SUBCONTRACTOR_PAID: [OrderStatus.COMPLETED],
        OrderStatus.COMPLETED: [],  # Terminal state
        OrderStatus.CANCELLED: [],  # Terminal state
        OrderStatus.DISPUTED: [OrderStatus.IN_TRANSIT, OrderStatus.AWAITING_DOCUMENTS, OrderStatus.CANCELLED]
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> bool:
        """Check if status transition is valid"""
        return to_status in cls.VALID_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def get_valid_next_statuses(cls, current_status: OrderStatus) -> List[OrderStatus]:
        """Get list of valid next statuses"""
        return cls.VALID_TRANSITIONS.get(current_status, [])


class OrderService:
    """
    Core Order Service providing business logic for order management
    
    Features:
    - CRUD operations with geographic data validation
    - Status workflow management with business rules
    - UIT generation for public document access
    - Integration with AI document processing
    - Profit calculations for subcontractor assignments
    - Geographic queries for route optimization
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._geographic_service: Optional[GeographicService] = None
        self._profit_engine: Optional[ProfitCalculationEngine] = None
    
    async def initialize(self):
        """Initialize service dependencies"""
        self._geographic_service = await create_geographic_service(self.db_session)
        self._profit_engine = await create_profit_calculation_engine(self.db_session)
        logger.info("OrderService initialized with geographic and profit services")
    
    @property
    def geographic_service(self) -> GeographicService:
        """Get geographic service instance"""
        if not self._geographic_service:
            raise RuntimeError("OrderService not initialized. Call initialize() first.")
        return self._geographic_service
    
    @property
    def profit_engine(self) -> ProfitCalculationEngine:
        """Get profit calculation engine instance"""
        if not self._profit_engine:
            raise RuntimeError("OrderService not initialized. Call initialize() first.")
        return self._profit_engine
    
    # CRUD Operations
    
    async def create_order(
        self, 
        order_data: OrderCreateRequest,
        created_by_user_id: Optional[str] = None
    ) -> Order:
        """Create new order with geographic validation and UIT generation"""
        
        try:
            # Validate and geocode addresses
            pickup_coords = await self._validate_and_geocode_address(
                order_data.pickup_address,
                order_data.pickup_postcode,
                order_data.pickup_city
            )
            
            delivery_coords = await self._validate_and_geocode_address(
                order_data.delivery_address,
                order_data.delivery_postcode,
                order_data.delivery_city
            )
            
            # Generate UIT code for public access
            uit_code = self._generate_uit_code()
            
            # Create order model
            order = Order(
                # Client information
                client_company_name=order_data.client_company_name,
                client_vat_number=order_data.client_vat_number,
                client_contact_email=order_data.client_contact_email,
                client_offered_price=order_data.client_offered_price,
                client_payment_terms=order_data.client_payment_terms or "30 days after delivery",
                
                # Pickup information
                pickup_address=order_data.pickup_address,
                pickup_postcode=order_data.pickup_postcode,
                pickup_city=order_data.pickup_city,
                pickup_country=order_data.pickup_country or "RO",
                pickup_coordinates=ST_GeomFromText(
                    f"POINT({pickup_coords.longitude} {pickup_coords.latitude})", 
                    4326
                ),
                pickup_date_start=order_data.pickup_date_start,
                pickup_date_end=order_data.pickup_date_end,
                
                # Delivery information  
                delivery_address=order_data.delivery_address,
                delivery_postcode=order_data.delivery_postcode,
                delivery_city=order_data.delivery_city,
                delivery_country=order_data.delivery_country or "RO",
                delivery_coordinates=ST_GeomFromText(
                    f"POINT({delivery_coords.longitude} {delivery_coords.latitude})", 
                    4326
                ),
                delivery_date_start=order_data.delivery_date_start,
                delivery_date_end=order_data.delivery_date_end,
                
                # Cargo information
                cargo_ldm=order_data.cargo_ldm,
                cargo_weight_kg=order_data.cargo_weight_kg,
                cargo_pallets=order_data.cargo_pallets,
                cargo_description=order_data.cargo_description,
                special_requirements=order_data.special_requirements,
                
                # System fields
                uit_code=uit_code,
                order_status=OrderStatus.PENDING,
                extraction_confidence=order_data.extraction_confidence or Decimal('1.0'),
                manual_review_required=order_data.manual_review_required or False,
                notes=order_data.notes
            )
            
            # Add to session and flush to get ID
            self.db_session.add(order)
            await self.db_session.flush()
            await self.db_session.refresh(order)
            
            await self.db_session.commit()
            
            logger.info(f"Created order {order.order_id} with UIT {uit_code}")
            return order
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Order creation failed: {e}")
            raise ValidationError(f"Failed to create order: {str(e)}")
    
    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID with relationships"""
        query = (
            select(Order)
            .where(Order.order_id == order_id)
            .options(selectinload(Order.subcontractor))
        )
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_order_by_uit_code(self, uit_code: str) -> Optional[Order]:
        """Get order by UIT code for public access"""
        query = select(Order).where(Order.uit_code == uit_code)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_orders(
        self,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[OrderStatus] = None,
        client_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Order]:
        """Get orders with filtering and pagination"""
        
        query = select(Order).options(selectinload(Order.subcontractor))
        
        # Apply filters
        if status_filter:
            query = query.where(Order.order_status == status_filter)
        
        if client_filter:
            query = query.where(
                Order.client_company_name.ilike(f"%{client_filter}%")
            )
        
        if date_from:
            query = query.where(Order.created_at >= date_from)
        
        if date_to:
            query = query.where(Order.created_at <= date_to)
        
        # Pagination and ordering
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def update_order(
        self,
        order_id: str,
        order_update: OrderUpdateRequest,
        updated_by_user_id: Optional[str] = None
    ) -> Order:
        """Update order with validation"""
        
        order = await self.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        try:
            # Update fields
            update_data = order_update.dict(exclude_unset=True)
            
            # Handle address updates with geocoding
            if any(field in update_data for field in [
                'pickup_address', 'pickup_postcode', 'pickup_city'
            ]):
                pickup_coords = await self._validate_and_geocode_address(
                    update_data.get('pickup_address', order.pickup_address),
                    update_data.get('pickup_postcode', order.pickup_postcode),
                    update_data.get('pickup_city', order.pickup_city)
                )
                update_data['pickup_coordinates'] = ST_GeomFromText(
                    f"POINT({pickup_coords.longitude} {pickup_coords.latitude})", 
                    4326
                )
            
            if any(field in update_data for field in [
                'delivery_address', 'delivery_postcode', 'delivery_city'
            ]):
                delivery_coords = await self._validate_and_geocode_address(
                    update_data.get('delivery_address', order.delivery_address),
                    update_data.get('delivery_postcode', order.delivery_postcode),
                    update_data.get('delivery_city', order.delivery_city)
                )
                update_data['delivery_coordinates'] = ST_GeomFromText(
                    f"POINT({delivery_coords.longitude} {delivery_coords.latitude})", 
                    4326
                )
            
            # Apply updates
            for field, value in update_data.items():
                if hasattr(order, field):
                    setattr(order, field, value)
            
            order.updated_at = datetime.now()
            
            await self.db_session.commit()
            await self.db_session.refresh(order)
            
            logger.info(f"Updated order {order_id}")
            return order
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Order update failed: {e}")
            raise ValidationError(f"Failed to update order: {str(e)}")
    
    async def delete_order(self, order_id: str) -> bool:
        """Soft delete order (mark as cancelled)"""
        order = await self.get_order_by_id(order_id)
        if not order:
            return False
        
        if order.order_status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            raise BusinessRuleError("Cannot delete completed or cancelled orders")
        
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        await self.db_session.commit()
        logger.info(f"Cancelled order {order_id}")
        return True
    
    # Status Management
    
    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
        updated_by_user_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Order:
        """Update order status with transition validation"""
        
        order = await self.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        # Validate transition
        if not OrderTransition.is_valid_transition(order.order_status, new_status):
            valid_statuses = OrderTransition.get_valid_next_statuses(order.order_status)
            raise BusinessRuleError(
                f"Invalid status transition from {order.order_status} to {new_status}. "
                f"Valid transitions: {valid_statuses}"
            )
        
        old_status = order.order_status
        order.order_status = new_status
        order.updated_at = datetime.now()
        
        if notes:
            order.notes = f"{order.notes}\n{datetime.now().isoformat()}: {notes}" if order.notes else notes
        
        await self.db_session.commit()
        
        logger.info(f"Order {order_id} status changed from {old_status} to {new_status}")
        return order
    
    # Subcontractor Assignment
    
    async def assign_subcontractor(
        self,
        order_id: str,
        subcontractor_id: str,
        subcontractor_price: Decimal,
        payment_terms: str = "30 days after delivery",
        truck_plate: Optional[str] = None,
        driver_contact: Optional[str] = None
    ) -> Tuple[Order, Dict[str, Any]]:
        """Assign subcontractor with profit calculation"""
        
        order = await self.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        if order.order_status != OrderStatus.PENDING:
            raise BusinessRuleError("Can only assign subcontractor to pending orders")
        
        # Get subcontractor
        subcontractor_query = select(Subcontractor).where(Subcontractor.id == subcontractor_id)
        result = await self.db_session.execute(subcontractor_query)
        subcontractor = result.scalar_one_or_none()
        
        if not subcontractor:
            raise NotFoundError(f"Subcontractor {subcontractor_id} not found")
        
        # Calculate profit
        profit_input = ProfitCalculationInput(
            client_offered_price=order.client_offered_price,
            client_currency=Currency.EUR,  # Assume EUR for MVP
            subcontractor_price=subcontractor_price,
            subcontractor_currency=Currency.EUR,
            client_vat_status=VATStatus.B2B_EXEMPT,  # Assume B2B for MVP
            subcontractor_vat_status=VATStatus.B2B_EXEMPT,
            pickup_country=order.pickup_country,
            delivery_country=order.delivery_country
        )
        
        profit_result = await self.profit_engine.calculate_profit(profit_input)
        
        # Validate minimum profit requirements
        if profit_result.warnings:
            logger.warning(f"Profit calculation warnings for order {order_id}: {profit_result.warnings}")
        
        # Update order
        order.subcontractor_id = subcontractor_id
        order.subcontractor_price = subcontractor_price
        order.subcontractor_payment_terms = payment_terms
        order.truck_plate = truck_plate
        order.driver_contact = driver_contact
        order.order_status = OrderStatus.ASSIGNED
        order.updated_at = datetime.now()
        
        await self.db_session.commit()
        
        assignment_result = {
            "profit_calculation": profit_result,
            "subcontractor": subcontractor,
            "assignment_date": datetime.now()
        }
        
        logger.info(
            f"Assigned subcontractor {subcontractor_id} to order {order_id}. "
            f"Profit margin: {profit_result.profit_margin} EUR ({profit_result.profit_percentage}%)"
        )
        
        return order, assignment_result
    
    # Geographic Operations
    
    async def find_nearby_orders(
        self,
        center_coordinates: Coordinates,
        radius_km: float = 50.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find orders near specified coordinates"""
        
        spatial_query = SpatialQuery(
            center=center_coordinates,
            radius_km=radius_km,
            limit=limit
        )
        
        return await self.geographic_service.find_nearby_orders(spatial_query)
    
    async def calculate_route_distance(
        self,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate distance for order route"""
        
        order = await self.get_order_by_id(order_id)
        if not order:
            return None
        
        # Extract coordinates from PostGIS geometry
        pickup_coords = await self._extract_coordinates_from_order(order, 'pickup')
        delivery_coords = await self._extract_coordinates_from_order(order, 'delivery')
        
        if not pickup_coords or not delivery_coords:
            return None
        
        distance_result = await self.geographic_service.calculate_distance(
            pickup_coords, 
            delivery_coords
        )
        
        return {
            "order_id": order_id,
            "route_distance_km": distance_result.distance_km,
            "calculation_time": distance_result.calculation_time,
            "coordinate_system": distance_result.coordinate_system.value,
            "cached": distance_result.cached
        }
    
    # AI Integration
    
    async def create_order_from_ai_parsing(
        self,
        ai_extraction_result: Dict[str, Any],
        extraction_confidence: Decimal,
        original_pdf_path: str
    ) -> Order:
        """Create order from AI document parsing results"""
        
        try:
            # Map AI extraction to order creation request
            order_data = OrderCreateRequest(
                client_company_name=ai_extraction_result.get('client_company_name'),
                client_vat_number=ai_extraction_result.get('client_vat_number'),
                client_contact_email=ai_extraction_result.get('client_contact_email'),
                client_offered_price=Decimal(str(ai_extraction_result.get('client_offered_price', 0))),
                
                pickup_address=ai_extraction_result.get('pickup_address'),
                pickup_postcode=ai_extraction_result.get('pickup_postcode'),
                pickup_city=ai_extraction_result.get('pickup_city'),
                pickup_country=ai_extraction_result.get('pickup_country', 'RO'),
                
                delivery_address=ai_extraction_result.get('delivery_address'),
                delivery_postcode=ai_extraction_result.get('delivery_postcode'),
                delivery_city=ai_extraction_result.get('delivery_city'),
                delivery_country=ai_extraction_result.get('delivery_country', 'RO'),
                
                cargo_ldm=ai_extraction_result.get('cargo_ldm'),
                cargo_weight_kg=ai_extraction_result.get('cargo_weight_kg'),
                cargo_pallets=ai_extraction_result.get('cargo_pallets'),
                cargo_description=ai_extraction_result.get('cargo_description'),
                special_requirements=ai_extraction_result.get('special_requirements'),
                
                extraction_confidence=extraction_confidence,
                manual_review_required=extraction_confidence < Decimal('0.8'),
                notes=f"Created from AI document processing. Original PDF: {original_pdf_path}"
            )
            
            order = await self.create_order(order_data)
            
            # Update with AI-specific fields
            order.original_pdf_path = original_pdf_path
            await self.db_session.commit()
            
            logger.info(f"Created order {order.order_id} from AI parsing (confidence: {extraction_confidence})")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create order from AI parsing: {e}")
            raise ValidationError(f"AI order creation failed: {str(e)}")
    
    # Helper Methods
    
    async def _validate_and_geocode_address(
        self,
        address: str,
        postcode: Optional[str],
        city: str
    ) -> Coordinates:
        """Validate and geocode address"""
        
        full_address = f"{address}, {city}"
        if postcode:
            full_address += f", {postcode}"
        
        geocoding_result = await self.geographic_service.geocode_address(full_address)
        
        if not geocoding_result.coordinates:
            raise ValidationError(f"Could not geocode address: {full_address}")
        
        if geocoding_result.confidence < 0.5:
            logger.warning(f"Low confidence geocoding for address: {full_address} (confidence: {geocoding_result.confidence})")
        
        return geocoding_result.coordinates
    
    def _generate_uit_code(self) -> str:
        """Generate unique interaction token for public access"""
        return str(uuid.uuid4()).replace('-', '').upper()[:12]
    
    async def _extract_coordinates_from_order(
        self,
        order: Order,
        location_type: str
    ) -> Optional[Coordinates]:
        """Extract coordinates from PostGIS geometry field"""
        
        try:
            if location_type == 'pickup' and order.pickup_coordinates:
                # Use PostGIS to extract coordinates
                query = select(
                    text("ST_X(pickup_coordinates) as longitude"),
                    text("ST_Y(pickup_coordinates) as latitude")
                ).where(Order.order_id == order.order_id)
                
                result = await self.db_session.execute(query)
                row = result.fetchone()
                
                if row:
                    return Coordinates(
                        latitude=row.latitude,
                        longitude=row.longitude,
                        system=CoordinateSystem.WGS84
                    )
            
            elif location_type == 'delivery' and order.delivery_coordinates:
                query = select(
                    text("ST_X(delivery_coordinates) as longitude"),
                    text("ST_Y(delivery_coordinates) as latitude")
                ).where(Order.order_id == order.order_id)
                
                result = await self.db_session.execute(query)
                row = result.fetchone()
                
                if row:
                    return Coordinates(
                        latitude=row.latitude,
                        longitude=row.longitude,
                        system=CoordinateSystem.WGS84
                    )
        
        except Exception as e:
            logger.warning(f"Failed to extract coordinates from order {order.order_id}: {e}")
        
        return None


# Service factory function
async def create_order_service(db_session: AsyncSession) -> OrderService:
    """Factory function to create and initialize order service"""
    service = OrderService(db_session)
    await service.initialize()
    return service 