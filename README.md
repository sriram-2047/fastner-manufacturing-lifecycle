# FASTENPRO AI — Fastener Manufacturing Intelligence Platform

FASTENPRO AI is an industrial-grade manufacturing intelligence platform designed for fastener production enterprises. It tracks the complete manufacturing lifecycle of fastener batches in real-time, maintains immutable historical audit records, manages quality assurance metrology, and provides a database-grounded AI Copilot powered by local Ollama.

---

## 🌟 Key Features

1. **Real-Time Lifecycle Tracking**: Tracks batches across 5 defined stages: *Scheduled*, *Material Preparation*, *Manufacturing*, *Quality Inspection*, and *Completed* (with *Quality Hold* quarantine support).
2. **Immutable Status History**: Every lifecycle transition creates an audit-grade timestamped record in `batch_status_history`. Historical data is **never** overwritten or deleted.
3. **Point-in-Time Historical AI Queries**: Users can ask relative or explicit historical questions (e.g., *"What was the status of BATCH-0001 two days ago?"* or *"What was the status on September 25?"*), and the AI will accurately inspect historical audit records (`batch_status_history`) instead of reporting current status.
4. **100% Database-Grounded AI Copilot**: Eliminates hallucinations by extracting structured facts from SQLite before prompting local Ollama. If a parameter (e.g., machine temperature) is not tracked, it explicitly answers: *"The requested information is not available in the manufacturing records."*
5. **Quality Assurance & Metrology**: Tracks dimensional conformity, thread pitch tolerances, surface finish, Rockwell hardness (HRC), and tensile strength (MPa).
6. **Interactive Demo Controls**: Single-click `ADVANCE BATCH` and `COMPLETE BATCH` simulation controls with atomic transactional integrity (`db.session.commit()` with rollback) and instant UI updates.
7. **Comprehensive Reporting & Export**: Printable Fastener Production Traceability Summaries with complete audit trails.

---

## 🏗️ Backend Architecture

The backend serves as the **single source of truth** for all business metrics, production counters, status histories, quality evaluations, and AI context:

```text
                    USER / BROWSER
                          ↓
               EXISTING FASTENPRO UI
             (HTML5 / Vanilla CSS / JS)
                          ↓
                    FLASK API
          (Validation & Error Handling)
                          ↓
                    SERVICE LAYER
    ┌─────────────────────┼─────────────────────┐
    ↓                     ↓                     ↓
Batch Service      History Service       Quality Service
    ↓                     ↓                     ↓
    └─────────────────────┼─────────────────────┘
                          ↓
                   SQLALCHEMY ORM
                          ↓
                    SQLITE DB
        (batches, batch_status_history, quality_inspections)
                          ↓
                 AI CONTEXT BUILDER
      (Deterministic Extraction & Strict Prompt)
                          ↓
                 LOCAL OLLAMA ENGINE
               (Default: gemma3:1b)
                          ↓
                 GROUNDED AI RESPONSE
```

---

## 🗄️ Database Structure

The database consists of normalized relational tables managed via SQLAlchemy ORM:

### 1. `batches`
- `id` (Integer, Primary Key)
- `batch_number` (String, Unique, Indexed) — e.g., `BATCH-0001`
- `fastener_type` (String) — e.g., `Hex Bolt`, `Flange Nut`
- `part_number` (String) — e.g., `HB-M10-050`
- `material` (String) — e.g., `Carbon Steel`
- `grade` (String) — e.g., `8.8`, `10.9`
- `coating` (String) — e.g., `Zinc Plated`
- `diameter` (String) — e.g., `M10`
- `length` (String) — e.g., `50 mm`
- `thread_type` (String) — e.g., `Metric`
- `thread_pitch` (String) — e.g., `1.5 mm`
- `head_type` (String) — e.g., `Hexagonal`
- `quantity` (Integer) — e.g., `10000`
- `customer` (String) — e.g., `Automotive Dynamics Corp`
- `production_line` (String) — e.g., `LINE-02`
- `machine` (String) — e.g., `CNC-04`
- `operator` (String) — e.g., `Operator-07`
- `current_status` (String) — `Scheduled` | `Material Preparation` | `Manufacturing` | `Quality Inspection` | `Completed` | `Quality Hold`
- `progress` (Integer, 0-100)
- `manufacturing_start` (DateTime)
- `expected_completion` (DateTime)
- `actual_completion` (DateTime, Nullable)
- `created_at` / `updated_at` (DateTime)

