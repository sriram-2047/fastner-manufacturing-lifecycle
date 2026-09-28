import re
from datetime import datetime, date, timedelta
from sqlalchemy import func, or_
from database import db_session
from models import Batch, BatchStatusHistory, QualityInspection
from services.history_service import get_batch_status_at_datetime, get_batch_history
from ai.ollama import query_ollama, check_ollama_status
from ai.prompt import FASTENPRO_SYSTEM_PROMPT, build_prompt

def get_base_date():
    """
    Get current reference date for relative date arithmetic.
    Defaults to system date.
    """
    return datetime.now().date()

def extract_batch_number(question, default_batch=None):
    """
    Find batch identifier in the user's question.
    Matches: BATCH-0001, BATCH 0001, BATCH-1, BATCH1, etc.
    """
    q_lower = question.lower()

    # Check if question is clearly a multi-batch aggregate query
    if any(k in q_lower for k in [
        "which batches", "what batches", "all batches", "how many batches",
        "how many bolts", "how many nuts", "how many washers", "total bolts",
        "total batches", "batches are completed", "batches are manufacturing",
        "batches are on quality hold", "batches are on hold", "plant overview"
    ]):
        return None

    # Direct match for BATCH-XXXX or BATCH XXXX
    match = re.search(r'\b(BATCH[-_\s]?\d+)\b', question, re.IGNORECASE)
    if match:
        raw = match.group(1).upper().replace(' ', '-').replace('_', '-')
        parts = raw.split('-')
        if len(parts) == 2 and parts[1].isdigit():
            return f"BATCH-{int(parts[1]):04d}"
        return raw

    # Match numeric like "batch 1"
    match_b = re.search(r'\bbatch\s*(\d+)\b', question, re.IGNORECASE)
    if match_b:
        num = int(match_b.group(1))
        return f"BATCH-{num:04d}"

    # Part number match like HB-M10-050 or HN-M10-150
    match_part = re.search(r'\b([A-Z]{2,4}-[A-Z0-9]+-[A-Z0-9]+)\b', question, re.IGNORECASE)
    if match_part:
        part_no = match_part.group(1).upper()
        batch = db_session.query(Batch).filter(func.upper(Batch.part_number) == part_no).first()
        if batch:
            return batch.batch_number

    # If contextual reference like "this batch" or "the batch"
    if any(k in q_lower for k in [
        "this batch", "the batch", "what material was used", "what was the hardness",
        "what was the tensile strength", "what is the quantity", "what is the material grade",
        "what fastener is", "what happened yesterday", "what was the status two days ago",
        "did it pass", "show manufacturing history", "give me a complete summary"
    ]):
        if default_batch:
            return default_batch
        return "BATCH-0001"

    # If question asks about a specific date without naming a batch (e.g. "What was the status on September 25?")
    if re.search(r'\b(status\s+on\s+|happened\s+on\s+)\b', q_lower):
        if default_batch:
            return default_batch
        return "BATCH-0001"

    return default_batch

def extract_date_target(question):
    """
    Parse relative and absolute time expressions from question.
    Returns (target_date, date_label, is_historical).
    """
    q_lower = question.lower()
    base_date = get_base_date()

    # Relative expressions
    if "today" in q_lower or "currently" in q_lower or "now" in q_lower or "current" in q_lower:
        return base_date, "today", False

    if "yesterday" in q_lower:
        target = base_date - timedelta(days=1)
        return target, "yesterday", True

    if "two days ago" in q_lower or "2 days ago" in q_lower:
        target = base_date - timedelta(days=2)
        return target, "two days ago", True

    if "three days ago" in q_lower or "3 days ago" in q_lower:
        target = base_date - timedelta(days=3)
        return target, "three days ago", True

    if "four days ago" in q_lower or "4 days ago" in q_lower:
        target = base_date - timedelta(days=4)
        return target, "four days ago", True

    if "five days ago" in q_lower or "5 days ago" in q_lower:
        target = base_date - timedelta(days=5)
        return target, "five days ago", True

    if "last week" in q_lower:
        target = base_date - timedelta(days=7)
        return target, "last week", True

    # Explicit date matching (e.g. September 25, 25 Sep, 25th September 2026, 2026-09-25)
    iso_match = re.search(r'\b(202[0-9]-[0-1][0-9]-[0-3][0-9])\b', question)
    if iso_match:
        try:
            d = datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
            return d, d.strftime("%d %B %Y"), True
        except ValueError:
            pass

    # Match Month Day (e.g. September 25, Sept 25, September 25th, Sep 26 2026)
    month_match = re.search(
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(202\d))?\b',
        q_lower
    )
    if month_match:
        month_str = month_match.group(1)[:3]
        day = int(month_match.group(2))
        year = int(month_match.group(3)) if month_match.group(3) else base_date.year
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        try:
            d = date(year, month_map.get(month_str, 9), day)
            return d, d.strftime("%d %B %Y"), True
        except ValueError:
            pass

    # Match Day Month (e.g. 25 September, 25th of Sept, 26 Sep 2026)
    day_month_match = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*(202\d)?\b',
        q_lower
    )
    if day_month_match:
        day = int(day_month_match.group(1))
        month_str = day_month_match.group(2)[:3]
        year = int(day_month_match.group(3)) if day_month_match.group(3) else base_date.year
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        try:
            d = date(year, month_map.get(month_str, 9), day)
            return d, d.strftime("%d %B %Y"), True
        except ValueError:
            pass

    return None, None, False

