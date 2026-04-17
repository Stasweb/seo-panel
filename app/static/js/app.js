function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function getUaState() {
  const choiceEl = document.getElementById("ua-choice");
  const customEl = document.getElementById("ua-custom");
  const choice = (choiceEl?.value ?? localStorage.getItem("ua_choice") ?? "").toString();
  const custom = (customEl?.value ?? localStorage.getItem("ua_custom") ?? "").toString();
  return { ua: choice, custom_ua: custom };
}

function saveUaState() {
  const choiceEl = document.getElementById("ua-choice");
  const customEl = document.getElementById("ua-custom");
  if (choiceEl) localStorage.setItem("ua_choice", String(choiceEl.value ?? ""));
  if (customEl) localStorage.setItem("ua_custom", String(customEl.value ?? ""));

  const auditUa = document.getElementById("audit-ua");
  const auditCustomUa = document.getElementById("audit-custom-ua");
  if (auditUa && choiceEl) auditUa.value = String(choiceEl.value ?? "");
  if (auditCustomUa && customEl) auditCustomUa.value = String(customEl.value ?? "");

  const deepUa = document.getElementById("deep-audit-ua");
  const deepCustomUa = document.getElementById("deep-audit-custom-ua");
  if (deepUa && choiceEl) deepUa.value = String(choiceEl.value ?? "");
  if (deepCustomUa && customEl) deepCustomUa.value = String(customEl.value ?? "");
}

function initUaUi() {
  const choiceEl = document.getElementById("ua-choice");
  const customEl = document.getElementById("ua-custom");

  if (choiceEl && localStorage.getItem("ua_choice") && !choiceEl.value) {
    choiceEl.value = localStorage.getItem("ua_choice");
  }
  if (customEl && localStorage.getItem("ua_custom") && !customEl.value) {
    customEl.value = localStorage.getItem("ua_custom");
  }

  if (choiceEl) choiceEl.addEventListener("change", saveUaState);
  if (customEl) customEl.addEventListener("input", saveUaState);
  saveUaState();
}

function initDeepAuditUi() {
  const expandedEl = document.getElementById("deep-suggest-expanded");
  const modeEl = document.getElementById("deep-suggest-mode");
  if (!expandedEl || !modeEl) return;
  const apply = () => {
    modeEl.value = expandedEl.checked ? "expanded" : "basic";
  };
  expandedEl.addEventListener("change", apply);
  apply();
}

function buildUaQuery() {
  const { ua, custom_ua } = getUaState();
  const params = new URLSearchParams();
  if (ua) params.set("ua", ua);
  if (custom_ua) params.set("custom_ua", custom_ua);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function translateDetail(detail) {
  if (!detail) return "";
  if (detail === "Not authenticated") return "Требуется вход";
  if (detail === "Invalid credentials") return "Неверный логин или пароль";
  if (detail === "Forbidden") return "Недостаточно прав";
  if (detail === "Site not found") return "Сайт не найден";
  if (detail === "Task not found") return "Задача не найдена";
  if (detail === "site_id mismatch") return "Некорректный site_id";
  if (detail === "Invalid site_id") return "Некорректный сайт";
  if (detail === "domain is required") return "Укажите домен конкурента";
  if (detail === "Admin only") return "Требуются права администратора";
  if (detail === "Ahrefs not connected") return "Ahrefs не подключен для этого сайта";
  return detail;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value == null ? "—" : String(value);
}

function openDashboardSummary(kind) {
  const modal = document.getElementById("dashboard-summary-modal");
  const titleEl = document.getElementById("dashboard-summary-title");
  const subEl = document.getElementById("dashboard-summary-subtitle");
  const bodyEl = document.getElementById("dashboard-summary-body");
  const linkEl = document.getElementById("dashboard-summary-link");
  if (!modal || !titleEl || !bodyEl || !linkEl) return;

  const k = (kind || "").toString();
  modal.classList.remove("hidden");
  bodyEl.innerHTML = '<div class="text-sm text-gray-500">Загрузка…</div>';

  if (k === "sites") {
    titleEl.textContent = "Сайты";
    if (subEl) subEl.textContent = "Список сайтов в системе";
    linkEl.href = "/sites";
    linkEl.textContent = "Перейти к сайтам";
    _fetchJson("/api/sites/")
      .then((sites) => {
        const list = Array.isArray(sites) ? sites : [];
        bodyEl.innerHTML = list.length
          ? `<div class="space-y-2">${list
              .slice(0, 50)
              .map((s) => `<div class="p-3 bg-gray-50 border rounded-lg">${escapeHtml(String(s.domain ?? ""))}</div>`)
              .join("")}</div>`
          : '<div class="text-sm text-gray-500">Нет сайтов</div>';
      })
      .catch((e) => {
        bodyEl.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
      });
    return;
  }

  if (k === "tasks_todo" || k === "tasks_in_progress") {
    const status = k === "tasks_todo" ? "todo" : "in_progress";
    titleEl.textContent = status === "todo" ? "Задачи (в ожидании)" : "Задачи (в работе)";
    if (subEl) subEl.textContent = "Последние задачи по статусу";
    linkEl.href = `/tasks${status ? `?status=${encodeURIComponent(status)}` : ""}`;
    linkEl.textContent = "Перейти к задачам";
    _fetchJson(`/api/tasks/?status=${encodeURIComponent(status)}&limit=50`)
      .then((payload) => {
        const items = Array.isArray(payload?.items) ? payload.items : [];
        bodyEl.innerHTML = items.length
          ? `<div class="space-y-2">${items
              .map((t) => {
                const dom = (t.site_domain || "").toString();
                const ttl = (t.title || "").toString();
                return `<div class="p-3 bg-gray-50 border rounded-lg">
                  <div class="text-xs text-gray-500">${escapeHtml(dom)}</div>
                  <div class="font-medium">${escapeHtml(ttl)}</div>
                </div>`;
              })
              .join("")}</div>`
          : '<div class="text-sm text-gray-500">Нет задач</div>';
      })
      .catch((e) => {
        bodyEl.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
      });
    return;
  }

  if (k === "content_ideas") {
    titleEl.textContent = "Идеи контента";
    if (subEl) subEl.textContent = "План контента (статус idea)";
    linkEl.href = "/content-plans";
    linkEl.textContent = "Перейти к контенту";
    _fetchJson("/api/content-plans/?status=idea&limit=50")
      .then((payload) => {
        const items = Array.isArray(payload?.items) ? payload.items : [];
        bodyEl.innerHTML = items.length
          ? `<div class="space-y-2">${items
              .map((r) => {
                const dom = (r.site_domain || "").toString();
                const ttl = (r.title || "").toString();
                const url = (r.url || "").toString();
                return `<div class="p-3 bg-gray-50 border rounded-lg">
                  <div class="text-xs text-gray-500">${escapeHtml(dom)}</div>
                  <div class="font-medium">${escapeHtml(ttl)}</div>
                  ${url ? `<div class="text-xs text-gray-500 mt-1 break-all">${escapeHtml(url)}</div>` : ""}
                </div>`;
              })
              .join("")}</div>`
          : '<div class="text-sm text-gray-500">Нет идей</div>';
      })
      .catch((e) => {
        bodyEl.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
      });
    return;
  }
}

function closeDashboardSummary() {
  const modal = document.getElementById("dashboard-summary-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

function renderDashboard(data) {
  setText("stat-sites", data.sites_count);
  setText("stat-todo", data.tasks_todo);
  setText("stat-inprogress", data.tasks_in_progress);
  setText("stat-ideas", data.content_idea);

  const tbody = document.getElementById("positions-body");
  if (!tbody) return;
  const positions = Array.isArray(data.last_positions) ? data.last_positions : [];
  if (positions.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="4" class="px-4 py-8 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }

  tbody.innerHTML = positions
    .map((p) => {
      const keyword = p.keyword ?? "";
      const pos = p.position ?? "";
      const date = p.check_date ?? "";
      const source = p.source ?? "";
      return `
        <tr>
          <td class="px-4 py-3 font-medium">${escapeHtml(keyword)}</td>
          <td class="px-4 py-3"><span class="px-2 py-1 bg-gray-100 rounded text-gray-600">${escapeHtml(
            String(pos)
          )}</span></td>
          <td class="px-4 py-3 text-gray-500">${escapeHtml(String(date))}</td>
          <td class="px-4 py-3 text-gray-500 uppercase">${escapeHtml(String(source))}</td>
        </tr>
      `;
    })
    .join("");
}

function renderDashboardKeywordDeltas(payload) {
  const body = document.getElementById("dashboard-deltas-body");
  if (!body) return;
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="4" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((r) => {
      const delta = Number(r.delta ?? 0);
      const badge =
        delta > 0
          ? _badge(`+${delta}`, "bg-emerald-100 text-emerald-700")
          : delta < 0
          ? _badge(`${delta}`, "bg-rose-100 text-rose-700")
          : _badge("0", "bg-gray-200 text-gray-800");
      return `
        <tr>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.keyword ?? ""))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.prev_position ?? "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.current_position ?? "—"))}</td>
          <td class="px-4 py-2">${badge}</td>
        </tr>
      `;
    })
    .join("");
}

function renderDashboardRecentErrors(payload) {
  const listEl = document.getElementById("dashboard-errors-list");
  if (!listEl) return;
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    listEl.innerHTML = '<div class="text-sm text-gray-400">Нет ошибок</div>';
    return;
  }
  listEl.innerHTML = items
    .map((r) => {
      const level = String(r.level ?? "").toUpperCase();
      const levelBadge =
        level === "ERROR"
          ? _badge("ERROR", "bg-rose-100 text-rose-700")
          : _badge("WARNING", "bg-amber-100 text-amber-700");
      const ts = (r.created_at ?? "").toString().slice(0, 19).replace("T", " ");
      const category = r.category ? `[${r.category}] ` : "";
      const msg = `${category}${String(r.message ?? "")}`;
      return `
        <div class="p-3 border rounded-lg bg-gray-50">
          <div class="flex items-center justify-between gap-3">
            <div class="text-xs text-gray-500">${escapeHtml(ts || "—")}</div>
            <div>${levelBadge}</div>
          </div>
          <div class="mt-1 text-sm text-gray-800 break-all">${escapeHtml(msg)}</div>
        </div>
      `;
    })
    .join("");
}

async function loadDashboardWidgets() {
  const deltasLoader = document.getElementById("dashboard-deltas-loader");
  const errorsLoader = document.getElementById("dashboard-errors-loader");
  const siteFilter = document.getElementById("dashboard-site-filter");
  if (!deltasLoader || !errorsLoader || !siteFilter) return;

  const sites = await _fetchJson("/api/sites/");
  const list = Array.isArray(sites) ? sites : [];
  const current = (siteFilter.value || localStorage.getItem("dashboard_site_id") || "").toString();
  siteFilter.innerHTML = ['<option value="">Все сайты</option>']
    .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
    .join("");
  if (current) siteFilter.value = current;

  const siteId = (siteFilter.value || "").toString();
  const qs = siteId ? `&site_id=${encodeURIComponent(siteId)}` : "";
  const deltas = await _fetchJson(`/api/dashboard/keyword-deltas?limit=8${qs}`);
  renderDashboardKeywordDeltas(deltas);
  const errors = await _fetchJson(`/api/dashboard/recent-errors?limit=10`);
  renderDashboardRecentErrors(errors);
  await loadIpWidget();
  await loadSystemWidget();
}

async function initDashboardWidgets() {
  const siteFilter = document.getElementById("dashboard-site-filter");
  const hasDashboard = Boolean(document.getElementById("dashboard-deltas-body")) && Boolean(siteFilter);
  if (!hasDashboard) return;
  await loadDashboardWidgets();
  siteFilter.addEventListener("change", () => {
    localStorage.setItem("dashboard_site_id", String(siteFilter.value || ""));
    loadDashboardWidgets();
  });
  setInterval(() => loadDashboardWidgets(), 30000);
}

let _ipState = { local_ip: null, external_ip: null, local_method: null, external_method: null };
let _ipHistoryDetails = {};

async function loadIpWidget() {
  const localEl = document.getElementById("ip-local");
  const extEl = document.getElementById("ip-external");
  const changedEl = document.getElementById("ip-changed");
  if (!localEl || !extEl || !changedEl) return;
  try {
    const payload = await _fetchJson("/api/dashboard/ip");
    if (!payload?.ok) return;
    _ipState.local_ip = payload.local_ip || null;
    _ipState.external_ip = payload.external_ip || null;
    _ipState.local_method = payload.local_method || null;
    _ipState.external_method = payload.external_method || null;
    localEl.textContent = String(payload.local_ip || "—");
    extEl.textContent = String(payload.external_ip || "—");
    const ldt = (payload.last_local_change_at || "").toString().slice(0, 19).replace("T", " ");
    const edt = (payload.last_external_change_at || "").toString().slice(0, 19).replace("T", " ");
    changedEl.textContent = `Последнее изменение: локальный — ${ldt || "—"}, внешний — ${edt || "—"}`;
  } catch {
    localEl.textContent = "—";
    extEl.textContent = "—";
    changedEl.textContent = "—";
  }
}

async function loadSystemWidget() {
  const uptimeEl = document.getElementById("sys-uptime");
  const dbEl = document.getElementById("sys-db");
  const rtEl = document.getElementById("sys-runtime");
  const dbSizeEl = document.getElementById("sys-db-size");
  if (!uptimeEl || !dbEl || !rtEl || !dbSizeEl) return;
  try {
    const payload = await _fetchJson("/api/dashboard/system");
    if (!payload?.ok) return;
    const up = Number(payload.uptime_seconds ?? 0);
    uptimeEl.textContent = formatDuration(up);
    const db = payload.db || {};
    const sqlitePath = db.sqlite_path ? String(db.sqlite_path) : "";
    dbEl.textContent = sqlitePath ? sqlitePath.split("/").slice(-1)[0] : "—";
    const py = payload.python || {};
    const os = payload.os || {};
    rtEl.textContent = `${py.implementation || "Python"} ${py.version || ""} · ${os.system || ""} ${os.release || ""}`.trim();
    const sizeBytes = db.size_bytes === null || db.size_bytes === undefined ? null : Number(db.size_bytes);
    dbSizeEl.textContent = sizeBytes !== null && Number.isFinite(sizeBytes) ? formatBytes(sizeBytes) : "—";
  } catch {
    uptimeEl.textContent = "—";
    dbEl.textContent = "—";
    rtEl.textContent = "—";
    dbSizeEl.textContent = "—";
  }
}

function openSystemDetails() {
  const modal = document.getElementById("system-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  loadSystemDetails();
}

function closeSystemDetails() {
  const modal = document.getElementById("system-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

async function loadSystemDetails() {
  const sub = document.getElementById("system-modal-subtitle");
  const body = document.getElementById("system-modal-body");
  if (!body) return;
  body.innerHTML = '<div class="text-sm text-gray-500">Загрузка…</div>';
  try {
    const payload = await _fetchJson("/api/dashboard/system");
    if (!payload?.ok) return;
    const checked = (payload.checked_at || "").toString().slice(0, 19).replace("T", " ");
    if (sub) sub.textContent = checked ? `Проверено: ${checked}` : "";
    const py = payload.python || {};
    const os = payload.os || {};
    const db = payload.db || {};
    const up = Number(payload.uptime_seconds ?? 0);
    const sizeBytes = db.size_bytes === null || db.size_bytes === undefined ? null : Number(db.size_bytes);
    body.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Среда выполнения</div>
          <div class="text-sm"><span class="text-gray-500">Python:</span> ${escapeHtml(String(py.implementation || "Python"))} ${escapeHtml(String(py.version || ""))}</div>
          <div class="text-sm"><span class="text-gray-500">ОС:</span> ${escapeHtml(String(os.system || ""))} ${escapeHtml(String(os.release || ""))} ${escapeHtml(String(os.machine || ""))}</div>
          <div class="text-sm"><span class="text-gray-500">Аптайм:</span> ${escapeHtml(formatDuration(up))}</div>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div class="text-xs font-semibold text-gray-500 uppercase mb-2">База данных</div>
          <div class="text-sm"><span class="text-gray-500">URL:</span> <span class="break-all">${escapeHtml(String(db.url || ""))}</span></div>
          <div class="text-sm"><span class="text-gray-500">Файл:</span> <span class="break-all">${escapeHtml(String(db.sqlite_path || "—"))}</span></div>
          <div class="text-sm"><span class="text-gray-500">Размер:</span> ${escapeHtml(sizeBytes !== null && Number.isFinite(sizeBytes) ? formatBytes(sizeBytes) : "—")}</div>
        </div>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

function openIpDetails() {
  const modal = document.getElementById("ip-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  loadIpDetails();
}

function closeIpDetails() {
  const modal = document.getElementById("ip-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

async function loadIpDetails() {
  const sub = document.getElementById("ip-modal-subtitle");
  const lEl = document.getElementById("ip-modal-local");
  const eEl = document.getElementById("ip-modal-external");
  const lm = document.getElementById("ip-modal-local-meta");
  const em = document.getElementById("ip-modal-external-meta");
  const detail = document.getElementById("ip-modal-detail");
  if (!lEl || !eEl || !lm || !em || !detail) return;
  detail.textContent = "";
  try {
    const payload = await _fetchJson("/api/dashboard/ip");
    if (!payload?.ok) return;
    _ipState.local_ip = payload.local_ip || null;
    _ipState.external_ip = payload.external_ip || null;
    _ipState.local_method = payload.local_method || null;
    _ipState.external_method = payload.external_method || null;
    const checked = (payload.checked_at || "").toString().slice(0, 19).replace("T", " ");
    if (sub) sub.textContent = checked ? `Проверено: ${checked}` : "";
    lEl.textContent = String(payload.local_ip || "—");
    eEl.textContent = String(payload.external_ip || "—");
    const ldt = (payload.last_local_change_at || "").toString().slice(0, 19).replace("T", " ");
    const edt = (payload.last_external_change_at || "").toString().slice(0, 19).replace("T", " ");
    lm.textContent = `Метод: ${payload.local_method || "—"} · Последнее изменение: ${ldt || "—"}`;
    em.textContent = `Метод: ${payload.external_method || "—"} · Последнее изменение: ${edt || "—"}`;
    await loadIpHistory();
  } catch (e) {
    detail.textContent = String(e?.message ?? e);
  }
}

async function loadIpHistory() {
  const body = document.getElementById("ip-history-body");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="4" class="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>';
  try {
    const payload = await _fetchJson("/api/dashboard/ip-history?limit=50");
    const items = Array.isArray(payload?.items) ? payload.items : [];
    _ipHistoryDetails = {};
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="4" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
      return;
    }
    body.innerHTML = items
      .map((r) => {
        const dt = (r.created_at || "").toString().slice(0, 19).replace("T", " ");
        const local = r.local_ip || "—";
        const ext = r.external_ip || "—";
        const id = String(r.id);
        _ipHistoryDetails[id] = r.details || {};
        return `<tr>
          <td class="px-4 py-2 text-gray-600">${escapeHtml(dt || "—")}</td>
          <td class="px-4 py-2 font-medium">${escapeHtml(String(local))}</td>
          <td class="px-4 py-2 font-medium">${escapeHtml(String(ext))}</td>
          <td class="px-4 py-2">
            <button class="text-sm text-indigo-700 hover:underline" onclick="showIpRowDetails('${escapeHtml(id)}')">Показать</button>
          </td>
        </tr>`;
      })
      .join("");
  } catch (e) {
    body.innerHTML = `<tr><td colspan="4" class="px-4 py-6 text-center text-rose-700">${escapeHtml(String(e?.message ?? e))}</td></tr>`;
  }
}

function showIpRowDetails(id) {
  const detail = document.getElementById("ip-modal-detail");
  if (!detail) return;
  const raw = _ipHistoryDetails[String(id)] || {};
  const txt = escapeHtml(JSON.stringify(raw, null, 2));
  detail.innerHTML = `<div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
    <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Детали записи #${escapeHtml(String(id))}</div>
    <pre class="text-xs overflow-x-auto whitespace-pre-wrap break-words">${txt}</pre>
  </div>`;
}

async function copyIp(kind) {
  const resEl = document.getElementById("ip-copy-result");
  const ip = kind === "external" ? _ipState.external_ip : _ipState.local_ip;
  if (!ip) return;
  try {
    await navigator.clipboard.writeText(String(ip));
    if (resEl) resEl.textContent = `Скопировано: ${ip}`;
  } catch {
    if (resEl) resEl.textContent = `Скопируй вручную: ${ip}`;
  }
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Number(totalSeconds || 0));
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}д ${h}ч ${m}м`;
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м`;
}

function formatBytes(bytes) {
  const b = Number(bytes || 0);
  if (!Number.isFinite(b) || b <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = b;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  const n = i === 0 ? String(Math.round(v)) : v.toFixed(1);
  return `${n} ${units[i]}`;
}

async function loadTasksPage() {
  const body = document.getElementById("tasks-body");
  const statusEl = document.getElementById("tasks-status");
  const siteEl = document.getElementById("tasks-site");
  const prEl = document.getElementById("tasks-priority");
  const qEl = document.getElementById("tasks-q");
  const sortEl = document.getElementById("tasks-sort");
  const resEl = document.getElementById("tasks-result");
  if (!body || !statusEl || !siteEl) return;

  try {
    const sites = await _fetchJson("/api/sites/");
    const list = Array.isArray(sites) ? sites : [];
    if (!siteEl.dataset.loaded) {
      siteEl.innerHTML = ['<option value="">все сайты</option>']
        .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
        .join("");
      siteEl.dataset.loaded = "1";
    }

    const st = (statusEl.value || "").toString();
    const sid = (siteEl.value || "").toString();
    const pr = (prEl?.value || "").toString();
    let q = (qEl?.value || "").toString().trim();
    const autoOn = localStorage.getItem("tasks_auto_filter") === "1";
    if (autoOn) {
      const token = "Авто:";
      if (!q) q = token;
      else if (!q.includes(token)) q = `${token} ${q}`;
    }
    const sort = (sortEl?.value || "created_desc").toString();
    const qs = new URLSearchParams();
    if (st) qs.set("status", st);
    if (sid) qs.set("site_id", sid);
    if (pr) qs.set("priority", pr);
    if (q) qs.set("q", q);
    if (sort) qs.set("sort", sort);
    qs.set("limit", "200");
    const payload = await _fetchJson(`/api/tasks/?${qs.toString()}`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (resEl) resEl.textContent = `Найдено: ${items.length}`;

    body.innerHTML = items.length
      ? items
          .map((t) => {
            const dom = (t.site_domain || "").toString();
            const title = (t.title || "").toString();
            const created = (t.created_at || "").toString().slice(0, 19).replace("T", " ");
            const prVal = (t.priority || "normal").toString();
            const prBadge =
              prVal === "high"
                ? _badge("высокий", "bg-rose-100 text-rose-700")
                : prVal === "low"
                ? _badge("низкий", "bg-gray-200 text-gray-800")
                : _badge("обычный", "bg-indigo-100 text-indigo-700");
            const stBadge =
              t.status === "done"
                ? _badge("готово", "bg-emerald-100 text-emerald-700")
                : t.status === "in_progress"
                ? _badge("в работе", "bg-amber-100 text-amber-700")
                : _badge("в ожидании", "bg-gray-200 text-gray-800");
            const statusSel = escapeHtml(String(t.status || "todo"));
            const prSel = escapeHtml(String(prVal));
            const taskId = Number(t.id);
            const srcUrl = (t.source_url || "").toString();
            const src = srcUrl
              ? `<a class="text-sm text-indigo-700 hover:underline break-all" target="_blank" rel="noreferrer" href="${escapeHtml(
                  srcUrl
                )}">URL</a>`
              : '<span class="text-gray-400 text-sm">—</span>';
            return `<tr>
              <td class="px-6 py-4 text-sm text-gray-700">${escapeHtml(dom)}</td>
              <td class="px-6 py-4 font-medium break-all">
                <button class="text-indigo-700 hover:underline text-left" onclick="openTaskModal(${taskId})">${escapeHtml(
                  title
                )}</button>
              </td>
              <td class="px-6 py-4">${src}</td>
              <td class="px-6 py-4">${prBadge}</td>
              <td class="px-6 py-4">${stBadge}</td>
              <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(created || "—")}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <select class="rounded-md border-gray-300 text-sm p-2 border" onchange="updateTaskStatus(${taskId}, this.value)">
                    <option value="todo" ${statusSel === "todo" ? "selected" : ""}>в ожидании</option>
                    <option value="in_progress" ${statusSel === "in_progress" ? "selected" : ""}>в работе</option>
                    <option value="done" ${statusSel === "done" ? "selected" : ""}>готово</option>
                  </select>
                  <select class="rounded-md border-gray-300 text-sm p-2 border" onchange="updateTaskPriority(${taskId}, this.value)">
                    <option value="high" ${prSel === "high" ? "selected" : ""}>высокий</option>
                    <option value="normal" ${prSel === "normal" ? "selected" : ""}>обычный</option>
                    <option value="low" ${prSel === "low" ? "selected" : ""}>низкий</option>
                  </select>
                </div>
              </td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="7" class="px-6 py-10 text-center text-gray-400">Нет задач</td></tr>';
  } catch (e) {
    body.innerHTML = `<tr><td colspan="7" class="px-6 py-10 text-center text-rose-700">${escapeHtml(
      String(e?.message ?? e)
    )}</td></tr>`;
  }
}

function _renderAutoTasksFilterButton() {
  const btn = document.getElementById("tasks-auto-filter");
  if (!btn) return;
  const on = localStorage.getItem("tasks_auto_filter") === "1";
  btn.textContent = on ? "Авто-задачи: вкл" : "Авто-задачи: выкл";
  btn.className = on
    ? "bg-indigo-600 text-white px-3 py-2 rounded-md hover:bg-indigo-700 transition text-sm"
    : "bg-white border border-gray-300 text-gray-800 px-3 py-2 rounded-md hover:bg-gray-50 transition text-sm";
}

function toggleAutoTasksFilter() {
  const on = localStorage.getItem("tasks_auto_filter") === "1";
  localStorage.setItem("tasks_auto_filter", on ? "0" : "1");
  _renderAutoTasksFilterButton();
  loadTasksPage();
}

async function initTasksPage() {
  const body = document.getElementById("tasks-body");
  if (!body) return;
  _renderAutoTasksFilterButton();
  const statusEl = document.getElementById("tasks-status");
  const siteEl = document.getElementById("tasks-site");
  const prEl = document.getElementById("tasks-priority");
  const qEl = document.getElementById("tasks-q");
  const sortEl = document.getElementById("tasks-sort");
  if (statusEl) statusEl.addEventListener("change", () => loadTasksPage());
  if (siteEl) siteEl.addEventListener("change", () => loadTasksPage());
  if (prEl) prEl.addEventListener("change", () => loadTasksPage());
  if (sortEl) sortEl.addEventListener("change", () => loadTasksPage());
  if (qEl) qEl.addEventListener("keydown", (e) => (e.key === "Enter" ? loadTasksPage() : null));
  await loadTasksPage();
}

async function updateTaskStatus(taskId, status) {
  const id = Number(taskId);
  if (!id) return;
  await _fetchJson(`/api/tasks/${encodeURIComponent(String(id))}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ status: String(status || "") }),
  });
}

async function updateTaskPriority(taskId, priority) {
  const id = Number(taskId);
  if (!id) return;
  await _fetchJson(`/api/tasks/${encodeURIComponent(String(id))}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ priority: String(priority || "") }),
  });
}

let _taskModalState = { task_id: null, source_url: null, deep_audit_report_id: null };

async function openTaskModal(taskId) {
  const modal = document.getElementById("task-modal");
  const subtitle = document.getElementById("task-modal-subtitle");
  const titleEl = document.getElementById("task-modal-title");
  const siteEl = document.getElementById("task-modal-site");
  const descEl = document.getElementById("task-modal-desc");
  const urlEl = document.getElementById("task-modal-url");
  const badgesEl = document.getElementById("task-modal-badges");
  const auditEl = document.getElementById("task-modal-audit");
  const openAuditBtn = document.getElementById("task-modal-open-audit");
  if (!modal || !titleEl || !siteEl || !descEl || !urlEl || !badgesEl || !auditEl) return;

  modal.classList.remove("hidden");
  titleEl.textContent = "Загрузка…";
  siteEl.textContent = "—";
  descEl.textContent = "—";
  badgesEl.innerHTML = "";
  auditEl.innerHTML = '<div class="text-sm text-gray-500">Нажми “Открыть последний SEO-отчёт”.</div>';
  if (subtitle) subtitle.textContent = "";
  if (openAuditBtn) openAuditBtn.disabled = false;

  try {
    const t = await _fetchJson(`/api/tasks/${encodeURIComponent(String(Number(taskId)))}`);
    _taskModalState = {
      task_id: Number(t?.id || taskId),
      source_url: t?.source_url ? String(t.source_url) : null,
      deep_audit_report_id: t?.deep_audit_report_id ? Number(t.deep_audit_report_id) : null,
    };
    titleEl.textContent = String(t?.title || "—");
    siteEl.textContent = String(t?.site_domain || "—");
    descEl.textContent = String(t?.description || "—");
    const created = String(t?.created_at || "").slice(0, 19).replace("T", " ");
    if (subtitle) subtitle.textContent = created ? `Создано: ${created}` : "";

    const st = String(t?.status || "todo");
    const pr = String(t?.priority || "normal");
    const stBadge = st === "done" ? _badge("готово", "bg-emerald-100 text-emerald-700") : st === "in_progress" ? _badge("в работе", "bg-amber-100 text-amber-700") : _badge("в ожидании", "bg-gray-200 text-gray-800");
    const prBadge = pr === "high" ? _badge("высокий", "bg-rose-100 text-rose-700") : pr === "low" ? _badge("низкий", "bg-gray-200 text-gray-800") : _badge("обычный", "bg-indigo-100 text-indigo-700");
    badgesEl.innerHTML = `${prBadge}${stBadge}`;

    if (_taskModalState.source_url) {
      urlEl.href = _taskModalState.source_url;
      urlEl.classList.remove("pointer-events-none");
      urlEl.classList.remove("text-gray-400");
    } else {
      urlEl.href = "#";
      urlEl.classList.add("pointer-events-none");
      urlEl.classList.add("text-gray-400");
    }
  } catch (e) {
    titleEl.textContent = "Ошибка загрузки";
    descEl.textContent = String(e?.message ?? e);
  }
}

function closeTaskModal() {
  const modal = document.getElementById("task-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

async function openTaskAudit() {
  const auditEl = document.getElementById("task-modal-audit");
  if (!auditEl) return;
  auditEl.innerHTML = '<div class="text-sm text-gray-500">Загрузка отчёта…</div>';
  try {
    let payload;
    if (_taskModalState.deep_audit_report_id) {
      payload = await _fetchJson(`/api/seo/deep-audit/report/${encodeURIComponent(String(_taskModalState.deep_audit_report_id))}`);
    } else if (_taskModalState.source_url) {
      payload = await _fetchJson(`/api/seo/deep-audit/latest?url=${encodeURIComponent(String(_taskModalState.source_url))}`);
    } else {
      auditEl.innerHTML = '<div class="text-sm text-gray-500">У задачи нет URL.</div>';
      return;
    }
    const result = payload?.result || null;
    if (!result) {
      auditEl.innerHTML = '<div class="text-sm text-gray-500">Отчёт не найден.</div>';
      return;
    }
    renderDeepAuditInto(result, "task-modal-audit", "task-modal");
  } catch (e) {
    auditEl.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

function renderDeepAuditInto(result, targetId, prefix) {
  const el = document.getElementById(String(targetId || ""));
  if (!el) return;
  if (!result) {
    el.textContent = "Нет результата";
    return;
  }
  const status = result.status_code ?? "Ошибка";
  const finalUrl = result.final_url ?? result.url ?? "—";
  const spamScore = Number(result.spam_score ?? 0);
  const spamBadge =
    spamScore >= 60
      ? _badge(`СПАМ ${spamScore}`, "bg-rose-100 text-rose-700")
      : spamScore >= 30
      ? _badge(`СПАМ ${spamScore}`, "bg-amber-100 text-amber-700")
      : _badge(`СПАМ ${spamScore}`, "bg-emerald-100 text-emerald-700");
  const idx =
    result.is_indexed === null || result.is_indexed === undefined ? "Неизвестно" : result.is_indexed ? "Да" : "Нет";
  const indexable =
    result.indexable === null || result.indexable === undefined ? "Неизвестно" : result.indexable ? "Да" : "Нет";

  const diffId = `${prefix}-diff`;
  const histId = `${prefix}-history`;
  const urlArg = escapeHtml(JSON.stringify(String(finalUrl)));

  el.innerHTML = `<div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
    <div class="flex items-center justify-between">
      <div class="text-xs font-semibold text-gray-400 uppercase">Отчёт</div>
      ${spamBadge}
    </div>
    <div class="flex justify-between"><span class="text-gray-500">URL:</span><span class="font-medium break-all">${escapeHtml(String(finalUrl))}</span></div>
    <div class="flex justify-between"><span class="text-gray-500">HTTP:</span><span class="font-medium">${escapeHtml(String(status))}</span></div>
    <div class="flex justify-between"><span class="text-gray-500">Indexable:</span><span class="font-medium">${escapeHtml(String(indexable))}</span></div>
    <div class="flex justify-between"><span class="text-gray-500">В индексе:</span><span class="font-medium">${escapeHtml(String(idx))}</span></div>
    <div class="pt-2 border-t">
      <div class="flex flex-wrap items-center gap-3">
        <div class="text-xs font-semibold text-gray-500 uppercase">Сравнение</div>
        <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadDeepAuditDiffInto(${urlArg}, '${diffId}', '${histId}')">Сравнить с прошлым</button>
        <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadDeepAuditHistoryInto(${urlArg}, '${histId}', '${diffId}')">История</button>
      </div>
      <div id="${diffId}" class="mt-3"></div>
      <div id="${histId}" class="mt-3"></div>
    </div>
  </div>`;
}

async function loadDeepAuditHistoryInto(url, targetId, clearId) {
  const el = document.getElementById(String(targetId || ""));
  const clearEl = document.getElementById(String(clearId || ""));
  if (clearEl) clearEl.innerHTML = "";
  if (!el) return;
  const u = (url || "").toString().trim();
  if (!u) return;
  el.innerHTML = '<div class="text-sm text-gray-500">Загрузка истории…</div>';
  try {
    const payload = await _fetchJson(`/api/seo/deep-audit/history?url=${encodeURIComponent(u)}&limit=10`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    el.innerHTML = items.length
      ? `<div class="overflow-x-auto border rounded-lg bg-white">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 text-xs font-semibold uppercase text-gray-400">
              <tr>
                <th class="px-4 py-2">Дата</th>
                <th class="px-4 py-2">HTTP</th>
                <th class="px-4 py-2">Indexable</th>
                <th class="px-4 py-2">В индексе</th>
                <th class="px-4 py-2">СПАМ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              ${items
                .map((r) => {
                  const dt = (r.created_at || "").toString().slice(0, 19).replace("T", " ");
                  const sc = r.status_code ?? "—";
                  const idx = r.is_indexed === null || r.is_indexed === undefined ? "—" : r.is_indexed ? "Да" : "Нет";
                  const ix = r.indexable === null || r.indexable === undefined ? "—" : r.indexable ? "Да" : "Нет";
                  const sp = r.spam_score ?? 0;
                  return `<tr>
                    <td class="px-4 py-2 text-gray-600">${escapeHtml(dt || "—")}</td>
                    <td class="px-4 py-2 font-medium">${escapeHtml(String(sc))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(ix))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(idx))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(sp))}</td>
                  </tr>`;
                })
                .join("")}
            </tbody>
          </table>
        </div>`
      : '<div class="text-sm text-gray-500">Истории пока нет.</div>';
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

async function loadDeepAuditDiffInto(url, targetId, clearId) {
  const el = document.getElementById(String(targetId || ""));
  const clearEl = document.getElementById(String(clearId || ""));
  if (clearEl) clearEl.innerHTML = "";
  if (!el) return;
  const u = (url || "").toString().trim();
  if (!u) return;
  el.innerHTML = '<div class="text-sm text-gray-500">Загрузка сравнения…</div>';
  try {
    const payload = await _fetchJson(`/api/seo/deep-audit/diff?url=${encodeURIComponent(u)}`);
    const diff = payload?.diff || {};
    const keys = Object.keys(diff);
    if (!keys.length) {
      el.innerHTML = '<div class="text-sm text-gray-500">Недостаточно данных для сравнения (нужно 2 проверки).</div>';
      return;
    }
    el.innerHTML = `<div class="bg-white border rounded-lg p-4 space-y-2">
      <div class="text-xs font-semibold text-gray-500 uppercase">Изменения</div>
      <div class="space-y-1">
        ${keys
          .map((k) => {
            const d = diff[k] || {};
            const from = d.from === null || d.from === undefined ? "—" : String(d.from);
            const to = d.to === null || d.to === undefined ? "—" : String(d.to);
            const delta = d.delta === undefined ? "" : ` (Δ ${escapeHtml(String(d.delta))})`;
            return `<div class="flex justify-between gap-4">
              <div class="text-gray-600">${escapeHtml(String(k))}</div>
              <div class="font-medium text-right break-all">${escapeHtml(from)} → ${escapeHtml(to)}${delta}</div>
            </div>`;
          })
          .join("")}
      </div>
    </div>`;
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

async function createContentIdea() {
  const resEl = document.getElementById("content-create-result");
  const siteEl = document.getElementById("content-create-site");
  const titleEl = document.getElementById("content-create-title");
  const urlEl = document.getElementById("content-create-url");
  if (!siteEl || !titleEl) return;
  const siteId = Number(siteEl.value || "");
  const title = (titleEl.value || "").toString().trim();
  const url = (urlEl?.value || "").toString().trim();
  if (!siteId || !title) {
    if (resEl) resEl.textContent = "Укажи сайт и заголовок.";
    return;
  }
  try {
    await _fetchJson("/api/content-plans/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ site_id: siteId, title, url: url || null, status: "idea" }),
    });
    if (resEl) resEl.textContent = "Добавлено.";
    titleEl.value = "";
    if (urlEl) urlEl.value = "";
    await loadContentPlansPage();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function loadContentPlansPage() {
  const body = document.getElementById("content-body");
  const statusEl = document.getElementById("content-status");
  const siteEl = document.getElementById("content-site");
  const siteCreateEl = document.getElementById("content-create-site");
  const resEl = document.getElementById("content-result");
  if (!body || !statusEl || !siteEl) return;
  try {
    const sites = await _fetchJson("/api/sites/");
    const list = Array.isArray(sites) ? sites : [];
    if (!siteEl.dataset.loaded) {
      siteEl.innerHTML = ['<option value="">все сайты</option>']
        .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
        .join("");
      siteEl.dataset.loaded = "1";
    }
    if (siteCreateEl && !siteCreateEl.dataset.loaded) {
      siteCreateEl.innerHTML = list
        .map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`)
        .join("");
      siteCreateEl.dataset.loaded = "1";
    }

    const st = (statusEl.value || "").toString();
    const sid = (siteEl.value || "").toString();
    const qs = new URLSearchParams();
    if (st) qs.set("status", st);
    if (sid) qs.set("site_id", sid);
    qs.set("limit", "200");
    const payload = await _fetchJson(`/api/content-plans/?${qs.toString()}`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (resEl) resEl.textContent = `Найдено: ${items.length}`;
    body.innerHTML = items.length
      ? items
          .map((r) => {
            const dom = (r.site_domain || "").toString();
            const title = (r.title || "").toString();
            const url = (r.url || "").toString();
            const created = (r.created_at || "").toString().slice(0, 19).replace("T", " ");
            const stBadge =
              r.status === "published"
                ? _badge("published", "bg-emerald-100 text-emerald-700")
                : r.status === "writing"
                ? _badge("writing", "bg-amber-100 text-amber-700")
                : _badge("idea", "bg-gray-200 text-gray-800");
            return `<tr>
              <td class="px-6 py-4 text-sm text-gray-700">${escapeHtml(dom)}</td>
              <td class="px-6 py-4">
                <div class="font-medium break-all">${escapeHtml(title)}</div>
                ${url ? `<div class="text-xs text-gray-500 break-all mt-1">${escapeHtml(url)}</div>` : ""}
              </td>
              <td class="px-6 py-4">${stBadge}</td>
              <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(created || "—")}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="4" class="px-6 py-10 text-center text-gray-400">Нет данных</td></tr>';
  } catch (e) {
    body.innerHTML = `<tr><td colspan="4" class="px-6 py-10 text-center text-rose-700">${escapeHtml(
      String(e?.message ?? e)
    )}</td></tr>`;
  }
}

async function initContentPlansPage() {
  const body = document.getElementById("content-body");
  if (!body) return;
  const statusEl = document.getElementById("content-status");
  const siteEl = document.getElementById("content-site");
  if (statusEl) statusEl.addEventListener("change", () => loadContentPlansPage());
  if (siteEl) siteEl.addEventListener("change", () => loadContentPlansPage());
  await loadContentPlansPage();
}


function renderSites(sites) {
  const tbody = document.getElementById("sites-body");
  if (!tbody) return;
  const list = Array.isArray(sites) ? sites : [];
  const selectedId = Number(localStorage.getItem("selected_site_id") ?? "");
  if (list.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="px-6 py-10 text-center text-gray-400">Сайтов пока нет.</td></tr>';
    return;
  }

  tbody.innerHTML = list
    .map((s) => {
      const id = s.id;
      const domain = s.domain ?? "";
      const cms = s.cms ?? "-";
      const region = s.region ?? "-";
      const isSelected = selectedId && Number(id) === selectedId;
      const domainArg = escapeHtml(JSON.stringify(domain));
      return `
        <tr class="${isSelected ? "bg-indigo-50" : ""}">
          <td class="px-6 py-4 font-medium">
            <button class="text-indigo-700 hover:underline" onclick="selectSite(${Number(id)}, ${domainArg})">
              ${escapeHtml(domain)}
            </button>
          </td>
          <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(cms)}</td>
          <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(region)}</td>
          <td class="px-6 py-4">
            <div class="flex gap-3 items-center">
              <button class="text-indigo-700 hover:underline text-sm" onclick="runSiteScan(${Number(
                id
              )})">Скан</button>
              <button class="text-indigo-700 hover:underline text-sm" onclick="runTechAudit(${Number(
                id
              )})">Полный аудит</button>
              <button class="text-gray-700 hover:underline text-sm" onclick="checkRobots(${Number(
                id
              )})">Проверить robots.txt</button>
              <button class="text-gray-700 hover:underline text-sm" onclick="checkSitemap(${Number(
                id
              )})">Проверить sitemap</button>
              <button class="text-gray-600 hover:underline text-sm" onclick="loadScanHistory(${Number(
                id
              )}, ${domainArg})">История</button>
              <button class="text-gray-600 hover:underline text-sm" onclick="openSiteSettings(${Number(
                id
              )}, ${domainArg})">Настроить</button>
            </div>
          </td>
          <td class="px-6 py-4 text-right">
            <button class="text-red-600 hover:underline text-sm" onclick="deleteSite(${Number(
              id
            )})">Удалить</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function selectSite(siteId, domain) {
  const panel = document.getElementById("scan-history-panel");
  if (panel) {
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    await loadScanHistory(siteId, domain);
    return;
  }
  setSelectedSite(siteId, domain);
  await loadSites();
}

