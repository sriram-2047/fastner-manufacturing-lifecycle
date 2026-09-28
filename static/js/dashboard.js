/**
 * FastenPro AI — Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  loadDashboardData();

  // Search form handler
  const searchForm = document.getElementById('dashboard-search-form');
  const searchInput = document.getElementById('dashboard-search-input');
  if (searchForm && searchInput) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const raw = searchInput.value.trim();
      if (!raw) return;

      let normalized = raw.toUpperCase().replace(/\s+/g, '-');
      if (/^\d+$/.test(normalized)) {
        normalized = `BATCH-${normalized.padStart(4, '0')}`;
      } else if (/^BATCH\d+$/.test(normalized)) {
        normalized = normalized.replace('BATCH', 'BATCH-');
      }
      window.location.href = `/batches/${normalized}`;
    });
  }

  // Quick AI Form
  const quickAiForm = document.getElementById('quick-ai-form');
  const quickAiInput = document.getElementById('quick-ai-input');
  if (quickAiForm && quickAiInput) {
    quickAiForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const q = quickAiInput.value.trim();
      if (!q) return;
      askQuickAi(q);
      quickAiInput.value = '';
    });
  }
});

async function loadDashboardData() {
  const res = await apiGet('/api/dashboard');
  if (!res.success || !res.data) {
    showToast('Failed to load dashboard metrics', 'error');
    return;
  }

  const d = res.data;

  // Update KPI counters
  document.getElementById('kpi-total-batches').textContent = d.total_batches || 0;
  document.getElementById('kpi-active-manufacturing').textContent = d.active_manufacturing || 0;
  document.getElementById('kpi-completed').textContent = d.completed || 0;
  document.getElementById('kpi-quality-hold').textContent = d.quality_hold || 0;

  if (d.total_units) {
    document.getElementById('kpi-total-units').textContent = `${d.total_units.toLocaleString()} total units`;
  }
  if (d.completed_units) {
    document.getElementById('kpi-completed-units').textContent = `${d.completed_units.toLocaleString()} units finished`;
  }

  // Render recent batches table
  const tbody = document.getElementById('recent-batches-tbody');
  if (!tbody) return;

  if (!d.recent_batches || d.recent_batches.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: var(--text-muted);">No batches found.</td></tr>`;
    return;
  }

  tbody.innerHTML = d.recent_batches.map(batch => {
    let progressClass = '';
    if (batch.current_status === 'Completed') progressClass = 'complete';
    else if (batch.current_status === 'Quality Hold') progressClass = 'hold';

    return `
      <tr>
        <td>
          <a href="/batches/${batch.batch_number}" class="batch-code" style="text-decoration: underline dotted;">
            ${batch.batch_number}
          </a>
        </td>
        <td>
          <strong>${batch.fastener_type}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${batch.part_number}</div>
        </td>
        <td>${batch.quantity.toLocaleString()}</td>
        <td>${formatStatusBadge(batch.current_status)}</td>
        <td>
          <div class="progress-container" style="max-width: 140px;">
            <div class="progress-track">
              <div class="progress-fill ${progressClass}" style="width: ${batch.progress}%;"></div>
            </div>
            <span class="progress-pct">${batch.progress}%</span>
          </div>
        </td>
        <td>
          <a href="/batches/${batch.batch_number}" class="btn btn-secondary btn-sm">Inspect</a>
        </td>
      </tr>
    `;
  }).join('');
}

async function askQuickAi(question) {
  const resultDiv = document.getElementById('quick-ai-result');
  if (!resultDiv) return;

  resultDiv.innerHTML = `
    <div style="display:flex; align-items:center; gap: 0.5rem; color: var(--accent-blue);">
      <div class="spinner"></div>
      <span>Analyzing batch records...</span>
    </div>
  `;

  const res = await apiPost('/api/ai/chat', { question: question });
  const dataObj = (res.data && typeof res.data === 'object' && res.data.answer) ? res.data : res;

  if (res.success && dataObj.answer) {
    resultDiv.innerHTML = `
      <div style="width: 100%;">
        <div style="font-size: 0.75rem; color: var(--accent-blue); font-weight: 600; margin-bottom: 0.35rem; display: flex; justify-content: space-between;">
          <span>Q: ${question}</span>
          <span>${dataObj.historical ? 'Historical ' + (dataObj.date || '') : 'Live Data'}</span>
        </div>
        <div style="color: var(--text-primary); line-height: 1.45;">
          ${dataObj.answer}
        </div>
      </div>
    `;
  } else {
    resultDiv.innerHTML = `
      <div style="color: var(--status-hold);">
        ${res.error || 'AI service is currently unavailable.'}
      </div>
    `;
  }
}
