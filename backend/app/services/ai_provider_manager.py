"""
AI Provider Management System

Implements intelligent provider selection with circuit breaker protection,
performance monitoring, and automatic failover for AI document parsing.
"""

import time
import json
import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from loguru import logger

from app.services.pdf_processor import PreprocessingResult
from app.schemas.ai import ExtractionResult


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if provider recovered


@dataclass
class ProviderMetrics:
    success_rate: float
    avg_response_time: float
    avg_quality_score: float
    cost_per_request: float
    total_requests: int
    last_success: float
    last_failure: Optional[float] = None


class CircuitBreaker:
    """Circuit breaker for AI provider failure protection"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenException("Provider circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
            
            raise e


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class NoHealthyProvidersException(Exception):
    """Exception raised when no healthy providers are available"""
    pass


class AllProvidersFailedException(Exception):
    """Exception raised when all providers fail"""
    pass


class OpenAIProvider:
    """OpenAI GPT-4 Vision provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4-vision-preview"
        self.base_url = "https://api.openai.com/v1"
        
    async def parse_document(self, preprocessing_result: PreprocessingResult, 
                           context: Optional[Dict] = None) -> ExtractionResult:
        """Parse document using OpenAI GPT-4 Vision"""
        
        start_time = time.time()
        
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(context)
            
            # Build user content with text and images
            user_content = self._build_user_content(preprocessing_result)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract and parse the response
                content = result["choices"][0]["message"]["content"]
                extracted_data = json.loads(content)
                
                # Calculate confidence scores
                confidence_scores = self._calculate_confidence_scores(
                    extracted_data, preprocessing_result
                )
                
                processing_time = time.time() - start_time
                
                return ExtractionResult(
                    extracted_data=extracted_data,
                    confidence_scores=confidence_scores,
                    provider_used="openai_gpt4v",
                    processing_time=processing_time
                )
                
        except Exception as e:
            logger.error(f"OpenAI provider failed: {e}")
            raise
    
    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Build context-aware system prompt"""
        
        base_prompt = """
You are an expert logistics document parser for Romanian freight forwarders.

TASK: Extract structured data from transport order PDFs with high accuracy.

CRITICAL REQUIREMENTS:
1. Extract client company name and VAT number with perfect accuracy
2. Identify pickup and delivery addresses (full address or at minimum postcode and city)
3. Extract the offered price with currency (assume EUR if not specified)
4. Extract cargo details if available (weight, pallets, LDM, special requirements)
5. Identify pickup and delivery date ranges if specified
6. Flag any ambiguous or missing critical information

OUTPUT FORMAT: Valid JSON with the following structure:
{
  "client_company_name": "string (required)",
  "client_vat_number": "string (required, format: RO/CUI number)",
  "client_contact_email": "string (optional)",
  "client_offered_price": number (required, in EUR),
  "pickup_address": "string (required)",
  "pickup_postcode": "string (optional)",
  "pickup_city": "string (required)",
  "pickup_country": "string (default: RO)",
  "delivery_address": "string (required)",
  "delivery_postcode": "string (optional)", 
  "delivery_city": "string (required)",
  "delivery_country": "string (required)",
  "cargo_weight_kg": number (optional),
  "cargo_pallets": number (optional),
  "cargo_ldm": number (optional),
  "special_requirements": "string (optional)",
  "pickup_date_start": "string YYYY-MM-DD (optional)",
  "pickup_date_end": "string YYYY-MM-DD (optional)",
  "delivery_date_start": "string YYYY-MM-DD (optional)",
  "delivery_date_end": "string YYYY-MM-DD (optional)",
  "client_reference_number": "string (optional)",
  "confidence_flags": {
    "missing_critical_fields": ["field_name"],
    "ambiguous_fields": ["field_name"],
    "extraction_notes": "string"
  }
}

