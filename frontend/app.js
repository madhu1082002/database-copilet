const API_BASE = window.location.origin;
const THEME_KEY = "dataops-theme";

function initThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
  });
}

initThemeToggle();

const statsGrid = document.getElementById("stats-grid");
const pipelineList = document.getElementById("pipeline-list");
const pipelineCount = document.getElementById("pipeline-count");
const pipelineSearch = document.getElementById("pipeline-search");
const lastUpdated = document.getElementById("last-updated");
const refreshBtn = document.getElementById("refresh-btn");
const sourceBadge = document.getElementById("source-badge");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const categorySelect = document.getElementById("category-select");

const STAT_ICONS = {
  info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
  success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  danger: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
};

const AVATAR_BOT = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/></svg>`;
const AVATAR_USER = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

let allPipelines = [];

function filterPipelines(pipelines, query) {
  const q = query.trim().toLowerCase();
  if (!q) return pipelines;
  return pipelines.filter((p) => {
    const haystack = [
      p.pipeline_name,
      p.pipeline_name.replace(/_/g, " "),
      p.status,
      p.cluster_id,
      p.error_message,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}

function renderPipelineList(pipelines) {
  if (pipelineCount) {
    const total = allPipelines.length;
    const shown = pipelines.length;
    pipelineCount.textContent =
      shown === total ? `${total} runs` : `${shown} of ${total} runs`;
  }

  if (!pipelines.length) {
    pipelineList.innerHTML = `<div class="empty-pipelines">${
      allPipelines.length ? "No pipelines match your search" : "No pipeline runs found"
    }</div>`;
    return;
  }

  pipelineList.innerHTML = pipelines
    .map(
      (p, index) => `
          <div class="pipeline-item" data-pipeline="${p.pipeline_name}" data-status="${p.status}" title="Click to ask about this pipeline">
            <span class="row-serial" aria-label="Serial number">${index + 1}</span>
            <div class="info">
              <span class="pipeline-status-dot ${p.status}"></span>
              <div>
                <div class="name">${p.pipeline_name.replace(/_/g, " ")}</div>
                <div class="meta">
                  <span class="time">${formatTime(p.run_time)}</span>
                  ${p.duration_minutes ? `<span class="duration">${p.duration_minutes} min</span>` : ""}
                </div>
              </div>
            </div>
            <span class="status-badge ${p.status}">${p.status.replace("_", " ")}</span>
          </div>
        `
    )
    .join("");
}

function showSkeletons() {
  statsGrid.innerHTML = Array(4).fill(`<div class="stat-card skeleton skeleton-stat"></div>`).join("");
  pipelineList.innerHTML = Array(3).fill(`<div class="skeleton skeleton-pipeline"></div>`).join("");
}

async function loadDashboard() {
  refreshBtn.classList.add("spinning");
  try {
    const res = await fetch(`${API_BASE}/dashboard`);
    const data = await res.json();

    const sourceLabel =
      data.data_source === "databricks_tables"
        ? "Databricks Tables"
        : data.data_source === "databricks"
          ? "Databricks Live"
          : "Mock JSON";

    const isLive = data.data_source === "databricks" || data.data_source === "databricks_tables";
    if (sourceBadge) {
      sourceBadge.innerHTML = `<span class="badge-dot${isLive ? "" : " mock"}"></span> S3-D-08 · ${sourceLabel}`;
    }

    statsGrid.innerHTML = `
      <div class="stat-card info">
        <div class="stat-top">
          <span class="label">Total Pipelines</span>
          <span class="stat-icon">${STAT_ICONS.info}</span>
        </div>
        <div class="value">${data.total_pipelines}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-top">
          <span class="label">Successful</span>
          <span class="stat-icon">${STAT_ICONS.success}</span>
        </div>
        <div class="value">${data.success_count}</div>
      </div>
      <div class="stat-card danger">
        <div class="stat-top">
          <span class="label">Failed</span>
          <span class="stat-icon">${STAT_ICONS.danger}</span>
        </div>
        <div class="value">${data.failed_count}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-top">
          <span class="label">Potential Savings</span>
          <span class="stat-icon">${STAT_ICONS.warning}</span>
        </div>
        <div class="value">₹${(data.potential_monthly_savings_inr / 1000).toFixed(0)}K</div>
      </div>
    `;

    if (pipelineCount) {
      pipelineCount.textContent = `${data.pipelines.length} runs`;
    }

    allPipelines = data.pipelines;
    renderPipelineList(filterPipelines(allPipelines, pipelineSearch?.value || ""));

    if (lastUpdated) {
      lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
    }
  } catch (err) {
    statsGrid.innerHTML = `<div class="stat-card error-card">Failed to load dashboard. Check that Flask is running.</div>`;
    pipelineList.innerHTML = "";
  } finally {
    refreshBtn.classList.remove("spinning");
  }
}

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n/g, "<br>");
}

function appendMessage(role, content, meta = {}) {
  const div = document.createElement("div");
  div.className = `message ${role}`;

  const avatar = role === "user" ? AVATAR_USER : AVATAR_BOT;
  let inner = meta.typing
    ? `<span class="typing">Analyzing pipeline data<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></span>`
    : formatMarkdown(content);

  if (meta.intent && role === "assistant") {
    const confidenceLabel =
      meta.confidence != null ? ` · ${Math.round(meta.confidence * 100)}%` : "";
    inner = `<span class="intent-tag">${meta.intent.replace(/_/g, " ")}${confidenceLabel}</span>` + inner;
  }

  if (role === "assistant" && !meta.typing && Array.isArray(meta.sources) && meta.sources.length) {
    const sourceNames = meta.sources
      .map((s) => s.name)
      .filter(Boolean)
      .slice(0, 4)
      .join(", ");
    if (sourceNames) {
      inner += `<div class="source-ref">Sources: ${sourceNames}</div>`;
    }
  }

  if (role === "assistant" && meta.cached) {
    inner += `<div class="cached-tag">Cached response</div>`;
  }

  if (role === "assistant" && !meta.typing) {
    const queryId = meta.query_id != null ? String(meta.query_id) : "";
    inner += `
      <div class="feedback-row">
        <button class="feedback-btn" data-feedback="up" data-query-id="${queryId}" title="Helpful">👍 Helpful</button>
        <button class="feedback-btn" data-feedback="down" data-query-id="${queryId}" title="Not helpful">👎</button>
      </div>`;
  }

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">${inner}</div>
  `;

  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

