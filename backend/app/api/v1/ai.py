"""
AI Document Processing API endpoints.

This module provides REST API endpoints for AI-powered document processing,
including document parsing, confidence scoring, and provider management.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.users import User
from app.services.ai_service import AIDocumentParser
from app.services.confidence_scorer import ConfidenceScorer
from app.services.ai_provider_manager import AIProviderManager
from app.services.pdf_processor import PDFProcessor
from app.tasks.ai_tasks import process_document_ai, batch_process_documents
from app.schemas.ai import (
    DocumentParsingRequest,
    DocumentParsingResponse,
    ConfidenceScoreResponse,
    ProviderMetricsResponse,
    BatchProcessingRequest,
    BatchProcessingResponse,
    ProviderHealthResponse
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Document Processing"])
settings = get_settings()


@router.post("/parse-document", response_model=DocumentParsingResponse)
async def parse_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    order_id: Optional[str] = None,
    async_processing: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DocumentParsingResponse:
    """
    Parse a PDF document using AI extraction.
    
    - **file**: PDF document to parse
    - **order_id**: Optional order ID to update with results
    - **async_processing**: Whether to process asynchronously (recommended)
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Save uploaded file temporarily
        upload_dir = Path(settings.upload_directory)
        upload_dir.mkdir(exist_ok=True)
        
        temp_file_path = upload_dir / f"temp_{file.filename}"
        
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        if async_processing:
            # Queue background processing
            task = process_document_ai.delay(str(temp_file_path), order_id)
            
            return DocumentParsingResponse(
                task_id=task.id,
                status="processing",
                message="Document queued for AI processing",
                async_processing=True
            )
        else:
            # Process synchronously (not recommended for production)
            ai_parser = AIDocumentParser()
            confidence_scorer = ConfidenceScorer()
            
            # Parse document
            extraction_result = await ai_parser.parse_document(str(temp_file_path))
            
            # Score confidence
            confidence_result = await confidence_scorer.score_extraction(
                extracted_data=extraction_result.extracted_data,
                ai_confidence_scores=extraction_result.confidence_scores
            )
            
            # Clean up temp file
            temp_file_path.unlink(missing_ok=True)
            
            return DocumentParsingResponse(
                task_id=None,
                status="completed",
                extracted_data=extraction_result.extracted_data,
                confidence_scores={
                    field: conf.confidence 
                    for field, conf in confidence_result.field_confidences.items()
                },
                overall_confidence=confidence_result.overall_confidence,
                manual_review_required=confidence_result.manual_review_required,
                provider_used=extraction_result.provider_used,
                processing_time=extraction_result.processing_time,
                async_processing=False
            )
            
    except Exception as e:
        logger.error(f"Document parsing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document parsing failed: {str(e)}"
        )


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of an AI processing task.
    
    - **task_id**: Celery task ID returned from async processing
    """
    try:
        from app.tasks.celery_app import celery_app
        
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'status': 'pending',
                'message': 'Task is waiting to be processed'
            }
        elif task_result.state == 'PROCESSING':
            response = {
                'task_id': task_id,
                'status': 'processing',
                'message': 'Task is currently being processed'
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'task_id': task_id,
                'status': 'completed',
                'result': task_result.result
            }
        elif task_result.state == 'FAILURE':
            response = {
                'task_id': task_id,
                'status': 'failed',
                'error': str(task_result.info)
            }
        else:
            response = {
                'task_id': task_id,
                'status': task_result.state.lower(),
                'info': str(task_result.info)
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_documents(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BatchProcessingResponse:
    """
    Process multiple documents in batch.
    
    - **document_paths**: List of document file paths to process
    """
    try:
        if not request.document_paths:
            raise HTTPException(
                status_code=400,
                detail="No document paths provided"
            )
        
        # Validate all paths exist
        missing_files = []
        for doc_path in request.document_paths:
            if not Path(doc_path).exists():
                missing_files.append(doc_path)
        
        if missing_files:
            raise HTTPException(
                status_code=400,
                detail=f"Missing files: {missing_files}"
            )
        
        # Queue batch processing
        task = batch_process_documents.delay(request.document_paths)
        
        return BatchProcessingResponse(
            batch_task_id=task.id,
            total_documents=len(request.document_paths),
            status="queued",
            message=f"Batch processing queued for {len(request.document_paths)} documents"
        )
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/confidence-analysis/{order_id}", response_model=ConfidenceScoreResponse)
async def get_confidence_analysis(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ConfidenceScoreResponse:
    """
    Get detailed confidence analysis for an order's AI extraction.
    
    - **order_id**: UUID of the order to analyze
    """
    try:
        # This would typically load order data and re-run confidence scoring
        # For now, return a placeholder response
        
        confidence_scorer = ConfidenceScorer()
        
        # In a real implementation, you'd load the order's extracted data
        # For now, return a sample response
        return ConfidenceScoreResponse(
            order_id=order_id,
            overall_confidence=0.85,
            critical_fields_confidence=0.90,
            manual_review_required=False,
            confidence_breakdown={
                "client_company_name": 0.95,
                "client_vat_number": 0.88,
                "client_offered_price": 0.92,
                "pickup_address": 0.82,
                "delivery_address": 0.79
            },
            review_reasons=[],
            analysis_timestamp="2024-01-17T10:30:00Z"
        )
        
    except Exception as e:
        logger.error(f"Confidence analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Confidence analysis failed: {str(e)}"
        )


@router.get("/providers/metrics", response_model=List[ProviderMetricsResponse])
async def get_provider_metrics(
    current_user: User = Depends(get_current_user)
) -> List[ProviderMetricsResponse]:
    """
    Get performance metrics for all AI providers.
    """
    try:
        provider_manager = AIProviderManager()
        
        metrics_list = []
        
        for provider_name in ['openai', 'claude', 'azure']:
            try:
                metrics = await provider_manager.get_provider_metrics(provider_name)
                
                metrics_list.append(ProviderMetricsResponse(
                    provider_name=provider_name,
                    success_rate=metrics.get('success_rate', 0.0),
                    avg_processing_time=metrics.get('avg_processing_time', 0.0),
                    avg_confidence=metrics.get('avg_confidence', 0.0),
                    total_requests=metrics.get('total_requests', 0),
                    error_rate=metrics.get('error_rate', 0.0),
                    cost_per_request=metrics.get('cost_per_request', 0.0),
                    last_updated="2024-01-17T10:30:00Z"
                ))
            except Exception as e:
                logger.warning(f"Could not get metrics for provider {provider_name}: {e}")
                metrics_list.append(ProviderMetricsResponse(
                    provider_name=provider_name,
                    success_rate=0.0,
                    avg_processing_time=0.0,
                    avg_confidence=0.0,
                    total_requests=0,
                    error_rate=1.0,
                    cost_per_request=0.0,
                    last_updated="2024-01-17T10:30:00Z",
                    error=str(e)
                ))
        
        return metrics_list
        
    except Exception as e:
        logger.error(f"Failed to get provider metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider metrics: {str(e)}"
        )


@router.get("/providers/health", response_model=ProviderHealthResponse)
async def check_provider_health(
    current_user: User = Depends(get_current_user)
) -> ProviderHealthResponse:
    """
    Check health status of all AI providers.
    """
    try:
        provider_manager = AIProviderManager()
        
        health_status = {}
        
        for provider_name in ['openai', 'claude', 'azure']:
            try:
                is_healthy = await provider_manager.check_provider_health(provider_name)
                health_status[provider_name] = {
                    'healthy': is_healthy,
                    'checked_at': "2024-01-17T10:30:00Z"
                }
            except Exception as e:
                health_status[provider_name] = {
                    'healthy': False,
                    'error': str(e),
                    'checked_at': "2024-01-17T10:30:00Z"
                }
        
        overall_healthy = all(
            status.get('healthy', False) 
            for status in health_status.values()
        )
        
        return ProviderHealthResponse(
            overall_healthy=overall_healthy,
            provider_health=health_status,
            checked_at="2024-01-17T10:30:00Z"
        )
        
    except Exception as e:
        logger.error(f"Provider health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Provider health check failed: {str(e)}"
        )


@router.post("/providers/{provider_name}/test")
async def test_provider(
    provider_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test a specific AI provider with a sample document.
    
    - **provider_name**: Name of the provider to test (openai, claude, azure)
    """
    try:
        if provider_name not in ['openai', 'claude', 'azure']:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider_name}"
            )
        
        provider_manager = AIProviderManager()
        
        # Perform a test request
        test_result = await provider_manager.test_provider(provider_name)
        
        return {
            'provider_name': provider_name,
            'test_successful': test_result.get('success', False),
            'response_time': test_result.get('response_time', 0.0),
            'error': test_result.get('error'),
            'tested_at': "2024-01-17T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Provider test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Provider test failed: {str(e)}"
        )


