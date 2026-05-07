/* =====================================================================
 *  注册页 - 控制 + 账号列表 + 状态轮询
 * ===================================================================== */
(function () {
  const { api, toast, modal, confirm: confirmDialog, onPageEnter } = window.App;

  const els = {
    startBtn:       document.getElementById('btn-start-register'),
    stopBtn:        document.getElementById('btn-stop-register'),
    confirmBtn:     document.getElementById('btn-confirm-action'),
    closeBtn:       document.getElementById('btn-close-browser'),
    refreshBtn:     document.getElementById('btn-refresh-accounts'),
    taskInfo:       document.getElementById('register-task-info'),
    tbody:          document.getElementById('accounts-tbody'),
    accountsCount:  document.getElementById('accounts-count'),
  };

  // ============================ 账号列表 ============================
  function statusBadgeColor(status) {
    if (!status) return 'bg-slate-700';
    const s = String(status).toLowerCase();
    if (s.includes('success') || s.includes('card_bound') || s.includes('已注册') || s.includes('registered')) return 'bg-green';
    if (s.includes('fail') || s.includes('error') || s.includes('失败')) return 'bg-red';
    return 'bg-blue';
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  async function loadAccounts() {
    try {
      const r = await api.get('/api/accounts');
      els.accountsCount.textContent = `(${r.count})`;
      if (!r.count) {
        els.tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-400 py-4">暂无账号</td></tr>';
        return;
      }
      els.tbody.innerHTML = r.items.map((acc) => `
        <tr>
          <td class="font-mono">${escapeHtml(acc.email)}</td>
          <td class="font-mono select-all">${escapeHtml(acc.password)}</td>
          <td><span class="badge ${statusBadgeColor(acc.status)}">${escapeHtml(acc.status)}</span></td>
          <td>${escapeHtml(acc.plan_name) || '-'}</td>
          <td>${acc.credits ?? '-'} / ${acc.total_credits ?? '-'}</td>
          <td class="text-xs text-slate-500">${escapeHtml(acc.registered_at) || '-'}</td>
          <td class="text-right">
            <button class="btn btn-ghost text-xs" data-del="${acc.id}">🗑️ 删除</button>
          </td>
        </tr>`).join('');

      els.tbody.querySelectorAll('[data-del]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.del;
          const ok = await confirmDialog('确认删除', '确定删除这个账号？此操作不可恢复。');
          if (!ok) return;
          try {
            await api.del(`/api/accounts/${id}`);
            toast('已删除', 'success');
            loadAccounts();
          } catch (e) {
            toast('删除失败：' + e.message, 'error');
          }
        });
      });
    } catch (e) {
      els.tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red-500 py-4">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
  }

  // ============================ 状态轮询 ============================
  let lastStatus = 'idle';
  let confirmModalOpen = false;
  let successModalOpen = false;

  const STATUS_LABELS = {
    idle: '等待',
    running: '注册中',
    waiting_confirm: '等待你确认（验证码）',
    waiting_confirm_success: '等待你确认（注册结果）',
    waiting_close: '等待关闭浏览器',
    done: '已完成',
    error: '失败',
  };

  function updateButtonsByStatus(s) {
    const isRunning = ['running', 'waiting_confirm', 'waiting_confirm_success', 'waiting_close'].includes(s.status);
    els.startBtn.disabled = isRunning;
    els.stopBtn.disabled = !isRunning;
    els.closeBtn.hidden = s.status !== 'waiting_close';
    els.confirmBtn.hidden = !s.confirm_message;

    if (s.status === 'idle') {
      els.taskInfo.hidden = true;
    } else {
      els.taskInfo.hidden = false;
      const info = s.user_info || {};
      const label = STATUS_LABELS[s.status] || s.status;
      els.taskInfo.innerHTML = `
        <div><span class="text-slate-500">状态：</span><span class="font-medium">${escapeHtml(label)}</span></div>
        ${info.email    ? `<div class="mt-1">📬 邮箱：<span class="font-mono">${escapeHtml(info.email)}</span></div>`    : ''}
        ${info.password ? `<div class="mt-1">🔑 密码：<span class="font-mono select-all">${escapeHtml(info.password)}</span></div>` : ''}
        ${s.error_msg   ? `<div class="mt-1 text-red-600">⚠️ ${escapeHtml(s.error_msg)}</div>` : ''}
      `;
    }
  }

  async function pollStatus() {
    let s;
    try {
      s = await api.get('/api/register/status');
    } catch {
      return;
    }
    updateButtonsByStatus(s);

    // 等待用户完成验证码
    if (s.confirm_message && !confirmModalOpen) {
      confirmModalOpen = true;
      modal({
        title: '需要手动操作',
        body: `${s.confirm_message}\n\n请在已打开的 Chrome 浏览器里完成操作，然后点击下方「✅ 我已完成」。`,
        actions: [{ label: '✅ 我已完成', kind: 'primary', value: true }],
      }).then(() => {
        confirmModalOpen = false;
        api.post('/api/register/confirm').catch((e) => toast(e.message, 'error'));
      });
    }

    // 等待用户确认注册结果
    if (s.confirm_success_message && !successModalOpen) {
      successModalOpen = true;
      const info = s.user_info || {};
      const body = document.createElement('div');
      body.innerHTML = `
        <p class="text-sm text-slate-700 mb-3 whitespace-pre-wrap">${escapeHtml(s.confirm_success_message)}</p>
        <div class="bg-slate-50 rounded p-3 text-sm space-y-1 mb-3">
          <div>📬 <span class="font-mono">${escapeHtml(info.email)}</span></div>
          <div>🔑 <span class="font-mono select-all">${escapeHtml(info.password)}</span></div>
        </div>`;
      modal({
        title: '请确认注册结果',
        body,
        actions: [
          { label: '❌ 失败',    kind: 'danger',  value: false },
          { label: '✅ 成功',    kind: 'success', value: true  },
        ],
      }).then(async (ok) => {
        successModalOpen = false;
        if (ok === null) return;   // 弹窗被关闭（理论上不应该）
        try {
          await api.post('/api/register/confirm-success', { success: !!ok });
        } catch (e) {
          toast('提交失败：' + e.message, 'error');
        }
      });
    }

    // 状态变化时刷新账号列表
    const finishedStates = ['done', 'error', 'idle'];
    if (finishedStates.includes(s.status) && !finishedStates.includes(lastStatus)) {
      loadAccounts();
    }
    lastStatus = s.status;
  }

  // ============================ 按钮 ============================
  els.startBtn.addEventListener('click', async () => {
    try {
      await api.post('/api/register/start');
      toast('已开始注册任务', 'success');
    } catch (e) {
      toast('启动失败：' + e.message, 'error');
    }
  });

  els.stopBtn.addEventListener('click', async () => {
    const ok = await confirmDialog('停止注册', '确定要停止当前注册任务？浏览器会被强制关闭。');
    if (!ok) return;
    try {
      await api.post('/api/register/stop');
      toast('已停止', 'warn');
    } catch (e) {
      toast('停止失败：' + e.message, 'error');
    }
  });

  els.closeBtn.addEventListener('click', async () => {
    try {
      await api.post('/api/register/close-browser');
      toast('已通知关闭浏览器', 'success');
    } catch (e) {
      toast(e.message, 'error');
    }
  });

  els.confirmBtn.addEventListener('click', async () => {
    try {
      await api.post('/api/register/confirm');
    } catch (e) {
      toast(e.message, 'error');
    }
  });

  els.refreshBtn.addEventListener('click', loadAccounts);

  // 进入注册页时刷新一次
  onPageEnter('register', loadAccounts);

  // 启动轮询
  setInterval(pollStatus, 1500);
  pollStatus();
  loadAccounts();
})();
