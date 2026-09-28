/**
 * FastenPro AI — Global JavaScript Framework & Helper Utilities
 */

// Helper: API GET Request
async function apiGet(url) {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API GET error for ${url}:`, error);
    return { success: false, error: error.message };
  }
}

// Helper: API POST Request
async function apiPost(url, payload = {}) {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API POST error for ${url}:`, error);
    return { success: false, error: error.message };
  }
}

// Helper: Toast Notifications
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconSvg = type === 'success' 
    ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`
    : type === 'error'
    ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`
    : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

  toast.innerHTML = `
    ${iconSvg}
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Helper: Format Status Badges
function formatStatusBadge(status) {
  if (!status) return '<span class="status-badge badge-scheduled">Unknown</span>';
  const clean = status.trim();
  switch (clean) {
    case 'Scheduled':
      return `<span class="status-badge badge-scheduled">Scheduled</span>`;
    case 'Material Preparation':
      return `<span class="status-badge badge-material-prep">Material Preparation</span>`;
    case 'Manufacturing':
      return `<span class="status-badge badge-manufacturing">Manufacturing</span>`;
    case 'Quality Inspection':
      return `<span class="status-badge badge-quality-inspection">Quality Inspection</span>`;
    case 'Completed':
      return `<span class="status-badge badge-completed">Completed</span>`;
    case 'Quality Hold':
      return `<span class="status-badge badge-quality-hold">Quality Hold</span>`;
    default:
      return `<span class="status-badge badge-scheduled">${clean}</span>`;
  }
}

// Helper: Format Date
function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr.replace(' ', 'T'));
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch (e) {
    return dateStr;
  }
}

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Mobile Sidebar Toggle
  const menuToggle = document.getElementById('mobile-menu-btn');
  const sidebar = document.querySelector('.sidebar');
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  // Global Header Search Navigation
  const headerSearchForm = document.getElementById('header-search-form');
  const headerSearchInput = document.getElementById('header-search-input');
  if (headerSearchForm && headerSearchInput) {
    headerSearchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const raw = headerSearchInput.value.trim();
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

  // Check System & Ollama Service Health
  checkSystemHealth();
});

async function checkSystemHealth() {
  const dbIndicator = document.getElementById('db-status-indicator');
  const dbText = document.getElementById('db-status-text');
  const ollamaIndicator = document.getElementById('ollama-status-indicator');
  const ollamaText = document.getElementById('ollama-status-text');
  const copilotBadge = document.getElementById('copilot-mode-badge');

  const res = await apiGet('/api/health');
  if (res.success && res.data) {
    const d = res.data;
    if (dbIndicator && dbText) {
      if (d.database === 'connected') {
        dbIndicator.className = 'status-indicator online';
        dbText.textContent = 'Database Connected';
      } else {
        dbIndicator.className = 'status-indicator offline';
        dbText.textContent = 'Database Offline';
      }
    }

    if (ollamaIndicator && ollamaText) {
      if (d.ollama === 'connected') {
        ollamaIndicator.className = 'status-indicator online';
        ollamaText.textContent = `Ollama Connected (${d.ollama_model || 'gemma3:1b'})`;
        if (copilotBadge) {
          copilotBadge.className = 'grounded-badge ollama-active';
          copilotBadge.innerHTML = `● Ollama (${d.ollama_model || 'gemma3:1b'}) + DB Grounded`;
        }
      } else {
        ollamaIndicator.className = 'status-indicator offline';
        ollamaText.textContent = 'Ollama Offline (DB Fallback)';
        if (copilotBadge) {
          copilotBadge.className = 'grounded-badge fallback-active';
          copilotBadge.innerHTML = '● Database Fallback Active';
        }
      }
    }
  } else {
    if (dbIndicator && dbText) {
      dbIndicator.className = 'status-indicator offline';
      dbText.textContent = 'Database Offline';
    }
    if (ollamaIndicator && ollamaText) {
      ollamaIndicator.className = 'status-indicator offline';
      ollamaText.textContent = 'Ollama Offline';
    }
    if (copilotBadge) {
      copilotBadge.className = 'grounded-badge fallback-active';
      copilotBadge.innerHTML = '● Database Fallback Active';
    }
  }
}

