import os
import sys
from datetime import datetime, timedelta
from database import db_session, init_db, engine, Base
from models import Batch, BatchStatusHistory, QualityInspection, FastenerType

def seed_database(force=False):
    init_db()
    
    existing_batches = db_session.query(Batch).count()
    if existing_batches > 0 and not force:
        print(f"Database already contains {existing_batches} batches. Use force=True or run with --force to reseed.")
        return

    if force:
        print("Clearing existing data...")
        db_session.query(QualityInspection).delete()
        db_session.query(BatchStatusHistory).delete()
        db_session.query(Batch).delete()
        db_session.query(FastenerType).delete()
        db_session.commit()

    print("Seeding Fastener Types...")
    fastener_types = [
        FastenerType(name="Hex Bolt", description="Heavy-duty hexagonal head threaded bolt for structural and mechanical joints."),
        FastenerType(name="Hex Nut", description="Internally threaded hexagonal fastener paired with bolts or studs."),
        FastenerType(name="Washer", description="Smooth distribution plate used to distribute fastener load evenly."),
        FastenerType(name="Socket Head Cap Screw", description="High-strength cylindrical head fastener driven by internal hex key."),
        FastenerType(name="Stud", description="Full or double-end threaded rod used in flanges and high-pressure assemblies."),
        FastenerType(name="Self-Tapping Screw", description="Thread-forming screw for sheet metal and composite materials."),
        FastenerType(name="Rivet", description="Permanent mechanical fastener with upset head for aerospace and sheet joinery."),
        FastenerType(name="Anchor Bolt", description="Heavy embedment bolt for anchoring structural steel to concrete foundations."),
        FastenerType(name="Flange Bolt", description="Integral circular washer-flange under hex head for increased bearing area."),
        FastenerType(name="Carriage Bolt", description="Round domed head with square neck designed for wood and structural assemblies."),
        FastenerType(name="Eye Bolt", description="Threaded shank with looped ring head for lifting and rigging applications.")
    ]
    db_session.add_all(fastener_types)
    db_session.commit()

    print("Seeding Manufacturing Batches...")

    # BATCH-0001 (Primary Demonstration Batch)
    batch_1 = Batch(
        batch_number="BATCH-0001",
        fastener_type="Hex Bolt",
        part_number="HB-M10-050",
        material="Carbon Steel",
        grade="8.8",
        coating="Zinc Plated",
        diameter="M10",
        length="50 mm",
        thread_type="Metric",
        thread_pitch="1.5 mm",
        head_type="Hexagonal",
        quantity=10000,
        customer="Apex Automotive Corp",
        production_line="LINE-02",
        machine="CNC-04",
        operator="Operator-07",
        current_status="Manufacturing",
        progress=65,
        manufacturing_start=datetime(2026, 9, 25, 8, 0, 0),
        expected_completion=datetime(2026, 9, 27, 18, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 25, 7, 30, 0),
        updated_at=datetime(2026, 9, 26, 16, 30, 0)
    )
    db_session.add(batch_1)
    db_session.flush()

    # BATCH-0001 History
    batch_1_history = [
        BatchStatusHistory(
            batch_id=batch_1.id,
            status="Material Preparation",
            progress=10,
            timestamp=datetime(2026, 9, 25, 8, 30, 0),
            remarks="Raw material issued."
        ),
        BatchStatusHistory(
            batch_id=batch_1.id,
            status="Manufacturing",
            progress=20,
            timestamp=datetime(2026, 9, 25, 14, 0, 0),
            remarks="Manufacturing started."
        ),
        BatchStatusHistory(
            batch_id=batch_1.id,
            status="Manufacturing",
            progress=65,
            timestamp=datetime(2026, 9, 26, 16, 30, 0),
            remarks="Production reached 65%."
        )
    ]
    db_session.add_all(batch_1_history)

    # BATCH-0001 Quality Inspection Record
    batch_1_quality = QualityInspection(
        batch_id=batch_1.id,
        dimensional_result="PASS",
        thread_result="PASS",
        surface_result="PASS",
        hardness="32 HRC",
        tensile_strength="800 MPa",
        overall_result="PASSED",
        inspection_date=datetime(2026, 9, 27, 14, 0, 0),
        remarks="All critical dimensions, thread pitch, and surface coating meet ISO 898-1 standards."
    )
    db_session.add(batch_1_quality)

    # BATCH-0002
    batch_2 = Batch(
        batch_number="BATCH-0002",
        fastener_type="Hex Nut",
        part_number="HN-M10-150",
        material="Carbon Steel",
        grade="8.8",
        coating="Zinc Plated",
        diameter="M10",
        length="8.4 mm",
        thread_type="Metric",
        thread_pitch="1.5 mm",
        head_type="Hexagonal",
        quantity=15000,
        customer="Apex Automotive Corp",
        production_line="LINE-01",
        machine="CNC-01",
        operator="Operator-03",
        current_status="Manufacturing",
        progress=72,
        manufacturing_start=datetime(2026, 9, 26, 9, 0, 0),
        expected_completion=datetime(2026, 9, 30, 17, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 26, 8, 0, 0),
        updated_at=datetime(2026, 9, 28, 11, 0, 0)
    )
    db_session.add(batch_2)
    db_session.flush()

    batch_2_history = [
        BatchStatusHistory(batch_id=batch_2.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 25, 10, 0, 0), remarks="Work order created."),
        BatchStatusHistory(batch_id=batch_2.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 26, 8, 30, 0), remarks="Billet stock inspected."),
        BatchStatusHistory(batch_id=batch_2.id, status="Manufacturing", progress=35, timestamp=datetime(2026, 9, 27, 12, 0, 0), remarks="Internal tapping initiated."),
        BatchStatusHistory(batch_id=batch_2.id, status="Manufacturing", progress=72, timestamp=datetime(2026, 9, 28, 11, 0, 0), remarks="Threading line running at optimal feed rate.")
    ]
    db_session.add_all(batch_2_history)

    # BATCH-0003
    batch_3 = Batch(
        batch_number="BATCH-0003",
        fastener_type="Washer",
        part_number="WS-M10-FLAT",
        material="Stainless Steel",
        grade="A2-70",
        coating="Passivated",
        diameter="M10",
        length="2 mm",
        thread_type="N/A",
        thread_pitch="N/A",
        head_type="Flat Disc",
        quantity=20000,
        customer="Marine Dynamics Ltd",
        production_line="LINE-03",
        machine="PRESS-02",
        operator="Operator-05",
        current_status="Quality Inspection",
        progress=90,
        manufacturing_start=datetime(2026, 9, 24, 8, 0, 0),
        expected_completion=datetime(2026, 9, 28, 18, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 24, 7, 0, 0),
        updated_at=datetime(2026, 9, 28, 10, 0, 0)
    )
    db_session.add(batch_3)
    db_session.flush()

    batch_3_history = [
        BatchStatusHistory(batch_id=batch_3.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 23, 16, 0, 0), remarks="Scheduled for high speed stamping."),
        BatchStatusHistory(batch_id=batch_3.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 24, 8, 30, 0), remarks="Coil loaded."),
        BatchStatusHistory(batch_id=batch_3.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 25, 17, 0, 0), remarks="Stamping and deburring completed."),
        BatchStatusHistory(batch_id=batch_3.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 28, 9, 0, 0), remarks="Batch routed to Metrology Lab.")
    ]
    db_session.add_all(batch_3_history)

    batch_3_quality = QualityInspection(
        batch_id=batch_3.id,
        dimensional_result="PASS",
        thread_result="N/A",
        surface_result="PASS",
        hardness="28 HRC",
        tensile_strength="700 MPa",
        overall_result="PENDING",
        inspection_date=datetime(2026, 9, 28, 9, 30, 0),
        remarks="Optical thickness check in progress. Initial 50 samples within ±0.02mm."
    )
    db_session.add(batch_3_quality)

    # BATCH-0004
    batch_4 = Batch(
        batch_number="BATCH-0004",
        fastener_type="Stud",
        part_number="ST-M12-080",
        material="Alloy Steel 4140",
        grade="10.9",
        coating="Black Oxide",
        diameter="M12",
        length="80 mm",
        thread_type="Metric Double-End",
        thread_pitch="1.75 mm",
        head_type="Stud Rod",
        quantity=8000,
        customer="PetroValves International",
        production_line="LINE-02",
        machine="CNC-03",
        operator="Operator-02",
        current_status="Scheduled",
        progress=0,
        manufacturing_start=datetime(2026, 9, 29, 8, 0, 0),
        expected_completion=datetime(2026, 10, 2, 17, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 27, 14, 0, 0),
        updated_at=datetime(2026, 9, 27, 14, 0, 0)
    )
    db_session.add(batch_4)
    db_session.flush()

    batch_4_history = [
        BatchStatusHistory(batch_id=batch_4.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 27, 14, 0, 0), remarks="Scheduled for CNC thread rolling. Tooling prepped.")
    ]
    db_session.add_all(batch_4_history)

    # BATCH-0005
    batch_5 = Batch(
        batch_number="BATCH-0005",
        fastener_type="Socket Head Cap Screw",
        part_number="SHCS-M08-035",
        material="Alloy Steel",
        grade="12.9",
        coating="Black Oxide",
        diameter="M8",
        length="35 mm",
        thread_type="Metric",
        thread_pitch="1.25 mm",
        head_type="Cylindrical Hex Socket",
        quantity=12500,
        customer="Nordic Heavy Machinery",
        production_line="LINE-01",
        machine="CNC-02",
        operator="Operator-07",
        current_status="Manufacturing",
        progress=82,
        manufacturing_start=datetime(2026, 9, 24, 7, 30, 0),
        expected_completion=datetime(2026, 9, 29, 16, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 23, 11, 0, 0),
        updated_at=datetime(2026, 9, 28, 8, 45, 0)
    )
    db_session.add(batch_5)
    db_session.flush()

    batch_5_history = [
        BatchStatusHistory(batch_id=batch_5.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 23, 11, 0, 0), remarks="Order entered into scheduling queue."),
        BatchStatusHistory(batch_id=batch_5.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 24, 8, 0, 0), remarks="Heat-treated wire stock loaded."),
        BatchStatusHistory(batch_id=batch_5.id, status="Manufacturing", progress=45, timestamp=datetime(2026, 9, 26, 15, 0, 0), remarks="Cold heading completed. Hex broaching active."),
        BatchStatusHistory(batch_id=batch_5.id, status="Manufacturing", progress=82, timestamp=datetime(2026, 9, 28, 8, 45, 0), remarks="Thread rolling 82% complete.")
    ]
    db_session.add_all(batch_5_history)

    # BATCH-0006
    batch_6 = Batch(
        batch_number="BATCH-0006",
        fastener_type="Self-Tapping Screw",
        part_number="STS-M04-020",
        material="Carbon Steel",
        grade="Case Hardened",
        coating="Galvanized",
        diameter="M4",
        length="20 mm",
        thread_type="Type AB Tapping",
        thread_pitch="1.4 mm",
        head_type="Pan Head Phillips",
        quantity=50000,
        customer="Electrolux Appliances",
        production_line="LINE-04",
        machine="THREAD-01",
        operator="Operator-09",
        current_status="Completed",
        progress=100,
        manufacturing_start=datetime(2026, 9, 20, 8, 0, 0),
        expected_completion=datetime(2026, 9, 23, 17, 0, 0),
        actual_completion=datetime(2026, 9, 23, 16, 30, 0),
        created_at=datetime(2026, 9, 19, 10, 0, 0),
        updated_at=datetime(2026, 9, 23, 16, 30, 0)
    )
    db_session.add(batch_6)
    db_session.flush()

    batch_6_history = [
        BatchStatusHistory(batch_id=batch_6.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 19, 10, 0, 0), remarks="Standard production run scheduled."),
        BatchStatusHistory(batch_id=batch_6.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 20, 8, 30, 0), remarks="Wire drawn and annealed."),
        BatchStatusHistory(batch_id=batch_6.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 21, 18, 0, 0), remarks="High-speed header run completed."),
        BatchStatusHistory(batch_id=batch_6.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 23, 11, 0, 0), remarks="Case depth and torque test passed."),
        BatchStatusHistory(batch_id=batch_6.id, status="Completed", progress=100, timestamp=datetime(2026, 9, 23, 16, 30, 0), remarks="Batch packaged and moved to warehouse.")
    ]
    db_session.add_all(batch_6_history)

    batch_6_quality = QualityInspection(
        batch_id=batch_6.id,
        dimensional_result="PASS",
        thread_result="PASS",
        surface_result="PASS",
        hardness="45 HRC (Case)",
        tensile_strength="650 MPa",
        overall_result="PASSED",
        inspection_date=datetime(2026, 9, 23, 14, 0, 0),
        remarks="Torsional strength 4.8 Nm conforms to DIN 7504."
    )
    db_session.add(batch_6_quality)

    # BATCH-0007
    batch_7 = Batch(
        batch_number="BATCH-0007",
        fastener_type="Rivet",
        part_number="RIV-D06-015",
        material="Aluminum 6061-T6",
        grade="Commercial",
        coating="Anodized Clear",
        diameter="6 mm",
        length="15 mm",
        thread_type="None (Smooth Shank)",
        thread_pitch="N/A",
        head_type="Button Head",
        quantity=30000,
        customer="AeroStructures Global",
        production_line="LINE-03",
        machine="COLD-01",
        operator="Operator-04",
        current_status="Material Preparation",
        progress=10,
        manufacturing_start=datetime(2026, 9, 28, 8, 0, 0),
        expected_completion=datetime(2026, 10, 1, 16, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 27, 9, 0, 0),
        updated_at=datetime(2026, 9, 28, 8, 30, 0)
    )
    db_session.add(batch_7)
    db_session.flush()

    batch_7_history = [
        BatchStatusHistory(batch_id=batch_7.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 27, 9, 0, 0), remarks="Aviation specification work order released."),
        BatchStatusHistory(batch_id=batch_7.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 28, 8, 30, 0), remarks="Aluminum rod alloy certificate verified.")
    ]
    db_session.add_all(batch_7_history)

    # BATCH-0008
    batch_8 = Batch(
        batch_number="BATCH-0008",
        fastener_type="Anchor Bolt",
        part_number="AB-M16-200",
        material="Carbon Steel",
        grade="8.8",
        coating="Hot Dip Galvanized",
        diameter="M16",
        length="200 mm",
        thread_type="Metric Partial",
        thread_pitch="2.0 mm",
        head_type="L-Shape Foundation",
        quantity=4500,
        customer="BuildCorp Infrastructure",
        production_line="LINE-02",
        machine="FORGE-01",
        operator="Operator-01",
        current_status="Completed",
        progress=100,
        manufacturing_start=datetime(2026, 9, 21, 8, 0, 0),
        expected_completion=datetime(2026, 9, 25, 17, 0, 0),
        actual_completion=datetime(2026, 9, 25, 15, 45, 0),
        created_at=datetime(2026, 9, 20, 14, 0, 0),
        updated_at=datetime(2026, 9, 25, 15, 45, 0)
    )
    db_session.add(batch_8)
    db_session.flush()

    batch_8_history = [
        BatchStatusHistory(batch_id=batch_8.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 20, 14, 0, 0), remarks="Civil engineering foundation order queued."),
        BatchStatusHistory(batch_id=batch_8.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 21, 8, 30, 0), remarks="M16 round bars cut and staged."),
        BatchStatusHistory(batch_id=batch_8.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 23, 16, 0, 0), remarks="Hot bending and threading completed."),
        BatchStatusHistory(batch_id=batch_8.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 25, 10, 0, 0), remarks="Galvanizing thickness and tensile test."),
        BatchStatusHistory(batch_id=batch_8.id, status="Completed", progress=100, timestamp=datetime(2026, 9, 25, 15, 45, 0), remarks="Shipped to site logistics yard.")
    ]
    db_session.add_all(batch_8_history)

    batch_8_quality = QualityInspection(
        batch_id=batch_8.id,
        dimensional_result="PASS",
        thread_result="PASS",
        surface_result="PASS",
        hardness="30 HRC",
        tensile_strength="830 MPa",
        overall_result="PASSED",
        inspection_date=datetime(2026, 9, 25, 11, 0, 0),
        remarks="Galvanizing coating thickness averaged 85 microns, passing ASTM A153."
    )
    db_session.add(batch_8_quality)

    # BATCH-0009 (Quality Hold Batch)
    batch_9 = Batch(
        batch_number="BATCH-0009",
        fastener_type="Flange Bolt",
        part_number="FB-M12-060",
        material="Stainless Steel",
        grade="A4-80",
        coating="Passivated",
        diameter="M12",
        length="60 mm",
        thread_type="Metric",
        thread_pitch="1.75 mm",
        head_type="Hex Flange",
        quantity=6000,
        customer="Siemens Energy",
        production_line="LINE-01",
        machine="CNC-05",
        operator="Operator-06",
        current_status="Quality Hold",
        progress=88,
        manufacturing_start=datetime(2026, 9, 24, 8, 0, 0),
        expected_completion=datetime(2026, 9, 27, 17, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 23, 15, 0, 0),
        updated_at=datetime(2026, 9, 27, 16, 20, 0)
    )
    db_session.add(batch_9)
    db_session.flush()

    batch_9_history = [
        BatchStatusHistory(batch_id=batch_9.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 23, 15, 0, 0), remarks="High grade SS316 flange order."),
        BatchStatusHistory(batch_id=batch_9.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 24, 8, 30, 0), remarks="Alloy chemical assay validated."),
        BatchStatusHistory(batch_id=batch_9.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 26, 16, 0, 0), remarks="Flange heading and roll-threading done."),
        BatchStatusHistory(batch_id=batch_9.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 27, 11, 0, 0), remarks="Optical comparator test in progress."),
        BatchStatusHistory(batch_id=batch_9.id, status="Quality Hold", progress=88, timestamp=datetime(2026, 9, 27, 16, 20, 0), remarks="Thread pitch pitch diameter +0.06mm out of tolerance on sample #4. Production halted on CNC-05.")
    ]
    db_session.add_all(batch_9_history)

    batch_9_quality = QualityInspection(
        batch_id=batch_9.id,
        dimensional_result="PASS",
        thread_result="FAIL",
        surface_result="PASS",
        hardness="34 HRC",
        tensile_strength="820 MPa",
        overall_result="HOLD",
        inspection_date=datetime(2026, 9, 27, 15, 0, 0),
        remarks="Thread gauge NO-GO inserted beyond 2 turns. Quarantined for MRB (Material Review Board) assessment."
    )
    db_session.add(batch_9_quality)

    # BATCH-0010
    batch_10 = Batch(
        batch_number="BATCH-0010",
        fastener_type="Hex Bolt",
        part_number="HB-M20-100",
        material="Alloy Steel 4140",
        grade="10.9",
        coating="Dacromet",
        diameter="M20",
        length="100 mm",
        thread_type="Metric",
        thread_pitch="2.5 mm",
        head_type="Hexagonal Heavy",
        quantity=5000,
        customer="Caterpillar Heavy Systems",
        production_line="LINE-02",
        machine="CNC-04",
        operator="Operator-07",
        current_status="Completed",
        progress=100,
        manufacturing_start=datetime(2026, 9, 20, 7, 0, 0),
        expected_completion=datetime(2026, 9, 24, 18, 0, 0),
        actual_completion=datetime(2026, 9, 24, 17, 30, 0),
        created_at=datetime(2026, 9, 19, 14, 0, 0),
        updated_at=datetime(2026, 9, 24, 17, 30, 0)
    )
    db_session.add(batch_10)
    db_session.flush()

    batch_10_history = [
        BatchStatusHistory(batch_id=batch_10.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 19, 14, 0, 0), remarks="Heavy fastener work order initialized."),
        BatchStatusHistory(batch_id=batch_10.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 20, 7, 30, 0), remarks="Raw material cut and chamfered."),
        BatchStatusHistory(batch_id=batch_10.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 22, 16, 0, 0), remarks="Forged heads and rolled M20 threads."),
        BatchStatusHistory(batch_id=batch_10.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 24, 11, 0, 0), remarks="Dacromet corrosion salt spray and hardness testing."),
        BatchStatusHistory(batch_id=batch_10.id, status="Completed", progress=100, timestamp=datetime(2026, 9, 24, 17, 30, 0), remarks="Passed all QA gates and sealed for export.")
    ]
    db_session.add_all(batch_10_history)

    batch_10_quality = QualityInspection(
        batch_id=batch_10.id,
        dimensional_result="PASS",
        thread_result="PASS",
        surface_result="PASS",
        hardness="38 HRC",
        tensile_strength="1040 MPa",
        overall_result="PASSED",
        inspection_date=datetime(2026, 9, 24, 14, 0, 0),
        remarks="1000-hour salt spray test rating passed with zero red rust."
    )
    db_session.add(batch_10_quality)

    # BATCH-0011
    batch_11 = Batch(
        batch_number="BATCH-0011",
        fastener_type="Carriage Bolt",
        part_number="CB-M08-040",
        material="Stainless Steel",
        grade="A2-70",
        coating="Polished",
        diameter="M8",
        length="40 mm",
        thread_type="Metric",
        thread_pitch="1.25 mm",
        head_type="Round Domed Head with Square Neck",
        quantity=18000,
        customer="SolarMount Technologies",
        production_line="LINE-04",
        machine="PRESS-03",
        operator="Operator-08",
        current_status="Scheduled",
        progress=0,
        manufacturing_start=datetime(2026, 9, 30, 8, 0, 0),
        expected_completion=datetime(2026, 10, 3, 17, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 28, 8, 0, 0),
        updated_at=datetime(2026, 9, 28, 8, 0, 0)
    )
    db_session.add(batch_11)
    db_session.flush()

    batch_11_history = [
        BatchStatusHistory(batch_id=batch_11.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 28, 8, 0, 0), remarks="Scheduled for solar racking production queue.")
    ]
    db_session.add_all(batch_11_history)

    # BATCH-0012
    batch_12 = Batch(
        batch_number="BATCH-0012",
        fastener_type="Eye Bolt",
        part_number="EB-M16-075",
        material="Carbon Steel",
        grade="8.8",
        coating="Yellow Zinc Dichromate",
        diameter="M16",
        length="75 mm",
        thread_type="Metric",
        thread_pitch="2.0 mm",
        head_type="Forged Eye Ring",
        quantity=3200,
        customer="CraneRig Solutions",
        production_line="LINE-02",
        machine="FORGE-02",
        operator="Operator-02",
        current_status="Quality Inspection",
        progress=90,
        manufacturing_start=datetime(2026, 9, 25, 8, 0, 0),
        expected_completion=datetime(2026, 9, 29, 17, 0, 0),
        actual_completion=None,
        created_at=datetime(2026, 9, 24, 16, 0, 0),
        updated_at=datetime(2026, 9, 28, 14, 0, 0)
    )
    db_session.add(batch_12)
    db_session.flush()

    batch_12_history = [
        BatchStatusHistory(batch_id=batch_12.id, status="Scheduled", progress=0, timestamp=datetime(2026, 9, 24, 16, 0, 0), remarks="Rigging lifting bolt batch queued."),
        BatchStatusHistory(batch_id=batch_12.id, status="Material Preparation", progress=10, timestamp=datetime(2026, 9, 25, 8, 30, 0), remarks="Drop forge stock heated and prepared."),
        BatchStatusHistory(batch_id=batch_12.id, status="Manufacturing", progress=65, timestamp=datetime(2026, 9, 27, 15, 0, 0), remarks="Forged loop and cut threaded shank."),
        BatchStatusHistory(batch_id=batch_12.id, status="Quality Inspection", progress=90, timestamp=datetime(2026, 9, 28, 14, 0, 0), remarks="Proof load pull testing in test rig.")
    ]
    db_session.add_all(batch_12_history)

    batch_12_quality = QualityInspection(
        batch_id=batch_12.id,
        dimensional_result="PASS",
        thread_result="PASS",
        surface_result="PASS",
        hardness="31 HRC",
        tensile_strength="840 MPa",
        overall_result="PENDING",
        inspection_date=datetime(2026, 9, 28, 14, 30, 0),
        remarks="Proof load 2x WLL (Working Load Limit) test passed with zero permanent deformation."
    )
    db_session.add(batch_12_quality)

    db_session.commit()
    print("Database seeding successfully completed!")
    print(f"Total Batches seeded: {db_session.query(Batch).count()}")

if __name__ == "__main__":
    force_seed = "--force" in sys.argv or "-f" in sys.argv
    seed_database(force=force_seed)