MANUFACTURING_KEYWORDS = [
    'batch', 'fastener', 'bolt', 'nut', 'washer', 'screw', 'stud', 'rivet',
    'production', 'manufactur', 'quality', 'inspect', 'hardness', 'tensile',
    'defect', 'hold', 'line', 'machine', 'operator', 'material', 'grade',
    'coating', 'diameter', 'length', 'pitch', 'thread', 'head', 'quantity',
    'unit', 'progress', 'stage', 'schedule', 'complete', 'status', 'kpi',
    'report', 'plant', 'factory', 'specification', 'spec', 'pass', 'fail',
    'timeline', 'audit', 'history', 'cnc', 'customer', 'part', 'order'
]

def detect_intent(question, batch_number=None, is_historical=False):
    """
    Deterministic backend intent classification.
    """
    q_lower = question.lower()

    if any(k in q_lower for k in ['temperature', 'humidity', 'pressure', 'vibration', 'coolant', 'oil', 'rpm', 'kwh', 'db', 'cctv', 'sensor']):
        return 'UNSUPPORTED'

    # Check if question is outside the manufacturing domain
    is_manufacturing_related = any(kw in q_lower for kw in MANUFACTURING_KEYWORDS)
    if not is_manufacturing_related and not batch_number:
        return 'UNKNOWN'

    if is_historical:
        return 'HISTORICAL_STATUS'

    if any(k in q_lower for k in ['history', 'timeline', 'audit trail', 'what happened to']):
        return 'MANUFACTURING_HISTORY'

    if any(k in q_lower for k in ['quality', 'inspection', 'pass', 'hardness', 'tensile', 'defect', 'mrb', 'test result']):
        return 'QUALITY'

    if any(k in q_lower for k in ['material', 'grade', 'coating', 'diameter', 'length', 'pitch', 'thread', 'head type', 'quantity', 'how many units', 'customer', 'line', 'machine', 'operator', 'spec']):
        return 'BATCH_SPECIFICATION'

    if any(k in q_lower for k in ['which batches', 'total batches', 'how many bolts', 'how many batches', 'completed batches', 'manufacturing batches', 'quality hold batches', 'plant overview']):
        return 'MULTI_BATCH'

    if any(k in q_lower for k in ['status', 'stage', 'progress', 'where is', 'current state']):
        return 'CURRENT_STATUS'

    if batch_number:
        return 'GENERAL_BATCH_QUERY'

    return 'UNKNOWN'