IMPORTANT: 
- Always return valid JSON
- Mark confidence_flags for any uncertain extractions
- For Romanian VAT numbers, accept both RO and CUI prefixes
- Convert all prices to EUR (common rates: 1 USD ≈ 0.92 EUR, 1 GBP ≈ 1.15 EUR)
- For addresses, prioritize full street addresses but accept "City, Postcode" minimum
"""
        
        # Add context-specific guidance
        if context and context.get("sender_domain"):
            base_prompt += f"\nCONTEXT: This document is from {context['sender_domain']} - adjust expectations for their typical format."
        
        return base_prompt
    
    def _build_user_content(self, preprocessing_result: PreprocessingResult) -> List[Dict]:
        """Build user content with text and images"""
        
        content = []
        
        # Add text content
        if preprocessing_result.text_content:
            content.append({
                "type": "text",
                "text": f"Document text content:\n{preprocessing_result.text_content[:4000]}"  # Limit text length
            })
        
        # Add images
        for image_b64 in preprocessing_result.images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
            })
        
        return content
    
    def _calculate_confidence_scores(self, extracted_data: Dict[str, Any], 
                                   preprocessing_result: PreprocessingResult) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields"""
        
        confidence_scores = {}
        
        # Basic confidence scoring based on field presence and format
        for field, value in extracted_data.items():
            if field == "confidence_flags":
                continue
            
            base_confidence = 0.7  # Starting confidence
            
            # Increase confidence if field has value
            if value is not None and str(value).strip():
                base_confidence += 0.2
            
            # Field-specific confidence adjustments
            if field == "client_vat_number" and value:
                if self._validate_vat_format(str(value)):
                    base_confidence += 0.1
            
            if field == "client_offered_price" and value:
                try:
                    float(value)
                    base_confidence += 0.1
                except:
                    base_confidence -= 0.2
            
            confidence_scores[field] = min(base_confidence, 1.0)
        
        return confidence_scores
    
    def _validate_vat_format(self, vat: str) -> bool:
        """Validate Romanian VAT format"""
        import re
        clean_vat = re.sub(r'[^0-9]', '', vat)
        return 2 <= len(clean_vat) <= 10
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for OpenAI provider"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                
                return {
                    "is_healthy": True,
                    "provider": "openai_gpt4v",
                    "response_time": response.elapsed.total_seconds()
                }
        except Exception as e:
            return {
                "is_healthy": False,
                "provider": "openai_gpt4v",
                "error": str(e)
            }