### 2. `batch_status_history` (Immutable Audit Log)
- `id` (Integer, Primary Key)
- `batch_id` (Integer, Foreign Key -> `batches.id`)
- `status` (String)
- `progress` (Integer)
- `timestamp` (DateTime, Indexed)
- `remarks` (Text)

### 3. `quality_inspections`
- `id` (Integer, Primary Key)
- `batch_id` (Integer, Foreign Key -> `batches.id`)
- `dimensional_result` (String) — `PASS` | `FAIL` | `PENDING`
- `thread_result` (String) — `PASS` | `FAIL` | `PENDING`
- `surface_result` (String) — `PASS` | `FAIL` | `PENDING`
- `hardness` (String) — e.g., `32 HRC`
- `tensile_strength` (String) — e.g., `800 MPa`
- `overall_result` (String) — `PASSED` | `FAILED` | `HOLD` | `PENDING`
- `inspection_date` (DateTime)
- `remarks` (Text)

---

## 🔌 API Endpoints Reference

All endpoints return a uniform JSON envelope: `{"success": true/false, "data": {...}}` or `{"success": false, "error": "...", "code": "..."}`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health (DB status, Ollama status, model) |
| `GET` | `/api/dashboard` | Aggregated dashboard KPIs and recent batches |
| `GET` | `/api/batches` | List batches (supports `?search=`, `?status=`, `?line=`) |
| `GET` | `/api/batches/<batch_number>` | Complete batch details |
| `GET` | `/api/batches/<batch_number>/history` | Historical audit log for batch |
| `GET` | `/api/batches/<batch_number>/quality` | Quality inspection data for batch |
| `GET` | `/api/production` | Active production batches grouped/filtered |
| `GET` | `/api/quality` | QA dashboard metrics, test statistics & quarantine logs |
| `GET` | `/api/reports/<batch_number>` | Complete traceability report data |
| `POST` | `/api/batches/<batch_number>/advance` | Transactional lifecycle stage advance |
| `POST` | `/api/batches/<batch_number>/complete` | Transactional completion with 100% progress |
| `POST` | `/api/ai/chat` | Database-grounded natural language AI Copilot |
| `GET` | `/api/ai/status` | AI engine connection and model status |

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `FLASK_ENV` | `development` | Flask runtime environment |
| `SECRET_KEY` | `fastenpro-super-secret-key-2026` | Flask session secret key |
| `DATABASE_URL` | `sqlite:///database/fastener.db` | SQLite database URI |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama local HTTP API address |
| `OLLAMA_MODEL` | `gemma3:1b` | Target local LLM model |
| `OLLAMA_TIMEOUT` | `15` | Ollama API HTTP timeout (seconds) |

---

## 🦙 Local Ollama Setup & Installation

FASTENPRO AI integrates directly with a locally running Ollama instance without third-party cloud AI APIs:

