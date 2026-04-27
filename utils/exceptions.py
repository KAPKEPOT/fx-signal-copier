# fx/utils/exceptions.py

class UtilityError(Exception):
    """Base exception for all utility errors"""
    pass


class ValidationError(UtilityError):
    """Raised when validation fails"""
    pass


class FormatError(UtilityError):
    """Raised when formatting fails"""
    pass


class ConversionError(UtilityError):
    """Raised when data conversion fails"""
    pass


class FileError(UtilityError):
    """Raised when file operations fail"""
    pass


class NetworkError(UtilityError):
    """Raised when network operations fail"""
    pass


class ConfigurationError(UtilityError):
    """Raised when configuration is invalid"""
    pass


class ResourceNotFoundError(UtilityError):
    """Raised when a resource is not found"""
    pass


class PermissionDeniedError(UtilityError):
    """Raised when permission is denied"""
    pass


class OperationTimeoutError(UtilityError):
    """Raised when operation times out"""
    pass