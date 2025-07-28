"""
Romanian Business Logic Service
Implements Romanian freight forwarding business rules and validations.
"""

import re
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class RomanianVATCalculator:
    """Handles Romanian VAT calculations and validations."""
    
    STANDARD_VAT_RATE = Decimal("0.19")  # 19% standard VAT
    REDUCED_RATES = {
        "books": Decimal("0.05"),  # 5% for books
        "accommodation": Decimal("0.09"),  # 9% for accommodation
        "transport": Decimal("0.19"),  # 19% for transport services
    }
    
    @staticmethod
    def validate_vat_number(vat_number: str) -> bool:
        """
        Validate Romanian VAT number format: RO + 2-10 digits
        """
        if not vat_number:
            return False
        
        # Remove spaces and convert to uppercase
        clean_vat = vat_number.replace(" ", "").upper()
        
        # Check Romanian VAT pattern: RO followed by 2-10 digits
        pattern = r"^RO\d{2,10}$"
        return bool(re.match(pattern, clean_vat))
    
    @staticmethod
    def calculate_vat(amount: Decimal, vat_rate: Optional[Decimal] = None, 
                     service_type: str = "transport") -> Dict[str, Decimal]:
        """
        Calculate VAT for Romanian freight forwarding services.
        
        Args:
            amount: Net amount in RON or EUR
            vat_rate: Override VAT rate (optional)
            service_type: Type of service for rate determination
            
        Returns:
            Dict with net_amount, vat_amount, total_amount
        """
        if vat_rate is None:
            vat_rate = RomanianVATCalculator.REDUCED_RATES.get(
                service_type, RomanianVATCalculator.STANDARD_VAT_RATE
            )
        
        net_amount = Decimal(str(amount))
        vat_amount = net_amount * vat_rate
        total_amount = net_amount + vat_amount
        
        return {
            "net_amount": net_amount.quantize(Decimal("0.01")),
            "vat_amount": vat_amount.quantize(Decimal("0.01")),
            "total_amount": total_amount.quantize(Decimal("0.01")),
            "vat_rate": vat_rate,
        }

