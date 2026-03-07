# fx/utils/decorators.py
import asyncio
import functools
import time
import logging
from typing import Any, Callable, Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.exceptions import ValidationError

logger = get_logger(__name__)


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on failure
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def rate_limit(max_calls: int, period: int = 60):
    """
    Decorator to rate limit function calls
    """
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            now = datetime.utcnow()
            
            # Remove old calls
            cutoff = now - timedelta(seconds=period)
            while calls and calls[0] < cutoff:
                calls.pop(0)
            
            # Check rate limit
            if len(calls) >= max_calls:
                wait_time = (calls[0] - cutoff).total_seconds()
                raise ValidationError(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds"
                )
            
            # Add current call
            calls.append(now)
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            now = datetime.utcnow()
            
            # Remove old calls
            cutoff = now - timedelta(seconds=period)
            while calls and calls[0] < cutoff:
                calls.pop(0)
            
            # Check rate limit
            if len(calls) >= max_calls:
                wait_time = (calls[0] - cutoff).total_seconds()
                raise ValidationError(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds"
                )
            
            # Add current call
            calls.append(now)
            
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function execution time
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            log = logger or get_logger(func.__module__)
            log.info(f"{func.__name__} executed in {duration:.3f}s")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            log = logger or get_logger(func.__module__)
            log.info(f"{func.__name__} executed in {duration:.3f}s")
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def handle_exceptions(
    error_message: str = "An error occurred",
    log_error: bool = True,
    re_raise: bool = False
):
    """
    Decorator to handle exceptions gracefully
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"{error_message}: {e}", exc_info=True)
                
                if re_raise:
                    raise
                
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"{error_message}: {e}", exc_info=True)
                
                if re_raise:
                    raise
                
                return None
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def memoize(timeout: Optional[int] = None):
    """
    Decorator to cache function results
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_times = {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            if key in cache:
                if timeout is None:
                    return cache[key]
                
                age = time.time() - cache_times[key]
                if age < timeout:
                    return cache[key]
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Update cache
            cache[key] = result
            cache_times[key] = time.time()
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            if key in cache:
                if timeout is None:
                    return cache[key]
                
                age = time.time() - cache_times[key]
                if age < timeout:
                    return cache[key]
            
            # Call function
            result = func(*args, **kwargs)
            
            # Update cache
            cache[key] = result
            cache_times[key] = time.time()
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def singleton(cls):
    """
    Decorator to create singleton class
    """
    instances = {}
    
    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


def validate_input(**validators):
    """
    Decorator to validate function arguments
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Validate each argument
            for arg_name, validator in validators.items():
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if not validator(value):
                        raise ValidationError(f"Invalid value for {arg_name}")
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Validate each argument
            for arg_name, validator in validators.items():
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if not validator(value):
                        raise ValidationError(f"Invalid value for {arg_name}")
            
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def require_permission(permission: str):
    """
    Decorator to check user permissions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Check if user has permission
            if hasattr(self, 'check_permission'):
                if not self.check_permission(permission):
                    raise PermissionError(f"Permission denied: {permission}")
            
            return await func(self, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # Check if user has permission
            if hasattr(self, 'check_permission'):
                if not self.check_permission(permission):
                    raise PermissionError(f"Permission denied: {permission}")
            
            return func(self, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator