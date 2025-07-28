"""
Email Processing Service for Romanian Freight Forwarder System

Implements async IMAP monitoring with Celery background tasks following
the creative phase architectural design.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.orders import EmailRecord, EmailStatus


class EmailProvider(Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    GENERIC_IMAP = "generic"


@dataclass
class EmailAccount:
    id: str
    email: str
    provider: EmailProvider
    imap_host: str
    imap_port: int
    oauth_config: Dict[str, Any]
    is_active: bool = True


@dataclass 
class Email:
    id: str
    subject: str
    sender: str
    recipient: str
    body: str
    attachments: List[Dict[str, Any]]
    received_at: datetime
    raw_headers: Dict[str, str]


class EmailMonitoringService:
    """Core email monitoring service with async IMAP and background processing"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.settings = get_settings()
        self.accounts = {}
        self.monitoring_tasks = {}
        self.is_running = False
        
    async def initialize(self):
        """Initialize email monitoring service"""
        logger.info("Initializing Email Monitoring Service")
        
        # Load email accounts configuration
        await self.load_email_accounts()
        
        # Initialize OAuth2 token management
        from app.services.email_auth_service import EmailAuthService
        self.auth_service = EmailAuthService(self.redis)
        
        # Initialize email classifier
        from app.services.email_classifier import TransportOrderClassifier
        self.classifier = TransportOrderClassifier()
        
        logger.info(f"Email monitoring service initialized with {len(self.accounts)} accounts")
    
    async def load_email_accounts(self):
        """Load email accounts from configuration"""
        # TODO: Load from database in production
        # For now, load from environment configuration
        
        if self.settings.email_host and self.settings.email_username:
            account = EmailAccount(
                id="primary",
                email=self.settings.email_username,
                provider=EmailProvider.GMAIL if "gmail" in self.settings.email_host else EmailProvider.GENERIC_IMAP,
                imap_host=self.settings.email_host,
                imap_port=self.settings.email_port or 993,
                oauth_config={
                    "client_id": getattr(self.settings, "gmail_client_id", ""),
                    "client_secret": getattr(self.settings, "gmail_client_secret", ""),
                    "refresh_token": getattr(self.settings, "gmail_refresh_token", "")
                }
            )
            self.accounts["primary"] = account
            logger.info(f"Loaded email account: {account.email}")
    
    async def start_monitoring(self):
        """Start monitoring all configured email accounts"""
        if self.is_running:
            logger.warning("Email monitoring is already running")
            return
        
        self.is_running = True
        logger.info("Starting email monitoring for all accounts")
        
        # Create monitoring tasks for each account
        for account_id, account in self.accounts.items():
            if account.is_active:
                task = asyncio.create_task(
                    self.monitor_account(account),
                    name=f"email_monitor_{account_id}"
                )
                self.monitoring_tasks[account_id] = task
                logger.info(f"Started monitoring task for account: {account.email}")
        
        logger.info(f"Email monitoring started for {len(self.monitoring_tasks)} accounts")
    
    async def stop_monitoring(self):
        """Stop monitoring all email accounts"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping email monitoring")
        
        # Cancel all monitoring tasks
        for account_id, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Stopped monitoring for account: {account_id}")
        
        self.monitoring_tasks.clear()
        logger.info("Email monitoring stopped")
    
    async def monitor_account(self, account: EmailAccount):
        """Monitor a single email account for new transport orders"""
        logger.info(f"Starting monitoring for account: {account.email}")
        
        while self.is_running:
            try:
                # Get authenticated email client
                client = await self.auth_service.get_authenticated_client(account)
                
                # Fetch new emails since last check
                since_timestamp = await self.get_last_check_timestamp(account.id)
                emails = await client.fetch_emails_since(since_timestamp)
                
                logger.debug(f"Found {len(emails)} new emails for {account.email}")
                
                # Process each email
                for email in emails:
                    try:
                        if await self.classifier.is_transport_order_email(email):
                            logger.info(f"Transport order detected: {email.subject} from {email.sender}")
                            await self.queue_email_processing(email, account)
                        else:
                            logger.debug(f"Skipping non-transport email: {email.subject}")
                    except Exception as e:
                        logger.error(f"Error processing email {email.id}: {e}")
                
                # Update last check timestamp
                await self.update_last_check_timestamp(account.id)
                
                # Wait before next poll (30 seconds as per requirements)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Email monitoring error for {account.email}: {e}")
                # Longer backoff on error (60 seconds)
                await asyncio.sleep(60)
    
    async def queue_email_processing(self, email: Email, account: EmailAccount):
        """Queue email for background AI processing"""
        try:
            # Store email metadata in database
            email_record = await self.store_email_metadata(email, account)
            
            # Download and store PDF attachments
            pdf_paths = await self.store_pdf_attachments(email)
            
            if not pdf_paths:
                logger.warning(f"No PDF attachments found in email: {email.subject}")
                return
            
            # Import here to avoid circular imports
            from app.tasks.email_tasks import process_transport_order_email
            
            # Queue Celery task for AI processing
            task = process_transport_order_email.delay(
                email_record_id=str(email_record.id),
                pdf_paths=pdf_paths,
                account_id=account.id
            )
            
            logger.info(f"Queued email processing: {email.subject} -> task {task.id}")
            
            # Store task ID for tracking
            await email_record.add_processing_task(task.id)
            
        except Exception as e:
            logger.error(f"Failed to queue email processing: {e}")
            raise
    
    async def store_email_metadata(self, email: Email, account: EmailAccount) -> EmailRecord:
        """Store email metadata in database"""
        async with get_async_session() as session:
            email_record = EmailRecord(
                external_email_id=email.id,
                account_id=account.id,
                sender=email.sender,
                recipient=email.recipient,
                subject=email.subject,
                body_preview=email.body[:500],  # Store preview only
                attachment_count=len(email.attachments),
                received_at=email.received_at,
                status=EmailStatus.RECEIVED,
                metadata={
                    "headers": email.raw_headers,
                    "provider": account.provider.value
                }
            )
            
            session.add(email_record)
            await session.commit()
            await session.refresh(email_record)
            
            logger.debug(f"Stored email metadata: {email_record.id}")
            return email_record
    
    async def store_pdf_attachments(self, email: Email) -> List[str]:
        """Download and store PDF attachments"""
        pdf_paths = []
        
        for attachment in email.attachments:
            if attachment.get("filename", "").lower().endswith('.pdf'):
                try:
                    # Generate unique filename
                    timestamp = int(time.time())
                    filename = f"email_{email.id}_{timestamp}_{attachment['filename']}"
                    
                    # Store in MinIO/S3
                    from app.services.file_storage_service import FileStorageService
                    storage_service = FileStorageService()
                    
                    file_path = await storage_service.store_file(
                        file_content=attachment['content'],
                        filename=filename,
                        bucket="email-attachments"
                    )
                    
                    pdf_paths.append(file_path)
                    logger.debug(f"Stored PDF attachment: {filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to store PDF attachment {attachment['filename']}: {e}")
        
        return pdf_paths
    
    async def get_last_check_timestamp(self, account_id: str) -> datetime:
        """Get the last check timestamp for an account"""
        cache_key = f"email_last_check:{account_id}"
        cached_timestamp = await self.redis.get(cache_key)
        
        if cached_timestamp:
            return datetime.fromisoformat(cached_timestamp.decode())
        else:
            # First time - check emails from 1 hour ago
            return datetime.now() - timedelta(hours=1)
    
    async def update_last_check_timestamp(self, account_id: str):
        """Update the last check timestamp for an account"""
        cache_key = f"email_last_check:{account_id}"
        timestamp = datetime.now().isoformat()
        
        # Cache for 24 hours
        await self.redis.setex(cache_key, 86400, timestamp)
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status for all accounts"""
        status = {
            "is_running": self.is_running,
            "accounts": {}
        }
        
        for account_id, account in self.accounts.items():
            task = self.monitoring_tasks.get(account_id)
            last_check = await self.get_last_check_timestamp(account_id)
            
            status["accounts"][account_id] = {
                "email": account.email,
                "provider": account.provider.value,
                "is_active": account.is_active,
                "task_running": task is not None and not task.done(),
                "last_check": last_check.isoformat(),
                "task_status": "running" if task and not task.done() else "stopped"
            }
        
        return status


# Global instance (will be initialized in main.py)
email_monitoring_service: Optional[EmailMonitoringService] = None


async def get_email_monitoring_service() -> EmailMonitoringService:
    """Get the global email monitoring service instance"""
    global email_monitoring_service
    
    if email_monitoring_service is None:
        # Initialize Redis connection
        redis_url = get_settings().redis_url
        redis_client = await redis.from_url(redis_url)
        
        # Create and initialize service
        email_monitoring_service = EmailMonitoringService(redis_client)
        await email_monitoring_service.initialize()
    
    return email_monitoring_service 