function openAlertsModal() {
  const modal = document.getElementById("site-alerts-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
}

function closeAlertsModal() {
  const modal = document.getElementById("site-alerts-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

function _applyAlertsUaUi() {
  const choiceEl = document.getElementById("alerts-ua-choice");
  const customEl = document.getElementById("alerts-custom-ua");
  if (!choiceEl || !customEl) return;
  const c = (choiceEl.value || "").toString().trim().toLowerCase();
  const isCustom = c === "custom";
  customEl.disabled = !isCustom;
  if (!isCustom) customEl.value = "";
}

function initAlertsModalControls() {
  const choiceEl = document.getElementById("alerts-ua-choice");
  const customEl = document.getElementById("alerts-custom-ua");
  if (!choiceEl || !customEl) return;
  choiceEl.addEventListener("change", _applyAlertsUaUi);
  _applyAlertsUaUi();
}

async function configureAlerts(siteId, domain) {
  localStorage.setItem("selected_site_id", String(siteId));
  localStorage.setItem("selected_site_domain", String(domain || ""));
  const resEl = document.getElementById("alerts-result");
  openAlertsModal();
  if (resEl) resEl.textContent = `Загрузка настроек для ${domain || ""}…`;
  try {
    const site = await _fetchJson(`/api/sites/${encodeURIComponent(String(siteId))}`);
    const enabled = Boolean(site?.email_alerts_enabled);
    const email = (site?.alert_email || "").toString();
    const emailEl = document.getElementById("alerts-email");
    const enabledEl = document.getElementById("alerts-enabled");
    const uaChoiceEl = document.getElementById("alerts-ua-choice");
    const customUaEl = document.getElementById("alerts-custom-ua");
    const priorityEl = document.getElementById("alerts-scan-priority");
    const pauseEl = document.getElementById("alerts-scan-pause-ms");
    const robotsEl = document.getElementById("alerts-respect-robots");
    const sitemapEl = document.getElementById("alerts-use-sitemap");
    const ahrefsEnabledEl = document.getElementById("alerts-ahrefs-enabled");
    const ahrefsKeyEl = document.getElementById("alerts-ahrefs-key");
    if (emailEl) emailEl.value = email;
    if (enabledEl) enabledEl.value = enabled ? "true" : "false";
    if (uaChoiceEl) uaChoiceEl.value = (site?.user_agent_choice || "").toString();
    if (customUaEl) customUaEl.value = (site?.custom_user_agent || "").toString();
    if (priorityEl) priorityEl.value = (site?.scan_priority || "normal").toString();
    if (pauseEl) pauseEl.value = String(Number(site?.scan_pause_ms ?? 300));
    if (robotsEl) robotsEl.value = site?.respect_robots_txt === false ? "false" : "true";
    if (sitemapEl) sitemapEl.value = site?.use_sitemap === false ? "false" : "true";
    if (ahrefsEnabledEl) ahrefsEnabledEl.value = "false";
    if (ahrefsKeyEl) ahrefsKeyEl.value = "";
    try {
      const payload = await _fetchJson(`/api/integrations/${encodeURIComponent(String(siteId))}/ahrefs`);
      const ah = payload?.ahrefs || {};
      if (ahrefsEnabledEl) ahrefsEnabledEl.value = ah?.enabled ? "true" : "false";
    } catch {}
    _applyAlertsUaUi();
    if (resEl) resEl.textContent = `Настройки для ${domain || site?.domain || ""}`;
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

function openSiteSettings(siteId, domain) {
  return configureAlerts(siteId, domain);
}

async function saveSiteAlerts() {
  const siteId = Number(localStorage.getItem("selected_site_id") || "");
  const resEl = document.getElementById("alerts-result");
  if (!siteId) {
    if (resEl) resEl.textContent = "Сначала выберите сайт (кнопка «Настроить» в таблице).";
    return;
  }
  const emailEl = document.getElementById("alerts-email");
  const enabledEl = document.getElementById("alerts-enabled");
  const alert_email = (emailEl?.value || "").toString();
  const uaChoiceEl = document.getElementById("alerts-ua-choice");
  const customUaEl = document.getElementById("alerts-custom-ua");
  const priorityEl = document.getElementById("alerts-scan-priority");
  const pauseEl = document.getElementById("alerts-scan-pause-ms");
  const robotsEl = document.getElementById("alerts-respect-robots");
  const sitemapEl = document.getElementById("alerts-use-sitemap");
  const ahrefsEnabledEl = document.getElementById("alerts-ahrefs-enabled");
  const ahrefsKeyEl = document.getElementById("alerts-ahrefs-key");
  const email_alerts_enabled = (enabledEl?.value || "false").toString() === "true";
  const user_agent_choice = (uaChoiceEl?.value || "").toString() || null;
  const custom_user_agent = (customUaEl?.value || "").toString() || null;
  const scan_priority = (priorityEl?.value || "normal").toString();
  const scan_pause_ms = Math.max(0, Math.min(10000, Number(pauseEl?.value || 0) || 0));
  const respect_robots_txt = (robotsEl?.value || "true").toString() === "true";
  const use_sitemap = (sitemapEl?.value || "true").toString() === "true";
  const ahrefs_enabled = (ahrefsEnabledEl?.value || "false").toString() === "true";
  const ahrefs_key = (ahrefsKeyEl?.value || "").toString();
  try {
    await _fetchJson(`/api/sites/${encodeURIComponent(String(siteId))}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        alert_email,
        email_alerts_enabled,
        user_agent_choice,
        custom_user_agent,
        scan_priority,
        scan_pause_ms,
        respect_robots_txt,
        use_sitemap,
      }),
    });
    const ahrefsBody = { enabled: ahrefs_enabled };
    if (ahrefs_key.trim()) ahrefsBody.api_key = ahrefs_key.trim();
    await _fetchJson(`/api/integrations/${encodeURIComponent(String(siteId))}/ahrefs-save`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(ahrefsBody),
    });
    if (resEl) resEl.textContent = "Сохранено.";
    setTimeout(() => closeAlertsModal(), 400);
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}


function renderAudit(result) {
  const el = document.getElementById("audit-result");
  if (!el) return;
  if (!result) {
    el.textContent = "Нет результата";
    return;
  }
  const status = result.status_code ?? "Ошибка";
  const title = result.title ?? "—";
  const h1 = result.h1 ?? "—";
  const indexed =
    result.is_indexed === null || result.is_indexed === undefined
      ? "Неизвестно"
      : result.is_indexed
      ? "Да"
      : "Нет";
  const aiUsed = Boolean(result.ai_used);
  const aiModel = result.ai_model ? String(result.ai_model) : "";
  const aiSummary = result.ai_summary ? String(result.ai_summary) : "";
  const aiActions = Array.isArray(result.ai_actions) ? result.ai_actions : [];
  const suggestPanelId = "audit-suggest-panel";
  const titleArg = escapeHtml(JSON.stringify(String(result.title || "")));
  const h1Arg = escapeHtml(JSON.stringify(String(result.h1 || "")));
  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
      <div class="flex items-center justify-between">
        <div class="text-xs font-semibold text-gray-400 uppercase">Результат</div>
        <div>${aiUsed ? _badge(`AI: ${escapeHtml(aiModel || "on")}`, "bg-indigo-100 text-indigo-700") : _badge("AI: off", "bg-gray-200 text-gray-800")}</div>
      </div>
      <div class="flex justify-between"><span class="text-gray-500">Статус:</span><span class="font-semibold">${escapeHtml(
        String(status)
      )}</span></div>
      <div><div class="text-gray-500">Title:</div><div class="font-medium break-all">${escapeHtml(
        String(title)
      )}</div></div>
      <div><div class="text-gray-500">H1:</div><div class="font-medium break-all">${escapeHtml(
        String(h1)
      )}</div></div>
      <div class="flex justify-between"><span class="text-gray-500">В индексе:</span><span class="font-medium">${escapeHtml(
        String(indexed)
      )}</span></div>
      <div class="pt-2 border-t">
        <div class="flex flex-wrap items-center gap-3">
          <div class="text-xs font-semibold text-gray-400 uppercase">Подсказки</div>
          <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadInlineKeywordSuggestions(${titleArg}, '${suggestPanelId}', true)">по Title</button>
          <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadInlineKeywordSuggestions(${h1Arg}, '${suggestPanelId}', true)">по H1</button>
        </div>
        <div id="${suggestPanelId}" class="mt-3"></div>
      </div>
      ${
        aiSummary
          ? `<div class="pt-2">
              <div class="text-gray-500">Пояснение:</div>
              <div class="text-sm text-gray-700 mt-1">${escapeHtml(aiSummary)}</div>
              ${
                aiActions.length
                  ? `<div class="text-gray-500 mt-2">Что сделать:</div>
                     <ul class="list-disc pl-5 text-sm text-gray-700 mt-1 space-y-1">
                       ${aiActions
                         .slice(0, 7)
                         .map((a) => `<li>${escapeHtml(String(a))}</li>`)
                         .join("")}
                     </ul>`
                  : ""
              }
            </div>`
          : ""
      }
    </div>
  `;
}

async function loadInlineKeywordSuggestions(query, targetId, expanded) {
  const el = document.getElementById(String(targetId || ""));
  if (!el) return;
  const q = (query || "").toString().trim();
  if (!q || q === "—") {
    el.innerHTML = '<div class="text-sm text-gray-400">Нет текста для подсказок.</div>';
    return;
  }
  el.innerHTML = '<div class="text-sm text-gray-500">Загрузка…</div>';
  const mode = expanded ? "expanded" : "basic";
  try {
    const payload = await _fetchJson(
      `/api/keywords/suggest?query=${encodeURIComponent(q)}&engines=google,yandex,bing,ddg&lang=ru&mode=${encodeURIComponent(
        mode
      )}&max_variants=20&max_per_engine=20`
    );
    const items = payload?.items || {};
    const engines = [
      { key: "google", title: "Google" },
      { key: "yandex", title: "Яндекс" },
      { key: "bing", title: "Bing" },
      { key: "ddg", title: "DuckDuckGo" },
    ];
    el.innerHTML = `<div class="space-y-3">${engines
      .map((e) => {
        const list = Array.isArray(items?.[e.key]) ? items[e.key] : [];
        return `<div>
          <div class="text-xs font-semibold text-gray-500 uppercase mb-2">${escapeHtml(e.title)}</div>
          ${
            list.length
              ? `<div class="flex flex-wrap gap-2">${list
                  .slice(0, 12)
                  .map((s) => {
                    const arg = escapeHtml(JSON.stringify(String(s)));
                    return `<button type="button" class="px-3 py-1 rounded-full bg-white border border-gray-200 text-sm hover:bg-gray-50" onclick="setKeywordFromSuggestion(${arg})">${escapeHtml(
                      String(s)
                    )}</button>`;
                  })
                  .join("")}</div>`
              : '<div class="text-sm text-gray-400">Нет</div>'
          }
        </div>`;
      })
      .join("")}</div>`;
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

function renderDeepAudit(result) {
  const el = document.getElementById("deep-audit-result");
  if (!el) return;
  if (!result) {
    el.textContent = "Нет результата";
    return;
  }
  const status = result.status_code ?? "Ошибка";
  const rt = result.response_time_ms ?? "—";
  const finalUrl = result.final_url ?? result.url ?? "—";
  const title = result.title ?? "—";
  const md = result.meta_description ?? "—";
  const canon = result.canonical ?? "—";
  const robots = result.robots_meta ?? "—";
  const xrt = result.x_robots_tag ?? "—";
  const idx =
    result.is_indexed === null || result.is_indexed === undefined ? "Неизвестно" : result.is_indexed ? "Да" : "Нет";
  const indexable =
    result.indexable === null || result.indexable === undefined ? "Неизвестно" : result.indexable ? "Да" : "Нет";
  const reasons = Array.isArray(result.indexability_reasons) ? result.indexability_reasons : [];
  const aiUsed = Boolean(result.ai_used);
  const aiModel = result.ai_model ? String(result.ai_model) : "";
  const aiSummary = result.ai_summary ? String(result.ai_summary) : "";
  const aiActions = Array.isArray(result.ai_actions) ? result.ai_actions : [];
  const sug = result.keyword_suggestions || {};
  const tk = result.target_keyword ? String(result.target_keyword) : "";
  const tks = result.target_keyword_stats || null;
  const spamScore = Number(result.spam_score ?? 0);
  const spamFlags = Array.isArray(result.spam_flags) ? result.spam_flags : [];
  const spamBadge =
    spamScore >= 60
      ? _badge(`СПАМ ${spamScore}`, "bg-rose-100 text-rose-700")
      : spamScore >= 30
      ? _badge(`СПАМ ${spamScore}`, "bg-amber-100 text-amber-700")
      : _badge(`СПАМ ${spamScore}`, "bg-emerald-100 text-emerald-700");
  const historyUrl = result.final_url ?? result.url ?? "";

  const renderSug = (block, titleText) => {
    const items = block?.items || {};
    const engines = [
      { key: "google", title: "Google" },
      { key: "yandex", title: "Яндекс" },
      { key: "bing", title: "Bing" },
      { key: "ddg", title: "DuckDuckGo" },
    ];
    return `<div class="pt-3">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">${escapeHtml(titleText)}</div>
      <div class="space-y-2">
        ${engines
          .map((e) => {
            const list = Array.isArray(items?.[e.key]) ? items[e.key] : [];
            return `<div>
              <div class="text-xs text-gray-400 mb-1">${escapeHtml(e.title)}</div>
              ${
                list.length
                  ? `<div class="flex flex-wrap gap-2">${list
                      .slice(0, 14)
                      .map((s) => {
                        const arg = escapeHtml(JSON.stringify(String(s)));
                        return `<button type="button" class="px-3 py-1 rounded-full bg-white border border-gray-200 text-sm hover:bg-gray-50" onclick="setKeywordFromSuggestion(${arg})">${escapeHtml(
                          String(s)
                        )}</button>`;
                      })
                      .join("")}</div>`
                  : '<div class="text-sm text-gray-400">Нет</div>'
              }
            </div>`;
          })
          .join("")}
      </div>
    </div>`;
  };

  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-3">
      <div class="flex items-center justify-between">
        <div class="text-xs font-semibold text-gray-400 uppercase">Результат</div>
        <div class="flex items-center gap-2">
          ${spamBadge}
          ${aiUsed ? _badge(`ИИ: ${escapeHtml(aiModel || "вкл")}`, "bg-indigo-100 text-indigo-700") : _badge("ИИ: выкл", "bg-gray-200 text-gray-800")}
        </div>
      </div>
      <div class="flex justify-between"><span class="text-gray-500">Статус:</span><span class="font-semibold">${escapeHtml(String(status))}</span></div>
      <div class="flex justify-between"><span class="text-gray-500">Время ответа:</span><span class="font-semibold">${escapeHtml(String(rt))} ms</span></div>
      <div><div class="text-gray-500">Итоговый URL:</div><div class="font-medium break-all">${escapeHtml(String(finalUrl))}</div></div>
      <div><div class="text-gray-500">Title:</div><div class="font-medium break-all">${escapeHtml(String(title))}</div></div>
      <div><div class="text-gray-500">Meta description:</div><div class="text-sm text-gray-700 break-all">${escapeHtml(String(md))}</div></div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t">
        <div><div class="text-gray-500">Canonical:</div><div class="text-sm break-all">${escapeHtml(String(canon))}</div></div>
        <div><div class="text-gray-500">Robots:</div><div class="text-sm break-all">${escapeHtml(String(robots))}</div></div>
        <div><div class="text-gray-500">X-Robots-Tag:</div><div class="text-sm break-all">${escapeHtml(String(xrt))}</div></div>
        <div class="space-y-1">
          <div class="flex justify-between"><span class="text-gray-500">Индексируемая:</span><span class="font-medium">${escapeHtml(String(indexable))}</span></div>
          <div class="flex justify-between"><span class="text-gray-500">В индексе:</span><span class="font-medium">${escapeHtml(String(idx))}</span></div>
          ${reasons.length ? `<div class="text-xs text-gray-500">Причины: ${escapeHtml(reasons.join("; "))}</div>` : ""}
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t">
        <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Слова</div><div class="font-semibold">${escapeHtml(String(result.word_count ?? "—"))}</div></div>
        <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Внутр. ссылки</div><div class="font-semibold">${escapeHtml(String(result.links_internal ?? "—"))}</div></div>
        <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Внешн. ссылки</div><div class="font-semibold">${escapeHtml(String(result.links_external ?? "—"))}</div></div>
        <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Картинки без alt</div><div class="font-semibold">${escapeHtml(String(result.images_missing_alt ?? "—"))}</div></div>
      </div>
      <div class="pt-2 border-t">
        <div class="flex flex-wrap items-center gap-3">
          <div class="text-xs font-semibold text-gray-500 uppercase">История</div>
          <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadDeepAuditDiff(${escapeHtml(
            JSON.stringify(String(historyUrl))
          )})">Сравнить с прошлым</button>
          <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="loadDeepAuditHistory(${escapeHtml(
            JSON.stringify(String(historyUrl))
          )})">Показать историю</button>
          <button type="button" class="text-sm text-indigo-700 hover:underline" onclick="createTasksFromDeepAudit(${escapeHtml(
            JSON.stringify(String(historyUrl))
          )})">Создать задачи</button>
        </div>
        <div id="deep-audit-diff" class="mt-3"></div>
        <div id="deep-audit-history" class="mt-3"></div>
      </div>
      <div class="pt-2 border-t">
        <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Антиспам</div>
        ${
          spamFlags.length
            ? `<ul class="list-disc pl-5 text-sm text-gray-700 space-y-1">
                ${spamFlags.slice(0, 12).map((x) => `<li>${escapeHtml(String(x))}</li>`).join("")}
              </ul>`
            : '<div class="text-sm text-gray-500">Явных признаков спама не найдено.</div>'
        }
      </div>
      ${
        tk && tks
          ? `<div class="pt-2 border-t">
              <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Целевой ключ</div>
              <div class="text-sm text-gray-700">${escapeHtml(tk)}</div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Плотность</div><div class="font-semibold">${escapeHtml(
                  String(tks.density_pct ?? "—")
                )}%</div></div>
                <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">Повторов фразы</div><div class="font-semibold">${escapeHtml(
                  String(tks.phrase_repeats ?? "—")
                )}</div></div>
                <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">В title</div><div class="font-semibold">${escapeHtml(
                  String(tks.title_count ?? "—")
                )}</div></div>
                <div class="p-3 bg-white border rounded-lg"><div class="text-xs text-gray-400">В h1</div><div class="font-semibold">${escapeHtml(
                  String(tks.h1_count ?? "—")
                )}</div></div>
              </div>
              ${
                Array.isArray(tks.spam_flags) && tks.spam_flags.length
                  ? `<ul class="list-disc pl-5 text-sm text-gray-700 mt-3 space-y-1">
                      ${tks.spam_flags.slice(0, 8).map((x) => `<li>${escapeHtml(String(x))}</li>`).join("")}
                    </ul>`
                  : '<div class="text-sm text-gray-500 mt-3">Явного спама по целевому ключу не найдено.</div>'
              }
            </div>`
          : ""
      }
      ${
        aiSummary
          ? `<div class="pt-2 border-t">
              <div class="text-gray-500">Пояснение:</div>
              <div class="text-sm text-gray-700 mt-1">${escapeHtml(aiSummary)}</div>
              ${
                aiActions.length
                  ? `<div class="text-gray-500 mt-2">Что сделать:</div>
                     <ul class="list-disc pl-5 text-sm text-gray-700 mt-1 space-y-1">
                       ${aiActions
                         .slice(0, 10)
                         .map((a) => `<li>${escapeHtml(String(a))}</li>`)
                         .join("")}
                     </ul>`
                  : ""
              }
            </div>`
          : ""
      }
      ${(sug?.title ? renderSug(sug.title, "Подсказки по Title") : "") + (sug?.h1 ? renderSug(sug.h1, "Подсказки по H1") : "")}
    </div>
  `;
}

async function loadDeepAuditHistory(url) {
  const el = document.getElementById("deep-audit-history");
  const diffEl = document.getElementById("deep-audit-diff");
  if (diffEl) diffEl.innerHTML = "";
  if (!el) return;
  const u = (url || "").toString().trim();
  if (!u) return;
  el.innerHTML = '<div class="text-sm text-gray-500">Загрузка истории…</div>';
  try {
    const payload = await _fetchJson(`/api/seo/deep-audit/history?url=${encodeURIComponent(u)}&limit=10`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    el.innerHTML = items.length
      ? `<div class="overflow-x-auto border rounded-lg bg-white">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 text-xs font-semibold uppercase text-gray-400">
              <tr>
                <th class="px-4 py-2">Дата</th>
                <th class="px-4 py-2">HTTP</th>
                <th class="px-4 py-2">Indexable</th>
                <th class="px-4 py-2">В индексе</th>
                <th class="px-4 py-2">SPAM</th>
                <th class="px-4 py-2">Alt</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              ${items
                .map((r) => {
                  const dt = (r.created_at || "").toString().slice(0, 19).replace("T", " ");
                  const sc = r.status_code ?? "—";
                  const idx = r.is_indexed === null || r.is_indexed === undefined ? "—" : r.is_indexed ? "Да" : "Нет";
                  const ix = r.indexable === null || r.indexable === undefined ? "—" : r.indexable ? "Да" : "Нет";
                  const sp = r.spam_score ?? 0;
                  const alt = r.images_missing_alt ?? "—";
                  return `<tr>
                    <td class="px-4 py-2 text-gray-600">${escapeHtml(dt || "—")}</td>
                    <td class="px-4 py-2 font-medium">${escapeHtml(String(sc))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(ix))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(idx))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(sp))}</td>
                    <td class="px-4 py-2">${escapeHtml(String(alt))}</td>
                  </tr>`;
                })
                .join("")}
            </tbody>
          </table>
        </div>`
      : '<div class="text-sm text-gray-500">Истории пока нет.</div>';
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

async function loadDeepAuditDiff(url) {
  const el = document.getElementById("deep-audit-diff");
  const histEl = document.getElementById("deep-audit-history");
  if (histEl) histEl.innerHTML = "";
  if (!el) return;
  const u = (url || "").toString().trim();
  if (!u) return;
  el.innerHTML = '<div class="text-sm text-gray-500">Загрузка сравнения…</div>';
  try {
    const payload = await _fetchJson(`/api/seo/deep-audit/diff?url=${encodeURIComponent(u)}`);
    const diff = payload?.diff || {};
    const keys = Object.keys(diff);
    if (!keys.length) {
      el.innerHTML = '<div class="text-sm text-gray-500">Недостаточно данных для сравнения (нужно 2 проверки).</div>';
      return;
    }
    el.innerHTML = `<div class="bg-white border rounded-lg p-4 space-y-2">
      <div class="text-xs font-semibold text-gray-500 uppercase">Изменения</div>
      <div class="space-y-1">
        ${keys
          .map((k) => {
            const d = diff[k] || {};
            const from = d.from === null || d.from === undefined ? "—" : String(d.from);
            const to = d.to === null || d.to === undefined ? "—" : String(d.to);
            const delta = d.delta === undefined ? "" : ` (Δ ${escapeHtml(String(d.delta))})`;
            return `<div class="flex justify-between gap-4">
              <div class="text-gray-600">${escapeHtml(String(k))}</div>
              <div class="font-medium text-right break-all">${escapeHtml(from)} → ${escapeHtml(to)}${delta}</div>
            </div>`;
          })
          .join("")}
      </div>
    </div>`;
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

async function createTasksFromDeepAudit(url) {
  const el = document.getElementById("deep-audit-diff");
  const u = (url || "").toString().trim();
  if (!el || !u) return;
  el.innerHTML = '<div class="text-sm text-gray-500">Создаю задачи…</div>';
  try {
    const payload = await _fetchJson("/api/seo/deep-audit/create-tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ url: u }),
    });
    const created = Number(payload?.created ?? 0);
    const skipped = Number(payload?.skipped_duplicates ?? 0);
    const siteId = payload?.site_id ? Number(payload.site_id) : null;
    const link = siteId ? `/tasks?status=todo&site_id=${encodeURIComponent(String(siteId))}` : "/tasks";
    el.innerHTML = `<div class="bg-white border rounded-lg p-4">
      <div class="font-medium">Готово: создано задач — ${escapeHtml(String(created))}${skipped ? `, пропущено дублей — ${escapeHtml(String(skipped))}` : ""}.</div>
      <a class="text-sm text-indigo-700 hover:underline" href="${escapeHtml(link)}">Открыть задачи</a>
    </div>`;
  } catch (e) {
    el.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

function renderMeta(data) {
  const el = document.getElementById("meta-result");
  if (!el) return;
  const meta = data?.meta ?? "";
  const length = data?.length ?? meta.length;
  const metaArg = escapeHtml(JSON.stringify(meta));
  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
      <div class="flex justify-between items-center">
        <div class="text-xs font-semibold text-gray-400 uppercase">Сгенерировано</div>
        <button class="text-xs text-indigo-700 hover:underline" onclick="navigator.clipboard.writeText(${metaArg})">Копировать</button>
      </div>
      <div class="text-sm text-gray-800 italic break-words">${escapeHtml(meta || "Пусто")}</div>
      <div class="text-xs text-gray-400 text-right">${escapeHtml(
        String(length)
      )} / 160</div>
    </div>
  `;
}

let positionsChartInstance = null;
let tasksChartInstance = null;
let errorsChartInstance = null;
const _chartCache = {};

function getChartPrefs() {
  const type = (localStorage.getItem("chart_type") || "line").toString();
  const smooth = (localStorage.getItem("chart_smooth") || "1").toString() === "1";
  const donutType = (localStorage.getItem("chart_donut_type") || "doughnut").toString();
  return {
    type: type === "bar" ? "bar" : "line",
    smooth,
    donutType: donutType === "bar" ? "bar" : "doughnut",
  };
}

function _withAlpha(hex, alpha) {
  const s = String(hex || "");
  const m = /^#?([a-fA-F0-9]{6})$/.exec(s);
  if (!m) return s;
  const v = m[1];
  const r = parseInt(v.slice(0, 2), 16);
  const g = parseInt(v.slice(2, 4), 16);
  const b = parseInt(v.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function _chartOptions({ reverseY, beginAtZero, yMin, yMax }) {
  const common = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: true, position: "bottom", labels: { boxWidth: 12, font: { size: 12 } } },
      tooltip: { mode: "index", intersect: false },
    },
  };
  return {
    ...common,
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: {
        reverse: Boolean(reverseY),
        beginAtZero: Boolean(beginAtZero),
        min: yMin,
        max: yMax,
        ticks: { precision: 0, font: { size: 11 } },
      },
    },
  };
}

function _seriesDataset(label, data, colorHex) {
  const prefs = getChartPrefs();
  if (prefs.type === "bar") {
    return {
      label,
      data,
      backgroundColor: _withAlpha(colorHex, 0.7),
      borderColor: _withAlpha(colorHex, 1),
      borderWidth: 0,
      borderRadius: 6,
    };
  }
  return {
    label,
    data,
    borderColor: _withAlpha(colorHex, 1),
    backgroundColor: _withAlpha(colorHex, 0.12),
    tension: prefs.smooth ? 0.35 : 0,
    fill: true,
    pointRadius: 2,
    pointHoverRadius: 5,
  };
}

function rerenderChartsFromCache() {
  if (_chartCache.positions && document.getElementById("positions-chart")) renderPositionsChart(_chartCache.positions);
  if (_chartCache.tasks && document.getElementById("tasks-chart")) renderTasksChart(_chartCache.tasks);
  if (_chartCache.errors && document.getElementById("errors-chart")) renderErrorsChart(_chartCache.errors);
  if (_chartCache.linksStats && document.getElementById("links-growth-chart")) renderLinksCharts(_chartCache.linksStats);
  if (_chartCache.ahrefs && document.getElementById("links-dr-chart")) renderAhrefsCharts(_chartCache.ahrefs);
  if (_chartCache.anchor && document.getElementById("links-anchors-chart")) renderAnchorAnalysis(_chartCache.anchor);
  if (_chartCache.kwHistory && document.getElementById("keywords-history-chart")) renderKeywordsHistoryChart(_chartCache.kwHistory);
  if (_chartCache.internalLinks && document.getElementById("il-depth-chart")) renderInternalLinks(_chartCache.internalLinks);
}

function initChartControls() {
  const typeEl = document.getElementById("chart-type");
  const smoothEl = document.getElementById("chart-smooth");
  const donutEl = document.getElementById("chart-donut-type");
  if (!typeEl && !smoothEl && !donutEl) return;

  const prefs = getChartPrefs();
  if (typeEl) typeEl.value = prefs.type;
  if (smoothEl) smoothEl.checked = Boolean(prefs.smooth);
  if (donutEl) donutEl.value = prefs.donutType;

  const onChange = () => {
    if (typeEl) localStorage.setItem("chart_type", String(typeEl.value || "line"));
    if (smoothEl) localStorage.setItem("chart_smooth", smoothEl.checked ? "1" : "0");
    if (donutEl) localStorage.setItem("chart_donut_type", String(donutEl.value || "doughnut"));
    rerenderChartsFromCache();
  };
  if (typeEl) typeEl.addEventListener("change", onChange);
  if (smoothEl) smoothEl.addEventListener("change", onChange);
  if (donutEl) donutEl.addEventListener("change", onChange);
}

function applySitesScanView(mode) {
  const view = (mode || "large").toString();
  const smallHeight = view === "compact" ? "10rem" : "14rem";
  const bigHeight = view === "compact" ? "14rem" : "18rem";
  document.querySelectorAll('[data-sites-chart-box="small"]').forEach((el) => {
    el.style.height = smallHeight;
  });
  document.querySelectorAll('[data-sites-chart-box="big"]').forEach((el) => {
    el.style.height = bigHeight;
  });
  window.dispatchEvent(new Event("resize"));
}

function initSitesScanViewControl() {
  const selectEl = document.getElementById("sites-scan-view");
  const panel = document.getElementById("scan-history-panel");
  if (!selectEl || !panel) return;
  const saved = (localStorage.getItem("sites_scan_view") || "large").toString();
  selectEl.value = saved === "compact" ? "compact" : "large";
  applySitesScanView(selectEl.value);
  selectEl.addEventListener("change", () => {
    localStorage.setItem("sites_scan_view", String(selectEl.value || "large"));
    applySitesScanView(selectEl.value);
  });
}

function initSitesChartTypeControl() {
  const el = document.getElementById("sites-chart-type");
  const panel = document.getElementById("scan-history-panel");
  if (!el || !panel) return;
  const prefs = getChartPrefs();
  el.value = prefs.type;
  el.addEventListener("change", () => {
    localStorage.setItem("chart_type", String(el.value || "line"));
    rerenderChartsFromCache();
    const { id, domain } = getSelectedSite();
    if (id && domain) loadScanHistory(id, domain);
    else if (id) loadScanHistory(id);
  });
}

function renderPositionsChart(payload) {
  _chartCache.positions = payload;
  const canvas = document.getElementById("positions-chart");
  if (!canvas || !window.Chart) return;
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const values = Array.isArray(payload?.values) ? payload.values : [];
  const lineLabel = payload?.label ? String(payload.label) : "Средняя позиция";
  const reverseY = payload?.reverse_y === false ? false : true;
  const prefs = getChartPrefs();

  if (positionsChartInstance) {
    positionsChartInstance.destroy();
    positionsChartInstance = null;
  }
  if (!labels.length || !values.length) {
    drawCanvasMessage(canvas, "Нет данных");
    return;
  }

  positionsChartInstance = new Chart(canvas, {
    type: prefs.type,
    data: {
      labels,
      datasets: [
        _seriesDataset(lineLabel, values, "#4f46e5"),
      ],
    },
    options: _chartOptions({ reverseY, beginAtZero: false }),
  });
}

function renderTasksChart(payload) {
  _chartCache.tasks = payload;
  const canvas = document.getElementById("tasks-chart");
  if (!canvas || !window.Chart) return;
  const todo = Number(payload?.todo ?? 0);
  const inProgress = Number(payload?.in_progress ?? 0);
  const done = Number(payload?.done ?? 0);
  const prefs = getChartPrefs();
  const labelsRu = ["в ожидании", "в работе", "готово"];

  if (tasksChartInstance) {
    tasksChartInstance.destroy();
    tasksChartInstance = null;
  }
  if (todo + inProgress + done === 0) {
    drawCanvasMessage(canvas, "Нет задач");
    return;
  }

  if (prefs.donutType === "bar") {
    tasksChartInstance = new Chart(canvas, {
      type: "bar",
      data: {
        labels: labelsRu,
        datasets: [
          {
            label: "Задачи",
            data: [todo, inProgress, done],
            backgroundColor: ["#f59e0b", "#10b981", "#6366f1"],
            borderRadius: 6,
          },
        ],
      },
      options: _chartOptions({ reverseY: false, beginAtZero: true }),
    });
    return;
  }

  tasksChartInstance = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labelsRu,
      datasets: [
        {
          data: [todo, inProgress, done],
          backgroundColor: ["#f59e0b", "#10b981", "#6366f1"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function renderErrorsChart(payload) {
  _chartCache.errors = payload;
  const canvas = document.getElementById("errors-chart");
  if (!canvas || !window.Chart) return;
  const ok = Number(payload?.ok ?? 0);
  const warning = Number(payload?.warning ?? 0);
  const error = Number(payload?.error ?? 0);
  const prefs = getChartPrefs();
  const labelsRu = ["OK", "предупреждение", "ошибка"];

  if (errorsChartInstance) {
    errorsChartInstance.destroy();
    errorsChartInstance = null;
  }
  if (ok + warning + error === 0) {
    drawCanvasMessage(canvas, "Нет данных");
    return;
  }

  if (prefs.donutType === "doughnut") {
    errorsChartInstance = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: labelsRu,
        datasets: [
          {
            label: "Проверки",
            data: [ok, warning, error],
            backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
    });
    return;
  }

  errorsChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labelsRu,
      datasets: [
        {
          label: "Количество (по последним данным)",
          data: [ok, warning, error],
          backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          borderRadius: 6,
        },
      ],
    },
    options: _chartOptions({ reverseY: false, beginAtZero: true }),
  });
}

function renderAiKeywords(payload) {
  const el = document.getElementById("ai-keywords-result");
  if (!el) return;
  const items = Array.isArray(payload?.keywords) ? payload.keywords : [];
  if (items.length === 0) {
    el.textContent = "Ключевые слова не найдены.";
    return;
  }
  el.innerHTML = `
    <div class="overflow-x-auto border rounded-lg">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-xs font-semibold uppercase text-gray-400">
          <tr>
            <th class="px-4 py-2">Ключевое слово</th>
            <th class="px-4 py-2">Частота</th>
            <th class="px-4 py-2">%</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          ${items
            .map(
              (k) => `
                <tr>
                  <td class="px-4 py-2 font-medium">${escapeHtml(k.keyword ?? "")}</td>
                  <td class="px-4 py-2">${escapeHtml(String(k.count ?? ""))}</td>
                  <td class="px-4 py-2">${escapeHtml(String(k.percentage ?? ""))}</td>
                </tr>
              `
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderTitleCheck(payload) {
  const el = document.getElementById("title-check-result");
  if (!el) return;
  const status = payload?.status ?? "unknown";
  const length = payload?.length ?? 0;
  const recommendation = payload?.recommendation ?? "";
  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
      <div class="flex justify-between">
        <span class="text-gray-500">Статус:</span>
        <span class="font-semibold">${escapeHtml(String(status))}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-gray-500">Длина:</span>
        <span class="font-medium">${escapeHtml(String(length))}</span>
      </div>
      <div class="text-gray-700">${escapeHtml(String(recommendation))}</div>
    </div>
  `;
}

async function loadSites() {
  const resp = await fetch("/api/sites/", { headers: { Accept: "application/json" } });
  const data = await resp.json();
  renderSites(data);
}

async function deleteSite(id) {
  await fetch(`/api/sites/${id}`, { method: "DELETE" });
  await loadSites();
}

let robotsStatusChartInstance = null;
let sitemapErrorsChartInstance = null;
let techAuditStatusChartInstance = null;

async function loadMetricHistory(siteId, metricType) {
  const resp = await fetch(`/api/sites/${siteId}/metric-history?metric_type=${encodeURIComponent(metricType)}`, {
    headers: { Accept: "application/json" },
  });
  return await resp.json();
}

function setSelectedSite(siteId, domain) {
  if (siteId != null) localStorage.setItem("selected_site_id", String(siteId));
  if (domain != null) localStorage.setItem("selected_site_domain", String(domain));
}

function getSelectedSite() {
  const idRaw = localStorage.getItem("selected_site_id");
  const domainRaw = localStorage.getItem("selected_site_domain");
  const id = idRaw ? Number(idRaw) : null;
  const domain = domainRaw ? String(domainRaw) : null;
  return { id: Number.isFinite(id) ? id : null, domain };
}

function setHistoryHint(siteId, domain) {
  const panel = document.getElementById("scan-history-panel");
  if (!panel) return;
  panel.dataset.siteId = siteId != null ? String(siteId) : "";
  panel.dataset.siteDomain = domain != null ? String(domain) : "";

  const label = document.getElementById("selected-site-label");
  if (label) {
    if (domain) label.textContent = String(domain);
    else if (siteId != null) label.textContent = `#${String(siteId)}`;
    else label.textContent = "—";
  }
}

function statusToNumber(status) {
  const s = String(status ?? "").toUpperCase();
  if (s === "OK") return 2;
  if (s === "WARNING") return 1;
  if (s === "ERROR") return 0;
  return null;
}

function techAuditToNumber(value) {
  const robots = String(value?.robots_status ?? "").toUpperCase();
  const sitemap = String(value?.sitemap_status ?? "").toUpperCase();
  if (robots === "ERROR" || sitemap === "ERROR") return 0;
  if (robots === "WARNING" || sitemap === "WARNING") return 1;
  if (robots === "OK" && sitemap === "OK") return 2;
  return null;
}

async function renderRobotsHistoryChart(siteId) {
  const payload = await loadMetricHistory(siteId, "robots");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const labels = items.map((i) => String(i.created_at ?? ""));
  const values = items.map((i) => statusToNumber(i?.value?.status));

  const canvas = document.getElementById("robots-status-chart");
  if (!canvas || !window.Chart) return;
  if (robotsStatusChartInstance) robotsStatusChartInstance.destroy();
  const prefs = getChartPrefs();
  robotsStatusChartInstance = new Chart(canvas, {
    type: prefs.type,
    data: {
      labels,
      datasets: [
        _seriesDataset("robots.txt (OK=2, WARNING=1, ERROR=0)", values, "#6366f1"),
      ],
    },
    options: _chartOptions({ reverseY: false, beginAtZero: true, yMin: 0, yMax: 2 }),
  });
}

async function renderSitemapErrorsChart(siteId) {
  const payload = await loadMetricHistory(siteId, "sitemap");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const labels = items.map((i) => String(i.created_at ?? ""));
  const values = items.map((i) => {
    const errs = i?.value?.errors;
    return Array.isArray(errs) ? errs.length : 0;
  });

  const canvas = document.getElementById("sitemap-errors-chart");
  if (!canvas || !window.Chart) return;
  if (sitemapErrorsChartInstance) sitemapErrorsChartInstance.destroy();
  const prefs = getChartPrefs();
  sitemapErrorsChartInstance = new Chart(canvas, {
    type: prefs.type,
    data: {
      labels,
      datasets: [
        _seriesDataset("Ошибки sitemap (кол-во)", values, "#ef4444"),
      ],
    },
    options: _chartOptions({ reverseY: false, beginAtZero: true }),
  });
}

function renderTechAuditResult(value) {
  const el = document.getElementById("tech-audit-result");
  if (!el) return;
  if (!value) {
    el.textContent = "Нет данных";
    return;
  }
  const scan = value?.scan ?? {};
  const health = scan?.health_score;
  const robots = value?.robots_status ?? "—";
  const sitemap = value?.sitemap_status ?? "—";
  el.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="text-xs text-gray-500">Оценка</div>
      <div class="font-semibold">${health != null ? escapeHtml(String(health)) : "—"}</div>
    </div>
    <div class="mt-1 text-xs text-gray-600">robots: ${escapeHtml(String(robots))}, sitemap: ${escapeHtml(
    String(sitemap)
  )}</div>
  `;
}

async function renderTechAuditStatusChart(siteId) {
  const payload = await loadMetricHistory(siteId, "tech_audit");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const labels = items.map((i) => String(i.created_at ?? ""));
  const values = items.map((i) => techAuditToNumber(i?.value));

  const canvas = document.getElementById("tech-audit-status-chart");
  if (!canvas || !window.Chart) return;
  if (techAuditStatusChartInstance) techAuditStatusChartInstance.destroy();
  const prefs = getChartPrefs();
  techAuditStatusChartInstance = new Chart(canvas, {
    type: prefs.type,
    data: {
      labels,
      datasets: [
        _seriesDataset("Тех. аудит (OK=2, WARNING=1, ERROR=0)", values, "#0ea5e9"),
      ],
    },
    options: _chartOptions({ reverseY: false, beginAtZero: true, yMin: 0, yMax: 2 }),
  });
}

async function runAllScans() {
  const resultEl = document.getElementById("site-create-error");
  try {
    const resp = await fetch(`/api/sites/scan-all${buildUaQuery()}`, { method: "POST" });
    const json = safeJsonParse(await resp.text()) || {};
    if (!resp.ok) throw new Error(json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`);
    if (resultEl) resultEl.textContent = "Полный аудит запущен в фоне.";
  } catch (e) {
    if (resultEl) resultEl.textContent = String(e?.message ?? e);
  }
}

