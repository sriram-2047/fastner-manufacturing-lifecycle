import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from dotenv import load_dotenv

try:
    from flask_cors import CORS
    has_flask_cors = True
except ImportError:
    has_flask_cors = False

from database import init_db, db_session
from models import Batch, BatchStatusHistory, QualityInspection, FastenerType
from services.batch_service import (
    get_all_batches,
    get_batch_by_number,
    get_dashboard_kpis,
    advance_batch,
    complete_batch
)
from sqlalchemy import text
from services.history_service import get_batch_history, get_batch_status_at_datetime
from services.quality_service import get_quality_overview, get_batch_quality
from services.ai_service import process_ai_query
from ai.ollama import check_ollama_status, OLLAMA_MODEL

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fastenpro-dev-key-2026')
app.config['JSON_SORT_KEYS'] = False

if has_flask_cors:
    CORS(app)
else:
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

# Ensure database tables exist at start
with app.app_context():
    init_db()

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# ---------------------------------------------------------
# PAGE ROUTES (HTML Templates)
# ---------------------------------------------------------

@app.route('/')
@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/batches')
def batches_page():
    return render_template('batches.html', active_page='batches')

@app.route('/batches/<batch_number>')
def batch_detail_page(batch_number):
    normalized = batch_number.strip().upper()
    batch = get_batch_by_number(normalized, include_relations=True)
    if not batch:
        return render_template('batch_detail.html', active_page='batches', batch=None, batch_number=normalized, not_found=True), 404
    return render_template('batch_detail.html', active_page='batches', batch=batch, batch_number=normalized, not_found=False)

@app.route('/production')
def production_page():
    return render_template('production.html', active_page='production')

@app.route('/quality')
def quality_page():
    return render_template('quality.html', active_page='quality')

@app.route('/reports')
@app.route('/reports/<batch_number>')
def reports_page(batch_number=None):
    selected_batch = batch_number.strip().upper() if batch_number else "BATCH-0001"
    return render_template('reports.html', active_page='reports', selected_batch=selected_batch)

@app.route('/ai')
@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot.html', active_page='ai')

# ---------------------------------------------------------
# REST API ENDPOINTS (JSON)
# ---------------------------------------------------------

@app.route('/api/health', methods=['GET'])
@app.route('/api/ollama/health', methods=['GET'])
def api_health():
    try:
        db_status = "connected"
        try:
            db_session.execute(text("SELECT 1"))
        except Exception:
            db_status = "offline"

        ollama_status_info = check_ollama_status()
        ollama_status = "connected" if ollama_status_info.get('available') else "offline"

        return jsonify({
            'success': True,
            'data': {
                'backend': 'healthy',
                'database': db_status,
                'ollama': ollama_status,
                'ollama_model': OLLAMA_MODEL,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    try:
        data = get_dashboard_kpis()
        return jsonify({'success': True, 'data': data}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches', methods=['GET'])
def api_batches():
    try:
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        line = request.args.get('line', '')
        material = request.args.get('material', '')
        batches = get_all_batches(search=search, status=status, line=line, material=material)
        return jsonify({'success': True, 'count': len(batches), 'data': batches}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches/<batch_number>', methods=['GET'])
def api_batch_detail(batch_number):
    try:
        batch = get_batch_by_number(batch_number, include_relations=True)
        if not batch:
            return jsonify({
                'success': False,
                'error': f"Batch {batch_number.strip().upper()} was not found."
            }), 404
        return jsonify({'success': True, 'data': batch}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches/<batch_number>/history', methods=['GET'])
def api_batch_history(batch_number):
    try:
        history = get_batch_history(batch_number)
        return jsonify({'success': True, 'data': history}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches/<batch_number>/quality', methods=['GET'])
def api_batch_quality(batch_number):
    try:
        quality = get_batch_quality(batch_number)
        if not quality:
            return jsonify({'success': False, 'error': f"Batch {batch_number.strip().upper()} quality data not found."}), 404
        return jsonify({'success': True, 'data': quality}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches/<batch_number>/advance', methods=['POST'])
def api_advance_batch(batch_number):
    try:
        payload = request.get_json(silent=True) or {}
        remarks = payload.get('remarks')
        updated_batch, err, status_code = advance_batch(batch_number, custom_remarks=remarks)
        if err and not updated_batch:
            return jsonify({'success': False, 'error': err}), status_code
        return jsonify({
            'success': True,
            'message': err if err else f"Batch {batch_number} advanced successfully.",
            'data': updated_batch
        }), status_code
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batches/<batch_number>/complete', methods=['POST'])
def api_complete_batch(batch_number):
    try:
        payload = request.get_json(silent=True) or {}
        remarks = payload.get('remarks')
        updated_batch, err, status_code = complete_batch(batch_number, custom_remarks=remarks)
        if err and not updated_batch:
            return jsonify({'success': False, 'error': err}), status_code
        return jsonify({
            'success': True,
            'message': err if err else f"Batch {batch_number} completed successfully.",
            'data': updated_batch
        }), status_code
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/production', methods=['GET'])
def api_production():
    try:
        all_batches = get_all_batches()
        active_batches = [b for b in all_batches if b['current_status'] in ['Manufacturing', 'Material Preparation', 'Quality Inspection']]
        
        # Line grouping
        lines = {}
        for b in active_batches:
            line_name = b['production_line']
            if line_name not in lines:
                lines[line_name] = {'line': line_name, 'batches': [], 'total_active_units': 0}
            lines[line_name]['batches'].append(b)
            lines[line_name]['total_active_units'] += b['quantity']

        prod_data = {
            'active_count': len(active_batches),
            'active_batches': active_batches,
            'production_lines': list(lines.values())
        }
        return jsonify({
            'success': True,
            'data': prod_data,
            'active_count': len(active_batches),
            'active_batches': active_batches,
            'production_lines': list(lines.values())
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/quality', methods=['GET'])
def api_quality():
    try:
        overview = get_quality_overview()
        return jsonify({'success': True, 'data': overview}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/<batch_number>', methods=['GET'])
def api_report_detail(batch_number):
    try:
        batch = get_batch_by_number(batch_number, include_relations=True)
        if not batch:
            return jsonify({'success': False, 'error': f"Batch {batch_number.strip().upper()} not found."}), 404
        return jsonify({'success': True, 'data': batch}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    try:
        payload = request.get_json(silent=True) or {}
        question = payload.get('question')
        context_batch = payload.get('batch_number')

        if not question or not str(question).strip():
            return jsonify({'success': False, 'error': 'Please provide a valid question.'}), 400

        result = process_ai_query(question, current_context_batch=context_batch)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"AI Copilot encountered an unexpected error: {str(e)}"
        }), 500

@app.route('/api/ai/status', methods=['GET'])
def api_ai_status():
    try:
        status = check_ollama_status()
        return jsonify({'success': True, 'data': status}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Resource not found.'}), 404
    return render_template('base.html', not_found_page=True), 404

@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error.'}), 500
    return render_template('base.html', server_error_page=True), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
