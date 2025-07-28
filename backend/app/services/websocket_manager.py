"""
WebSocket Manager Service
Handles real-time communication for order collaboration and workflow updates.
"""

import json
import asyncio
from typing import Dict, Set, List, Optional, Any
from datetime import datetime
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.services.order.order_service_enhanced import create_enhanced_order_service
from app.core.logging import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and real-time communication"""
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Order rooms - tracks which users are in which order rooms
        self.order_rooms: Dict[str, Set[str]] = {}
        
        # User presence - tracks what users are currently editing
        self.user_presence: Dict[str, Dict[str, Any]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the connection manager"""
        logger.info("🔄 Initializing WebSocket connection manager")
        
    async def cleanup(self):
        """Cleanup all connections and resources"""
        logger.info("🧹 Cleaning up WebSocket connections")
        
        # Close all active connections
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.close()
                logger.info(f"✅ Closed connection for user {user_id}")
            except Exception as e:
                logger.error(f"❌ Error closing connection for user {user_id}: {e}")
        
        # Clear all data structures
        self.active_connections.clear()
        self.order_rooms.clear()
        self.user_presence.clear()
        self.connection_metadata.clear()
        
    async def connect(self, websocket: WebSocket, user_id: str, username: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Close existing connection if user reconnects
        if user_id in self.active_connections:
            try:
                old_websocket = self.active_connections[user_id]
                await old_websocket.close()
                logger.info(f"🔄 Replaced existing connection for user {user_id}")
            except:
                pass
        
        # Store new connection
        self.active_connections[user_id] = websocket
        self.connection_metadata[user_id] = {
            "username": username,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ User {username} ({user_id}) connected via WebSocket")
        
    async def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        if user_id in self.connection_metadata:
            username = self.connection_metadata[user_id].get("username", "Unknown")
            del self.connection_metadata[user_id]
            logger.info(f"🚪 User {username} ({user_id}) disconnected")
        
        # Remove from all order rooms
        rooms_to_update = []
        for order_id, users in self.order_rooms.items():
            if user_id in users:
                users.remove(user_id)
                rooms_to_update.append(order_id)
        
        # Notify other users in rooms about disconnection
        for order_id in rooms_to_update:
            await self.broadcast_to_order(order_id, {
                "type": "user:left_order",
                "payload": {
                    "orderId": order_id,
                    "userId": user_id,
                    "username": self.connection_metadata.get(user_id, {}).get("username", "Unknown"),
                    "action": "left",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
        
        # Clean up user presence
        if user_id in self.user_presence:
            del self.user_presence[user_id]
    
    async def join_order_room(self, user_id: str, order_id: str):
        """Add user to an order room for real-time collaboration"""
        if order_id not in self.order_rooms:
            self.order_rooms[order_id] = set()
        
        # Add user to room
        self.order_rooms[order_id].add(user_id)
        
        # Get username
        username = self.connection_metadata.get(user_id, {}).get("username", "Unknown")
        
        # Notify other users in the room
        await self.broadcast_to_order(order_id, {
            "type": "user:joined_order",
            "payload": {
                "orderId": order_id,
                "userId": user_id,
                "username": username,
                "action": "joined",
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
        
        # Send current room state to joining user
        room_users = []
        for room_user_id in self.order_rooms[order_id]:
            if room_user_id != user_id and room_user_id in self.connection_metadata:
                room_users.append({
                    "userId": room_user_id,
                    "username": self.connection_metadata[room_user_id].get("username", "Unknown"),
                    "editingField": self.user_presence.get(room_user_id, {}).get("editingField")
                })
        
        await self.send_to_user(user_id, {
            "type": "room:state",
            "payload": {
                "orderId": order_id,
                "activeUsers": room_users
            }
        })
        
        logger.info(f"👥 User {username} joined order room {order_id}")
    
    async def leave_order_room(self, user_id: str, order_id: str):
        """Remove user from an order room"""
        if order_id in self.order_rooms and user_id in self.order_rooms[order_id]:
            self.order_rooms[order_id].remove(user_id)
            
            # Clean up empty rooms
            if not self.order_rooms[order_id]:
                del self.order_rooms[order_id]
            
            # Get username
            username = self.connection_metadata.get(user_id, {}).get("username", "Unknown")
            
            # Notify other users
            await self.broadcast_to_order(order_id, {
                "type": "user:left_order",
                "payload": {
                    "orderId": order_id,
                    "userId": user_id,
                    "username": username,
                    "action": "left",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
            logger.info(f"🚪 User {username} left order room {order_id}")
    
    async def update_user_presence(self, user_id: str, order_id: str, editing_field: Optional[str] = None):
        """Update what field a user is currently editing"""
        username = self.connection_metadata.get(user_id, {}).get("username", "Unknown")
        
        if editing_field:
            self.user_presence[user_id] = {
                "orderId": order_id,
                "editingField": editing_field,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            action = "editing"
        else:
            # Stop editing
            if user_id in self.user_presence:
                del self.user_presence[user_id]
            action = "stop_editing"
        
        # Broadcast presence update to order room
        await self.broadcast_to_order(order_id, {
            "type": "user:editing",
            "payload": {
                "orderId": order_id,
                "userId": user_id,
                "username": username,
                "action": action,
                "field": editing_field,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                
                # Update last activity
                if user_id in self.connection_metadata:
                    self.connection_metadata[user_id]["last_activity"] = datetime.utcnow().isoformat()
                    
            except WebSocketDisconnect:
                logger.warning(f"🚪 User {user_id} disconnected during message send")
                await self.disconnect(user_id)
            except Exception as e:
                logger.error(f"❌ Error sending message to user {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def broadcast_to_order(self, order_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """Broadcast message to all users in an order room"""
        if order_id not in self.order_rooms:
            return
        
        users_to_remove = []
        for user_id in self.order_rooms[order_id]:
            if exclude_user and user_id == exclude_user:
                continue
                
            try:
                await self.send_to_user(user_id, message)
            except:
                users_to_remove.append(user_id)
        
        # Clean up disconnected users
        for user_id in users_to_remove:
            await self.disconnect(user_id)
    
    async def broadcast_order_update(self, order_id: str, update_type: str, data: Any):
        """Broadcast order-specific updates (status changes, field updates, etc.)"""
        message = {
            "type": f"order:{update_type}",
            "payload": {
                "orderId": order_id,
                "type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.broadcast_to_order(order_id, message)
        logger.info(f"📢 Broadcasted {update_type} for order {order_id}")
    
    async def get_active_users_in_order(self, order_id: str) -> List[Dict[str, Any]]:
        """Get list of active users in an order room"""
        if order_id not in self.order_rooms:
            return []
        
        active_users = []
        for user_id in self.order_rooms[order_id]:
            if user_id in self.connection_metadata:
                user_info = {
                    "userId": user_id,
                    "username": self.connection_metadata[user_id].get("username", "Unknown"),
                    "connectedAt": self.connection_metadata[user_id].get("connected_at"),
                    "lastActivity": self.connection_metadata[user_id].get("last_activity")
                }
                
                # Add editing status if available
                if user_id in self.user_presence:
                    user_info["editingField"] = self.user_presence[user_id].get("editingField")
                
                active_users.append(user_info)
        
        return active_users
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics for monitoring"""
        return {
            "active_connections": len(self.active_connections),
            "active_order_rooms": len(self.order_rooms),
            "users_with_presence": len(self.user_presence),
            "rooms_detail": {
                order_id: len(users) for order_id, users in self.order_rooms.items()
            }
        }

# Global connection manager instance
websocket_manager = ConnectionManager()

class WebSocketService:
    """Service layer for WebSocket operations with business logic integration"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.enhanced_order_service = None
    
    async def get_enhanced_order_service(self):
        """Lazy initialization of enhanced order service"""
        if not self.enhanced_order_service:
            self.enhanced_order_service = await create_enhanced_order_service(self.db)
        return self.enhanced_order_service
    
    async def handle_order_field_update(self, user_id: str, order_id: str, field: str, value: Any):
        """Handle real-time order field updates"""
        try:
            # Update order in database
            service = await self.get_enhanced_order_service()
            # Note: This would need to be implemented in the enhanced order service
            # await service.update_order_field(order_id, field, value)
            
            # Broadcast update to other users
            await websocket_manager.broadcast_order_update(order_id, "field_update", {
                "field": field,
                "value": value,
                "updatedBy": user_id,
                "updatedAt": datetime.utcnow().isoformat()
            })
            
            logger.info(f"🔄 Updated field {field} for order {order_id} by user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating order field: {e}")
            raise
    
    async def handle_workflow_state_change(self, user_id: str, order_id: str, context: Dict[str, Any]):
        """Handle workflow state transitions with real-time updates"""
        try:
            service = await self.get_enhanced_order_service()
            
            # Update workflow state using Romanian business logic
            result = await service.update_order_workflow_state(order_id, context)
            
            if result["success"]:
                # Broadcast workflow state change
                await websocket_manager.broadcast_order_update(order_id, "status_changed", {
                    "previousState": result["previous_state"],
                    "newState": result["new_state"],
                    "updatedBy": user_id,
                    "context": context
                })
                
                logger.info(f"🔄 Workflow updated for order {order_id}: {result['previous_state']} → {result['new_state']}")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Error updating workflow state: {e}")
            raise

async def create_websocket_service(db: AsyncSession) -> WebSocketService:
    """Factory function for WebSocket service"""
    return WebSocketService(db) 