def build_database_context(question, batch_number=None, target_date=None, is_historical=False):
    """
    Retrieve structured facts from SQLite via SQLAlchemy to ground the AI response.
    Returns (context_text, metadata_dict).
    """
    context_lines = []
    metadata = {
        'batch_number': batch_number,
        'is_historical': is_historical,
        'target_date': str(target_date) if target_date else None,
        'source': 'database'
    }

    q_lower = question.lower()
    intent = detect_intent(question, batch_number=batch_number, is_historical=is_historical)
    metadata['intent'] = intent

    # Check for unsupported attributes (Hallucination prevention)
    unsupported_topics = [
        'temperature', 'humidity', 'pressure sensor', 'vibration sensor',
        'coolant level', 'supplier oil', 'oil brand', 'spindle speed rpm',
        'electricity consumption', 'kwh', 'sound level db', 'cctv', 'sensor'
    ]
    for topic in unsupported_topics:
        if topic in q_lower:
            context_lines.append(f"UNSUPPORTED RECORD: Sensor or equipment parameter '{topic}' is not tracked in the manufacturing database.")
            metadata['unsupported_attribute'] = topic
            return "\n".join(context_lines), metadata

    if intent == 'UNKNOWN':
        context_lines.append("GENERAL NOTICE: The question is unrelated to manufacturing batches, production operations, quality records, or product specifications.")
        return "\n".join(context_lines), metadata

    # Case 1: Specific Batch Query
    if batch_number:
        batch = db_session.query(Batch).filter(
            func.upper(Batch.batch_number) == batch_number.upper()
        ).first()

        if not batch:
            context_lines.append(f"BATCH RECORD: Batch '{batch_number}' was not found in the manufacturing database.")
            metadata['batch_found'] = False
            return "\n".join(context_lines), metadata

        metadata['batch_found'] = True
        metadata['fastener_type'] = batch.fastener_type
        metadata['current_status'] = batch.current_status
        metadata['progress'] = batch.progress

        # 1A. Historical Status Query: ONLY SEND HISTORICAL CONTEXT
        if is_historical and target_date:
            hist_result, err = get_batch_status_at_datetime(batch.id, target_date)
            if hist_result and hist_result.get('found'):
                metadata['historical_status'] = hist_result['status']
                metadata['historical_progress'] = hist_result['progress']
                context_lines.append(
                    f"HISTORICAL RECORD ON {hist_result['formatted_date']} (TARGET DATE: {hist_result['target_date']}):\n"
                    f"- Batch: {batch.batch_number} ({batch.fastener_type}, Part #{batch.part_number})\n"
                    f"- Historical Status on that date: {hist_result['status']}\n"
                    f"- Production Progress on that date: {hist_result['progress']}%\n"
                    f"- Logged Timestamp: {hist_result['timestamp']}\n"
                    f"- Status Remarks: {hist_result['remarks']}\n"
                    f"CRITICAL: The historical status on {hist_result['formatted_date']} was '{hist_result['status']}'. Do NOT state its current status."
                )
            else:
                context_lines.append(
                    f"HISTORICAL RECORD ON {target_date.strftime('%d %B %Y') if isinstance(target_date, date) else target_date}:\n"
                    f"- No manufacturing activity was logged on or before this date for {batch.batch_number}.\n"
                    f"- Batch creation date: {batch.created_at.strftime('%d %B %Y') if batch.created_at else 'Unknown'}."
                )
            return "\n".join(context_lines), metadata

        # 1B. Manufacturing History Timeline Query
        if intent == 'MANUFACTURING_HISTORY':
            context_lines.append(f"MANUFACTURING AUDIT TRAIL FOR {batch.batch_number} ({batch.fastener_type}):")
            if batch.history_records:
                for h in sorted(batch.history_records, key=lambda x: x.timestamp):
                    context_lines.append(f"- [{h.timestamp.strftime('%d %b %Y %H:%M')}] Stage: {h.status} ({h.progress}%) — {h.remarks}")
            else:
                context_lines.append("- No status history records found.")
            return "\n".join(context_lines), metadata

        # 1C. Quality Inspection Query
        if intent == 'QUALITY':
            if batch.quality_inspections:
                qi = batch.quality_inspections[0]
                context_lines.append(
                    f"QUALITY INSPECTION REPORT FOR {batch.batch_number}:\n"
                    f"- Dimensional Inspection: {qi.dimensional_result}\n"
                    f"- Thread Form / Pitch Inspection: {qi.thread_result}\n"
                    f"- Surface Coating Inspection: {qi.surface_result}\n"
                    f"- Core Hardness: {qi.hardness or 'N/A'}\n"
                    f"- Tensile Strength: {qi.tensile_strength or 'N/A'}\n"
                    f"- Overall Quality Result: {qi.overall_result}\n"
                    f"- Inspection Date: {qi.inspection_date.strftime('%d %B %Y') if qi.inspection_date else 'N/A'}\n"
                    f"- QA Remarks: {qi.remarks or 'Standard inspection passed.'}"
                )
            else:
                context_lines.append(f"QUALITY INSPECTION: No quality inspection report recorded yet for {batch.batch_number}.")
            return "\n".join(context_lines), metadata

        # 1D. Specification or General Batch Query
        context_lines.append(
            f"CURRENT BATCH DETAILS:\n"
            f"- Batch Number: {batch.batch_number}\n"
            f"- Fastener Type: {batch.fastener_type}\n"
            f"- Part Number: {batch.part_number}\n"
            f"- Material: {batch.material}\n"
            f"- Material Grade: {batch.grade}\n"
            f"- Surface Coating: {batch.coating or 'None'}\n"
            f"- Dimensions: Diameter {batch.diameter}, Length {batch.length}\n"
            f"- Thread Specifications: Type {batch.thread_type}, Pitch {batch.thread_pitch}\n"
            f"- Head Type: {batch.head_type}\n"
            f"- Quantity: {batch.quantity:,} units\n"
            f"- Customer: {batch.customer or 'Standard Inventory'}\n"
            f"- Production Line: {batch.production_line}\n"
            f"- Machine Station: {batch.machine}\n"
            f"- Lead Operator: {batch.operator}\n"
            f"- Current Status: {batch.current_status}\n"
            f"- Current Progress: {batch.progress}%\n"
            f"- Manufacturing Start: {batch.manufacturing_start.strftime('%d %B %Y %H:%M') if batch.manufacturing_start else 'Not started'}\n"
            f"- Expected Completion: {batch.expected_completion.strftime('%d %B %Y %H:%M') if batch.expected_completion else 'TBD'}\n"
            f"- Actual Completion: {batch.actual_completion.strftime('%d %B %Y %H:%M') if batch.actual_completion else 'Incomplete (In Progress)'}"
        )

        if batch.quality_inspections:
            qi = batch.quality_inspections[0]
            context_lines.append(
                f"\nLATEST QUALITY INSPECTION:\n"
                f"- Overall Result: {qi.overall_result} (Dimensional: {qi.dimensional_result}, Thread: {qi.thread_result}, Surface: {qi.surface_result})\n"
                f"- Hardness: {qi.hardness}, Tensile Strength: {qi.tensile_strength}"
            )

    # Case 2: Multi-Batch / Aggregate Inquiries
    else:
        if "completed" in q_lower:
            comp_batches = db_session.query(Batch).filter(Batch.current_status == 'Completed').all()
            context_lines.append(f"COMPLETED BATCHES ({len(comp_batches)} total):")
            for b in comp_batches:
                context_lines.append(f"- {b.batch_number}: {b.fastener_type} ({b.part_number}), Qty: {b.quantity:,}, Completed: {b.actual_completion.strftime('%d %b %Y') if b.actual_completion else 'Yes'}")

        elif "quality hold" in q_lower or "hold" in q_lower or "failed" in q_lower:
            hold_batches = db_session.query(Batch).filter(Batch.current_status == 'Quality Hold').all()
            context_lines.append(f"QUALITY HOLD BATCHES ({len(hold_batches)} total):")
            for b in hold_batches:
                context_lines.append(f"- {b.batch_number}: {b.fastener_type} ({b.part_number}), Line: {b.production_line}, Machine: {b.machine}, Progress: {b.progress}%")

        elif "manufacturing" in q_lower or "in production" in q_lower or "active" in q_lower:
            mfg_batches = db_session.query(Batch).filter(Batch.current_status == 'Manufacturing').all()
            context_lines.append(f"ACTIVE MANUFACTURING BATCHES ({len(mfg_batches)} total):")
            for b in mfg_batches:
                context_lines.append(f"- {b.batch_number}: {b.fastener_type} ({b.part_number}), Qty: {b.quantity:,}, Line: {b.production_line}, Machine: {b.machine}, Progress: {b.progress}%")

        elif "how many" in q_lower or "quantity" in q_lower or "total" in q_lower or "count" in q_lower or "bolts" in q_lower:
            total_b = db_session.query(func.count(Batch.id)).scalar() or 0
            total_u = db_session.query(func.sum(Batch.quantity)).scalar() or 0
            mfg_count = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Manufacturing').scalar() or 0
            comp_count = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Completed').scalar() or 0
            hold_count = db_session.query(func.count(Batch.id)).filter(Batch.current_status == 'Quality Hold').scalar() or 0
            
            # Bolt quantity specifically
            bolt_units = db_session.query(func.sum(Batch.quantity)).filter(Batch.fastener_type.ilike('%Bolt%')).scalar() or 0

            context_lines.append(
                f"ENTERPRISE PRODUCTION METRICS:\n"
                f"- Total Batches: {total_b}\n"
                f"- Total Units Across All Batches: {total_u:,}\n"
                f"- Total Bolt Units: {bolt_units:,}\n"
                f"- Batches in Active Manufacturing: {mfg_count}\n"
                f"- Batches Completed: {comp_count}\n"
                f"- Batches on Quality Hold: {hold_count}"
            )
        else:
            all_batches = db_session.query(Batch).order_by(Batch.batch_number).all()
            context_lines.append(f"MANUFACTURING OVERVIEW ({len(all_batches)} batches in database):")
            for b in all_batches[:10]:
                context_lines.append(f"- {b.batch_number}: {b.fastener_type}, Status: {b.current_status} ({b.progress}%), Line: {b.production_line}, Qty: {b.quantity:,}")

    return "\n".join(context_lines), metadata

def generate_grounded_fallback_answer(question, context_str, metadata):
    """
    Deterministic rule-based response generator strictly grounded in the database context.
    Used when Ollama is offline or for guaranteed factual fallback.
    """
    q_lower = question.lower()

    # Unsupported check (Hallucination prevention)
    if 'unsupported_attribute' in metadata or metadata.get('intent') == 'UNSUPPORTED':
        return "The requested information is not available in the manufacturing records."

    # Nonexistent batch
    if metadata.get('batch_number') and metadata.get('batch_found') is False:
        return f"Batch {metadata['batch_number']} was not found in the manufacturing database."

    # Multi-batch queries take priority if batch_number is None or question is aggregate
    if not metadata.get('batch_number'):
        if "completed" in q_lower:
            comp = db_session.query(Batch).filter(Batch.current_status == 'Completed').all()
            names = [f"{b.batch_number} ({b.fastener_type}, Qty: {b.quantity:,})" for b in comp]
            return f"There are {len(comp)} completed batches in the system: " + ", ".join(names) + "."

        if "quality hold" in q_lower or "hold" in q_lower:
            holds = db_session.query(Batch).filter(Batch.current_status == 'Quality Hold').all()
            if holds:
                names = [f"{b.batch_number} ({b.fastener_type}, Line: {b.production_line})" for b in holds]
                return f"Currently {len(holds)} batch is on Quality Hold: " + ", ".join(names) + "."
            return "There are currently no batches on Quality Hold."

        if "manufacturing" in q_lower or "active" in q_lower or "in progress" in q_lower:
            mfg = db_session.query(Batch).filter(Batch.current_status == 'Manufacturing').all()
            names = [f"{b.batch_number} ({b.fastener_type}, {b.progress}%)" for b in mfg]
            return f"Currently {len(mfg)} batches are in Manufacturing: " + ", ".join(names) + "."

        if "how many bolts" in q_lower or "bolts" in q_lower:
            bolt_qty = db_session.query(func.sum(Batch.quantity)).filter(Batch.fastener_type.ilike('%Bolt%')).scalar() or 0
            bolt_batches = db_session.query(Batch).filter(Batch.fastener_type.ilike('%Bolt%')).all()
            return f"A total of {bolt_qty:,} bolts are recorded across {len(bolt_batches)} bolt batches in the database."

    # Specific batch queries
    batch_no = metadata.get('batch_number')
    if batch_no:
        batch = db_session.query(Batch).filter(func.upper(Batch.batch_number) == batch_no.upper()).first()
        if batch:
            # 1. Historical query
            if metadata.get('is_historical') and metadata.get('target_date'):
                hist = metadata.get('historical_status')
                prog = metadata.get('historical_progress')
                target_str = metadata.get('target_date')
                try:
                    d_obj = datetime.strptime(target_str, "%Y-%m-%d")
                    fmt_d = d_obj.strftime("%B %d, %Y")
                except Exception:
                    fmt_d = target_str

                if hist:
                    return f"On {fmt_d}, {batch.batch_number} was in the {hist} stage with {prog}% progress."
                else:
                    return f"On {fmt_d}, no manufacturing activity was recorded for {batch.batch_number} (batch was created on {batch.created_at.strftime('%B %d, %Y') if batch.created_at else 'a later date'})."

            # 2. Quality query
            if metadata.get('intent') == 'QUALITY' or any(k in q_lower for k in ["quality", "inspection", "pass", "hardness", "tensile"]):
                if batch.quality_inspections:
                    qi = batch.quality_inspections[0]
                    if "hardness" in q_lower and "tensile" not in q_lower:
                        return f"The hardness for {batch.batch_number} is {qi.hardness}."
                    if "tensile" in q_lower and "hardness" not in q_lower:
                        return f"The tensile strength for {batch.batch_number} is {qi.tensile_strength}."
                    
                    if qi.overall_result.upper() == 'PASSED':
                        return f"{batch.batch_number} passed quality inspection. Dimensional, thread, and surface inspections passed, with an overall result of PASSED (Hardness: {qi.hardness}, Tensile Strength: {qi.tensile_strength})."
                    elif qi.overall_result.upper() == 'HOLD':
                        return f"{batch.batch_number} is on QUALITY HOLD. Dimensional inspection: {qi.dimensional_result}, Thread inspection: {qi.thread_result}, Surface: {qi.surface_result}. Remarks: {qi.remarks}"
                    else:
                        return f"{batch.batch_number} quality inspection status is {qi.overall_result} (Dimensional: {qi.dimensional_result}, Thread: {qi.thread_result}, Surface: {qi.surface_result})."
                else:
                    return f"There is no quality inspection record currently available for {batch.batch_number}."

            # 3. Manufacturing History / Timeline
            if metadata.get('intent') == 'MANUFACTURING_HISTORY' or "history" in q_lower or "timeline" in q_lower:
                history_entries = get_batch_history(batch.id)
                lines = [f"Manufacturing history for {batch.batch_number}:"]
                for h in sorted(history_entries, key=lambda x: x['timestamp']):
                    lines.append(f"- {h['formatted_date']}: {h['status']} ({h['progress']}%) — {h['remarks']}")
                return "\n".join(lines)

            # 4. Current Status (Prioritized for status/stage/progress queries)
            if "status" in q_lower or "stage" in q_lower or "progress" in q_lower:
                if batch.current_status == 'Completed':
                    return f"{batch.batch_number} is currently Completed (100% progress)."
                return f"{batch.batch_number} is currently in the {batch.current_status} stage with {batch.progress}% completion."

            # 5. Material & Grade
            if "material" in q_lower or "grade" in q_lower:
                if "grade" in q_lower and "material" not in q_lower:
                    return f"The material grade for {batch.batch_number} is {batch.grade}."
                return f"{batch.batch_number} is manufactured from {batch.material} (Grade {batch.grade}) with {batch.coating or 'standard'} coating."

            # 6. Machine & Operator / Production Line
            if "machine" in q_lower or "line" in q_lower or "operator" in q_lower:
                return f"{batch.batch_number} is produced on {batch.production_line} using machine {batch.machine}, operated by {batch.operator}."

            # 7. Dimensions & Specifications
            if "diameter" in q_lower or "length" in q_lower or "pitch" in q_lower or "thread" in q_lower or "head" in q_lower or "coating" in q_lower:
                return f"{batch.batch_number} specifications: {batch.fastener_type} ({batch.part_number}), Diameter: {batch.diameter}, Length: {batch.length}, Thread: {batch.thread_type} (Pitch: {batch.thread_pitch}), Head: {batch.head_type}, Coating: {batch.coating or 'None'}."

            # 8. Quantity
            if "quantity" in q_lower or "how many" in q_lower or "units" in q_lower:
                return f"The production quantity for {batch.batch_number} is {batch.quantity:,} units."

            # 9. Fastener Type & Part Number
            if "fastener" in q_lower or "product" in q_lower or "part" in q_lower or "item" in q_lower:
                return f"{batch.batch_number} is a {batch.fastener_type} (Part Number: {batch.part_number}, Diameter: {batch.diameter}, Length: {batch.length})."

            # 10. Start & Completion Dates / Duration
            if "start" in q_lower or "when did" in q_lower:
                if batch.manufacturing_start:
                    return f"{batch.batch_number} started manufacturing on {batch.manufacturing_start.strftime('%B %d, %Y at %H:%M UTC')}."
                return f"{batch.batch_number} has not started manufacturing yet."

            if "completed" in q_lower or "finish" in q_lower or "duration" in q_lower or "how long" in q_lower:
                if batch.actual_completion:
                    duration_str = ""
                    if batch.manufacturing_start:
                        diff = batch.actual_completion - batch.manufacturing_start
                        duration_str = f" (Duration: {diff.days} days, {diff.seconds // 3600} hours)"
                    return f"{batch.batch_number} was completed on {batch.actual_completion.strftime('%B %d, %Y at %H:%M UTC')}{duration_str}."
                return f"{batch.batch_number} is not completed yet; expected completion is {batch.expected_completion.strftime('%B %d, %Y') if batch.expected_completion else 'TBD'}."

            # 11. Full Summary
            if "summary" in q_lower or "details" in q_lower or "tell me about" in q_lower:
                return (
                    f"Summary for {batch.batch_number}:\n"
                    f"• Product: {batch.fastener_type} ({batch.part_number})\n"
                    f"• Specifications: {batch.material} Grade {batch.grade}, {batch.diameter} x {batch.length}\n"
                    f"• Quantity: {batch.quantity:,} units for {batch.customer or 'Stock'}\n"
                    f"• Current Status: {batch.current_status} ({batch.progress}%)\n"
                    f"• Production: {batch.production_line} / {batch.machine} ({batch.operator})\n"
                    f"• Start: {batch.manufacturing_start.strftime('%d %b %Y') if batch.manufacturing_start else 'N/A'}, Expected: {batch.expected_completion.strftime('%d %b %Y') if batch.expected_completion else 'N/A'}"
                )

    # General unknown questions fallback
    if metadata.get('intent') == 'UNKNOWN':
        return "I can answer questions about FASTENPRO manufacturing batches, production, quality inspections, specifications, and historical status records."

    # Fallback to general context summary
    return f"Based on manufacturing records:\n{context_str}"

