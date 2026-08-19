/* ==========================================================================
   AI Cyber Attack Response Coordinator — Dashboard logic
   Vanilla JS, same-origin fetch calls against the FastAPI backend in api/app.py.
   No build step required.
   ========================================================================== */

const API = ""; // same-origin

const els = {
  healthDot: document.getElementById("healthDot"),
  healthText: document.getElementById("healthText"),
  runBtn: document.getElementById("runBtn"),
  uploadBtn: document.getElementById("uploadBtn"),
  csvFileInput: document.getElementById("csvFileInput"),
  csvSourceLabel: document.getElementById("csvSourceLabel"),
  uploadStatus: document.getElementById("uploadStatus"),
  lastRun: document.getElementById("lastRun"),
  incidentsBody: document.getElementById("incidentsBody"),
  incidentCount: document.getElementById("incidentCount"),
  emptyState: document.getElementById("emptyState"),
  incidentsTable: document.getElementById("incidentsTable"),
  statLogs: document.getElementById("statLogs"),
  statIncidents: document.getElementById("statIncidents"),
  statResponded: document.getElementById("statResponded"),
  statPending: document.getElementById("statPending"),
  statAlerts: document.getElementById("statAlerts"),
  sevBars: document.getElementById("sevBars"),
  execSummary: document.getElementById("execSummary"),
  pulseReading: document.getElementById("pulseReading"),
  pulseLine: document.getElementById("pulseLine"),
  pulseFill: document.getElementById("pulseFill"),
  pulseDots: document.getElementById("pulseDots"),
  workflowTrack: document.getElementById("workflowTrack"),
  workflowStatus: document.getElementById("workflowStatus"),
  tailPanel: document.getElementById("tailPanel"),
  tailToggle: document.getElementById("tailToggle"),
  tailBody: document.getElementById("tailBody"),
  overlay: document.getElementById("overlay"),
  drawer: document.getElementById("drawer"),
  drawerId: document.getElementById("drawerId"),
  drawerTitle: document.getElementById("drawerTitle"),
  drawerBody: document.getElementById("drawerBody"),
  drawerFooter: document.getElementById("drawerFooter"),
  drawerClose: document.getElementById("drawerClose"),
  toast: document.getElementById("toast"),
};

let state = {
  incidents: [],
  activeIncidentId: null,
  workflowPollTimer: null,
  activeCsvPath: null,   // set after a successful upload; null = use bundled sample data
};

/* ---------------------------------------------------------------------- */
/* CSV upload                                                            */
/* ---------------------------------------------------------------------- */

function setUploadStatus(message, kind) {
  els.uploadStatus.hidden = !message;
  els.uploadStatus.textContent = message || "";
  els.uploadStatus.className = "upload-status" + (kind ? ` ${kind}` : "");
}

function setCsvSourceLabel(text, isCustom) {
  els.csvSourceLabel.textContent = text;
  els.csvSourceLabel.title = isCustom
    ? "Custom uploaded dataset — the next pipeline run will use this file"
    : "Bundled sample dataset";
  els.csvSourceLabel.classList.toggle("custom", !!isCustom);
}

els.uploadBtn.addEventListener("click", () => els.csvFileInput.click());

