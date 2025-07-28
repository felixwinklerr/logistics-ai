"""
WebSocket API Endpoints
Handles real-time communication for order collaboration and workflow updates.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.services.websocket_manager import websocket_manager, create_websocket_service

logger = get_logger(__name__)
websocket_router = APIRouter()

async def get_user_from_token(token: str) -> Dict[str, Any]:
    """Extract user information from JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        username = payload.get("username", f"User-{user_id}")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "user_id": user_id,
            "username": username,
            "email": payload.get("email"),
            "role": payload.get("role", "user")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@websocket_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Main WebSocket endpoint for real-time communication.
    
    Supports:
    - User authentication via JWT token
    - Order room management
    - Real-time collaboration
    - Workflow state updates
    - User presence tracking
    """
    try:
        # Authenticate user
        user_info = await get_user_from_token(token)
        user_id = user_info["user_id"]
        username = user_info["username"]
        
        # Connect user
        await websocket_manager.connect(websocket, user_id, username)
        
        # Create WebSocket service for this connection
        ws_service = await create_websocket_service(db)
        
        logger.info(f"🔗 WebSocket connected: {username} ({user_id})")
        
        # Send connection confirmation
        await websocket_manager.send_to_user(user_id, {
            "type": "connection:established",
            "payload": {
                "userId": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket connection established successfully"
            }
        })
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Route message based on type
                await handle_websocket_message(ws_service, user_id, username, message)
                
        except WebSocketDisconnect:
            logger.info(f"🚪 WebSocket disconnected: {username} ({user_id})")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON received from {username}: {e}")
            await websocket_manager.send_to_user(user_id, {
                "type": "error",
                "payload": {"message": "Invalid JSON format"}
            })
        except Exception as e:
            logger.error(f"❌ WebSocket error for {username}: {e}")
            await websocket_manager.send_to_user(user_id, {
                "type": "error",
                "payload": {"message": "Internal server error"}
            })
            
    except HTTPException as e:
        logger.warning(f"🚫 WebSocket authentication failed: {e.detail}")
        await websocket.close(code=4001, reason="Authentication failed")
    except Exception as e:
        logger.error(f"❌ WebSocket connection error: {e}")
        await websocket.close(code=4000, reason="Internal server error")
    finally:
        # Cleanup connection
        try:
            await websocket_manager.disconnect(user_id)
        except:
            pass

async def handle_websocket_message(
    ws_service,
    user_id: str,
    username: str,
    message: Dict[str, Any]
):
    """Route and handle WebSocket messages based on type"""
    
    message_type = message.get("type")
    payload = message.get("payload", {})
    
    logger.info(f"📨 Message from {username}: {message_type}")
    
    try:
        if message_type == "join_order":
            await handle_join_order(user_id, payload)
            
        elif message_type == "leave_order":
            await handle_leave_order(user_id, payload)
            
        elif message_type == "user_editing":
            await handle_user_editing(user_id, payload)
            
        elif message_type == "user_stop_editing":
            await handle_user_stop_editing(user_id, payload)
            
        elif message_type == "update_order_field":
            await handle_update_order_field(ws_service, user_id, payload)
            
        elif message_type == "workflow_state_change":
            await handle_workflow_state_change(ws_service, user_id, payload)
            
        elif message_type == "ping":
            await handle_ping(user_id, payload)
            
        else:
            logger.warning(f"🤷 Unknown message type: {message_type}")
            await websocket_manager.send_to_user(user_id, {
                "type": "error",
                "payload": {"message": f"Unknown message type: {message_type}"}
            })
            
    except Exception as e:
        logger.error(f"❌ Error handling message {message_type}: {e}")
        await websocket_manager.send_to_user(user_id, {
            "type": "error",
            "payload": {"message": f"Error processing {message_type}: {str(e)}"}
        })

async def handle_join_order(user_id: str, payload: Dict[str, Any]):
    """Handle user joining an order room"""
    order_id = payload.get("orderId")
    if not order_id:
        raise ValueError("Order ID is required")
    
    await websocket_manager.join_order_room(user_id, order_id)

async def handle_leave_order(user_id: str, payload: Dict[str, Any]):
    """Handle user leaving an order room"""
    order_id = payload.get("orderId")
    if not order_id:
        raise ValueError("Order ID is required")
    
    await websocket_manager.leave_order_room(user_id, order_id)

async def handle_user_editing(user_id: str, payload: Dict[str, Any]):
    """Handle user starting to edit a field"""
    order_id = payload.get("orderId")
    field = payload.get("field")
    
    if not order_id or not field:
        raise ValueError("Order ID and field are required")
    
    await websocket_manager.update_user_presence(user_id, order_id, field)

async def handle_user_stop_editing(user_id: str, payload: Dict[str, Any]):
    """Handle user stopping editing"""
    order_id = payload.get("orderId")
    
    if not order_id:
        raise ValueError("Order ID is required")
    
    await websocket_manager.update_user_presence(user_id, order_id, None)

async def handle_update_order_field(ws_service, user_id: str, payload: Dict[str, Any]):
    """Handle real-time order field updates"""
    order_id = payload.get("orderId")
    field = payload.get("field")
    value = payload.get("value")
    
    if not order_id or not field:
        raise ValueError("Order ID and field are required")
    
    await ws_service.handle_order_field_update(user_id, order_id, field, value)

async def handle_workflow_state_change(ws_service, user_id: str, payload: Dict[str, Any]):
    """Handle workflow state changes"""
    order_id = payload.get("orderId")
    context = payload.get("context", {})
    
    if not order_id:
        raise ValueError("Order ID is required")
    
    result = await ws_service.handle_workflow_state_change(user_id, order_id, context)
    
    # Send result back to requesting user
    await websocket_manager.send_to_user(user_id, {
        "type": "workflow:state_changed",
        "payload": result
    })

async def handle_ping(user_id: str, payload: Dict[str, Any]):
    """Handle ping/keepalive messages"""
    await websocket_manager.send_to_user(user_id, {
        "type": "pong",
        "payload": {
            "timestamp": datetime.utcnow().isoformat(),
            "originalPayload": payload
        }
    })

# REST API endpoints for WebSocket management

@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    stats = websocket_manager.get_connection_stats()
    return JSONResponse(content={
        "success": True,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    })

@websocket_router.get("/ws/orders/{order_id}/users")
async def get_active_users_in_order(order_id: str):
    """Get list of active users in an order room"""
    active_users = await websocket_manager.get_active_users_in_order(order_id)
    return JSONResponse(content={
        "success": True,
        "orderId": order_id,
        "activeUsers": active_users,
        "count": len(active_users),
        "timestamp": datetime.utcnow().isoformat()
    })

@websocket_router.post("/ws/orders/{order_id}/broadcast")
async def broadcast_to_order(
    order_id: str,
    message: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Broadcast a message to all users in an order room (for system notifications)"""
    try:
        await websocket_manager.broadcast_to_order(order_id, {
            "type": "system:notification",
            "payload": {
                "orderId": order_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return JSONResponse(content={
            "success": True,
            "message": "Broadcast sent successfully",
            "orderId": order_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error broadcasting to order {order_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        ) 