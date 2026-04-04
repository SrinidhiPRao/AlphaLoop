/* leaderboard.js */

document.addEventListener('DOMContentLoaded', () => {
  loadLeaderboard();
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
      <td><div class="formula-text" style="max-width:none;white-space:normal;overflow:visible;text-overflow:unset;">${r.formula}</div></td>
      <td style="color:var(--accent-2);font-weight:700;">${(+r.ic_mean).toFixed(4)}</td>
      <td style="color:var(--accent);">${(+r.sharpe).toFixed(2)}</td>
      <td style="color:var(--short);">${(+r.max_drawdown).toFixed(2)}%</td>
    `;
    tr.addEventListener('click', () => openModal(r));
    tbody.appendChild(tr);
  });
}
