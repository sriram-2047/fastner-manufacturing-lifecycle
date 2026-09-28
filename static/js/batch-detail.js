/**
 * FastenPro AI — Batch Detail Controller & Lifecycle Simulation Engine
 */

const LIFECYCLE_ORDER = [
  'Scheduled',
  'Material Preparation',
  'Manufacturing',
  'Quality Inspection',
  'Completed'
];

let currentBatchNumber = '';
let currentBatchData = null;

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('batch-container');
  if (!container) return;

  currentBatchNumber = container.dataset.batchNumber;
  fetchBatchDetails();
});

async function fetchBatchDetails() {
  if (!currentBatchNumber) return;

  const res = await apiGet(`/api/batches/${currentBatchNumber}`);
  if (res.success && res.data) {
    currentBatchData = res.data;
    updateBatchUI(currentBatchData);
  } else {
    showToast(res.error || 'Failed to load batch details', 'error');
  }
}

function updateBatchUI(batch) {
  // Update header status & progress
  const statusEl = document.getElementById('header-status-text');
  const barEl = document.getElementById('header-progress-bar');
  const pctEl = document.getElementById('header-progress-pct');

  if (statusEl) {
    statusEl.textContent = batch.current_status.toUpperCase();
    if (batch.current_status === 'Completed') statusEl.style.color = '#34d399';
    else if (batch.current_status === 'Quality Hold') statusEl.style.color = '#f87171';
    else if (batch.current_status === 'Manufacturing') statusEl.style.color = '#fbbf24';
    else statusEl.style.color = '#38bdf8';
  }

  if (barEl) {
    barEl.style.width = `${batch.progress}%`;
    barEl.className = 'progress-fill';
    if (batch.current_status === 'Completed') barEl.classList.add('complete');
    else if (batch.current_status === 'Quality Hold') barEl.classList.add('hold');
  }

  if (pctEl) {
    pctEl.textContent = `${batch.progress}%`;
  }

  // Update dates
  const actualEl = document.getElementById('val-mfg-actual');
  if (actualEl) {
    actualEl.textContent = batch.actual_completion ? batch.actual_completion : 'In Progress';
    actualEl.style.color = batch.actual_completion ? '#34d399' : 'var(--text-muted)';
  }

  // Render Lifecycle Stepper
  renderLifecycleStepper(batch.current_status);

  // Render Quality Inspection
  renderQualitySection(batch.latest_quality, batch.current_status);

  // Render History Audit Trail
  renderHistoryTrail(batch.history);
}

function renderLifecycleStepper(currentStatus) {
  const stepper = document.getElementById('lifecycle-stepper');
  if (!stepper) return;

  const isHold = currentStatus === 'Quality Hold';
  let currentIndex = LIFECYCLE_ORDER.indexOf(currentStatus);
  if (isHold) {
    // Quality hold maps to inspection stage with warning
    currentIndex = LIFECYCLE_ORDER.indexOf('Quality Inspection');
  }

  stepper.innerHTML = LIFECYCLE_ORDER.map((stage, idx) => {
    let stateClass = '';
    let iconContent = idx + 1;

    if (currentStatus === 'Completed') {
      stateClass = 'completed';
      iconContent = '✓';
    } else if (idx < currentIndex) {
      stateClass = 'completed';
      iconContent = '✓';
    } else if (idx === currentIndex) {
      stateClass = 'current';
      if (isHold) {
        iconContent = '!';
      }
    }

    return `
      <div class="step-item ${stateClass}">
        <div class="step-circle" ${isHold && idx === currentIndex ? 'style="border-color: #ef4444; background: #991b1b; color: #fff;"' : ''}>
          ${iconContent}
        </div>
        <div class="step-title" ${isHold && idx === currentIndex ? 'style="color: #f87171;"' : ''}>
          ${stage}
        </div>
      </div>
    `;
  }).join('');
}

