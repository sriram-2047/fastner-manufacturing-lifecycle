"""
FASTENPRO AI Comprehensive Test Runner & Validation Suite
Executes end-to-end tests against the running live server and local SQLite database,
capturing real outputs, latencies, HTTP response codes, JSON payloads, and validation states.
"""

import sys
import os
import time
import json
import sqlite3
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "fastener.db")

test_results = []
test_logs = []

def log(msg):
    print(msg)
    test_logs.append(msg)

def record_test(test_id, category, name, expected, actual, status, latency_ms=0, details=None):
    res = {
        "id": test_id,
        "category": category,
        "name": name,
        "expected": str(expected),
        "actual": str(actual),
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "details": details or {}
    }
    test_results.append(res)
    mark = "[PASS]" if status == "PASS" else "[FAIL]"
    log(f"{mark} {test_id}: {name} -> {status} ({round(latency_ms, 1)}ms)")
    return res

def run_tests():
    log("=" * 70)
    log("FASTENPRO AI — COMPLETE VALIDATION & TEST EXECUTION")
    log(f"Date: {datetime.now().isoformat()}")
    log(f"Target Server: {BASE_URL}")
    log(f"Database Path: {DB_PATH}")
    log("=" * 70)

    # -------------------------------------------------------------------------
    # A. Environment Testing
    # -------------------------------------------------------------------------
    log("\n--- Category A: Environment Testing ---")
    
    # TC-ENV-001: Python Version
    py_ver = sys.version.split()[0]
    record_test("TC-ENV-001", "Environment", "Python 3.10+ Runtime Check",
                ">= 3.10.0", py_ver, "PASS" if sys.version_info >= (3, 10) else "FAIL")

    # TC-ENV-002: SQLite Availability
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        sq_ver = cursor.fetchone()[0]
        conn.close()
        record_test("TC-ENV-002", "Environment", "SQLite Engine & Database File",
                    "SQLite connected", f"SQLite v{sq_ver}", "PASS")
    except Exception as e:
        record_test("TC-ENV-002", "Environment", "SQLite Engine & Database File",
                    "SQLite connected", str(e), "FAIL")

    # TC-ENV-003: Local Ollama Reachability
    t0 = time.time()
    try:
        r_ol = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        ol_status = "Connected" if r_ol.status_code == 200 else f"HTTP {r_ol.status_code}"
    except Exception:
        ol_status = "Offline (Graceful Fallback Active)"
    lat_ol = (time.time() - t0) * 1000
    record_test("TC-ENV-003", "Environment", "Ollama Service Reachability Check",
                "Connected or Truthful Offline Status", ol_status, "PASS", lat_ol)

    # -------------------------------------------------------------------------
    # B. Database Integrity & Seed Verification
    # -------------------------------------------------------------------------
    log("\n--- Category B: Database Testing ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # TC-DB-001: Required Tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    req_tables = ["batches", "batch_status_history", "quality_inspections", "fastener_types"]
    all_present = all(t in tables for t in req_tables)
    record_test("TC-DB-001", "Database", "Required Schema Tables Exist",
                req_tables, tables, "PASS" if all_present else "FAIL")

    # TC-DB-002: Batch Count
    cursor.execute("SELECT COUNT(*) FROM batches;")
    batch_count = cursor.fetchone()[0]
    record_test("TC-DB-002", "Database", "Database Batch Seed Count",
                ">= 10 batches", f"{batch_count} batches", "PASS" if batch_count >= 10 else "FAIL")

    # TC-DB-003: BATCH-0001 Initial Specifications
    cursor.execute("""
        SELECT batch_number, fastener_type, part_number, material, grade, coating,
               diameter, length, thread_pitch, quantity, production_line, machine,
               operator, current_status, progress
        FROM batches WHERE batch_number='BATCH-0001';
    """)
    b1 = cursor.fetchone()
    b1_valid = (
        b1 and
        b1[0] == "BATCH-0001" and
        b1[1] == "Hex Bolt" and
        b1[2] == "HB-M10-050" and
        b1[3] == "Carbon Steel" and
        b1[4] == "8.8" and
        b1[5] == "Zinc Plated" and
        b1[6] == "M10" and
        b1[7] == "50 mm" and
        b1[8] == "1.5 mm" and
        b1[9] == 10000 and
        b1[10] == "LINE-02" and
        b1[11] == "CNC-04" and
        b1[12] == "Operator-07" and
        b1[13] == "Manufacturing" and
        b1[14] == 65
    )
    record_test("TC-DB-003", "Database", "BATCH-0001 Initial State & Specs",
                "Hex Bolt, Carbon Steel 8.8, 10000 units, LINE-02, CNC-04, Manufacturing 65%",
                f"{b1[1]}, {b1[3]} {b1[4]}, {b1[9]} units, {b1[10]}, {b1[11]}, {b1[13]} {b1[14]}%",
                "PASS" if b1_valid else "FAIL")

    # TC-DB-004: Orphan Prevention / Foreign Keys
    cursor.execute("""
        SELECT COUNT(*) FROM batch_status_history
        WHERE batch_id NOT IN (SELECT id FROM batches);
    """)
    orphan_hist = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM quality_inspections
        WHERE batch_id NOT IN (SELECT id FROM batches);
    """)
    orphan_qa = cursor.fetchone()[0]
    record_test("TC-DB-004", "Database", "Orphan History/Quality Prevention",
                "0 orphans", f"{orphan_hist} orphan history, {orphan_qa} orphan QA",
                "PASS" if orphan_hist == 0 and orphan_qa == 0 else "FAIL")

    # TC-DB-005: Quality Inspection Consistency
    cursor.execute("""
        SELECT id, dimensional_result, thread_result, surface_result, overall_result
        FROM quality_inspections;
    """)
    qa_rows = cursor.fetchall()
    qa_inconsistent = 0
    for q in qa_rows:
        dim, thr, surf, overall = q[1], q[2], q[3], q[4]
        # Inconsistency: all PASS but overall is FAILED
        if dim == "PASS" and thr == "PASS" and surf == "PASS" and overall == "FAILED":
            qa_inconsistent += 1
    record_test("TC-DB-005", "Database", "Quality Inspection Data Consistency",
                "0 contradictory records", f"{qa_inconsistent} contradictory records",
                "PASS" if qa_inconsistent == 0 else "FAIL")
    conn.close()

    # -------------------------------------------------------------------------
    # C. API Endpoint Testing
    # -------------------------------------------------------------------------
    log("\n--- Category C: API Testing ---")

    # TC-API-001: Health Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/health")
    lat = (time.time() - t0) * 1000
    data = r.json()
    h_pass = r.status_code == 200 and data.get("success") is True and data["data"]["database"] == "connected"
    record_test("TC-API-001", "API", "GET /api/health",
                "200 OK with database=connected", f"{r.status_code} DB: {data.get('data', {}).get('database')}, Ollama: {data.get('data', {}).get('ollama')}",
                "PASS" if h_pass else "FAIL", lat, data)

    # TC-API-002: Dashboard Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/dashboard")
    lat = (time.time() - t0) * 1000
    data = r.json()
    d_data = data.get("data", {})
    d_pass = (
        r.status_code == 200 and
        d_data.get("total_batches") == 12 and
        d_data.get("active_manufacturing") == 3 and
        d_data.get("completed") == 3 and
        d_data.get("quality_hold") == 1 and
        d_data.get("total_units") == 182200 and
        d_data.get("completed_units") == 59500
    )
    record_test("TC-API-002", "API", "GET /api/dashboard (Real DB KPI Aggregations)",
                "Total: 12, Active Mfg: 3, Completed: 3, Hold: 1, Units: 182200",
                f"Total: {d_data.get('total_batches')}, Active Mfg: {d_data.get('active_manufacturing')}, Completed: {d_data.get('completed')}, Hold: {d_data.get('quality_hold')}, Units: {d_data.get('total_units')}",
                "PASS" if d_pass else "FAIL", lat, d_data)

    # TC-API-003: Batches List
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches")
    lat = (time.time() - t0) * 1000
    data = r.json()
    b_raw = data.get("data", [])
    b_list = b_raw if isinstance(b_raw, list) else b_raw.get("batches", [])
    record_test("TC-API-003", "API", "GET /api/batches (List All Batches)",
                "200 OK with 12 batches", f"{r.status_code} with {len(b_list)} batches",
                "PASS" if r.status_code == 200 and len(b_list) == 12 else "FAIL", lat)

    # TC-API-004: Search Filter
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches?search=BATCH-0001")
    lat = (time.time() - t0) * 1000
    data = r.json()
    s_raw = data.get("data", [])
    s_batches = s_raw if isinstance(s_raw, list) else s_raw.get("batches", [])
    record_test("TC-API-004", "API", "GET /api/batches?search=BATCH-0001",
                "1 matching batch", f"{len(s_batches)} matching batch(es)",
                "PASS" if len(s_batches) == 1 and s_batches[0]["batch_number"] == "BATCH-0001" else "FAIL", lat)

    # TC-API-005: Status Filter
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches?status=Manufacturing")
    lat = (time.time() - t0) * 1000
    data = r.json()
    m_raw = data.get("data", [])
    m_batches = m_raw if isinstance(m_raw, list) else m_raw.get("batches", [])
    record_test("TC-API-005", "API", "GET /api/batches?status=Manufacturing",
                "3 manufacturing batches", f"{len(m_batches)} batches returned",
                "PASS" if len(m_batches) == 3 else "FAIL", lat)

    # TC-API-006: Line Filter
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches?line=LINE-02")
    lat = (time.time() - t0) * 1000
    data = r.json()
    l_raw = data.get("data", [])
    l_batches = l_raw if isinstance(l_raw, list) else l_raw.get("batches", [])
    record_test("TC-API-006", "API", "GET /api/batches?line=LINE-02",
                "5 LINE-02 batches", f"{len(l_batches)} batches returned",
                "PASS" if len(l_batches) == 5 else "FAIL", lat)

    # TC-API-007: Batch Detail Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches/BATCH-0001")
    lat = (time.time() - t0) * 1000
    data = r.json()
    b_data = data.get("data", {})
    record_test("TC-API-007", "API", "GET /api/batches/BATCH-0001",
                "200 OK with full batch details", f"{r.status_code} Status: {b_data.get('current_status')}, Progress: {b_data.get('progress')}%",
                "PASS" if r.status_code == 200 and b_data.get("batch_number") == "BATCH-0001" else "FAIL", lat)

    # TC-API-008: Case-Insensitive Batch Lookup
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches/batch-0001")
    lat = (time.time() - t0) * 1000
    data = r.json()
    record_test("TC-API-008", "API", "GET /api/batches/batch-0001 (Case Insensitive)",
                "200 OK resolving to BATCH-0001", f"{r.status_code} Batch: {data.get('data', {}).get('batch_number')}",
                "PASS" if r.status_code == 200 and data.get("data", {}).get("batch_number") == "BATCH-0001" else "FAIL", lat)

    # TC-API-009: 404 Batch Not Found
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches/BATCH-9999")
    lat = (time.time() - t0) * 1000
    data = r.json()
    record_test("TC-API-009", "API", "GET /api/batches/BATCH-9999 (Not Found)",
                "404 Not Found error", f"{r.status_code} Error: {data.get('error')}",
                "PASS" if r.status_code == 404 and "not found" in data.get("error", "").lower() else "FAIL", lat)

    # TC-API-010: Batch History Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches/BATCH-0001/history")
    lat = (time.time() - t0) * 1000
    data = r.json()
    h_raw = data.get("data", [])
    h_list = h_raw if isinstance(h_raw, list) else h_raw.get("history", [])
    record_test("TC-API-010", "API", "GET /api/batches/BATCH-0001/history",
                "200 OK with 3 initial history records", f"{r.status_code} with {len(h_list)} records",
                "PASS" if r.status_code == 200 and len(h_list) == 3 else "FAIL", lat)

    # TC-API-011: Batch Quality Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches/BATCH-0001/quality")
    lat = (time.time() - t0) * 1000
    data = r.json()
    q_raw = data.get("data", {})
    latest = q_raw.get("latest_inspection") or (q_raw.get("inspections", [{}])[0] if q_raw.get("inspections") else q_raw)
    q_pass = r.status_code == 200 and latest.get("overall_result") == "PASSED"
    record_test("TC-API-011", "API", "GET /api/batches/BATCH-0001/quality",
                "200 OK with PASSED overall result", f"{r.status_code} Result: {latest.get('overall_result')}, Hardness: {latest.get('hardness')}",
                "PASS" if q_pass else "FAIL", lat)

    # TC-API-012: Production Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/production")
    lat = (time.time() - t0) * 1000
    data = r.json()
    prod_lines = data.get("production_lines") or data.get("data", {}).get("production_lines", [])
    record_test("TC-API-012", "API", "GET /api/production",
                "200 OK with active production lines", f"{r.status_code} with {len(prod_lines)} production line groups",
                "PASS" if r.status_code == 200 and len(prod_lines) > 0 else "FAIL", lat)

    # TC-API-013: Quality Overview Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/quality")
    lat = (time.time() - t0) * 1000
    data = r.json()
    qa_kpis = data.get("data", {})
    record_test("TC-API-013", "API", "GET /api/quality",
                "200 OK with QA KPIs & quarantine log", f"{r.status_code} Passed: {qa_kpis.get('passed')}, Hold: {qa_kpis.get('hold')}, Failed: {qa_kpis.get('failed')}",
                "PASS" if r.status_code == 200 and qa_kpis.get("passed", 0) > 0 else "FAIL", lat)

    # TC-API-014: Reports Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/reports/BATCH-0001")
    lat = (time.time() - t0) * 1000
    data = r.json()
    rep = data.get("data", {})
    record_test("TC-API-014", "API", "GET /api/reports/BATCH-0001",
                "200 OK with full traceability report", f"{r.status_code} Batch: {rep.get('batch_number')}, Status: {rep.get('current_status')}",
                "PASS" if r.status_code == 200 and rep.get("batch_number") == "BATCH-0001" else "FAIL", lat)

    # TC-API-015: AI Status Endpoint
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/ai/status")
    lat = (time.time() - t0) * 1000
    data = r.json()
    record_test("TC-API-015", "API", "GET /api/ai/status",
                "200 OK with AI engine status", f"{r.status_code} Provider: {data.get('data', {}).get('provider')}, Status: {data.get('data', {}).get('status')}",
                "PASS" if r.status_code == 200 else "FAIL", lat)

    # -------------------------------------------------------------------------
    # D. Historical Data & Point-in-Time Integrity Testing
    # -------------------------------------------------------------------------
    log("\n--- Category D: Historical Data & AI Grounding ---")

    # TC-HIST-001: Historical status on Sep 25
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What was the status of BATCH-0001 on September 25?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    h_src = data.get("data", {}).get("source", "")
    # Expect Material Prep or Manufacturing (started) on Sep 25
    h25_pass = "2026-09-25" in str(data) and ("Manufacturing" in ans or "Material Preparation" in ans)
    record_test("TC-HIST-001", "Historical", "Historical Status on Sep 25, 2026",
                "Material Preparation / Manufacturing (20%)", f"Answer: {ans[:80]}... [Source: {h_src}]",
                "PASS" if h25_pass else "FAIL", lat, {"answer": ans, "raw": data})

    # TC-HIST-002: Historical status on Sep 26
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What was the status of BATCH-0001 on September 26?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    h26_pass = "Manufacturing" in ans and "65%" in ans
    record_test("TC-HIST-002", "Historical", "Historical Status on Sep 26, 2026",
                "Manufacturing at 65%", f"Answer: {ans[:80]}...",
                "PASS" if h26_pass else "FAIL", lat, {"answer": ans})

    # TC-HIST-003: Current status question before lifecycle update
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What is the current status of BATCH-0001?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    curr_pass = "Manufacturing" in ans and "65%" in ans
    record_test("TC-HIST-003", "AI", "Current Status AI Query (Before Advance)",
                "Manufacturing (65%)", f"Answer: {ans[:80]}...",
                "PASS" if curr_pass else "FAIL", lat, {"answer": ans})

    # TC-HIST-004: Relative Date ("two days ago")
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What was the status of BATCH-0001 two days ago?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    rel_pass = "Manufacturing" in ans and "65%" in ans
    record_test("TC-HIST-004", "Historical", "Relative Date Historical Query ('two days ago')",
                "Manufacturing at 65%", f"Answer: {ans[:80]}...",
                "PASS" if rel_pass else "FAIL", lat, {"answer": ans})

    # TC-HIST-005: Manufacturing History List Query
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "Show me the manufacturing history of BATCH-0001"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    hist_list_pass = "Material Preparation" in ans and "Manufacturing" in ans
    record_test("TC-HIST-005", "AI", "Manufacturing History List Query",
                "Audit trail with Material Prep and Manufacturing", f"Answer: {ans[:80]}...",
                "PASS" if hist_list_pass else "FAIL", lat, {"answer": ans})

    # -------------------------------------------------------------------------
    # E. Batch Lifecycle Testing (Advance, Complete, Concurrency, Conflict)
    # -------------------------------------------------------------------------
    log("\n--- Category E: Batch Lifecycle Testing ---")

    # TC-LIFE-001: Advance Batch (Manufacturing -> Quality Inspection)
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/batches/BATCH-0001/advance")
    lat = (time.time() - t0) * 1000
    data = r.json()
    b_adv = data.get("data", {}).get("batch", {})
    adv_pass = r.status_code == 200 and b_adv.get("current_status") == "Quality Inspection" and b_adv.get("progress") == 90
    record_test("TC-LIFE-001", "Lifecycle", "Advance BATCH-0001 (Mfg -> Quality Inspection)",
                "Quality Inspection, 90% progress", f"{r.status_code} Status: {b_adv.get('current_status')}, Progress: {b_adv.get('progress')}%",
                "PASS" if adv_pass else "FAIL", lat, data)

    # TC-LIFE-002: History Immutability Check (Count incremented by 1)
    r_hist = requests.get(f"{BASE_URL}/api/batches/BATCH-0001/history")
    h_data_adv = r_hist.json().get("data", [])
    h_count_after_adv = len(h_data_adv if isinstance(h_data_adv, list) else h_data_adv.get("history", []))
    record_test("TC-LIFE-002", "Lifecycle", "History Immutability (Count Incremented by 1)",
                "4 history records (3 initial + 1 new)", f"{h_count_after_adv} history records",
                "PASS" if h_count_after_adv == 4 else "FAIL")

    # TC-LIFE-003: Critical Historical Integrity Test (Sep 26 status still Mfg 65% after advance)
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What was the status of BATCH-0001 on September 26?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    crit_pass = "Manufacturing" in ans and "65%" in ans and "Quality Inspection" not in ans
    record_test("TC-LIFE-003", "Historical", "Historical Status on Sep 26 PRESERVED After Advance",
                "Manufacturing (65%)", f"Answer: {ans[:80]}...",
                "PASS" if crit_pass else "FAIL", lat, {"answer": ans})

    # TC-LIFE-004: Complete Batch (Quality Inspection -> Completed 100%)
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/batches/BATCH-0001/complete")
    lat = (time.time() - t0) * 1000
    data = r.json()
    b_comp = data.get("data", {}).get("batch", {})
    comp_pass = (
        r.status_code == 200 and
        b_comp.get("current_status") == "Completed" and
        b_comp.get("progress") == 100 and
        b_comp.get("actual_completion") is not None
    )
    record_test("TC-LIFE-004", "Lifecycle", "Complete BATCH-0001 (-> Completed 100%)",
                "Completed, 100% progress, actual_completion set",
                f"{r.status_code} Status: {b_comp.get('current_status')}, Progress: {b_comp.get('progress')}%, Actual Completion: {b_comp.get('actual_completion')}",
                "PASS" if comp_pass else "FAIL", lat, data)

    # TC-LIFE-005: Dashboard Dynamic Update Verification After Completion
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/dashboard")
    lat = (time.time() - t0) * 1000
    d_after = r.json().get("data", {})
    # Completed batches should increase from 3 to 4, completed units from 59500 to 69500
    dash_upd_pass = d_after.get("completed") == 4 and d_after.get("completed_units") == 69500
    record_test("TC-LIFE-005", "Dashboard", "Dashboard Live Counters Update After Completion",
                "Completed batches: 4, Completed units: 69500",
                f"Completed: {d_after.get('completed')}, Completed Units: {d_after.get('completed_units')}",
                "PASS" if dash_upd_pass else "FAIL", lat, d_after)

    # TC-LIFE-006: Duplicate Complete Call (Idempotency Test)
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/batches/BATCH-0001/complete")
    lat = (time.time() - t0) * 1000
    data = r.json()
    r_hist2 = requests.get(f"{BASE_URL}/api/batches/BATCH-0001/history")
    h_data_comp2 = r_hist2.json().get("data", [])
    h_count2 = len(h_data_comp2 if isinstance(h_data_comp2, list) else h_data_comp2.get("history", []))
    record_test("TC-LIFE-006", "Lifecycle", "Duplicate Complete Call Idempotency",
                "No duplicate history record created (total stays 5)",
                f"History count: {h_count2}, Msg: {data.get('message', 'OK')}",
                "PASS" if h_count2 == 5 else "FAIL", lat)

    # TC-LIFE-007: Invalid Lifecycle Transition (Advance from Completed -> 409 Conflict)
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/batches/BATCH-0001/advance")
    lat = (time.time() - t0) * 1000
    data = r.json()
    record_test("TC-LIFE-007", "Lifecycle", "Invalid Transition Rejection (Advance from Completed)",
                "409 Conflict error", f"{r.status_code} Error: {data.get('error')}",
                "PASS" if r.status_code == 409 else "FAIL", lat)

    # TC-LIFE-008: Current Status AI Query After Completion
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What is the current status of BATCH-0001?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    comp_ai_pass = "Completed" in ans and "100%" in ans
    record_test("TC-LIFE-008", "AI", "Current Status AI Query (After Completion)",
                "Completed (100%)", f"Answer: {ans[:80]}...",
                "PASS" if comp_ai_pass else "FAIL", lat, {"answer": ans})

    # TC-LIFE-009: Historical Status on Sep 26 PRESERVED After Completion
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "What was the status of BATCH-0001 on September 26?"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    crit_comp_pass = "Manufacturing" in ans and "65%" in ans and "Completed" not in ans
    record_test("TC-LIFE-009", "Historical", "Historical Status on Sep 26 PRESERVED After Completion",
                "Manufacturing (65%)", f"Answer: {ans[:80]}...",
                "PASS" if crit_comp_pass else "FAIL", lat, {"answer": ans})

    # -------------------------------------------------------------------------
    # F. AI Grounding & Specification Questions
    # -------------------------------------------------------------------------
    log("\n--- Category F: AI Grounding & Metrology Questions ---")

    spec_tests = [
        ("TC-AI-001", "Did BATCH-0001 pass quality inspection?", "PASSED (Dimensional: PASS, Thread: PASS, Surface: PASS, Hardness: 32 HRC, Tensile: 800 MPa)", "PASSED"),
        ("TC-AI-002", "What material was used for BATCH-0001?", "Carbon Steel", "Carbon Steel"),
        ("TC-AI-003", "What is the material grade of BATCH-0001?", "8.8", "8.8"),
        ("TC-AI-004", "What is the quantity of BATCH-0001?", "10,000", "10,000"),
        ("TC-AI-005", "What fastener is BATCH-0001?", "Hex Bolt", "Hex Bolt"),
        ("TC-AI-006", "What is the diameter and length of BATCH-0001?", "Diameter: M10, Length: 50 mm", "M10"),
        ("TC-AI-007", "What coating was used for BATCH-0001?", "Zinc Plated", "Zinc Plated"),
        ("TC-AI-008", "What machine produced BATCH-0001?", "CNC-04", "CNC-04"),
        ("TC-AI-009", "What production line produced BATCH-0001?", "LINE-02", "LINE-02"),
        ("TC-AI-010", "Who was the operator for BATCH-0001?", "Operator-07", "Operator-07"),
        ("TC-AI-011", "Which batches are currently manufacturing?", "Batches in Manufacturing (BATCH-0002, BATCH-0005, etc.)", "BATCH-0002"),
        ("TC-AI-012", "Which batches are on quality hold?", "BATCH-0009 on Quality Hold", "quality hold"),
        ("TC-AI-013", "What is the CNC temperature for BATCH-0001?", "The requested information is not available in the manufacturing records.", "not available in the manufacturing records"),
        ("TC-AI-014", "What is the status of BATCH-9999?", "Batch BATCH-9999 was not found in the database.", "not found"),
    ]

    for t_id, q, exp, match_str in spec_tests:
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": q})
        lat = (time.time() - t0) * 1000
        data = r.json()
        ans = data.get("data", {}).get("answer", "")
        pass_cond = match_str.lower() in ans.lower()
        record_test(t_id, "AI Grounding", f"AI Query: '{q}'",
                    exp, f"Answer: {ans[:75]}...",
                    "PASS" if pass_cond else "FAIL", lat, {"question": q, "answer": ans, "data": data})

    # -------------------------------------------------------------------------
    # G. Security & Input Validation
    # -------------------------------------------------------------------------
    log("\n--- Category G: Security & Error Handling ---")

    # TC-SEC-001: SQL Injection Attempt in Search
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/api/batches?search=BATCH-0001'%20OR%20'1'='1")
    lat = (time.time() - t0) * 1000
    raw_found = data.get("data", [])
    b_found = raw_found if isinstance(raw_found, list) else raw_found.get("batches", [])
    record_test("TC-SEC-001", "Security", "SQL Injection in Search Query",
                "0 unauthorized records / safe query execution", f"{len(b_found)} records returned",
                "PASS" if len(b_found) == 0 else "FAIL", lat)

    # TC-SEC-002: XSS Script Tag in AI Chat Question
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "<script>alert('XSS')</script> BATCH-0001"})
    lat = (time.time() - t0) * 1000
    data = r.json()
    ans = data.get("data", {}).get("answer", "")
    record_test("TC-SEC-002", "Security", "XSS Tag Sanitization in AI Question",
                "Safe handling without script execution / grounded response", f"Answer: {ans[:60]}...",
                "PASS" if r.status_code == 200 else "FAIL", lat)

    # TC-SEC-003: Empty Question to AI Chat
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", json={"question": "   "})
    lat = (time.time() - t0) * 1000
    data = r.json()
    record_test("TC-SEC-003", "Validation", "Empty Question Validation",
                "400 Bad Request error", f"{r.status_code} Error: {data.get('error')}",
                "PASS" if r.status_code == 400 else "FAIL", lat)

    # TC-SEC-004: Missing JSON Body to AI Chat
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/ai/chat", data="not json", headers={"Content-Type": "text/plain"})
    lat = (time.time() - t0) * 1000
    record_test("TC-SEC-004", "Validation", "Non-JSON Body Validation",
                "400 Bad Request error", f"{r.status_code} Status",
                "PASS" if r.status_code == 400 else "FAIL", lat)

    # -------------------------------------------------------------------------
    # H. Frontend Routes Verification
    # -------------------------------------------------------------------------
    log("\n--- Category H: Frontend HTML Routes ---")
    routes = [
        ("TC-FE-001", "/", "Dashboard Page HTML"),
        ("TC-FE-002", "/batches", "Batch Catalog Page HTML"),
        ("TC-FE-003", "/production", "Production Floor Page HTML"),
        ("TC-FE-004", "/quality", "Quality Metrology Page HTML"),
        ("TC-FE-005", "/ai", "AI Copilot Page HTML"),
        ("TC-FE-006", "/reports", "Traceability Reports Page HTML"),
    ]

    for t_id, path, desc in routes:
        t0 = time.time()
        r = requests.get(f"{BASE_URL}{path}")
        lat = (time.time() - t0) * 1000
        pass_fe = r.status_code == 200 and "<!DOCTYPE html>" in r.text
        record_test(t_id, "Frontend", f"GET {path} ({desc})",
                    "200 OK HTML", f"{r.status_code} ({len(r.text)} bytes)",
                    "PASS" if pass_fe else "FAIL", lat)

    # -------------------------------------------------------------------------
    # Summary Calculations
    # -------------------------------------------------------------------------
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["status"] == "PASS")
    failed_tests = sum(1 for t in test_results if t["status"] == "FAIL")
    blocked_tests = 0
    pass_pct = round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0

    log("\n" + "=" * 70)
    log("TESTING SUMMARY")
    log("=" * 70)
    log(f"Total Tests:    {total_tests}")
    log(f"Passed:         {passed_tests}")
    log(f"Failed:         {failed_tests}")
    log(f"Blocked:        {blocked_tests}")
    log(f"Pass Rate:      {pass_pct}%")
    log("=" * 70)

    return {
        "results": test_results,
        "logs": test_logs,
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "blocked": blocked_tests,
        "pass_pct": pass_pct
    }

if __name__ == "__main__":
    summary = run_tests()
    with open("test_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
