from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class FastenerType(Base):
    __tablename__ = 'fastener_types'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Batch(Base):
    __tablename__ = 'batches'

    id = Column(Integer, primary_key=True)
    batch_number = Column(String(50), unique=True, nullable=False, index=True)
    fastener_type = Column(String(100), nullable=False)
    part_number = Column(String(100), nullable=False)
    material = Column(String(100), nullable=False)
    grade = Column(String(50), nullable=False)
    coating = Column(String(100), nullable=True, default='None')
    diameter = Column(String(50), nullable=False)
    length = Column(String(50), nullable=False)
    thread_type = Column(String(50), nullable=False)
    thread_pitch = Column(String(50), nullable=False)
    head_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    customer = Column(String(150), nullable=True)
    production_line = Column(String(50), nullable=False)
    machine = Column(String(50), nullable=False)
    operator = Column(String(100), nullable=False)
    current_status = Column(String(50), nullable=False, default='Scheduled')
    progress = Column(Integer, nullable=False, default=0)
    manufacturing_start = Column(DateTime, nullable=True)
    expected_completion = Column(DateTime, nullable=True)
    actual_completion = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    history_records = relationship(
        'BatchStatusHistory',
        backref='batch',
        cascade='all, delete-orphan',
        order_by='desc(BatchStatusHistory.timestamp)'
    )
    quality_inspections = relationship(
        'QualityInspection',
        backref='batch',
        cascade='all, delete-orphan',
        order_by='desc(QualityInspection.inspection_date)'
    )

    def to_dict(self, include_history=False, include_quality=False):
        data = {
            'id': self.id,
            'batch_number': self.batch_number,
            'fastener_type': self.fastener_type,
            'part_number': self.part_number,
            'material': self.material,
            'grade': self.grade,
            'coating': self.coating or 'None',
            'diameter': self.diameter,
            'length': self.length,
            'thread_type': self.thread_type,
            'thread_pitch': self.thread_pitch,
            'head_type': self.head_type,
            'quantity': self.quantity,
            'customer': self.customer or 'Standard Inventory',
            'production_line': self.production_line,
            'machine': self.machine,
            'operator': self.operator,
            'current_status': self.current_status,
            'progress': self.progress,
            'manufacturing_start': self.manufacturing_start.isoformat() if self.manufacturing_start else None,
            'expected_completion': self.expected_completion.isoformat() if self.expected_completion else None,
            'actual_completion': self.actual_completion.isoformat() if self.actual_completion else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_history:
            data['history'] = [h.to_dict() for h in self.history_records]
        if include_quality:
            data['quality'] = [q.to_dict() for q in self.quality_inspections]
            data['latest_quality'] = self.quality_inspections[0].to_dict() if self.quality_inspections else None
        return data


class BatchStatusHistory(Base):
    __tablename__ = 'batch_status_history'

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, nullable=False, default=datetime.now, index=True)
    remarks = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'status': self.status,
            'progress': self.progress,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'formatted_date': self.timestamp.strftime('%d %b %Y, %H:%M') if self.timestamp else '',
            'remarks': self.remarks or ''
        }


class QualityInspection(Base):
    __tablename__ = 'quality_inspections'

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    dimensional_result = Column(String(50), nullable=False, default='PASS')
    thread_result = Column(String(50), nullable=False, default='PASS')
    surface_result = Column(String(50), nullable=False, default='PASS')
    hardness = Column(String(50), nullable=True)
    tensile_strength = Column(String(50), nullable=True)
    overall_result = Column(String(50), nullable=False, default='PASSED')
    inspection_date = Column(DateTime, nullable=False, default=datetime.now)
    remarks = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'dimensional_result': self.dimensional_result,
            'thread_result': self.thread_result,
            'surface_result': self.surface_result,
            'hardness': self.hardness or 'N/A',
            'tensile_strength': self.tensile_strength or 'N/A',
            'overall_result': self.overall_result,
            'inspection_date': self.inspection_date.isoformat() if self.inspection_date else None,
            'formatted_date': self.inspection_date.strftime('%d %b %Y, %H:%M') if self.inspection_date else '',
            'remarks': self.remarks or ''
        }