@router.get("/analytics/extraction-quality")
async def get_extraction_quality_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get analytics on AI extraction quality over time.
    
    - **days**: Number of days to analyze (default: 30)
    """
    try:
        # This would query the database for extraction quality metrics
        # For now, return sample data
        
        return {
            'period_days': days,
            'total_extractions': 1250,
            'avg_overall_confidence': 0.87,
            'avg_critical_confidence': 0.91,
            'manual_review_rate': 0.15,
            'top_confidence_fields': [
                {'field': 'client_vat_number', 'avg_confidence': 0.94},
                {'field': 'client_offered_price', 'avg_confidence': 0.92},
                {'field': 'client_company_name', 'avg_confidence': 0.89}
            ],
            'low_confidence_fields': [
                {'field': 'special_requirements', 'avg_confidence': 0.68},
                {'field': 'pickup_date_range', 'avg_confidence': 0.72}
            ],
            'provider_performance': {
                'openai': {'usage_percentage': 70, 'avg_confidence': 0.88},
                'claude': {'usage_percentage': 25, 'avg_confidence': 0.85},
                'azure': {'usage_percentage': 5, 'avg_confidence': 0.82}
            },
            'analyzed_at': "2024-01-17T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Extraction quality analytics failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analytics failed: {str(e)}"
        ) 