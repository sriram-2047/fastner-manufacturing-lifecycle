/**
 * FastenPro AI — AI Copilot Chatbot Controller
 */

let activeContextBatch = 'BATCH-0001';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');

  if (form && input) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      handleSendMessage(text);
      input.value = '';
    });
  }
});

function sendSuggestedQuestion(question) {
  const input = document.getElementById('chat-input');
  if (input) {
    input.value = '';
  }
  handleSendMessage(question);
}

async function handleSendMessage(question) {
  const messagesContainer = document.getElementById('chat-messages');
  if (!messagesContainer) return;

  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // 1. Append User Message
  const userBubble = document.createElement('div');
  userBubble.className = 'message-bubble user';
  userBubble.innerHTML = `
    <div class="avatar user-avatar">ME</div>
    <div class="message-content">
      <div>${escapeHtml(question)}</div>
      <div class="message-meta" style="justify-content: flex-end; color: rgba(255, 255, 255, 0.7);">
        <span>${timeStr}</span>
      </div>
    </div>
  `;
  messagesContainer.appendChild(userBubble);
  scrollToBottom();

  // 2. Append Loading Placeholder
  const loadingBubble = document.createElement('div');
  loadingBubble.className = 'message-bubble ai';
  loadingBubble.id = 'ai-loading-bubble';
  loadingBubble.innerHTML = `
    <div class="avatar ai-avatar">AI</div>
    <div class="message-content" style="display: flex; align-items: center; gap: 0.65rem; color: #38bdf8;">
      <div class="spinner"></div>
      <span>Analyzing batch records & database context...</span>
    </div>
  `;
  messagesContainer.appendChild(loadingBubble);
  scrollToBottom();

  // 3. Send API Request
  try {
    const res = await apiPost('/api/ai/chat', {
      question: question,
      batch_number: activeContextBatch
    });

    // Remove loading bubble
    const currentLoading = document.getElementById('ai-loading-bubble');
    if (currentLoading) currentLoading.remove();

    const dataObj = (res.data && typeof res.data === 'object' && res.data.answer) ? res.data : res;

    if (res.success && dataObj.answer) {
      if (dataObj.batch_number) {
        activeContextBatch = dataObj.batch_number;
      }

      const aiBubble = document.createElement('div');
      aiBubble.className = 'message-bubble ai';

      const isOllama = dataObj.engine === 'ollama';
      const isHistorical = dataObj.historical === true;

      // Determine clean source label & tag
      let sourceLabel = '';
      let tagClass = '';
      let dateBadge = '';

      if (isHistorical) {
        tagClass = 'historical';
        sourceLabel = isOllama ? 'Source: Batch Status History + Ollama' : 'Source: Batch Status History (Database Fallback)';
        if (dataObj.date) {
          dateBadge = `<span class="ai-source-tag historical">📅 Date: ${dataObj.date}</span>`;
        }
      } else if (dataObj.source === 'current_batch' || dataObj.batch_number) {
        tagClass = isOllama ? 'ollama' : 'fallback';
        sourceLabel = isOllama ? 'Source: Current Batch Record + Ollama' : 'Source: Current Batch Record (Database Fallback)';
      } else {
        tagClass = isOllama ? 'ollama' : 'fallback';
        sourceLabel = isOllama ? 'Source: Database + Ollama' : 'Source: Database Fallback';
      }

      let headerBadge = isOllama
        ? '<span class="grounded-badge ollama-active">● Ollama Grounded</span>'
        : '<span class="grounded-badge fallback-active">● DB Fallback Engine</span>';

      if (isHistorical) {
        headerBadge = `<span class="grounded-badge fallback-active" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">📜 Historical Audit Log</span>`;
      }

      // Convert line breaks and bullet points to formatted HTML
      const formattedAnswer = formatAiText(dataObj.answer);

      aiBubble.innerHTML = `
        <div class="avatar ai-avatar">AI</div>
        <div class="message-content">
          <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.35rem; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;">
            <span>FASTENPRO AI COPILOT</span>
            ${headerBadge}
          </div>
          <div style="color: var(--text-primary); line-height: 1.6;">
            ${formattedAnswer}
          </div>
          <div class="message-meta" style="flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; padding-top: 0.4rem; border-top: 1px solid rgba(255, 255, 255, 0.06);">
            <span class="ai-source-tag ${tagClass}">${sourceLabel}</span>
            ${dateBadge}
            <span style="margin-left: auto; color: var(--text-muted); font-size: 0.72rem;">${timeStr}</span>
          </div>
        </div>
      `;
      messagesContainer.appendChild(aiBubble);
    } else {
      const errorBubble = document.createElement('div');
      errorBubble.className = 'message-bubble ai';
      errorBubble.innerHTML = `
        <div class="avatar ai-avatar">AI</div>
        <div class="message-content" style="border-color: rgba(239, 68, 68, 0.4);">
          <div style="color: #f87171; font-weight: 600;">Service Notice</div>
          <p style="color: var(--text-secondary); margin-top: 0.3rem;">
            ${res.error || 'AI service is currently unavailable. Please check the Ollama service.'}
          </p>
          <div class="message-meta">
            <span>${timeStr}</span>
          </div>
        </div>
      `;
      messagesContainer.appendChild(errorBubble);
    }
  } catch (error) {
    const currentLoading = document.getElementById('ai-loading-bubble');
    if (currentLoading) currentLoading.remove();

    showToast('Failed to contact AI service', 'error');
  }

  scrollToBottom();
}

function formatAiText(text) {
  if (!text) return '';
  return text
    .split('\n')
    .map(line => {
      const escaped = escapeHtml(line);
      if (escaped.startsWith('• ') || escaped.startsWith('- ') || escaped.startsWith('* ')) {
        return `<div style="margin-left: 0.5rem; margin-bottom: 0.25rem;">${escaped}</div>`;
      }
      return escaped ? `<p style="margin-bottom: 0.4rem;">${escaped}</p>` : '<div style="height: 0.4rem;"></div>';
    })
    .join('');
}

function escapeHtml(string) {
  const div = document.createElement('div');
  div.innerText = string;
  return div.innerHTML;
}

function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function clearChat() {
  const container = document.getElementById('chat-messages');
  if (container) {
    container.innerHTML = `
      <div class="message-bubble ai">
        <div class="avatar ai-avatar">AI</div>
        <div class="message-content">
          <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.35rem;">FASTENPRO Manufacturing Assistant</div>
          <p>Chat history cleared. How can I assist you with your manufacturing batches?</p>
        </div>
      </div>
    `;
  }
}
