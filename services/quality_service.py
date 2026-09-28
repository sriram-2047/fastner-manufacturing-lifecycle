from sqlalchemy import func
from database import db_session
from models import Batch, QualityInspection

def get_quality_overview():
    """
    Compute quality assurance KPIs and fetch all inspection reports.
    """
    # Count metrics
    passed_count = db_session.query(func.count(QualityInspection.id)).filter(
        func.upper(QualityInspection.overall_result) == 'PASSED'
    ).scalar() or 0

    pending_count = db_session.query(func.count(QualityInspection.id)).filter(
        func.upper(QualityInspection.overall_result) == 'PENDING'
    ).scalar() or 0

    hold_count = db_session.query(func.count(QualityInspection.id)).filter(
        func.upper(QualityInspection.overall_result) == 'HOLD'
    ).scalar() or 0

    failed_count = db_session.query(func.count(QualityInspection.id)).filter(
        func.upper(QualityInspection.overall_result) == 'FAILED'
    ).scalar() or 0

    # Also count batches that are in Quality Inspection status but might not have an inspection record yet
    batches_in_qi = db_session.query(func.count(Batch.id)).filter(
        Batch.current_status == 'Quality Inspection'
    ).scalar() or 0

    batches_on_hold = db_session.query(func.count(Batch.id)).filter(
        Batch.current_status == 'Quality Hold'
    ).scalar() or 0

    # Join QualityInspection with Batch
    inspections = (
        db_session.query(QualityInspection, Batch)
        .join(Batch, QualityInspection.batch_id == Batch.id)
        .order_by(QualityInspection.inspection_date.desc(), QualityInspection.id.desc())
        .all()
    )

    inspection_list = []
    for qi, batch in inspections:
        item = qi.to_dict()
        item['batch_number'] = batch.batch_number
        item['fastener_type'] = batch.fastener_type
        item['part_number'] = batch.part_number
        item['material'] = batch.material
        item['grade'] = batch.grade
        item['quantity'] = batch.quantity
        item['production_line'] = batch.production_line
        item['batch_status'] = batch.current_status
        inspection_list.append(item)

    return {
        'passed': passed_count,
        'pending': max(pending_count, batches_in_qi),
        'hold': max(hold_count, batches_on_hold),
        'failed': failed_count,
        'inspections': inspection_list
    }

def get_batch_quality(batch_identifier):
    """
    Fetch quality inspection data for a specific batch.
    """
    if isinstance(batch_identifier, int):
        batch = db_session.query(Batch).filter(Batch.id == batch_identifier).first()
    else:
        normalized = str(batch_identifier).strip().upper()
        batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == normalized).first()

    if not batch:
        return None

    inspections = db_session.query(QualityInspection).filter(
        QualityInspection.batch_id == batch.id
    ).order_by(QualityInspection.inspection_date.desc()).all()

    return {
        'batch_number': batch.batch_number,
        'fastener_type': batch.fastener_type,
        'part_number': batch.part_number,
        'inspections': [i.to_dict() for i in inspections],
        'latest_inspection': inspections[0].to_dict() if inspections else None
    }
