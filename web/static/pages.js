/* =====================================================================
 *  剩余三页：账号管理 / 邮件监听 / 数据管理
 *  （单文件维护，避免太多 <script> 标签）
 * ===================================================================== */
(function () {
  const { api, toast, modal, confirm: confirmDialog, onPageEnter } = window.App;

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function statusBadgeColor(status) {
    if (!status) return 'bg-slate-700';
    const s = String(status).toLowerCase();
    if (s.includes('success') || s.includes('card_bound') || s.includes('已注册') || s.includes('registered') || s === 'used') return 'bg-green';
    if (s.includes('fail') || s.includes('error') || s.includes('失败')) return 'bg-red';
    if (s === 'unused') return 'bg-amber';
    return 'bg-blue';
  }

  // =====================================================================
  //  账号管理页
  // =====================================================================
  const acc = {
    count:   document.getElementById('acc-mgr-count'),
    filter:  document.getElementById('acc-mgr-filter'),
    refresh: document.getElementById('btn-acc-mgr-refresh'),
    tbody:   document.getElementById('acc-mgr-tbody'),
  };

  async function loadAccountsMgr() {
    try {
      const status = acc.filter.value;
      const url = status ? `/api/accounts?status=${encodeURIComponent(status)}` : '/api/accounts';
      const r = await api.get(url);
      acc.count.textContent = `(${r.count})`;
      if (!r.count) {
        acc.tbody.innerHTML = '<tr><td colspan="9" class="text-center text-slate-400 py-4">暂无账号</td></tr>';
        return;
      }
      acc.tbody.innerHTML = r.items.map((a) => `
        <tr>
          <td class="font-mono">${escapeHtml(a.email)}</td>
          <td class="font-mono select-all">${escapeHtml(a.password)}</td>
          <td><span class="badge ${statusBadgeColor(a.status)}">${escapeHtml(a.status)}</span></td>
          <td>${escapeHtml(a.plan_name) || '-'}</td>
          <td>${a.credits ?? '-'} / ${a.total_credits ?? '-'}</td>
          <td>${a.card_bound ? '✅' : '—'}</td>
          <td class="text-xs text-slate-500">${escapeHtml(a.registered_at) || '-'}</td>
          <td class="text-xs text-slate-500" style="max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(a.notes)}">${escapeHtml(a.notes) || ''}</td>
          <td class="text-right">
            <button class="btn btn-ghost text-xs" data-edit="${a.id}">✏️ 编辑</button>
            <button class="btn btn-ghost text-xs" data-del="${a.id}">🗑️</button>
          </td>
        </tr>`).join('');

      acc.tbody.querySelectorAll('[data-edit]').forEach((b) => {
        b.addEventListener('click', () => openEditAccountModal(Number(b.dataset.edit), r.items.find((x) => x.id == b.dataset.edit)));
      });
      acc.tbody.querySelectorAll('[data-del]').forEach((b) => {
        b.addEventListener('click', async () => {
          const ok = await confirmDialog('删除账号', '确定删除？此操作不可恢复');
          if (!ok) return;
          try {
            await api.del(`/api/accounts/${b.dataset.del}`);
            toast('已删除', 'success');
            loadAccountsMgr();
          } catch (e) { toast(e.message, 'error'); }
        });
      });
    } catch (e) {
      acc.tbody.innerHTML = `<tr><td colspan="9" class="text-center text-red-500 py-4">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
  }

  function openEditAccountModal(id, current) {
    const wrap = document.createElement('div');
    wrap.innerHTML = `
      <div class="space-y-2 text-sm">
        <div>
          <label class="text-xs text-slate-500">状态</label>
          <input class="input mt-1" data-f="status" value="${escapeHtml(current?.status)}" />
        </div>
        <div>
          <label class="text-xs text-slate-500">套餐</label>
          <input class="input mt-1" data-f="plan_name" value="${escapeHtml(current?.plan_name)}" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-xs text-slate-500">余额</label>
            <input class="input mt-1" type="number" data-f="credits" value="${current?.credits ?? ''}" />
          </div>
          <div>
            <label class="text-xs text-slate-500">总额</label>
            <input class="input mt-1" type="number" data-f="total_credits" value="${current?.total_credits ?? ''}" />
          </div>
        </div>
        <div>
          <label class="text-xs text-slate-500">备注</label>
          <textarea class="input mt-1" rows="3" data-f="notes">${escapeHtml(current?.notes)}</textarea>
        </div>
      </div>
    `;
    modal({
      title: `编辑账号 #${id}`,
      body: wrap,
      actions: [
        { label: '取消', kind: 'ghost', value: false },
        { label: '保存', kind: 'primary', value: true },
      ],
    }).then(async (ok) => {
      if (!ok) return;
      const body = {};
      wrap.querySelectorAll('[data-f]').forEach((el) => {
        const k = el.dataset.f;
        let v = el.value;
        if (el.type === 'number') v = v === '' ? null : Number(v);
        body[k] = v === '' ? null : v;
      });
      try {
        await api.put(`/api/accounts/${id}`, body);
        toast('已保存', 'success');
        loadAccountsMgr();
      } catch (e) {
        toast('保存失败：' + e.message, 'error');
      }
    });
  }

  acc.filter.addEventListener('change', loadAccountsMgr);
  acc.refresh.addEventListener('click', loadAccountsMgr);
  onPageEnter('accounts', loadAccountsMgr);


  // =====================================================================
  //  邮件监听页
  // =====================================================================
  const mon = {
    email:    document.getElementById('mon-email'),
    password: document.getElementById('mon-password'),
    interval: document.getElementById('mon-interval'),
    useApi:   document.getElementById('mon-use-api'),
    startBtn: document.getElementById('btn-mon-start'),
    stopBtn:  document.getElementById('btn-mon-stop'),
    statusEl: document.getElementById('mon-status'),
    tbody:    document.getElementById('mon-tbody'),
    count:    document.getElementById('mon-email-count'),
  };

  async function loadMonitorEmails() {
    try {
      const r = await api.get('/api/monitor/emails');
      mon.count.textContent = `(${r.count})`;
      if (!r.count) {
        mon.tbody.innerHTML = '<tr><td colspan="4" class="text-center text-slate-400 py-4">暂无邮件</td></tr>';
        return;
      }
      mon.tbody.innerHTML = r.items.map((e) => `
        <tr>
          <td class="text-xs text-slate-500">${escapeHtml(e.date)}</td>
          <td class="text-xs">${escapeHtml(e.from)}</td>
          <td class="text-xs font-medium">${escapeHtml(e.subject)}</td>
          <td class="text-xs text-slate-500" style="max-width:480px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(e.body)}">${escapeHtml(e.body)}</td>
        </tr>`).join('');
    } catch (e) {
      /* 静默 */
    }
  }

  async function loadMonitorStatus() {
    try {
      const s = await api.get('/api/monitor/status');
      const isRunning = s.is_running || s.status === 'running';
      mon.startBtn.disabled = isRunning;
      mon.stopBtn.disabled = !isRunning;
      const labels = { idle: '空闲', running: '监听中', done: '已停止', error: '错误' };
      mon.statusEl.textContent = `状态: ${labels[s.status] || s.status}`
        + (s.email ? ` (${s.email})` : '')
        + (s.error_msg ? ` ⚠️ ${s.error_msg}` : '');
    } catch { /* 静默 */ }
  }

  mon.startBtn.addEventListener('click', async () => {
    const email = mon.email.value.trim();
    const password = mon.password.value;
    const useApi = mon.useApi.checked;
    if (!email || (!useApi && !password)) {
      toast('请填写邮箱和密码（API 模式可不填密码）', 'warn');
      return;
    }
    try {
      await api.post('/api/monitor/start', {
        email,
        password,
        interval: Number(mon.interval.value || 30),
        use_api: useApi,
      });
      toast('已开始监听', 'success');
      loadMonitorStatus();
    } catch (e) { toast(e.message, 'error'); }
  });

  mon.stopBtn.addEventListener('click', async () => {
    try {
      await api.post('/api/monitor/stop');
      toast('已停止', 'warn');
      loadMonitorStatus();
    } catch (e) { toast(e.message, 'error'); }
  });

  onPageEnter('monitor', () => {
    loadMonitorStatus();
    loadMonitorEmails();
  });

  // 监听页定时刷新邮件列表（独立于全局轮询）
  setInterval(() => {
    if (document.querySelector('[data-page-content="monitor"]')?.hidden === false) {
      loadMonitorEmails();
      loadMonitorStatus();
    }
  }, 5000);


  // =====================================================================
  //  数据管理页（邮箱导入）
  // =====================================================================
  const dat = {
    importText: document.getElementById('data-import-text'),
    importBtn:  document.getElementById('btn-data-import'),
    refreshBtn: document.getElementById('btn-data-refresh'),
    filter:     document.getElementById('data-filter'),
    tbody:      document.getElementById('data-tbody'),
    count:      document.getElementById('data-emails-count'),
  };

  async function loadEmails() {
    try {
      const status = dat.filter.value;
      const url = status ? `/api/emails?status=${encodeURIComponent(status)}` : '/api/emails';
      const r = await api.get(url);
      dat.count.textContent = `(${r.count})`;
      if (!r.count) {
        dat.tbody.innerHTML = '<tr><td colspan="5" class="text-center text-slate-400 py-4">暂无邮箱</td></tr>';
        return;
      }
      dat.tbody.innerHTML = r.items.map((e) => `
        <tr>
          <td class="font-mono">${escapeHtml(e.email)}</td>
          <td><span class="badge ${statusBadgeColor(e.status)}">${escapeHtml(e.status) || 'unused'}</span></td>
          <td class="text-xs text-slate-500">${escapeHtml(e.created_at) || '-'}</td>
          <td class="text-xs text-slate-500">${escapeHtml(e.used_at) || '-'}</td>
          <td class="text-right">
            <button class="btn btn-ghost text-xs" data-del="${e.id}">🗑️</button>
          </td>
        </tr>`).join('');
      dat.tbody.querySelectorAll('[data-del]').forEach((b) => {
        b.addEventListener('click', async () => {
          const ok = await confirmDialog('删除邮箱', '确定？');
          if (!ok) return;
          try {
            await api.del(`/api/emails/${b.dataset.del}`);
            toast('已删除', 'success');
            loadEmails();
          } catch (e) { toast(e.message, 'error'); }
        });
      });
    } catch (e) {
      dat.tbody.innerHTML = `<tr><td colspan="5" class="text-center text-red-500 py-4">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
  }

  dat.importBtn.addEventListener('click', async () => {
    const text = dat.importText.value.trim();
    if (!text) {
      toast('请粘贴邮箱', 'warn');
      return;
    }
    try {
      const r = await api.post('/api/emails/import', { text });
      toast(`成功 ${r.success_count} · 失败 ${r.fail_count}`, r.fail_count ? 'warn' : 'success');
      if (r.fail_count) console.warn('邮箱导入失败详情:', r.failures);
      dat.importText.value = '';
      loadEmails();
    } catch (e) { toast(e.message, 'error'); }
  });

  dat.refreshBtn.addEventListener('click', loadEmails);
  dat.filter.addEventListener('change', loadEmails);
  onPageEnter('data', loadEmails);
})();
