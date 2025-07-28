"""
Enhanced Order Service with Romanian Business Logic Integration
Includes caching, workflow management, and real-time communication support.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger

from app.core.logging import get_logger
from app.models.orders import Order, RomanianWorkflowState
from app.schemas.orders import OrderCreateRequest
from app.services.order.romanian_business_logic import create_romanian_business_engine
from app.services.cache_service import cache_service, create_cache_key_hash, cache_result

logger = get_logger(__name__)

class EnhancedOrderService:
    """
    Enhanced order service with Romanian business logic integration and caching.
    
    Features:
    - Comprehensive caching for performance optimization
    - Romanian business rule validation and pricing
    - Workflow-centric order lifecycle management
    - Real-time communication integration
    - AI confidence-based processing routing
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.romanian_engine = create_romanian_business_engine()
        self.cache = cache_service
    
    async def create_order_with_romanian_validation(
        self, 
        order_data: OrderCreateRequest, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create order with comprehensive Romanian business validation and caching.
        
        Process:
        1. Check cached validation results
        2. Validate using Romanian business rules
        3. Calculate pricing with VAT
        4. Create order with workflow state
        5. Cache results for future use
        """
        try:
            logger.info(f"Creating Romanian order for user {user_id}")
            
            # Convert order data to dict for processing
            order_dict = order_data.dict()
            
            # Create cache key for validation results
            validation_cache_key = create_cache_key_hash({
                "action": "romanian_validation",
                "data": order_dict
            })
            
            # Check cached Romanian validation
            cached_validation = await self.cache.get_cached_romanian_validation(validation_cache_key)
            
            if cached_validation:
                logger.info("🎯 Using cached Romanian validation result")
                validation_result = cached_validation
            else:
                # Perform Romanian validation
                validation_result = self.romanian_engine.validate_order_data(order_dict)
                
                # Cache validation result
                await self.cache.cache_romanian_validation(
                    validation_cache_key, 
                    validation_result, 
                    ttl=3600  # 1 hour
                )
                logger.info("💾 Cached Romanian validation result")
            
            # Check if validation passed
            if not validation_result["is_valid"]:
                logger.warning(f"Romanian validation failed: {validation_result['errors']}")
                return {
                    "success": False,
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            
            # Calculate pricing with caching
            pricing_cache_key = create_cache_key_hash({
                "action": "romanian_pricing",
                "data": order_dict
            })
            
            cached_pricing = await self.cache.get_cached_pricing(pricing_cache_key)
            
            if cached_pricing:
                logger.info("🎯 Using cached pricing calculation")
                pricing_result = cached_pricing
            else:
                # Calculate pricing using Romanian business rules
                pricing_result = self.romanian_engine.calculate_order_pricing(order_dict)
                
                # Cache pricing result
                await self.cache.cache_pricing_calculation(
                    pricing_cache_key,
                    pricing_result,
                    ttl=1800  # 30 minutes
                )
                logger.info("💾 Cached pricing calculation")
            
            # Create order with Romanian enhancements
            order = Order(
                # Basic order data
                client_company_name=order_data.client_company_name,
                client_vat_number=order_data.client_vat_number,
                client_contact_email=order_data.client_contact_email,
                client_offered_price=order_data.client_offered_price,
                
                # Addresses
                pickup_address=order_data.pickup_address,
                pickup_city=order_data.pickup_city,
                pickup_postcode=order_data.pickup_postcode,
                pickup_country=order_data.pickup_country or "RO",
                
                delivery_address=order_data.delivery_address,
                delivery_city=order_data.delivery_city,
                delivery_postcode=order_data.delivery_postcode,
                delivery_country=order_data.delivery_country or "RO",
                
                # Cargo information
                cargo_description=order_data.cargo_description,
                cargo_weight_kg=order_data.cargo_weight_kg,
                
                # Romanian business data
                workflow_state=RomanianWorkflowState.VALIDATED,
                romanian_validations=validation_result,
                pricing_data=pricing_result,
                vat_number=order_data.client_vat_number,
                vat_calculation=pricing_result.get("vat_calculation", {}),
                assigned_user_id=user_id,
                
                # AI processing metadata
                ai_confidence=Decimal("1.0"),  # Manual entry has high confidence
                ai_processing_metadata={
                    "source": "manual_entry",
                    "validation_method": "romanian_business_rules",
                    "pricing_method": "romanian_calculator",
                    "processed_at": datetime.utcnow().isoformat()
                }
            )
            
            # Save to database
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)
            
            # Cache the created order
            await self.cache.cache_order(
                str(order.order_id),
                {
                    **order.__dict__,
                    "user_id": user_id
                },
                ttl=1800  # 30 minutes
            )
            
            logger.info(f"✅ Romanian order created successfully: {order.order_id}")
            
            return {
                "success": True,
                "order": order,
                "validation": validation_result,
                "pricing": pricing_result,
                "workflow_state": order.workflow_state.value
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating Romanian order: {e}")
            await self.db.rollback()
            raise
    
    async def get_order_with_romanian_context(self, order_id: str) -> Dict[str, Any]:
        """
        Get order with comprehensive Romanian business context, using caching.
        """
        try:
            logger.info(f"Retrieving Romanian context for order {order_id}")
            
            # Check cache first
            cached_order = await self.cache.get_cached_order(order_id)
            
            if cached_order:
                logger.info("🎯 Using cached order data")
                order_data = cached_order
                
                # Get order from database for relationships
                stmt = select(Order).where(Order.order_id == order_id)
                result = await self.db.execute(stmt)
                order = result.scalar_one_or_none()
                
                if not order:
                    return {"success": False, "error": "Order not found"}
            else:
                # Get from database
                stmt = select(Order).where(Order.order_id == order_id)
                result = await self.db.execute(stmt)
                order = result.scalar_one_or_none()
                
                if not order:
                    return {"success": False, "error": "Order not found"}
                
                # Cache the order
                order_data = order.__dict__
                await self.cache.cache_order(order_id, order_data, ttl=1800)
                logger.info("💾 Cached order data")
            
            # Prepare Romanian context
            romanian_context = {
                "validation_status": order.romanian_validations or {},
                "pricing_breakdown": order.pricing_data or {},
                "workflow_state": order.workflow_state.value,
                "workflow_history": order.workflow_history or [],
                "vat_information": {
                    "vat_number": order.vat_number,
                    "vat_calculation": order.vat_calculation or {}
                },
                "ai_processing": {
                    "confidence": float(order.ai_confidence) if order.ai_confidence else None,
                    "metadata": order.ai_processing_metadata or {}
                },
                "collaboration": {
                    "assigned_user": order.assigned_user_id,
                    "collaborators": order.collaborators or []
                }
            }
            
            return {
                "success": True,
                "order": order,
                "romanian_context": romanian_context
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving Romanian context for order {order_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_order_workflow_state(
        self, 
        order_id: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update order workflow state using Romanian business rules with caching.
        """
        try:
            logger.info(f"Updating workflow state for order {order_id}")
            
            # Get order (with caching)
            order_result = await self.get_order_with_romanian_context(order_id)
            if not order_result["success"]:
                return order_result
            
            order = order_result["order"]
            current_state = order.workflow_state
            
            # Determine next state using Romanian business engine
            next_state_result = self.romanian_engine.determine_next_workflow_state(
                current_state.value,
                context
            )
            
            if not next_state_result["success"]:
                return {
                    "success": False,
                    "error": next_state_result["error"]
                }
            
            new_state = RomanianWorkflowState(next_state_result["next_state"])
            
            # Update workflow history
            workflow_history = order.workflow_history or []
            workflow_history.append({
                "from_state": current_state.value,
                "to_state": new_state.value,
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": context.get("user_id")
            })
            
            # Update order in database
            stmt = update(Order).where(
                Order.order_id == order_id
            ).values(
                workflow_state=new_state,
                workflow_history=workflow_history,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Invalidate cache
            await self.cache.invalidate_order(order_id)
            
            logger.info(f"✅ Workflow updated: {current_state.value} → {new_state.value}")
            
            return {
                "success": True,
                "previous_state": current_state.value,
                "new_state": new_state.value,
                "order": order,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating workflow state: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def list_orders_with_workflow_filter(
        self,
        user_id: str,
        workflow_states: List[str],
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List orders filtered by workflow states with caching optimization.
        """
        try:
            logger.info(f"Listing orders for user {user_id} with workflow states: {workflow_states}")
            
            # Create cache key for this query
            cache_key = create_cache_key_hash({
                "action": "list_orders",
                "user_id": user_id,
                "workflow_states": workflow_states,
                "skip": skip,
                "limit": limit
            })
            
            # Check cache
            cached_result = await self.cache.get("api_response", cache_key)
            if cached_result:
                logger.info("🎯 Using cached order list")
                return cached_result
            
            # Build query
            stmt = select(Order)
            
            # Apply filters
            if user_id:
                stmt = stmt.where(Order.assigned_user_id == user_id)
            
            if workflow_states:
                workflow_enums = [RomanianWorkflowState(state) for state in workflow_states]
                stmt = stmt.where(Order.workflow_state.in_(workflow_enums))
            
            # Apply pagination
            stmt = stmt.offset(skip).limit(limit).order_by(Order.updated_at.desc())
            
            # Execute query
            result = await self.db.execute(stmt)
            orders = result.scalars().all()
            
            # Prepare response
            order_list = []
            for order in orders:
                order_data = {
                    "order": order,
                    "romanian_context": {
                        "workflow_state": order.workflow_state.value,
                        "vat_number": order.vat_number,
                        "pricing_available": bool(order.pricing_data),
                        "ai_confidence": float(order.ai_confidence) if order.ai_confidence else None
                    }
                }
                order_list.append(order_data)
            
            response = {
                "success": True,
                "orders": order_list,
                "total": len(order_list),
                "skip": skip,
                "limit": limit,
                "filters": {
                    "user_id": user_id,
                    "workflow_states": workflow_states
                }
            }
            
            # Cache the response for 5 minutes
            await self.cache.set("api_response", cache_key, response, ttl=300)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error listing orders: {e}")
            return {"success": False, "error": str(e)}

async def create_enhanced_order_service(db: AsyncSession) -> EnhancedOrderService:
    """Factory function for creating enhanced order service"""
    return EnhancedOrderService(db) 