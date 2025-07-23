"""
Subcontractor API Endpoints - REST API for Subcontractor Management

Provides comprehensive REST API for subcontractor operations including:
- Full CRUD operations with validation
- Assignment recommendations with scoring algorithms
- Performance metrics and analytics
- Cost estimation and profit calculations
"""

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.exceptions import ValidationError, NotFoundError, BusinessRuleError
from app.schemas.subcontractors import (
    SubcontractorCreateRequest, SubcontractorUpdateRequest, SubcontractorResponse,
    SubcontractorListResponse, SubcontractorDetailResponse, AssignmentRequest,
    AssignmentRecommendationResponse, PerformanceMetricsResponse
)
from app.services.subcontractor_service import create_subcontractor_service, AssignmentCriteria
from app.services.order_service import create_order_service

logger = get_logger(__name__)
router = APIRouter(prefix="/subcontractors", tags=["subcontractors"])


# CRUD Operations

@router.post(
    "/",
    response_model=SubcontractorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new subcontractor",
    description="Create a new subcontractor with business validation"
)
async def create_subcontractor(
    subcontractor_data: SubcontractorCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> SubcontractorResponse:
    """
    Create a new subcontractor with validation:
    
    - Validates VAT number uniqueness
    - Applies business rules validation
    - Initializes performance tracking
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        subcontractor = await subcontractor_service.create_subcontractor(subcontractor_data)
        
        return SubcontractorResponse(
            id=str(subcontractor.id),
            company_name=subcontractor.company_name,
            vat_number=subcontractor.vat_number,
            contact_person=subcontractor.contact_person,
            phone=subcontractor.phone,
            email=subcontractor.email,
            address=subcontractor.address,
            preferred_payment_terms=subcontractor.preferred_payment_terms,
            
            total_orders=subcontractor.total_orders or 0,
            successful_orders=subcontractor.successful_orders or 0,
            average_rating=subcontractor.average_rating or Decimal('0'),
            
            is_active=subcontractor.is_active,
            created_at=subcontractor.created_at,
            updated_at=subcontractor.updated_at
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Subcontractor creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during subcontractor creation"
        )


@router.get(
    "/",
    response_model=SubcontractorListResponse,
    summary="List subcontractors",
    description="Get subcontractors with filtering and pagination"
)
async def get_subcontractors(
    skip: int = Query(0, ge=0, description="Number of subcontractors to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of subcontractors to return"),
    active_only: bool = Query(True, description="Filter to active subcontractors only"),
    search: Optional[str] = Query(None, description="Search term for company name, VAT, or contact"),
    db: AsyncSession = Depends(get_db)
) -> SubcontractorListResponse:
    """
    Get subcontractors with filtering:
    
    - Supports pagination with skip/limit
    - Filter by active status
    - Search across company name, VAT number, and contact person
    - Sorted by average rating (highest first)
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        
        subcontractors = await subcontractor_service.get_subcontractors(
            skip=skip,
            limit=limit,
            active_only=active_only,
            search_term=search
        )
        
        # Convert to response format
        subcontractor_responses = []
        for subcontractor in subcontractors:
            subcontractor_responses.append(SubcontractorResponse(
                id=str(subcontractor.id),
                company_name=subcontractor.company_name,
                vat_number=subcontractor.vat_number,
                contact_person=subcontractor.contact_person,
                phone=subcontractor.phone,
                email=subcontractor.email,
                address=subcontractor.address,
                preferred_payment_terms=subcontractor.preferred_payment_terms,
                
                total_orders=subcontractor.total_orders or 0,
                successful_orders=subcontractor.successful_orders or 0,
                average_rating=subcontractor.average_rating or Decimal('0'),
                
                is_active=subcontractor.is_active,
                created_at=subcontractor.created_at,
                updated_at=subcontractor.updated_at
            ))
        
        return SubcontractorListResponse(
            subcontractors=subcontractor_responses,
            total_count=len(subcontractor_responses),  # Simplified for MVP
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Subcontractor listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during subcontractor listing"
        )


@router.get(
    "/{subcontractor_id}",
    response_model=SubcontractorDetailResponse,
    summary="Get subcontractor details",
    description="Get detailed subcontractor information including performance metrics"
)
async def get_subcontractor(
    subcontractor_id: str,
    include_performance: bool = Query(True, description="Include performance metrics"),
    performance_period_days: int = Query(90, ge=1, le=365, description="Performance analysis period in days"),
    db: AsyncSession = Depends(get_db)
) -> SubcontractorDetailResponse:
    """
    Get detailed subcontractor information:
    
    - Complete subcontractor data
    - Performance metrics over specified period
    - Order history and analytics
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        subcontractor = await subcontractor_service.get_subcontractor_by_id(subcontractor_id)
        
        if not subcontractor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subcontractor {subcontractor_id} not found"
            )
        
        performance_metrics = None
        if include_performance:
            performance_metrics = await subcontractor_service.get_subcontractor_performance(
                subcontractor_id=subcontractor_id,
                period_days=performance_period_days
            )
        
        return SubcontractorDetailResponse(
            id=str(subcontractor.id),
            company_name=subcontractor.company_name,
            vat_number=subcontractor.vat_number,
            contact_person=subcontractor.contact_person,
            phone=subcontractor.phone,
            email=subcontractor.email,
            address=subcontractor.address,
            preferred_payment_terms=subcontractor.preferred_payment_terms,
            
            total_orders=subcontractor.total_orders or 0,
            successful_orders=subcontractor.successful_orders or 0,
            average_rating=subcontractor.average_rating or Decimal('0'),
            
            # Performance metrics
            performance_metrics=PerformanceMetricsResponse(
                total_orders=performance_metrics.total_orders,
                completed_orders=performance_metrics.completed_orders,
                completion_rate=performance_metrics.completion_rate,
                average_rating=performance_metrics.average_rating,
                on_time_delivery_rate=performance_metrics.on_time_delivery_rate,
                average_response_time_hours=performance_metrics.average_response_time_hours,
                total_revenue=performance_metrics.total_revenue,
                average_order_value=performance_metrics.average_order_value,
                last_active=performance_metrics.last_active,
                analysis_period_days=performance_period_days
            ) if performance_metrics else None,
            
            is_active=subcontractor.is_active,
            created_at=subcontractor.created_at,
            updated_at=subcontractor.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subcontractor detail retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during subcontractor retrieval"
        )


@router.put(
    "/{subcontractor_id}",
    response_model=SubcontractorResponse,
    summary="Update subcontractor",
    description="Update subcontractor information with validation"
)
async def update_subcontractor(
    subcontractor_id: str,
    subcontractor_update: SubcontractorUpdateRequest,
    db: AsyncSession = Depends(get_db)
) -> SubcontractorResponse:
    """
    Update subcontractor with validation:
    
    - Validates VAT number uniqueness if changed
    - Applies business rules validation
    - Maintains performance history
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        subcontractor = await subcontractor_service.update_subcontractor(
            subcontractor_id, subcontractor_update
        )
        
        return SubcontractorResponse(
            id=str(subcontractor.id),
            company_name=subcontractor.company_name,
            vat_number=subcontractor.vat_number,
            contact_person=subcontractor.contact_person,
            phone=subcontractor.phone,
            email=subcontractor.email,
            address=subcontractor.address,
            preferred_payment_terms=subcontractor.preferred_payment_terms,
            
            total_orders=subcontractor.total_orders or 0,
            successful_orders=subcontractor.successful_orders or 0,
            average_rating=subcontractor.average_rating or Decimal('0'),
            
            is_active=subcontractor.is_active,
            created_at=subcontractor.created_at,
            updated_at=subcontractor.updated_at
        )
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Subcontractor update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during subcontractor update"
        )


