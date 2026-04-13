function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value == null ? "—" : String(value);
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
      '<tr><td colspan="4" class="px-4 py-8 text-center text-gray-400">No data</td></tr>';
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

function renderSites(sites) {
  const tbody = document.getElementById("sites-body");
  if (!tbody) return;
  const list = Array.isArray(sites) ? sites : [];
  if (list.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="4" class="px-6 py-10 text-center text-gray-400">No sites added.</td></tr>';
    return;
  }

  tbody.innerHTML = list
    .map((s) => {
      const id = s.id;
      const domain = s.domain ?? "";
      const cms = s.cms ?? "-";
      const region = s.region ?? "-";
      return `
        <tr>
          <td class="px-6 py-4 font-medium">${escapeHtml(domain)}</td>
          <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(cms)}</td>
          <td class="px-6 py-4 text-sm text-gray-500">${escapeHtml(region)}</td>
          <td class="px-6 py-4 text-right">
            <button class="text-red-600 hover:underline text-sm" onclick="deleteSite(${Number(
              id
            )})">Delete</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderAudit(result) {
  const el = document.getElementById("audit-result");
  if (!el) return;
  if (!result) {
    el.textContent = "No result";
    return;
  }
  const status = result.status_code ?? "Error";
  const title = result.title ?? "N/A";
  const h1 = result.h1 ?? "N/A";
  const indexed =
    result.is_indexed === null || result.is_indexed === undefined
      ? "Unknown"
      : result.is_indexed
      ? "Yes"
      : "No";
  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
      <div class="flex justify-between"><span class="text-gray-500">Status:</span><span class="font-semibold">${escapeHtml(
        String(status)
      )}</span></div>
      <div><div class="text-gray-500">Title:</div><div class="font-medium break-all">${escapeHtml(
        String(title)
      )}</div></div>
      <div><div class="text-gray-500">H1:</div><div class="font-medium break-all">${escapeHtml(
        String(h1)
      )}</div></div>
      <div class="flex justify-between"><span class="text-gray-500">Indexed:</span><span class="font-medium">${escapeHtml(
        String(indexed)
      )}</span></div>
    </div>
  `;
}

function renderMeta(data) {
  const el = document.getElementById("meta-result");
  if (!el) return;
  const meta = data?.meta ?? "";
  const length = data?.length ?? meta.length;
  el.innerHTML = `
    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
      <div class="flex justify-between items-center">
        <div class="text-xs font-semibold text-gray-400 uppercase">Generated meta</div>
        <button class="text-xs text-indigo-700 hover:underline" onclick="navigator.clipboard.writeText(${JSON.stringify(
          meta
        )})">Copy</button>
      </div>
      <div class="text-sm text-gray-800 italic break-words">${escapeHtml(meta || "Empty")}</div>
      <div class="text-xs text-gray-400 text-right">${escapeHtml(
        String(length)
      )} / 160</div>
    </div>
  `;
}

let positionsChartInstance = null;
let tasksChartInstance = null;

function renderPositionsChart(payload) {
  const canvas = document.getElementById("positions-chart");
  if (!canvas || !window.Chart) return;
  const labels = Array.isArray(payload?.labels) ? payload.labels : [];
  const values = Array.isArray(payload?.values) ? payload.values : [];

  if (positionsChartInstance) {
    positionsChartInstance.destroy();
    positionsChartInstance = null;
  }

  positionsChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Avg position",
          data: values,
          borderColor: "rgb(79, 70, 229)",
          backgroundColor: "rgba(79, 70, 229, 0.15)",
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          reverse: true,
          beginAtZero: false,
          ticks: { precision: 0 },
        },
      },
      plugins: {
        legend: { display: true },
      },
    },
  });
}

function renderTasksChart(payload) {
  const canvas = document.getElementById("tasks-chart");
  if (!canvas || !window.Chart) return;
  const todo = Number(payload?.todo ?? 0);
  const inProgress = Number(payload?.in_progress ?? 0);
  const done = Number(payload?.done ?? 0);

  if (tasksChartInstance) {
    tasksChartInstance.destroy();
    tasksChartInstance = null;
  }

  tasksChartInstance = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["todo", "in_progress", "done"],
      datasets: [
        {
          data: [todo, inProgress, done],
          backgroundColor: ["#f59e0b", "#10b981", "#6366f1"],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function renderAiKeywords(payload) {
  const el = document.getElementById("ai-keywords-result");
  if (!el) return;
  const items = Array.isArray(payload?.keywords) ? payload.keywords : [];
  if (items.length === 0) {
    el.textContent = "No keywords found.";
    return;
  }
  el.innerHTML = `
    <div class="overflow-x-auto border rounded-lg">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-xs font-semibold uppercase text-gray-400">
          <tr>
            <th class="px-4 py-2">Keyword</th>
            <th class="px-4 py-2">Count</th>
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
        <span class="text-gray-500">Status:</span>
        <span class="font-semibold">${escapeHtml(String(status))}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-gray-500">Length:</span>
        <span class="font-medium">${escapeHtml(String(length))}</span>
      </div>
      <div class="text-gray-700">${escapeHtml(String(recommendation))}</div>
    </div>
  `;
}

async function loadSites() {
  const resp = await fetch("/api/sites", { headers: { Accept: "application/json" } });
  const data = await resp.json();
  renderSites(data);
}

async function deleteSite(id) {
  await fetch(`/api/sites/${id}`, { method: "DELETE" });
  await loadSites();
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
      errorEl.textContent = json?.detail ? String(json.detail) : `Request failed: ${xhr.status}`;
    }
    return;
  }

  if (renderKey === "audit") {
    renderAudit(json);
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
