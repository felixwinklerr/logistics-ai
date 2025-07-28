"""
Enhanced Order Service with Romanian Business Logic Integration
Extends the existing order service with Romanian freight forwarding capabilities.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.orders import Order
from app.schemas.orders import OrderCreateRequest, OrderUpdateRequest, OrderResponse
from app.services.order.romanian_business_logic import (
    RomanianBusinessRuleEngine, 
    OrderWorkflowState,
    create_romanian_business_engine
)
from app.core.logging import get_logger

logger = get_logger(__name__)

class EnhancedOrderService:
    """
    Enhanced order service with Romanian business logic integration.
    Implements workflow-centric design as per creative phase decision.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.romanian_engine = create_romanian_business_engine()
        
    async def create_order_with_romanian_validation(
        self, 
        order_data: OrderCreate,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create order with Romanian business rule validation.
        
        Args:
            order_data: Order creation data
            user_id: ID of user creating the order
            
        Returns:
            Dict with order data and validation results
        """
        try:
            logger.info(f"Creating order with Romanian validation for user {user_id}")
            
            # Convert Pydantic model to dict for business rule validation
            order_dict = order_data.dict()
            
            # Validate against Romanian business rules
            validation_result = self.romanian_engine.validate_order_data(order_dict)
            
            if not validation_result["is_valid"]:
                logger.warning(f"Order validation failed: {validation_result['errors']}")
                return {
                    "success": False,
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", []),
                    "order": None
                }
            
            # Calculate Romanian pricing
            pricing_result = self.romanian_engine.calculate_order_pricing(order_dict)
            
            # Create order with calculated pricing
            order_create_data = order_data.dict()
            order_create_data.update({
                "user_id": user_id,
                "pricing_data": pricing_result,
                "workflow_state": OrderWorkflowState.DRAFT.value,
                "romanian_validations": validation_result["romanian_validations"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            # Create order in database
            new_order = Order(**order_create_data)
            self.db.add(new_order)
            await self.db.commit()
            await self.db.refresh(new_order)
            
            logger.info(f"Order created successfully with ID: {new_order.id}")
            
            return {
                "success": True,
                "order": new_order,
                "pricing": pricing_result,
                "validation": validation_result,
                "warnings": validation_result.get("warnings", [])
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            await self.db.rollback()
            raise
    
    async def update_order_workflow_state(
        self, 
        order_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update order workflow state based on Romanian business rules.
        
        Args:
            order_id: ID of order to update
            context: Context data for state transition
            
        Returns:
            Updated order data with new state
        """
        try:
            logger.info(f"Updating workflow state for order {order_id}")
            
            # Get current order
            result = await self.db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"Order {order_id} not found")
                return {"success": False, "error": "Order not found"}
            
            # Get current state
            current_state = OrderWorkflowState(order.workflow_state)
            
            # Determine next state using Romanian business rules
            next_state = self.romanian_engine.determine_next_workflow_state(
                current_state, context or {}
            )
            
            # Update order state
            await self.db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(
                    workflow_state=next_state.value,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            # Refresh order data
            await self.db.refresh(order)
            
            logger.info(
                f"Order {order_id} state updated: {current_state.value} → {next_state.value}"
            )
            
            return {
                "success": True,
                "order": order,
                "previous_state": current_state.value,
                "new_state": next_state.value
            }
            
        except Exception as e:
            logger.error(f"Error updating order workflow state: {str(e)}")
            await self.db.rollback()
            raise
    
    async def get_order_with_romanian_context(self, order_id: str) -> Dict[str, Any]:
        """
        Get order with Romanian business context and validation status.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            Order data with Romanian context
        """
        try:
            logger.info(f"Retrieving order {order_id} with Romanian context")
            
            # Get order
            result = await self.db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            
            if not order:
                return {"success": False, "error": "Order not found"}
            
            # Get workflow state info
            workflow_state = OrderWorkflowState(order.workflow_state)
            
            # Prepare Romanian context
            romanian_context = {
                "workflow_state": {
                    "current": workflow_state.value,
                    "display_name": self._get_workflow_display_name(workflow_state),
                    "next_actions": self._get_next_actions(workflow_state)
                },
                "pricing_breakdown": order.pricing_data,
                "validation_status": order.romanian_validations,
                "business_rules_applied": True
            }
            
            return {
                "success": True,
                "order": order,
                "romanian_context": romanian_context
            }
            
        except Exception as e:
            logger.error(f"Error retrieving order with Romanian context: {str(e)}")
            raise
    
    async def list_orders_with_workflow_filter(
        self, 
        user_id: str,
        workflow_states: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List orders with workflow state filtering for Romanian context.
        
        Args:
            user_id: User ID for filtering
            workflow_states: List of workflow states to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of orders with Romanian context
        """
        try:
            logger.info(f"Listing orders for user {user_id} with workflow filter")
            
            # Build query
            query = select(Order).where(Order.user_id == user_id)
            
            if workflow_states:
                query = query.where(Order.workflow_state.in_(workflow_states))
            
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await self.db.execute(query)
            orders = result.scalars().all()
            
            # Add Romanian context to each order
            orders_with_context = []
            for order in orders:
                workflow_state = OrderWorkflowState(order.workflow_state)
                order_dict = {
                    "order": order,
                    "workflow_display": self._get_workflow_display_name(workflow_state),
                    "next_actions": self._get_next_actions(workflow_state),
                    "romanian_status": "compliant"  # Simplified for foundation
                }
                orders_with_context.append(order_dict)
            
            return {
                "success": True,
                "orders": orders_with_context,
                "total": len(orders_with_context)
            }
            
        except Exception as e:
            logger.error(f"Error listing orders with workflow filter: {str(e)}")
            raise
    
    def _get_workflow_display_name(self, state: OrderWorkflowState) -> str:
        """Get user-friendly display name for workflow state."""
        display_names = {
            OrderWorkflowState.DRAFT: "Draft",
            OrderWorkflowState.DOCUMENT_UPLOADED: "Document Uploaded",
            OrderWorkflowState.AI_PROCESSING: "AI Processing",
            OrderWorkflowState.VALIDATION_REQUIRED: "Validation Required",
            OrderWorkflowState.VALIDATED: "Validated",
            OrderWorkflowState.PRICING_CALCULATED: "Pricing Calculated",
            OrderWorkflowState.CONFIRMED: "Confirmed",
            OrderWorkflowState.SUBCONTRACTOR_ASSIGNED: "Subcontractor Assigned",
            OrderWorkflowState.IN_TRANSIT: "In Transit",
            OrderWorkflowState.CUSTOMS_CLEARANCE: "Customs Clearance",
            OrderWorkflowState.DELIVERED: "Delivered",
            OrderWorkflowState.INVOICED: "Invoiced",
            OrderWorkflowState.PAID: "Paid",
            OrderWorkflowState.COMPLETED: "Completed",
            OrderWorkflowState.CANCELLED: "Cancelled"
        }
        return display_names.get(state, state.value)
    
    def _get_next_actions(self, state: OrderWorkflowState) -> List[str]:
        """Get available next actions for workflow state."""
        next_actions = {
            OrderWorkflowState.DRAFT: ["Upload Document", "Cancel"],
            OrderWorkflowState.DOCUMENT_UPLOADED: ["Process with AI", "Manual Entry"],
            OrderWorkflowState.AI_PROCESSING: ["View Progress"],
            OrderWorkflowState.VALIDATION_REQUIRED: ["Validate Data", "Edit Details"],
            OrderWorkflowState.VALIDATED: ["Calculate Pricing", "Edit"],
            OrderWorkflowState.PRICING_CALCULATED: ["Confirm Order", "Adjust Pricing"],
            OrderWorkflowState.CONFIRMED: ["Assign Subcontractor", "Modify"],
            OrderWorkflowState.SUBCONTRACTOR_ASSIGNED: ["Start Transit", "Change Assignment"],
            OrderWorkflowState.IN_TRANSIT: ["Track Shipment", "Update Status"],
            OrderWorkflowState.CUSTOMS_CLEARANCE: ["Process Customs", "Track"],
            OrderWorkflowState.DELIVERED: ["Generate Invoice", "Confirm Delivery"],
            OrderWorkflowState.INVOICED: ["Record Payment", "Send Reminder"],
            OrderWorkflowState.PAID: ["Complete Order", "Generate Report"],
            OrderWorkflowState.COMPLETED: ["View Details", "Duplicate Order"],
            OrderWorkflowState.CANCELLED: ["View Details", "Reactivate"]
        }
        return next_actions.get(state, ["View Details"])

# Service factory for dependency injection
async def create_enhanced_order_service(db_session: AsyncSession) -> EnhancedOrderService:
    """Factory function for enhanced order service."""
    return EnhancedOrderService(db_session)
