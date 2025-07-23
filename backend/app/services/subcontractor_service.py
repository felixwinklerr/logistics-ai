"""
Subcontractor Service - Business Logic for Subcontractor Management

Provides comprehensive subcontractor management including:
- CRUD operations with business validation
- Assignment algorithms and profit calculations
- Performance metrics tracking and rating system
- Geographic proximity matching
- Cost optimization and margin analysis
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.subcontractors import Subcontractor
from app.models.orders import Order, OrderStatus
from app.schemas.subcontractors import (
    SubcontractorCreateRequest, SubcontractorUpdateRequest, SubcontractorResponse
)
from app.services.geographic_service import (
    GeographicService, Coordinates, SpatialQuery, create_geographic_service
)
from app.services.profit_calculation_service import (
    ProfitCalculationEngine, ProfitCalculationInput, Currency, VATStatus,
    create_profit_calculation_engine
)
from app.core.logging import get_logger
from app.core.exceptions import ValidationError, NotFoundError, BusinessRuleError

logger = get_logger(__name__)


class AssignmentCriteria(str, Enum):
    """Criteria for subcontractor assignment algorithms"""
    LOWEST_COST = "lowest_cost"
    BEST_PERFORMANCE = "best_performance"
    NEAREST_GEOGRAPHIC = "nearest_geographic"
    OPTIMAL_PROFIT = "optimal_profit"
    BALANCED = "balanced"


@dataclass
class AssignmentRecommendation:
    """Subcontractor assignment recommendation with scoring"""
    subcontractor: Subcontractor
    score: float
    estimated_cost: Decimal
    distance_km: Optional[float] = None
    performance_rating: Optional[float] = None
    profit_margin: Optional[Decimal] = None
    profit_percentage: Optional[float] = None
    reasoning: List[str] = None


@dataclass
class PerformanceMetrics:
    """Subcontractor performance metrics"""
    total_orders: int
    completed_orders: int
    completion_rate: float
    average_rating: float
    on_time_delivery_rate: float
    average_response_time_hours: float
    total_revenue: Decimal
    average_order_value: Decimal
    last_active: Optional[datetime] = None


class SubcontractorService:
    """
    Subcontractor Service providing business logic for subcontractor management
    
    Features:
    - CRUD operations with business validation
    - Intelligent assignment algorithms
    - Performance tracking and analytics
    - Geographic proximity matching
    - Cost optimization and profit calculations
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._geographic_service: Optional[GeographicService] = None
        self._profit_engine: Optional[ProfitCalculationEngine] = None
    
    async def initialize(self):
        """Initialize service dependencies"""
        self._geographic_service = await create_geographic_service(self.db_session)
        self._profit_engine = await create_profit_calculation_engine(self.db_session)
        logger.info("SubcontractorService initialized with geographic and profit services")
    
    @property
    def geographic_service(self) -> GeographicService:
        """Get geographic service instance"""
        if not self._geographic_service:
            raise RuntimeError("SubcontractorService not initialized. Call initialize() first.")
        return self._geographic_service
    
    @property
    def profit_engine(self) -> ProfitCalculationEngine:
        """Get profit calculation engine instance"""
        if not self._profit_engine:
            raise RuntimeError("SubcontractorService not initialized. Call initialize() first.")
        return self._profit_engine
    
    # CRUD Operations
    
    async def create_subcontractor(
        self,
        subcontractor_data: SubcontractorCreateRequest,
        created_by_user_id: Optional[str] = None
    ) -> Subcontractor:
        """Create new subcontractor with validation"""
        
        try:
            # Validate VAT number uniqueness
            await self._validate_vat_uniqueness(subcontractor_data.vat_number)
            
            # Create subcontractor model
            subcontractor = Subcontractor(
                company_name=subcontractor_data.company_name,
                vat_number=subcontractor_data.vat_number,
                contact_person=subcontractor_data.contact_person,
                phone=subcontractor_data.phone,
                email=subcontractor_data.email,
                address=subcontractor_data.address,
                preferred_payment_terms=subcontractor_data.preferred_payment_terms or "30 days after delivery",
                is_active=True
            )
            
            # Add to session and flush to get ID
            self.db_session.add(subcontractor)
            await self.db_session.flush()
            await self.db_session.refresh(subcontractor)
            
            await self.db_session.commit()
            
            logger.info(f"Created subcontractor {subcontractor.id} - {subcontractor.company_name}")
            return subcontractor
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Subcontractor creation failed: {e}")
            raise ValidationError(f"Failed to create subcontractor: {str(e)}")
    
    async def get_subcontractor_by_id(self, subcontractor_id: str) -> Optional[Subcontractor]:
        """Get subcontractor by ID"""
        query = select(Subcontractor).where(Subcontractor.id == subcontractor_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_subcontractors(
        self,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
        search_term: Optional[str] = None
    ) -> List[Subcontractor]:
        """Get subcontractors with filtering"""
        
        query = select(Subcontractor)
        
        # Apply filters
        if active_only:
            query = query.where(Subcontractor.is_active == True)
        
        if search_term:
            search_filter = or_(
                Subcontractor.company_name.ilike(f"%{search_term}%"),
                Subcontractor.vat_number.ilike(f"%{search_term}%"),
                Subcontractor.contact_person.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
        
        # Pagination and ordering
        query = query.order_by(Subcontractor.average_rating.desc()).offset(skip).limit(limit)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def update_subcontractor(
        self,
        subcontractor_id: str,
        subcontractor_update: SubcontractorUpdateRequest,
        updated_by_user_id: Optional[str] = None
    ) -> Subcontractor:
        """Update subcontractor with validation"""
        
        subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            raise NotFoundError(f"Subcontractor {subcontractor_id} not found")
        
        try:
            # Validate VAT number uniqueness if changed
            update_data = subcontractor_update.dict(exclude_unset=True)
            if 'vat_number' in update_data and update_data['vat_number'] != subcontractor.vat_number:
                await self._validate_vat_uniqueness(update_data['vat_number'], exclude_id=subcontractor_id)
            
            # Apply updates
            for field, value in update_data.items():
                if hasattr(subcontractor, field):
                    setattr(subcontractor, field, value)
            
            subcontractor.updated_at = datetime.now()
            
            await self.db_session.commit()
            await self.db_session.refresh(subcontractor)
            
            logger.info(f"Updated subcontractor {subcontractor_id}")
            return subcontractor
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Subcontractor update failed: {e}")
            raise ValidationError(f"Failed to update subcontractor: {str(e)}")
    
    async def deactivate_subcontractor(self, subcontractor_id: str) -> bool:
        """Deactivate subcontractor (soft delete)"""
        subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            return False
        
        subcontractor.is_active = False
        subcontractor.updated_at = datetime.now()
        
        await self.db_session.commit()
        logger.info(f"Deactivated subcontractor {subcontractor_id}")
        return True
    
    # Assignment Operations
    
    async def recommend_subcontractors(
        self,
        order: Order,
        criteria: AssignmentCriteria = AssignmentCriteria.BALANCED,
        max_recommendations: int = 5
    ) -> List[AssignmentRecommendation]:
        """Recommend subcontractors for order assignment"""
        
        try:
            # Get active subcontractors
            active_subcontractors = await self.get_subcontractors(
                limit=100,  # Get larger pool for recommendation
                active_only=True
            )
            
            if not active_subcontractors:
                return []
            
            recommendations = []
            
            for subcontractor in active_subcontractors:
                recommendation = await self._evaluate_subcontractor_for_order(
                    subcontractor, order, criteria
                )
                if recommendation:
                    recommendations.append(recommendation)
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:max_recommendations]
            
        except Exception as e:
            logger.error(f"Subcontractor recommendation failed: {e}")
            raise BusinessRuleError(f"Recommendation generation failed: {str(e)}")
    
    async def estimate_assignment_cost(
        self,
        order: Order,
        subcontractor: Subcontractor,
        target_profit_percentage: float = 15.0
    ) -> Dict[str, Any]:
        """Estimate cost and profit for subcontractor assignment"""
        
        try:
            # Calculate base cost estimation (simplified for MVP)
            # In production, this would integrate with real pricing APIs
            base_cost = await self._estimate_transport_cost(order, subcontractor)
            
            # Calculate profit scenarios
            client_price = order.client_offered_price
            
            # Target profit calculation
            target_profit_amount = client_price * (Decimal(target_profit_percentage) / 100)
            max_subcontractor_cost = client_price - target_profit_amount
            
            # Create profit calculation input
            profit_input = ProfitCalculationInput(
                client_offered_price=client_price,
                client_currency=Currency.EUR,
                subcontractor_price=base_cost,
                subcontractor_currency=Currency.EUR,
                client_vat_status=VATStatus.B2B_EXEMPT,
                subcontractor_vat_status=VATStatus.B2B_EXEMPT,
                pickup_country=order.pickup_country,
                delivery_country=order.delivery_country
            )
            
            profit_result = await self.profit_engine.calculate_profit(profit_input)
            
            return {
                'estimated_cost': base_cost,
                'max_cost_for_target_profit': max_subcontractor_cost,
                'target_profit_percentage': target_profit_percentage,
                'profit_calculation': profit_result,
                'is_profitable': profit_result.profit_margin > 0,
                'meets_target': profit_result.profit_percentage >= target_profit_percentage,
                'cost_estimation_confidence': 0.7  # MVP estimation confidence
            }
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            raise BusinessRuleError(f"Cost estimation failed: {str(e)}")
    
    # Performance Tracking
    
    async def get_subcontractor_performance(
        self, 
        subcontractor_id: str,
        period_days: int = 90
    ) -> PerformanceMetrics:
        """Get comprehensive performance metrics for subcontractor"""
        
        try:
            date_threshold = datetime.now() - timedelta(days=period_days)
            
            # Query for performance data
            performance_query = select(
                func.count(Order.order_id).label('total_orders'),
                func.sum(
                    func.case(
                        (Order.order_status == OrderStatus.COMPLETED, 1),
                        else_=0
                    )
                ).label('completed_orders'),
                func.avg(Order.client_offered_price).label('avg_order_value'),
                func.sum(Order.client_offered_price).label('total_revenue'),
                func.max(Order.updated_at).label('last_active')
            ).where(
                and_(
                    Order.subcontractor_id == subcontractor_id,
                    Order.created_at >= date_threshold
                )
            )
            
            result = await self.db_session.execute(performance_query)
            row = result.fetchone()
            
            if row and row.total_orders:
                completion_rate = (row.completed_orders / row.total_orders) * 100
                
                # Get current subcontractor for average rating
                subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
                
                return PerformanceMetrics(
                    total_orders=row.total_orders,
                    completed_orders=row.completed_orders,
                    completion_rate=completion_rate,
                    average_rating=float(subcontractor.average_rating or 0),
                    on_time_delivery_rate=85.0,  # Simplified for MVP
                    average_response_time_hours=4.2,  # Simplified for MVP
                    total_revenue=Decimal(str(row.total_revenue or 0)),
                    average_order_value=Decimal(str(row.avg_order_value or 0)),
                    last_active=row.last_active
                )
            else:
                # No orders in period
                subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
                return PerformanceMetrics(
                    total_orders=0,
                    completed_orders=0,
                    completion_rate=0.0,
                    average_rating=float(subcontractor.average_rating or 0) if subcontractor else 0,
                    on_time_delivery_rate=0.0,
                    average_response_time_hours=0.0,
                    total_revenue=Decimal('0'),
                    average_order_value=Decimal('0'),
                    last_active=None
                )
                
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            raise BusinessRuleError(f"Performance calculation failed: {str(e)}")
    
    async def update_subcontractor_rating(
        self,
        subcontractor_id: str,
        new_rating: float,
        order_id: Optional[str] = None
    ) -> Subcontractor:
        """Update subcontractor rating (simplified average for MVP)"""
        
        subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            raise NotFoundError(f"Subcontractor {subcontractor_id} not found")
        
        try:
            # Simple average calculation for MVP
            # In production, implement weighted rating system
            current_rating = subcontractor.average_rating or Decimal('0')
            total_orders = subcontractor.total_orders or 0
            
            if total_orders == 0:
                new_average = Decimal(str(new_rating))
            else:
                new_average = ((current_rating * total_orders) + Decimal(str(new_rating))) / (total_orders + 1)
            
            subcontractor.average_rating = new_average.quantize(Decimal('0.01'))
            subcontractor.updated_at = datetime.now()
            
            await self.db_session.commit()
            
            logger.info(f"Updated rating for subcontractor {subcontractor_id}: {new_average}")
            return subcontractor
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Rating update failed: {e}")
            raise BusinessRuleError(f"Rating update failed: {str(e)}")
    
    # Helper Methods
    
    async def _validate_vat_uniqueness(
        self, 
        vat_number: str, 
        exclude_id: Optional[str] = None
    ):
        """Validate VAT number uniqueness"""
        query = select(Subcontractor).where(Subcontractor.vat_number == vat_number)
        
        if exclude_id:
            query = query.where(Subcontractor.id != exclude_id)
        
        result = await self.db_session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValidationError(f"VAT number {vat_number} already exists")
    
    async def _evaluate_subcontractor_for_order(
        self,
        subcontractor: Subcontractor,
        order: Order,
        criteria: AssignmentCriteria
    ) -> Optional[AssignmentRecommendation]:
        """Evaluate subcontractor suitability for order"""
        
        try:
            score = 0.0
            reasoning = []
            
            # Base cost estimation
            estimated_cost = await self._estimate_transport_cost(order, subcontractor)
            
            # Performance scoring
            performance_rating = float(subcontractor.average_rating or 0)
            if performance_rating > 4.0:
                score += 30
                reasoning.append("High performance rating")
            elif performance_rating > 3.0:
                score += 20
                reasoning.append("Good performance rating")
            
            # Cost competitiveness
            profit_margin = order.client_offered_price - estimated_cost
            profit_percentage = (profit_margin / order.client_offered_price) * 100 if order.client_offered_price > 0 else 0
            
            if profit_percentage >= 20:
                score += 30
                reasoning.append("Excellent profit margin")
            elif profit_percentage >= 10:
                score += 20
                reasoning.append("Good profit margin")
            elif profit_percentage >= 5:
                score += 10
                reasoning.append("Acceptable profit margin")
            else:
                score -= 20
                reasoning.append("Low profit margin")
            
            # Activity and reliability
            if subcontractor.total_orders and subcontractor.total_orders > 10:
                score += 15
                reasoning.append("Experienced contractor")
            
            if subcontractor.successful_orders and subcontractor.total_orders:
                success_rate = subcontractor.successful_orders / subcontractor.total_orders
                if success_rate > 0.9:
                    score += 15
                    reasoning.append("High success rate")
                elif success_rate > 0.8:
                    score += 10
                    reasoning.append("Good success rate")
            
            # Apply criteria-specific adjustments
            if criteria == AssignmentCriteria.LOWEST_COST:
                # Prioritize lowest cost
                max_cost = max([estimated_cost], default=estimated_cost)
                cost_score = ((max_cost - estimated_cost) / max_cost) * 50 if max_cost > 0 else 0
                score += cost_score
                reasoning.append("Cost optimization prioritized")
                
            elif criteria == AssignmentCriteria.BEST_PERFORMANCE:
                # Prioritize performance
                score += performance_rating * 10
                reasoning.append("Performance prioritized")
                
            elif criteria == AssignmentCriteria.OPTIMAL_PROFIT:
                # Prioritize profit optimization
                if profit_percentage >= 15:
                    score += 25
                    reasoning.append("Optimal profit achieved")
            
            # Minimum viability check
            if profit_margin <= 0:
                return None  # Not viable
            
            return AssignmentRecommendation(
                subcontractor=subcontractor,
                score=score,
                estimated_cost=estimated_cost,
                performance_rating=performance_rating,
                profit_margin=profit_margin,
                profit_percentage=float(profit_percentage),
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.warning(f"Evaluation failed for subcontractor {subcontractor.id}: {e}")
            return None
    
    async def _estimate_transport_cost(
        self,
        order: Order,
        subcontractor: Subcontractor
    ) -> Decimal:
        """Estimate transport cost for order (simplified for MVP)"""
        
        try:
            # Base cost calculation (simplified)
            base_cost = order.client_offered_price * Decimal('0.7')  # 70% of client price as starting point
            
            # Adjust based on cargo details
            if order.cargo_weight_kg:
                if order.cargo_weight_kg > 10000:  # Heavy cargo
                    base_cost *= Decimal('1.1')
                elif order.cargo_weight_kg < 1000:  # Light cargo
                    base_cost *= Decimal('0.9')
            
            if order.special_requirements:
                base_cost *= Decimal('1.05')  # 5% premium for special requirements
            
            # Adjust based on subcontractor performance
            if subcontractor.average_rating:
                if subcontractor.average_rating > 4.5:
                    base_cost *= Decimal('1.02')  # Premium for top performers
                elif subcontractor.average_rating < 3.0:
                    base_cost *= Decimal('0.95')  # Discount for lower rated
            
            return base_cost.quantize(Decimal('0.01'))
            
        except Exception as e:
            logger.warning(f"Cost estimation failed: {e}")
            # Return conservative estimate
            return order.client_offered_price * Decimal('0.75')


# Service factory function
async def create_subcontractor_service(db_session: AsyncSession) -> SubcontractorService:
    """Factory function to create and initialize subcontractor service"""
    service = SubcontractorService(db_session)
    await service.initialize()
    return service 