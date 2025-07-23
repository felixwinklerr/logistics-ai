"""
Order Repository - Data Access Layer for Order Management

Provides optimized database operations for orders including:
- Async SQLAlchemy CRUD operations
- PostGIS spatial queries for geographic operations
- Performance optimizations with proper indexing
- Complex filtering and search capabilities
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select, update, delete, and_, or_, func, text, 
    Index, desc, asc
)
from sqlalchemy.orm import selectinload, joinedload
from geoalchemy2 import Geography
from geoalchemy2.functions import (
    ST_Distance, ST_DWithin, ST_GeomFromText, 
    ST_AsText, ST_X, ST_Y, ST_Transform
)

from app.models.orders import Order, OrderStatus
from app.models.subcontractors import Subcontractor
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)


class OrderFilterCriteria:
    """Advanced filtering criteria for order queries"""
    
    def __init__(
        self,
        status: Optional[OrderStatus] = None,
        client_name: Optional[str] = None,
        client_vat: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        pickup_city: Optional[str] = None,
        delivery_city: Optional[str] = None,
        subcontractor_id: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        manual_review_required: Optional[bool] = None,
        has_subcontractor: Optional[bool] = None,
        profit_margin_min: Optional[Decimal] = None,
        profit_margin_max: Optional[Decimal] = None
    ):
        self.status = status
        self.client_name = client_name
        self.client_vat = client_vat
        self.date_from = date_from
        self.date_to = date_to
        self.pickup_city = pickup_city
        self.delivery_city = delivery_city
        self.subcontractor_id = subcontractor_id
        self.min_price = min_price
        self.max_price = max_price
        self.manual_review_required = manual_review_required
        self.has_subcontractor = has_subcontractor
        self.profit_margin_min = profit_margin_min
        self.profit_margin_max = profit_margin_max


class SpatialSearchCriteria:
    """Spatial search criteria for geographic queries"""
    
    def __init__(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        location_type: str = "pickup"  # "pickup", "delivery", or "both"
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = radius_km
        self.location_type = location_type


class OrderRepository:
    """
    Order Repository - Optimized data access layer for order operations
    
    Features:
    - High-performance async SQLAlchemy operations
    - PostGIS spatial queries with proper indexing
    - Complex filtering and search capabilities
    - Optimized joins and query patterns
    - Geographic distance calculations and spatial searches
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    # Basic CRUD Operations
    
    async def create(self, order: Order) -> Order:
        """Create new order with optimized insertion"""
        try:
            self.db_session.add(order)
            await self.db_session.flush()
            await self.db_session.refresh(order)
            return order
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to create order: {e}")
            raise DatabaseError(f"Order creation failed: {str(e)}")
    
    async def get_by_id(self, order_id: str, include_subcontractor: bool = True) -> Optional[Order]:
        """Get order by ID with optional relationships"""
        try:
            query = select(Order).where(Order.order_id == order_id)
            
            if include_subcontractor:
                query = query.options(selectinload(Order.subcontractor))
            
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise DatabaseError(f"Order retrieval failed: {str(e)}")
    
    async def get_by_uit_code(self, uit_code: str) -> Optional[Order]:
        """Get order by UIT code for public access"""
        try:
            query = select(Order).where(Order.uit_code == uit_code)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get order by UIT {uit_code}: {e}")
            raise DatabaseError(f"Order retrieval by UIT failed: {str(e)}")
    
    async def update(self, order: Order) -> Order:
        """Update existing order"""
        try:
            order.updated_at = datetime.now()
            await self.db_session.flush()
            await self.db_session.refresh(order)
            return order
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to update order {order.order_id}: {e}")
            raise DatabaseError(f"Order update failed: {str(e)}")
    
    async def delete(self, order_id: str) -> bool:
        """Hard delete order (use with caution)"""
        try:
            query = delete(Order).where(Order.order_id == order_id)
            result = await self.db_session.execute(query)
            return result.rowcount > 0
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to delete order {order_id}: {e}")
            raise DatabaseError(f"Order deletion failed: {str(e)}")
    
    # Advanced Query Operations
    
    async def get_orders_with_filters(
        self,
        filters: OrderFilterCriteria,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> List[Order]:
        """Get orders with advanced filtering"""
        
        try:
            query = select(Order).options(selectinload(Order.subcontractor))
            
            # Apply filters
            query = self._apply_filters(query, filters)
            
            # Apply ordering
            if order_direction.lower() == "desc":
                query = query.order_by(desc(getattr(Order, order_by)))
            else:
                query = query.order_by(asc(getattr(Order, order_by)))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get orders with filters: {e}")
            raise DatabaseError(f"Filtered order query failed: {str(e)}")
    
    async def count_orders_with_filters(self, filters: OrderFilterCriteria) -> int:
        """Count orders matching filters"""
        try:
            query = select(func.count(Order.order_id))
            query = self._apply_filters(query, filters)
            
            result = await self.db_session.execute(query)
            return result.scalar()
            
        except Exception as e:
            logger.error(f"Failed to count orders with filters: {e}")
            raise DatabaseError(f"Order count query failed: {str(e)}")
    
    # Geographic Operations
    
    async def find_orders_within_radius(
        self,
        search_criteria: SpatialSearchCriteria,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find orders within radius using PostGIS spatial queries"""
        
        try:
            center_point = f"POINT({search_criteria.center_lon} {search_criteria.center_lat})"
            radius_meters = search_criteria.radius_km * 1000
            
            if search_criteria.location_type == "pickup":
                distance_column = ST_Distance(
                    Order.pickup_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography)
                ) / 1000.0
                
                where_clause = ST_DWithin(
                    Order.pickup_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography),
                    radius_meters
                )
                
            elif search_criteria.location_type == "delivery":
                distance_column = ST_Distance(
                    Order.delivery_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography)
                ) / 1000.0
                
                where_clause = ST_DWithin(
                    Order.delivery_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography),
                    radius_meters
                )
                
            else:  # both
                # Find orders where either pickup or delivery is within radius
                pickup_distance = ST_Distance(
                    Order.pickup_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography)
                ) / 1000.0
                
                delivery_distance = ST_Distance(
                    Order.delivery_coordinates.cast(Geography),
                    ST_GeomFromText(center_point, 4326).cast(Geography)
                ) / 1000.0
                
                distance_column = func.least(pickup_distance, delivery_distance)
                
                where_clause = or_(
                    ST_DWithin(
                        Order.pickup_coordinates.cast(Geography),
                        ST_GeomFromText(center_point, 4326).cast(Geography),
                        radius_meters
                    ),
                    ST_DWithin(
                        Order.delivery_coordinates.cast(Geography),
                        ST_GeomFromText(center_point, 4326).cast(Geography),
                        radius_meters
                    )
                )
            
            query = select(
                Order.order_id,
                Order.client_company_name,
                Order.client_offered_price,
                Order.order_status,
                Order.pickup_address,
                Order.pickup_city,
                Order.delivery_address,
                Order.delivery_city,
                ST_AsText(Order.pickup_coordinates).label('pickup_coords'),
                ST_AsText(Order.delivery_coordinates).label('delivery_coords'),
                distance_column.label('distance_km')
            ).where(where_clause).order_by(distance_column).limit(limit)
            
            result = await self.db_session.execute(query)
            
            orders = []
            for row in result.fetchall():
                orders.append({
                    'order_id': row.order_id,
                    'client_company_name': row.client_company_name,
                    'client_offered_price': row.client_offered_price,
                    'order_status': row.order_status,
                    'pickup_address': row.pickup_address,
                    'pickup_city': row.pickup_city,
                    'delivery_address': row.delivery_address,
                    'delivery_city': row.delivery_city,
                    'pickup_coordinates': row.pickup_coords,
                    'delivery_coordinates': row.delivery_coords,
                    'distance_km': float(row.distance_km)
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Spatial search failed: {e}")
            raise DatabaseError(f"Spatial order search failed: {str(e)}")
    
    async def calculate_route_distance(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Calculate distance between pickup and delivery for an order"""
        
        try:
            # Use Romanian projection (EPSG:3844) for accurate distance calculation
            query = select(
                Order.order_id,
                ST_Distance(
                    ST_Transform(Order.pickup_coordinates, 3844),
                    ST_Transform(Order.delivery_coordinates, 3844)
                ).label('distance_meters'),
                ST_AsText(Order.pickup_coordinates).label('pickup_coords'),
                ST_AsText(Order.delivery_coordinates).label('delivery_coords')
            ).where(Order.order_id == order_id)
            
            result = await self.db_session.execute(query)
            row = result.fetchone()
            
            if row:
                return {
                    'order_id': row.order_id,
                    'distance_km': round(row.distance_meters / 1000.0, 2),
                    'distance_meters': row.distance_meters,
                    'pickup_coordinates': row.pickup_coords,
                    'delivery_coordinates': row.delivery_coords,
                    'coordinate_system': 'EPSG:3844'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Route distance calculation failed for order {order_id}: {e}")
            raise DatabaseError(f"Route distance calculation failed: {str(e)}")
    
    # Business Analytics Queries
    
    async def get_orders_by_status_counts(self) -> Dict[str, int]:
        """Get order counts by status"""
        try:
            query = select(
                Order.order_status,
                func.count(Order.order_id).label('count')
            ).group_by(Order.order_status)
            
            result = await self.db_session.execute(query)
            
            status_counts = {}
            for row in result.fetchall():
                status_counts[row.order_status.value] = row.count
            
            return status_counts
            
        except Exception as e:
            logger.error(f"Status counts query failed: {e}")
            raise DatabaseError(f"Status counts query failed: {str(e)}")
    
    async def get_profit_analytics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get profit analytics for orders with subcontractors"""
        
        try:
            query = select(
                func.count(Order.order_id).label('total_orders'),
                func.sum(Order.client_offered_price).label('total_revenue'),
                func.sum(Order.subcontractor_price).label('total_costs'),
                func.sum(Order.profit_margin).label('total_profit'),
                func.avg(Order.profit_percentage).label('avg_profit_percentage'),
                func.min(Order.profit_percentage).label('min_profit_percentage'),
                func.max(Order.profit_percentage).label('max_profit_percentage')
            ).where(
                and_(
                    Order.subcontractor_price.is_not(None),
                    Order.profit_margin.is_not(None)
                )
            )
            
            if date_from:
                query = query.where(Order.created_at >= date_from)
            if date_to:
                query = query.where(Order.created_at <= date_to)
            
            result = await self.db_session.execute(query)
            row = result.fetchone()
            
            if row:
                return {
                    'total_orders': row.total_orders or 0,
                    'total_revenue': float(row.total_revenue or 0),
                    'total_costs': float(row.total_costs or 0),
                    'total_profit': float(row.total_profit or 0),
                    'avg_profit_percentage': float(row.avg_profit_percentage or 0),
                    'min_profit_percentage': float(row.min_profit_percentage or 0),
                    'max_profit_percentage': float(row.max_profit_percentage or 0),
                    'profit_margin_percentage': round(
                        (float(row.total_profit or 0) / float(row.total_revenue or 1)) * 100, 2
                    )
                }
            
            return {
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_costs': 0.0,
                'total_profit': 0.0,
                'avg_profit_percentage': 0.0,
                'min_profit_percentage': 0.0,
                'max_profit_percentage': 0.0,
                'profit_margin_percentage': 0.0
            }
            
        except Exception as e:
            logger.error(f"Profit analytics query failed: {e}")
            raise DatabaseError(f"Profit analytics query failed: {str(e)}")
    
    async def get_orders_requiring_review(self) -> List[Order]:
        """Get orders requiring manual review"""
        try:
            query = select(Order).options(selectinload(Order.subcontractor)).where(
                or_(
                    Order.manual_review_required == True,
                    Order.extraction_confidence < 0.8,
                    and_(
                        Order.order_status == OrderStatus.PENDING,
                        Order.created_at < datetime.now() - timedelta(hours=24)
                    )
                )
            ).order_by(Order.created_at.asc())
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Manual review query failed: {e}")
            raise DatabaseError(f"Manual review query failed: {str(e)}")
    
    # Performance Optimized Queries
    
    async def get_recent_orders_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent orders summary with minimal data for dashboard"""
        try:
            query = select(
                Order.order_id,
                Order.client_company_name,
                Order.client_offered_price,
                Order.order_status,
                Order.pickup_city,
                Order.delivery_city,
                Order.created_at,
                Order.updated_at
            ).order_by(Order.created_at.desc()).limit(limit)
            
            result = await self.db_session.execute(query)
            
            orders = []
            for row in result.fetchall():
                orders.append({
                    'order_id': row.order_id,
                    'client_company_name': row.client_company_name,
                    'client_offered_price': float(row.client_offered_price),
                    'order_status': row.order_status.value,
                    'pickup_city': row.pickup_city,
                    'delivery_city': row.delivery_city,
                    'created_at': row.created_at.isoformat(),
                    'updated_at': row.updated_at.isoformat()
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Recent orders summary query failed: {e}")
            raise DatabaseError(f"Recent orders summary failed: {str(e)}")
    
    # Helper Methods
    
    def _apply_filters(self, query, filters: OrderFilterCriteria):
        """Apply filtering criteria to query"""
        
        if filters.status:
            query = query.where(Order.order_status == filters.status)
        
        if filters.client_name:
            query = query.where(
                Order.client_company_name.ilike(f"%{filters.client_name}%")
            )
        
        if filters.client_vat:
            query = query.where(Order.client_vat_number == filters.client_vat)
        
        if filters.date_from:
            query = query.where(Order.created_at >= filters.date_from)
        
        if filters.date_to:
            query = query.where(Order.created_at <= filters.date_to)
        
        if filters.pickup_city:
            query = query.where(
                Order.pickup_city.ilike(f"%{filters.pickup_city}%")
            )
        
        if filters.delivery_city:
            query = query.where(
                Order.delivery_city.ilike(f"%{filters.delivery_city}%")
            )
        
        if filters.subcontractor_id:
            query = query.where(Order.subcontractor_id == filters.subcontractor_id)
        
        if filters.min_price is not None:
            query = query.where(Order.client_offered_price >= filters.min_price)
        
        if filters.max_price is not None:
            query = query.where(Order.client_offered_price <= filters.max_price)
        
        if filters.manual_review_required is not None:
            query = query.where(Order.manual_review_required == filters.manual_review_required)
        
        if filters.has_subcontractor is not None:
            if filters.has_subcontractor:
                query = query.where(Order.subcontractor_id.is_not(None))
            else:
                query = query.where(Order.subcontractor_id.is_(None))
        
        if filters.profit_margin_min is not None:
            query = query.where(Order.profit_margin >= filters.profit_margin_min)
        
        if filters.profit_margin_max is not None:
            query = query.where(Order.profit_margin <= filters.profit_margin_max)
        
        return query


# Repository factory function
def create_order_repository(db_session: AsyncSession) -> OrderRepository:
    """Factory function to create order repository"""
    return OrderRepository(db_session) 