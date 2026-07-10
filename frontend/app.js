const API_BASE = window.location.origin;

const statsGrid = document.getElementById("stats-grid");
const pipelineList = document.getElementById("pipeline-list");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const categorySelect = document.getElementById("category-select");

async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard`);
    const data = await res.json();

    const sourceLabel =
      data.data_source === "databricks_tables"
        ? "Databricks Tables"
        : data.data_source === "databricks"
          ? "Databricks Live"
          : "Mock JSON";
    const badge = document.querySelector(".badge");
    if (badge) badge.textContent = `S3-D-08 · ${sourceLabel}`;

    statsGrid.innerHTML = `
      <div class="stat-card info">
        <div class="label">Total Pipelines</div>
        <div class="value">${data.total_pipelines}</div>
      </div>
      <div class="stat-card success">
        <div class="label">Successful</div>
        <div class="value">${data.success_count}</div>
      </div>
      <div class="stat-card danger">
        <div class="label">Failed</div>
        <div class="value">${data.failed_count}</div>
      </div>
      <div class="stat-card warning">
        <div class="label">Potential Savings</div>
        <div class="value">₹${(data.potential_monthly_savings_inr / 1000).toFixed(0)}K</div>
      </div>
    `;

    pipelineList.innerHTML = data.pipelines
      .map(
        (p) => `
        <div class="pipeline-item">
          <div>
            <div class="name">${p.pipeline_name.replace(/_/g, " ")}</div>
            <div class="time">${formatTime(p.run_time)}</div>
          </div>
          <span class="status-badge ${p.status}">${p.status.replace("_", " ")}</span>
        </div>
      `
      )
      .join("");
  } catch (err) {
    statsGrid.innerHTML = `<div class="stat-card danger">Failed to load dashboard</div>`;
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
    .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
    .replace(/\n/g, "<br>");
}

function appendMessage(role, content, meta = {}) {
  const div = document.createElement("div");
  div.className = `message ${role}`;

  const avatar = role === "user" ? "👤" : "🤖";
  let inner = formatMarkdown(content);

  if (meta.intent && role === "assistant") {
    inner = `<span class="intent-tag">${meta.intent.replace(/_/g, " ")}</span>` + inner;
  }

  if (role === "assistant" && !meta.typing) {
    inner += `
      <div class="feedback-row">
        <button class="feedback-btn" data-feedback="up" title="Helpful">👍</button>
        <button class="feedback-btn" data-feedback="down" title="Not helpful">👎</button>
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

  const typingEl = appendMessage("assistant", "Analyzing pipeline data...", { typing: true });
  typingEl.querySelector(".message-content").classList.add("typing");

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
      appendMessage("assistant", data.response, { intent: data.intent });
    }
  } catch (err) {
    typingEl.remove();
    appendMessage("assistant", "Sorry, I couldn't reach the backend. Make sure Flask is running on port 5000.");
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendQuery(chatInput.value);
});

document.querySelectorAll(".suggestion").forEach((btn) => {
  btn.addEventListener("click", () => sendQuery(btn.dataset.query));
});

chatMessages.addEventListener("click", (e) => {
  if (e.target.classList.contains("feedback-btn")) {
    e.target.style.opacity = "1";
    e.target.style.borderColor = "var(--primary)";
  }
});

loadDashboard();
setInterval(loadDashboard, 60000);
