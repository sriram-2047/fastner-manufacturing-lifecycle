/**
 * FastenPro AI — Production Floor Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  fetchProductionFloorData();
});

async function fetchProductionFloorData() {
  const container = document.getElementById('production-lines-container');
  if (!container) return;

  const res = await apiGet('/api/production');
  if (!res.success || !res.production_lines) {
    container.innerHTML = `<div class="panel" style="color: var(--status-hold); padding: 2rem; text-align: center;">Failed to load production data.</div>`;
    return;
  }

  const lines = res.production_lines;
  if (lines.length === 0) {
    container.innerHTML = `<div class="panel" style="color: var(--text-muted); padding: 3rem; text-align: center;">No active production runs currently in progress.</div>`;
    return;
  }

  container.innerHTML = lines.map(lineData => {
    const batches = lineData.batches || [];
    return `
      <div class="panel" style="margin-bottom: 2rem;">
        <div class="panel-header">
          <div>
            <h2 class="panel-title" style="color: #fff;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00f2fe" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
              <span>${lineData.line}</span>
            </h2>
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">
              ${batches.length} active batch${batches.length === 1 ? '' : 'es'} &bull; ${lineData.total_active_units.toLocaleString()} total units in process
            </div>
          </div>
          <span class="status-badge badge-manufacturing">OPERATIONAL</span>
        </div>

        <div class="table-responsive">
          <table class="industrial-table">
            <thead>
              <tr>
                <th>Batch Number</th>
                <th>Fastener / Part Number</th>
                <th>Machine Station</th>
                <th>Lead Operator</th>
                <th>Current Stage</th>
                <th>Progress</th>
                <th>Expected Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${batches.map(b => {
                let progressClass = '';
                if (b.current_status === 'Completed') progressClass = 'complete';
                else if (b.current_status === 'Quality Hold') progressClass = 'hold';

                return `
                  <tr>
                    <td>
                      <a href="/batches/${b.batch_number}" class="batch-code" style="text-decoration: underline dotted;">
                        ${b.batch_number}
                      </a>
                    </td>
                    <td>
                      <strong>${b.fastener_type}</strong>
                      <div style="font-size: 0.75rem; color: var(--text-muted);">${b.part_number} (${b.quantity.toLocaleString()} pcs)</div>
                    </td>
                    <td><span style="font-family: monospace; font-weight: 700;">${b.machine}</span></td>
                    <td>${b.operator}</td>
                    <td>${formatStatusBadge(b.current_status)}</td>
                    <td>
                      <div class="progress-container" style="max-width: 130px;">
                        <div class="progress-track">
                          <div class="progress-fill ${progressClass}" style="width: ${b.progress}%;"></div>
                        </div>
                        <span class="progress-pct">${b.progress}%</span>
                      </div>
                    </td>
                    <td style="font-size: 0.85rem; color: var(--text-secondary);">${formatDate(b.expected_completion)}</td>
                    <td>
                      <a href="/batches/${b.batch_number}" class="btn btn-secondary btn-sm">Inspect</a>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join('');
}