els.csvFileInput.addEventListener("change", async () => {
  const file = els.csvFileInput.files && els.csvFileInput.files[0];
  els.csvFileInput.value = ""; // allow re-selecting the same filename later
  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".csv")) {
    setUploadStatus("Only .csv files are accepted.", "error");
    return;
  }

  els.uploadBtn.disabled = true;
  els.uploadBtn.textContent = "Uploading\u2026";
  setUploadStatus(`Uploading ${file.name}\u2026`, null);

  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API}/pipeline/upload-csv`, { method: "POST", body: formData });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_e) {}
      throw new Error(detail);
    }
    const result = await res.json();

    state.activeCsvPath = result.csv_path;
    setCsvSourceLabel(`${result.filename} (${result.rows} rows)`, true);
    setUploadStatus(
      `Loaded ${result.filename} \u2014 ${result.rows} rows, ${result.columns.length} columns. Click "Run pipeline" to process it.`,
      "success"
    );
    showToast(`CSV uploaded: ${result.rows} rows ready`, "success");
  } catch (e) {
    setUploadStatus(`Upload failed: ${e.message}`, "error");
    showToast(`CSV upload failed: ${e.message}`, "error");
  } finally {
    els.uploadBtn.disabled = false;
    els.uploadBtn.textContent = "Upload CSV";
  }
});

/* ---------------------------------------------------------------------- */
/* Agent workflow orchestration panel                                    */
/* ---------------------------------------------------------------------- */

const WORKFLOW_STAGES = [
  { key: "detection", label: "Detection", icon: "\u{1F50E}" },
  { key: "analysis", label: "Analysis", icon: "\u{1F9EA}" },
  { key: "coordination", label: "Coordination", icon: "\u{1F5C2}\uFE0F" },
  { key: "decision", label: "Decision", icon: "\u2696\uFE0F" },
  { key: "response", label: "Response", icon: "\u{1F6A8}" },
  { key: "alert", label: "Alert", icon: "\u{1F4E3}" },
  { key: "report", label: "Report", icon: "\u{1F4CA}" },
];

function buildWorkflowTrack() {
  els.workflowTrack.innerHTML = WORKFLOW_STAGES.map((stage, i) => `
    <div class="wf-node" data-status="pending" data-stage="${stage.key}">
      <div class="wf-node__body">
        <div class="wf-node__dot">${stage.icon}</div>
        <div class="wf-node__label">${stage.label}</div>
        <div class="wf-node__meta" data-meta></div>
      </div>
      ${i < WORKFLOW_STAGES.length - 1 ? '<div class="wf-node__connector"></div>' : ""}
    </div>
  `).join("");
}

function renderWorkflow(stageTimings, pipelineStatus) {
  if (!stageTimings) return;
  els.workflowStatus.textContent = pipelineStatus || "idle";
  WORKFLOW_STAGES.forEach((stage) => {
    const node = els.workflowTrack.querySelector(`.wf-node[data-stage="${stage.key}"]`);
    if (!node) return;
    const info = stageTimings[stage.key] || { status: "pending", duration_seconds: null };
    node.dataset.status = info.status;
    const meta = node.querySelector("[data-meta]");
    if (info.status === "running") meta.textContent = "running\u2026";
    else if (info.status === "done") meta.textContent = `${Math.round((info.duration_seconds || 0) * 1000)}ms`;
    else if (info.status === "error") meta.textContent = "failed";
    else meta.textContent = "";
  });
}

async function pollWorkflowStatus() {
  try {
    const data = await api("/pipeline/status");
    renderWorkflow(data.stage_timings, data.pipeline_status);
    return data.pipeline_status;
  } catch (_e) {
    return null;
  }
}

function startWorkflowPolling() {
  stopWorkflowPolling();
  state.workflowPollTimer = setInterval(pollWorkflowStatus, 400);
}

function stopWorkflowPolling() {
  if (state.workflowPollTimer) {
    clearInterval(state.workflowPollTimer);
    state.workflowPollTimer = null;
  }
}

buildWorkflowTrack();

/* ---------------------------------------------------------------------- */
/* Helpers                                                               */
/* ---------------------------------------------------------------------- */

function showToast(message, kind) {
  els.toast.textContent = message;
  els.toast.className = "toast show" + (kind ? " " + kind : "");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { els.toast.className = "toast"; }, 3200);
}

async function api(path, options) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_e) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function fmtTime(d) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/* ---------------------------------------------------------------------- */
/* Health check                                                          */
/* ---------------------------------------------------------------------- */

async function checkHealth() {
  try {
    const data = await api("/health");
    els.healthDot.className = "status-dot online";
    els.healthText.textContent = `online \u00b7 ${data.environment}`;
  } catch (e) {
    els.healthDot.className = "status-dot offline";
    els.healthText.textContent = "backend unreachable";
  }
}

/* ---------------------------------------------------------------------- */
/* Risk pulse (signature element)                                       */
/* ---------------------------------------------------------------------- */

function renderPulse(incidents) {
  const w = 800, h = 64, pad = 8;
  els.pulseDots.innerHTML = "";

  if (!incidents.length) {
    els.pulseLine.setAttribute("d", `M0,${h - pad} L${w},${h - pad}`);
    els.pulseFill.setAttribute("d", `M0,${h} L0,${h - pad} L${w},${h - pad} L${w},${h} Z`);
    els.pulseReading.textContent = "no active incidents";
    return;
  }

  const sorted = [...incidents].sort((a, b) => a.priority_rank - b.priority_rank);
  const n = sorted.length;
  const stepX = n > 1 ? (w - pad * 2) / (n - 1) : 0;

  const points = sorted.map((inc, i) => {
    const x = pad + stepX * i;
    const y = h - pad - (inc.risk_score / 100) * (h - pad * 2);
    return [x, y, inc];
  });

  let linePath = `M${points[0][0]},${points[0][1]}`;
  for (let i = 1; i < points.length; i++) linePath += ` L${points[i][0]},${points[i][1]}`;
  els.pulseLine.setAttribute("d", linePath);

  let fillPath = `M${points[0][0]},${h - pad}`;
  points.forEach(([x, y]) => { fillPath += ` L${x},${y}`; });
  fillPath += ` L${points[points.length - 1][0]},${h - pad} Z`;
  els.pulseFill.setAttribute("d", fillPath);

  const colors = { Critical: "#fb5c5c", High: "#ffa94d", Medium: "#f5d142", Low: "#6ee7a0" };
  points.forEach(([x, y, inc]) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", 3);
    circle.setAttribute("class", "pulse__dot");
    circle.setAttribute("stroke", colors[inc.severity] || "#2dd4bf");
    els.pulseDots.appendChild(circle);
  });

  const avg = incidents.reduce((s, i) => s + i.risk_score, 0) / incidents.length;
  const top = sorted[0];
  els.pulseReading.textContent = `avg ${avg.toFixed(1)} \u00b7 peak ${top.risk_score.toFixed(1)} (${top.attack_type})`;
}

/* ---------------------------------------------------------------------- */
/* Incident table + stats                                                */
/* ---------------------------------------------------------------------- */

function renderIncidents(incidents) {
  state.incidents = incidents;
  els.incidentCount.textContent = `${incidents.length} incident${incidents.length === 1 ? "" : "s"}`;

  if (!incidents.length) {
    els.incidentsTable.style.display = "none";
    els.emptyState.style.display = "block";
    renderPulse([]);
    return;
  }
  els.incidentsTable.style.display = "table";
  els.emptyState.style.display = "none";

  const sorted = [...incidents].sort((a, b) => (a.priority_rank || 0) - (b.priority_rank || 0));

  els.incidentsBody.innerHTML = sorted.map((inc) => {
    const d = inc.data || inc;
    const status = d.response_status || "queued";
    return `
      <tr data-severity="${d.severity}" data-id="${d.incident_id}">
        <td class="rank">${d.priority_rank ?? "-"}</td>
        <td class="incident-id">${d.incident_id}</td>
        <td>${d.attack_type}</td>
        <td><span class="badge badge--${d.severity}">${d.severity}</span></td>
        <td class="risk-score">${Number(d.risk_score).toFixed(1)}</td>
        <td>${d.asset || d.destination_ip || "-"}</td>
        <td class="mono">${d.decided_action || d.action || "-"}</td>
        <td><span class="status-tag ${status}">${status}</span></td>
      </tr>
    `;
  }).join("");

  Array.from(els.incidentsBody.querySelectorAll("tr")).forEach((row) => {
    row.addEventListener("click", () => openDrawer(row.dataset.id));
  });

  renderPulse(sorted.map((inc) => inc.data || inc));
}

function renderStats(summary) {
  els.statLogs.textContent = summary.logs_processed ?? "\u2014";
  els.statIncidents.textContent = summary.incidents ?? "\u2014";
  els.statAlerts.textContent = summary.alerts ?? "\u2014";

  const responses = summary.responses ?? 0;
  els.statResponded.textContent = responses;

  const breakdown = summary.severity_breakdown || {};
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
  ["Critical", "High", "Medium", "Low"].forEach((sev, idx) => {
    const count = breakdown[sev] || 0;
    const row = els.sevBars.children[idx];
    row.querySelector(".sev-fill").style.width = `${(count / total) * 100}%`;
    row.querySelector(".sev-count").textContent = count;
  });

  els.execSummary.textContent = summary.executive_summary || "No summary available.";
  els.execSummary.classList.toggle("muted", !summary.executive_summary);
}

async function computePendingCount() {
  const pending = state.incidents.filter((inc) => {
    const d = inc.data || inc;
    return d.response_status === "pending_approval";
  }).length;
  els.statPending.textContent = pending;
}

/* ---------------------------------------------------------------------- */
/* Drawer                                                                */
/* ---------------------------------------------------------------------- */

function field(label, value) {
  return `<div class="field"><div class="field__label">${label}</div><div class="field__value">${value ?? "&mdash;"}</div></div>`;
}
function fieldMono(label, value) {
  return `<div class="field"><div class="field__label">${label}</div><div class="field__value mono">${value ?? "&mdash;"}</div></div>`;
}

async function openDrawer(incidentId) {
  state.activeIncidentId = incidentId;
  els.drawerId.textContent = incidentId;
  els.drawerTitle.textContent = "Loading\u2026";
  els.drawerBody.innerHTML = "";
  els.drawerFooter.innerHTML = "";
  els.overlay.classList.add("open");
  els.drawer.classList.add("open");

  try {
    const record = await api(`/incidents/${incidentId}`);
    const d = record.data || record;

    els.drawerTitle.textContent = `${d.attack_type} \u00b7 ${d.severity}`;
    els.drawerBody.innerHTML = [
      field("Risk score", `${Number(d.risk_score).toFixed(1)} / 100`),
      field("Source IP", d.source_ip),
      field("Asset", `${d.asset || "\u2014"} (criticality: ${d.asset_criticality || "\u2014"})`),
      fieldMono("MITRE ATT&CK", d.mitre_attack_technique),
      field("Impact", d.impact),
      field("Decided action", d.decided_action || d.action || "\u2014"),
      field("Justification", d.decision_justification || d.justification || "\u2014"),
      field("Response status", `<span class="status-tag ${d.response_status || ""}">${d.response_status || "not yet responded"}</span>`),
      field("Runbook note", d.runbook_note || "\u2014"),
    ].join("");

    els.drawerFooter.innerHTML = "";
    if (d.requires_human_approval && d.response_status === "pending_approval") {
      const approveBtn = document.createElement("button");
      approveBtn.className = "btn";
      approveBtn.textContent = "Approve action";
      approveBtn.addEventListener("click", () => approveIncident(incidentId, approveBtn));
      els.drawerFooter.appendChild(approveBtn);
    }
    const closeBtn = document.createElement("button");
    closeBtn.className = "btn btn--ghost";
    closeBtn.textContent = "Close";
    closeBtn.addEventListener("click", closeDrawer);
    els.drawerFooter.appendChild(closeBtn);
  } catch (e) {
    els.drawerTitle.textContent = "Failed to load incident";
    els.drawerBody.innerHTML = `<div class="field__value">${e.message}</div>`;
  }
}

function closeDrawer() {
  els.overlay.classList.remove("open");
  els.drawer.classList.remove("open");
}

async function approveIncident(incidentId, btn) {
  btn.disabled = true;
  const original = btn.textContent;
  btn.innerHTML = `<span class="spinner"></span>Approving\u2026`;
  try {
    const result = await api(`/incidents/${incidentId}/approve`, { method: "POST" });
    showToast(`Action "${result.action}" ${result.status} for ${incidentId}`, "success");
    closeDrawer();
    await refreshIncidents();
    await loadEvents();
  } catch (e) {
    showToast(`Approval failed: ${e.message}`, "error");
    btn.disabled = false;
    btn.textContent = original;
  }
}

els.drawerClose.addEventListener("click", closeDrawer);
els.overlay.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

/* ---------------------------------------------------------------------- */
/* Event tail                                                            */
/* ---------------------------------------------------------------------- */

async function loadEvents() {
  try {
    const events = await api("/events");
    if (!events.length) {
      els.tailBody.innerHTML = `<div class="tail__line">No events yet.</div>`;
      return;
    }
    els.tailBody.innerHTML = events.slice(-60).reverse().map((ev) => {
      const time = new Date(ev.created_at).toLocaleTimeString();
      return `<div class="tail__line">[${time}] <span class="agent">${ev.agent}</span> <span class="type">${ev.event_type}</span></div>`;
    }).join("");
  } catch (e) {
    els.tailBody.innerHTML = `<div class="tail__line">Could not load events: ${e.message}</div>`;
  }
}

els.tailToggle.addEventListener("click", () => {
  els.tailPanel.classList.toggle("collapsed");
});

/* ---------------------------------------------------------------------- */
/* Incident refresh (without a full pipeline run)                        */
/* ---------------------------------------------------------------------- */

async function refreshIncidents() {
  try {
    const incidents = await api("/incidents");
    renderIncidents(incidents);
    computePendingCount();
  } catch (e) {
    showToast(`Could not refresh incidents: ${e.message}`, "error");
  }
}

/* ---------------------------------------------------------------------- */
/* Run pipeline                                                          */
/* ---------------------------------------------------------------------- */

async function runPipeline() {
  els.runBtn.disabled = true;
  els.runBtn.innerHTML = `<span class="spinner"></span>Running pipeline\u2026`;
  els.healthDot.className = "status-dot busy";
  startWorkflowPolling();

  try {
    const summary = await api("/pipeline/run", {
      method: "POST",
      body: JSON.stringify({ csv_path: state.activeCsvPath, clear_memory: true }),
    });
    renderWorkflow(summary.stage_timings, "idle");
    renderStats(summary);
    await refreshIncidents();
    await loadEvents();
    els.lastRun.textContent = `last run ${fmtTime(new Date())} \u00b7 ${summary.elapsed_seconds}s`;
    showToast(`Pipeline complete: ${summary.incidents} incident(s) triaged`, "success");
  } catch (e) {
    await pollWorkflowStatus();
    showToast(`Pipeline run failed: ${e.message}`, "error");
  } finally {
    stopWorkflowPolling();
    els.runBtn.disabled = false;
    els.runBtn.textContent = "Run pipeline";
    checkHealth();
  }
}

els.runBtn.addEventListener("click", runPipeline);

/* ---------------------------------------------------------------------- */
/* Init                                                                   */
/* ---------------------------------------------------------------------- */

async function init() {
  setCsvSourceLabel("sample data", false);
  await checkHealth();
  await refreshIncidents();
  await loadEvents();
  await pollWorkflowStatus();

  // Try to hydrate the right-rail stats + summary from the last saved report,
  // if one already exists on disk from a prior run.
  try {
    const summary = await api("/reports/summary");
    renderStats({
      severity_breakdown: summary.severity_breakdown,
      executive_summary: summary.executive_summary,
      incidents: summary.incident_count,
    });
  } catch (_e) {
    // No prior report yet — fine, stats stay at placeholder state.
  }

  setInterval(checkHealth, 15000);
}

init();
