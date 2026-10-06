<script>
  import { tick } from "svelte";

  let session = null;
  let logs = [];
  let loginUser = "surveyor";
  let loginPass = "surv123456";
  let chainage = "";
  let deltaMm = "";
  let error = "";
  let loading = false;
  let timer;

  // 页眉导航：测量记录 / 邻断面对照
  let view = "logs";

  // 邻断面对照状态
  let cmpLeft = "";
  let cmpRight = "";
  let cmpAsOf = "";
  let cmpResult = null;
  let cmpLoading = false;
  let cmpError = "";
  let cmpSeq = 0;

  $: isWriter = session?.role === "writer";
  $: chainages = [...new Set(logs.map((l) => l.chainage))].sort();
  $: cmpSame = cmpLeft && cmpRight && cmpLeft === cmpRight;
  $: cmpReady = Boolean(cmpLeft && cmpRight && cmpAsOf && !cmpSame);

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
      timer = setInterval(refresh, 2000);
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
    view = "logs";
    resetCompare();
    localStorage.removeItem("tunnel_session");
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
    } catch {
      error = "提交时网络异常";
    } finally {
      loading = false;
    }
  }

  function toLocalInput(d) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function fmtTime(iso) {
    return iso ? new Date(iso).toLocaleString() : "—";
  }

  function resetCompare() {
    cmpResult = null;
    cmpError = "";
    cmpLoading = false;
    cmpSeq += 1;
  }

  function compareReady() {
    return Boolean(cmpLeft && cmpRight && cmpAsOf && cmpLeft !== cmpRight);
  }

  function enterCompare() {
    view = "compare";
    if (!cmpAsOf) cmpAsOf = toLocalInput(new Date());
    // 进页时条件已齐就重算一遍，保证中排是最新重算结果
    if (isWriter && compareReady()) recalcCompare();
  }

  // 选定条件一变：旧结果立即作废（不留假数），条件齐了就触发重算
  async function onCompareInput() {
    await tick(); // 等绑定值与响应式语句刷新
    resetCompare();
    if (isWriter && compareReady()) recalcCompare();
  }

  async function recalcCompare() {
    if (!isWriter || !compareReady()) return;
    const seq = ++cmpSeq;
    cmpLoading = true;
    cmpError = "";
    cmpResult = null;
    try {
      const res = await fetch("/api/compare/recalc", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers() },
        body: JSON.stringify({
          left: cmpLeft,
          right: cmpRight,
          as_of: new Date(cmpAsOf).toISOString(),
        }),
      });
      const data = await res.json();
      if (seq !== cmpSeq) return; // 只认最后一次重算的返回
      if (!res.ok) {
        cmpError = data.detail || "重算失败";
        return;
      }
      cmpResult = data;
    } catch {
      if (seq === cmpSeq) cmpError = "重算时网络异常";
    } finally {
      if (seq === cmpSeq) cmpLoading = false;
    }
  }

  $: harderText =
    cmpResult && cmpResult.harder === "left"
      ? `左侧 ${cmpResult.left.chainage} 挤得更狠`
      : cmpResult && cmpResult.harder === "right"
        ? `右侧 ${cmpResult.right.chainage} 挤得更狠`
        : cmpResult && cmpResult.harder === "tie"
          ? "两侧绝对值相同，一样狠"
          : "";

  const raw = localStorage.getItem("tunnel_session");
  if (raw) {
    try {
      session = JSON.parse(raw);
      refresh();
      timer = setInterval(refresh, 2000);
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
  h1 { color: #fbbf24; margin: 0 0 0.25rem; }
  h2 { font-size: 1.05rem; margin: 0 0 0.75rem; color: #fcd34d; }
  .sub { color: #a8a29e; margin-bottom: 1.25rem; }
  .topbar {
    display: flex; justify-content: space-between; align-items: flex-end;
    gap: 1rem; flex-wrap: wrap; margin-bottom: 1.25rem;
    border-bottom: 1px solid #44403c; padding-bottom: 0.75rem;
  }
  .topbar .sub { margin: 0.25rem 0 0; }
  nav { display: flex; gap: 0.5rem; }
  nav button.nav { background: #44403c; }
  nav button.nav.active { background: #d97706; }
  section {
    background: #292524; border: 1px solid #44403c; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 1rem;
  }
  label { display: block; font-size: 0.85rem; color: #d6d3d1; margin-bottom: 0.25rem; }
  input, select {
    width: 100%; box-sizing: border-box; padding: 0.5rem 0.65rem; border-radius: 6px;
    border: 1px solid #57534e; background: #0c0a09; color: #fafaf9; margin-bottom: 0.75rem;
  }
  button {
    cursor: pointer; padding: 0.5rem 1rem; border: none; border-radius: 6px;
    background: #d97706; color: #fff; font-weight: 600;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.secondary { background: #57534e; }
  .err { color: #fb7185; }
  .muted { color: #a8a29e; font-size: 0.85rem; }
  .warn { color: #fde68a; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.45rem; border-bottom: 1px solid #44403c; }
  .tag { padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.8rem; }
  .ok { background: #14532d; color: #86efac; }
  .bad { background: #7f1d1d; color: #fca5a5; }
  .pending { background: #713f12; color: #fde68a; }
  .compare-controls {
    display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 0.75rem; align-items: end;
  }
  .compare-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem;
  }
  .cell {
    background: #0c0a09; border: 1px solid #44403c; border-radius: 6px;
    padding: 0.75rem; text-align: center;
  }
  .cell .val { font-size: 1.4rem; font-weight: 700; color: #fbbf24; margin: 0.25rem 0; }
  @media (max-width: 720px) {
    .compare-controls, .compare-grid { grid-template-columns: 1fr; }
  }
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
    <header class="topbar">
      <div>
        <h1>隧道收敛测缝台</h1>
        <p class="sub">已登录：{session.username}（{isWriter ? "测量员·可提交" : "巡检岗·只读"}）</p>
      </div>
      <nav>
        <button class="nav" class:active={view === "logs"} on:click={() => (view = "logs")}>测量记录</button>
        <button class="nav" class:active={view === "compare"} on:click={enterCompare}>邻断面对照</button>
        <button class="secondary" on:click={logout}>退出</button>
      </nav>
    </header>

    {#if view === "logs"}
      <section>
        <button class="secondary" disabled={loading} on:click={refresh}>刷新列表</button>
      </section>
      {#if isWriter}
        <section>
          <label>里程桩号</label>
          <input placeholder="例如 K20+050" bind:value={chainage} />
          <label>收敛（毫米，可正可负）</label>
          <input type="number" step="0.1" bind:value={deltaMm} />
          <button disabled={loading} on:click={submit}>提交（进入待认领）</button>
          {#if error}<p class="err">{error}</p>{/if}
        </section>
      {/if}
      <section>
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
        <h2>邻断面对照 · 选桩号</h2>
        {#if !isWriter}
          <p class="warn">巡检岗为只读岗位，不能报送重算，下面控件已锁定。</p>
        {/if}
        <div class="compare-controls">
          <div>
            <label>左侧桩号</label>
            <select bind:value={cmpLeft} disabled={!isWriter} on:change={onCompareInput}>
              <option value="">请选择</option>
              {#each chainages as c}<option value={c}>{c}</option>{/each}
            </select>
          </div>
          <div>
            <label>右侧桩号</label>
            <select bind:value={cmpRight} disabled={!isWriter} on:change={onCompareInput}>
              <option value="">请选择</option>
              {#each chainages as c}<option value={c}>{c}</option>{/each}
            </select>
          </div>
          <div>
            <label>截止时刻</label>
            <input type="datetime-local" bind:value={cmpAsOf} disabled={!isWriter} on:change={onCompareInput} />
          </div>
          <button disabled={!isWriter || cmpLoading || !cmpReady} on:click={recalcCompare}>
            {cmpLoading ? "重算中…" : "重算"}
          </button>
        </div>
        {#if cmpSame}<p class="err">两个桩号不能相同。</p>{/if}
        {#if cmpError}<p class="err">{cmpError}</p>{/if}
      </section>

      <section>
        <h2>最近办结值与差值</h2>
        {#if cmpLoading}
          <p class="muted">重算中，结果以接口返回为准……</p>
        {:else if cmpResult}
          <div class="compare-grid">
            <div class="cell">
              <div class="muted">左 · {cmpLeft}</div>
              {#if cmpResult.left}
                <div class="val">{cmpResult.left.delta_mm} mm</div>
                <span class="tag {cmpResult.left.verdict === '合格' ? 'ok' : 'bad'}">{cmpResult.left.verdict}</span>
                <div class="muted">记录于 {fmtTime(cmpResult.left.created_at)}</div>
              {:else}
                <div class="val">—</div>
                <div class="muted">截止时刻前无已办结记录</div>
              {/if}
            </div>
            <div class="cell">
              <div class="muted">右 · {cmpRight}</div>
              {#if cmpResult.right}
                <div class="val">{cmpResult.right.delta_mm} mm</div>
                <span class="tag {cmpResult.right.verdict === '合格' ? 'ok' : 'bad'}">{cmpResult.right.verdict}</span>
                <div class="muted">记录于 {fmtTime(cmpResult.right.created_at)}</div>
              {:else}
                <div class="val">—</div>
                <div class="muted">截止时刻前无已办结记录</div>
              {/if}
            </div>
            <div class="cell">
              <div class="muted">差值（左 − 右）</div>
              {#if cmpResult.diff_mm !== null}
                <div class="val">{cmpResult.diff_mm} mm</div>
                <div class="muted">{harderText}</div>
              {:else}
                <div class="val">—</div>
                <div class="muted">任一侧未办结，不出差值</div>
              {/if}
            </div>
          </div>
          <p class="muted">本次重算截至 {fmtTime(cmpResult.as_of)}，接口重算时刻 {fmtTime(cmpResult.recalculated_at)}。</p>
        {:else}
          <p class="muted">选好两个桩号和截止时刻后自动重算；未重算前这里不填数。</p>
        {/if}
      </section>

      <section>
        <h2>口径</h2>
        <p class="muted">
          每侧取所选桩号在截止时刻（含）之前最近一条已办结记录的收敛值；差值 = 左侧收敛 − 右侧收敛，单位 mm；
          谁挤得更狠按绝对值判定。任一侧在截止时刻前没有已办结记录时，该侧与差值一律留空，不出假数；
          截止时刻之外的测点本次不算。重算与截止时刻必须一起提交，缺一边接口不收。
          合格标准沿用判定规则：|收敛| ≤ 3.0 mm 为合格。测量员可选桩号报送重算，巡检岗只读不能报送。
        </p>
      </section>
    {/if}
  {/if}
</main>
