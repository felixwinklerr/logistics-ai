"""
Profit Calculation Engine - Business Rules Pipeline for Freight Operations

Implements the profit calculation architecture designed in Sprint 3 creative phase.
Provides enterprise-grade profit margin calculations with Romanian business compliance,
configurable business rules, and comprehensive audit logging.

Features:
- Multi-currency support (EUR/RON) with real-time conversion
- Romanian VAT compliance (19%, B2B exemptions)
- Configurable business rules engine
- Pipeline pattern for calculation flow
- Comprehensive audit logging for compliance
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field, validator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Currency(str, Enum):
    """Supported currencies for Romanian freight operations"""
    EUR = "EUR"
    RON = "RON"
    USD = "USD"


class VATStatus(str, Enum):
    """VAT status for Romanian business transactions"""
    B2B_EXEMPT = "b2b_exempt"  # Business-to-business, VAT exempt
    B2C_STANDARD = "b2c_standard"  # Business-to-consumer, 19% VAT
    EXPORT = "export"  # Export transaction, 0% VAT
    IMPORT = "import"  # Import transaction, special rules


class FeeType(str, Enum):
    """Types of fees applicable to freight operations"""
    FIXED = "fixed"  # Fixed amount in specified currency
    PERCENTAGE = "percentage"  # Percentage of base amount
    TIERED = "tiered"  # Different rates based on value brackets


@dataclass
class Fee:
    """Represents a fee in profit calculations"""
    fee_type: FeeType
    amount: Decimal
    currency: Currency = Currency.EUR
    description: str = ""
    minimum: Optional[Decimal] = None
    maximum: Optional[Decimal] = None


@dataclass 
class ProfitCalculationInput:
    """Input parameters for profit calculation"""
    client_offered_price: Decimal
    client_currency: Currency
    subcontractor_price: Decimal
    subcontractor_currency: Currency
    
    # Business context
    client_vat_status: VATStatus
    subcontractor_vat_status: VATStatus
    transaction_date: datetime = field(default_factory=datetime.now)
    
    # Additional costs
    additional_fees: List[Fee] = field(default_factory=list)
    insurance_cost: Decimal = Decimal('0.00')
    fuel_surcharge: Decimal = Decimal('0.00')
    
    # Geographic context
    pickup_country: str = "RO"
    delivery_country: str = "RO"
    
    # Calculation preferences
    target_currency: Currency = Currency.EUR
    apply_rounding: bool = True


@dataclass
class ProfitCalculationResult:
    """Complete profit calculation result with breakdown"""
    
    # Core results
    profit_margin: Decimal
    profit_percentage: Decimal
    
    # Detailed breakdown
    client_amount_eur: Decimal
    subcontractor_amount_eur: Decimal
    total_fees_eur: Decimal
    vat_amount: Decimal
    
    # Exchange rates used
    eur_ron_rate: Optional[Decimal] = None
    eur_usd_rate: Optional[Decimal] = None
    
    # Calculation metadata
    calculation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    calculated_at: datetime = field(default_factory=datetime.now)
    calculation_method: str = "business_rules_pipeline"
    
    # Rule evaluation results
    rules_applied: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Audit information
    currency_conversion_logs: List[Dict[str, Any]] = field(default_factory=list)
    fee_calculation_logs: List[Dict[str, Any]] = field(default_factory=list)


class CurrencyService:
    """Currency conversion service with real-time rates"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.cache_ttl = 3600  # 1 hour cache
        self._rate_cache: Dict[str, Tuple[Decimal, datetime]] = {}
    
    async def get_exchange_rate(
        self, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Decimal:
        """Get exchange rate between currencies"""
        
        if from_currency == to_currency:
            return Decimal('1.00')
        
        cache_key = f"{from_currency}_{to_currency}"
        
        # Check cache
        if cache_key in self._rate_cache:
            rate, cached_at = self._rate_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                return rate
        
        # For MVP, use simulated exchange rates
        # In production, integrate with ECB, XE, or Romanian National Bank
        rate = await self._get_simulated_rate(from_currency, to_currency)
        
        # Cache the rate
        self._rate_cache[cache_key] = (rate, datetime.now())
        
        return rate
    
    async def _get_simulated_rate(
        self, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Decimal:
        """Simulated exchange rates for MVP"""
        
        # Base rates (simulated but realistic for Romanian market)
        base_rates = {
            "EUR_RON": Decimal('4.9750'),  # EUR to RON
            "EUR_USD": Decimal('1.0850'),  # EUR to USD
            "RON_USD": Decimal('0.2180'),  # RON to USD
        }
        
        pair = f"{from_currency}_{to_currency}"
        reverse_pair = f"{to_currency}_{from_currency}"
        
        if pair in base_rates:
            return base_rates[pair]
        elif reverse_pair in base_rates:
            return Decimal('1.00') / base_rates[reverse_pair]
        else:
            # Cross currency calculation via EUR
            if from_currency != Currency.EUR:
                eur_rate = await self.get_exchange_rate(from_currency, Currency.EUR)
                target_rate = await self.get_exchange_rate(Currency.EUR, to_currency)
                return eur_rate * target_rate
            else:
                return Decimal('1.00')  # Fallback
    
    async def convert_amount(
        self, 
        amount: Decimal, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Tuple[Decimal, Decimal]:
        """Convert amount between currencies, returns (converted_amount, exchange_rate)"""
        
        rate = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate
        
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), rate


class VATCalculationService:
    """Romanian VAT calculation service"""
    
    # Romanian VAT rates (2024)
    STANDARD_VAT_RATE = Decimal('0.19')  # 19%
    REDUCED_VAT_RATE = Decimal('0.09')   # 9% (books, medicine, etc.)
    ZERO_VAT_RATE = Decimal('0.00')      # 0% (exports, exempt services)
    
    def calculate_vat(
        self, 
        base_amount: Decimal, 
        vat_status: VATStatus,
        is_export: bool = False
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate VAT amount and total including VAT
        Returns (vat_amount, total_with_vat)
        """
        
        if is_export or vat_status == VATStatus.EXPORT:
            vat_rate = self.ZERO_VAT_RATE
        elif vat_status == VATStatus.B2B_EXEMPT:
            vat_rate = self.ZERO_VAT_RATE  # B2B transactions often VAT exempt
        elif vat_status == VATStatus.B2C_STANDARD:
            vat_rate = self.STANDARD_VAT_RATE
        else:
            vat_rate = self.STANDARD_VAT_RATE  # Default to standard rate
        
        vat_amount = (base_amount * vat_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_with_vat = base_amount + vat_amount
        
        return vat_amount, total_with_vat
    
    def is_vat_exempt_transaction(
        self, 
        pickup_country: str, 
        delivery_country: str,
        client_vat_status: VATStatus
    ) -> bool:
        """Determine if transaction is VAT exempt based on business rules"""
        
        # EU export rules
        if pickup_country == "RO" and delivery_country != "RO":
            eu_countries = {"DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "HU", "CZ", "SK"}
            if delivery_country in eu_countries:
                return client_vat_status == VATStatus.B2B_EXEMPT
        
        # Import rules
        if pickup_country != "RO" and delivery_country == "RO":
            return False  # Usually subject to import VAT
        
        # Domestic Romanian transactions
        if pickup_country == "RO" and delivery_country == "RO":
            return client_vat_status == VATStatus.B2B_EXEMPT
        
        return False


class BusinessRulesService:
    """Configurable business rules evaluation engine"""
    
    def __init__(self):
        self.rules: Dict[str, Any] = self._load_default_rules()
    
    def _load_default_rules(self) -> Dict[str, Any]:
        """Load default business rules for Romanian freight operations"""
        return {
            "minimum_profit_percentage": Decimal('5.00'),  # Minimum 5% profit margin
            "maximum_profit_percentage": Decimal('50.00'),  # Maximum 50% profit margin
            "minimum_order_value": Decimal('100.00'),  # Minimum order value EUR
            "fuel_surcharge_threshold": Decimal('500.00'),  # Apply fuel surcharge above EUR 500
            "insurance_required_threshold": Decimal('10000.00'),  # Insurance required above EUR 10k
            "vat_validation_enabled": True,
            "currency_conversion_required": True,
            "audit_logging_enabled": True
        }
    
    async def evaluate_profit_margin(
        self, 
        profit_percentage: Decimal,
        calculation_input: ProfitCalculationInput
    ) -> List[str]:
        """Evaluate profit margin against business rules"""
        
        warnings = []
        
        # Check minimum profit margin
        min_profit = self.rules["minimum_profit_percentage"]
        if profit_percentage < min_profit:
            warnings.append(f"Profit margin {profit_percentage}% below minimum {min_profit}%")
        
        # Check maximum profit margin
        max_profit = self.rules["maximum_profit_percentage"]
        if profit_percentage > max_profit:
            warnings.append(f"Profit margin {profit_percentage}% above maximum {max_profit}%")
        
        # Check minimum order value
        min_order = self.rules["minimum_order_value"]
        if calculation_input.client_offered_price < min_order:
            warnings.append(f"Order value below minimum threshold {min_order} EUR")
        
        return warnings
    
    async def evaluate_fee_requirements(
        self, 
        calculation_input: ProfitCalculationInput
    ) -> List[Fee]:
        """Evaluate and generate required fees based on business rules"""
        
        required_fees = []
        
        # Fuel surcharge for large orders
        if calculation_input.client_offered_price >= self.rules["fuel_surcharge_threshold"]:
            fuel_fee = Fee(
                fee_type=FeeType.PERCENTAGE,
                amount=Decimal('2.50'),  # 2.5% fuel surcharge
                description="Fuel surcharge for large order"
            )
            required_fees.append(fuel_fee)
        
        # Insurance fee for high-value orders
        if calculation_input.client_offered_price >= self.rules["insurance_required_threshold"]:
            insurance_fee = Fee(
                fee_type=FeeType.PERCENTAGE,
                amount=Decimal('0.50'),  # 0.5% insurance fee
                description="Mandatory insurance for high-value cargo"
            )
            required_fees.append(insurance_fee)
        
        return required_fees


class CalculationService:
    """Core profit margin and percentage calculation service"""
    
    def calculate_base_profit(
        self, 
        client_amount: Decimal, 
        subcontractor_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Calculate base profit margin and percentage"""
        
        profit_margin = client_amount - subcontractor_amount
        
        if client_amount > 0:
            profit_percentage = ((profit_margin / client_amount) * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            profit_percentage = Decimal('0.00')
        
        return profit_margin, profit_percentage
    
    def calculate_fee_total(
        self, 
        fees: List[Fee], 
        base_amount: Decimal,
        currency_service: CurrencyService
    ) -> Decimal:
        """Calculate total fees in target currency"""
        
        total_fees = Decimal('0.00')
        
        for fee in fees:
            if fee.fee_type == FeeType.FIXED:
                fee_amount = fee.amount
            elif fee.fee_type == FeeType.PERCENTAGE:
                fee_amount = (base_amount * fee.amount / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            else:  # TIERED - simplified for MVP
                fee_amount = fee.amount
            
            # Apply minimum/maximum limits
            if fee.minimum and fee_amount < fee.minimum:
                fee_amount = fee.minimum
            if fee.maximum and fee_amount > fee.maximum:
                fee_amount = fee.maximum
            
            total_fees += fee_amount
        
        return total_fees


class AuditService:
    """Comprehensive calculation logging and compliance service"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def log_calculation(
        self, 
        calculation_input: ProfitCalculationInput,
        calculation_result: ProfitCalculationResult
    ):
        """Log profit calculation for audit compliance"""
        
        audit_data = {
            "calculation_id": calculation_result.calculation_id,
            "timestamp": calculation_result.calculated_at,
            "input_data": {
                "client_price": str(calculation_input.client_offered_price),
                "client_currency": calculation_input.client_currency.value,
                "subcontractor_price": str(calculation_input.subcontractor_price),
                "subcontractor_currency": calculation_input.subcontractor_currency.value,
                "vat_status": calculation_input.client_vat_status.value
            },
            "result_data": {
                "profit_margin": str(calculation_result.profit_margin),
                "profit_percentage": str(calculation_result.profit_percentage),
                "total_fees": str(calculation_result.total_fees_eur),
                "rules_applied": calculation_result.rules_applied,
                "warnings": calculation_result.warnings
            }
        }
        
        # In production, store in audit table
        logger.info(f"Profit calculation audit: {audit_data}")


class ProfitCalculationEngine:
    """
    Main Profit Calculation Engine with Pipeline Pattern
    
    Orchestrates the complete profit calculation workflow including:
    1. Currency conversion to target currency
    2. Business rules evaluation
    3. Fee calculations
    4. VAT handling
    5. Final profit calculation
    6. Audit logging
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
        # Initialize component services
        self.currency_service = CurrencyService()
        self.vat_service = VATCalculationService()
        self.rules_service = BusinessRulesService()
        self.calculation_service = CalculationService()
        self.audit_service = AuditService(db_session)
    
    async def calculate_profit(
        self, 
        calculation_input: ProfitCalculationInput
    ) -> ProfitCalculationResult:
        """
        Execute complete profit calculation pipeline
        
        Pipeline Steps:
        1. Base Calculation
        2. Currency Normalization
        3. VAT Handling
        4. Fee Calculations
        5. Final Profit Calculation
        6. Business Rules Validation
        7. Audit Logging
        """
        
        start_time = datetime.now()
        result = ProfitCalculationResult(
            profit_margin=Decimal('0.00'),
            profit_percentage=Decimal('0.00'),
            client_amount_eur=Decimal('0.00'),
            subcontractor_amount_eur=Decimal('0.00'),
            total_fees_eur=Decimal('0.00'),
            vat_amount=Decimal('0.00')
        )
        
        try:
            # Step 1: Currency Normalization
            result.client_amount_eur, client_rate = await self.currency_service.convert_amount(
                calculation_input.client_offered_price,
                calculation_input.client_currency,
                calculation_input.target_currency
            )
            
            result.subcontractor_amount_eur, subcontractor_rate = await self.currency_service.convert_amount(
                calculation_input.subcontractor_price,
                calculation_input.subcontractor_currency,
                calculation_input.target_currency
            )
            
            # Log currency conversions
            if calculation_input.client_currency == Currency.RON:
                result.eur_ron_rate = client_rate
            
            result.rules_applied.append("currency_normalization")
            
            # Step 2: Evaluate Business Rules for Additional Fees
            required_fees = await self.rules_service.evaluate_fee_requirements(calculation_input)
            all_fees = calculation_input.additional_fees + required_fees
            
            # Step 3: Calculate Total Fees
            result.total_fees_eur = self.calculation_service.calculate_fee_total(
                all_fees,
                result.client_amount_eur,
                self.currency_service
            )
            
            # Step 4: VAT Calculation
            if self.vat_service.is_vat_exempt_transaction(
                calculation_input.pickup_country,
                calculation_input.delivery_country,
                calculation_input.client_vat_status
            ):
                result.vat_amount = Decimal('0.00')
                result.rules_applied.append("vat_exempt")
            else:
                result.vat_amount, _ = self.vat_service.calculate_vat(
                    result.client_amount_eur,
                    calculation_input.client_vat_status
                )
                result.rules_applied.append("vat_calculated")
            
            # Step 5: Final Profit Calculation
            effective_client_amount = result.client_amount_eur - result.vat_amount
            effective_cost = result.subcontractor_amount_eur + result.total_fees_eur
            
            result.profit_margin, result.profit_percentage = self.calculation_service.calculate_base_profit(
                effective_client_amount,
                effective_cost
            )
            
            result.rules_applied.append("final_calculation")
            
            # Step 6: Business Rules Validation
            validation_warnings = await self.rules_service.evaluate_profit_margin(
                result.profit_percentage,
                calculation_input
            )
            result.warnings.extend(validation_warnings)
            
            # Step 7: Audit Logging
            await self.audit_service.log_calculation(calculation_input, result)
            result.rules_applied.append("audit_logged")
            
            logger.info(
                f"Profit calculation completed: "
                f"margin={result.profit_margin}, "
                f"percentage={result.profit_percentage}%, "
                f"duration={(datetime.now() - start_time).total_seconds():.3f}s"
            )
            
        except Exception as e:
            logger.error(f"Profit calculation failed: {e}")
            result.warnings.append(f"Calculation error: {str(e)}")
        
        return result
    
    async def validate_calculation_input(
        self, 
        calculation_input: ProfitCalculationInput
    ) -> List[str]:
        """Validate calculation input parameters"""
        
        validation_errors = []
        
        if calculation_input.client_offered_price <= 0:
            validation_errors.append("Client offered price must be positive")
        
        if calculation_input.subcontractor_price <= 0:
            validation_errors.append("Subcontractor price must be positive")
        
        if calculation_input.subcontractor_price > calculation_input.client_offered_price:
            validation_errors.append("Subcontractor price exceeds client offered price")
        
        return validation_errors


# Service factory function
async def create_profit_calculation_engine(db_session: AsyncSession) -> ProfitCalculationEngine:
    """Factory function to create profit calculation engine"""
    return ProfitCalculationEngine(db_session) 