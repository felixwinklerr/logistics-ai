"""
AI processing background tasks for document parsing and analysis.

This module contains Celery tasks for AI-powered document processing,
including PDF parsing, confidence scoring, and provider management.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pathlib import Path

from celery import Task
from celery.exceptions import Retry

from app.tasks.celery_app import celery_app
from app.services.ai_service import AIDocumentParser
from app.services.confidence_scorer import ConfidenceScorer
from app.services.ai_provider_manager import AIProviderManager
from app.services.pdf_processor import PDFProcessor
from app.core.database import AsyncSessionLocal
from app.repositories.order_repository import OrderRepository
from app.repositories.document_repository import DocumentRepository
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIProcessingTask(Task):
    """Base task class for AI processing with error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 300  # 5 minutes max delay
    retry_jitter = True


@celery_app.task(bind=True, base=AIProcessingTask)
def process_document_ai(self, document_path: str, order_id: str = None) -> Dict[str, Any]:
    """
    Process a document using AI extraction.
    
    Args:
        document_path: Path to the PDF document
        order_id: Optional order ID if updating existing order
        
    Returns:
        Dict containing extraction results and metadata
    """
    try:
        logger.info(f"Starting AI processing for document: {document_path}")
        
        # Run async processing in thread
        result = asyncio.run(_process_document_async(document_path, order_id))
        
        logger.info(f"AI processing completed for document: {document_path}")
        return result
        
    except Exception as exc:
        logger.error(f"AI processing failed for {document_path}: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = min(60 * (2 ** self.request.retries), 300)
            logger.info(f"Retrying in {retry_delay} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=retry_delay, exc=exc)
        
        # Max retries exceeded - mark for manual processing
        return {
            'success': False,
            'error': str(exc),
            'manual_review_required': True,
            'retry_count': self.request.retries,
            'document_path': document_path
        }


async def _process_document_async(document_path: str, order_id: str = None) -> Dict[str, Any]:
    """Async helper for document processing."""
    
    async with AsyncSessionLocal() as session:
        try:
            # Initialize services
            ai_parser = AIDocumentParser()
            confidence_scorer = ConfidenceScorer()
            pdf_processor = PDFProcessor()
            
            # Validate document exists
            doc_path = Path(document_path)
            if not doc_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            # Pre-process PDF
            logger.info("Pre-processing PDF document")
            processing_result = await pdf_processor.process_pdf(str(doc_path))
            
            if not processing_result.success:
                raise ValueError(f"PDF processing failed: {processing_result.error}")
            
            # Extract data using AI
            logger.info("Extracting data using AI service")
            extraction_result = await ai_parser.parse_document(str(doc_path))
            
            # Score confidence
            logger.info("Scoring extraction confidence")
            confidence_result = await confidence_scorer.score_extraction(
                extracted_data=extraction_result.extracted_data,
                ai_confidence_scores=extraction_result.confidence_scores,
                provider_metadata=extraction_result.metadata
            )
            
            # Prepare result
            result = {
                'success': True,
                'extracted_data': extraction_result.extracted_data,
                'confidence_scores': {
                    field: conf.confidence 
                    for field, conf in confidence_result.field_confidences.items()
                },
                'overall_confidence': confidence_result.overall_confidence,
                'critical_confidence': confidence_result.critical_fields_confidence,
                'manual_review_required': confidence_result.manual_review_required,
                'review_reasons': confidence_result.review_reasons,
                'processing_metadata': {
                    'ai_provider': extraction_result.provider_used,
                    'processing_time': extraction_result.processing_time,
                    'pdf_pages': processing_result.metadata.get('page_count', 0),
                    'text_length': len(processing_result.text),
                    'image_count': len(processing_result.images),
                    'processed_at': datetime.utcnow().isoformat()
                },
                'document_path': document_path
            }
            
            # Update order if ID provided
            if order_id:
                await _update_order_with_results(session, order_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in async document processing: {e}")
            raise


async def _update_order_with_results(session, order_id: str, results: Dict[str, Any]):
    """Update order with AI processing results."""
    try:
        order_repo = OrderRepository(session)
        
        # Get existing order
        order = await order_repo.get_by_id(UUID(order_id))
        if not order:
            logger.warning(f"Order {order_id} not found for result update")
            return
        
        # Update order with extracted data
        extracted_data = results['extracted_data']
        
        update_data = {}
        
        # Map extracted fields to order fields
        field_mapping = {
            'client_company_name': 'client_company_name',
            'client_vat_number': 'client_vat_number',
            'client_contact_email': 'client_contact_email',
            'client_offered_price': 'client_offered_price',
            'pickup_address': 'pickup_address',
            'pickup_postcode': 'pickup_postcode',
            'pickup_city': 'pickup_city',
            'delivery_address': 'delivery_address',
            'delivery_postcode': 'delivery_postcode',
            'delivery_city': 'delivery_city',
            'cargo_ldm': 'cargo_ldm',
            'cargo_weight_kg': 'cargo_weight_kg',
            'cargo_pallets': 'cargo_pallets',
            'special_requirements': 'special_requirements'
        }
        
        for extracted_field, order_field in field_mapping.items():
            if extracted_field in extracted_data:
                update_data[order_field] = extracted_data[extracted_field]
        
        # Add confidence metadata
        update_data.update({
            'extraction_confidence': results['overall_confidence'],
            'manual_review_required': results['manual_review_required']
        })
        
        # Update order
        await order_repo.update(UUID(order_id), update_data)
        logger.info(f"Updated order {order_id} with AI extraction results")
        
    except Exception as e:
        logger.error(f"Error updating order {order_id} with results: {e}")


@celery_app.task(bind=True)
def analyze_provider_performance(self) -> Dict[str, Any]:
    """
    Analyze AI provider performance and update selection algorithms.
    
    This task runs periodically to evaluate provider performance and
    optimize future provider selection.
    """
    try:
        logger.info("Starting AI provider performance analysis")
        
        result = asyncio.run(_analyze_provider_performance_async())
        
        logger.info("AI provider performance analysis completed")
        return result
        
    except Exception as exc:
        logger.error(f"Provider performance analysis failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'analyzed_at': datetime.utcnow().isoformat()
        }


async def _analyze_provider_performance_async() -> Dict[str, Any]:
    """Async helper for provider performance analysis."""
    
    async with AsyncSessionLocal() as session:
        try:
            provider_manager = AIProviderManager()
            
            # Analyze performance for each provider
            performance_data = {}
            
            for provider_name in ['openai', 'claude', 'azure']:
                try:
                    metrics = await provider_manager.get_provider_metrics(provider_name)
                    performance_data[provider_name] = {
                        'success_rate': metrics.get('success_rate', 0.0),
                        'avg_processing_time': metrics.get('avg_processing_time', 0.0),
                        'avg_confidence': metrics.get('avg_confidence', 0.0),
                        'total_requests': metrics.get('total_requests', 0),
                        'error_rate': metrics.get('error_rate', 0.0),
                        'cost_per_request': metrics.get('cost_per_request', 0.0)
                    }
                except Exception as e:
                    logger.warning(f"Could not analyze provider {provider_name}: {e}")
                    performance_data[provider_name] = {'error': str(e)}
            
            # Update provider rankings based on performance
            await provider_manager.update_provider_rankings(performance_data)
            
            return {
                'success': True,
                'performance_data': performance_data,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in provider performance analysis: {e}")
            raise


@celery_app.task(bind=True)
def health_check_ai_providers(self) -> Dict[str, Any]:
    """
    Check health status of all AI providers.
    
    Returns:
        Dict with health status of each provider
    """
    try:
        logger.info("Starting AI provider health check")
        
        result = asyncio.run(_health_check_providers_async())
        
        logger.info("AI provider health check completed")
        return result
        
    except Exception as exc:
        logger.error(f"AI provider health check failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'checked_at': datetime.utcnow().isoformat()
        }


async def _health_check_providers_async() -> Dict[str, Any]:
    """Async helper for provider health checks."""
    try:
        provider_manager = AIProviderManager()
        
        health_status = {}
        
        # Check each provider
        for provider_name in ['openai', 'claude', 'azure']:
            try:
                is_healthy = await provider_manager.check_provider_health(provider_name)
                health_status[provider_name] = {
                    'healthy': is_healthy,
                    'checked_at': datetime.utcnow().isoformat()
                }
            except Exception as e:
                health_status[provider_name] = {
                    'healthy': False,
                    'error': str(e),
                    'checked_at': datetime.utcnow().isoformat()
                }
        
        return {
            'success': True,
            'provider_health': health_status,
            'overall_healthy': all(
                status.get('healthy', False) 
                for status in health_status.values()
            )
        }
        
    except Exception as e:
        logger.error(f"Error in provider health check: {e}")
        raise


@celery_app.task
def batch_process_documents(document_paths: list) -> Dict[str, Any]:
    """
    Process multiple documents in batch.
    
    Args:
        document_paths: List of paths to process
        
    Returns:
        Dict with batch processing results
    """
    try:
        logger.info(f"Starting batch processing of {len(document_paths)} documents")
        
        results = []
        failed_documents = []
        
        for doc_path in document_paths:
            try:
                # Queue individual processing task
                task_result = process_document_ai.delay(doc_path)
                results.append({
                    'document_path': doc_path,
                    'task_id': task_result.id,
                    'status': 'queued'
                })
            except Exception as e:
                failed_documents.append({
                    'document_path': doc_path,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'total_documents': len(document_paths),
            'queued_successfully': len(results),
            'failed_to_queue': len(failed_documents),
            'results': results,
            'failed_documents': failed_documents,
            'batch_started_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Batch processing failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'total_documents': len(document_paths) if document_paths else 0
        }


@celery_app.task(bind=True)
def cleanup_failed_ai_tasks(self, days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up failed AI processing tasks older than specified days.
    
    Args:
        days_old: Number of days old for cleanup threshold
        
    Returns:
        Dict with cleanup results
    """
    try:
        logger.info(f"Starting cleanup of AI tasks older than {days_old} days")
        
        # This would interact with Celery's result backend to clean up old tasks
        # For now, return a placeholder result
        
        return {
            'success': True,
            'cleaned_up_tasks': 0,  # Would be actual count
            'cleanup_threshold_days': days_old,
            'cleaned_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"AI task cleanup failed: {exc}")
        return {
            'success': False,
            'error': str(exc)
        }


# Periodic tasks configuration
@celery_app.on_after_configure.connect
def setup_periodic_ai_tasks(sender, **kwargs):
    """Setup periodic AI-related tasks."""
    
    # Provider performance analysis - daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        analyze_provider_performance.s(),
        name='daily-ai-provider-analysis'
    )
    
    # Provider health checks - every 5 minutes
    sender.add_periodic_task(
        300.0,  # 5 minutes
        health_check_ai_providers.s(),
        name='ai-provider-health-checks'
    )
    
    # Cleanup old tasks - weekly on Sunday at 3 AM
    sender.add_periodic_task(
        crontab(hour=3, minute=0, day_of_week=0),
        cleanup_failed_ai_tasks.s(),
        name='weekly-ai-task-cleanup'
    ) 