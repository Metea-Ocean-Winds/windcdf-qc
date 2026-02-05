"""Custom exceptions for windcdf-qc."""


class WindCDFError(Exception):
    """Base exception for windcdf-qc."""

    pass


class QCError(WindCDFError):
    """Exception raised during QC operations."""

    pass


class IOError(WindCDFError):
    """Exception raised during I/O operations."""

    pass


class ConfigError(WindCDFError):
    """Exception raised for configuration errors."""

    pass


class ValidationError(WindCDFError):
    """Exception raised for data validation errors."""

    pass