def process_ai_query(question, current_context_batch=None):
    """
    Full AI Copilot Pipeline
    """
    if not question or not question.strip():
        return {
            'success': False,
            'error': 'Please provide a valid question.'
        }

    clean_question = question.strip()

    # Step 1 & 2: Entity & Date Extraction
    batch_number = extract_batch_number(clean_question, default_batch=current_context_batch)
    target_date, date_label, is_historical = extract_date_target(clean_question)

    # Step 3: Database Grounding Context
    context_str, metadata = build_database_context(
        clean_question,
        batch_number=batch_number,
        target_date=target_date,
        is_historical=is_historical
    )

    # Nonexistent batch check: Return cleanly without asking Ollama
    if batch_number and metadata.get('batch_found') is False:
        not_found_ans = f"Batch {batch_number} was not found."
        response_data = {
            'answer': not_found_ans,
            'batch_number': batch_number,
            'grounded': True,
            'historical': False,
            'date': None,
            'source': 'database',
            'engine': 'database'
        }
        return {
            'success': True,
            'data': response_data,
            **response_data
        }

    # Step 4: Ollama Prompt Generation
    user_prompt = build_prompt(context_str, clean_question)

    # Step 5: Execute Ollama Query
    ollama_response, ollama_err = query_ollama(user_prompt, FASTENPRO_SYSTEM_PROMPT)

    answer_text = None
    ai_engine = "ollama"
    source_val = "batch_status_history" if is_historical else "database"

    if ollama_response and len(ollama_response.strip()) > 0:
        answer_text = ollama_response.strip()
    else:
        # Graceful fallback: use deterministic grounded response generator
        answer_text = generate_grounded_fallback_answer(clean_question, context_str, metadata)
        ai_engine = "grounded_db_engine"
        source_val = "batch_status_history" if is_historical else "database_fallback"

    response_data = {
        'answer': answer_text,
        'batch_number': batch_number,
        'grounded': True,
        'historical': is_historical,
        'date': str(target_date) if target_date else None,
        'source': source_val,
        'engine': ai_engine,
        'ollama_status': 'connected' if ollama_response else 'offline'
    }

    return {
        'success': True,
        'data': response_data,
        **response_data
    }

