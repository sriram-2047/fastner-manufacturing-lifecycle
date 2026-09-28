/**
 * FastenPro AI — Batches Page Controller
 */

let allBatchesData = [];

document.addEventListener('DOMContentLoaded', () => {
  fetchBatches();

  const searchInput = document.getElementById('batch-filter-search');
  const statusSelect = document.getElementById('batch-filter-status');
  const lineSelect = document.getElementById('batch-filter-line');

  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (statusSelect) statusSelect.addEventListener('change', applyFilters);
  if (lineSelect) lineSelect.addEventListener('change', applyFilters);
});

async function fetchBatches() {
  const res = await apiGet('/api/batches');
  if (res.success && res.data) {
    allBatchesData = res.data;
    renderBatches(allBatchesData);
  } else {
    showToast('Failed to load batches list', 'error');
  }
}

function applyFilters() {
  const searchVal = (document.getElementById('batch-filter-search')?.value || '').toLowerCase().trim();
  const statusVal = document.getElementById('batch-filter-status')?.value || 'ALL';
  const lineVal = document.getElementById('batch-filter-line')?.value || 'ALL';

  const filtered = allBatchesData.filter(b => {
    // Search match
    const matchSearch = !searchVal || 
      b.batch_number.toLowerCase().includes(searchVal) ||
      b.fastener_type.toLowerCase().includes(searchVal) ||
      b.part_number.toLowerCase().includes(searchVal) ||
      b.material.toLowerCase().includes(searchVal) ||
      b.operator.toLowerCase().includes(searchVal) ||
      b.machine.toLowerCase().includes(searchVal);

    // Status match
    const matchStatus = statusVal === 'ALL' || b.current_status === statusVal;

    // Line match
    const matchLine = lineVal === 'ALL' || b.production_line === lineVal;

    return matchSearch && matchStatus && matchLine;
  });

  renderBatches(filtered);
}

function renderBatches(batches) {
  const tbody = document.getElementById('all-batches-tbody');
  const badge = document.getElementById('batch-count-badge');
  if (!tbody) return;

  if (badge) {
    badge.textContent = `Showing ${batches.length} batch${batches.length === 1 ? '' : 'es'}`;
  }

  if (batches.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; padding: 3rem; color: var(--text-muted);">
          No batches match your selected criteria.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = batches.map(batch => {
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
        <td>
          <div>${batch.material}</div>
          <span style="font-size: 0.75rem; color: var(--accent-blue);">Grade ${batch.grade}</span>
        </td>
        <td>${batch.quantity.toLocaleString()}</td>
        <td>
          <div>${batch.production_line}</div>
          <span style="font-size: 0.75rem; color: var(--text-muted);">${batch.machine}</span>
        </td>
        <td>${formatStatusBadge(batch.current_status)}</td>
        <td>
          <div class="progress-container" style="max-width: 130px;">
            <div class="progress-track">
              <div class="progress-fill ${progressClass}" style="width: ${batch.progress}%;"></div>
            </div>
            <span class="progress-pct">${batch.progress}%</span>
          </div>
        </td>
        <td style="font-size: 0.85rem; color: var(--text-secondary);">
          ${formatDate(batch.expected_completion)}
        </td>
        <td>
          <a href="/batches/${batch.batch_number}" class="btn btn-secondary btn-sm">Inspect</a>
        </td>
      </tr>
    `;
  }).join('');
}
