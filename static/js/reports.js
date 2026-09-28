/**
 * FastenPro AI — Reports Controller
 */

let reportBatches = [];

document.addEventListener('DOMContentLoaded', () => {
  initReports();
});

async function initReports() {
  const container = document.getElementById('report-content-container');
  const initialBatch = container ? container.dataset.initialBatch || 'BATCH-0001' : 'BATCH-0001';

  // Load batch options
  const res = await apiGet('/api/batches');
  if (res.success && res.data) {
    reportBatches = res.data;
    const select = document.getElementById('report-batch-select');
    if (select) {
      select.innerHTML = reportBatches.map(b => `
        <option value="${b.batch_number}" ${b.batch_number === initialBatch ? 'selected' : ''}>
          ${b.batch_number} — ${b.fastener_type} (${b.part_number})
        </option>
      `).join('');

      select.addEventListener('change', () => {
        loadSelectedReport();
      });
    }
  }

  fetchReport(initialBatch);
}

function loadSelectedReport() {
  const select = document.getElementById('report-batch-select');
  if (select && select.value) {
    fetchReport(select.value);
  }
}

async function fetchReport(batchNumber) {
  const container = document.getElementById('report-content-container');
  if (!container) return;

  container.innerHTML = `
    <div class="panel">
      <div class="loading-placeholder">
        <div class="spinner"></div>
        <span>Generating production report for ${batchNumber}...</span>
      </div>
    </div>
  `;

  const res = await apiGet(`/api/reports/${batchNumber}`);
  if (!res.success || !res.data) {
    container.innerHTML = `
      <div class="panel" style="color: var(--status-hold); padding: 2rem; text-align: center;">
        ${res.error || 'Failed to generate report.'}
      </div>
    `;
    return;
  }

  const b = res.data;
  const q = b.latest_quality;

  let qualityBanner = `<span class="badge-pending">PENDING</span>`;
  if (q) {
    if (q.overall_result === 'PASSED') qualityBanner = `<span class="badge-pass" style="font-size: 0.9rem;">PASSED / CONFORMANT</span>`;
    else if (q.overall_result === 'HOLD') qualityBanner = `<span class="badge-fail" style="font-size: 0.9rem;">QUALITY HOLD / NON-CONFORMANT</span>`;
  }

  container.innerHTML = `
    <div class="panel" style="padding: 2.5rem; background: #0d1527; border: 1px solid #23355d;">
      <!-- Report Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1e293b; padding-bottom: 1.5rem; margin-bottom: 2rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-size: 1.4rem;">⚡</span>
            <span style="font-size: 1.3rem; font-weight: 800; color: #fff;">FASTENPRO MANUFACTURING REPORT</span>
          </div>
          <div style="font-size: 0.82rem; color: var(--accent-blue); margin-top: 0.3rem;">
            Fastener Production Traceability Summary
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-family: monospace; font-size: 1.2rem; font-weight: 700; color: #38bdf8;">${b.batch_number}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;">Generated: ${new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
        </div>
      </div>

      <!-- Core Metadata Cards -->
      <div class="specs-grid" style="margin-bottom: 2rem;">
        <!-- Product Specs -->
        <div style="background: rgba(15, 23, 42, 0.6); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <h3 style="font-size: 0.95rem; color: #38bdf8; font-weight: 700; margin-bottom: 0.85rem;">Fastener Specifications</h3>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.85rem;">
            <div><span style="color: var(--text-secondary);">Product:</span> <strong>${b.fastener_type}</strong></div>
            <div><span style="color: var(--text-secondary);">Part #:</span> <strong>${b.part_number}</strong></div>
            <div><span style="color: var(--text-secondary);">Material:</span> <strong>${b.material}</strong></div>
            <div><span style="color: var(--text-secondary);">Grade:</span> <strong>${b.grade}</strong></div>
            <div><span style="color: var(--text-secondary);">Diameter:</span> <strong>${b.diameter}</strong></div>
            <div><span style="color: var(--text-secondary);">Length:</span> <strong>${b.length}</strong></div>
            <div><span style="color: var(--text-secondary);">Thread:</span> <strong>${b.thread_type} (${b.thread_pitch})</strong></div>
            <div><span style="color: var(--text-secondary);">Coating:</span> <strong>${b.coating || 'None'}</strong></div>
            <div style="grid-column: span 2;"><span style="color: var(--text-secondary);">Work Order Quantity:</span> <strong>${b.quantity.toLocaleString()} units</strong> (Customer: ${b.customer})</div>
          </div>
        </div>

        <!-- Production Execution -->
        <div style="background: rgba(15, 23, 42, 0.6); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <h3 style="font-size: 0.95rem; color: #fbbf24; font-weight: 700; margin-bottom: 0.85rem;">Production Operations</h3>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.85rem;">
            <div><span style="color: var(--text-secondary);">Line:</span> <strong>${b.production_line}</strong></div>
            <div><span style="color: var(--text-secondary);">Station:</span> <strong>${b.machine}</strong></div>
            <div><span style="color: var(--text-secondary);">Lead Operator:</span> <strong>${b.operator}</strong></div>
            <div><span style="color: var(--text-secondary);">Current Status:</span> ${formatStatusBadge(b.current_status)}</div>
            <div><span style="color: var(--text-secondary);">Mfg Start:</span> <strong>${formatDate(b.manufacturing_start)}</strong></div>
            <div><span style="color: var(--text-secondary);">Expected Completion:</span> <strong>${formatDate(b.expected_completion)}</strong></div>
            <div style="grid-column: span 2;"><span style="color: var(--text-secondary);">Actual Completion:</span> <strong>${b.actual_completion || 'In Progress'}</strong></div>
          </div>
        </div>
      </div>

      <!-- Quality Assurance Metrology -->
      <div style="background: rgba(15, 23, 42, 0.6); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
          <h3 style="font-size: 0.95rem; color: #10b981; font-weight: 700;">Metrology & Quality Assurance Sign-Off</h3>
          ${qualityBanner}
        </div>
        ${q ? `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; font-size: 0.85rem; margin-bottom: 0.75rem;">
            <div class="spec-item"><div class="spec-label">Dimensions</div><div class="spec-val">${q.dimensional_result}</div></div>
            <div class="spec-item"><div class="spec-label">Thread Pitch</div><div class="spec-val">${q.thread_result}</div></div>
            <div class="spec-item"><div class="spec-label">Surface</div><div class="spec-val">${q.surface_result}</div></div>
            <div class="spec-item"><div class="spec-label">Hardness</div><div class="spec-val">${q.hardness || 'N/A'}</div></div>
            <div class="spec-item"><div class="spec-label">Tensile</div><div class="spec-val">${q.tensile_strength || 'N/A'}</div></div>
          </div>
          <div style="font-size: 0.82rem; color: var(--text-secondary);"><strong style="color: #fff;">QA Metrology Notes:</strong> ${q.remarks || 'Standard testing passed.'}</div>
        ` : `
          <p style="font-size: 0.85rem; color: var(--text-muted);">No QA inspection logged yet.</p>
        `}
      </div>

      <!-- Historical Traceability Trail -->
      <div style="margin-bottom: 2rem;">
        <h3 style="font-size: 0.95rem; color: #fff; font-weight: 700; margin-bottom: 0.85rem;">Lifecycle Audit Trail</h3>
        <table class="industrial-table" style="font-size: 0.82rem;">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Stage</th>
              <th>Progress</th>
              <th>Operational Remarks</th>
            </tr>
          </thead>
          <tbody>
            ${(b.history || []).map(h => `
              <tr>
                <td style="color: var(--accent-blue); font-family: monospace;">${h.formatted_date || h.timestamp}</td>
                <td>${formatStatusBadge(h.status)}</td>
                <td>${h.progress}%</td>
                <td>${h.remarks || ''}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <!-- Signatures Footer -->
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2rem; border-top: 1px dashed var(--border-subtle); padding-top: 1.5rem; font-size: 0.8rem; color: var(--text-secondary);">
        <div>
          <div>Production Supervisor</div>
          <div style="border-bottom: 1px solid #334155; height: 35px; margin-bottom: 0.3rem;"></div>
          <div>Authorized Signature & Date</div>
        </div>
        <div>
          <div>Quality Metrologist</div>
          <div style="border-bottom: 1px solid #334155; height: 35px; margin-bottom: 0.3rem;"></div>
          <div>Authorized Signature & Date</div>
        </div>
        <div>
          <div>Plant Operations Director</div>
          <div style="border-bottom: 1px solid #334155; height: 35px; margin-bottom: 0.3rem;"></div>
          <div>Authorized Signature & Date</div>
        </div>
      </div>
    </div>
  `;
}
