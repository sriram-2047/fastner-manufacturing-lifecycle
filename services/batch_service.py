from datetime import datetime
from sqlalchemy import func, or_
from database import db_session
from models import Batch, BatchStatusHistory, QualityInspection

LIFECYCLE_STAGES = [
    {"status": "Scheduled", "progress": 0, "default_remarks": "Batch scheduled for production."},
    {"status": "Material Preparation", "progress": 10, "default_remarks": "Raw material issued and prepared."},
    {"status": "Manufacturing", "progress": 65, "default_remarks": "Machining and cold forming in progress."},
    {"status": "Quality Inspection", "progress": 90, "default_remarks": "Batch moved to QA lab for dimension and hardness testing."},
    {"status": "Completed", "progress": 100, "default_remarks": "Batch completed successfully and packaged for dispatch."}
]

def get_all_batches(search=None, status=None, line=None, material=None):
    query = db_session.query(Batch)
    
    if search:
        search_term = f"%{search.strip().upper()}%"
        query = query.filter(
            or_(
                Batch.batch_number.ilike(search_term),
                Batch.fastener_type.ilike(search_term),
                Batch.part_number.ilike(search_term),
                Batch.customer.ilike(search_term),
                Batch.material.ilike(search_term),
                Batch.machine.ilike(search_term),
                Batch.operator.ilike(search_term)
            )
        )
    
    if status and status != 'ALL':
        query = query.filter(Batch.current_status == status)
        
    if line and line != 'ALL':
        query = query.filter(Batch.production_line == line)

    if material and material != 'ALL':
        query = query.filter(Batch.material.ilike(f"%{material}%"))

    batches = query.order_by(Batch.id.asc()).all()
    return [b.to_dict(include_history=False, include_quality=False) for b in batches]

def get_batch_by_number(batch_number, include_relations=True):
    if not batch_number:
        return None
    normalized_number = batch_number.strip().upper()
    batch = db_session.query(Batch).filter(
        func.upper(Batch.batch_number) == normalized_number
    ).first()
    
    if not batch:
        return None
        
    return batch.to_dict(include_history=include_relations, include_quality=include_relations)

def get_dashboard_kpis():
    total_batches = db_session.query(func.count(Batch.id)).scalar() or 0
    active_manufacturing = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Manufacturing').scalar() or 0
    completed = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Completed').scalar() or 0
    quality_hold = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Quality Hold').scalar() or 0
    material_prep = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Material Preparation').scalar() or 0
    quality_inspection = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Quality Inspection').scalar() or 0
    scheduled = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Scheduled').scalar() or 0

    # Total units manufactured across completed and active batches
    total_units = db_session.query(func.sum(Batch.quantity)).scalar() or 0
    completed_units = db_session.query(func.sum(Batch.quantity)).filter(Batch.current_status == 'Completed').scalar() or 0

    # Recent batches
    recent_batches = db_session.query(Batch).order_by(Batch.updated_at.desc(), Batch.id.desc()).limit(6).all()

    # Fastener distribution
    type_distribution = db_session.query(
        Batch.fastener_type,
        func.count(Batch.id).label('count'),
        func.sum(Batch.quantity).label('total_units')
    ).group_by(Batch.fastener_type).all()

    return {
        'total_batches': total_batches,
        'active_manufacturing': active_manufacturing,
        'completed': completed,
        'quality_hold': quality_hold,
        'material_prep': material_prep,
        'quality_inspection': quality_inspection,
        'scheduled': scheduled,
        'total_units': total_units,
        'completed_units': completed_units,
        'recent_batches': [b.to_dict() for b in recent_batches],
        'distribution': [
            {'fastener_type': t[0], 'count': t[1], 'total_units': t[2] or 0}
            for t in type_distribution
        ]
    }

def advance_batch(batch_number, custom_remarks=None):
    if not batch_number:
        return None, "Invalid batch number", 400
        
    normalized = batch_number.strip().upper()
    batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == normalized).first()
    
    if not batch:
        return None, f"Batch {normalized} was not found.", 404

    current = batch.current_status
    next_status = None
    next_progress = 0
    remarks = custom_remarks or ""

    if current == 'Scheduled':
        next_status = 'Material Preparation'
        next_progress = 10
        remarks = remarks or "Raw material issued for cutting and preparation."
        if not batch.manufacturing_start:
            batch.manufacturing_start = datetime.now()
    elif current == 'Material Preparation':
        next_status = 'Manufacturing'
        next_progress = 65
        remarks = remarks or "Machining operations started."
        if not batch.manufacturing_start:
            batch.manufacturing_start = datetime.now()
    elif current == 'Manufacturing':
        next_status = 'Quality Inspection'
        next_progress = 90
        remarks = remarks or "Production completed; routed to Quality Assurance lab."
    elif current == 'Quality Inspection':
        next_status = 'Completed'
        next_progress = 100
        remarks = remarks or "Batch passed quality inspection and marked completed."
        batch.actual_completion = datetime.now()
    elif current == 'Quality Hold':
        next_status = 'Quality Inspection'
        next_progress = 90
        remarks = remarks or "Rework completed. Re-submitted to Quality Inspection."
    elif current == 'Completed':
        return None, f"Invalid lifecycle transition from Completed.", 409
    else:
        return None, f"Cannot advance batch from current status: {current}", 409

    try:
        now = datetime.now()
        batch.current_status = next_status
        batch.progress = next_progress
        batch.updated_at = now

        # NEVER OVERWRITE: ALWAYS CREATE A NEW HISTORY RECORD
        history_entry = BatchStatusHistory(
            batch_id=batch.id,
            status=next_status,
            progress=next_progress,
            timestamp=now,
            remarks=remarks
        )
        db_session.add(history_entry)
        db_session.commit()

        batch_dict = batch.to_dict(include_history=True, include_quality=True)
        return {
            'batch': batch_dict,
            'history_entry': history_entry.to_dict(),
            **batch_dict
        }, None, 200
    except Exception as e:
        db_session.rollback()
        return None, f"Database transaction failed: {str(e)}", 500

def complete_batch(batch_number, custom_remarks=None):
    if not batch_number:
        return None, "Invalid batch number", 400
        
    normalized = batch_number.strip().upper()
    batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == normalized).first()
    
    if not batch:
        return None, f"Batch {normalized} was not found.", 404

    # Idempotent check: If already completed with 100% progress, do not add duplicate records
    if batch.current_status == 'Completed' and batch.progress == 100:
        batch_dict = batch.to_dict(include_history=True, include_quality=True)
        return {
            'batch': batch_dict,
            'history_entry': batch.history_records[0].to_dict() if batch.history_records else None,
            **batch_dict
        }, "Batch is already completed.", 200

    try:
        now = datetime.now()
        batch.current_status = 'Completed'
        batch.progress = 100
        batch.actual_completion = now
        batch.updated_at = now

        remarks = custom_remarks or "Batch completed successfully."

        # Create new immutable status history record
        history_entry = BatchStatusHistory(
            batch_id=batch.id,
            status="Completed",
            progress=100,
            timestamp=now,
            remarks=remarks
        )
        db_session.add(history_entry)
        db_session.commit()

        batch_dict = batch.to_dict(include_history=True, include_quality=True)
        return {
            'batch': batch_dict,
            'history_entry': history_entry.to_dict(),
            **batch_dict
        }, None, 200
    except Exception as e:
        db_session.rollback()
        return None, f"Database transaction failed: {str(e)}", 500