async function runSiteScan(siteId) {
  const resultEl = document.getElementById("site-create-error");
  try {
    const resp = await fetch(`/api/sites/${siteId}/scan${buildUaQuery()}`, { method: "POST" });
    const json = safeJsonParse(await resp.text()) || {};
    if (!resp.ok) throw new Error(json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`);
    if (resultEl) resultEl.textContent = `Скан запущен (task #${json.task_id ?? "?"}).`;
    if (json.task_id) pollTaskStatus(Number(json.task_id), `Скан сайта #${siteId}`);
  } catch (e) {
    if (resultEl) resultEl.textContent = String(e?.message ?? e);
  }
  await loadScanHistory(siteId);
}

async function runTechAudit(siteId) {
  const resultEl = document.getElementById("site-create-error");
  try {
    const resp = await fetch(`/api/sites/${siteId}/tech-audit${buildUaQuery()}`, { method: "POST" });
    const json = safeJsonParse(await resp.text()) || {};
    if (!resp.ok) throw new Error(json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`);
    if (resultEl) resultEl.textContent = `Тех. аудит запущен (task #${json.task_id ?? "?"}).`;
    if (json.task_id) pollTaskStatus(Number(json.task_id), `Тех. аудит (сайт #${siteId})`);
  } catch (e) {
    if (resultEl) resultEl.textContent = String(e?.message ?? e);
  }
  await loadScanHistory(siteId);
}

function _translateTaskStatus(st) {
  const v = (st || "").toString();
  if (v === "todo") return "в ожидании";
  if (v === "in_progress") return "в работе";
  if (v === "done") return "готово";
  return v || "неизвестно";
}

async function pollTaskStatus(taskId, title, resultElementId) {
  const resultEl = document.getElementById(resultElementId || "site-create-error");
  if (!taskId) return;
  let attempts = 0;
  while (attempts < 60) {
    attempts += 1;
    try {
      const t = await _fetchJson(`/api/sites/tasks/${encodeURIComponent(String(taskId))}`);
      const st = (t?.status || "").toString();
      const ru = _translateTaskStatus(st);
      const taskTitle = (t?.title || "").toString().trim();
      const main = taskTitle ? `Задача #${taskId} — ${taskTitle}` : `Задача #${taskId}`;
      if (resultEl) {
        if (st === "done") resultEl.textContent = `${title}: ${ru}. ${main}. Результаты обновлены.`;
        else resultEl.textContent = `${title}: ${ru}. ${main}.`;
      }
      if (st === "done") return;
      if (st === "todo" && String(t?.description || "").includes("Ошибка")) return;
    } catch (e) {
      if (resultEl) resultEl.textContent = `${title}: не удалось получить статус task #${taskId}`;
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

async function checkRobots(siteId) {
  setSelectedSite(siteId, getSelectedSite().domain);
  const resp = await fetch(`/api/sites/${siteId}/robots-check${buildUaQuery()}`, { method: "POST" });
  const data = await resp.json();
  renderRobotsResult(data);
  await renderRobotsHistoryChart(siteId);
}

async function checkSitemap(siteId) {
  setSelectedSite(siteId, getSelectedSite().domain);
  const resp = await fetch(`/api/sites/${siteId}/sitemap-check${buildUaQuery()}`, { method: "POST" });
  const data = await resp.json();
  renderSitemapResult(data);
  await renderSitemapErrorsChart(siteId);
}

function renderRobotsResult(data) {
  const el = document.getElementById("robots-result");
  if (!el) return;
  const status = data?.status ?? "—";
  const httpStatus = data?.http_status ?? "—";
  const hasSitemap = Array.isArray(data?.sitemaps) && data.sitemaps.length > 0;
  const warn = Array.isArray(data?.warnings) ? data.warnings : [];
  el.innerHTML = `
    <div class="flex items-center justify-between">
      <div><span class="font-semibold">${escapeHtml(String(status))}</span> (HTTP ${escapeHtml(String(httpStatus))})</div>
      <div class="text-xs text-gray-500">${hasSitemap ? "Sitemap: да" : "Sitemap: нет"}</div>
    </div>
    ${warn.length ? `<div class="mt-2 text-xs text-gray-600">${warn.map(escapeHtml).join("<br/>")}</div>` : ""}
  `;
}

function renderSitemapResult(data) {
  const el = document.getElementById("sitemap-result");
  if (!el) return;
  const status = data?.status ?? "—";
  const httpStatus = data?.http_status ?? "—";
  const urlsCount = data?.urls_count;
  const sitemaps = Array.isArray(data?.sitemaps) ? data.sitemaps : [];
  const errors = Array.isArray(data?.errors) ? data.errors : [];
  el.innerHTML = `
    <div class="flex items-center justify-between">
      <div><span class="font-semibold">${escapeHtml(String(status))}</span> (HTTP ${escapeHtml(String(httpStatus))})</div>
      <div class="text-xs text-gray-500">${urlsCount != null ? `URL: ${escapeHtml(String(urlsCount))}` : `Sitemap: ${escapeHtml(String(sitemaps.length))}`}</div>
    </div>
    ${errors.length ? `<div class="mt-2 text-xs text-gray-600">${errors.map(escapeHtml).join("<br/>")}</div>` : ""}
  `;
}

let scanRtChartInstance = null;
let scanHealthChartInstance = null;

function renderScanHistory(payload) {
  const table = document.getElementById("scan-history-table");
  if (table) {
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const last = items.slice(-20).reverse();
    if (last.length === 0) {
      table.innerHTML =
        '<tr><td colspan="7" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    } else {
      table.innerHTML = last
        .map((i) => {
          return `
            <tr>
              <td class="px-4 py-2 text-gray-500">${escapeHtml(i.created_at ?? "")}</td>
              <td class="px-4 py-2">${escapeHtml(String(i.status_code ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(String(i.response_time_ms ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(String(i.title_length ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(i.h1_present ? "да" : "нет")}</td>
              <td class="px-4 py-2">${escapeHtml(
                i.indexed === true ? "да" : i.indexed === false ? "нет" : "неизвестно"
              )}</td>
              <td class="px-4 py-2">${escapeHtml(String(i.health_score ?? ""))}</td>
            </tr>
          `;
        })
        .join("");
    }
  }

  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const rt = Array.isArray(payload?.response_time_ms) ? payload.response_time_ms : [];
  const health = Array.isArray(payload?.health_score) ? payload.health_score : [];

  if (window.Chart) {
    const rtCanvas = document.getElementById("scan-rt-chart");
    const healthCanvas = document.getElementById("scan-health-chart");
    const prefs = getChartPrefs();

    if (rtCanvas) {
      if (scanRtChartInstance) scanRtChartInstance.destroy();
      if (!labels.length || !rt.length) {
        drawCanvasMessage(rtCanvas, "Нет данных");
        scanRtChartInstance = null;
      } else {
      scanRtChartInstance = new Chart(rtCanvas, {
        type: prefs.type,
        data: { labels, datasets: [_seriesDataset("Время ответа (мс)", rt, "#0ea5e9")] },
        options: _chartOptions({ reverseY: false, beginAtZero: true }),
      });
      }
    }

    if (healthCanvas) {
      if (scanHealthChartInstance) scanHealthChartInstance.destroy();
      if (!labels.length || !health.length) {
        drawCanvasMessage(healthCanvas, "Нет данных");
        scanHealthChartInstance = null;
      } else {
      scanHealthChartInstance = new Chart(healthCanvas, {
        type: prefs.type,
        data: { labels, datasets: [_seriesDataset("Оценка (0..100)", health, "#10b981")] },
        options: _chartOptions({ reverseY: false, beginAtZero: true, yMin: 0, yMax: 100 }),
      });
      }
    }
  }
}

async function loadAndRenderLatestMetrics(siteId) {
  const robotsPayload = await loadMetricHistory(siteId, "robots");
  const robotsItems = Array.isArray(robotsPayload?.items) ? robotsPayload.items : [];
  const robotsLast = robotsItems.length ? robotsItems[robotsItems.length - 1] : null;
  if (robotsLast?.value) {
    renderRobotsResult(robotsLast.value);
  } else {
    const el = document.getElementById("robots-result");
    if (el) el.textContent = "Нет данных";
  }

  const sitemapPayload = await loadMetricHistory(siteId, "sitemap");
  const sitemapItems = Array.isArray(sitemapPayload?.items) ? sitemapPayload.items : [];
  const sitemapLast = sitemapItems.length ? sitemapItems[sitemapItems.length - 1] : null;
  if (sitemapLast?.value) {
    renderSitemapResult(sitemapLast.value);
  } else {
    const el = document.getElementById("sitemap-result");
    if (el) el.textContent = "Нет данных";
  }

  const techPayload = await loadMetricHistory(siteId, "tech_audit");
  const techItems = Array.isArray(techPayload?.items) ? techPayload.items : [];
  const techLast = techItems.length ? techItems[techItems.length - 1] : null;
  if (techLast?.value) {
    renderTechAuditResult(techLast.value);
  } else {
    const el = document.getElementById("tech-audit-result");
    if (el) el.textContent = "Нет данных";
  }
}

async function loadScanHistory(siteId, domain) {
  if (siteId == null) return;
  setSelectedSite(siteId, domain ?? getSelectedSite().domain);
  setHistoryHint(siteId, domain ?? getSelectedSite().domain);

  const resp = await fetch(`/api/sites/${siteId}/scan-history`, { headers: { Accept: "application/json" } });
  const data = await resp.json();
  renderScanHistory(data);

  await loadAndRenderLatestMetrics(siteId);
  await renderRobotsHistoryChart(siteId);
  await renderSitemapErrorsChart(siteId);
  await renderTechAuditStatusChart(siteId);
  await loadSites();
}

async function refreshHistory() {
  const { id, domain } = getSelectedSite();
  if (!id) return;
  await loadScanHistory(id, domain ?? undefined);
}

async function clearSelectedScanHistory() {
  const { id, domain } = getSelectedSite();
  if (!id) return;
  const resEl = document.getElementById("site-create-error");
  const ok = window.prompt("Сбросить историю сканов для выбранного сайта? Введите DELETE:", "");
  if (ok !== "DELETE") return;
  try {
    const payload = await _fetchJson(
      `/api/sites/${encodeURIComponent(String(id))}/scan-history/clear?confirm=DELETE`,
      { method: "POST" }
    );
    const msg = `История очищена: scans=${payload.deleted_scan_rows ?? 0}, health=${payload.deleted_health_rows ?? 0}`;
    if (resEl) resEl.textContent = msg;
    await loadScanHistory(id, domain ?? undefined);
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function cleanupScans() {
  const resEl = document.getElementById("site-create-error");
  try {
    const payload = await _fetchJson("/api/scans/cleanup?hours=48", { method: "POST" });
    const msg = `Очистка выполнена: scans=${payload.deleted_scan_rows ?? 0}, audits=${payload.deleted_audit_rows ?? 0}`;
    if (resEl) resEl.textContent = msg;
    await refreshHistory();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

let linksGrowthChartInstance = null;
let linksNewLostChartInstance = null;
let linksDrChartInstance = null;
let linksToxicChartInstance = null;
let linksAnchorsChartInstance = null;

function drawCanvasMessage(canvas, text) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const ratio = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || canvas.width;
  const h = canvas.clientHeight || canvas.height;
  canvas.width = Math.max(1, Math.floor(w * ratio));
  canvas.height = Math.max(1, Math.floor(h * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#9ca3af";
  ctx.font = "14px system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(String(text || "Нет данных"), w / 2, h / 2);
}

function resetLinksCharts(message) {
  const msg = message || "Нет данных";
  const canvases = [
    "links-growth-chart",
    "links-newlost-chart",
    "links-dr-chart",
    "links-toxic-chart",
    "links-anchors-chart",
  ].map((id) => document.getElementById(id));
  if (linksGrowthChartInstance) linksGrowthChartInstance.destroy();
  if (linksNewLostChartInstance) linksNewLostChartInstance.destroy();
  if (linksDrChartInstance) linksDrChartInstance.destroy();
  if (linksToxicChartInstance) linksToxicChartInstance.destroy();
  if (linksAnchorsChartInstance) linksAnchorsChartInstance.destroy();
  linksGrowthChartInstance = null;
  linksNewLostChartInstance = null;
  linksDrChartInstance = null;
  linksToxicChartInstance = null;
  linksAnchorsChartInstance = null;
  canvases.forEach((c) => drawCanvasMessage(c, msg));
}

function _linksColorByCompare(compare) {
  const c = String(compare ?? "").toUpperCase();
  if (c === "OK") return "bg-emerald-50";
  if (c === "NEW") return "bg-amber-50";
  if (c === "LOST") return "bg-rose-50";
  return "";
}

function _badge(text, color) {
  return `<span class="px-2 py-1 rounded text-xs ${color}">${escapeHtml(String(text ?? ""))}</span>`;
}

async function _fetchJson(url, options) {
  const resp = await fetch(url, { headers: { Accept: "application/json" }, ...(options || {}) });
  const text = await resp.text();
  const json = safeJsonParse(text);
  if (!resp.ok) {
    const msg = json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`;
    throw new Error(msg);
  }
  return json;
}

function _selectedLinksSiteId() {
  const el = document.getElementById("links-site-select");
  const val = el?.value ? Number(el.value) : null;
  if (val) return val;
  const saved = localStorage.getItem("selected_site_id");
  return saved ? Number(saved) : null;
}

async function loadLinksSites() {
  const selectEl = document.getElementById("links-site-select");
  if (!selectEl) return;
  const sites = await _fetchJson("/api/sites/");
  const list = Array.isArray(sites) ? sites : [];
  const saved = localStorage.getItem("selected_site_id") || "";
  selectEl.innerHTML = ['<option value="">Выберите сайт…</option>']
    .concat(
      list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`)
    )
    .join("");
  if (saved) selectEl.value = String(saved);
}

async function reloadLinks() {
  const siteId = _selectedLinksSiteId();
  const tbody = document.getElementById("links-body");
  if (!siteId) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="px-6 py-10 text-center text-gray-400">Выберите сайт</td></tr>';
    const totalsEl = document.getElementById("links-totals");
    if (totalsEl) totalsEl.textContent = "—";
    const lastEl = document.getElementById("links-last-analyzed");
    if (lastEl) lastEl.textContent = "—";
    resetLinksCharts("Выберите сайт");
    return;
  }

  const compareEl = document.getElementById("links-compare-filter");
  const typeEl = document.getElementById("links-type-filter");
  const toxicEl = document.getElementById("links-toxic-filter");
  const qEl = document.getElementById("links-q");
  const compare = (compareEl?.value || "").toString();
  const link_type = (typeEl?.value || "").toString();
  const toxic = (toxicEl?.value || "").toString();
  const q = (qEl?.value || "").toString();

  const params = new URLSearchParams();
  params.set("site_id", String(siteId));
  if (compare) params.set("compare", compare);
  if (link_type) params.set("link_type", link_type);
  if (toxic) params.set("toxic", toxic);
  if (q) params.set("q", q);

  const items = await _fetchJson(`/api/links?${params.toString()}`);
  renderLinksTable(items);
  await loadLinksStats();
  await loadAhrefsHistory();
  await loadAnchorAnalysis();
  await loadTopPages();
  await loadBrokenLinks();
}

function renderLinksTable(items) {
  const tbody = document.getElementById("links-body");
  if (!tbody) return;
  const list = Array.isArray(items) ? items : [];
  if (list.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="px-6 py-10 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }

  tbody.innerHTML = list
    .map((b) => {
      const rowClass = _linksColorByCompare(b.compare);
      const target = b.target_url ?? "";
      const donor = b.donor ?? "";
      const anchor = b.anchor ?? "";
      const linkType = b.link_type ?? "";
      const status = b.status ?? "";
      const source = b.source ?? "";
      const firstSeen = b.first_seen ?? "";
      const lastChecked = b.last_checked ?? "";

      const statusBadge =
        String(status).toLowerCase() === "active"
          ? _badge("active", "bg-emerald-100 text-emerald-700")
          : String(status).toLowerCase() === "lost"
          ? _badge("lost", "bg-rose-100 text-rose-700")
          : _badge("broken", "bg-gray-200 text-gray-800");

      const compareBadge =
        String(b.compare).toUpperCase() === "OK"
          ? _badge("OK", "bg-emerald-100 text-emerald-700")
          : String(b.compare).toUpperCase() === "NEW"
          ? _badge("NEW", "bg-amber-100 text-amber-700")
          : _badge("LOST", "bg-rose-100 text-rose-700");

      const typeBadge =
        String(linkType).toLowerCase() === "nofollow"
          ? _badge("nofollow", "bg-gray-200 text-gray-800")
          : _badge("dofollow", "bg-indigo-100 text-indigo-700");

      const dr = b.domain_score != null ? String(b.domain_score) : "—";
      const tox = b.toxic_score != null ? String(b.toxic_score) : "—";
      const toxFlag = (b.toxic_flag || "").toString();
      const toxBadge =
        toxFlag === "toxic"
          ? _badge(`toxic ${tox}`, "bg-rose-100 text-rose-700")
          : toxFlag === "suspicious"
          ? _badge(`sus ${tox}`, "bg-amber-100 text-amber-700")
          : toxFlag === "safe"
          ? _badge(`safe ${tox}`, "bg-emerald-100 text-emerald-700")
          : _badge(String(tox), "bg-gray-200 text-gray-800");

      return `
        <tr class="${rowClass}">
          <td class="px-6 py-3 break-all">${escapeHtml(String(target))}</td>
          <td class="px-6 py-3">${escapeHtml(String(donor))}</td>
          <td class="px-6 py-3">${escapeHtml(String(anchor))}</td>
          <td class="px-6 py-3">${typeBadge}</td>
          <td class="px-6 py-3 space-x-2">${statusBadge} ${compareBadge}</td>
          <td class="px-6 py-3 text-gray-700">${escapeHtml(dr)}</td>
          <td class="px-6 py-3">${toxBadge}</td>
          <td class="px-6 py-3 text-gray-600">${escapeHtml(String(source))}</td>
          <td class="px-6 py-3 text-gray-600">${escapeHtml(String(firstSeen).slice(0, 10))}</td>
          <td class="px-6 py-3 text-gray-600">${lastChecked ? escapeHtml(String(lastChecked).slice(0, 19).replace("T", " ")) : "—"}</td>
        </tr>
      `;
    })
    .join("");
}

async function loadLinksStats() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const payload = await _fetchJson(`/api/links/stats?site_id=${encodeURIComponent(String(siteId))}&days=30`);
  renderLinksCharts(payload);
}

function renderLinksCharts(payload) {
  _chartCache.linksStats = payload;
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const newCounts = Array.isArray(payload?.new) ? payload.new : [];
  const lostCounts = Array.isArray(payload?.lost) ? payload.lost : [];
  const totals = payload?.totals ?? {};
  const prefs = getChartPrefs();

  const totalsEl = document.getElementById("links-totals");
  if (totalsEl) {
    totalsEl.textContent = `всего: ${totals.all ?? 0}, active: ${totals.active ?? 0}, lost: ${totals.lost ?? 0}, broken: ${totals.broken ?? 0}`;
  }

  const growthCanvas = document.getElementById("links-growth-chart");
  if (growthCanvas && window.Chart) {
    if (linksGrowthChartInstance) linksGrowthChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(growthCanvas, "Нет данных");
      linksGrowthChartInstance = null;
      return;
    }
    const base = Math.max(0, Number(totals.all ?? 0) - newCounts.reduce((a, b) => a + Number(b || 0), 0));
    let running = base;
    const series = newCounts.map((n) => {
      running += Number(n || 0);
      return running;
    });
    linksGrowthChartInstance = new Chart(growthCanvas, {
      type: prefs.type,
      data: {
        labels,
        datasets: [_seriesDataset("Всего ссылок (по first_seen)", series, "#6366f1")],
      },
      options: _chartOptions({ reverseY: false, beginAtZero: true }),
    });
  }

  const nlCanvas = document.getElementById("links-newlost-chart");
  if (nlCanvas && window.Chart) {
    if (linksNewLostChartInstance) linksNewLostChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(nlCanvas, "Нет данных");
      linksNewLostChartInstance = null;
      return;
    }
    linksNewLostChartInstance = new Chart(nlCanvas, {
      type: prefs.type,
      data: {
        labels,
        datasets: [
          prefs.type === "bar"
            ? { label: "Новые", data: newCounts, backgroundColor: "#10b981", borderRadius: 6 }
            : { label: "Новые", data: newCounts, borderColor: "#10b981", backgroundColor: _withAlpha("#10b981", 0.08), tension: prefs.smooth ? 0.35 : 0, fill: false, pointRadius: 2 },
          prefs.type === "bar"
            ? { label: "Потерянные", data: lostCounts, backgroundColor: "#ef4444", borderRadius: 6 }
            : { label: "Потерянные", data: lostCounts, borderColor: "#ef4444", backgroundColor: _withAlpha("#ef4444", 0.08), tension: prefs.smooth ? 0.35 : 0, fill: false, pointRadius: 2 },
        ],
      },
      options: _chartOptions({ reverseY: false, beginAtZero: true }),
    });
  }
}

async function loadAhrefsHistory() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const payload = await _fetchJson(`/api/links/ahrefs-history?site_id=${encodeURIComponent(String(siteId))}&limit=200`);
  renderAhrefsCharts(payload);
}

function renderAhrefsCharts(payload) {
  _chartCache.ahrefs = payload;
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const dr = Array.isArray(payload?.avg_dr) ? payload.avg_dr : [];
  const tox = Array.isArray(payload?.toxic_pct) ? payload.toxic_pct : [];
  const prefs = getChartPrefs();

  const drCanvas = document.getElementById("links-dr-chart");
  if (drCanvas && window.Chart) {
    if (linksDrChartInstance) linksDrChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(drCanvas, "Нет данных");
      linksDrChartInstance = null;
    } else {
      linksDrChartInstance = new Chart(drCanvas, {
        type: prefs.type,
        data: { labels, datasets: [_seriesDataset("AVG DR", dr, "#6366f1")] },
        options: _chartOptions({ reverseY: false, beginAtZero: true, yMin: 0, yMax: 100 }),
      });
    }
  }

  const toxCanvas = document.getElementById("links-toxic-chart");
  if (toxCanvas && window.Chart) {
    if (linksToxicChartInstance) linksToxicChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(toxCanvas, "Нет данных");
      linksToxicChartInstance = null;
      return;
    }
    linksToxicChartInstance = new Chart(toxCanvas, {
      type: prefs.type,
      data: { labels, datasets: [_seriesDataset("Toxic %", tox, "#ef4444")] },
      options: _chartOptions({ reverseY: false, beginAtZero: true, yMin: 0, yMax: 100 }),
    });
  }
}

async function loadAnchorAnalysis() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const payload = await _fetchJson(`/api/links/anchors?site_id=${encodeURIComponent(String(siteId))}&limit=50`);
  renderAnchorAnalysis(payload);
}

async function loadTopPages() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const payload = await _fetchJson(`/api/links/top-pages?site_id=${encodeURIComponent(String(siteId))}&limit=20`);
  const body = document.getElementById("top-pages-body");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!body) return;
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((r) => {
      return `
        <tr>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.target_url ?? ""))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.count ?? ""))}</td>
        </tr>
      `;
    })
    .join("");
}

async function loadBrokenLinks() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const payload = await _fetchJson(`/api/links/broken?site_id=${encodeURIComponent(String(siteId))}&limit=200`);
  const body = document.getElementById("broken-links-body");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!body) return;
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="3" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .slice(0, 50)
    .map((r) => {
      const last = r.last_checked ? String(r.last_checked).slice(0, 19).replace("T", " ") : "—";
      return `
        <tr>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.source_url ?? ""))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.http_status ?? "—"))}</td>
          <td class="px-4 py-2 text-gray-600">${escapeHtml(last)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderAnchorAnalysis(payload) {
  _chartCache.anchor = payload;
  const total = Number(payload?.total ?? 0);
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const values = Array.isArray(payload?.values) ? payload.values : [];
  const prefs = getChartPrefs();

  const totalEl = document.getElementById("anchors-total");
  if (totalEl) totalEl.textContent = `всего анкоров: ${total}`;

  const tbody = document.getElementById("anchors-body");
  if (tbody) {
    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    } else {
      tbody.innerHTML = items
        .slice(0, 30)
        .map((r) => {
          return `
            <tr>
              <td class="px-4 py-2 break-all">${escapeHtml(String(r.anchor ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.count ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.pct ?? ""))}</td>
            </tr>
          `;
        })
        .join("");
    }
  }

  const canvas = document.getElementById("links-anchors-chart");
  if (canvas && window.Chart) {
    if (linksAnchorsChartInstance) linksAnchorsChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(canvas, "Нет данных");
      linksAnchorsChartInstance = null;
      return;
    }
    linksAnchorsChartInstance = new Chart(canvas, {
      type: prefs.type,
      data: { labels: labels.slice(0, 12), datasets: [_seriesDataset("Топ анкоры", values.slice(0, 12), "#10b981")] },
      options: _chartOptions({ reverseY: false, beginAtZero: true }),
    });
  }
}

async function refreshLinks() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const el = document.getElementById("links-action-result");
  try {
    const r = await _fetchJson(`/api/links/refresh?site_id=${encodeURIComponent(String(siteId))}`, { method: "POST" });
    if (el) el.textContent = `Обновление запущено (task #${r?.task_id ?? "?"}).`;
    if (r?.task_id) pollTaskStatus(Number(r.task_id), `Обновление ссылок`, "links-action-result");
  } catch (e) {
    if (el) el.textContent = String(e?.message ?? e);
  }
}

async function refreshLinksAhrefs() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const el = document.getElementById("links-action-result");
  try {
    const r = await _fetchJson(`/api/links/refresh-ahrefs?site_id=${encodeURIComponent(String(siteId))}&limit=200`, {
      method: "POST",
    });
    if (el) el.textContent = `Обновление из Ahrefs запущено (task #${r?.task_id ?? "?"}).`;
    if (r?.task_id) pollTaskStatus(Number(r.task_id), "Обновление из Ahrefs", "links-action-result");
    await loadAhrefsHistory();
  } catch (e) {
    if (el) el.textContent = String(e?.message ?? e);
  }
}

async function analyzeLinks() {
  const siteId = _selectedLinksSiteId();
  if (!siteId) return;
  const el = document.getElementById("links-action-result");
  try {
    const r = await _fetchJson(`/api/links/analyze?site_id=${encodeURIComponent(String(siteId))}&limit=300`, { method: "POST" });
    if (el) el.textContent = `Анализ запущен (task #${r?.task_id ?? "?"}).`;
    if (r?.task_id) pollTaskStatus(Number(r.task_id), `Анализ ссылок`, "links-action-result");
  } catch (e) {
    if (el) el.textContent = String(e?.message ?? e);
  }
}

function triggerLinksImport() {
  openLinksImportModal();
}

async function importLinksCsvFile(file) {
  const siteId = _selectedLinksSiteId();
  if (!siteId || !file) return;
  const el = document.getElementById("links-action-result");
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch(`/api/links/import-csv?site_id=${encodeURIComponent(String(siteId))}`, { method: "POST", body: fd });
    const json = safeJsonParse(await resp.text());
    if (!resp.ok) throw new Error(json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`);
    if (el) el.textContent = `Импортировано: ${json?.imported_count ?? 0}${json?.errors?.length ? `, ошибки: ${json.errors.length}` : ""}`;
    await reloadLinks();
  } catch (e) {
    if (el) el.textContent = String(e?.message ?? e);
  }
}

function openLinksImportModal() {
  const modal = document.getElementById("links-import-modal");
  const resEl = document.getElementById("links-import-result");
  if (!modal) return;
  modal.classList.remove("hidden");
  if (resEl) resEl.textContent = "";
  setLinksImportTab("csv");
}

function closeLinksImportModal() {
  const modal = document.getElementById("links-import-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

function setLinksImportTab(tab) {
  const t = String(tab || "csv");
  const btnCsv = document.getElementById("links-import-tab-csv");
  const btnText = document.getElementById("links-import-tab-text");
  const btnManual = document.getElementById("links-import-tab-manual");
  const paneCsv = document.getElementById("links-import-pane-csv");
  const paneText = document.getElementById("links-import-pane-text");
  const paneManual = document.getElementById("links-import-pane-manual");

  const on = "bg-indigo-600 text-white";
  const off = "bg-white border border-gray-300 text-gray-800";

  if (btnCsv) btnCsv.className = `${t === "csv" ? on : off} px-3 py-2 rounded-md hover:bg-indigo-700 transition text-sm`;
  if (btnText) btnText.className = `${t === "text" ? on : off} px-3 py-2 rounded-md hover:bg-gray-50 transition text-sm`;
  if (btnManual) btnManual.className = `${t === "manual" ? on : off} px-3 py-2 rounded-md hover:bg-gray-50 transition text-sm`;

  if (paneCsv) paneCsv.classList.toggle("hidden", t !== "csv");
  if (paneText) paneText.classList.toggle("hidden", t !== "text");
  if (paneManual) paneManual.classList.toggle("hidden", t !== "manual");
}

async function importLinksCsvFromModal() {
  const input = document.getElementById("backlinks-csv");
  const resEl = document.getElementById("links-import-result");
  const file = input?.files?.[0];
  if (!file) return;
  if (resEl) resEl.textContent = "Импорт CSV…";
  await importLinksCsvFile(file);
  if (resEl) resEl.textContent = "Готово.";
  input.value = "";
}

async function importLinksText() {
  const siteId = _selectedLinksSiteId();
  const txtEl = document.getElementById("backlinks-text");
  const resEl = document.getElementById("links-import-result");
  const text = (txtEl?.value || "").toString();
  if (!siteId || !text.trim()) return;
  try {
    if (resEl) resEl.textContent = "Импорт текста…";
    const payload = await _fetchJson(`/api/links/import-text?site_id=${encodeURIComponent(String(siteId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ text }),
    });
    if (resEl) resEl.textContent = `Импортировано: ${payload?.imported_count ?? 0}${payload?.errors?.length ? `, ошибки: ${payload.errors.length}` : ""}`;
    await reloadLinks();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function addLinkManual() {
  const siteId = _selectedLinksSiteId();
  const resEl = document.getElementById("links-import-result");
  const src = (document.getElementById("backlink-manual-source")?.value || "").toString().trim();
  const tgt = (document.getElementById("backlink-manual-target")?.value || "").toString().trim();
  const anchor = (document.getElementById("backlink-manual-anchor")?.value || "").toString().trim();
  const lt = (document.getElementById("backlink-manual-type")?.value || "").toString().trim();
  const drRaw = (document.getElementById("backlink-manual-dr")?.value || "").toString().trim();
  const domainScore = drRaw ? Number(drRaw) : null;
  if (!siteId || !src || !tgt) return;
  try {
    if (resEl) resEl.textContent = "Добавляю ссылку…";
    await _fetchJson(`/api/links/add?site_id=${encodeURIComponent(String(siteId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ source_url: src, target_url: tgt, anchor: anchor || null, link_type: lt || null, domain_score: Number.isFinite(domainScore) ? domainScore : null }),
    });
    if (resEl) resEl.textContent = "Ссылка добавлена.";
    await reloadLinks();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function clearLinks(mode) {
  const siteId = _selectedLinksSiteId();
  const resEl = document.getElementById("links-import-result");
  const m = (mode || "all").toString();
  if (!siteId) return;
  const ok = window.prompt("Подтверждение удаления. Введите DELETE:", "");
  if (ok !== "DELETE") return;
  try {
    if (resEl) resEl.textContent = "Удаление…";
    const payload = await _fetchJson(
      `/api/links/clear?site_id=${encodeURIComponent(String(siteId))}&mode=${encodeURIComponent(m)}&confirm=DELETE`,
      { method: "POST" }
    );
    if (resEl) resEl.textContent = `Удалено: ${payload?.deleted ?? 0}`;
    await reloadLinks();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

let _purchasedAutoTimer = null;
let _purchasedHistoryChart = null;
let _purchasedSelectedHistoryId = null;

function _selectedPurchasedSiteId() {
  const el = document.getElementById("purchased-site-select");
  const val = el?.value ? Number(el.value) : null;
  if (val) return val;
  const saved = localStorage.getItem("selected_site_id");
  return saved ? Number(saved) : null;
}

async function loadPurchasedLinksSites() {
  const selectEl = document.getElementById("purchased-site-select");
  if (!selectEl) return;
  const resEl = document.getElementById("purchased-action-result");
  try {
    const sites = await _fetchJson("/api/sites/");
    const list = Array.isArray(sites) ? sites : [];
    const saved = localStorage.getItem("selected_site_id") || "";
    selectEl.innerHTML = ['<option value="">Выберите сайт…</option>']
      .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
      .join("");
    if (saved && list.some((s) => String(s.id) === String(saved))) {
      selectEl.value = String(saved);
    } else if (list.length) {
      selectEl.value = String(list[0].id);
      localStorage.setItem("selected_site_id", String(list[0].id));
    }
  } catch (e) {
    selectEl.innerHTML = '<option value="">Ошибка загрузки сайтов</option>';
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

function renderPurchasedLinksTable(items) {
  const body = document.getElementById("purchased-links-body");
  if (!body) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    body.innerHTML = '<tr><td colspan="10" class="px-6 py-10 text-center text-gray-400">Нет купленных ссылок</td></tr>';
    return;
  }
  body.innerHTML = list
    .map((b) => {
      const st = (b.status || "").toString().toLowerCase();
      const stBadge =
        st === "active"
          ? _badge("активна", "bg-emerald-100 text-emerald-700")
          : st === "lost"
          ? _badge("потеряна", "bg-amber-100 text-amber-700")
          : st === "broken"
          ? _badge("битая", "bg-rose-100 text-rose-700")
          : _badge("—", "bg-gray-200 text-gray-800");
      const tf = (b.toxic_flag || "").toString();
      const toxBadge =
        tf === "toxic"
          ? _badge("toxic", "bg-rose-100 text-rose-700")
          : tf === "suspicious"
          ? _badge("suspicious", "bg-amber-100 text-amber-700")
          : tf === "safe"
          ? _badge("safe", "bg-emerald-100 text-emerald-700")
          : _badge("—", "bg-gray-200 text-gray-800");
      const last = (b.last_checked || "").toString().slice(0, 19).replace("T", " ");
      const http = b.http_status ?? "—";
      const dr = b.domain_score ?? "—";
      return `<tr>
        <td class="px-6 py-3 break-all text-indigo-700"><a href="${escapeHtml(String(b.source_url || ""))}" target="_blank" class="hover:underline">${escapeHtml(String(b.source_url || ""))}</a></td>
        <td class="px-6 py-3 break-all">${escapeHtml(String(b.target_url || ""))}</td>
        <td class="px-6 py-3">${escapeHtml(String(b.anchor || "—"))}</td>
        <td class="px-6 py-3">${escapeHtml(String(b.link_type || "—"))}</td>
        <td class="px-6 py-3">${stBadge}</td>
        <td class="px-6 py-3">${escapeHtml(String(http))}</td>
        <td class="px-6 py-3">${escapeHtml(String(dr))}</td>
        <td class="px-6 py-3">${toxBadge}</td>
        <td class="px-6 py-3 text-xs text-gray-500">${escapeHtml(String(last || "—"))}</td>
        <td class="px-6 py-3"><button class="text-sm text-indigo-700 hover:underline" onclick="openPurchasedHistory(${Number(b.id)})">Открыть</button></td>
      </tr>`;
    })
    .join("");
}

async function reloadPurchasedLinks() {
  const siteId = _selectedPurchasedSiteId();
  const body = document.getElementById("purchased-links-body");
  if (!siteId) {
    if (body) body.innerHTML = '<tr><td colspan="10" class="px-6 py-10 text-center text-gray-400">Выберите сайт</td></tr>';
    return;
  }
  const params = new URLSearchParams();
  params.set("site_id", String(siteId));
  const items = await _fetchJson(`/api/purchased-links?${params.toString()}`);
  renderPurchasedLinksTable(items);
}

function _renderPurchasedAutoBtn() {
  const btn = document.getElementById("purchased-auto-btn");
  if (!btn) return;
  const on = localStorage.getItem("purchased_auto") === "1";
  btn.textContent = on ? "Авто-мониторинг: вкл" : "Авто-мониторинг: выкл";
  btn.className = on
    ? "bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-black transition text-sm"
    : "bg-white border border-gray-300 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-50 transition text-sm";
}

function togglePurchasedAuto() {
  const on = localStorage.getItem("purchased_auto") === "1";
  localStorage.setItem("purchased_auto", on ? "0" : "1");
  _renderPurchasedAutoBtn();
  _resetPurchasedAutoTimer();
}

function _resetPurchasedAutoTimer() {
  if (_purchasedAutoTimer) clearInterval(_purchasedAutoTimer);
  _purchasedAutoTimer = null;
  const on = localStorage.getItem("purchased_auto") === "1";
  if (!on) return;
  _purchasedAutoTimer = setInterval(() => monitorPurchasedLinksNow(true), 10 * 60 * 1000);
}

function openPurchasedAddModal() {
  const modal = document.getElementById("purchased-add-modal");
  const res = document.getElementById("purchased-add-result");
  if (!modal) return;
  const siteId = _selectedPurchasedSiteId();
  if (!siteId) {
    const out = document.getElementById("purchased-action-result");
    if (out) out.textContent = "Сначала выберите сайт.";
    return;
  }
  modal.classList.remove("hidden");
  if (res) res.textContent = "";
}

function closePurchasedAddModal() {
  const modal = document.getElementById("purchased-add-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

async function submitPurchasedAdd() {
  const siteId = _selectedPurchasedSiteId();
  const res = document.getElementById("purchased-add-result");
  if (!siteId) {
    if (res) res.textContent = "Сначала выберите сайт.";
    return;
  }
  const src = (document.getElementById("purchased-add-source")?.value || "").toString().trim();
  const tgt = (document.getElementById("purchased-add-target")?.value || "").toString().trim();
  const anchor = (document.getElementById("purchased-add-anchor")?.value || "").toString().trim();
  const lt = (document.getElementById("purchased-add-type")?.value || "").toString().trim();
  const drRaw = (document.getElementById("purchased-add-dr")?.value || "").toString().trim();
  const dr = drRaw ? Number(drRaw) : null;
  if (!src) return;
  try {
    if (res) res.textContent = "Сохраняю…";
    await _fetchJson(`/api/purchased-links/add?site_id=${encodeURIComponent(String(siteId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        source_url: src,
        target_url: tgt || null,
        anchor: anchor || null,
        link_type: lt || null,
        domain_score: Number.isFinite(dr) ? dr : null,
      }),
    });
    if (res) res.textContent = "Добавлено.";
    await reloadPurchasedLinks();
  } catch (e) {
    if (res) res.textContent = String(e?.message ?? e);
  }
}

async function monitorPurchasedLinksNow(silent) {
  const siteId = _selectedPurchasedSiteId();
  const resEl = document.getElementById("purchased-action-result");
  if (!siteId) {
    if (resEl) resEl.textContent = "Сначала выберите сайт.";
    return;
  }
  try {
    if (!silent && resEl) resEl.textContent = "Запускаю проверку…";
    const r = await _fetchJson(`/api/purchased-links/monitor?site_id=${encodeURIComponent(String(siteId))}&limit=80`, { method: "POST" });
    if (!silent && resEl) resEl.textContent = `Проверка запущена (task #${r?.task_id ?? "?"}).`;
    if (r?.task_id) pollTaskStatus(Number(r.task_id), "Мониторинг купленных ссылок", "purchased-action-result");
    setTimeout(() => reloadPurchasedLinks(), 1200);
  } catch (e) {
    if (!silent && resEl) resEl.textContent = String(e?.message ?? e);
  }
}

function openPurchasedHistory(backlinkId) {
  _purchasedSelectedHistoryId = Number(backlinkId);
  const modal = document.getElementById("purchased-history-modal");
  const body = document.getElementById("purchased-history-body");
  const sub = document.getElementById("purchased-history-subtitle");
  if (!modal || !body) return;
  modal.classList.remove("hidden");
  body.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>';
  if (sub) sub.textContent = `ID: ${backlinkId}`;
  loadPurchasedHistoryData();
}

function closePurchasedHistory() {
  const modal = document.getElementById("purchased-history-modal");
  if (!modal) return;
  modal.classList.add("hidden");
  if (_purchasedHistoryChart) {
    _purchasedHistoryChart.destroy();
    _purchasedHistoryChart = null;
  }
}

async function loadPurchasedHistoryData() {
  const backlinkId = _purchasedSelectedHistoryId;
  const body = document.getElementById("purchased-history-body");
  const chartEl = document.getElementById("purchased-history-chart");
  const resEl = document.getElementById("purchased-history-result");
  if (!backlinkId || !body || !chartEl || !window.Chart) return;
  try {
    const payload = await _fetchJson(`/api/purchased-links/history?backlink_id=${encodeURIComponent(String(backlinkId))}&limit=200`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
      if (resEl) resEl.textContent = "";
      return;
    }
    const rows = items.slice().reverse();
    const labels = rows.map((r) => (r.checked_at || "").toString().slice(0, 19).replace("T", " "));
    const dr = rows.map((r) => (r.domain_score === null || r.domain_score === undefined ? null : Number(r.domain_score)));
    const tox = rows.map((r) => (r.toxic_score === null || r.toxic_score === undefined ? null : Number(r.toxic_score)));
    if (_purchasedHistoryChart) _purchasedHistoryChart.destroy();
    _purchasedHistoryChart = new Chart(chartEl, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "DR", data: dr, borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.15)", tension: 0.25 },
          { label: "Toxic", data: tox, borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.12)", tension: 0.25 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { beginAtZero: true, suggestedMax: 100 } },
      },
    });

    body.innerHTML = items
      .slice(0, 50)
      .map((r) => {
        const dt = (r.checked_at || "").toString().slice(0, 19).replace("T", " ");
        return `<tr>
          <td class="px-4 py-2 text-gray-600">${escapeHtml(dt || "—")}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.status || "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.http_status ?? "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.domain_score ?? "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.toxic_flag ?? "—"))}</td>
        </tr>`;
      })
      .join("");
    if (resEl) resEl.textContent = "";
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
    body.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center text-rose-700">Ошибка загрузки</td></tr>';
  }
}