class RomanianAddressValidator:
    """Validates and formats Romanian addresses."""
    
    # Romanian county codes (județe)
    VALID_JUDETE = [
        "AB", "AR", "AG", "BC", "BH", "BN", "BT", "BV", "BR", "BZ",
        "CS", "CL", "CJ", "CT", "CV", "DB", "DJ", "GL", "GR", "GJ",
        "HR", "HD", "IL", "IS", "IF", "MM", "MH", "MS", "NT", "OT",
        "PH", "SM", "SJ", "SB", "SV", "TR", "TM", "TL", "VS", "VL",
        "VN", "B"  # B for Bucharest
    ]
    
    @staticmethod
    def validate_postal_code(postal_code: str) -> bool:
        """
        Validate Romanian postal code format: 6 digits
        """
        if not postal_code:
            return False
        
        # Remove spaces and check for 6 digits
        clean_code = postal_code.replace(" ", "")
        return len(clean_code) == 6 and clean_code.isdigit()
    
    @staticmethod
    def validate_judet_code(judet: str) -> bool:
        """
        Validate Romanian county (județ) code.
        """
        if not judet:
            return False
        
        return judet.upper() in RomanianAddressValidator.VALID_JUDETE
    
    @staticmethod
    def format_address(address_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Format and validate Romanian address.
        
        Args:
            address_data: Dict with strada, numar, judet, localitate, cod_postal
            
        Returns:
            Dict with formatted address and validation results
        """
        result = {
            "formatted_address": "",
            "is_valid": True,
            "validation_errors": []
        }
        
        # Validate postal code
        if not RomanianAddressValidator.validate_postal_code(
            address_data.get("cod_postal", "")
        ):
            result["is_valid"] = False
            result["validation_errors"].append("Invalid postal code format")
        
        # Validate județ
        if not RomanianAddressValidator.validate_judet_code(
            address_data.get("judet", "")
        ):
            result["is_valid"] = False
            result["validation_errors"].append("Invalid county (județ) code")
        
        # Format address if valid
        if result["is_valid"]:
            strada = address_data.get("strada", "")
            numar = address_data.get("numar", "")
            localitate = address_data.get("localitate", "")
            judet = address_data.get("judet", "").upper()
            cod_postal = address_data.get("cod_postal", "")
            
            result["formatted_address"] = (
                f"{strada} {numar}, {localitate}, "
                f"jud. {judet}, {cod_postal}, România"
            )
        
        return result

class OrderWorkflowState(Enum):
    """Romanian freight forwarding order workflow states."""
    
    DRAFT = "draft"
    DOCUMENT_UPLOADED = "document_uploaded"
    AI_PROCESSING = "ai_processing"
    VALIDATION_REQUIRED = "validation_required"
    VALIDATED = "validated"
    PRICING_CALCULATED = "pricing_calculated"
    CONFIRMED = "confirmed"
    SUBCONTRACTOR_ASSIGNED = "subcontractor_assigned"
    IN_TRANSIT = "in_transit"
    CUSTOMS_CLEARANCE = "customs_clearance"
    DELIVERED = "delivered"
    INVOICED = "invoiced"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RomanianBusinessRuleEngine:
    """
    Core Romanian business rule engine for freight forwarding.
    Implements rule-based decision making as per creative phase decision.
    """
    
    def __init__(self):
        self.vat_calculator = RomanianVATCalculator()
        self.address_validator = RomanianAddressValidator()
    
    def validate_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order data against Romanian business rules.
        
        Args:
            order_data: Order data dictionary
            
        Returns:
            Validation result with errors and warnings
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "romanian_validations": {}
        }
        
        # Validate VAT number if provided
        if "vat_number" in order_data:
            if not self.vat_calculator.validate_vat_number(order_data["vat_number"]):
                validation_result["errors"].append(
                    "Invalid Romanian VAT number format"
                )
                validation_result["is_valid"] = False
        
        # Validate addresses
        for addr_type in ["pickup_address", "delivery_address"]:
            if addr_type in order_data:
                addr_validation = self.address_validator.format_address(
                    order_data[addr_type]
                )
                validation_result["romanian_validations"][addr_type] = addr_validation
                
                if not addr_validation["is_valid"]:
                    validation_result["errors"].extend(
                        [f"{addr_type}: {error}" for error in 
                         addr_validation["validation_errors"]]
                    )
                    validation_result["is_valid"] = False
        
        # Currency validation for Romanian context
        if "currency" in order_data:
            currency = order_data["currency"].upper()
            if currency not in ["RON", "EUR"]:
                validation_result["warnings"].append(
                    "Currency should be RON or EUR for Romanian operations"
                )
        
        return validation_result
    
    def calculate_order_pricing(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate pricing for Romanian freight forwarding order.
        
        Args:
            order_data: Order data with weight, dimensions, route info
            
        Returns:
            Pricing calculation with Romanian VAT
        """
        pricing_result = {
            "base_cost": Decimal("0.00"),
            "additional_fees": {},
            "vat_calculation": {},
            "total_cost": Decimal("0.00"),
            "currency": "RON"
        }
        
        # Basic cost calculation (simplified for foundation)
        weight = Decimal(str(order_data.get("weight", 0)))
        distance = Decimal(str(order_data.get("distance_km", 100)))
        
        # Base calculation: weight * distance * rate
        base_rate = Decimal("0.50")  # RON per kg per km
        base_cost = weight * distance * base_rate
        
        # Romanian specific fees
        additional_fees = {}
        
        # Fuel surcharge (Romanian market standard)
        fuel_surcharge = base_cost * Decimal("0.15")  # 15% fuel surcharge
        additional_fees["fuel_surcharge"] = fuel_surcharge
        
        # EU cross-border fee if applicable
        if order_data.get("is_eu_cross_border", False):
            eu_fee = Decimal("50.00")  # Fixed EU processing fee
            additional_fees["eu_processing_fee"] = eu_fee
        
        # Calculate subtotal
        subtotal = base_cost + sum(additional_fees.values())
        
        # Calculate Romanian VAT
        vat_calculation = self.vat_calculator.calculate_vat(
            subtotal, service_type="transport"
        )
        
        pricing_result.update({
            "base_cost": base_cost.quantize(Decimal("0.01")),
            "additional_fees": {
                k: v.quantize(Decimal("0.01")) 
                for k, v in additional_fees.items()
            },
            "vat_calculation": vat_calculation,
            "total_cost": vat_calculation["total_amount"]
        })
        
        return pricing_result
    
    def determine_next_workflow_state(self, current_state: OrderWorkflowState, 
                                    context: Dict[str, Any]) -> OrderWorkflowState:
        """
        Determine next workflow state based on Romanian business rules.
        
        Args:
            current_state: Current order state
            context: Context data for state transition
            
        Returns:
            Next workflow state
        """
        state_transitions = {
            OrderWorkflowState.DRAFT: OrderWorkflowState.DOCUMENT_UPLOADED,
            OrderWorkflowState.DOCUMENT_UPLOADED: OrderWorkflowState.AI_PROCESSING,
            OrderWorkflowState.AI_PROCESSING: self._determine_post_ai_state(context),
            OrderWorkflowState.VALIDATION_REQUIRED: OrderWorkflowState.VALIDATED,
            OrderWorkflowState.VALIDATED: OrderWorkflowState.PRICING_CALCULATED,
            OrderWorkflowState.PRICING_CALCULATED: OrderWorkflowState.CONFIRMED,
            OrderWorkflowState.CONFIRMED: OrderWorkflowState.SUBCONTRACTOR_ASSIGNED,
            OrderWorkflowState.SUBCONTRACTOR_ASSIGNED: OrderWorkflowState.IN_TRANSIT,
            OrderWorkflowState.IN_TRANSIT: self._determine_transit_state(context),
            OrderWorkflowState.CUSTOMS_CLEARANCE: OrderWorkflowState.DELIVERED,
            OrderWorkflowState.DELIVERED: OrderWorkflowState.INVOICED,
            OrderWorkflowState.INVOICED: OrderWorkflowState.PAID,
            OrderWorkflowState.PAID: OrderWorkflowState.COMPLETED,
        }
        
        return state_transitions.get(current_state, current_state)
    
    def _determine_post_ai_state(self, context: Dict[str, Any]) -> OrderWorkflowState:
        """Determine state after AI processing based on confidence."""
        confidence = context.get("ai_confidence", 0.0)
        
        # Use 0.85 confidence threshold as per QA validation
        if confidence >= 0.85:
            return OrderWorkflowState.VALIDATED
        else:
            return OrderWorkflowState.VALIDATION_REQUIRED
    
    def _determine_transit_state(self, context: Dict[str, Any]) -> OrderWorkflowState:
        """Determine state during transit based on route."""
        is_eu_cross_border = context.get("is_eu_cross_border", False)
        
        if is_eu_cross_border:
            return OrderWorkflowState.CUSTOMS_CLEARANCE
        else:
            return OrderWorkflowState.DELIVERED


# Service factory for dependency injection
def create_romanian_business_engine() -> RomanianBusinessRuleEngine:
    """Factory function for Romanian business rule engine."""
    return RomanianBusinessRuleEngine()