@router.delete(
    "/{subcontractor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate subcontractor",
    description="Deactivate subcontractor (soft delete)"
)
async def deactivate_subcontractor(
    subcontractor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate subcontractor (soft delete):
    
    - Sets active status to False
    - Preserves historical data
    - Prevents new assignments
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        success = await subcontractor_service.deactivate_subcontractor(subcontractor_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subcontractor {subcontractor_id} not found"
            )
        
    except Exception as e:
        logger.error(f"Subcontractor deactivation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during subcontractor deactivation"
        )


# Assignment Operations

@router.get(
    "/recommendations/{order_id}",
    response_model=List[AssignmentRecommendationResponse],
    summary="Get assignment recommendations",
    description="Get recommended subcontractors for order assignment with scoring"
)
async def get_assignment_recommendations(
    order_id: str,
    criteria: AssignmentCriteria = Query(
        AssignmentCriteria.BALANCED, 
        description="Assignment criteria algorithm"
    ),
    max_recommendations: int = Query(5, ge=1, le=10, description="Maximum number of recommendations"),
    db: AsyncSession = Depends(get_db)
) -> List[AssignmentRecommendationResponse]:
    """
    Get intelligent subcontractor recommendations:
    
    - Multiple scoring algorithms available
    - Considers performance, cost, and geographic factors
    - Includes profit calculations and reasoning
    - Sorted by recommendation score
    """
    try:
        # Get order and services
        order_service = await create_order_service(db)
        subcontractor_service = await create_subcontractor_service(db)
        
        order = await order_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        
        # Get recommendations
        recommendations = await subcontractor_service.recommend_subcontractors(
            order=order,
            criteria=criteria,
            max_recommendations=max_recommendations
        )
        
        # Convert to response format
        recommendation_responses = []
        for rec in recommendations:
            recommendation_responses.append(AssignmentRecommendationResponse(
                subcontractor=SubcontractorResponse(
                    id=str(rec.subcontractor.id),
                    company_name=rec.subcontractor.company_name,
                    vat_number=rec.subcontractor.vat_number,
                    contact_person=rec.subcontractor.contact_person,
                    phone=rec.subcontractor.phone,
                    email=rec.subcontractor.email,
                    address=rec.subcontractor.address,
                    preferred_payment_terms=rec.subcontractor.preferred_payment_terms,
                    
                    total_orders=rec.subcontractor.total_orders or 0,
                    successful_orders=rec.subcontractor.successful_orders or 0,
                    average_rating=rec.subcontractor.average_rating or Decimal('0'),
                    
                    is_active=rec.subcontractor.is_active,
                    created_at=rec.subcontractor.created_at,
                    updated_at=rec.subcontractor.updated_at
                ),
                recommendation_score=rec.score,
                estimated_cost=rec.estimated_cost,
                distance_km=rec.distance_km,
                performance_rating=rec.performance_rating,
                profit_margin=rec.profit_margin,
                profit_percentage=rec.profit_percentage,
                reasoning=rec.reasoning or []
            ))
        
        return recommendation_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assignment recommendations failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during recommendation generation"
        )