async function sendQuery(query) {
  if (!query.trim()) return;

  appendMessage("user", query);
  chatInput.value = "";
  sendBtn.disabled = true;

  const typingEl = appendMessage("assistant", "", { typing: true });

  try {
    const category = categorySelect.value || undefined;
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, category }),
    });

    const data = await res.json();
    typingEl.remove();

    if (data.error) {
      appendMessage("assistant", `Error: ${data.error}`);
    } else {
      appendMessage("assistant", data.response, {
        intent: data.intent,
        query_id: data.query_id,
        confidence: data.confidence,
        sources: data.sources,
        cached: data.cached,
      });
    }
  } catch (err) {
    typingEl.remove();
    appendMessage("assistant", "Sorry, I couldn't reach the backend. Make sure Flask is running on port 5000.");
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

function pipelineQuery(name, status) {
  const label = name.replace(/_/g, " ");
  if (status === "failed" || status === "partial_failure") {
    return `Why did ${name} fail?`;
  }
  return `What is the status of ${label}?`;
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendQuery(chatInput.value);
});

document.querySelectorAll(".suggestion").forEach((btn) => {
  btn.addEventListener("click", () => sendQuery(btn.dataset.query));
});

pipelineList.addEventListener("click", (e) => {
  const item = e.target.closest(".pipeline-item");
  if (!item) return;
  sendQuery(pipelineQuery(item.dataset.pipeline, item.dataset.status));
});

refreshBtn.addEventListener("click", () => {
  showSkeletons();
  loadDashboard();
});

if (pipelineSearch) {
  pipelineSearch.addEventListener("input", () => {
    renderPipelineList(filterPipelines(allPipelines, pipelineSearch.value));
  });
}

chatMessages.addEventListener("click", async (e) => {
  const btn = e.target.closest(".feedback-btn");
  if (!btn) return;
  btn.closest(".feedback-row").querySelectorAll(".feedback-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");

  const queryId = btn.dataset.queryId;
  if (!queryId) return;

  try {
    await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_id: Number(queryId), feedback: btn.dataset.feedback }),
    });
  } catch (_err) {
    /* keep the visual state even if logging fails */
  }
});

loadDashboard();
setInterval(loadDashboard, 60000);