function renderQualitySection(quality, batchStatus) {
  const container = document.getElementById('quality-details-content');
  const badgeContainer = document.getElementById('quality-overall-badge');
  if (!container) return;

  if (!quality) {
    container.innerHTML = `
      <div style="padding: 2rem; text-align: center; color: var(--text-muted); background: rgba(15, 23, 42, 0.4); border-radius: var(--radius-md);">
        Quality inspection is scheduled after manufacturing phase completion.
      </div>
    `;
    if (badgeContainer) badgeContainer.innerHTML = '<span class="status-badge badge-scheduled">Pending Inspection</span>';
    return;
  }

  // Set overall badge
  if (badgeContainer) {
    if (quality.overall_result === 'PASSED') {
      badgeContainer.innerHTML = '<span class="status-badge badge-completed">✓ PASSED</span>';
    } else if (quality.overall_result === 'HOLD') {
      badgeContainer.innerHTML = '<span class="status-badge badge-quality-hold">⚠️ QUALITY HOLD</span>';
    } else {
      badgeContainer.innerHTML = `<span class="status-badge badge-scheduled">${quality.overall_result}</span>`;
    }
  }

  let alertBanner = '';
  if (quality.overall_result === 'HOLD' || batchStatus === 'Quality Hold') {
    alertBanner = `
      <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: var(--radius-md); padding: 0.85rem 1rem; margin-bottom: 1rem; color: #f87171; font-size: 0.85rem; display: flex; align-items: center; gap: 0.6rem;">
        <span style="font-size: 1.2rem;">⚠️</span>
        <div>
          <strong>QUALITY HOLD:</strong> Non-conformance detected during metrology check. MRB review required.
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    ${alertBanner}
    <div class="spec-list">
      <div class="spec-item">
        <div class="spec-label">Dimensional Check</div>
        <div class="spec-val">
          <span class="badge-${quality.dimensional_result === 'PASS' ? 'pass' : 'fail'}">${quality.dimensional_result}</span>
        </div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Thread Form / Pitch</div>
        <div class="spec-val">
          <span class="badge-${quality.thread_result === 'PASS' ? 'pass' : (quality.thread_result === 'FAIL' ? 'fail' : 'pending')}">${quality.thread_result}</span>
        </div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Surface & Coating</div>
        <div class="spec-val">
          <span class="badge-${quality.surface_result === 'PASS' ? 'pass' : 'fail'}">${quality.surface_result}</span>
        </div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Core Hardness</div>
        <div class="spec-val" style="color: #38bdf8;">${quality.hardness || 'N/A'}</div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Tensile Strength</div>
        <div class="spec-val" style="color: #38bdf8;">${quality.tensile_strength || 'N/A'}</div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Inspection Date</div>
        <div class="spec-val" style="font-size: 0.85rem;">${quality.formatted_date || quality.inspection_date || 'N/A'}</div>
      </div>
    </div>
    <div style="margin-top: 1rem; padding: 0.75rem 1rem; background: rgba(15, 23, 42, 0.4); border-radius: var(--radius-md); border: 1px solid var(--border-subtle); font-size: 0.82rem; color: var(--text-secondary);">
      <strong style="color: var(--text-primary);">QA Remarks:</strong> ${quality.remarks || 'Standard testing protocol completed.'}
    </div>
  `;
}

function renderHistoryTrail(history) {
  const container = document.getElementById('batch-history-container');
  if (!container) return;

  if (!history || history.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">No historical status logs recorded.</div>`;
    return;
  }

  container.innerHTML = history.map(h => {
    return `
      <div class="history-entry">
        <div class="history-node"></div>
        <div class="history-card">
          <div class="history-header">
            <div>
              <span style="font-weight: 700; color: #fff; margin-right: 0.5rem;">${h.status}</span>
              ${formatStatusBadge(h.status)}
            </div>
            <span class="history-date">${h.formatted_date || h.timestamp}</span>
          </div>
          <div style="font-size: 0.8rem; color: #38bdf8; margin-bottom: 0.25rem;">
            Production Progress: ${h.progress}%
          </div>
          <div class="history-remarks">
            ${h.remarks || 'Status logged.'}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function advanceBatchAction() {
  const btn = document.getElementById('btn-advance-batch');
  if (btn) btn.disabled = true;

  try {
    const res = await apiPost(`/api/batches/${currentBatchNumber}/advance`);
    if (res.success && res.data) {
      currentBatchData = res.data.batch || res.data;
      updateBatchUI(currentBatchData);
      showToast(res.message || `Advanced to ${currentBatchData.current_status}`, 'success');
    } else {
      showToast(res.error || 'Failed to advance batch', 'error');
    }
  } catch (e) {
    showToast('Network error while advancing batch', 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function completeBatchAction() {
  const btn = document.getElementById('btn-complete-batch');
  if (btn) btn.disabled = true;

  try {
    const res = await apiPost(`/api/batches/${currentBatchNumber}/complete`);
    if (res.success && res.data) {
      currentBatchData = res.data.batch || res.data;
      updateBatchUI(currentBatchData);
      showToast(res.message || 'Batch marked COMPLETED (100%)', 'success');
    } else {
      showToast(res.error || 'Failed to complete batch', 'error');
    }
  } catch (e) {
    showToast('Network error while completing batch', 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}
