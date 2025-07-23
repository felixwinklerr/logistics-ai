"""
Pydantic schemas for AI document processing API.

This module defines request and response schemas for AI-powered
document processing endpoints.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator


@dataclass
class ExtractionResult:
    """AI extraction result with metadata"""
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    provider_used: str
    processing_time: float
    validation_errors: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all fields"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)


class DocumentParsingRequest(BaseModel):
    """Request schema for document parsing."""
    
    order_id: Optional[str] = Field(None, description="Optional order ID to update")
    async_processing: bool = Field(True, description="Whether to process asynchronously")
    preferred_provider: Optional[str] = Field(None, description="Preferred AI provider")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentParsingResponse(BaseModel):
    """Response schema for document parsing."""
    
    task_id: Optional[str] = Field(None, description="Celery task ID for async processing")
    status: str = Field(..., description="Processing status")
    message: Optional[str] = Field(None, description="Status message")
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Extracted document data")
    confidence_scores: Optional[Dict[str, float]] = Field(None, description="Field confidence scores")
    overall_confidence: Optional[float] = Field(None, description="Overall extraction confidence")
    critical_fields_confidence: Optional[float] = Field(None, description="Critical fields confidence")
    manual_review_required: Optional[bool] = Field(None, description="Whether manual review is needed")
    review_reasons: Optional[List[str]] = Field(None, description="Reasons for manual review")
    provider_used: Optional[str] = Field(None, description="AI provider used")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    async_processing: bool = Field(True, description="Whether processed asynchronously")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConfidenceScoreResponse(BaseModel):
    """Response schema for confidence analysis."""
    
    order_id: UUID = Field(..., description="Order UUID")
    overall_confidence: float = Field(..., description="Overall confidence score")
    critical_fields_confidence: float = Field(..., description="Critical fields confidence")
    manual_review_required: bool = Field(..., description="Whether manual review is required")
    confidence_breakdown: Dict[str, float] = Field(..., description="Per-field confidence scores")
    review_reasons: List[str] = Field([], description="Reasons for manual review")
    analysis_timestamp: str = Field(..., description="Timestamp of analysis")
    
    @validator('overall_confidence', 'critical_fields_confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v
    
    @validator('confidence_breakdown')
    def validate_breakdown(cls, v):
        for field, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f'Confidence score for {field} must be between 0.0 and 1.0')
        return v


class BatchProcessingRequest(BaseModel):
    """Request schema for batch document processing."""
    
    document_paths: List[str] = Field(..., description="List of document paths to process")
    preferred_provider: Optional[str] = Field(None, description="Preferred AI provider")
    
    @validator('document_paths')
    def validate_paths(cls, v):
        if not v:
            raise ValueError('At least one document path must be provided')
        return v


class BatchProcessingResponse(BaseModel):
    """Response schema for batch processing."""
    
    batch_task_id: str = Field(..., description="Celery task ID for batch processing")
    total_documents: int = Field(..., description="Total number of documents to process")
    status: str = Field(..., description="Batch processing status")
    message: str = Field(..., description="Status message")
    individual_task_ids: Optional[List[str]] = Field(None, description="Individual task IDs")
    
    @validator('total_documents')
    def validate_total(cls, v):
        if v <= 0:
            raise ValueError('Total documents must be greater than 0')
        return v


class ProviderMetricsResponse(BaseModel):
    """Response schema for AI provider metrics."""
    
    provider_name: str = Field(..., description="Name of the AI provider")
    success_rate: float = Field(..., description="Success rate (0.0 to 1.0)")
    avg_processing_time: float = Field(..., description="Average processing time in seconds")
    avg_confidence: float = Field(..., description="Average confidence score")
    total_requests: int = Field(..., description="Total number of requests processed")
    error_rate: float = Field(..., description="Error rate (0.0 to 1.0)")
    cost_per_request: float = Field(..., description="Average cost per request")
    last_updated: str = Field(..., description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if metrics unavailable")
    
    @validator('success_rate', 'avg_confidence', 'error_rate')
    def validate_rates(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Rate must be between 0.0 and 1.0')
        return v
    
    @validator('avg_processing_time', 'cost_per_request')
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ProviderHealthResponse(BaseModel):
    """Response schema for provider health check."""
    
    overall_healthy: bool = Field(..., description="Whether all providers are healthy")
    provider_health: Dict[str, Dict[str, Any]] = Field(..., description="Health status per provider")
    checked_at: str = Field(..., description="Timestamp of health check")
    
    class Config:
        schema_extra = {
            "example": {
                "overall_healthy": True,
                "provider_health": {
                    "openai": {
                        "healthy": True,
                        "checked_at": "2024-01-17T10:30:00Z"
                    },
                    "claude": {
                        "healthy": True,
                        "checked_at": "2024-01-17T10:30:00Z"
                    },
                    "azure": {
                        "healthy": False,
                        "error": "API quota exceeded",
                        "checked_at": "2024-01-17T10:30:00Z"
                    }
                },
                "checked_at": "2024-01-17T10:30:00Z"
            }
        }


class FieldConfidenceDetail(BaseModel):
    """Detailed confidence information for a field."""
    
    field_name: str = Field(..., description="Name of the field")
    value: Any = Field(..., description="Extracted value")
    confidence: float = Field(..., description="Confidence score")
    confidence_level: str = Field(..., description="Confidence level (high/medium/low/very_low)")
    validation_passed: bool = Field(..., description="Whether validation passed")
    reasons: List[str] = Field([], description="Reasons affecting confidence")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v
    
    @validator('confidence_level')
    def validate_level(cls, v):
        valid_levels = ['high', 'medium', 'low', 'very_low']
        if v not in valid_levels:
            raise ValueError(f'Confidence level must be one of: {valid_levels}')
        return v


class DetailedConfidenceResponse(BaseModel):
    """Detailed confidence analysis response."""
    
    order_id: UUID = Field(..., description="Order UUID")
    overall_confidence: float = Field(..., description="Overall confidence score")
    overall_level: str = Field(..., description="Overall confidence level")
    critical_fields_confidence: float = Field(..., description="Critical fields confidence")
    manual_review_required: bool = Field(..., description="Whether manual review is required")
    review_reasons: List[str] = Field([], description="Reasons for manual review")
    field_details: List[FieldConfidenceDetail] = Field(..., description="Detailed field analysis")
    processing_metadata: Dict[str, Any] = Field({}, description="Processing metadata")
    analysis_timestamp: str = Field(..., description="Timestamp of analysis")
    
    @validator('overall_confidence', 'critical_fields_confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v


class AITaskStatusResponse(BaseModel):
    """Response schema for AI task status."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    progress: Optional[float] = Field(None, description="Progress percentage (0.0 to 1.0)")
    message: Optional[str] = Field(None, description="Status message")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[str] = Field(None, description="Task start timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    @validator('progress')
    def validate_progress(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError('Progress must be between 0.0 and 1.0')
        return v


class ExtractionQualityMetrics(BaseModel):
    """Metrics for extraction quality analysis."""
    
    period_days: int = Field(..., description="Analysis period in days")
    total_extractions: int = Field(..., description="Total number of extractions")
    avg_overall_confidence: float = Field(..., description="Average overall confidence")
    avg_critical_confidence: float = Field(..., description="Average critical fields confidence")
    manual_review_rate: float = Field(..., description="Rate of manual reviews required")
    top_confidence_fields: List[Dict[str, Any]] = Field(..., description="Fields with highest confidence")
    low_confidence_fields: List[Dict[str, Any]] = Field(..., description="Fields with lowest confidence")
    provider_performance: Dict[str, Dict[str, Any]] = Field(..., description="Performance by provider")
    analyzed_at: str = Field(..., description="Analysis timestamp")
    
    @validator('avg_overall_confidence', 'avg_critical_confidence', 'manual_review_rate')
    def validate_rates(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Rate must be between 0.0 and 1.0')
        return v
    
    @validator('period_days', 'total_extractions')
    def validate_positive_int(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ProviderTestResponse(BaseModel):
    """Response schema for provider testing."""
    
    provider_name: str = Field(..., description="Name of the tested provider")
    test_successful: bool = Field(..., description="Whether the test was successful")
    response_time: float = Field(..., description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if test failed")
    test_details: Optional[Dict[str, Any]] = Field(None, description="Additional test details")
    tested_at: str = Field(..., description="Test timestamp")
    
    @validator('response_time')
    def validate_response_time(cls, v):
        if v < 0:
            raise ValueError('Response time must be non-negative')
        return v


class DocumentProcessingStats(BaseModel):
    """Statistics for document processing."""
    
    total_processed: int = Field(..., description="Total documents processed")
    successful: int = Field(..., description="Successfully processed documents")
    failed: int = Field(..., description="Failed document processing")
    manual_review: int = Field(..., description="Documents requiring manual review")
    avg_processing_time: float = Field(..., description="Average processing time")
    avg_confidence: float = Field(..., description="Average confidence score")
    provider_usage: Dict[str, int] = Field(..., description="Usage count by provider")
    period_start: str = Field(..., description="Statistics period start")
    period_end: str = Field(..., description="Statistics period end")
    
    @validator('total_processed', 'successful', 'failed', 'manual_review')
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError('Count must be non-negative')
        return v
    
    @validator('avg_confidence')
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    @validator('avg_processing_time')
    def validate_time(cls, v):
        if v < 0:
            raise ValueError('Processing time must be non-negative')
        return v


# Error response schemas
class AIErrorResponse(BaseModel):
    """Error response schema for AI endpoints."""
    
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(..., description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "error_type": "processing_failed",
                "message": "Document processing failed due to invalid PDF format",
                "details": {
                    "file_path": "/tmp/invalid_document.pdf",
                    "pdf_error": "Cannot read PDF structure"
                },
                "request_id": "req_123456789",
                "timestamp": "2024-01-17T10:30:00Z"
            }
        } 