async function initPurchasedLinksPage() {
  const selectEl = document.getElementById("purchased-site-select");
  if (!selectEl) return;
  await loadPurchasedLinksSites();
  _renderPurchasedAutoBtn();
  _resetPurchasedAutoTimer();
  selectEl.addEventListener("change", () => {
    if (selectEl.value) localStorage.setItem("selected_site_id", String(selectEl.value));
    reloadPurchasedLinks();
  });
  await reloadPurchasedLinks();
}

let _linksReloadTimer = null;
function _debouncedReloadLinks() {
  if (_linksReloadTimer) clearTimeout(_linksReloadTimer);
  _linksReloadTimer = setTimeout(() => reloadLinks(), 250);
}

async function initLinksPage() {
  const selectEl = document.getElementById("links-site-select");
  if (!selectEl) return;

  await loadLinksSites();
  const compareEl = document.getElementById("links-compare-filter");
  const typeEl = document.getElementById("links-type-filter");
  const toxicEl = document.getElementById("links-toxic-filter");
  const qEl = document.getElementById("links-q");
  const csvEl = document.getElementById("backlinks-csv");

  const savedCompare = localStorage.getItem("links_compare") || "";
  if (compareEl && savedCompare && !compareEl.value) compareEl.value = savedCompare;
  const savedType = localStorage.getItem("links_type") || "";
  if (typeEl && savedType && !typeEl.value) typeEl.value = savedType;
  const savedToxic = localStorage.getItem("links_toxic") || "";
  if (toxicEl && savedToxic && !toxicEl.value) toxicEl.value = savedToxic;

  selectEl.addEventListener("change", () => {
    if (selectEl.value) localStorage.setItem("selected_site_id", String(selectEl.value));
    reloadLinks();
    loadLinksLastAnalyzed();
  });
  compareEl?.addEventListener("change", () => {
    localStorage.setItem("links_compare", String(compareEl.value || ""));
    reloadLinks();
  });
  typeEl?.addEventListener("change", () => {
    localStorage.setItem("links_type", String(typeEl.value || ""));
    reloadLinks();
  });
  toxicEl?.addEventListener("change", () => {
    localStorage.setItem("links_toxic", String(toxicEl.value || ""));
    reloadLinks();
  });
  qEl?.addEventListener("input", _debouncedReloadLinks);
  csvEl?.addEventListener("change", () => {});

  await reloadLinks();
  await loadLinksLastAnalyzed();
}

