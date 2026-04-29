const JSONL_URL = "https://raw.githubusercontent.com/edwin813/roleplay-coach/latency-lab-results/latency_lab/experiments.jsonl";
const REFRESH_MS = 60000;

let chart = null;
let lastFetchedAt = null;

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
  if (sec < 3600) return `${Math.floor(sec/60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec/3600)}h ago`;
  return `${Math.floor(sec/86400)}d ago`;
}

function decisionTag(d) {
  const cls = { WIN: "tag-win", LOSS: "tag-loss", ERROR: "tag-error" }[d] || "tag-pending";
  return `<span class="tag ${cls}">${d || "PENDING"}</span>`;
}

function shortModel(m) {
  return (m || "?").replace(/^claude-/, "").replace(/-202\d.*$/, "");
}
function shortTts(m) {
  return (m || "?").replace(/^eleven_/, "").replace(/_v2_5$/, "");
}

function render(rows) {
  if (!rows.length) {
    document.getElementById("status-text").textContent = "no experiments yet";
    return;
  }

  const valid = rows.filter(r => r.results && r.results.total_ms);
  const latest = rows[rows.length - 1];

  // Summary cards
  const sortedByP95 = [...valid].sort((a,b) => a.results.total_ms.p95 - b.results.total_ms.p95);
  const best = sortedByP95[0];
  if (best) {
    document.getElementById("best-p95").textContent = `${Math.round(best.results.total_ms.p95)}ms`;
    document.getElementById("best-config").textContent = `${shortModel(best.config.claude_model)} · q=${best.results.quality_score}`;
  }
  document.getElementById("latest-p95").textContent = latest.results?.total_ms ? `${Math.round(latest.results.total_ms.p95)}ms` : "—";
  document.getElementById("latest-decision").innerHTML = decisionTag(latest.decision);
  document.getElementById("run-count").textContent = rows.length;
  const counts = rows.reduce((acc, r) => { acc[r.decision || "PENDING"] = (acc[r.decision || "PENDING"] || 0) + 1; return acc; }, {});
  document.getElementById("run-counts-detail").textContent = `${counts.WIN || 0}W · ${counts.LOSS || 0}L · ${counts.ERROR || 0}E`;
  document.getElementById("latest-quality").textContent = latest.results?.quality_score ?? "—";

  // Timeline chart
  const labels = valid.map(r => new Date(r.timestamp).toLocaleString([], { month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit" }));
  const p95Data = valid.map(r => r.results.total_ms.p95);
  const p50Data = valid.map(r => r.results.total_ms.p50);
  const qualityData = valid.map(r => r.results.quality_score * 100); // scale to ms-ish for visibility
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
        { label: "p95 (ms)", data: p95Data, borderColor: "#58a6ff", backgroundColor: "rgba(88,166,255,0.1)", pointBackgroundColor: pointColors, pointBorderColor: pointColors, pointRadius: 5, tension: 0.2, yAxisID: "y" },
        { label: "p50 (ms)", data: p50Data, borderColor: "#7d8590", borderDash: [4,4], pointRadius: 0, tension: 0.2, yAxisID: "y" },
        { label: "quality ×100", data: qualityData, borderColor: "#3fb950", borderDash: [2,4], pointRadius: 0, tension: 0.2, yAxisID: "y" }
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
              return [`model: ${shortModel(r.config.claude_model)}`, `tts: ${shortTts(r.config.tts_model)}`, `decision: ${r.decision}`, r.notes ? `notes: ${r.notes.slice(0, 80)}` : ""].filter(Boolean);
            }
          }
        }
      },
      scales: {
        x: { ticks: { color: "#7d8590", maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: "#21262d" } },
        y: { ticks: { color: "#7d8590" }, grid: { color: "#21262d" } }
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
      <td>${r.config.prompt_caching ? "✓" : "·"}</td>
      <td class="num">${Math.round(r.results.total_ms.p95)}</td>
      <td class="num">${Math.round(r.results.total_ms.p50)}</td>
      <td class="num">${r.results.quality_score}</td>
      <td>${fmtAgo(r.timestamp)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Latest JSON
  document.getElementById("latest-json").textContent = JSON.stringify(latest, null, 2);

  // Status
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
    lastFetchedAt = Date.now();
  } catch (e) {
    document.getElementById("status-text").textContent = `error: ${e.message}`;
    document.getElementById("status-dot").className = "dot dot-error";
  }
}

tick();
setInterval(tick, REFRESH_MS);
