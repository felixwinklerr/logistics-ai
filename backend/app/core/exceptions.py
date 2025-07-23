"""
Custom Exception Classes for Business Logic and Error Handling

Provides specialized exceptions for different error scenarios in the logistics system.
"""


class LogisticsBaseException(Exception):
    """Base exception for all logistics-related errors"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(LogisticsBaseException):
    """Raised when data validation fails"""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": value}
        )
        self.field = field
        self.value = value


class NotFoundError(LogisticsBaseException):
    """Raised when a requested resource is not found"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class BusinessRuleError(LogisticsBaseException):
    """Raised when business rules are violated"""
    
    def __init__(self, message: str, rule_name: str = None, context: dict = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            details={"rule_name": rule_name, "context": context or {}}
        )
        self.rule_name = rule_name
        self.context = context or {}


class DatabaseError(LogisticsBaseException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None, table: str = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation, "table": table}
        )
        self.operation = operation
        self.table = table


class ExternalServiceError(LogisticsBaseException):
    """Raised when external service calls fail"""
    
    def __init__(self, message: str, service_name: str = None, status_code: int = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service_name": service_name, "status_code": status_code}
        )
        self.service_name = service_name
        self.status_code = status_code


class GeographicError(LogisticsBaseException):
    """Raised when geographic operations fail"""
    
    def __init__(self, message: str, operation: str = None, coordinates: tuple = None):
        super().__init__(
            message=message,
            error_code="GEOGRAPHIC_ERROR",
            details={"operation": operation, "coordinates": coordinates}
        )
        self.operation = operation
        self.coordinates = coordinates


class ProfitCalculationError(LogisticsBaseException):
    """Raised when profit calculations fail"""
    
    def __init__(self, message: str, calculation_type: str = None, input_data: dict = None):
        super().__init__(
            message=message,
            error_code="PROFIT_CALCULATION_ERROR",
            details={"calculation_type": calculation_type, "input_data": input_data or {}}
        )
        self.calculation_type = calculation_type
        self.input_data = input_data or {}


class AIProcessingError(LogisticsBaseException):
    """Raised when AI document processing fails"""
    
    def __init__(self, message: str, provider: str = None, confidence: float = None):
        super().__init__(
            message=message,
            error_code="AI_PROCESSING_ERROR",
            details={"provider": provider, "confidence": confidence}
        )
        self.provider = provider
        self.confidence = confidence


class AuthenticationError(LogisticsBaseException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(LogisticsBaseException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", required_permission: str = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details={"required_permission": required_permission}
        )
        self.required_permission = required_permission


class ConfigurationError(LogisticsBaseException):
    """Raised when system configuration is invalid"""
    
    def __init__(self, message: str, setting_name: str = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"setting_name": setting_name}
        )
        self.setting_name = setting_name


# Exception factory functions for common scenarios

def create_validation_error(field: str, value, message: str = None) -> ValidationError:
    """Create a standardized validation error"""
    if not message:
        message = f"Invalid value for field '{field}': {value}"
    return ValidationError(message, field=field, value=value)


def create_not_found_error(resource_type: str, resource_id: str) -> NotFoundError:
    """Create a standardized not found error"""
    message = f"{resource_type} with ID '{resource_id}' not found"
    return NotFoundError(message, resource_type=resource_type, resource_id=resource_id)


def create_business_rule_error(rule_name: str, message: str, context: dict = None) -> BusinessRuleError:
    """Create a standardized business rule error"""
    return BusinessRuleError(message, rule_name=rule_name, context=context)


def create_database_error(operation: str, table: str, original_error: Exception) -> DatabaseError:
    """Create a standardized database error"""
    message = f"Database {operation} failed on table '{table}': {str(original_error)}"
    return DatabaseError(message, operation=operation, table=table)


def create_external_service_error(service_name: str, status_code: int, message: str = None) -> ExternalServiceError:
    """Create a standardized external service error"""
    if not message:
        message = f"External service '{service_name}' returned status {status_code}"
    return ExternalServiceError(message, service_name=service_name, status_code=status_code) 