async function loadLinksLastAnalyzed() {
  const siteId = _selectedLinksSiteId();
  const el = document.getElementById("links-last-analyzed");
  if (!el) return;
  if (!siteId) {
    el.textContent = "—";
    return;
  }
  try {
    const payload = await _fetchJson(`/api/links/last-analyzed?site_id=${encodeURIComponent(String(siteId))}`);
    const ts = (payload?.last_analyzed_at || "").toString().slice(0, 19).replace("T", " ");
    el.textContent = ts || "—";
  } catch {
    el.textContent = "—";
  }
}

async function loadIntegrations() {
  const body = document.getElementById("integrations-body");
  if (!body) return;
  const payload = await _fetchJson("/api/integrations");
  renderIntegrations(payload);
}

function renderIntegrations(payload) {
  const body = document.getElementById("integrations-body");
  if (!body) return;
  const items = Array.isArray(payload) ? payload : [];
  if (items.length === 0) {
    body.innerHTML = '<tr><td colspan="3" class="px-4 py-8 text-center text-gray-400">Нет сайтов</td></tr>';
    return;
  }

  body.innerHTML = items
    .map((r) => {
      const domain = r.domain ?? "";
      const gStatus = _badge("ручной ввод", "bg-gray-200 text-gray-800");
      const yStatus = _badge("ручной ввод", "bg-gray-200 text-gray-800");

      return `
        <tr>
          <td class="px-4 py-3 font-medium">${escapeHtml(String(domain))}</td>
          <td class="px-4 py-3 align-top">
            <div class="flex items-center justify-between mb-2">${gStatus}</div>
            <div class="text-xs text-gray-500">Данные добавляются вручную.</div>
          </td>
          <td class="px-4 py-3 align-top">
            <div class="flex items-center justify-between mb-2">${yStatus}</div>
            <div class="text-xs text-gray-500">Данные добавляются вручную.</div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadAiSettings() {
  const providerEl = document.getElementById("ai-provider");
  const modelEl = document.getElementById("ai-model");
  const statusEl = document.getElementById("ai-status");
  if (!providerEl || !modelEl) return;
  try {
    const cfg = await _fetchJson("/api/ai/config");
    const provider = (cfg?.provider || "auto").toString() || "auto";
    const model = (cfg?.model || "").toString();
    const effProvider = (cfg?.effective_provider || "").toString();
    const effModel = (cfg?.effective_model || "").toString();
    const ollama = cfg?.ollama || {};
    const models = Array.isArray(ollama?.models) ? ollama.models : [];

    providerEl.value = provider;
    modelEl.innerHTML = models.length
      ? models.map((m) => `<option value="${escapeHtml(String(m))}">${escapeHtml(String(m))}</option>`).join("")
      : '<option value="">(нет моделей)</option>';
    if (model) modelEl.value = model;

    const enabled = provider !== "off";
    modelEl.disabled = !enabled || (provider !== "ollama" && provider !== "auto");

    if (statusEl) {
      const parts = [];
      parts.push(`effective: ${effProvider || "off"}${effModel ? ` / ${effModel}` : ""}`);
      if (ollama?.available) parts.push(`ollama: OK (${models.length} моделей)`);
      else parts.push("ollama: не найден");
      statusEl.textContent = parts.join(" · ");
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = String(e?.message ?? e);
  }
}

async function saveAiSettings() {
  const providerEl = document.getElementById("ai-provider");
  const modelEl = document.getElementById("ai-model");
  const statusEl = document.getElementById("ai-status");
  if (!providerEl || !modelEl) return;
  try {
    await _fetchJson("/api/ai/config", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ provider: providerEl.value || "auto", model: modelEl.value || "" }),
    });
    if (statusEl) statusEl.textContent = "Сохранено.";
    await loadAiSettings();
  } catch (e) {
    if (statusEl) statusEl.textContent = String(e?.message ?? e);
  }
}

async function initAiWidget() {
  const providerEl = document.getElementById("ai-provider");
  const modelEl = document.getElementById("ai-model");
  if (!providerEl || !modelEl) return;
  await loadAiSettings();
  providerEl.addEventListener("change", () => {
    const p = (providerEl.value || "").toString();
    modelEl.disabled = p === "off" || (p !== "ollama" && p !== "auto");
  });
}

async function initIntegrationsPage() {
  const body = document.getElementById("integrations-body");
  if (!body) return;
  await loadIntegrations();
  await loadAiSettings();
}

async function loadUsers() {
  const body = document.getElementById("users-body");
  if (!body) return;
  const payload = await _fetchJson("/api/users");
  renderUsers(payload);
}

function renderUsers(payload) {
  const body = document.getElementById("users-body");
  if (!body) return;
  const items = Array.isArray(payload) ? payload : [];
  if (items.length === 0) {
    body.innerHTML = '<tr><td colspan="5" class="px-6 py-10 text-center text-gray-400">Нет пользователей</td></tr>';
    return;
  }

  body.innerHTML = items
    .map((u) => {
      const id = u.id;
      const username = u.username ?? "";
      const role = u.role ?? "viewer";
      const isActive = u.is_active !== false;
      const createdAt = (u.created_at ?? "").toString().slice(0, 19).replace("T", " ");
      return `
        <tr>
          <td class="px-6 py-3 font-medium">${escapeHtml(String(username))}</td>
          <td class="px-6 py-3">
            <select id="user-role-${escapeHtml(String(id))}" class="rounded-md border-gray-300 text-sm p-2 border">
              <option value="viewer" ${role === "viewer" ? "selected" : ""}>viewer</option>
              <option value="manager" ${role === "manager" ? "selected" : ""}>manager</option>
              <option value="admin" ${role === "admin" ? "selected" : ""}>admin</option>
            </select>
          </td>
          <td class="px-6 py-3">
            <select id="user-active-${escapeHtml(String(id))}" class="rounded-md border-gray-300 text-sm p-2 border">
              <option value="true" ${isActive ? "selected" : ""}>да</option>
              <option value="false" ${!isActive ? "selected" : ""}>нет</option>
            </select>
          </td>
          <td class="px-6 py-3 text-gray-600">${escapeHtml(createdAt || "—")}</td>
          <td class="px-6 py-3 text-right space-x-3">
            <button class="text-indigo-700 hover:underline text-sm" onclick="saveUser(${Number(id)})">Сохранить</button>
            <button class="text-red-600 hover:underline text-sm" onclick="deleteUser(${Number(id)})">Удалить</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function createUserFromForm() {
  const uEl = document.getElementById("user-new-username");
  const pEl = document.getElementById("user-new-password");
  const rEl = document.getElementById("user-new-role");
  const resEl = document.getElementById("users-result");
  const username = (uEl?.value || "").toString();
  const password = (pEl?.value || "").toString();
  const role = (rEl?.value || "viewer").toString();
  try {
    await _fetchJson("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ username, password, role }),
    });
    if (resEl) resEl.textContent = "Пользователь создан.";
    if (uEl) uEl.value = "";
    if (pEl) pEl.value = "";
    await loadUsers();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function saveUser(userId) {
  const roleEl = document.getElementById(`user-role-${userId}`);
  const activeEl = document.getElementById(`user-active-${userId}`);
  const resEl = document.getElementById("users-result");
  const role = (roleEl?.value || "").toString();
  const is_active = (activeEl?.value || "true").toString() === "true";
  try {
    await _fetchJson(`/api/users/${encodeURIComponent(String(userId))}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ role, is_active }),
    });
    if (resEl) resEl.textContent = "Сохранено.";
    await loadUsers();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function deleteUser(userId) {
  const resEl = document.getElementById("users-result");
  try {
    await _fetchJson(`/api/users/${encodeURIComponent(String(userId))}`, { method: "DELETE" });
    if (resEl) resEl.textContent = "Удалено.";
    await loadUsers();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function initUsersPage() {
  const body = document.getElementById("users-body");
  if (!body) return;
  await loadUsers();
}

async function loadDomainAnalysis() {
  const domainEl = document.getElementById("da-domain");
  if (!domainEl) return;
  const path = window.location.pathname || "";
  const prefix = "/domain-analysis/";
  const domain = path.startsWith(prefix) ? decodeURIComponent(path.slice(prefix.length)) : "";
  if (!domain) return;

  domainEl.textContent = domain;
  const payload = await _fetchJson(`/api/domain-analysis/${encodeURIComponent(domain)}`);
  renderDomainAnalysis(payload);
}

function renderDomainAnalysis(payload) {
  setText("da-dr", payload?.dr);
  setText("da-backlinks", payload?.backlinks);
  setText("da-refdomains", payload?.referring_domains);

  const regionsEl = document.getElementById("da-regions");
  const regions = Array.isArray(payload?.regions) ? payload.regions : [];
  if (regionsEl) {
    if (!regions.length) regionsEl.textContent = "—";
    else regionsEl.textContent = regions.map((r) => `${r.region}: ${r.count}`).join(", ");
  }

  const tbody = document.getElementById("da-anchors-body");
  const anchors = Array.isArray(payload?.top_anchors) ? payload.top_anchors : [];
  if (tbody) {
    if (!anchors.length) {
      tbody.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    } else {
      tbody.innerHTML = anchors
        .map(
          (a) => `
          <tr>
            <td class="px-4 py-2 break-all">${escapeHtml(String(a.anchor ?? ""))}</td>
            <td class="px-4 py-2">${escapeHtml(String(a.count ?? ""))}</td>
          </tr>
        `
        )
        .join("");
    }
  }
}

let ilDepthChartInstance = null;

async function loadInternalLinks() {
  const domainEl = document.getElementById("da-domain");
  if (!domainEl) return;
  const domain = (domainEl.textContent || "").toString();
  if (!domain || domain === "—") return;
  const payload = await _fetchJson(`/api/domain-analysis/${encodeURIComponent(domain)}/internal-links`);
  renderInternalLinks(payload);
}

function renderInternalLinks(payload) {
  _chartCache.internalLinks = payload;
  const summaryEl = document.getElementById("il-summary");
  if (summaryEl) {
    if (!payload?.ok) summaryEl.textContent = payload?.detail ? String(payload.detail) : "Нет данных";
    else
      summaryEl.textContent = `HTTP ${payload.http_status ?? "—"}, internal links: ${payload.internal_links_total ?? 0}, unique pages: ${
        payload.unique_pages ?? 0
      }`;
  }

  const topBody = document.getElementById("il-top-body");
  const top = Array.isArray(payload?.top_pages) ? payload.top_pages : [];
  if (topBody) {
    if (!top.length) {
      topBody.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    } else {
      topBody.innerHTML = top
        .slice(0, 25)
        .map((r) => {
          return `
            <tr>
              <td class="px-4 py-2 break-all">${escapeHtml(String(r.path ?? ""))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.count ?? ""))}</td>
            </tr>
          `;
        })
        .join("");
    }
  }

  const depth = Array.isArray(payload?.depth_hist) ? payload.depth_hist : [];
  const labels = depth.map((r) => String(r.depth ?? ""));
  const values = depth.map((r) => Number(r.count ?? 0));
  const canvas = document.getElementById("il-depth-chart");
  if (canvas && window.Chart) {
    if (ilDepthChartInstance) ilDepthChartInstance.destroy();
    if (!labels.length) {
      drawCanvasMessage(canvas, "Нет данных");
      ilDepthChartInstance = null;
      return;
    }
    const prefs = getChartPrefs();
    ilDepthChartInstance = new Chart(canvas, {
      type: prefs.type,
      data: { labels, datasets: [_seriesDataset("Глубина (по / в URL)", values, "#0ea5e9")] },
      options: _chartOptions({ reverseY: false, beginAtZero: true }),
    });
  }
}

async function initDomainAnalysisPage() {
  const domainEl = document.getElementById("da-domain");
  if (!domainEl) return;
  await loadDomainAnalysis();
  await loadInternalLinks();
}

let _notifMenuOpen = false;
let _notifTimer = null;

function toggleNotifications() {
  const menu = document.getElementById("notif-menu");
  if (!menu) return;
  _notifMenuOpen = !_notifMenuOpen;
  if (_notifMenuOpen) {
    menu.classList.remove("hidden");
    loadNotifications();
  } else {
    menu.classList.add("hidden");
  }
}

async function loadNotifications() {
  const itemsEl = document.getElementById("notif-items");
  const countEl = document.getElementById("notif-count");
  if (!itemsEl || !countEl) return;
  try {
    const items = await _fetchJson("/api/notifications/recent?limit=20");
    const list = Array.isArray(items) ? items : [];
    const unseen = list.filter((x) => x && x.seen === false).length;
    if (unseen > 0) {
      countEl.textContent = String(unseen);
      countEl.classList.remove("hidden");
    } else {
      countEl.textContent = "0";
      countEl.classList.add("hidden");
    }

    if (list.length === 0) {
      itemsEl.innerHTML = '<div class="px-4 py-4 text-sm text-gray-500">Нет событий</div>';
      return;
    }

    itemsEl.innerHTML = list
      .map((e) => {
        const sev = String(e.severity ?? "info").toLowerCase();
        const badge =
          sev === "error"
            ? _badge("error", "bg-rose-100 text-rose-700")
            : sev === "warning"
            ? _badge("warning", "bg-amber-100 text-amber-700")
            : _badge("info", "bg-gray-200 text-gray-800");
        const msg = e.message ?? "";
        const ts = (e.created_at ?? "").toString().slice(0, 19).replace("T", " ");
        const seen = e.seen === true;
        return `
          <div class="px-4 py-3 border-b ${seen ? "bg-white" : "bg-indigo-50"}">
            <div class="flex items-center justify-between gap-3">
              <div class="text-xs text-gray-500">${escapeHtml(ts || "")}</div>
              <div class="flex items-center gap-2">
                ${badge}
                ${seen ? "" : `<button class="text-xs text-indigo-700 hover:underline" onclick="markNotificationSeen(${Number(
                  e.id
                )})">Прочитано</button>`}
              </div>
            </div>
            <div class="mt-1 text-sm text-gray-800">${escapeHtml(String(msg))}</div>
          </div>
        `;
      })
      .join("");
  } catch {
    itemsEl.innerHTML = '<div class="px-4 py-4 text-sm text-gray-500">Не удалось загрузить события</div>';
  }
}

async function markNotificationSeen(eventId) {
  try {
    await _fetchJson(`/api/notifications/${encodeURIComponent(String(eventId))}/seen`, { method: "POST" });
    await loadNotifications();
  } catch {
    return;
  }
}

function _startNotificationsPoll() {
  const countEl = document.getElementById("notif-count");
  const hasBell = Boolean(document.getElementById("notif-btn")) && Boolean(document.getElementById("notif-menu"));
  if (!hasBell || !countEl) return;
  if (_notifTimer) clearInterval(_notifTimer);
  _notifTimer = setInterval(() => loadNotifications(), 30000);
  loadNotifications();
}

async function loadRecommendations() {
  const domainEl = document.getElementById("rec-domain");
  const itemsEl = document.getElementById("rec-items");
  if (!itemsEl) return;
  const path = window.location.pathname || "";
  const prefix = "/recommendations/";
  const siteId = path.startsWith(prefix) ? Number(path.slice(prefix.length)) : null;
  if (!siteId) return;
  const payload = await _fetchJson(`/api/recommendations/${encodeURIComponent(String(siteId))}`);
  if (domainEl) domainEl.textContent = payload?.domain ?? "—";
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    itemsEl.innerHTML = '<div class="text-sm text-gray-500">Рекомендаций пока нет.</div>';
    return;
  }
  itemsEl.innerHTML = items
    .map((r) => {
      const p = String(r.priority ?? "low").toLowerCase();
      const badge =
        p === "high"
          ? _badge("high", "bg-rose-100 text-rose-700")
          : p === "medium"
          ? _badge("medium", "bg-amber-100 text-amber-700")
          : _badge("low", "bg-gray-200 text-gray-800");
      return `
        <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div class="flex items-center justify-between">
            <div class="font-semibold">${escapeHtml(String(r.title ?? ""))}</div>
            ${badge}
          </div>
          <div class="mt-2 text-sm text-gray-700">${escapeHtml(String(r.what_to_do ?? ""))}</div>
        </div>
      `;
    })
    .join("");
}

async function initRecommendationsPage() {
  const itemsEl = document.getElementById("rec-items");
  if (!itemsEl) return;
  await loadRecommendations();
}

async function loadNotes() {
  const body = document.getElementById("notes-body");
  if (!body) return;
  const statusEl = document.getElementById("notes-status-filter");
  const status = (statusEl?.value || "").toString();
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const payload = await _fetchJson(`/api/notes${qs}`);
  renderNotes(payload);
}

function noteStatusLabel(status) {
  const s = String(status || "").toLowerCase();
  if (s === "todo") return "К выполнению";
  if (s === "in_progress") return "В работе";
  if (s === "done") return "Завершено";
  return s || "—";
}

function noteColorBadge(color) {
  const c = String(color || "gray").toLowerCase();
  if (c === "yellow") return _badge("Жёлтый", "bg-amber-100 text-amber-700");
  if (c === "green") return _badge("Зелёный", "bg-emerald-100 text-emerald-700");
  if (c === "red") return _badge("Красный", "bg-rose-100 text-rose-700");
  return _badge("Серый", "bg-gray-200 text-gray-800");
}

function renderNotes(payload) {
  const body = document.getElementById("notes-body");
  if (!body) return;
  const items = Array.isArray(payload) ? payload : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="5" class="px-6 py-10 text-center text-gray-400">Нет заметок</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((n) => {
      const created = (n.created_at ?? "").toString().slice(0, 19).replace("T", " ");
      return `
        <tr>
          <td class="px-6 py-3">
            <div class="font-medium">${escapeHtml(String(n.title ?? ""))}</div>
            <div class="text-sm text-gray-600 mt-1">${escapeHtml(String(n.content ?? ""))}</div>
          </td>
          <td class="px-6 py-3">${escapeHtml(noteStatusLabel(n.status))}</td>
          <td class="px-6 py-3">${noteColorBadge(n.color)}</td>
          <td class="px-6 py-3 text-gray-600">${escapeHtml(created || "—")}</td>
          <td class="px-6 py-3 text-right">
            <button class="text-red-600 hover:underline text-sm" onclick="deleteNote(${Number(n.id)})">Удалить</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function createNoteFromForm() {
  const titleEl = document.getElementById("note-title");
  const contentEl = document.getElementById("note-content");
  const statusEl = document.getElementById("note-status");
  const colorEl = document.getElementById("note-color");
  const resEl = document.getElementById("notes-result");
  const title = (titleEl?.value || "").toString();
  const content = (contentEl?.value || "").toString();
  const status = (statusEl?.value || "todo").toString();
  const color = (colorEl?.value || "gray").toString();
  try {
    await _fetchJson("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ title, content, status, color }),
    });
    if (resEl) resEl.textContent = "Заметка создана.";
    if (titleEl) titleEl.value = "";
    if (contentEl) contentEl.value = "";
    await loadNotes();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function deleteNote(noteId) {
  const resEl = document.getElementById("notes-result");
  try {
    await _fetchJson(`/api/notes/${encodeURIComponent(String(noteId))}`, { method: "DELETE" });
    if (resEl) resEl.textContent = "Удалено.";
    await loadNotes();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function initNotesPage() {
  const body = document.getElementById("notes-body");
  if (!body) return;
  await loadNotes();
}

async function loadKeywordsSites() {
  const selectEl = document.getElementById("keywords-site-select");
  if (!selectEl) return;
  const sites = await _fetchJson("/api/sites/");
  const list = Array.isArray(sites) ? sites : [];
  const saved = localStorage.getItem("selected_site_id") || "";
  selectEl.innerHTML = ['<option value="">Все сайты</option>']
    .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
    .join("");
  if (saved) selectEl.value = String(saved);
}

async function loadKeywords() {
  const body = document.getElementById("keywords-body");
  if (!body) return;
  const siteEl = document.getElementById("keywords-site-select");
  const qEl = document.getElementById("keywords-q");
  const siteId = (siteEl?.value || "").toString();
  const q = (qEl?.value || "").toString();
  const params = new URLSearchParams();
  if (siteId) params.set("site_id", siteId);
  if (q) params.set("q", q);
  const payload = await _fetchJson(`/api/keywords${params.toString() ? `?${params.toString()}` : ""}`);
  const items = Array.isArray(payload) ? payload : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="px-6 py-10 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((k) => {
      const dt = (k.date ?? "").toString().slice(0, 10);
      return `
        <tr>
          <td class="px-6 py-3">${escapeHtml(String(k.keyword ?? ""))}</td>
          <td class="px-6 py-3">${escapeHtml(String(k.position ?? "—"))}</td>
          <td class="px-6 py-3 break-all">${escapeHtml(String(k.url ?? "—"))}</td>
          <td class="px-6 py-3">${escapeHtml(String(k.frequency ?? "—"))}</td>
          <td class="px-6 py-3">${escapeHtml(String(k.source ?? ""))}</td>
          <td class="px-6 py-3">${escapeHtml(dt || "—")}</td>
          <td class="px-6 py-3 text-right"><button class="text-red-600 hover:underline text-sm" onclick="deleteKeyword(${Number(
            k.id
          )})">Удалить</button></td>
        </tr>
      `;
    })
    .join("");
}

async function createKeywordFromForm() {
  const siteEl = document.getElementById("keywords-site-select");
  const keywordEl = document.getElementById("kw-keyword");
  const positionEl = document.getElementById("kw-position");
  const urlEl = document.getElementById("kw-url");
  const freqEl = document.getElementById("kw-frequency");
  const resEl = document.getElementById("keywords-result");
  const site_id = Number(siteEl?.value || "");
  const keyword = (keywordEl?.value || "").toString();
  const positionRaw = (positionEl?.value || "").toString();
  const position = positionRaw ? Number(positionRaw) : null;
  const url = (urlEl?.value || "").toString();
  const frequencyRaw = (freqEl?.value || "").toString();
  const frequency = frequencyRaw ? Number(frequencyRaw) : null;
  if (!site_id) {
    if (resEl) resEl.textContent = "Выберите сайт.";
    return;
  }
  try {
    await _fetchJson("/api/keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ site_id, keyword, position, url, frequency, source: "manual" }),
    });
    if (resEl) resEl.textContent = "Ключ добавлен.";
    if (keywordEl) keywordEl.value = "";
    if (positionEl) positionEl.value = "";
    if (urlEl) urlEl.value = "";
    if (freqEl) freqEl.value = "";
    await loadKeywords();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function loadKeywordSuggestions() {
  const kwEl = document.getElementById("kw-keyword");
  const panel = document.getElementById("kw-suggest-panel");
  if (!kwEl || !panel) return;
  const q = (kwEl.value || "").toString().trim();
  const expandedEl = document.getElementById("kw-suggest-expanded");
  const mode = expandedEl?.checked ? "expanded" : "basic";
  if (!q) {
    panel.classList.remove("hidden");
    panel.innerHTML = '<div class="text-sm text-gray-500">Введите ключевое слово.</div>';
    return;
  }
  panel.classList.remove("hidden");
  panel.innerHTML = '<div class="text-sm text-gray-500">Загрузка подсказок…</div>';
  try {
    const payload = await _fetchJson(
      `/api/keywords/suggest?query=${encodeURIComponent(q)}&engines=google,yandex,bing,ddg&lang=ru&mode=${encodeURIComponent(
        mode
      )}&max_variants=30&max_per_engine=30`
    );
    const items = payload?.items || {};
    const variantsUsed = Number(payload?.meta?.variants_used ?? 0);
    const engines = [
      { key: "google", title: "Google" },
      { key: "yandex", title: "Яндекс" },
      { key: "bing", title: "Bing" },
      { key: "ddg", title: "DuckDuckGo" },
    ];
    const header = `<div class="flex items-center justify-between mb-3">
      <div class="text-xs font-semibold text-gray-500 uppercase">Подсказки (${escapeHtml(mode)})</div>
      <div class="text-xs text-gray-400">${variantsUsed ? `вариантов: ${variantsUsed}` : ""}</div>
    </div>`;
    const blocks = engines
      .map((e) => {
        const list = Array.isArray(items?.[e.key]) ? items[e.key] : [];
        const content = list.length
          ? `<div class="flex flex-wrap gap-2">${list
              .slice(0, 20)
              .map((s) => {
                const arg = escapeHtml(JSON.stringify(String(s)));
                return `<button type="button" class="px-3 py-1 rounded-full bg-white border border-gray-200 text-sm hover:bg-gray-50" onclick="setKeywordFromSuggestion(${arg})">${escapeHtml(
                  String(s)
                )}</button>`;
              })
              .join("")}</div>`
          : '<div class="text-sm text-gray-400">Нет подсказок</div>';
        return `<div class="space-y-2">
          <div class="text-xs font-semibold text-gray-500 uppercase">${escapeHtml(e.title)}</div>
          ${content}
        </div>`;
      })
      .join('<div class="h-px bg-gray-200 my-4"></div>');
    panel.innerHTML = header + blocks;
  } catch (e) {
    panel.innerHTML = `<div class="text-sm text-rose-700">${escapeHtml(String(e?.message ?? e))}</div>`;
  }
}

function setKeywordFromSuggestion(value) {
  const kwEl = document.getElementById("kw-keyword");
  if (!kwEl) return;
  kwEl.value = String(value || "");
  kwEl.focus();
}

async function deleteKeyword(keywordId) {
  const resEl = document.getElementById("keywords-result");
  try {
    await _fetchJson(`/api/keywords/${encodeURIComponent(String(keywordId))}`, { method: "DELETE" });
    if (resEl) resEl.textContent = "Удалено.";
    await loadKeywords();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function initKeywordsPage() {
  const body = document.getElementById("keywords-body");
  if (!body) return;
  await loadKeywordsSites();
  await loadKeywords();
  await loadKeywordsHistory();
  await loadCannibalization();
  await loadKeywordChanges();
  const siteEl = document.getElementById("keywords-site-select");
  const qEl = document.getElementById("keywords-q");
  const csvEl = document.getElementById("kw-csv");
  siteEl?.addEventListener("change", () => {
    localStorage.setItem("selected_site_id", String(siteEl.value || ""));
    loadKeywords();
    loadKeywordsHistory();
    loadCannibalization();
    loadKeywordChanges();
  });
  qEl?.addEventListener("input", () => {
    if (window._kwTimer) clearTimeout(window._kwTimer);
    window._kwTimer = setTimeout(() => loadKeywords(), 250);
  });
  csvEl?.addEventListener("change", (e) => {
    const f = e?.target?.files?.[0];
    importKeywordCsvFile(f);
    e.target.value = "";
  });
}

let keywordsHistoryChartInstance = null;

async function loadKeywordsHistory() {
  const canvas = document.getElementById("keywords-history-chart");
  if (!canvas || !window.Chart) return;
  const siteEl = document.getElementById("keywords-site-select");
  const siteId = Number(siteEl?.value || "");
  if (!siteId) {
    if (keywordsHistoryChartInstance) {
      keywordsHistoryChartInstance.destroy();
      keywordsHistoryChartInstance = null;
    }
    drawCanvasMessage(canvas, "Выберите сайт");
    return;
  }
  const payload = await _fetchJson(`/api/keywords/history?site_id=${encodeURIComponent(String(siteId))}&days=30`);
  renderKeywordsHistoryChart(payload);
}

function renderKeywordsHistoryChart(payload) {
  _chartCache.kwHistory = payload;
  const canvas = document.getElementById("keywords-history-chart");
  if (!canvas || !window.Chart) return;
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const values = Array.isArray(payload?.values) ? payload.values : [];
  const reverseY = payload?.reverse_y === false ? false : true;
  const label = payload?.label ? String(payload.label) : "Средняя позиция";
  if (keywordsHistoryChartInstance) keywordsHistoryChartInstance.destroy();
  if (!labels.length || !values.length) {
    keywordsHistoryChartInstance = null;
    drawCanvasMessage(canvas, "Нет данных");
    return;
  }
  const prefs = getChartPrefs();
  keywordsHistoryChartInstance = new Chart(canvas, {
    type: prefs.type,
    data: { labels, datasets: [_seriesDataset(label, values, "#6366f1")] },
    options: _chartOptions({ reverseY, beginAtZero: false }),
  });
}

async function loadCannibalization() {
  const body = document.getElementById("cannibal-body");
  if (!body) return;
  const siteEl = document.getElementById("keywords-site-select");
  const siteId = Number(siteEl?.value || "");
  if (!siteId) return;
  const payload = await _fetchJson(`/api/keywords/cannibalization?site_id=${encodeURIComponent(String(siteId))}&limit=50`);
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((r) => {
      return `
        <tr>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.keyword ?? ""))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.urls ?? ""))}</td>
        </tr>
      `;
    })
    .join("");
}

async function loadKeywordChanges() {
  const body = document.getElementById("kw-changes-body");
  if (!body) return;
  const siteEl = document.getElementById("keywords-site-select");
  const siteId = Number(siteEl?.value || "");
  if (!siteId) return;
  const payload = await _fetchJson(`/api/keywords/changes?site_id=${encodeURIComponent(String(siteId))}&limit=50`);
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="6" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((r) => {
      const delta = Number(r.delta ?? 0);
      const deltaBadge =
        delta > 0
          ? _badge(`+${delta}`, "bg-emerald-100 text-emerald-700")
          : delta < 0
          ? _badge(`${delta}`, "bg-rose-100 text-rose-700")
          : _badge("0", "bg-gray-200 text-gray-800");
      const dateLabel = r.current_date ? String(r.current_date).slice(0, 10) : "—";
      return `
        <tr>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.keyword ?? ""))}</td>
          <td class="px-4 py-2 break-all">${escapeHtml(String(r.url ?? "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.prev_position ?? "—"))}</td>
          <td class="px-4 py-2">${escapeHtml(String(r.current_position ?? "—"))}</td>
          <td class="px-4 py-2">${deltaBadge}</td>
          <td class="px-4 py-2 text-gray-600">${escapeHtml(dateLabel)}</td>
        </tr>
      `;
    })
    .join("");
}

function triggerKeywordImport() {
  const el = document.getElementById("kw-csv");
  if (!el) return;
  el.click();
}

async function importKeywordCsvFile(file) {
  const resEl = document.getElementById("keywords-result");
  const siteEl = document.getElementById("keywords-site-select");
  const siteId = Number(siteEl?.value || "");
  if (!file || !siteId) {
    if (resEl) resEl.textContent = "Выберите сайт и CSV файл.";
    return;
  }
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch(`/api/keywords/import-csv?site_id=${encodeURIComponent(String(siteId))}`, { method: "POST", body: fd });
    const json = safeJsonParse(await resp.text());
    if (!resp.ok) throw new Error(json?.detail ? translateDetail(String(json.detail)) : `Ошибка запроса: ${resp.status}`);
    if (resEl) resEl.textContent = `Импортировано: ${json?.imported ?? 0}${json?.errors?.length ? `, ошибки: ${json.errors.length}` : ""}`;
    await loadKeywords();
    await loadKeywordsHistory();
    await loadCannibalization();
    await loadKeywordChanges();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function loadLogs() {
  const body = document.getElementById("logs-body");
  if (!body) return;
  const level = (document.getElementById("logs-level")?.value || "").toString();
  const category = (document.getElementById("logs-category")?.value || "").toString();
  const hours = (document.getElementById("logs-hours")?.value || "24").toString();
  const params = new URLSearchParams();
  if (level) params.set("level", level);
  if (category) params.set("category", category);
  params.set("hours", hours || "24");
  params.set("limit", "500");
  const payload = await _fetchJson(`/api/logs?${params.toString()}`);
  const items = Array.isArray(payload) ? payload : [];
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="px-6 py-10 text-center text-gray-400">Нет логов</td></tr>';
    return;
  }
  body.innerHTML = items
    .map((r) => {
      const ts = (r.created_at ?? "").toString().slice(0, 19).replace("T", " ");
      return `
        <tr>
          <td class="px-6 py-3">${escapeHtml(ts || "—")}</td>
          <td class="px-6 py-3">${escapeHtml(String(r.level ?? ""))}</td>
          <td class="px-6 py-3">${escapeHtml(String(r.category ?? ""))}</td>
          <td class="px-6 py-3">${escapeHtml(String(r.method ?? ""))}</td>
          <td class="px-6 py-3 break-all">${escapeHtml(String(r.path ?? ""))}</td>
          <td class="px-6 py-3">${escapeHtml(String(r.status_code ?? ""))}</td>
          <td class="px-6 py-3 break-all">${escapeHtml(String(r.message ?? ""))}</td>
        </tr>
      `;
    })
    .join("");
}

async function cleanupLogs(period) {
  const resEl = document.getElementById("logs-result");
  try {
    const r = await _fetchJson(`/api/logs/cleanup?period=${encodeURIComponent(String(period || "1d"))}`, { method: "POST" });
    if (resEl) resEl.textContent = `Удалено записей: ${r.deleted ?? 0}`;
    await loadLogs();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function initLogsPage() {
  const body = document.getElementById("logs-body");
  if (!body) return;
  await loadLogs();
}

function showLastErrors1h() {
  const levelEl = document.getElementById("logs-level");
  const categoryEl = document.getElementById("logs-category");
  const hoursEl = document.getElementById("logs-hours");
  if (levelEl) levelEl.value = "ERROR";
  if (categoryEl) categoryEl.value = "";
  if (hoursEl) hoursEl.value = "1";
  loadLogs();
}

function resetLogsFilters() {
  const levelEl = document.getElementById("logs-level");
  const categoryEl = document.getElementById("logs-category");
  const hoursEl = document.getElementById("logs-hours");
  if (levelEl) levelEl.value = "";
  if (categoryEl) categoryEl.value = "";
  if (hoursEl) hoursEl.value = "24";
  loadLogs();
}

async function analyzeCompetitor() {
  const input = document.getElementById("competitor-domain");
  const resEl = document.getElementById("competitor-result");
  const reportEl = document.getElementById("competitor-report");
  const domain = (input?.value || "").toString();
  if (!domain) return;
  try {
    if (resEl) resEl.textContent = "Запрос…";
    const payload = await _fetchJson(`/api/competitors/analyze?domain=${encodeURIComponent(domain)}`);
    if (!payload?.ok) {
      if (resEl) resEl.textContent = payload?.detail ? String(payload.detail) : "Ошибка";
      if (reportEl) reportEl.textContent = "Нет данных";
      return;
    }
    if (resEl) resEl.textContent = "Готово.";
    if (reportEl) reportEl.innerHTML = renderCompetitorReport(payload);
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
    if (reportEl) reportEl.textContent = "Нет данных";
  }
}

function renderCompetitorReport(payload) {
  const dom = payload?.domain ?? "";
  const httpStatus = payload?.http_status ?? "—";
  const url = payload?.url ?? "";
  const title = payload?.title ?? "—";
  const h1 = payload?.h1 ?? "—";
  const md = payload?.meta_description ?? "—";
  const canon = payload?.canonical ?? "";
  const robots = payload?.robots ?? {};
  const sitemap = payload?.sitemap ?? {};
  const structure = payload?.structure ?? {};
  const issues = Array.isArray(payload?.issues) ? payload.issues : [];
  const aiUsed = Boolean(payload?.ai_used);
  const aiModel = payload?.ai_model ? String(payload.ai_model) : "";

  const robotsStatus = robots?.status ?? "—";
  const sitemapStatus = sitemap?.status ?? "—";
  const outLinks = structure?.outgoing_links ?? 0;
  const titleLen = structure?.title_length ?? 0;
  const mdLen = structure?.meta_description_length ?? 0;
  const hasH1 = Boolean(structure?.h1_present);

  const httpBadge =
    Number(httpStatus) === 200
      ? _badge(`HTTP ${httpStatus}`, "bg-emerald-100 text-emerald-700")
      : _badge(`HTTP ${httpStatus}`, "bg-rose-100 text-rose-700");
  const robotsBadge =
    String(robotsStatus).toUpperCase() === "OK"
      ? _badge("robots: OK", "bg-emerald-100 text-emerald-700")
      : String(robotsStatus).toUpperCase() === "WARNING"
      ? _badge("robots: предупреждение", "bg-amber-100 text-amber-700")
      : _badge("robots: ошибка", "bg-rose-100 text-rose-700");
  const sitemapBadge =
    String(sitemapStatus).toUpperCase() === "OK"
      ? _badge("sitemap: OK", "bg-emerald-100 text-emerald-700")
      : String(sitemapStatus).toUpperCase() === "WARNING"
      ? _badge("sitemap: предупреждение", "bg-amber-100 text-amber-700")
      : _badge("sitemap: ошибка", "bg-rose-100 text-rose-700");

  return `
    <div class="flex items-center justify-between mb-4">
      <div class="text-sm text-gray-600">${aiUsed ? _badge(`ИИ: ${escapeHtml(aiModel || "вкл")}`, "bg-indigo-100 text-indigo-700") : _badge("ИИ: выкл", "bg-gray-200 text-gray-800")}</div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Страница</div>
        <div class="text-sm"><span class="text-gray-500">Домен:</span> ${escapeHtml(String(dom))}</div>
        <div class="text-sm"><span class="text-gray-500">URL:</span> ${escapeHtml(String(url))}</div>
        <div class="text-sm"><span class="text-gray-500">HTTP:</span> ${httpBadge}</div>
        <div class="text-sm"><span class="text-gray-500">Исх. ссылок:</span> ${escapeHtml(String(outLinks))}</div>
        <div class="text-sm"><span class="text-gray-500">Длина Title:</span> ${escapeHtml(String(titleLen))}</div>
        <div class="text-sm"><span class="text-gray-500">Длина meta description:</span> ${escapeHtml(String(mdLen))}</div>
        <div class="text-sm"><span class="text-gray-500">H1:</span> ${hasH1 ? _badge("есть", "bg-emerald-100 text-emerald-700") : _badge("нет", "bg-rose-100 text-rose-700")}</div>
      </div>
      <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Файлы</div>
        <div class="text-sm"><span class="text-gray-500">robots:</span> ${robotsBadge}</div>
        <div class="text-sm"><span class="text-gray-500">sitemap:</span> ${sitemapBadge}</div>
      </div>
    </div>
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Рекомендации</div>
      ${
        issues.length
          ? issues
              .map((it) => {
                const p = String(it.priority ?? "low").toLowerCase();
                const badge =
                  p === "high"
                    ? _badge("высокий", "bg-rose-100 text-rose-700")
                    : p === "medium"
                    ? _badge("средний", "bg-amber-100 text-amber-700")
                    : _badge("низкий", "bg-gray-200 text-gray-800");
                return `<div class="flex items-start justify-between gap-3 py-2 border-b last:border-b-0">
                  <div>
                    <div class="font-medium">${escapeHtml(String(it.title ?? ""))}</div>
                    <div class="text-sm text-gray-600 mt-1">${escapeHtml(String(it.what_to_do ?? ""))}</div>
                  </div>
                  <div>${badge}</div>
                </div>`;
              })
              .join("")
          : '<div class="text-sm text-gray-500">Нет явных проблем по быстрым проверкам.</div>'
      }
    </div>
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Заголовок (Title)</div>
      <div class="text-sm break-words">${escapeHtml(String(title))}</div>
    </div>
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Заголовок H1</div>
      <div class="text-sm break-words">${escapeHtml(String(h1))}</div>
    </div>
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Описание (meta description)</div>
      <div class="text-sm break-words">${escapeHtml(String(md))}</div>
    </div>
    <div class="bg-white p-4 rounded-lg border border-gray-200">
      <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Канонический URL (canonical)</div>
      <div class="text-sm break-words">${canon ? escapeHtml(String(canon)) : "—"}</div>
    </div>
  `;
}

async function initCompetitorsPage() {
  const input = document.getElementById("competitor-domain");
  const report = document.getElementById("competitor-report");
  if (!input || !report) return;
  const siteEl = document.getElementById("competitor-site");
  if (siteEl) {
    try {
      const sites = await _fetchJson("/api/sites/");
      const list = Array.isArray(sites) ? sites : [];
      siteEl.innerHTML = ['<option value="">не выбрано</option>']
        .concat(list.map((s) => `<option value="${escapeHtml(String(s.id))}">${escapeHtml(String(s.domain ?? ""))}</option>`))
        .join("");
    } catch (e) {
      siteEl.innerHTML = '<option value="">не выбрано</option>';
    }
  }
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      analyzeCompetitor();
    }
  });

  await loadSavedCompetitors();
  await loadCompetitorHistory();
}

async function importCompetitorBacklinks() {
  const domainEl = document.getElementById("competitor-domain");
  const fileEl = document.getElementById("competitor-links-file");
  const resEl = document.getElementById("competitor-links-result");
  const domain = (domainEl?.value || "").toString().trim();
  const file = fileEl?.files?.[0];
  if (!domain || !file) return;
  try {
    if (resEl) resEl.textContent = "Импорт…";
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`/api/competitors/backlinks/import?domain=${encodeURIComponent(domain)}`, { method: "POST", body: fd });
    const json = await r.json();
    if (!r.ok || !json?.ok) {
      if (resEl) resEl.textContent = json?.detail ? String(json.detail) : "Ошибка импорта";
      return;
    }
    if (resEl) resEl.textContent = `Импортировано: ${json.imported}, обновлено: ${json.updated}${json.errors?.length ? `, ошибок: ${json.errors.length}` : ""}`;
    await loadCompetitorBacklinks();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function clearCompetitorBacklinks() {
  const domainEl = document.getElementById("competitor-domain");
  const resEl = document.getElementById("competitor-links-result");
  const domain = (domainEl?.value || "").toString().trim();
  if (!domain) return;
  try {
    if (resEl) resEl.textContent = "Очистка…";
    const payload = await _fetchJson(`/api/competitors/backlinks/clear?domain=${encodeURIComponent(domain)}`, { method: "POST" });
    if (resEl) resEl.textContent = `Удалено: ${payload?.deleted ?? 0}`;
    await loadCompetitorBacklinks();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function loadCompetitorBacklinks() {
  const domainEl = document.getElementById("competitor-domain");
  const siteEl = document.getElementById("competitor-site");
  const domain = (domainEl?.value || "").toString().trim();
  const resEl = document.getElementById("competitor-links-result");
  if (!domain) return;
  try {
    if (resEl) resEl.textContent = "Загрузка…";
    const sid = (siteEl?.value || "").toString().trim();
    const qs = new URLSearchParams();
    qs.set("domain", domain);
    qs.set("limit", "50");
    if (sid) qs.set("site_id", sid);
    const payload = await _fetchJson(`/api/competitors/backlinks/stats?${qs.toString()}`);
    if (!payload?.ok) {
      if (resEl) resEl.textContent = payload?.detail ? String(payload.detail) : "Ошибка";
      return;
    }
    if (resEl) resEl.textContent = payload.total ? "Готово." : "Нет импортированных ссылок.";
    renderCompetitorBacklinks(payload);
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

function renderCompetitorBacklinks(payload) {
  setText("comp-total", payload?.total ?? "—");
  setText("comp-donors", payload?.donors_total ?? "—");
  setText("comp-dofollow", payload?.dofollow_pct ?? "—");
  setText("comp-avgdr", payload?.avg_dr ?? "—");

  const donorsBody = document.getElementById("comp-donors-body");
  const anchorsBody = document.getElementById("comp-anchors-body");
  const targetsBody = document.getElementById("comp-targets-body");
  const overlapEl = document.getElementById("comp-overlap");
  const drEl = document.getElementById("comp-dr-buckets");
  const ltEl = document.getElementById("comp-link-types");
  const regEl = document.getElementById("comp-regions");
  const gapEl = document.getElementById("comp-gap");

  const donors = Array.isArray(payload?.top_donors) ? payload.top_donors : [];
  const anchors = Array.isArray(payload?.top_anchors) ? payload.top_anchors : [];
  const targets = Array.isArray(payload?.top_targets) ? payload.top_targets : [];

  if (donorsBody) {
    donorsBody.innerHTML = donors.length
      ? donors
          .map((d) => {
            const donor = String(d.donor || "");
            const bl = Number(d.backlinks || 0);
            const dr = Number(d.avg_dr || 0);
            const ua = Number(d.unique_anchors || 0);
            const drBadge =
              dr >= 60 ? _badge(String(dr), "bg-emerald-100 text-emerald-700") : dr >= 40 ? _badge(String(dr), "bg-amber-100 text-amber-700") : _badge(String(dr), "bg-gray-200 text-gray-800");
            const donorArg = escapeHtml(JSON.stringify(donor));
            return `<tr>
              <td class="px-4 py-2 break-all">
                <button class="text-indigo-700 hover:underline text-left" onclick="openDonorModal(${donorArg})">${escapeHtml(
                  donor
                )}</button>
              </td>
              <td class="px-4 py-2 font-medium">${escapeHtml(String(bl))}</td>
              <td class="px-4 py-2">${drBadge}</td>
              <td class="px-4 py-2">${escapeHtml(String(ua))}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="4" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
  }

  if (anchorsBody) {
    anchorsBody.innerHTML = anchors.length
      ? anchors
          .map((a) => {
            return `<tr>
              <td class="px-4 py-2 break-all">${escapeHtml(String(a.anchor || ""))}</td>
              <td class="px-4 py-2 font-medium">${escapeHtml(String(a.count ?? 0))}</td>
              <td class="px-4 py-2">${escapeHtml(String(a.pct ?? 0))}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="3" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
  }

  if (targetsBody) {
    targetsBody.innerHTML = targets.length
      ? targets
          .map((t) => {
            return `<tr>
              <td class="px-4 py-2 break-all">${escapeHtml(String(t.url || ""))}</td>
              <td class="px-4 py-2 font-medium">${escapeHtml(String(t.count ?? 0))}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
  }

  if (overlapEl) {
    const ov = payload?.overlap || null;
    if (!ov) {
      overlapEl.textContent = "Выбери ваш сайт, чтобы увидеть пересечения.";
    } else {
      overlapEl.innerHTML = `<div class="space-y-2">
        <div class="text-sm"><span class="text-gray-500">Пересечение:</span> <span class="font-medium">${escapeHtml(String(ov.overlap_count ?? 0))}</span></div>
        <div class="text-sm"><span class="text-gray-500">Уникальные доноры конкурента:</span> <span class="font-medium">${escapeHtml(String(ov.unique_competitor_donors_count ?? 0))}</span></div>
        ${
          Array.isArray(ov.overlap_donors) && ov.overlap_donors.length
            ? `<div class="text-xs font-semibold text-gray-500 uppercase mt-2">Примеры пересечений</div>
               <div class="text-sm text-gray-700 break-words">${escapeHtml(ov.overlap_donors.slice(0, 20).join(", "))}</div>`
            : ""
        }
        ${
          Array.isArray(ov.unique_competitor_donors) && ov.unique_competitor_donors.length
            ? `<div class="text-xs font-semibold text-gray-500 uppercase mt-2">Уникальные доноры</div>
               <div class="text-sm text-gray-700 break-words">${escapeHtml(ov.unique_competitor_donors.slice(0, 20).join(", "))}</div>`
            : ""
        }
      </div>`;
    }
  }

  if (gapEl) {
    const gap = payload?.gap || null;
    if (!gap) {
      gapEl.textContent = "Выбери ваш сайт, чтобы увидеть разрыв доноров.";
    } else {
      const donors = Array.isArray(gap.donor_gap) ? gap.donor_gap : [];
      gapEl.innerHTML = `<div class="space-y-2">
        <div class="text-sm"><span class="text-gray-500">Доноров в разрыве:</span> <span class="font-medium">${escapeHtml(
          String(gap.donor_gap_count ?? donors.length ?? 0)
        )}</span></div>
        ${
          donors.length
            ? `<div class="text-xs font-semibold text-gray-500 uppercase mt-2">Примеры</div>
               <div class="text-sm text-gray-700 break-words">${escapeHtml(donors.slice(0, 30).join(", "))}</div>`
            : '<div class="text-sm text-gray-500">Нет доноров в разрыве.</div>'
        }
      </div>`;
    }
  }

  if (drEl) {
    const b = payload?.dr_buckets || {};
    const keys = ["0-19", "20-39", "40-59", "60-79", "80-100"];
    const rows = keys.map((k) => `${escapeHtml(k)}: ${escapeHtml(String(b?.[k] ?? 0))}`).join("<br/>");
    drEl.innerHTML = rows || "Нет данных";
  }

  if (ltEl) {
    const lt = payload?.link_types || {};
    const parts = Object.keys(lt)
      .map((k) => ({ k, v: Number(lt[k] ?? 0) }))
      .sort((a, b) => b.v - a.v)
      .slice(0, 8)
      .map((x) => `${escapeHtml(String(x.k))}: ${escapeHtml(String(x.v))}`)
      .join("<br/>");
    ltEl.innerHTML = parts || "Нет данных";
  }

  if (regEl) {
    const regs = Array.isArray(payload?.top_regions) ? payload.top_regions : [];
    regEl.innerHTML = regs.length
      ? regs
          .map((r) => `${escapeHtml(String(r.region ?? "?"))}: ${escapeHtml(String(r.count ?? 0))}`)
          .join("<br/>")
      : "Нет данных";
  }
}

async function exportCompetitorGap() {
  const domainEl = document.getElementById("competitor-domain");
  const siteEl = document.getElementById("competitor-site");
  const domain = (domainEl?.value || "").toString().trim();
  const sid = (siteEl?.value || "").toString().trim();
  if (!domain || !sid) return;
  const payload = await _fetchJson(`/api/competitors/backlinks/gap/export?domain=${encodeURIComponent(domain)}&site_id=${encodeURIComponent(sid)}`);
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const csv = ["donor"].concat(items.map((d) => String(d).replace(/"/g, '""'))).map((x) => `"${x}"`).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `donor_gap_${domain.replace(/[^a-z0-9.-]+/gi, "_")}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function createTasksFromCompetitorGap() {
  const domainEl = document.getElementById("competitor-domain");
  const siteEl = document.getElementById("competitor-site");
  const resEl = document.getElementById("competitor-links-result");
  const domain = (domainEl?.value || "").toString().trim();
  const sid = (siteEl?.value || "").toString().trim();
  if (!domain || !sid) return;
  try {
    if (resEl) resEl.textContent = "Создаю задачи…";
    const payload = await _fetchJson(
      `/api/competitors/backlinks/gap/create-tasks?domain=${encodeURIComponent(domain)}&site_id=${encodeURIComponent(sid)}&limit=30`,
      { method: "POST" }
    );
    if (resEl) resEl.textContent = `Готово: создано задач — ${payload?.created ?? 0}${payload?.skipped_duplicates ? `, дублей — ${payload.skipped_duplicates}` : ""}.`;
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

let _savedCompetitorSelectedId = null;

async function loadSavedCompetitors() {
  const body = document.getElementById("saved-competitors-body");
  const resEl = document.getElementById("saved-competitors-result");
  if (!body) return;
  try {
    if (resEl) resEl.textContent = "Загрузка…";
    const siteEl = document.getElementById("competitor-site");
    const sid = (siteEl?.value || "").toString().trim();
    const qs = new URLSearchParams();
    if (sid) qs.set("site_id", sid);
    const payload = await _fetchJson(`/api/competitors/saved?${qs.toString()}`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (resEl) resEl.textContent = `Сохранено: ${items.length}`;
    const selected = Number(localStorage.getItem("selected_competitor_id") || "");
    if (selected) _savedCompetitorSelectedId = selected;

    body.innerHTML = items.length
      ? items
          .map((c) => {
            const id = Number(c.id);
            const dom = String(c.domain || "");
            const label = c.label ? ` (${String(c.label)})` : "";
            const last = (c.last_checked_at || "").toString().slice(0, 19).replace("T", " ") || "—";
            const donors = c.donors_total ?? "—";
            const links = c.backlinks_total ?? "—";
            const dr = c.avg_dr ?? "—";
            const isSel = _savedCompetitorSelectedId && id === Number(_savedCompetitorSelectedId);
            const domArg = escapeHtml(JSON.stringify(dom));
            return `<tr class="${isSel ? "bg-indigo-50" : ""}">
              <td class="px-4 py-2 font-medium break-all">${escapeHtml(dom)}${escapeHtml(label)}</td>
              <td class="px-4 py-2 text-sm text-gray-600">${c.site_domain ? escapeHtml(String(c.site_domain)) : c.site_id ? escapeHtml(String(c.site_id)) : "—"}</td>
              <td class="px-4 py-2 text-sm text-gray-600">${escapeHtml(last)}</td>
              <td class="px-4 py-2">${escapeHtml(String(donors))}</td>
              <td class="px-4 py-2">${escapeHtml(String(links))}</td>
              <td class="px-4 py-2">${escapeHtml(String(dr))}</td>
              <td class="px-4 py-2 text-right">
                <div class="flex justify-end gap-2">
                  <button class="text-sm text-indigo-700 hover:underline" onclick="selectSavedCompetitor(${id}, ${domArg})">Выбрать</button>
                  <button class="text-sm text-indigo-700 hover:underline" onclick="refreshSavedCompetitor(${id})">Обновить</button>
                  <button class="text-sm text-gray-600 hover:underline" onclick="loadCompetitorHistory(${id})">История</button>
                  <button class="text-sm text-rose-700 hover:underline" onclick="deleteSavedCompetitor(${id})">Удалить</button>
                </div>
              </td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="7" class="px-4 py-6 text-center text-gray-400">Сохранённых конкурентов пока нет.</td></tr>';
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
    body.innerHTML = '<tr><td colspan="7" class="px-4 py-6 text-center text-rose-700">Ошибка загрузки</td></tr>';
  }
}

async function saveCompetitor() {
  const domainEl = document.getElementById("competitor-domain");
  const siteEl = document.getElementById("competitor-site");
  const resEl = document.getElementById("saved-competitors-result");
  const domain = (domainEl?.value || "").toString().trim();
  const sid = (siteEl?.value || "").toString().trim();
  if (!domain) return;
  try {
    if (resEl) resEl.textContent = "Сохранение…";
    const payload = await _fetchJson("/api/competitors/saved", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ domain, site_id: sid ? Number(sid) : null }),
    });
    if (payload?.id) {
      _savedCompetitorSelectedId = Number(payload.id);
      localStorage.setItem("selected_competitor_id", String(_savedCompetitorSelectedId));
    }
    if (resEl) resEl.textContent = payload?.created ? "Конкурент сохранён." : "Конкурент уже был сохранён (обновлено).";
    await loadSavedCompetitors();
    await loadCompetitorHistory();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function selectSavedCompetitor(id, domain) {
  _savedCompetitorSelectedId = Number(id);
  localStorage.setItem("selected_competitor_id", String(_savedCompetitorSelectedId));
  const domainEl = document.getElementById("competitor-domain");
  if (domainEl) domainEl.value = String(domain || "");
  await loadSavedCompetitors();
  await analyzeCompetitor();
  await loadCompetitorBacklinks();
  await loadCompetitorHistory();
}

async function refreshSavedCompetitor(id) {
  const resEl = document.getElementById("saved-competitors-result");
  const siteEl = document.getElementById("competitor-site");
  const sid = (siteEl?.value || "").toString().trim();
  try {
    if (resEl) resEl.textContent = "Обновление конкурента…";
    const qs = new URLSearchParams();
    if (sid) qs.set("site_id", sid);
    const payload = await _fetchJson(`/api/competitors/saved/${encodeURIComponent(String(Number(id)))}/refresh?${qs.toString()}`, { method: "POST" });
    if (!payload?.ok) {
      if (resEl) resEl.textContent = payload?.detail ? String(payload.detail) : "Ошибка";
      return;
    }
    _savedCompetitorSelectedId = Number(id);
    localStorage.setItem("selected_competitor_id", String(_savedCompetitorSelectedId));
    const analysis = payload?.analysis;
    const links = payload?.links;
    const reportEl = document.getElementById("competitor-report");
    const domEl = document.getElementById("competitor-domain");
    if (domEl) domEl.value = String(analysis?.domain || domEl.value || "");
    if (reportEl && analysis?.ok) reportEl.innerHTML = renderCompetitorReport(analysis);
    if (links?.ok) renderCompetitorBacklinks(links);
    if (resEl) resEl.textContent = "Готово: метрики обновлены и сохранены.";
    await loadSavedCompetitors();
    await loadCompetitorHistory();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function deleteSavedCompetitor(id) {
  const resEl = document.getElementById("saved-competitors-result");
  try {
    if (resEl) resEl.textContent = "Удаление…";
    await _fetchJson(`/api/competitors/saved/${encodeURIComponent(String(Number(id)))}`, { method: "DELETE" });
    if (_savedCompetitorSelectedId && Number(id) === Number(_savedCompetitorSelectedId)) {
      _savedCompetitorSelectedId = null;
      localStorage.removeItem("selected_competitor_id");
    }
    if (resEl) resEl.textContent = "Удалено.";
    await loadSavedCompetitors();
    await loadCompetitorHistory();
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

async function loadCompetitorHistory(forceId) {
  const body = document.getElementById("competitor-history-body");
  const resEl = document.getElementById("competitor-history-result");
  if (!body) return;
  const id = forceId ? Number(forceId) : Number(_savedCompetitorSelectedId || localStorage.getItem("selected_competitor_id") || "");
  if (!id) {
    body.innerHTML = '<tr><td colspan="8" class="px-4 py-6 text-center text-gray-400">Выбери сохранённого конкурента.</td></tr>';
    if (resEl) resEl.textContent = "";
    return;
  }
  _savedCompetitorSelectedId = id;
  localStorage.setItem("selected_competitor_id", String(id));
  try {
    if (resEl) resEl.textContent = "Загрузка…";
    const payload = await _fetchJson(`/api/competitors/saved/${encodeURIComponent(String(id))}/history?limit=30`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (resEl) resEl.textContent = items.length ? `Записей: ${items.length}` : "Истории пока нет.";
    body.innerHTML = items.length
      ? items
          .map((r) => {
            const dt = (r.created_at || "").toString().slice(0, 19).replace("T", " ");
            return `<tr>
              <td class="px-4 py-2 text-gray-600">${escapeHtml(dt || "—")}</td>
              <td class="px-4 py-2 font-medium">${escapeHtml(String(r.http_status ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.donors_total ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.backlinks_total ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.dofollow_pct ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.avg_dr ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.gap_donors ?? "—"))}</td>
              <td class="px-4 py-2">${escapeHtml(String(r.overlap_donors ?? "—"))}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="8" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
    body.innerHTML = '<tr><td colspan="8" class="px-4 py-6 text-center text-rose-700">Ошибка загрузки</td></tr>';
  }
}

let _donorModalState = { competitor_domain: null, donor_domain: null, site_id: null, items: [] };

async function openDonorModal(donorDomain) {
  const modal = document.getElementById("donor-modal");
  const subtitle = document.getElementById("donor-modal-subtitle");
  const domEl = document.getElementById("donor-modal-domain");
  const totalEl = document.getElementById("donor-modal-total");
  const avgEl = document.getElementById("donor-modal-avgdr");
  const dfEl = document.getElementById("donor-modal-dofollow");
  const uaEl = document.getElementById("donor-modal-uanchors");
  const anchorsEl = document.getElementById("donor-modal-anchors");
  const targetsEl = document.getElementById("donor-modal-targets");
  const linksEl = document.getElementById("donor-modal-links");
  const taskBtn = document.getElementById("donor-modal-task");
  if (!modal || !domEl || !totalEl || !avgEl || !dfEl || !uaEl || !anchorsEl || !targetsEl || !linksEl) return;

  const compDomain = (document.getElementById("competitor-domain")?.value || "").toString().trim();
  const siteId = (document.getElementById("competitor-site")?.value || "").toString().trim();
  const donor = (donorDomain || "").toString().trim();
  if (!compDomain || !donor) return;

  _donorModalState = { competitor_domain: compDomain, donor_domain: donor, site_id: siteId || null, items: [] };
  modal.classList.remove("hidden");
  domEl.textContent = donor;
  if (subtitle) subtitle.textContent = "Загрузка данных донора…";
  totalEl.textContent = "—";
  avgEl.textContent = "—";
  dfEl.textContent = "—";
  uaEl.textContent = "—";
  anchorsEl.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>';
  targetsEl.innerHTML = '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>';
  linksEl.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>';

  if (taskBtn) taskBtn.disabled = !siteId;
  await loadDonorDetails();
}

function closeDonorModal() {
  const modal = document.getElementById("donor-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

async function loadDonorDetails() {
  const subtitle = document.getElementById("donor-modal-subtitle");
  const totalEl = document.getElementById("donor-modal-total");
  const avgEl = document.getElementById("donor-modal-avgdr");
  const dfEl = document.getElementById("donor-modal-dofollow");
  const uaEl = document.getElementById("donor-modal-uanchors");
  const anchorsEl = document.getElementById("donor-modal-anchors");
  const targetsEl = document.getElementById("donor-modal-targets");
  const linksEl = document.getElementById("donor-modal-links");
  if (!totalEl || !avgEl || !dfEl || !uaEl || !anchorsEl || !targetsEl || !linksEl) return;

  const comp = _donorModalState.competitor_domain;
  const donor = _donorModalState.donor_domain;
  if (!comp || !donor) return;
  try {
    const payload = await _fetchJson(
      `/api/competitors/backlinks/donor?domain=${encodeURIComponent(comp)}&donor=${encodeURIComponent(donor)}&limit=200`
    );
    if (!payload?.ok) {
      if (subtitle) subtitle.textContent = payload?.detail ? String(payload.detail) : "Ошибка";
      return;
    }
    const summary = payload?.summary || {};
    const total = Number(payload?.total ?? 0);
    const avgDr = Number(summary?.avg_dr ?? 0);
    const maxDr = Number(summary?.max_dr ?? 0);
    const dfPct = summary?.dofollow_pct ?? "—";
    const uAnch = summary?.unique_anchors ?? "—";
    const region = summary?.region ? String(summary.region) : "—";

    totalEl.textContent = String(total);
    avgEl.textContent = String(avgDr);
    dfEl.textContent = String(dfPct);
    uaEl.textContent = String(uAnch);
    const pr = avgDr >= 60 ? "высокий" : avgDr >= 40 ? "средний" : "низкий";
    if (subtitle) subtitle.textContent = `Приоритет: ${pr} · Регион: ${region} · max DR: ${maxDr}`;

    const topAnchors = Array.isArray(payload?.top_anchors) ? payload.top_anchors : [];
    anchorsEl.innerHTML = topAnchors.length
      ? topAnchors
          .slice(0, 20)
          .map((a) => `<tr><td class="px-4 py-2 break-all">${escapeHtml(String(a.anchor || ""))}</td><td class="px-4 py-2 font-medium">${escapeHtml(String(a.count ?? 0))}</td></tr>`)
          .join("")
      : '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';

    const topTargets = Array.isArray(payload?.top_targets) ? payload.top_targets : [];
    targetsEl.innerHTML = topTargets.length
      ? topTargets
          .slice(0, 20)
          .map(
            (t) =>
              `<tr><td class="px-4 py-2 break-all">${escapeHtml(String(t.url || ""))}</td><td class="px-4 py-2 font-medium">${escapeHtml(
                String(t.count ?? 0)
              )}</td></tr>`
          )
          .join("")
      : '<tr><td colspan="2" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';

    const items = Array.isArray(payload?.items) ? payload.items : [];
    _donorModalState.items = items;
    linksEl.innerHTML = items.length
      ? items
          .slice(0, 200)
          .map((x) => {
            const src = String(x.source_url || "");
            const tgt = String(x.target_url || "");
            const anchor = (x.anchor || "").toString();
            const lt = String(x.link_type || "");
            const dr = x.domain_score === null || x.domain_score === undefined ? "—" : String(x.domain_score);
            const srcLink = src ? `<a class="text-indigo-700 hover:underline break-all" target="_blank" rel="noreferrer" href="${escapeHtml(src)}">${escapeHtml(src)}</a>` : "—";
            const tgtLink = tgt ? `<a class="text-indigo-700 hover:underline break-all" target="_blank" rel="noreferrer" href="${escapeHtml(tgt)}">${escapeHtml(tgt)}</a>` : "—";
            return `<tr>
              <td class="px-4 py-2">${srcLink}</td>
              <td class="px-4 py-2">${tgtLink}</td>
              <td class="px-4 py-2 break-words">${escapeHtml(anchor || "—")}</td>
              <td class="px-4 py-2">${escapeHtml(lt || "—")}</td>
              <td class="px-4 py-2 font-medium">${escapeHtml(dr)}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="5" class="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>';
  } catch (e) {
    if (subtitle) subtitle.textContent = String(e?.message ?? e);
  }
}

function exportDonorLinks() {
  const comp = _donorModalState.competitor_domain;
  const donor = _donorModalState.donor_domain;
  const items = Array.isArray(_donorModalState.items) ? _donorModalState.items : [];
  if (!comp || !donor || !items.length) return;
  const header = ["source_url", "target_url", "anchor", "link_type", "dr", "first_seen"].join(",");
  const lines = items.map((x) => {
    const row = [
      x.source_url || "",
      x.target_url || "",
      (x.anchor || "").toString().replace(/\s+/g, " ").trim(),
      x.link_type || "",
      x.domain_score === null || x.domain_score === undefined ? "" : String(x.domain_score),
      x.first_seen || "",
    ].map((v) => `"${String(v).replace(/"/g, '""')}"`);
    return row.join(",");
  });
  const csv = [header].concat(lines).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `donor_${donor.replace(/[^a-z0-9.-]+/gi, "_")}_${comp.replace(/[^a-z0-9.-]+/gi, "_")}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function createTaskFromDonor() {
  const resEl = document.getElementById("competitor-links-result");
  const comp = _donorModalState.competitor_domain;
  const donor = _donorModalState.donor_domain;
  const siteId = _donorModalState.site_id;
  if (!comp || !donor || !siteId) return;
  try {
    if (resEl) resEl.textContent = "Создаю задачу по донору…";
    const payload = await _fetchJson(
      `/api/competitors/backlinks/donor/create-task?domain=${encodeURIComponent(comp)}&site_id=${encodeURIComponent(siteId)}&donor=${encodeURIComponent(donor)}`,
      { method: "POST" }
    );
    if (resEl) resEl.textContent = `Готово: создано — ${payload?.created ?? 0}${payload?.skipped_duplicates ? `, дублей — ${payload.skipped_duplicates}` : ""}.`;
  } catch (e) {
    if (resEl) resEl.textContent = String(e?.message ?? e);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.body.addEventListener("htmx:afterRequest", function (evt) {
  const elt = evt.detail.elt;
  const renderKey = elt?.dataset?.render;
  if (!renderKey) return;

  const xhr = evt.detail.xhr;
  const json = safeJsonParse(xhr.responseText);

  if (renderKey === "dashboard") {
    if (json) renderDashboard(json);
    return;
  }

  if (renderKey === "sites") {
    if (json) renderSites(json);
    return;
  }

  if (renderKey === "siteCreated") {
    const errorEl = document.getElementById("site-create-error");
    if (xhr.status >= 200 && xhr.status < 300) {
      if (errorEl) errorEl.textContent = "";
      elt.reset?.();
      loadSites();
      return;
    }
    if (errorEl) {
      const detail = json?.detail ? String(json.detail) : "";
      errorEl.textContent = translateDetail(detail) || `Ошибка запроса: ${xhr.status}`;
    }
    return;
  }

  if (renderKey === "audit") {
    renderAudit(json);
    return;
  }

  if (renderKey === "deepAudit") {
    renderDeepAudit(json);
    return;
  }

  if (renderKey === "meta") {
    renderMeta(json);
    return;
  }

  if (renderKey === "positionsChart") {
    if (json) renderPositionsChart(json);
    return;
  }

  if (renderKey === "tasksChart") {
    if (json) renderTasksChart(json);
    return;
  }

  if (renderKey === "errorsChart") {
    if (json) renderErrorsChart(json);
    return;
  }

  if (renderKey === "keywordDeltas") {
    if (json) renderDashboardKeywordDeltas(json);
    return;
  }

  if (renderKey === "recentErrors") {
    if (json) renderDashboardRecentErrors(json);
    return;
  }

  if (renderKey === "aiKeywords") {
    if (json) renderAiKeywords(json);
    return;
  }

  if (renderKey === "titleCheck") {
    if (json) renderTitleCheck(json);
    return;
  }
});

window.deleteSite = deleteSite;
window.selectSite = selectSite;
window.runAllScans = runAllScans;
window.runSiteScan = runSiteScan;
window.loadScanHistory = loadScanHistory;
window.runTechAudit = runTechAudit;
window.checkRobots = checkRobots;
window.checkSitemap = checkSitemap;
window.refreshHistory = refreshHistory;
window.clearSelectedScanHistory = clearSelectedScanHistory;
window.cleanupScans = cleanupScans;
window.pollTaskStatus = pollTaskStatus;
window.reloadLinks = reloadLinks;
window.refreshLinks = refreshLinks;
window.refreshLinksAhrefs = refreshLinksAhrefs;
window.analyzeLinks = analyzeLinks;
window.triggerLinksImport = triggerLinksImport;
window.openLinksImportModal = openLinksImportModal;
window.closeLinksImportModal = closeLinksImportModal;
window.setLinksImportTab = setLinksImportTab;
window.importLinksCsvFromModal = importLinksCsvFromModal;
window.importLinksText = importLinksText;
window.addLinkManual = addLinkManual;
window.clearLinks = clearLinks;
window.openPurchasedAddModal = openPurchasedAddModal;
window.closePurchasedAddModal = closePurchasedAddModal;
window.submitPurchasedAdd = submitPurchasedAdd;
window.monitorPurchasedLinksNow = monitorPurchasedLinksNow;
window.togglePurchasedAuto = togglePurchasedAuto;
window.openPurchasedHistory = openPurchasedHistory;
window.closePurchasedHistory = closePurchasedHistory;
window.loadAnchorAnalysis = loadAnchorAnalysis;
window.loadTopPages = loadTopPages;
window.loadBrokenLinks = loadBrokenLinks;
window.loadIntegrations = loadIntegrations;
window.loadAiSettings = loadAiSettings;
window.saveAiSettings = saveAiSettings;
window.loadUsers = loadUsers;
window.createUserFromForm = createUserFromForm;
window.saveUser = saveUser;
window.deleteUser = deleteUser;
window.loadDomainAnalysis = loadDomainAnalysis;
window.loadInternalLinks = loadInternalLinks;
window.toggleNotifications = toggleNotifications;
window.loadNotifications = loadNotifications;
window.markNotificationSeen = markNotificationSeen;
window.configureAlerts = configureAlerts;
window.openSiteSettings = openSiteSettings;
window.saveSiteAlerts = saveSiteAlerts;
window.openAlertsModal = openAlertsModal;
window.closeAlertsModal = closeAlertsModal;
window.loadRecommendations = loadRecommendations;
window.loadNotes = loadNotes;
window.createNoteFromForm = createNoteFromForm;
window.deleteNote = deleteNote;
window.loadKeywords = loadKeywords;
window.createKeywordFromForm = createKeywordFromForm;
window.loadKeywordSuggestions = loadKeywordSuggestions;
window.setKeywordFromSuggestion = setKeywordFromSuggestion;
window.loadInlineKeywordSuggestions = loadInlineKeywordSuggestions;
window.loadDeepAuditHistory = loadDeepAuditHistory;
window.loadDeepAuditDiff = loadDeepAuditDiff;
window.createTasksFromDeepAudit = createTasksFromDeepAudit;
window.deleteKeyword = deleteKeyword;
window.updateTaskStatus = updateTaskStatus;
window.updateTaskPriority = updateTaskPriority;
window.openTaskModal = openTaskModal;
window.closeTaskModal = closeTaskModal;
window.openTaskAudit = openTaskAudit;
window.loadDeepAuditHistoryInto = loadDeepAuditHistoryInto;
window.loadDeepAuditDiffInto = loadDeepAuditDiffInto;
window.loadKeywordsHistory = loadKeywordsHistory;
window.loadCannibalization = loadCannibalization;
window.loadKeywordChanges = loadKeywordChanges;
window.triggerKeywordImport = triggerKeywordImport;
window.loadLogs = loadLogs;
window.cleanupLogs = cleanupLogs;
window.showLastErrors1h = showLastErrors1h;
window.resetLogsFilters = resetLogsFilters;
window.analyzeCompetitor = analyzeCompetitor;
window.importCompetitorBacklinks = importCompetitorBacklinks;
window.loadCompetitorBacklinks = loadCompetitorBacklinks;
window.clearCompetitorBacklinks = clearCompetitorBacklinks;
window.exportCompetitorGap = exportCompetitorGap;
window.createTasksFromCompetitorGap = createTasksFromCompetitorGap;
window.loadSavedCompetitors = loadSavedCompetitors;
window.saveCompetitor = saveCompetitor;
window.selectSavedCompetitor = selectSavedCompetitor;
window.refreshSavedCompetitor = refreshSavedCompetitor;
window.deleteSavedCompetitor = deleteSavedCompetitor;
window.loadCompetitorHistory = loadCompetitorHistory;
window.openDonorModal = openDonorModal;
window.closeDonorModal = closeDonorModal;
window.exportDonorLinks = exportDonorLinks;
window.createTaskFromDonor = createTaskFromDonor;
window.openDashboardSummary = openDashboardSummary;
window.closeDashboardSummary = closeDashboardSummary;
window.openIpDetails = openIpDetails;
window.closeIpDetails = closeIpDetails;
window.loadIpHistory = loadIpHistory;
window.copyIp = copyIp;
window.showIpRowDetails = showIpRowDetails;
window.openSystemDetails = openSystemDetails;
window.closeSystemDetails = closeSystemDetails;
window.loadSystemDetails = loadSystemDetails;
window.loadTasksPage = loadTasksPage;
window.toggleAutoTasksFilter = toggleAutoTasksFilter;
window.loadContentPlansPage = loadContentPlansPage;
window.createContentIdea = createContentIdea;

document.addEventListener("DOMContentLoaded", function () {
  initChartControls();
  initUaUi();
  initDeepAuditUi();
  initAlertsModalControls();
  const { id, domain } = getSelectedSite();
  const hasHistoryPanel = Boolean(document.getElementById("scan-history-panel"));
  if (hasHistoryPanel && id) {
    loadScanHistory(id, domain ?? undefined);
  }
  initSitesScanViewControl();
  initSitesChartTypeControl();
  initLinksPage();
  initPurchasedLinksPage();
  initUsersPage();
  initDomainAnalysisPage();
  initRecommendationsPage();
  initNotesPage();
  initKeywordsPage();
  initLogsPage();
  initDashboardWidgets();
  initAiWidget();
  initTasksPage();
  initContentPlansPage();
  initCompetitorsPage();
  _startNotificationsPoll();
});
