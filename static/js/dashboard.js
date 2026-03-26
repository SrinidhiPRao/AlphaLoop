/* dashboard.js */

let currentHorizon = '1M';
let equityChart = null;
let refreshInterval = null;
let portfolioData = [];

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupHorizonSelector();
  loadAll();
  refreshInterval = setInterval(softRefresh, 30000);
  startClock();
});

function startClock() {
  let seconds = 0;
  setInterval(() => {
    seconds++;
    const el = document.getElementById('last-updated');
    if (el) el.textContent = seconds < 60
      ? `${seconds}s ago`
      : `${Math.floor(seconds / 60)}m ago`;
  }, 1000);
}

function resetClock() {
  document.getElementById('last-updated').textContent = 'just now';
}

// ── Horizon ───────────────────────────────────────────────────────────────────
function setupHorizonSelector() {
  document.querySelectorAll('.horizon-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.horizon-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentHorizon = btn.dataset.h;
      document.getElementById('portfolio-horizon').textContent = `${currentHorizon} horizon`;
      loadPortfolio();
    });
  });
}

// ── Load all ──────────────────────────────────────────────────────────────────
async function loadAll() {
  await Promise.all([loadPerformance(), loadPortfolio(), loadHeatmap()]);
  resetClock();
}

async function softRefresh() {
  await loadPortfolio();
  resetClock();
}

// ── Performance ───────────────────────────────────────────────────────────────
async function loadPerformance() {
  const res = await fetch('/api/performance');
  const data = await res.json();
  renderMetrics(data.metrics);
  renderEquityChart(data);
}

function renderMetrics(m) {
  const row = document.getElementById('metrics-row');
  row.innerHTML = `
    <div class="stat fade-in">
      <div class="stat-label">Total Return</div>
      <div class="stat-value ${m.total_return >= 0 ? 'pos' : 'neg'}">${m.total_return >= 0 ? '+' : ''}${m.total_return}%</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.05s">
      <div class="stat-label">Sharpe Ratio</div>
      <div class="stat-value neu">${m.sharpe}</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.1s">
      <div class="stat-label">Max Drawdown</div>
      <div class="stat-value neg">${m.max_drawdown}%</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.15s">
      <div class="stat-label">IC Mean</div>
      <div class="stat-value neu">${m.ic_mean}</div>
    </div>
  `;
}

function renderEquityChart(data) {
  const ctx = document.getElementById('equity-chart').getContext('2d');
  if (equityChart) equityChart.destroy();

  const stride = Math.max(1, Math.floor(data.dates.length / 60));
  const labels = data.dates.filter((_, i) => i % stride === 0);
  const nav    = data.nav.filter((_, i) => i % stride === 0);
  const bench  = data.benchmark.filter((_, i) => i % stride === 0);

  equityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Alpha Portfolio',
          data: nav,
          borderColor: '#00e5ff',
          backgroundColor: 'rgba(0,229,255,0.06)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3,
          fill: true,
        },
        {
          label: 'Nifty 50',
          data: bench,
          borderColor: '#4a6070',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 0,
          tension: 0.3,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: {
            color: '#7a9aaa',
            font: { family: 'Space Mono', size: 10 },
            boxWidth: 20,
            padding: 16,
          }
        },
        tooltip: {
          backgroundColor: '#0d1117',
          borderColor: '#1e2a35',
          borderWidth: 1,
          titleColor: '#4a6070',
          bodyColor: '#c8d8e8',
          titleFont: { family: 'Space Mono', size: 10 },
          bodyFont: { family: 'Space Mono', size: 11 },
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#4a6070', font: { family: 'Space Mono', size: 9 }, maxTicksLimit: 6 },
          grid: { color: '#131920' },
        },
        y: {
          ticks: { color: '#4a6070', font: { family: 'Space Mono', size: 9 } },
          grid: { color: '#131920' },
        }
      }
    }
  });
}

// ── Portfolio ─────────────────────────────────────────────────────────────────
async function loadPortfolio() {
  const res = await fetch(`/api/portfolio?horizon=${currentHorizon}`);
  const data = await res.json();
  portfolioData = data.portfolio;
  document.getElementById('n-stocks').textContent = portfolioData.length;
  renderPortfolio(portfolioData);
}

function renderPortfolio(stocks) {
  const list = document.getElementById('portfolio-list');
  const maxSignal = Math.max(...stocks.map(s => Math.abs(s.signal)));

  list.innerHTML = '';
  stocks.forEach((s, i) => {
    const pct = (Math.abs(s.signal) / maxSignal) * 100;
    const isPos = s.expected_return >= 0;
    const row = document.createElement('div');
    row.className = 'stock-row fade-in';
    row.style.animationDelay = `${i * 0.04}s`;
    row.innerHTML = `
      <div>
        <div class="stock-ticker">${s.ticker}</div>
      </div>
      <div>
        <div class="signal-bar-wrap">
          <div class="signal-bar ${s.signal >= 0 ? 'pos' : 'neg'}" style="width:${pct}%"></div>
        </div>
      </div>
      <div class="dir-pill ${s.direction}">${s.direction}</div>
      <div class="ret-value ${isPos ? 'pos' : 'neg'}">${isPos ? '+' : ''}${s.expected_return}%</div>
      <div class="weight-pill">${s.weight}%</div>
    `;
    row.addEventListener('click', () => {
      window.location.href = `/stock.html?ticker=${s.ticker}&horizon=${currentHorizon}`;
    });
    list.appendChild(row);
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────────
async function loadHeatmap() {
  const res = await fetch('/api/heatmap');
  const data = await res.json();
  renderHeatmap(data.stocks);
}

function signalToColor(signal) {
  // -3 → red, 0 → dark, +3 → green
  const t = Math.max(-3, Math.min(3, signal));
  if (t >= 0) {
    const intensity = t / 3;
    const r = Math.round(13 + (0 - 13) * intensity);
    const g = Math.round(25 + (230 - 25) * intensity);
    const b = Math.round(32 + (118 - 32) * intensity);
    return `rgba(${r},${g},${b},${0.3 + intensity * 0.5})`;
  } else {
    const intensity = Math.abs(t) / 3;
    const r = Math.round(13 + (255 - 13) * intensity);
    const g = Math.round(25 + (61 - 25) * intensity);
    const b = Math.round(32 + (113 - 32) * intensity);
    return `rgba(${r},${g},${b},${0.3 + intensity * 0.5})`;
  }
}

function renderHeatmap(stocks) {
  const grid = document.getElementById('heatmap-grid');
  grid.innerHTML = '';
  stocks.forEach(s => {
    const cell = document.createElement('div');
    cell.className = 'heatmap-cell';
    cell.style.background = signalToColor(s.signal);
    cell.innerHTML = `
      <div class="cell-ticker">${s.ticker.slice(0, 6)}</div>
      <div class="cell-val">${s.signal > 0 ? '+' : ''}${s.signal.toFixed(1)}</div>
    `;
    cell.addEventListener('click', () => {
      window.location.href = `/stock.html?ticker=${s.ticker}&horizon=${currentHorizon}`;
    });
    grid.appendChild(cell);
  });
}
