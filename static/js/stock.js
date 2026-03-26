/* stock.js */

let currentHorizon = '1M';

const params = new URLSearchParams(window.location.search);
const ticker = params.get('ticker') || '';
currentHorizon = params.get('horizon') || '1M';

document.addEventListener('DOMContentLoaded', () => {
  if (!ticker) { window.location.href = '/'; return; }
  setActiveHorizon(currentHorizon);
  loadStock();
  setupHorizonSelector();
});

function setupHorizonSelector() {
  document.querySelectorAll('.horizon-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentHorizon = btn.dataset.h;
      setActiveHorizon(currentHorizon);
      loadStock();
    });
  });
}

function setActiveHorizon(h) {
  document.querySelectorAll('.horizon-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.h === h);
  });
}

async function loadStock() {
  const res = await fetch(`/api/stock/${ticker}?horizon=${currentHorizon}`);
  if (!res.ok) { window.location.href = '/'; return; }
  const data = await res.json();
  renderHeader(data);
  renderStats(data);
  renderSignalGauge(data.signal, data.ticker);
}

function renderHeader(data) {
  document.title = `${data.ticker} — ARS`;
  document.getElementById('stock-title').textContent = data.ticker;
  const isPos = data.signal >= 0;
  const badge = document.getElementById('stock-dir-badge');
  badge.textContent = data.direction.toUpperCase();
  badge.style.cssText = `
    font-family:var(--font-mono);font-size:11px;letter-spacing:0.1em;
    padding:4px 10px;border-radius:3px;
    background:${isPos ? 'rgba(0,230,118,0.1)' : 'rgba(255,61,113,0.1)'};
    color:${isPos ? 'var(--long)' : 'var(--short)'};
    border:1px solid ${isPos ? 'rgba(0,230,118,0.25)' : 'rgba(255,61,113,0.25)'};
  `;
}

function renderStats(data) {
  const isPos = data.expected_return >= 0;
  const isSigPos = data.signal >= 0;
  document.getElementById('stock-stats').innerHTML = `
    <div class="stat fade-in">
      <div class="stat-label">Expected Return (${data.horizon})</div>
      <div class="stat-value ${isPos ? 'pos' : 'neg'}">${isPos ? '+' : ''}${data.expected_return.toFixed(2)}%</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.05s">
      <div class="stat-label">Alpha Signal</div>
      <div class="stat-value ${isSigPos ? 'pos' : 'neg'}">${data.signal > 0 ? '+' : ''}${data.signal.toFixed(4)}σ</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.1s">
      <div class="stat-label">Portfolio Weight</div>
      <div class="stat-value neu">${data.weight.toFixed(2)}%</div>
    </div>
    <div class="stat fade-in" style="animation-delay:0.15s">
      <div class="stat-label">Last Updated</div>
      <div class="stat-value" style="font-size:12px;color:var(--text-mid);">${formatTime(data.updated_at)}</div>
    </div>
  `;
}

function renderSignalGauge(signal, tickerName) {
  const wrap = document.getElementById('price-chart-wrap');
  if (!wrap) return;
  const clamped = Math.max(-3, Math.min(3, signal));
  const pct = ((clamped + 3) / 6) * 100;
  const isPos = signal >= 0;

  wrap.innerHTML = `
    <div class="card-title" style="margin-bottom:20px;">Alpha Signal Strength</div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
      <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-dim);width:40px;">SHORT</span>
      <div style="flex:1;position:relative;height:12px;background:var(--bg-3);border-radius:6px;overflow:visible;">
        <div style="position:absolute;inset:0;background:linear-gradient(to right,#ff3d71,#1e2a35 50%,#00e676);opacity:0.35;border-radius:6px;"></div>
        <div style="
          position:absolute;top:50%;left:${pct}%;transform:translate(-50%,-50%);
          width:18px;height:18px;border-radius:50%;
          background:${isPos ? 'var(--long)' : 'var(--short)'};
          box-shadow:0 0 12px ${isPos ? 'rgba(0,230,118,0.7)' : 'rgba(255,61,113,0.7)'};
          border:2px solid var(--bg-2);
        "></div>
      </div>
      <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-dim);width:40px;text-align:right;">LONG</span>
    </div>
    <div style="text-align:center;font-family:var(--font-mono);font-size:26px;font-weight:700;
      color:${isPos ? 'var(--long)' : 'var(--short)'};">
      ${signal > 0 ? '+' : ''}${signal.toFixed(4)}σ
    </div>
    <p style="text-align:center;font-family:var(--font-mono);font-size:10px;color:var(--text-dim);margin-top:12px;">
      Add a <code style="color:var(--accent)">/api/stock/${tickerName}/ohlcv</code> endpoint to display price history
    </p>
  `;
}

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso + 'Z');
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}