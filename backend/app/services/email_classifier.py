"""
Email Classification Service for Transport Order Detection

Classifies emails to identify those containing transport orders
using multiple detection strategies.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger
from app.services.email_service import Email


class TransportOrderClassifier:
    """Classifier to identify transport order emails"""
    
    def __init__(self):
        # Romanian and English keywords for transport orders
        self.transport_keywords = [
            # Romanian terms
            "transport", "marfă", "încărcare", "descărcare", 
            "expediere", "livrare", "camion", "șofer",
            "comandă", "transport", "colet", "expediție",
            "ridicare", "predare", "AWB", "CMR",
            
            # English terms  
            "shipment", "cargo", "freight", "delivery",
            "pickup", "transport", "truck", "driver",
            "order", "consignment", "package", "dispatch"
        ]
        
        # Client domains that typically send transport orders
        self.trusted_client_domains = [
            # Will be loaded from configuration/database
            "@logistics-client1.ro",
            "@transport-company.com",
            "@freight-forwarder.ro"
        ]
        
        # Email patterns that indicate transport orders
        self.transport_patterns = [
            r"nr\.\s*AWB",  # AWB number
            r"CMR\s*nr",    # CMR number
            r"comandă\s*transport",  # Transport order
            r"order\s*number",  # Order number
            r"pickup\s*address",  # Pickup address
            r"delivery\s*address",  # Delivery address
            r"cargo\s*weight",  # Cargo weight
            r"loading\s*date",  # Loading date
        ]
        
        # Attachment requirements
        self.required_attachment_extensions = [".pdf"]
        
        # Exclusion patterns (emails to ignore)
        self.exclusion_patterns = [
            r"unsubscribe",
            r"newsletter",
            r"marketing",
            r"promotion",
            r"spam",
            r"noreply"
        ]
    
    async def is_transport_order_email(self, email: Email) -> bool:
        """Determine if email contains a transport order"""
        
        try:
            # First check - sender domain validation
            if await self._is_trusted_sender(email):
                logger.debug(f"Email from trusted sender: {email.sender}")
                return await self._has_pdf_attachments(email)
            
            # Second check - subject line analysis
            if await self._has_transport_keywords_in_subject(email):
                logger.debug(f"Transport keywords found in subject: {email.subject}")
                return await self._has_pdf_attachments(email)
            
            # Third check - body content analysis
            if await self._contains_transport_content(email):
                logger.debug(f"Transport content found in body")
                return await self._has_pdf_attachments(email)
            
            # Fourth check - attachment filename analysis
            if await self._has_transport_related_attachments(email):
                logger.debug(f"Transport-related attachment found")
                return True
            
            # Check for exclusion patterns
            if await self._matches_exclusion_patterns(email):
                logger.debug(f"Email matches exclusion patterns")
                return False
            
            logger.debug(f"Email does not appear to be a transport order: {email.subject}")
            return False
            
        except Exception as e:
            logger.error(f"Error classifying email {email.subject}: {e}")
            # Default to false on error
            return False
    
    async def _is_trusted_sender(self, email: Email) -> bool:
        """Check if email is from a trusted client domain"""
        sender_domain = self._extract_domain(email.sender)
        
        for trusted_domain in self.trusted_client_domains:
            if sender_domain and trusted_domain.lstrip('@') in sender_domain:
                return True
        
        return False
    
    async def _has_transport_keywords_in_subject(self, email: Email) -> bool:
        """Check if subject contains transport-related keywords"""
        subject_lower = email.subject.lower()
        
        for keyword in self.transport_keywords:
            if keyword.lower() in subject_lower:
                return True
        
        return False
    
    async def _contains_transport_content(self, email: Email) -> bool:
        """Analyze email body for transport order indicators"""
        body_lower = email.body.lower()
        
        # Check for transport keywords in body
        keyword_matches = 0
        for keyword in self.transport_keywords:
            if keyword.lower() in body_lower:
                keyword_matches += 1
        
        # Require at least 2 keyword matches for body-based detection
        if keyword_matches >= 2:
            return True
        
        # Check for transport-specific patterns
        for pattern in self.transport_patterns:
            if re.search(pattern, body_lower, re.IGNORECASE):
                return True
        
        return False
    
    async def _has_pdf_attachments(self, email: Email) -> bool:
        """Check if email has PDF attachments"""
        if not email.attachments:
            return False
        
        for attachment in email.attachments:
            filename = attachment.get("filename", "").lower()
            if any(filename.endswith(ext) for ext in self.required_attachment_extensions):
                return True
        
        return False
    
    async def _has_transport_related_attachments(self, email: Email) -> bool:
        """Check if attachment filenames suggest transport documents"""
        
        transport_filename_patterns = [
            r"awb",
            r"cmr",  
            r"transport",
            r"order",
            r"comandă",
            r"marfă",
            r"invoice",
            r"factură"
        ]
        
        for attachment in email.attachments:
            filename = attachment.get("filename", "").lower()
            
            # Must be PDF
            if not filename.endswith('.pdf'):
                continue
            
            # Check for transport-related terms in filename
            for pattern in transport_filename_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return True
        
        return False
    
    async def _matches_exclusion_patterns(self, email: Email) -> bool:
        """Check if email matches exclusion patterns"""
        
        # Check subject
        subject_lower = email.subject.lower()
        for pattern in self.exclusion_patterns:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                return True
        
        # Check sender
        sender_lower = email.sender.lower()
        for pattern in self.exclusion_patterns:
            if re.search(pattern, sender_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_domain(self, email_address: str) -> Optional[str]:
        """Extract domain from email address"""
        try:
            if '@' in email_address:
                return email_address.split('@')[1].lower()
        except Exception as e:
            logger.warning(f"Failed to extract domain from {email_address}: {e}")
        
        return None
    
    async def classify_email_confidence(self, email: Email) -> Dict[str, Any]:
        """Get detailed classification with confidence scores"""
        
        classification_result = {
            "is_transport_order": False,
            "confidence_score": 0.0,
            "classification_reasons": [],
            "detected_features": {}
        }
        
        confidence_factors = []
        
        # Factor 1: Trusted sender (+0.4)
        if await self._is_trusted_sender(email):
            confidence_factors.append(("trusted_sender", 0.4))
            classification_result["detected_features"]["trusted_sender"] = True
        
        # Factor 2: Subject keywords (+0.3)
        if await self._has_transport_keywords_in_subject(email):
            confidence_factors.append(("subject_keywords", 0.3))
            classification_result["detected_features"]["subject_keywords"] = True
        
        # Factor 3: Body content (+0.2)
        if await self._contains_transport_content(email):
            confidence_factors.append(("body_content", 0.2))
            classification_result["detected_features"]["body_content"] = True
        
        # Factor 4: PDF attachments (+0.2)
        if await self._has_pdf_attachments(email):
            confidence_factors.append(("pdf_attachments", 0.2))
            classification_result["detected_features"]["pdf_attachments"] = True
        
        # Factor 5: Transport-related attachments (+0.3)
        if await self._has_transport_related_attachments(email):
            confidence_factors.append(("transport_attachments", 0.3))
            classification_result["detected_features"]["transport_attachments"] = True
        
        # Factor 6: Exclusion patterns (-1.0)
        if await self._matches_exclusion_patterns(email):
            confidence_factors.append(("exclusion_patterns", -1.0))
            classification_result["detected_features"]["exclusion_patterns"] = True
        
        # Calculate total confidence
        total_confidence = sum(factor[1] for factor in confidence_factors)
        classification_result["confidence_score"] = max(0.0, min(1.0, total_confidence))
        classification_result["classification_reasons"] = [factor[0] for factor in confidence_factors]
        
        # Determine final classification (threshold: 0.5)
        classification_result["is_transport_order"] = classification_result["confidence_score"] >= 0.5
        
        return classification_result
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get classifier statistics and configuration"""
        
        return {
            "transport_keywords_count": len(self.transport_keywords),
            "trusted_domains_count": len(self.trusted_client_domains),
            "transport_patterns_count": len(self.transport_patterns),
            "exclusion_patterns_count": len(self.exclusion_patterns),
            "required_extensions": self.required_attachment_extensions,
            "classification_threshold": 0.5
        }
    
    async def update_trusted_domains(self, domains: List[str]):
        """Update the list of trusted client domains"""
        self.trusted_client_domains = domains
        logger.info(f"Updated trusted domains: {len(domains)} domains")
    
    async def add_transport_keyword(self, keyword: str):
        """Add a new transport keyword"""
        if keyword not in self.transport_keywords:
            self.transport_keywords.append(keyword)
            logger.info(f"Added transport keyword: {keyword}") 