<script>
  let session = null;
  let logs = [];
  let loginUser = "surveyor";
  let loginPass = "surv123456";
  let chainage = "";
  let deltaMm = "";
  let error = "";
  let loading = false;
  let timer;
  let view = "desk";

  // 邻断面对照页状态
  let chainages = [];
  let pickA = "";
  let pickB = "";
  let startAt = "";
  let cutoffAt = nowLocalInput();
  let calc = null; // 只装后端“重算”的返回；选择一变就清空
  let caliber = "";
  let reports = [];
  let compareBusy = false;

  $: isWriter = session?.role === "writer";

  function nowLocalInput() {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  function toIso(localValue) {
    if (!localValue) return null;
    return new Date(localValue).toISOString();
  }

  function fmtDt(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("zh-CN", { hour12: false });
  }

  function headers() {
    return session ? { Authorization: "Bearer " + session.token } : {};
  }

  async function refresh() {
    if (!session) return;
    const res = await fetch("/api/logs", { headers: headers() });
    if (res.status === 401) {
      logout();
      return;
    }
    if (res.ok) logs = await res.json();
  }

  async function refreshChainages() {
    if (!session) return;
    const res = await fetch("/api/chainages", { headers: headers() });
    if (res.ok) chainages = await res.json();
  }

  async function refreshReports() {
    if (!session) return;
    const res = await fetch("/api/comparisons", { headers: headers() });
    if (res.ok) reports = await res.json();
  }

  async function login() {
    error = "";
    loading = true;
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      });
      const data = await res.json();
      if (!res.ok) {
        error = data.detail || "登录失败";
        return;
      }
      session = { token: data.access_token, username: data.username, role: data.role };
      localStorage.setItem("tunnel_session", JSON.stringify(session));
      await refresh();
      await refreshChainages();
      await refreshReports();
      timer = setInterval(tick, 2000);
    } catch {
      error = "无法连接接口";
    } finally {
      loading = false;
    }
  }

  function logout() {
    if (timer) clearInterval(timer);
    session = null;
    logs = [];
    reports = [];
    chainages = [];
    calc = null;
    view = "desk";
    localStorage.removeItem("tunnel_session");
  }

  async function tick() {
    await refresh();
    if (view === "compare") await refreshReports();
  }

  function switchView(name) {
    view = name;
    error = "";
    if (name === "compare") {
      refreshReports();
      refreshChainages();
    }
  }

  // 选择项一变，中间列立刻作废：没重新重算之前不允许留着旧数，更不许临时填数
  function invalidateCalc() {
    calc = null;
    error = "";
  }

  async function submit() {
    error = "";
    loading = true;
    try {
      const res = await fetch("/api/logs", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers() },
        body: JSON.stringify({ chainage, delta_mm: Number(deltaMm) }),
      });
      const data = await res.json();
      if (!res.ok) {
        error = data.detail || "提交失败";
        return;
      }
      chainage = "";
      deltaMm = "";
      await refresh();
      await refreshChainages();
    } catch {
      error = "提交时网络异常";
    } finally {
      loading = false;
    }
  }

  function comparePayload() {
    return {
      chainage_a: pickA,
      chainage_b: pickB,
      start_at: toIso(startAt),
      cutoff_at: toIso(cutoffAt),
    };
  }

  async function recompute() {
    error = "";
    if (!pickA || !pickB) {
      error = "必须在上部选定两个桩号";
      return;
    }
    if (pickA === pickB) {
      error = "两个桩号不能相同";
      return;
    }
    if (!cutoffAt) {
      error = "重算必须带截止时刻";
      return;
    }
    compareBusy = true;
    try {
      const res = await fetch("/api/comparisons/recompute", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers() },
        body: JSON.stringify(comparePayload()),
      });
      const data = await res.json();
      if (!res.ok) {
        error = data.detail || "重算失败";
        calc = null;
        return;
      }
      calc = data;
    } catch {
      error = "重算时网络异常";
    } finally {
      compareBusy = false;
    }
  }

  async function submitReport() {
    error = "";
    if (!caliber.trim()) {
      error = "请先写下对照口径";
      return;
    }
    if (!cutoffAt) {
      error = "重算和截止时刻必须一起提交，缺截止时刻不能报送";
      return;
    }
    compareBusy = true;
    try {
      const res = await fetch("/api/comparisons", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers() },
        body: JSON.stringify({ ...comparePayload(), caliber: caliber.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        error = data.detail || "报送失败";
        return;
      }
      caliber = "";
      calc = null;
      await refreshReports();
    } catch {
      error = "报送时网络异常";
    } finally {
      compareBusy = false;
    }
  }

  const raw = localStorage.getItem("tunnel_session");
  if (raw) {
    try {
      session = JSON.parse(raw);
      refresh();
      refreshChainages();
      refreshReports();
      timer = setInterval(tick, 2000);
    } catch {
      localStorage.removeItem("tunnel_session");
    }
  }
</script>

<style>
  :global(body) {
    margin: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: #1c1917;
    color: #f5f5f4;
  }
  main { max-width: 960px; margin: 0 auto; padding: 1.5rem; }
  .topbar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
  h1 { color: #fbbf24; margin: 0; font-size: 1.4rem; }
  nav { display: flex; gap: 0.5rem; }
  nav button { background: #44403c; }
  nav button.active { background: #d97706; }
  .sub { color: #a8a29e; margin: 0.5rem 0 1.25rem; }
  section {
    background: #292524; border: 1px solid #44403c; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 1rem;
  }
  h2 { font-size: 1rem; color: #fbbf24; margin: 0 0 0.75rem; }
  label { display: block; font-size: 0.85rem; color: #d6d3d1; margin-bottom: 0.25rem; }
  input, select, textarea {
    width: 100%; box-sizing: border-box; padding: 0.5rem 0.65rem; border-radius: 6px;
    border: 1px solid #57534e; background: #0c0a09; color: #fafaf9; margin-bottom: 0.75rem;
    font-family: inherit; font-size: 0.9rem;
  }
  textarea { resize: vertical; min-height: 4.5rem; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1rem; }
  @media (max-width: 720px) { .grid2 { grid-template-columns: 1fr; } }
  button {
    cursor: pointer; padding: 0.5rem 1rem; border: none; border-radius: 6px;
    background: #d97706; color: #fff; font-weight: 600;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.secondary { background: #57534e; font-weight: 400; }
  .err { color: #fb7185; }
  .hint { color: #a8a29e; font-size: 0.85rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.45rem; border-bottom: 1px solid #44403c; }
  .tag { padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.8rem; }
  .ok { background: #14532d; color: #86efac; }
  .bad { background: #7f1d1d; color: #fca5a5; }
  .pending { background: #713f12; color: #fde68a; }
  .empty { color: #78716c; font-style: italic; }
  .num { font-variant-numeric: tabular-nums; font-weight: 600; }
</style>

<main>
  {#if !session}
    <h1>隧道收敛测缝台</h1>
    <p class="sub">测量员提交桩号与收敛毫米值，接口进程内线程认领后出结论。登录框已预填可写账号 surveyor / surv123456。</p>
    <section>
      <label>用户名</label>
      <input bind:value={loginUser} autocomplete="off" />
      <label>密码</label>
      <input type="password" bind:value={loginPass} autocomplete="off" />
      <button disabled={loading} on:click={login}>登录</button>
      {#if error}<p class="err">{error}</p>{/if}
    </section>
  {:else}
    <div class="topbar">
      <h1>隧道收敛测缝台</h1>
      <nav>
        <button class={view === "desk" ? "active" : ""} on:click={() => switchView("desk")}>登记台</button>
        <button class={view === "compare" ? "active" : ""} on:click={() => switchView("compare")}>邻断面对照</button>
      </nav>
    </div>
    <p class="sub">已登录：{session.username}（{isWriter ? "测量员 · 可报送" : "巡检岗 · 只读，不能报送"}）</p>

    {#if view === "desk"}
      <section>
        <button class="secondary" on:click={logout}>退出</button>
        <button class="secondary" disabled={loading} on:click={refresh}>刷新列表</button>
      </section>
      {#if isWriter}
        <section>
          <h2>提交收敛读数</h2>
          <label>里程桩号</label>
          <input placeholder="例如 K20+050" bind:value={chainage} />
          <label>收敛（毫米，可正可负）</label>
          <input type="number" step="0.1" bind:value={deltaMm} />
          <button disabled={loading} on:click={submit}>提交（进入待认领）</button>
          {#if error}<p class="err">{error}</p>{/if}
        </section>
      {/if}
      <section>
        <h2>读数明细</h2>
        <table>
          <thead>
            <tr><th>编号</th><th>桩号</th><th>收敛mm</th><th>状态</th><th>结论</th><th>说明</th></tr>
          </thead>
          <tbody>
            {#each logs as row}
              <tr>
                <td>{row.id}</td>
                <td>{row.chainage}</td>
                <td>{row.delta_mm}</td>
                <td><span class="tag {row.status === 'pending' ? 'pending' : 'ok'}">{row.status === 'pending' ? '待处理' : '已完成'}</span></td>
                <td>
                  {#if row.verdict}
                    <span class="tag {row.verdict === '合格' ? 'ok' : 'bad'}">{row.verdict}</span>
                  {:else}—{/if}
                </td>
                <td>{row.reason ?? "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </section>
    {:else}
      <section>
        <button class="secondary" on:click={logout}>退出</button>
      </section>

      <!-- 上部：选两个桩号 + 选定时段 -->
      <section>
        <h2>① 选定断面与时段</h2>
        <div class="grid2">
          <div>
            <label>桩号 A</label>
            <select bind:value={pickA} on:change={invalidateCalc}>
              <option value="">— 选择桩号 —</option>
              {#each chainages as c}<option value={c}>{c}</option>{/each}
            </select>
          </div>
          <div>
            <label>桩号 B（相邻断面）</label>
            <select bind:value={pickB} on:change={invalidateCalc}>
              <option value="">— 选择桩号 —</option>
              {#each chainages as c}<option value={c}>{c}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid2">
          <div>
            <label>时段起始（可选，留空即截止时刻之前全部）</label>
            <input type="datetime-local" step="1" bind:value={startAt} on:change={invalidateCalc} />
          </div>
          <div>
            <label>截止时刻（必填，与重算一起提交）</label>
            <input type="datetime-local" step="1" bind:value={cutoffAt} on:change={invalidateCalc} />
          </div>
        </div>
        <button disabled={compareBusy} on:click={recompute}>重算</button>
        {#if error}<p class="err">{error}</p>{/if}
      </section>

      <!-- 中部：只列最近办结值和差值；数只能来自重算 -->
      <section>
        <h2>② 最近办结值与差值</h2>
        {#if !calc}
          <p class="hint">选定桩号与截止时刻后点“重算”。未重算前中间列不填数；任一侧在选定时段内没有办结读数时，该侧与差值一律留空。</p>
        {:else}
          <table>
            <thead>
              <tr><th>侧</th><th>桩号</th><th>时段内最近办结值（mm）</th><th>办结时刻</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>A</td>
                <td>{calc.chainage_a}</td>
                {#if calc.value_a !== undefined}
                  <td class="num">{calc.value_a}</td>
                  <td>{fmtDt(calc.processed_at_a)}</td>
                {:else}
                  <td class="empty">— 时段内无办结读数 —</td>
                  <td class="empty">—</td>
                {/if}
              </tr>
              <tr>
                <td>B</td>
                <td>{calc.chainage_b}</td>
                {#if calc.value_b !== undefined}
                  <td class="num">{calc.value_b}</td>
                  <td>{fmtDt(calc.processed_at_b)}</td>
                {:else}
                  <td class="empty">— 时段内无办结读数 —</td>
                  <td class="empty">—</td>
                {/if}
              </tr>
              <tr>
                <td colspan="2"><strong>差值（A − B，mm）</strong></td>
                {#if calc.ready}
                  <td class="num">{calc.diff_mm}</td>
                {:else}
                  <td class="empty" colspan="2">— 两侧未齐办结，不出差值 —</td>
                {/if}
                {#if calc.ready}<td></td>{/if}
              </tr>
            </tbody>
          </table>
          {#if !calc.ready}
            <p class="err">缺失办结值：{calc.missing.join("、")}。未办结不许报送，也不替它填假数。</p>
          {/if}
        {/if}
      </section>

      <!-- 下部：口径与报送 -->
      <section>
        <h2>③ 对照口径与报送</h2>
        {#if isWriter}
          <label>口径说明（判定谁挤得更狠的依据）</label>
          <textarea bind:value={caliber} placeholder="例如：取选定时段内两侧最近一次已办结收敛，按 A−B 差值比较，差值为正即 A 侧挤压更重。"></textarea>
          <button
            disabled={compareBusy || !calc || !calc.ready || !caliber.trim()}
            on:click={submitReport}
          >
            报送对照
          </button>
          {#if calc && !calc.ready}<p class="hint">任一侧尚无办结值，报送按钮保持禁用。</p>{/if}
          {#if !calc}<p class="hint">请先点“重算”，报送与截止时刻必须一起提交。</p>{/if}
        {:else}
          <p class="hint">巡检岗可在本页选桩号、点重算查看对照，但不能报送；报送仅测量员可操作。</p>
        {/if}
      </section>

      <section>
        <h2>已报送对照</h2>
        {#if reports.length === 0}
          <p class="hint">还没有报送记录。</p>
        {:else}
          <table>
            <thead>
              <tr><th>编号</th><th>桩号 A</th><th>桩号 B</th><th>时段起</th><th>截止</th><th>A 值</th><th>B 值</th><th>差值 mm</th><th>口径</th><th>报送人</th><th>报送时刻</th></tr>
            </thead>
            <tbody>
              {#each reports as r}
                <tr>
                  <td>{r.id}</td>
                  <td>{r.chainage_a}</td>
                  <td>{r.chainage_b}</td>
                  <td>{fmtDt(r.start_at)}</td>
                  <td>{fmtDt(r.cutoff_at)}</td>
                  <td class="num">{r.value_a}</td>
                  <td class="num">{r.value_b}</td>
                  <td class="num">{r.diff_mm}</td>
                  <td>{r.caliber}</td>
                  <td>{r.submitted_by}</td>
                  <td>{fmtDt(r.submitted_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </section>
    {/if}
  {/if}
</main>
