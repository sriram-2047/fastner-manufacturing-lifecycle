/**
 * FastenPro AI — Quality Assurance Page Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  loadQualityOverview();
});

async function loadQualityOverview() {
  const res = await apiGet('/api/quality');
  if (!res.success || !res.data) {
    showToast('Failed to load quality metrics', 'error');
    return;
  }

  const d = res.data;

  // Update KPI counters
  document.getElementById('qa-passed-count').textContent = d.passed || 0;
  document.getElementById('qa-pending-count').textContent = d.pending || 0;
  document.getElementById('qa-hold-count').textContent = d.hold || 0;
  document.getElementById('qa-failed-count').textContent = d.failed || 0;

  // Render Table
  const tbody = document.getElementById('quality-tbody');
  if (!tbody) return;

  const inspections = d.inspections || [];
  if (inspections.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 2rem; color: var(--text-muted);">No QA inspection reports recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = inspections.map(i => {
    let resultBadge = `<span class="badge-pass">PASS</span>`;
    if (i.overall_result === 'HOLD') {
      resultBadge = `<span class="badge-fail">HOLD</span>`;
    } else if (i.overall_result === 'PENDING') {
      resultBadge = `<span class="badge-pending">PENDING</span>`;
    }

    return `
      <tr>
        <td>
          <a href="/batches/${i.batch_number}" class="batch-code" style="text-decoration: underline dotted;">
            ${i.batch_number}
          </a>
        </td>
        <td>
          <strong>${i.fastener_type}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${i.part_number}</div>
        </td>
        <td><span class="badge-${i.dimensional_result === 'PASS' ? 'pass' : 'fail'}">${i.dimensional_result}</span></td>
        <td><span class="badge-${i.thread_result === 'PASS' ? 'pass' : (i.thread_result === 'FAIL' ? 'fail' : 'pending')}">${i.thread_result}</span></td>
        <td><span class="badge-${i.surface_result === 'PASS' ? 'pass' : 'fail'}">${i.surface_result}</span></td>
        <td><strong style="color: #38bdf8;">${i.hardness}</strong></td>
        <td><strong style="color: #38bdf8;">${i.tensile_strength}</strong></td>
        <td>${resultBadge}</td>
        <td style="font-size: 0.82rem; color: var(--text-secondary);">${i.formatted_date || i.inspection_date || 'N/A'}</td>
        <td>
          <a href="/batches/${i.batch_number}" class="btn btn-secondary btn-sm">Inspect</a>
        </td>
      </tr>
    `;
  }).join('');
}
