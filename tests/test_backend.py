import unittest
import os
import sys
import json
from datetime import datetime

# Add project root to Python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import init_db, db_session
from models import Batch, BatchStatusHistory, QualityInspection
from seed import seed_database
from services.batch_service import (
    get_all_batches,
    get_batch_by_number,
    get_dashboard_kpis,
    advance_batch,
    complete_batch
)
from services.history_service import get_batch_status_at_datetime, get_batch_history
from services.quality_service import get_quality_overview, get_batch_quality
from services.ai_service import process_ai_query, build_database_context

class FastenProBackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup test app client
        app.config['TESTING'] = True
        cls.client = app.test_client()
        # Seed fresh database
        seed_database(force=True)

    def setUp(self):
        # Ensure fresh seed before test where needed
        pass

    def test_01_health_endpoint(self):
        """Test GET /api/health returns database and ollama status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('database', data['data'])
        self.assertIn('ollama', data['data'])
        self.assertIn('ollama_model', data['data'])
        self.assertEqual(data['data']['database'], 'connected')

    def test_02_dashboard_kpis(self):
        """Test GET /api/dashboard returns real aggregate SQL numbers."""
        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        kpis = data['data']
        self.assertGreaterEqual(kpis['total_batches'], 10)
        self.assertGreaterEqual(kpis['active_manufacturing'], 1)
        self.assertGreaterEqual(kpis['completed'], 1)
        self.assertGreaterEqual(kpis['total_units'], 100000)
        self.assertTrue(isinstance(kpis['recent_batches'], list))

    def test_03_batches_list_and_filters(self):
        """Test GET /api/batches with search, status, and line filters."""
        # All batches
        res_all = self.client.get('/api/batches')
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.get_json()
        self.assertGreaterEqual(data_all['count'], 10)

        # Filter by status
        res_status = self.client.get('/api/batches?status=Manufacturing')
        self.assertEqual(res_status.status_code, 200)
        data_status = res_status.get_json()
        for b in data_status['data']:
            self.assertEqual(b['current_status'], 'Manufacturing')

        # Filter by line
        res_line = self.client.get('/api/batches?line=LINE-02')
        self.assertEqual(res_line.status_code, 200)
        data_line = res_line.get_json()
        for b in data_line['data']:
            self.assertEqual(b['production_line'], 'LINE-02')

        # Filter by search
        res_search = self.client.get('/api/batches?search=HB-M10-050')
        self.assertEqual(res_search.status_code, 200)
        data_search = res_search.get_json()
        self.assertGreaterEqual(len(data_search['data']), 1)
        self.assertEqual(data_search['data'][0]['batch_number'], 'BATCH-0001')

    def test_04_batch_detail_and_not_found(self):
        """Test GET /api/batches/<batch_number> normalization and 404."""
        # Case insensitive normalization
        res = self.client.get('/api/batches/batch-0001')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['batch_number'], 'BATCH-0001')
        self.assertEqual(data['data']['fastener_type'], 'Hex Bolt')

        # Not found
        res_404 = self.client.get('/api/batches/BATCH-9999')
        self.assertEqual(res_404.status_code, 404)
        data_404 = res_404.get_json()
        self.assertFalse(data_404['success'])
        self.assertIn('was not found', data_404['error'])

    def test_05_historical_status_service(self):
        """Test point-in-time status query logic and end-of-day timestamp handling."""
        # Seed fresh for BATCH-0001
        seed_database(force=True)

        # On September 25, 2026: Material Preparation (10%) at 8:30 and Manufacturing (20%) at 14:00
        status_sep25, err = get_batch_status_at_datetime('BATCH-0001', '2026-09-25')
        self.assertIsNone(err)
        self.assertTrue(status_sep25['found'])
        self.assertEqual(status_sep25['status'], 'Manufacturing')
        self.assertEqual(status_sep25['progress'], 20)

        # On September 25 at 10:00: Should be Material Preparation
        status_sep25_morning, err = get_batch_status_at_datetime('BATCH-0001', datetime(2026, 9, 25, 10, 0, 0))
        self.assertIsNone(err)
        self.assertTrue(status_sep25_morning['found'])
        self.assertEqual(status_sep25_morning['status'], 'Material Preparation')
        self.assertEqual(status_sep25_morning['progress'], 10)

        # On September 26, 2026: Manufacturing (65%)
        status_sep26, err = get_batch_status_at_datetime('BATCH-0001', '2026-09-26')
        self.assertIsNone(err)
        self.assertTrue(status_sep26['found'])
        self.assertEqual(status_sep26['status'], 'Manufacturing')
        self.assertEqual(status_sep26['progress'], 65)

        # On September 20, 2026 (before creation): Should return found=False, NOT fall back to current status!
        status_before, err = get_batch_status_at_datetime('BATCH-0001', '2026-09-20')
        self.assertIsNone(err)
        self.assertFalse(status_before['found'])
        self.assertNotIn('status', status_before)

    def test_06_lifecycle_advance_and_completion(self):
        """Test advance batch, complete batch, idempotency, and invalid transitions."""
        seed_database(force=True)

        # Initial state: Manufacturing 65%
        batch = get_batch_by_number('BATCH-0001')
        self.assertEqual(batch['current_status'], 'Manufacturing')
        self.assertEqual(batch['progress'], 65)

        # Advance: Manufacturing -> Quality Inspection (90%)
        res_adv = self.client.post('/api/batches/BATCH-0001/advance')
        self.assertEqual(res_adv.status_code, 200)
        data_adv = res_adv.get_json()
        self.assertTrue(data_adv['success'])
        self.assertEqual(data_adv['data']['current_status'], 'Quality Inspection')
        self.assertEqual(data_adv['data']['progress'], 90)

        # Complete batch: Quality Inspection -> Completed (100%)
        res_comp = self.client.post('/api/batches/BATCH-0001/complete')
        self.assertEqual(res_comp.status_code, 200)
        data_comp = res_comp.get_json()
        self.assertTrue(data_comp['success'])
        self.assertEqual(data_comp['data']['current_status'], 'Completed')
        self.assertEqual(data_comp['data']['progress'], 100)
        self.assertIsNotNone(data_comp['data']['actual_completion'])

        # Double click complete: Idempotent (does not error, does not add duplicate history record)
        history_before = get_batch_history('BATCH-0001')
        res_comp2 = self.client.post('/api/batches/BATCH-0001/complete')
        self.assertEqual(res_comp2.status_code, 200)
        history_after = get_batch_history('BATCH-0001')
        self.assertEqual(len(history_before), len(history_after))

        # Invalid transition: Cannot advance from Completed (returns 409)
        res_invalid = self.client.post('/api/batches/BATCH-0001/advance')
        self.assertEqual(res_invalid.status_code, 409)
        data_inv = res_invalid.get_json()
        self.assertFalse(data_inv['success'])
        self.assertIn('Invalid lifecycle transition', data_inv['error'])

    def test_07_quality_api(self):
        """Test GET /api/quality and GET /api/batches/<batch_number>/quality."""
        seed_database(force=True)

        res_q = self.client.get('/api/quality')
        self.assertEqual(res_q.status_code, 200)
        data_q = res_q.get_json()
        self.assertTrue(data_q['success'])
        self.assertGreaterEqual(data_q['data']['passed'], 1)
        self.assertGreaterEqual(data_q['data']['hold'], 1)

        res_b_q = self.client.get('/api/batches/BATCH-0001/quality')
        self.assertEqual(res_b_q.status_code, 200)
        data_b_q = res_b_q.get_json()
        self.assertTrue(data_b_q['success'])
        self.assertEqual(data_b_q['data']['latest_inspection']['overall_result'], 'PASSED')
        self.assertEqual(data_b_q['data']['latest_inspection']['hardness'], '32 HRC')

    def test_08_production_api(self):
        """Test GET /api/production returns active batches grouped by line."""
        seed_database(force=True)

        res_p = self.client.get('/api/production')
        self.assertEqual(res_p.status_code, 200)
        data_p = res_p.get_json()
        self.assertTrue(data_p['success'])
        self.assertGreaterEqual(data_p['active_count'], 1)
        self.assertGreaterEqual(len(data_p['production_lines']), 1)

    def test_09_reports_api(self):
        """Test GET /api/reports/<batch_number> returns live database values."""
        seed_database(force=True)

        res_r = self.client.get('/api/reports/BATCH-0001')
        self.assertEqual(res_r.status_code, 200)
        data_r = res_r.get_json()
        self.assertTrue(data_r['success'])
        self.assertEqual(data_r['data']['batch_number'], 'BATCH-0001')
        self.assertEqual(data_r['data']['material'], 'Carbon Steel')
        self.assertEqual(data_r['data']['grade'], '8.8')

    def test_10_ai_grounded_context_and_hallucination_prevention(self):
        """Test AI context generation and hallucination prevention on unsupported parameters."""
        seed_database(force=True)

        # 1. Unsupported parameter test (CNC temperature)
        res_temp = process_ai_query("What is the CNC temperature for BATCH-0001?")
        self.assertTrue(res_temp['success'])
        self.assertIn("The requested information is not available in the manufacturing records.", res_temp['answer'])

        # 2. Non-existent batch test
        res_none = process_ai_query("What is the status of BATCH-9999?")
        self.assertTrue(res_none['success'])
        self.assertIn("Batch BATCH-9999 was not found", res_none['answer'])

        # 3. Quality query test
        res_qa = process_ai_query("Did BATCH-0001 pass quality inspection?")
        self.assertTrue(res_qa['success'])
        self.assertIn("passed", res_qa['answer'].lower())
        self.assertIn("32 HRC", res_qa['answer'])

        # 4. Specification test
        res_mat = process_ai_query("What material was used for BATCH-0001?")
        self.assertTrue(res_mat['success'])
        self.assertIn("Carbon Steel", res_mat['answer'])
        self.assertIn("8.8", res_mat['answer'])

    def test_11_critical_state_preservation_workflow(self):
        """
        CRITICAL TEST CASE (Requirement #64):
        1. BATCH-0001 in Manufacturing 65%.
        2. Query current status -> Manufacturing 65%.
        3. Query historical status on Sep 26 -> Manufacturing 65%.
        4. Advance batch -> Quality Inspection 90%.
        5. Query current status -> Quality Inspection.
        6. Query historical status on Sep 26 -> MUST STILL BE Manufacturing 65% (unaffected by lifecycle advance)!
        """
        seed_database(force=True)

        # 1. Ask current status
        res_curr1 = process_ai_query("What is the current status of BATCH-0001?")
        self.assertIn("Manufacturing", res_curr1['answer'])
        self.assertIn("65%", res_curr1['answer'])

        # 2. Ask historical status on September 26
        res_hist1 = process_ai_query("What was the status of BATCH-0001 on September 26?")
        self.assertTrue(res_hist1['historical'])
        self.assertIn("Manufacturing", res_hist1['answer'])
        self.assertIn("65%", res_hist1['answer'])

        # 3. Advance batch
        advance_batch('BATCH-0001')

        # 4. Ask current status
        res_curr2 = process_ai_query("What is the current status of BATCH-0001?")
        self.assertIn("Quality Inspection", res_curr2['answer'])
        self.assertIn("90%", res_curr2['answer'])

        # 5. Ask historical status on September 26 again
        res_hist2 = process_ai_query("What was the status of BATCH-0001 on September 26?")
        self.assertTrue(res_hist2['historical'])
        # The historical answer MUST NOT change merely because current status changed!
        self.assertIn("Manufacturing", res_hist2['answer'])
        self.assertIn("65%", res_hist2['answer'])
        self.assertNotIn("Quality Inspection", res_hist2['answer'])

    def test_12_multi_batch_queries(self):
        """Test multi-batch and aggregate AI queries."""
        seed_database(force=True)

        # Active manufacturing batches
        res_mfg = process_ai_query("Which batches are currently manufacturing?")
        self.assertTrue(res_mfg['success'])
        self.assertIn("Manufacturing", res_mfg['answer'])

        # Quality hold batches
        res_hold = process_ai_query("Which batches are on quality hold?")
        self.assertTrue(res_hold['success'])
        self.assertIn("BATCH-0009", res_hold['answer'])

        # Total bolt count
        res_bolts = process_ai_query("How many bolts were manufactured?")
        self.assertTrue(res_bolts['success'])
        self.assertIn("bolts", res_bolts['answer'].lower())

    def test_13_batch_specifications(self):
        """Test specification and equipment queries for a batch."""
        seed_database(force=True)

        res_spec = process_ai_query("What machine produced BATCH-0001?")
        self.assertTrue(res_spec['success'])
        self.assertIn("CNC-04", res_spec['answer'])
        self.assertIn("Operator-07", res_spec['answer'])

    def test_14_unknown_questions(self):
        """Test unknown and out-of-domain questions."""
        seed_database(force=True)

        res_unk = process_ai_query("Who won the football championship yesterday?")
        self.assertTrue(res_unk['success'])
        self.assertIn("I can answer questions about FASTENPRO", res_unk['answer'])

    def test_15_api_ai_chat_endpoint(self):
        """Test POST /api/ai/chat endpoint directly via HTTP."""
        seed_database(force=True)

        # Empty question
        res_empty = self.client.post('/api/ai/chat', json={})
        self.assertEqual(res_empty.status_code, 400)

        # Valid question
        res_valid = self.client.post('/api/ai/chat', json={'question': 'What is the status of BATCH-0001?'})
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()
        self.assertTrue(data['success'])
        self.assertIn('answer', data)
        self.assertEqual(data['batch_number'], 'BATCH-0001')

if __name__ == '__main__':
    unittest.main()

