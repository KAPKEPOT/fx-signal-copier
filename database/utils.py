# fx/database/utils.py
"""
Database utility functions
"""
import json
from datetime import datetime, date
from typing import Any
import logging

logger = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for database serialization"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


def paginate(query, page: int = 1, per_page: int = 20):
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        tuple: (items, total, pages)
    """
    if page < 1:
        page = 1
    
    total = query.count()
    pages = (total + per_page - 1) // per_page
    
    if page > pages and pages > 0:
        page = pages
    
    offset = (page - 1) * per_page
    items = query.limit(per_page).offset(offset).all()
    
    return items, total, pages


def bulk_insert(session, model, items: list, chunk_size: int = 1000):
    """
    Bulk insert items in chunks
    
    Args:
        session: SQLAlchemy session
        model: SQLAlchemy model class
        items: List of dicts to insert
        chunk_size: Number of items per chunk
    """
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        session.bulk_insert_mappings(model, chunk)
        session.commit()
        logger.debug(f"Inserted chunk {i//chunk_size + 1}")


def get_or_create(session, model, defaults: dict = None, **kwargs):
    """
    Get or create a database record
    
    Args:
        session: SQLAlchemy session
        model: SQLAlchemy model class
        defaults: Default values if creating
        **kwargs: Filter criteria
    
    Returns:
        tuple: (instance, created)
    """
    instance = session.query(model).filter_by(**kwargs).first()
    
    if instance:
        return instance, False
    
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    session.add(instance)
    session.commit()
    
    return instance, True


def test_connection(engine) -> bool:
    """
    Test database connection
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        bool: True if connection successful
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_table_stats(session) -> dict:
    """
    Get statistics about database tables
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        dict: Table statistics
    """
    from sqlalchemy import inspect
    
    inspector = inspect(session.bind)
    stats = {}
    
    for table_name in inspector.get_table_names():
        result = session.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = result.scalar()
        stats[table_name] = count
    
    return stats


def vacuum_analyze(session):
    """
    Run VACUUM ANALYZE on PostgreSQL database
    
    Args:
        session: SQLAlchemy session
    """
    if session.bind.dialect.name == 'postgresql':
        session.execute("VACUUM ANALYZE")
        session.commit()
        logger.info("VACUUM ANALYZE completed")
    else:
        logger.warning("VACUUM ANALYZE only supported on PostgreSQL")