@router.post(
    "/assign",
    response_model=Dict[str, Any],
    summary="Assign subcontractor to order",
    description="Assign subcontractor to order with profit calculation and validation"
)
async def assign_subcontractor_to_order(
    assignment: AssignmentRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Assign subcontractor to order:
    
    - Validates order and subcontractor exist
    - Calculates profit margins and validates profitability
    - Updates order status to ASSIGNED
    - Returns assignment details with profit analysis
    """
    try:
        order_service = await create_order_service(db)
        
        order, assignment_result = await order_service.assign_subcontractor(
            order_id=assignment.order_id,
            subcontractor_id=assignment.subcontractor_id,
            subcontractor_price=assignment.subcontractor_price,
            payment_terms=assignment.payment_terms or "30 days after delivery",
            truck_plate=assignment.truck_plate,
            driver_contact=assignment.driver_contact
        )
        
        return {
            "order_id": str(order.order_id),
            "subcontractor_id": str(order.subcontractor_id),
            "subcontractor_company": assignment_result["subcontractor"].company_name,
            "subcontractor_price": order.subcontractor_price,
            "profit_margin": assignment_result["profit_calculation"].profit_margin,
            "profit_percentage": assignment_result["profit_calculation"].profit_percentage,
            "assignment_date": assignment_result["assignment_date"].isoformat(),
            "status": order.order_status.value,
            "warnings": assignment_result["profit_calculation"].warnings
        }
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Subcontractor assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during assignment"
        )


@router.post(
    "/estimate-cost",
    response_model=Dict[str, Any],
    summary="Estimate assignment cost",
    description="Estimate cost and profit for potential subcontractor assignment"
)
async def estimate_assignment_cost(
    order_id: str = Body(..., embed=True),
    subcontractor_id: str = Body(..., embed=True),
    target_profit_percentage: float = Body(15.0, embed=True, ge=0, le=50),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Estimate assignment cost and profit:
    
    - Calculates estimated transport cost
    - Analyzes profit scenarios
    - Validates against target profit margins
    - Returns detailed cost breakdown
    """
    try:
        # Get services and entities
        order_service = await create_order_service(db)
        subcontractor_service = await create_subcontractor_service(db)
        
        order = await order_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        
        subcontractor = await subcontractor_service.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subcontractor {subcontractor_id} not found"
            )
        
        # Estimate cost and profit
        cost_estimation = await subcontractor_service.estimate_assignment_cost(
            order=order,
            subcontractor=subcontractor,
            target_profit_percentage=target_profit_percentage
        )
        
        return cost_estimation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during cost estimation"
        )


# Performance Management

@router.post(
    "/{subcontractor_id}/rating",
    response_model=SubcontractorResponse,
    summary="Update subcontractor rating",
    description="Update subcontractor performance rating"
)
async def update_subcontractor_rating(
    subcontractor_id: str,
    rating: float = Body(..., ge=1.0, le=5.0, embed=True),
    order_id: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db)
) -> SubcontractorResponse:
    """
    Update subcontractor rating:
    
    - Accepts rating from 1.0 to 5.0
    - Updates average rating calculation
    - Links rating to specific order if provided
    - Maintains rating history for analytics
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        subcontractor = await subcontractor_service.update_subcontractor_rating(
            subcontractor_id=subcontractor_id,
            new_rating=rating,
            order_id=order_id
        )
        
        return SubcontractorResponse(
            id=str(subcontractor.id),
            company_name=subcontractor.company_name,
            vat_number=subcontractor.vat_number,
            contact_person=subcontractor.contact_person,
            phone=subcontractor.phone,
            email=subcontractor.email,
            address=subcontractor.address,
            preferred_payment_terms=subcontractor.preferred_payment_terms,
            
            total_orders=subcontractor.total_orders or 0,
            successful_orders=subcontractor.successful_orders or 0,
            average_rating=subcontractor.average_rating or Decimal('0'),
            
            is_active=subcontractor.is_active,
            created_at=subcontractor.created_at,
            updated_at=subcontractor.updated_at
        )
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} not found"
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Rating update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during rating update"
        )


@router.get(
    "/{subcontractor_id}/performance",
    response_model=PerformanceMetricsResponse,
    summary="Get performance metrics",
    description="Get detailed performance metrics for subcontractor"
)
async def get_subcontractor_performance_metrics(
    subcontractor_id: str,
    period_days: int = Query(90, ge=1, le=365, description="Analysis period in days"),
    db: AsyncSession = Depends(get_db)
) -> PerformanceMetricsResponse:
    """
    Get comprehensive performance metrics:
    
    - Order completion statistics
    - Performance ratings and trends
    - Financial analytics
    - Response time and reliability metrics
    """
    try:
        subcontractor_service = await create_subcontractor_service(db)
        
        # Verify subcontractor exists
        subcontractor = await subcontractor_service.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subcontractor {subcontractor_id} not found"
            )
        
        performance_metrics = await subcontractor_service.get_subcontractor_performance(
            subcontractor_id=subcontractor_id,
            period_days=period_days
        )
        
        return PerformanceMetricsResponse(
            total_orders=performance_metrics.total_orders,
            completed_orders=performance_metrics.completed_orders,
            completion_rate=performance_metrics.completion_rate,
            average_rating=performance_metrics.average_rating,
            on_time_delivery_rate=performance_metrics.on_time_delivery_rate,
            average_response_time_hours=performance_metrics.average_response_time_hours,
            total_revenue=performance_metrics.total_revenue,
            average_order_value=performance_metrics.average_order_value,
            last_active=performance_metrics.last_active,
            analysis_period_days=period_days
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during performance metrics retrieval"
        ) 