1. **Install Ollama**: Download from [https://ollama.com](https://ollama.com).
2. **Start Ollama Daemon**:
   ```bash
   ollama serve
   ```
3. **Pull Target Model**:
   ```bash
   ollama pull gemma3:1b
   ```
4. **Verify Model**:
   ```bash
   ollama list
   ```

*Note: If Ollama is not running, the application gracefully operates in `database_fallback` mode via its internal grounded query engine. The UI sidebar truthfully indicates `● Ollama Offline` and `● Database Connected`.*

---

## 🚀 Running the Application

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database
```bash
python seed.py
```
*(Use `python seed.py --force` to cleanly re-create and populate the database with all 12 demo batches).*

### 3. Start Flask Server
```bash
python app.py
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## 💬 AI Query Examples & Grounding Behavior

The AI Copilot uses strict deterministic entity and date extraction before querying SQLite:

### 1. Current Status Query
- **Question**: `What is the current status of BATCH-0001?`
- **Context**: Queries `batches` table.
- **Answer**: *"BATCH-0001 is currently in the Manufacturing stage with 65% completion. Started on 2026-09-25 with expected completion on 2026-09-27."*

### 2. Point-in-Time Historical Query (End-of-Day)
- **Question**: `What was the status of BATCH-0001 on September 25?`
- **Context**: Queries `batch_status_history` where `timestamp <= 2026-09-25 23:59:59`.
- **Answer**: *"On September 25, 2026, BATCH-0001 was in the Manufacturing stage with 20% progress (after Material Preparation at 10%)."*

### 3. Relative Date Historical Query
- **Question**: `What was the status of BATCH-0001 two days ago?`
- **Context**: Calculates target date relative to current time and queries audit log.
- **Answer**: *"On September 26, 2026, BATCH-0001 was at 65% progress in Manufacturing."*

### 4. Quality Inspection Query
- **Question**: `Did BATCH-0001 pass quality inspection?`
- **Context**: Queries `quality_inspections` table.
- **Answer**: *"BATCH-0001 overall inspection result is PASSED. Dimensional: PASS, Thread: PASS, Surface: PASS, Hardness: 32 HRC, Tensile: 800 MPa."*

### 5. Multi-Batch Query
- **Question**: `Which batches are currently manufacturing?`
- **Context**: Aggregates all batches where `current_status = 'Manufacturing'`.
- **Answer**: Lists active manufacturing batches (`BATCH-0001`, `BATCH-0004`, `BATCH-0009`) with their lines and operators.

### 6. Hallucination Prevention (Untracked Parameters)
- **Question**: `What is the CNC temperature for BATCH-0001?`
- **Answer**: *"The requested information is not available in the manufacturing records."*

---

## 🧪 Automated Testing

FASTENPRO includes a comprehensive automated test suite covering all critical requirements:

```bash
python tests/test_backend.py
```

Test coverage includes:
1. `test_01_health_check` — Truthful health reporting for DB and Ollama.
2. `test_02_dashboard_kpis` — Aggregate calculations from SQLite.
3. `test_03_batch_search_and_case_insensitivity` — Normalized batch lookup.
4. `test_04_batch_not_found_404` — Clean 404 response.
5. `test_05_initial_batch_0001_state` — Verifies 65% Manufacturing and no pre-completed history.
6. `test_06_historical_status_point_in_time` — Accurate status at past timestamps.
7. `test_07_advance_batch_lifecycle` — Transactional stage advancement.
8. `test_08_complete_batch_lifecycle` — 100% completion with timestamp.
9. `test_09_duplicate_completion_idempotency` — Prevents double-click duplicate records.
10. `test_10_invalid_transition_409` — Rejects advancing completed batches.
11. `test_11_production_endpoint` — Active floor batch filtering.
12. `test_12_quality_endpoint` — Metrology KPIs and logs.
13. `test_13_report_endpoint` — Traceability report generation.
14. `test_14_ai_current_status_query` — Database-grounded query.
15. `test_15_ai_hallucination_prevention` — Explicit rejection of unrecorded parameters.

---

## 🔧 Troubleshooting

- **Ollama Offline**: If the sidebar shows `● Ollama Offline`, ensure `ollama serve` is running in your terminal and `OLLAMA_BASE_URL` in `.env` is reachable. The app will automatically switch back to Ollama once reachable.
- **Model Not Found**: Run `ollama pull gemma3:1b` if Ollama returns a model not found error.
- **Database Reset**: If you need to restore the baseline demo state, run `python seed.py --force`.

---

## 🚀 Deploying to Vercel

FASTENPRO AI is fully configured for seamless one-click Vercel deployment.

### Steps to Deploy:
1. Push this repository to GitHub (`https://github.com/sriram-2047/fastner-manufacturing-lifecycle`).
2. Go to [Vercel Dashboard](https://vercel.com/new).
3. Import the `fastner-manufacturing-lifecycle` repository.
4. Framework Preset: **Other** (Root directory: `./`).
5. (Optional) Set Environment Variables:
   - `SECRET_KEY`: `your-production-secret-key`
   - `OLLAMA_BASE_URL`: `https://your-ollama-host.example.com` (or leave default for automated offline deterministic engine)
6. Click **Deploy**.

Vercel automatically detects `vercel.json` and `@vercel/python` serverless WSGI runtime, self-seeds the database on cold-start in writable `/tmp/fastener.db`, and serves all dashboard, batch management, quality, and AI copilot routes.

---

## 📦 Production Deployment Notes

- Use a production WSGI server such as `gunicorn` or `waitress`:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:5000 app:app
  ```
- Configure CORS origins appropriately in `app.py` for restricted domain deployments.
- For multi-tenant setups, transition `DATABASE_URL` in `.env` to PostgreSQL.


