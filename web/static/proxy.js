/* =====================================================================
 *  代理配置页
 * ===================================================================== */
(function () {
  const { api, toast, confirm: confirmDialog, onPageEnter } = window.App;

  const els = {
    // 链式代理
    chainEnabled: document.getElementById('chain-enabled'),
    chainUrl:     document.getElementById('chain-url'),
    saveChainBtn: document.getElementById('btn-save-chain'),
    // 添加
    text:         document.getElementById('proxy-text'),
    detect:       document.getElementById('proxy-detect'),
    addBtn:       document.getElementById('btn-add-proxies'),
    // 列表
    tbody:        document.getElementById('proxy-tbody'),
    listCount:    document.getElementById('proxy-list-count'),
    poolTag:      document.getElementById('proxy-pool-tag'),
    useAllBtn:    document.getElementById('btn-use-all'),
    clearPoolBtn: document.getElementById('btn-clear-pool'),
    clearAllBtn:  document.getElementById('btn-clear-all'),
  };

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ============================ 链式代理 ============================
  async function loadChainSettings() {
    try {
      const r = await api.get('/api/proxies/chain');
      const s = r.settings || {};
      els.chainEnabled.checked = !!s.enabled;
      els.chainUrl.value = s.upstream_url || 'http://127.0.0.1:7897';
    } catch (e) {
      toast('读取链式设置失败：' + e.message, 'error');
    }
  }

  els.saveChainBtn.addEventListener('click', async () => {
    try {
      await api.put('/api/proxies/chain', {
        enabled: els.chainEnabled.checked,
        upstream_url: els.chainUrl.value.trim(),
      });
      toast('已保存链式代理设置', 'success');
    } catch (e) {
      toast('保存失败：' + e.message, 'error');
    }
  });

  // ============================ 代理列表 ============================
  async function loadProxies() {
    try {
      const r = await api.get('/api/proxies');
      els.listCount.textContent = `(${r.count})`;
      els.poolTag.textContent = `(${r.pool_count} 个)`;

      if (!r.count) {
        els.tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-400 py-4">暂无代理</td></tr>';
        return;
      }
      els.tbody.innerHTML = r.items.map((p) => `
        <tr>
          <td class="font-mono text-xs">${escapeHtml(p.protocol)}</td>
          <td class="font-mono text-xs">${escapeHtml(p.host)}:${p.port}</td>
          <td class="font-mono text-xs">${escapeHtml(p.ip_address) || '<span class="text-slate-400">—</span>'}</td>
          <td class="text-xs">${escapeHtml(p.location) || '<span class="text-slate-400">—</span>'}</td>
          <td class="text-xs">${escapeHtml(p.provider) || ''} <span class="text-slate-400">${escapeHtml(p.as_number) || ''}</span></td>
          <td class="text-xs">${p.in_pool ? '<span class="badge bg-green">在池</span>' : '<span class="text-slate-400">—</span>'}</td>
          <td class="text-right text-xs">
            <button class="btn btn-ghost text-xs" data-use="${p.id}">✅ 使用</button>
            <button class="btn btn-ghost text-xs" data-recheck="${p.id}">🔍 重测</button>
            <button class="btn btn-ghost text-xs" data-del="${p.id}">🗑️</button>
          </td>
        </tr>`).join('');

      els.tbody.querySelectorAll('[data-use]').forEach((b) => {
        b.addEventListener('click', async () => {
          try {
            const r = await api.post('/api/proxies/use-one', { proxy_id: Number(b.dataset.use) });
            toast(`已使用（池=${r.pool_count}）`, 'success');
            loadProxies();
            window.App.refreshTopStatus();
          } catch (e) { toast(e.message, 'error'); }
        });
      });
      els.tbody.querySelectorAll('[data-recheck]').forEach((b) => {
        b.addEventListener('click', async () => {
          b.disabled = true;
          b.textContent = '🔄 检测中';
          try {
            const r = await api.post(`/api/proxies/${b.dataset.recheck}/recheck`);
            if (r.ok) toast(`重测成功：${r.result?.ip || ''}`, 'success');
            else      toast(`重测失败：${r.error || ''}`, 'error');
            loadProxies();
          } catch (e) { toast(e.message, 'error'); }
          finally {
            b.disabled = false;
            b.textContent = '🔍 重测';
          }
        });
      });
      els.tbody.querySelectorAll('[data-del]').forEach((b) => {
        b.addEventListener('click', async () => {
          const ok = await confirmDialog('删除代理', '确定删除这个代理？');
          if (!ok) return;
          try {
            await api.del(`/api/proxies/${b.dataset.del}`);
            toast('已删除', 'success');
            loadProxies();
          } catch (e) { toast(e.message, 'error'); }
        });
      });
    } catch (e) {
      els.tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red-500 py-4">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
  }

  // ============================ 添加 ============================
  els.addBtn.addEventListener('click', async () => {
    const text = els.text.value.trim();
    if (!text) {
      toast('请先粘贴代理', 'warn');
      return;
    }
    els.addBtn.disabled = true;
    const originalText = els.addBtn.textContent;
    els.addBtn.textContent = '⏳ 检测中（每条约 5-10 秒）...';
    try {
      const r = await api.post('/api/proxies', { text, detect: els.detect.checked });
      const msg = `成功 ${r.success_count} · 失败 ${r.fail_count}`;
      toast(msg, r.fail_count ? 'warn' : 'success', 4000);
      if (r.fail_count) {
        console.warn('代理添加失败详情:', r.failures);
      }
      els.text.value = '';
      loadProxies();
    } catch (e) {
      toast('添加失败：' + e.message, 'error');
    } finally {
      els.addBtn.disabled = false;
      els.addBtn.textContent = originalText;
    }
  });

  // ============================ 池操作 ============================
  els.useAllBtn.addEventListener('click', async () => {
    try {
      const r = await api.post('/api/proxies/use-all');
      const extra = r.skipped ? `（${r.skipped} 条解析失败已跳过）` : '';
      toast(`已加入 ${r.pool_count} 个到运行时池${extra}`, 'success');
      loadProxies();
      window.App.refreshTopStatus();
    } catch (e) { toast(e.message, 'error'); }
  });

  els.clearPoolBtn.addEventListener('click', async () => {
    try {
      await api.post('/api/proxies/clear-pool');
      toast('运行时池已清空（数据库未动）', 'warn');
      loadProxies();
      window.App.refreshTopStatus();
    } catch (e) { toast(e.message, 'error'); }
  });

  els.clearAllBtn.addEventListener('click', async () => {
    const ok = await confirmDialog('清空全部代理', '将删除所有已保存的代理，此操作不可恢复。确定？');
    if (!ok) return;
    try {
      await api.del('/api/proxies');
      toast('全部已清空', 'success');
      loadProxies();
      window.App.refreshTopStatus();
    } catch (e) { toast(e.message, 'error'); }
  });

  // 进入代理页时加载
  onPageEnter('proxy', () => {
    loadChainSettings();
    loadProxies();
  });

  // 初次进入（默认首页是 register，本脚本要在用户切到 proxy 才加载一次）
  // 但链式配置这种"小数据"可以提前拿，方便注册页若要用到
  loadChainSettings();
})();
