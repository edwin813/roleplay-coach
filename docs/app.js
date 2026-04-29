const JSONL_URL = "https://raw.githubusercontent.com/edwin813/roleplay-coach/latency-lab-results/latency_lab/experiments.jsonl";
const REFRESH_MS = 60000;

let chart = null;

async function fetchExperiments() {
  const url = `${JSONL_URL}?t=${Date.now()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetch failed: ${res.status}`);
  const text = await res.text();
  return text.split("\n").filter(l => l.trim()).map(l => JSON.parse(l));
}

function fmtAgo(iso) {
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec/60)} min ago`;
  if (sec < 86400) return `${Math.floor(sec/3600)} hr ago`;
  return `${Math.floor(sec/86400)} days ago`;
}

function fmtSec(ms) {
  if (ms == null) return "—";
  return `${(ms/1000).toFixed(1)}s`;
}

function decisionTag(d) {
  const map = {
    WIN: { cls: "tag-win", text: "🎉 Faster" },
    LOSS: { cls: "tag-loss", text: "⏸ Didn't help" },
    ERROR: { cls: "tag-error", text: "⚠️ Errored" },
  };
  const m = map[d] || { cls: "tag-pending", text: d || "Pending" };
  return `<span class="tag ${m.cls}">${m.text}</span>`;
}

function shortModel(m) {
  return (m || "?").replace(/^claude-/, "").replace(/-202\d.*$/, "");
}
function shortTts(m) {
  return (m || "?").replace(/^eleven_/, "").replace(/_v2_5$/, "");
}

const FIELD_LABEL = {
  claude_model: "AI model",
  claude_max_tokens: "reply length cap",
  claude_streaming: "streaming",
  prompt_caching: "caching",
  system_prompt_version: "prompt version",
  tts_provider: "voice provider",
  tts_model: "voice",
  tts_voice_id: "voice ID",
};

function diffConfig(now, prev) {
  if (!prev) return [];
  const out = [];
  for (const key of Object.keys(FIELD_LABEL)) {
    if (now[key] !== prev[key]) {
      let v = now[key];
      if (typeof v === "boolean") v = v ? "on" : "off";
      out.push(`${FIELD_LABEL[key]} = ${v}`);
    }
  }
  return out;
}

function render(rows) {
  if (!rows.length) {
    document.getElementById("status-text").textContent = "no experiments yet";
    document.getElementById("latest-summary").textContent = "No experiments yet. The first one will appear here within an hour.";
    return;
  }

  const valid = rows.filter(r => r.results && r.results.total_ms);
  const latest = rows[rows.length - 1];
  const prior = rows.length >= 2 ? rows[rows.length - 2] : null;

  // Summary cards
  const sortedByP95 = [...valid].sort((a,b) => a.results.total_ms.p95 - b.results.total_ms.p95);
  const best = sortedByP95[0];
  if (best) {
    document.getElementById("best-p95").textContent = fmtSec(best.results.total_ms.p95);
    document.getElementById("best-config").textContent = `${shortModel(best.config.claude_model)} · naturalness ${best.results.quality_score}/10`;
  }
  document.getElementById("latest-p95").textContent = latest.results?.total_ms ? fmtSec(latest.results.total_ms.p95) : "—";
  document.getElementById("latest-decision").innerHTML = decisionTag(latest.decision);
  document.getElementById("run-count").textContent = rows.length;
  const counts = rows.reduce((acc, r) => { acc[r.decision || "PENDING"] = (acc[r.decision || "PENDING"] || 0) + 1; return acc; }, {});
  document.getElementById("run-counts-detail").textContent = `${counts.WIN || 0} improvements · ${counts.LOSS || 0} didn't help · ${counts.ERROR || 0} errors`;
  document.getElementById("latest-quality").textContent = latest.results?.quality_score ?? "—";

  // Timeline chart
  const labels = valid.map(r => new Date(r.timestamp).toLocaleString([], { month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit" }));
  const p95Data = valid.map(r => r.results.total_ms.p95 / 1000);
  const p50Data = valid.map(r => r.results.total_ms.p50 / 1000);
  const pointColors = valid.map(r => {
    const d = r.decision || "PENDING";
    return d === "WIN" ? "#3fb950" : d === "LOSS" ? "#f85149" : d === "ERROR" ? "#d29922" : "#7d8590";
  });

  const ctx = document.getElementById("timeline").getContext("2d");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Worst case (seconds)", data: p95Data, borderColor: "#58a6ff", backgroundColor: "rgba(88,166,255,0.1)", pointBackgroundColor: pointColors, pointBorderColor: pointColors, pointRadius: 5, tension: 0.2 },
        { label: "Typical (seconds)", data: p50Data, borderColor: "#7d8590", borderDash: [4,4], pointRadius: 0, tension: 0.2 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#e6edf3", font: { family: "ui-monospace, monospace", size: 11 } } },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const r = valid[ctx.dataIndex];
              const result = { WIN: "🎉 Faster", LOSS: "⏸ Didn't help", ERROR: "⚠️ Errored" }[r.decision] || r.decision;
              return [
                `AI model: ${shortModel(r.config.claude_model)}`,
                `Voice: ${shortTts(r.config.tts_model)}`,
                `Naturalness: ${r.results.quality_score}/10`,
                `Result: ${result}`,
                r.notes ? `Notes: ${r.notes.slice(0, 80)}` : ""
              ].filter(Boolean);
            }
          }
        }
      },
      scales: {
        x: { ticks: { color: "#7d8590", maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: "#21262d" } },
        y: { ticks: { color: "#7d8590", callback: (v) => `${v}s` }, grid: { color: "#21262d" }, title: { display: true, text: "Seconds (lower is better)", color: "#7d8590" } }
      }
    }
  });

  // Leaderboard
  const tbody = document.querySelector("#leaderboard tbody");
  tbody.innerHTML = "";
  sortedByP95.slice(0, 10).forEach((r, i) => {
    const tr = document.createElement("tr");
    if (r.decision === "WIN") tr.classList.add("win-row");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${shortModel(r.config.claude_model)}</td>
      <td>${shortTts(r.config.tts_model)}</td>
      <td class="num">${r.config.claude_max_tokens || "—"}</td>
      <td>${r.config.prompt_caching ? "on" : "off"}</td>
      <td class="num">${fmtSec(r.results.total_ms.p95)}</td>
      <td class="num">${fmtSec(r.results.total_ms.p50)}</td>
      <td class="num">${r.results.quality_score}/10</td>
      <td>${fmtAgo(r.timestamp)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Latest experiment — plain summary
  const summaryEl = document.getElementById("latest-summary");
  const decisionLabel = { WIN: "🎉 Faster!", LOSS: "⏸ Didn't help — reverted", ERROR: "⚠️ Run errored", PENDING: "🔬 Run finished" }[latest.decision] || latest.decision;
  const summaryParts = [`<div class="latest-decision">${decisionLabel}</div>`];

  const changes = diffConfig(latest.config || {}, prior?.config || null);
  if (changes.length) {
    summaryParts.push(`<div class="latest-row"><span class="latest-key">Change tested:</span> ${changes.join(", ")}</div>`);
  }

  if (latest.results?.total_ms) {
    const t = latest.results.total_ms;
    let timeLine = `~${fmtSec(t.p50)} typical, ~${fmtSec(t.p95)} worst case`;
    if (prior?.results?.total_ms) {
      const pt = prior.results.total_ms;
      timeLine += ` <span class="muted">(was ~${fmtSec(pt.p50)} / ~${fmtSec(pt.p95)})</span>`;
    }
    summaryParts.push(`<div class="latest-row"><span class="latest-key">Reply time:</span> ${timeLine}</div>`);
  }

  if (latest.results?.quality_score != null) {
    let qLine = `<b>${latest.results.quality_score}/10</b>`;
    if (prior?.results?.quality_score != null) {
      qLine += ` <span class="muted">(was ${prior.results.quality_score}/10)</span>`;
    }
    summaryParts.push(`<div class="latest-row"><span class="latest-key">How natural the AI sounded:</span> ${qLine}</div>`);
  }

  if (latest.notes) {
    summaryParts.push(`<div class="latest-row latest-notes">${latest.notes}</div>`);
  }
  if (latest.decision === "ERROR" && latest.errors?.length) {
    summaryParts.push(`<div class="latest-row latest-error">Error: ${latest.errors[0]}</div>`);
  }

  summaryParts.push(`<div class="latest-row muted">Ran ${fmtAgo(latest.timestamp)}</div>`);
  summaryEl.innerHTML = summaryParts.join("");

  document.getElementById("latest-json").textContent = JSON.stringify(latest, null, 2);

  // Status dot
  const ageMin = (Date.now() - new Date(latest.timestamp).getTime()) / 60000;
  const dot = document.getElementById("status-dot");
  const txt = document.getElementById("status-text");
  if (ageMin < 5) { dot.className = "dot dot-fresh"; txt.textContent = "fresh"; }
  else if (ageMin < 90) { dot.className = "dot dot-idle"; txt.textContent = "idle"; }
  else { dot.className = "dot dot-stale"; txt.textContent = "stale"; }
  document.getElementById("last-updated").textContent = `latest run ${fmtAgo(latest.timestamp)}`;
}

async function tick() {
  try {
    const rows = await fetchExperiments();
    render(rows);
  } catch (e) {
    document.getElementById("status-text").textContent = `error: ${e.message}`;
    document.getElementById("status-dot").className = "dot dot-error";
  }
}

tick();
setInterval(tick, REFRESH_MS);
