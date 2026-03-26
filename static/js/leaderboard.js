/* leaderboard.js */

let modalChart = null;

document.addEventListener('DOMContentLoaded', () => {
  loadLeaderboard();
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });
});

async function loadLeaderboard() {
  const res = await fetch('/api/leaderboard');
  const data = await res.json();
  renderTable(data.leaderboard);
  document.getElementById('last-updated').textContent = 'live';
}

function rankBadge(rank) {
  const cls = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : 'normal';
  return `<span class="rank-badge ${cls}">${rank}</span>`;
}

function renderTable(rows) {
  const tbody = document.getElementById('lb-body');
  tbody.innerHTML = '';
  rows.forEach((r, i) => {
    const tr = document.createElement('tr');
    tr.className = 'fade-in';
    tr.style.animationDelay = `${i * 0.05}s`;
    tr.innerHTML = `
      <td>${rankBadge(r.rank)}</td>
      <td><div class="formula-text" title="${r.formula}">${r.formula}</div></td>
      <td style="color:var(--accent-2);font-weight:700;">${r.ic_mean}</td>
      <td style="color:var(--accent);">${r.sharpe}</td>
      <td style="color:var(--short);">${r.max_drawdown}%</td>
      <td style="color:var(--text-dim);">${r.found_at}</td>
    `;
    tr.addEventListener('click', () => openModal(r));
    tbody.appendChild(tr);
  });
}

function openModal(row) {
  document.getElementById('modal-formula').textContent = row.formula;
  document.getElementById('modal-stats').innerHTML = `
    <div class="stat">
      <div class="stat-label">IC Mean</div>
      <div class="stat-value neu">${row.ic_mean}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Sharpe</div>
      <div class="stat-value neu">${row.sharpe}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Max Drawdown</div>
      <div class="stat-value neg">${row.max_drawdown}%</div>
    </div>
    <div class="stat">
      <div class="stat-label">Found</div>
      <div class="stat-value" style="font-size:13px;color:var(--text-mid);">${row.found_at}</div>
    </div>
  `;
  renderModalChart(row.rank);
  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

function renderModalChart(seed) {
  const ctx = document.getElementById('modal-chart').getContext('2d');
  if (modalChart) modalChart.destroy();

  // Deterministic mock NAV based on rank seed
  const rng = mulberry32(seed * 12345);
  const n = 120;
  const nav = [100];
  for (let i = 1; i < n; i++) {
    const drift = 0.0005 - (seed - 1) * 0.00004;
    nav.push(+(nav[nav.length - 1] * (1 + drift + (rng() - 0.5) * 0.024)).toFixed(3));
  }

  const labels = Array.from({ length: n }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (n - i));
    return d.toISOString().slice(0, 10);
  }).filter((_, i) => i % 10 === 0);

  const navSparse = nav.filter((_, i) => i % 10 === 0);

  modalChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Simulated NAV',
        data: navSparse,
        borderColor: '#00e5ff',
        backgroundColor: 'rgba(0,229,255,0.05)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0d1117',
          borderColor: '#1e2a35',
          borderWidth: 1,
          titleColor: '#4a6070',
          bodyColor: '#c8d8e8',
          titleFont: { family: 'Space Mono', size: 10 },
          bodyFont: { family: 'Space Mono', size: 11 },
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

// Simple seedable PRNG
function mulberry32(a) {
  return function() {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