class ClaudeProvider:
    """Claude 3.5 Sonnet provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "claude-3-5-sonnet-20241022"
        self.base_url = "https://api.anthropic.com/v1"
        
    async def parse_document(self, preprocessing_result: PreprocessingResult, 
                           context: Optional[Dict] = None) -> ExtractionResult:
        """Parse document using Claude 3.5 Sonnet"""
        
        start_time = time.time()
        
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(context)
            
            # Build user content
            user_content = self._build_user_content(preprocessing_result)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 2048,
                        "temperature": 0.1,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": user_content}
                        ]
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract and parse the response
                content = result["content"][0]["text"]
                
                # Extract JSON from the response (Claude might wrap it in markdown)
                extracted_data = self._extract_json_from_response(content)
                
                # Calculate confidence scores
                confidence_scores = self._calculate_confidence_scores(
                    extracted_data, preprocessing_result
                )
                
                processing_time = time.time() - start_time
                
                return ExtractionResult(
                    extracted_data=extracted_data,
                    confidence_scores=confidence_scores,
                    provider_used="claude_sonnet",
                    processing_time=processing_time
                )
                
        except Exception as e:
            logger.error(f"Claude provider failed: {e}")
            raise
    
    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Build Claude-specific system prompt"""
        
        return """You are an expert logistics document parser for Romanian freight forwarders.

Extract structured data from transport order documents with high accuracy.

Return the extracted data as valid JSON only, with no additional text or markdown formatting.

Follow the exact JSON structure specified in the user message."""
    
    def _build_user_content(self, preprocessing_result: PreprocessingResult) -> List[Dict]:
        """Build user content for Claude"""
        
        content = []
        
        # Add text instruction
        content.append({
            "type": "text",
            "text": f"""
Extract the following information from this transport order document and return as JSON:

{{
  "client_company_name": "string (required)",
  "client_vat_number": "string (required)",
  "client_offered_price": number (in EUR),
  "pickup_address": "string (required)",
  "pickup_city": "string (required)",
  "delivery_address": "string (required)",
  "delivery_city": "string (required)",
  "cargo_weight_kg": number (optional),
  "cargo_pallets": number (optional),
  "special_requirements": "string (optional)"
}}

Document text:
{preprocessing_result.text_content[:4000]}
"""
        })
        
        # Add images
        for image_b64 in preprocessing_result.images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64
                }
            })
        
        return content
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from Claude response that might contain markdown"""
        
        import re
        
        # Try to find JSON in the response
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response_text, re.DOTALL)
        
        if match:
            json_text = match.group(1)
        else:
            # Try to find any JSON object
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                json_text = match.group(0)
            else:
                json_text = response_text
        
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            raise ValueError(f"Invalid JSON response from Claude: {json_text[:500]}")
    
    def _calculate_confidence_scores(self, extracted_data: Dict[str, Any], 
                                   preprocessing_result: PreprocessingResult) -> Dict[str, float]:
        """Calculate confidence scores for Claude extractions"""
        
        # Similar to OpenAI but slightly different weighting
        confidence_scores = {}
        
        for field, value in extracted_data.items():
            base_confidence = 0.75  # Claude tends to be more conservative
            
            if value is not None and str(value).strip():
                base_confidence += 0.15
            
            confidence_scores[field] = min(base_confidence, 1.0)
        
        return confidence_scores
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Claude provider"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Simple test request
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 10,
                        "messages": [
                            {"role": "user", "content": "Hello"}
                        ]
                    }
                )
                
                return {
                    "is_healthy": response.status_code == 200,
                    "provider": "claude_sonnet",
                    "response_time": response.elapsed.total_seconds()
                }
        except Exception as e:
            return {
                "is_healthy": False,
                "provider": "claude_sonnet",
                "error": str(e)
            }


class AIProviderManager:
    """Intelligent AI provider management with circuit breaker protection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.providers = {}
        self.circuit_breakers = {}
        self.metrics = {}
        self.config = config
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured AI providers"""
        
        if self.config.get("openai_api_key"):
            self.providers["openai"] = OpenAIProvider(self.config["openai_api_key"])
            self.circuit_breakers["openai"] = CircuitBreaker()
            self.metrics["openai"] = ProviderMetrics(
                success_rate=1.0, avg_response_time=30.0, 
                avg_quality_score=0.9, cost_per_request=0.08,
                total_requests=0, last_success=time.time()
            )
        
        if self.config.get("anthropic_api_key"):
            self.providers["claude"] = ClaudeProvider(self.config["anthropic_api_key"])
            self.circuit_breakers["claude"] = CircuitBreaker()
            self.metrics["claude"] = ProviderMetrics(
                success_rate=1.0, avg_response_time=25.0,
                avg_quality_score=0.85, cost_per_request=0.06,
                total_requests=0, last_success=time.time()
            )
    
    async def parse_document(self, preprocessing_result: PreprocessingResult, 
                           priority: str = "balanced", exclude_provider: Optional[str] = None,
                           context: Optional[Dict] = None) -> ExtractionResult:
        """Parse document with intelligent provider selection and failover"""
        
        max_retries = 3
        attempts = 0
        last_exception = None
        
        while attempts < max_retries:
            try:
                # Select best available provider
                provider_name = await self._select_provider(priority, exclude_provider)
                provider = self.providers[provider_name]
                circuit_breaker = self.circuit_breakers[provider_name]
                
                logger.info(f"Attempting document parsing with {provider_name} (attempt {attempts + 1})")
                
                # Execute with circuit breaker protection
                start_time = time.time()
                result = await circuit_breaker.call(
                    provider.parse_document, preprocessing_result, context
                )
                processing_time = time.time() - start_time
                
                # Update metrics on success
                await self._update_metrics(provider_name, True, processing_time, result.average_confidence)
                
                result.provider = provider_name
                
                return result
                
            except Exception as e:
                attempts += 1
                last_exception = e
                
                # Update metrics on failure
                await self._update_metrics(provider_name, False, time.time() - start_time, 0.0)
                
                logger.warning(f"Provider {provider_name} failed (attempt {attempts}): {e}")
                
                # Exclude failed provider for next attempt
                if exclude_provider is None:
                    exclude_provider = provider_name
                else:
                    exclude_provider = f"{exclude_provider},{provider_name}"
        
        # All providers failed
        raise AllProvidersFailedException(f"All providers failed after {max_retries} attempts. Last error: {last_exception}")
    
    async def _select_provider(self, priority: str = "balanced", exclude_provider: Optional[str] = None) -> str:
        """Select optimal provider based on priority and current health"""
        
        # Get list of providers to exclude
        excluded = set()
        if exclude_provider:
            excluded = set(exclude_provider.split(","))
        
        # Filter healthy providers
        healthy_providers = []
        for name, provider in self.providers.items():
            if name not in excluded and await self._is_provider_healthy(name):
                healthy_providers.append(name)
        
        if not healthy_providers:
            raise NoHealthyProvidersException("No healthy providers available")
        
        if priority == "cost":
            return min(healthy_providers, key=lambda p: self.metrics[p].cost_per_request)
        elif priority == "speed":
            return min(healthy_providers, key=lambda p: self.metrics[p].avg_response_time)
        elif priority == "quality":
            return max(healthy_providers, key=lambda p: self.metrics[p].avg_quality_score)
        else:  # balanced
            return await self._select_balanced_provider(healthy_providers)
    
    async def _select_balanced_provider(self, available_providers: List[str]) -> str:
        """Select provider using balanced scoring algorithm"""
        
        best_provider = None
        best_score = -1
        
        for provider_name in available_providers:
            metrics = self.metrics[provider_name]
            
            # Calculate composite score (normalized 0-1)
            quality_score = metrics.avg_quality_score  # Already 0-1
            speed_score = max(0, 1 - (metrics.avg_response_time / 120))  # Normalize 120s = 0 score
            cost_score = max(0, 1 - (metrics.cost_per_request / 0.20))   # Normalize $0.20 = 0 score
            reliability_score = metrics.success_rate  # Already 0-1
            
            # Weighted composite score
            composite_score = (
                quality_score * 0.3 +      # 30% quality
                speed_score * 0.2 +        # 20% speed
                cost_score * 0.2 +         # 20% cost
                reliability_score * 0.3    # 30% reliability
            )
            
            if composite_score > best_score:
                best_score = composite_score
                best_provider = provider_name
        
        return best_provider
    
    async def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if provider is healthy and available"""
        
        # Check circuit breaker state
        cb = self.circuit_breakers.get(provider_name)
        if cb and cb.state == CircuitBreakerState.OPEN:
            return False
        
        # Check success rate
        metrics = self.metrics.get(provider_name)
        if metrics and metrics.success_rate < 0.5:  # Less than 50% success rate
            return False
        
        return True
    
    async def _update_metrics(self, provider_name: str, success: bool, 
                            response_time: float, quality_score: float):
        """Update provider performance metrics"""
        
        metrics = self.metrics[provider_name]
        
        # Update totals
        metrics.total_requests += 1
        
        # Update success rate (exponential moving average)
        alpha = 0.1  # Smoothing factor
        if success:
            metrics.success_rate = (1 - alpha) * metrics.success_rate + alpha * 1.0
            metrics.last_success = time.time()
        else:
            metrics.success_rate = (1 - alpha) * metrics.success_rate + alpha * 0.0
            metrics.last_failure = time.time()
        
        # Update response time (exponential moving average)
        metrics.avg_response_time = (1 - alpha) * metrics.avg_response_time + alpha * response_time
        
        # Update quality score (exponential moving average)
        if success and quality_score > 0:
            metrics.avg_quality_score = (1 - alpha) * metrics.avg_quality_score + alpha * quality_score
        
        # Log metrics for monitoring
        logger.debug(f"Provider {provider_name} metrics updated: "
                    f"success_rate={metrics.success_rate:.3f}, "
                    f"avg_response_time={metrics.avg_response_time:.1f}s, "
                    f"avg_quality={metrics.avg_quality_score:.3f}")
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        
        status = {}
        
        for provider_name in self.providers.keys():
            circuit_breaker = self.circuit_breakers[provider_name]
            metrics = self.metrics[provider_name]
            
            status[provider_name] = {
                "circuit_breaker_state": circuit_breaker.state.value,
                "is_healthy": await self._is_provider_healthy(provider_name),
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.avg_response_time,
                "avg_quality_score": metrics.avg_quality_score,
                "total_requests": metrics.total_requests
            }
        
        return status 