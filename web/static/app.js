/* =====================================================================
 *  Outlook 注册控制台 - 前端逻辑
 *  - 单页：5 个 Tab 切换
 *  - SSE 实时日志
 *  - 通用 toast / modal helper
 *  - 阶段 2-5 的具体页面渲染会陆续填充
 * ===================================================================== */

// ============================================================
//  HTTP 工具
// ============================================================
const api = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`GET ${url} -> ${r.status}`);
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`POST ${url} -> ${r.status} ${text}`);
    }
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`PUT ${url} -> ${r.status} ${text}`);
    }
    return r.json();
  },
  async del(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`DELETE ${url} -> ${r.status} ${text}`);
    }
    return r.json();
  },
};

// ============================================================
//  Toast
// ============================================================
const toastContainer = document.getElementById('toast-container');
function toast(msg, kind = 'info', duration = 3000) {
  const el = document.createElement('div');
  el.className = `toast toast-${kind}`;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.2s';
    setTimeout(() => el.remove(), 200);
  }, duration);
}

// ============================================================
//  Modal
// ============================================================
function modal({ title, body, actions, dismissible = true }) {
  return new Promise((resolve) => {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    const m = document.createElement('div');
    m.className = 'modal';

    const titleEl = document.createElement('div');
    titleEl.className = 'text-base font-semibold mb-2 text-slate-800';
    titleEl.textContent = title || '';
    m.appendChild(titleEl);

    if (typeof body === 'string') {
      const p = document.createElement('div');
      p.className = 'text-sm text-slate-600 mb-4 whitespace-pre-wrap';
      p.textContent = body;
      m.appendChild(p);
    } else if (body instanceof Node) {
      m.appendChild(body);
    }

    const btnRow = document.createElement('div');
    btnRow.className = 'flex justify-end gap-2 mt-4';
    (actions || [{ label: '确定', kind: 'primary', value: true }]).forEach((a) => {
      const b = document.createElement('button');
      b.className = `btn btn-${a.kind || 'ghost'}`;
      b.textContent = a.label;
      b.addEventListener('click', () => {
        backdrop.remove();
        resolve(a.value);
      });
      btnRow.appendChild(b);
    });
    m.appendChild(btnRow);

    backdrop.appendChild(m);
    if (dismissible) {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          backdrop.remove();
          resolve(null);
        }
      });
    }
    document.body.appendChild(backdrop);
  });
}

function confirm(title, body) {
  return modal({
    title,
    body,
    actions: [
      { label: '取消', kind: 'ghost', value: false },
      { label: '确定', kind: 'primary', value: true },
    ],
  });
}

// ============================================================
//  Tab 切换
// ============================================================
const navButtons = document.querySelectorAll('#nav .nav-btn');
const pageContainer = document.getElementById('page-container');
const pageTitle = document.getElementById('page-title');
const PAGE_TITLES = {
  register: '🚀 自动注册',
  proxy: '🌐 代理配置',
  accounts: '📋 账号管理',
  monitor: '📬 邮件监听',
  data: '🗂️ 数据管理',
};

const onPageEnterHooks = {};
function onPageEnter(page, fn) { onPageEnterHooks[page] = fn; }

navButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.page;
    navButtons.forEach((b) => b.classList.toggle('active', b === btn));
    pageContainer.querySelectorAll('[data-page-content]').forEach((el) => {
      el.hidden = el.dataset.pageContent !== target;
    });
    pageTitle.textContent = PAGE_TITLES[target] || '';
    if (onPageEnterHooks[target]) {
      try { onPageEnterHooks[target](); } catch (e) { console.error(e); }
    }
  });
});

// ============================================================
//  日志面板 (SSE)
// ============================================================
const logOutput = document.getElementById('log-output');
const logCountTag = document.getElementById('log-count-tag');
const btnCopyLogs = document.getElementById('btn-copy-logs');
const btnClearLogs = document.getElementById('btn-clear-logs');
const toggleAutoscroll = document.getElementById('toggle-autoscroll');
const connIndicator = document.getElementById('connection-indicator');

let logCount = 0;
const LOG_LIMIT = 5000;   // 超过这个行数自动裁剪首部，避免内存膨胀

function appendLog(line) {
  const el = document.createElement('div');
  el.className = `log-line ${(line.level || 'info').toLowerCase()}`;
  el.textContent = `[${line.ts}] [${line.level}] ${line.msg}`;
  logOutput.appendChild(el);
  logCount++;

  // 裁剪
  if (logCount > LOG_LIMIT) {
    const overflow = logCount - LOG_LIMIT;
    for (let i = 0; i < overflow; i++) {
      if (logOutput.firstChild) logOutput.firstChild.remove();
    }
    logCount = LOG_LIMIT;
  }

  logCountTag.textContent = `${logCount} 行`;
  if (toggleAutoscroll.checked) {
    logOutput.scrollTop = logOutput.scrollHeight;
  }
}

function connectLogStream() {
  const es = new EventSource('/api/logs/stream');
  es.onopen = () => {
    connIndicator.textContent = '🟢 已连接';
  };
  es.onmessage = (ev) => {
    try {
      const line = JSON.parse(ev.data);
      appendLog(line);
    } catch (e) {
      /* ignore */
    }
  };
  es.onerror = () => {
    connIndicator.textContent = '🔴 连接断开，5s 后重连';
    es.close();
    setTimeout(connectLogStream, 5000);
  };
}
connectLogStream();

btnClearLogs.addEventListener('click', () => {
  logOutput.innerHTML = '';
  logCount = 0;
  logCountTag.textContent = '0 行';
});

btnCopyLogs.addEventListener('click', async () => {
  const text = Array.from(logOutput.querySelectorAll('.log-line'))
    .map((el) => el.textContent)
    .join('\n');
  if (!text) {
    btnCopyLogs.textContent = '⚠️ 日志为空';
  } else {
    try {
      await navigator.clipboard.writeText(text);
      btnCopyLogs.textContent = `✅ 已复制 (${logCount} 行)`;
    } catch {
      btnCopyLogs.textContent = '❌ 复制失败';
    }
  }
  setTimeout(() => {
    btnCopyLogs.textContent = '📋 复制全部';
  }, 1500);
});

// ============================================================
//  顶部状态栏轮询（代理池 + 注册状态）
// ============================================================
async function refreshTopStatus() {
  // 代理池数量
  try {
    const r = await api.get('/api/proxies/status');
    document.getElementById('proxy-pool-count').textContent = r.count != null ? `${r.count} 个` : '—';
  } catch { /* 还没实现端点时静默 */ }

  // 注册任务状态
  try {
    const s = await api.get('/api/register/status');
    const badge = document.getElementById('status-badge');
    const txt = {
      idle: ['等待', 'bg-slate-700'],
      running: ['注册中', 'bg-blue'],
      waiting_confirm: ['等确认', 'bg-amber'],
      waiting_confirm_success: ['确认结果', 'bg-amber'],
      waiting_close: ['等关闭', 'bg-amber'],
      done: ['完成', 'bg-green'],
      error: ['错误', 'bg-red'],
    }[s.status] || ['未知', 'bg-slate-700'];
    badge.textContent = txt[0];
    badge.className = `badge ${txt[1]}`;
  } catch { /* 还没实现端点时静默 */ }
}
setInterval(refreshTopStatus, 2000);
refreshTopStatus();

// ============================================================
//  Bootstrap：进入页面立刻调用 register 的 hook（如有）
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
  if (onPageEnterHooks.register) onPageEnterHooks.register();
});

// 暴露给后续阶段的脚本扩展
window.App = { api, toast, modal, confirm, onPageEnter, refreshTopStatus };
