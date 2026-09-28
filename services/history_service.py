from datetime import datetime, time
from sqlalchemy import func
from database import db_session
from models import Batch, BatchStatusHistory

def get_batch_history(batch_identifier):
    """
    Get full chronological history for a batch, ordered newest first.
    batch_identifier can be batch_id (int) or batch_number (str).
    """
    if isinstance(batch_identifier, int):
        batch = db_session.query(Batch).filter(Batch.id == batch_identifier).first()
    else:
        normalized = str(batch_identifier).strip().upper()
        batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == normalized).first()
        
    if not batch:
        return []

    records = db_session.query(BatchStatusHistory).filter(
        BatchStatusHistory.batch_id == batch.id
    ).order_by(BatchStatusHistory.timestamp.desc(), BatchStatusHistory.id.desc()).all()

    return [r.to_dict() for r in records]

def add_status_history_record(batch_id, status, progress, remarks, timestamp=None):
    """
    Add a new immutable history record for a batch.
    """
    if not timestamp:
        timestamp = datetime.now()

    record = BatchStatusHistory(
        batch_id=batch_id,
        status=status,
        progress=progress,
        timestamp=timestamp,
        remarks=remarks
    )
    db_session.add(record)
    db_session.commit()
    return record.to_dict()

def get_batch_status_at_datetime(batch_identifier, target_datetime):
    """
    Retrieve the exact manufacturing status of a batch at a specific point in time or date.
    target_datetime can be a datetime, date, or date string 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    
    Rule:
    Filter records where timestamp <= target_datetime (end of specified target date if time not given).
    Sort newest first (timestamp desc).
    The top record represents the accurate historical state at that time.
    """
    if isinstance(batch_identifier, int):
        batch = db_session.query(Batch).filter(Batch.id == batch_identifier).first()
    else:
        normalized = str(batch_identifier).strip().upper()
        batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == normalized).first()

    if not batch:
        return None, "Batch not found"

    # Convert target_datetime to end-of-day datetime if it's a date or date string without time
    if isinstance(target_datetime, str):
        target_str = target_datetime.strip()
        try:
            # Handle YYYY-MM-DD
            parsed_date = datetime.strptime(target_str, "%Y-%m-%d")
            query_dt = datetime.combine(parsed_date.date(), time(23, 59, 59))
        except ValueError:
            try:
                # Handle YYYY-MM-DD HH:MM:SS
                query_dt = datetime.strptime(target_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Handle ISO format YYYY-MM-DDTHH:MM:SS
                    query_dt = datetime.fromisoformat(target_str)
                except ValueError:
                    return None, f"Invalid date format: {target_datetime}"
    elif isinstance(target_datetime, datetime):
        query_dt = target_datetime
    elif hasattr(target_datetime, 'year'):  # date object
        query_dt = datetime.combine(target_datetime, time(23, 59, 59))
    else:
        return None, "Unsupported date type"

    # Query latest status record at or before query_dt
    historical_record = (
        db_session.query(BatchStatusHistory)
        .filter(
            BatchStatusHistory.batch_id == batch.id,
            BatchStatusHistory.timestamp <= query_dt
        )
        .order_by(BatchStatusHistory.timestamp.desc(), BatchStatusHistory.id.desc())
        .first()
    )

    if not historical_record:
        # Batch had no history logged on or before target date
        return {
            'found': False,
            'batch_number': batch.batch_number,
            'target_date': query_dt.strftime('%Y-%m-%d'),
            'message': f"No manufacturing records exist for {batch.batch_number} on or before {query_dt.strftime('%d %B %Y')} (Batch was created later on {batch.created_at.strftime('%d %B %Y') if batch.created_at else 'unknown'})."
        }, None

    return {
        'found': True,
        'batch_number': batch.batch_number,
        'target_date': query_dt.strftime('%Y-%m-%d'),
        'formatted_date': query_dt.strftime('%d %B %Y'),
        'status': historical_record.status,
        'progress': historical_record.progress,
        'timestamp': historical_record.timestamp.isoformat(),
        'remarks': historical_record.remarks,
        'part_number': batch.part_number,
        'fastener_type': batch.fastener_type
    }, None

# Alias for backward compatibility
get_batch_status_at_date = get_batch_status_at_datetime
