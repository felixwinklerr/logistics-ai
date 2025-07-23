"""
Email processing Celery tasks

Background tasks for processing transport order emails and managing
email monitoring health.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from celery import current_task
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.core.database import get_async_session
from app.models.orders import EmailRecord, EmailStatus
from app.services.email_service import get_email_monitoring_service


@celery_app.task(bind=True, max_retries=3)
def process_transport_order_email(self, email_record_id: str, pdf_paths: List[str], account_id: str):
    """
    Background task to process transport order email with AI
    
    Args:
        email_record_id: Database ID of the email record
        pdf_paths: List of PDF file paths to process
        account_id: Email account ID
    """
    task_id = self.request.id
    logger.info(f"Starting email processing task {task_id} for email {email_record_id}")
    
    try:
        # Run async processing in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _process_email_async(email_record_id, pdf_paths, account_id, task_id)
            )
            logger.info(f"Email processing task {task_id} completed successfully")
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Email processing task {task_id} failed: {exc}")
        
        # Update email record with error
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _update_email_record_error(email_record_id, str(exc))
            )
        finally:
            loop.close()
        
        # Retry with exponential backoff
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(countdown=countdown, exc=exc)


async def _process_email_async(email_record_id: str, pdf_paths: List[str], account_id: str, task_id: str) -> Dict[str, Any]:
    """Async helper for email processing"""
    
    async with get_async_session() as session:
        # Load email record
        email_record = await session.get(EmailRecord, email_record_id)
        if not email_record:
            raise ValueError(f"Email record {email_record_id} not found")
        
        # Update status to processing
        email_record.update_status(EmailStatus.PROCESSING)
        await session.commit()
        
        try:
            # Process each PDF attachment with AI
            processing_results = []
            
            for pdf_path in pdf_paths:
                logger.info(f"Processing PDF: {pdf_path}")
                
                # Import AI tasks here to avoid circular imports
                from app.tasks.ai_tasks import parse_transport_document
                
                # Queue AI processing task
                ai_task = parse_transport_document.delay(
                    pdf_path=pdf_path,
                    email_record_id=email_record_id,
                    source_account_id=account_id,
                    parent_task_id=task_id
                )
                
                processing_results.append({
                    "pdf_path": pdf_path,
                    "ai_task_id": ai_task.id,
                    "status": "queued"
                })
                
                # Add AI task to email record tracking
                await email_record.add_processing_task(ai_task.id)
            
            # Update email record with processing results
            if not email_record.metadata:
                email_record.metadata = {}
            
            email_record.metadata.update({
                "processing_results": processing_results,
                "processed_at": datetime.utcnow().isoformat(),
                "task_id": task_id
            })
            
            await session.commit()
            
            return {
                "status": "ai_processing_queued",
                "pdf_count": len(pdf_paths),
                "ai_tasks": [r["ai_task_id"] for r in processing_results]
            }
            
        except Exception as e:
            # Update status to failed
            email_record.update_status(EmailStatus.FAILED, {"error": str(e)})
            await session.commit()
            raise


async def _update_email_record_error(email_record_id: str, error_message: str):
    """Update email record with error status"""
    async with get_async_session() as session:
        email_record = await session.get(EmailRecord, email_record_id)
        if email_record:
            email_record.update_status(EmailStatus.FAILED, {"error": error_message})
            await session.commit()


@celery_app.task
def health_check_email_monitoring():
    """Periodic health check for email monitoring service"""
    logger.info("Running email monitoring health check")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_health_check_async())
            logger.info("Email monitoring health check completed")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Email monitoring health check failed: {e}")
        return {"status": "failed", "error": str(e)}


async def _health_check_async() -> Dict[str, Any]:
    """Async health check implementation"""
    try:
        email_service = await get_email_monitoring_service()
        status = await email_service.get_monitoring_status()
        
        return {
            "status": "healthy",
            "monitoring_status": status,
            "checked_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }


@celery_app.task
def cleanup_old_email_records():
    """Clean up old email records to prevent database bloat"""
    logger.info("Running email records cleanup")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_cleanup_email_records_async())
            logger.info(f"Email records cleanup completed: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Email records cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


async def _cleanup_email_records_async() -> Dict[str, Any]:
    """Async cleanup implementation"""
    cutoff_date = datetime.utcnow() - timedelta(days=30)  # Keep records for 30 days
    
    async with get_async_session() as session:
        # Count old records
        from sqlalchemy import select, func, delete
        
        count_query = select(func.count(EmailRecord.id)).where(
            EmailRecord.created_at < cutoff_date,
            EmailRecord.status.in_([EmailStatus.PROCESSED, EmailStatus.FAILED, EmailStatus.IGNORED])
        )
        
        count_result = await session.execute(count_query)
        old_count = count_result.scalar()
        
        if old_count > 0:
            # Delete old records (keep PROCESSING status records)
            delete_query = delete(EmailRecord).where(
                EmailRecord.created_at < cutoff_date,
                EmailRecord.status.in_([EmailStatus.PROCESSED, EmailStatus.FAILED, EmailStatus.IGNORED])
            )
            
            await session.execute(delete_query)
            await session.commit()
            
            logger.info(f"Cleaned up {old_count} old email records")
        
        return {
            "status": "completed",
            "records_deleted": old_count,
            "cutoff_date": cutoff_date.isoformat()
        }


@celery_app.task(bind=True)
def start_email_monitoring(self):
    """Start email monitoring service"""
    logger.info("Starting email monitoring service via Celery task")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(_start_monitoring_async())
            return {"status": "started", "task_id": self.request.id}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to start email monitoring: {e}")
        return {"status": "failed", "error": str(e)}


async def _start_monitoring_async():
    """Async helper to start email monitoring"""
    email_service = await get_email_monitoring_service()
    await email_service.start_monitoring()


@celery_app.task(bind=True)
def stop_email_monitoring(self):
    """Stop email monitoring service"""
    logger.info("Stopping email monitoring service via Celery task")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(_stop_monitoring_async())
            return {"status": "stopped", "task_id": self.request.id}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to stop email monitoring: {e}")
        return {"status": "failed", "error": str(e)}


async def _stop_monitoring_async():
    """Async helper to stop email monitoring"""
    email_service = await get_email_monitoring_service()
    await email_service.stop_monitoring() 