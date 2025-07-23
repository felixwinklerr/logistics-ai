"""
Confidence scoring service for evaluating AI document extraction quality.

This service provides confidence scoring algorithms to assess the quality
of AI extraction results and determine when manual review is required.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import statistics
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence level classifications."""
    HIGH = "high"           # >= 0.9 - Auto-process
    MEDIUM = "medium"       # 0.7-0.89 - Auto-process with notification
    LOW = "low"             # 0.5-0.69 - Manual review recommended
    VERY_LOW = "very_low"   # < 0.5 - Manual review required


@dataclass
class FieldConfidence:
    """Confidence score for a specific field."""
    field_name: str
    value: Any
    confidence: float
    reasons: List[str]
    validation_passed: bool
    
    @property
    def level(self) -> ConfidenceLevel:
        """Get confidence level classification."""
        if self.confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class DocumentConfidence:
    """Overall document confidence assessment."""
    overall_confidence: float
    field_confidences: Dict[str, FieldConfidence]
    critical_fields_confidence: float
    manual_review_required: bool
    review_reasons: List[str]
    
    @property
    def level(self) -> ConfidenceLevel:
        """Get overall confidence level."""
        if self.overall_confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif self.overall_confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        elif self.overall_confidence >= 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class ConfidenceScorer:
    """
    Service for scoring confidence in AI document extraction results.
    
    Uses multiple validation techniques:
    - Format validation (email, VAT, addresses)
    - Business rule validation
    - Cross-field consistency checks
    - Statistical analysis of extraction quality
    """
    
    # Critical fields that must have high confidence
    CRITICAL_FIELDS = {
        'client_company_name',
        'client_vat_number', 
        'client_offered_price',
        'pickup_address',
        'delivery_address'
    }
    
    # Format validation patterns
    VALIDATION_PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'romanian_vat': r'^RO\d{8,10}$',
        'eu_vat': r'^[A-Z]{2}\d{8,12}$',
        'phone': r'^(\+4|4|0)[0-9]{8,9}$',
        'postcode_ro': r'^\d{6}$',
        'currency': r'^\d+([.,]\d{2})?$'
    }
    
    def __init__(self):
        """Initialize confidence scorer."""
        self.logger = logging.getLogger(__name__)
    
    async def score_extraction(
        self, 
        extracted_data: Dict[str, Any],
        ai_confidence_scores: Optional[Dict[str, float]] = None,
        provider_metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentConfidence:
        """
        Score the confidence of extracted document data.
        
        Args:
            extracted_data: Data extracted by AI service
            ai_confidence_scores: Confidence scores from AI provider
            provider_metadata: Additional metadata from AI provider
            
        Returns:
            DocumentConfidence with detailed scoring
        """
        try:
            # Score individual fields
            field_confidences = {}
            for field_name, value in extracted_data.items():
                field_confidence = await self._score_field(
                    field_name, value, ai_confidence_scores, extracted_data
                )
                field_confidences[field_name] = field_confidence
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(field_confidences)
            
            # Score critical fields specifically
            critical_confidence = self._calculate_critical_fields_confidence(field_confidences)
            
            # Determine if manual review is needed
            manual_review_required, review_reasons = self._assess_manual_review_need(
                field_confidences, overall_confidence, critical_confidence
            )
            
            return DocumentConfidence(
                overall_confidence=overall_confidence,
                field_confidences=field_confidences,
                critical_fields_confidence=critical_confidence,
                manual_review_required=manual_review_required,
                review_reasons=review_reasons
            )
            
        except Exception as e:
            self.logger.error(f"Error scoring extraction confidence: {e}")
            # Return low confidence if scoring fails
            return DocumentConfidence(
                overall_confidence=0.3,
                field_confidences={},
                critical_fields_confidence=0.3,
                manual_review_required=True,
                review_reasons=[f"Confidence scoring failed: {str(e)}"]
            )
    
    async def _score_field(
        self,
        field_name: str,
        value: Any,
        ai_scores: Optional[Dict[str, float]],
        full_data: Dict[str, Any]
    ) -> FieldConfidence:
        """Score confidence for a specific field."""
        reasons = []
        confidence_factors = []
        
        # Start with AI provider confidence if available
        base_confidence = ai_scores.get(field_name, 0.5) if ai_scores else 0.5
        confidence_factors.append(("ai_provider", base_confidence))
        
        # Format validation
        format_confidence, format_reasons = self._validate_field_format(field_name, value)
        confidence_factors.append(("format_validation", format_confidence))
        reasons.extend(format_reasons)
        
        # Business rule validation
        business_confidence, business_reasons = self._validate_business_rules(
            field_name, value, full_data
        )
        confidence_factors.append(("business_rules", business_confidence))
        reasons.extend(business_reasons)
        
        # Cross-field consistency
        consistency_confidence, consistency_reasons = self._validate_field_consistency(
            field_name, value, full_data
        )
        confidence_factors.append(("consistency", consistency_confidence))
        reasons.extend(consistency_reasons)
        
        # Calculate weighted average
        final_confidence = self._calculate_weighted_confidence(confidence_factors)
        
        # Validation passed if confidence is reasonable
        validation_passed = final_confidence >= 0.6
        
        return FieldConfidence(
            field_name=field_name,
            value=value,
            confidence=final_confidence,
            reasons=reasons,
            validation_passed=validation_passed
        )
    
    def _validate_field_format(self, field_name: str, value: Any) -> Tuple[float, List[str]]:
        """Validate field format and return confidence score."""
        if not value or value == "":
            return 0.0, [f"{field_name}: Empty value"]
        
        value_str = str(value).strip()
        reasons = []
        
        # Email validation
        if field_name.endswith('_email') or 'email' in field_name.lower():
            if re.match(self.VALIDATION_PATTERNS['email'], value_str):
                return 0.95, [f"{field_name}: Valid email format"]
            else:
                return 0.2, [f"{field_name}: Invalid email format"]
        
        # VAT number validation
        if 'vat' in field_name.lower():
            if re.match(self.VALIDATION_PATTERNS['romanian_vat'], value_str):
                return 0.9, [f"{field_name}: Valid Romanian VAT format"]
            elif re.match(self.VALIDATION_PATTERNS['eu_vat'], value_str):
                return 0.85, [f"{field_name}: Valid EU VAT format"]
            else:
                return 0.3, [f"{field_name}: Invalid VAT format"]
        
        # Price validation
        if 'price' in field_name.lower() or 'cost' in field_name.lower():
            try:
                price_val = Decimal(str(value))
                if price_val > 0:
                    return 0.9, [f"{field_name}: Valid price format"]
                else:
                    return 0.4, [f"{field_name}: Price must be positive"]
            except (InvalidOperation, ValueError):
                return 0.2, [f"{field_name}: Invalid price format"]
        
        # Address validation (basic)
        if 'address' in field_name.lower():
            if len(value_str) >= 10 and any(char.isdigit() for char in value_str):
                return 0.8, [f"{field_name}: Reasonable address format"]
            else:
                return 0.5, [f"{field_name}: Questionable address format"]
        
        # Postcode validation
        if 'postcode' in field_name.lower():
            if re.match(self.VALIDATION_PATTERNS['postcode_ro'], value_str):
                return 0.9, [f"{field_name}: Valid Romanian postcode"]
            elif value_str.isdigit() and len(value_str) >= 4:
                return 0.7, [f"{field_name}: Valid international postcode format"]
            else:
                return 0.4, [f"{field_name}: Invalid postcode format"]
        
        # Company name validation
        if 'company' in field_name.lower():
            if len(value_str) >= 3 and any(char.isalpha() for char in value_str):
                return 0.8, [f"{field_name}: Reasonable company name"]
            else:
                return 0.4, [f"{field_name}: Questionable company name"]
        
        # Default for other fields
        if len(value_str) >= 2:
            return 0.7, [f"{field_name}: Non-empty value"]
        else:
            return 0.3, [f"{field_name}: Very short value"]
    
    def _validate_business_rules(
        self, field_name: str, value: Any, full_data: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """Validate against business rules."""
        reasons = []
        
        # Price reasonableness
        if 'price' in field_name.lower():
            try:
                price = Decimal(str(value))
                if 100 <= price <= 50000:  # Reasonable transport prices in EUR
                    return 0.9, [f"{field_name}: Price in reasonable range"]
                elif price < 100:
                    return 0.6, [f"{field_name}: Price seems low for transport"]
                else:
                    return 0.5, [f"{field_name}: Price seems high for transport"]
            except (InvalidOperation, ValueError):
                return 0.3, [f"{field_name}: Cannot validate price range"]
        
        # Date validation
        if 'date' in field_name.lower():
            # Basic date reasonableness could be added here
            return 0.8, [f"{field_name}: Date format acceptable"]
        
        # Weight/dimension validation
        if field_name in ['cargo_weight_kg', 'cargo_ldm']:
            try:
                val = float(value)
                if 1 <= val <= 25000:  # Reasonable cargo limits
                    return 0.9, [f"{field_name}: Value in reasonable range"]
                else:
                    return 0.5, [f"{field_name}: Value outside typical range"]
            except (ValueError, TypeError):
                return 0.4, [f"{field_name}: Invalid numeric value"]
        
        # Default business rule confidence
        return 0.7, [f"{field_name}: No specific business rules violated"]
    
    def _validate_field_consistency(
        self, field_name: str, value: Any, full_data: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """Validate consistency across fields."""
        reasons = []
        
        # Check pickup/delivery consistency
        if field_name == 'pickup_city' and 'delivery_city' in full_data:
            pickup_city = str(value).lower().strip()
            delivery_city = str(full_data['delivery_city']).lower().strip()
            if pickup_city == delivery_city:
                return 0.6, [f"{field_name}: Same pickup and delivery city (unusual)"]
            else:
                return 0.9, [f"{field_name}: Different pickup/delivery cities"]
        
        # Check VAT and company name consistency
        if field_name == 'client_vat_number' and 'client_company_name' in full_data:
            vat = str(value).strip()
            company = str(full_data['client_company_name']).strip()
            if vat.startswith('RO') and len(company) > 0:
                return 0.8, [f"{field_name}: VAT and company both present"]
            else:
                return 0.6, [f"{field_name}: VAT/company consistency unclear"]
        
        # Default consistency confidence
        return 0.8, [f"{field_name}: No consistency issues detected"]
    
    def _calculate_weighted_confidence(self, confidence_factors: List[Tuple[str, float]]) -> float:
        """Calculate weighted average confidence score."""
        if not confidence_factors:
            return 0.5
        
        # Weights for different validation types
        weights = {
            'ai_provider': 0.3,
            'format_validation': 0.35,
            'business_rules': 0.2,
            'consistency': 0.15
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for factor_type, confidence in confidence_factors:
            weight = weights.get(factor_type, 0.1)
            weighted_sum += confidence * weight
            total_weight += weight
        
        return min(1.0, weighted_sum / total_weight if total_weight > 0 else 0.5)
    
    def _calculate_overall_confidence(self, field_confidences: Dict[str, FieldConfidence]) -> float:
        """Calculate overall document confidence."""
        if not field_confidences:
            return 0.3
        
        # Separate critical and non-critical fields
        critical_scores = []
        non_critical_scores = []
        
        for field_name, field_conf in field_confidences.items():
            if field_name in self.CRITICAL_FIELDS:
                critical_scores.append(field_conf.confidence)
            else:
                non_critical_scores.append(field_conf.confidence)
        
        # Critical fields have more weight
        critical_avg = statistics.mean(critical_scores) if critical_scores else 0.5
        non_critical_avg = statistics.mean(non_critical_scores) if non_critical_scores else 0.7
        
        # Weighted average: 70% critical, 30% non-critical
        overall = (critical_avg * 0.7) + (non_critical_avg * 0.3)
        
        return min(1.0, overall)
    
    def _calculate_critical_fields_confidence(
        self, field_confidences: Dict[str, FieldConfidence]
    ) -> float:
        """Calculate confidence for critical fields only."""
        critical_scores = [
            field_conf.confidence 
            for field_name, field_conf in field_confidences.items()
            if field_name in self.CRITICAL_FIELDS
        ]
        
        if not critical_scores:
            return 0.5
        
        return statistics.mean(critical_scores)
    
    def _assess_manual_review_need(
        self,
        field_confidences: Dict[str, FieldConfidence],
        overall_confidence: float,
        critical_confidence: float
    ) -> Tuple[bool, List[str]]:
        """Determine if manual review is required."""
        reasons = []
        
        # Critical field thresholds
        if critical_confidence < 0.7:
            reasons.append(f"Critical fields confidence too low: {critical_confidence:.2f}")
        
        # Overall confidence threshold
        if overall_confidence < 0.6:
            reasons.append(f"Overall confidence too low: {overall_confidence:.2f}")
        
        # Check for any very low confidence critical fields
        for field_name, field_conf in field_confidences.items():
            if field_name in self.CRITICAL_FIELDS and field_conf.confidence < 0.5:
                reasons.append(f"Critical field '{field_name}' has very low confidence: {field_conf.confidence:.2f}")
        
        # Check for validation failures
        failed_validations = [
            field_name for field_name, field_conf in field_confidences.items()
            if not field_conf.validation_passed and field_name in self.CRITICAL_FIELDS
        ]
        
        if failed_validations:
            reasons.append(f"Critical fields failed validation: {', '.join(failed_validations)}")
        
        manual_review_required = len(reasons) > 0
        
        return manual_review_required, reasons
    
    def get_confidence_summary(self, confidence: DocumentConfidence) -> Dict[str, Any]:
        """Get a summary of confidence assessment for logging/UI."""
        return {
            "overall_confidence": confidence.overall_confidence,
            "confidence_level": confidence.level.value,
            "critical_fields_confidence": confidence.critical_fields_confidence,
            "manual_review_required": confidence.manual_review_required,
            "review_reasons": confidence.review_reasons,
            "field_count": len(confidence.field_confidences),
            "high_confidence_fields": len([
                f for f in confidence.field_confidences.values() 
                if f.level == ConfidenceLevel.HIGH
            ]),
            "low_confidence_fields": [
                f.field_name for f in confidence.field_confidences.values()
                if f.level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
            ]
        } 