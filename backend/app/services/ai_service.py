"""
AI Document Processing Service

Implements hybrid consensus + cascading AI architecture for transport document parsing
using OpenAI GPT-4 Vision and Claude 3.5 Sonnet with intelligent provider selection.
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import httpx
from loguru import logger

from app.core.config import get_settings
from app.services.pdf_processor import PDFProcessor, PreprocessingResult
from app.schemas.ai import ExtractionResult


class AIProvider(Enum):
    """AI provider enumeration"""
    OPENAI_GPT4V = "openai_gpt4v"
    CLAUDE_SONNET = "claude_sonnet"
    AZURE_OPENAI = "azure_openai"


@dataclass
class DocumentParsingResult:
    """Final document parsing result"""
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    provider_used: str
    processing_time: float
    validation_errors: List[str]
    metadata: Dict[str, Any]
    requires_manual_review: bool = False
    
    @property
    def success(self) -> bool:
        """Check if parsing was successful"""
        return len(self.validation_errors) == 0 and self.average_confidence >= 0.7
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all fields"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)


class AIDocumentParser:
    """Core AI document parser with hybrid provider management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pdf_processor = PDFProcessor()
        # Delayed import to avoid circular import
        from app.services.confidence_scorer import ConfidenceScorer
        from app.services.ai_provider_manager import AIProviderManager
        self.confidence_scorer = ConfidenceScorer()
        self.provider_manager = AIProviderManager(self._get_ai_config())
        
        # Parsing configuration
        self.confidence_threshold = 0.85
        self.critical_fields = [
            "client_company_name", 
            "client_vat_number", 
            "client_offered_price",
            "pickup_address",
            "delivery_address"
        ]
    
    def _get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration from settings"""
        return {
            "openai_api_key": getattr(self.settings, "openai_api_key", ""),
            "anthropic_api_key": getattr(self.settings, "anthropic_api_key", ""),
            "azure_openai_key": getattr(self.settings, "azure_openai_key", ""),
            "azure_openai_endpoint": getattr(self.settings, "azure_openai_endpoint", "")
        }
    
    async def parse_document(self, pdf_path: str, context: Optional[Dict] = None) -> DocumentParsingResult:
        """
        Main document parsing entry point
        
        Args:
            pdf_path: Path to PDF file
            context: Optional context (email sender, etc.)
            
        Returns:
            DocumentParsingResult with extracted data and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting document parsing: {pdf_path}")
            
            # Step 1: Preprocess PDF
            preprocessing_result = await self.pdf_processor.process(pdf_path)
            logger.debug(f"PDF preprocessing completed: {len(preprocessing_result.images)} images extracted")
            
            # Step 2: Primary AI extraction
            primary_result = await self._primary_extraction(preprocessing_result, context)
            logger.info(f"Primary extraction completed with confidence: {primary_result.average_confidence:.3f}")
            
            # Step 3: Validate and potentially get second opinion
            final_result = await self._validate_and_enhance(primary_result, preprocessing_result)
            
            # Step 4: Post-process and validate business rules
            document_result = await self._post_process_result(final_result, pdf_path, start_time)
            
            logger.info(f"Document parsing completed: {document_result.provider_used}, "
                       f"confidence: {document_result.average_confidence:.3f}, "
                       f"success: {document_result.success}")
            
            return document_result
            
        except Exception as e:
            logger.error(f"Document parsing failed for {pdf_path}: {e}")
            return await self._create_error_result(pdf_path, str(e), start_time)
    
    async def _primary_extraction(self, preprocessing_result: PreprocessingResult, 
                                 context: Optional[Dict]) -> ExtractionResult:
        """Primary AI extraction using provider manager"""
        
        try:
            # Use provider manager for intelligent selection
            result = await self.provider_manager.parse_document(
                preprocessing_result, 
                priority="balanced",
                context=context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Primary extraction failed: {e}")
            raise
    
    async def _validate_and_enhance(self, primary_result: ExtractionResult, 
                                   preprocessing_result: PreprocessingResult) -> ExtractionResult:
        """Validate primary result and enhance with secondary provider if needed"""
        
        # Check if secondary validation is needed
        if not self._needs_secondary_validation(primary_result):
            logger.debug("Primary result has sufficient confidence, skipping secondary validation")
            return primary_result
        
        logger.info("Low confidence detected for critical fields, getting second opinion")
        
        try:
            # Get secondary validation with different provider
            secondary_result = await self.provider_manager.parse_document(
                preprocessing_result,
                priority="quality",  # Use highest quality provider for validation
                exclude_provider=primary_result.provider
            )
            
            # Merge results with confidence weighting
            enhanced_result = await self._merge_extraction_results(
                primary_result, secondary_result
            )
            
            logger.info(f"Enhanced result with secondary validation: "
                       f"confidence improved to {enhanced_result.average_confidence:.3f}")
            
            return enhanced_result
            
        except Exception as e:
            logger.warning(f"Secondary validation failed: {e}, using primary result")
            return primary_result
    
    def _needs_secondary_validation(self, result: ExtractionResult) -> bool:
        """Determine if secondary validation is needed"""
        
        # Check confidence for critical fields
        for field in self.critical_fields:
            field_confidence = result.confidence_scores.get(field, 0.0)
            if field_confidence < self.confidence_threshold:
                logger.debug(f"Critical field {field} has low confidence: {field_confidence:.3f}")
                return True
        
        # Check overall confidence
        if result.average_confidence < 0.8:
            logger.debug(f"Overall confidence too low: {result.average_confidence:.3f}")
            return True
        
        # Check for data anomalies
        if self._detect_data_anomalies(result):
            logger.debug("Data anomalies detected, requiring validation")
            return True
        
        return False
    
    def _detect_data_anomalies(self, result: ExtractionResult) -> bool:
        """Detect anomalies in extracted data"""
        
        data = result.data
        
        # Check for unrealistic prices
        price = data.get("client_offered_price", 0)
        if isinstance(price, (int, float)):
            if price < 100 or price > 50000:  # Unrealistic transport prices
                return True
        
        # Check for missing critical data
        missing_criticals = 0
        for field in self.critical_fields:
            if not data.get(field):
                missing_criticals += 1
        
        if missing_criticals >= 2:  # Too many missing critical fields
            return True
        
        # Check for invalid VAT format
        vat = data.get("client_vat_number", "")
        if vat and not self._validate_romanian_vat_format(vat):
            return True
        
        return False
    
    def _validate_romanian_vat_format(self, vat: str) -> bool:
        """Basic Romanian VAT number format validation"""
        import re
        
        # Clean VAT number
        clean_vat = re.sub(r'[^0-9]', '', str(vat))
        
        # Romanian VAT is 2-10 digits
        return 2 <= len(clean_vat) <= 10
    
    async def _merge_extraction_results(self, primary: ExtractionResult, 
                                       secondary: ExtractionResult) -> ExtractionResult:
        """Merge two extraction results with confidence weighting"""
        
        merged_data = {}
        merged_confidence = {}
        
        # Get all fields from both results
        all_fields = set(primary.data.keys()) | set(secondary.data.keys())
        
        for field in all_fields:
            primary_value = primary.data.get(field)
            secondary_value = secondary.data.get(field)
            primary_conf = primary.confidence_scores.get(field, 0.0)
            secondary_conf = secondary.confidence_scores.get(field, 0.0)
            
            # Choose value with higher confidence
            if primary_conf >= secondary_conf:
                merged_data[field] = primary_value
                merged_confidence[field] = primary_conf
            else:
                merged_data[field] = secondary_value
                merged_confidence[field] = secondary_conf
            
            # For critical fields, flag if values differ significantly
            if field in self.critical_fields and primary_value != secondary_value:
                logger.warning(f"Critical field {field} differs between providers: "
                              f"'{primary_value}' vs '{secondary_value}'")
        
        return ExtractionResult(
            extracted_data=merged_data,
            confidence_scores=merged_confidence,
            provider_used=f"{primary.provider_used}+{secondary.provider_used}",
            processing_time=primary.processing_time + secondary.processing_time
        )
    
    async def _post_process_result(self, result: ExtractionResult, pdf_path: str, 
                                  start_time: float) -> DocumentParsingResult:
        """Post-process extraction result and create final result"""
        
        # Validate business rules
        validation_errors = await self._validate_business_rules(result.data)
        
        # Calculate final confidence scores
        final_confidence = self.confidence_scorer.calculate_confidence_scores(
            result.data, validation_errors
        )
        
        # Determine if manual review is required
        requires_manual_review = (
            result.average_confidence < 0.7 or
            len(validation_errors) > 0 or
            any(final_confidence.get(field, 0) < 0.8 for field in self.critical_fields)
        )
        
        # Create metadata
        metadata = {
            "pdf_path": pdf_path,
            "processing_provider": result.provider,
            "processing_duration": result.processing_time,
            "total_duration": time.time() - start_time,
            "field_count": len(result.data),
            "critical_fields_extracted": sum(1 for field in self.critical_fields if result.data.get(field)),
            "average_confidence": result.average_confidence
        }
        
        return DocumentParsingResult(
            extracted_data=result.data,
            confidence_scores=final_confidence,
            provider_used=result.provider,
            processing_time=time.time() - start_time,
            validation_errors=validation_errors,
            metadata=metadata,
            requires_manual_review=requires_manual_review
        )
    
    async def _validate_business_rules(self, data: Dict[str, Any]) -> List[str]:
        """Validate extracted data against business rules"""
        
        errors = []
        
        # Required fields validation
        for field in self.critical_fields:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Price validation
        price = data.get("client_offered_price")
        if price is not None:
            try:
                price_float = float(price)
                if price_float <= 0:
                    errors.append("Client price must be positive")
                elif price_float < 50:
                    errors.append("Client price seems too low for transport order")
                elif price_float > 100000:
                    errors.append("Client price seems too high for typical transport order")
            except (ValueError, TypeError):
                errors.append("Client price is not a valid number")
        
        # VAT number validation
        vat = data.get("client_vat_number")
        if vat and not self._validate_romanian_vat_format(vat):
            errors.append("Invalid Romanian VAT number format")
        
        return errors
    
    async def _create_error_result(self, pdf_path: str, error_message: str, 
                                  start_time: float) -> DocumentParsingResult:
        """Create error result for failed parsing"""
        
        return DocumentParsingResult(
            extracted_data={},
            confidence_scores={},
            provider_used="none",
            processing_time=time.time() - start_time,
            validation_errors=[f"Parsing failed: {error_message}"],
            metadata={
                "pdf_path": pdf_path,
                "error": error_message,
                "failed_at": datetime.utcnow().isoformat()
            },
            requires_manual_review=True
        ) 