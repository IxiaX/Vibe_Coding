from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, render_template_string

BASE_DIR = Path(__file__).resolve().parent
API_KEY_FILE = BASE_DIR / "finnhub_api_key.txt"
SP500_FILE = BASE_DIR / "sp500.json"
FINNHUB_BASE = "https://finnhub.io/api/v1"
PLACEHOLDER_IMG = "https://via.placeholder.com/120x80.png?text=No+Image"

app = Flask(__name__)


def load_api_key() -> str:
    return API_KEY_FILE.read_text(encoding="utf-8").strip()


def load_symbols() -> list[dict[str, str]]:
    raw = json.loads(SP500_FILE.read_text(encoding="utf-8"))
    symbols = [
        {"symbol": item.get("symbol", "").strip(), "name": item.get("name", "").strip()}
        for item in raw
        if item.get("symbol") and item.get("name")
    ]
    symbols.sort(key=lambda item: item["symbol"])
    return symbols


def finnhub_get(path: str, params: dict[str, Any]) -> Any:
    key = load_api_key()
    query = {**params, "token": key}
    response = requests.get(f"{FINNHUB_BASE}/{path}", params=query, timeout=12)
    response.raise_for_status()
    return response.json()


@app.route("/")
def index() -> str:
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>S&P 500 Stock Tracker</title>
  <style>
    :root {
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --line: #e2e8f0;
      --accent: #2563eb;
      --good: #059669;
      --bad: #dc2626;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .container {
      max-width: 860px;
      margin: 0 auto;
      padding: 14px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 12px;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    }
    h1 { font-size: 1.3rem; margin: 0 0 10px; }
    .search-wrap { position: relative; }
    input[type="text"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      font-size: 1rem;
      padding: 12px;
      outline: none;
      background: white;
    }
    input[type="text"]:focus { border-color: var(--accent); }
    .dropdown {
      position: absolute;
      left: 0;
      right: 0;
      margin-top: 6px;
      max-height: 240px;
      overflow-y: auto;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 10px;
      display: none;
      z-index: 10;
    }
    .item {
      padding: 10px 12px;
      cursor: pointer;
      border-bottom: 1px solid #f1f5f9;
    }
    .item:last-child { border-bottom: 0; }
    .item:hover { background: #f8fafc; }
    .muted { color: var(--muted); }
    .row { display: flex; gap: 10px; align-items: center; }
    .logo { width: 56px; height: 56px; border-radius: 10px; border: 1px solid var(--line); object-fit: contain; background: #fff; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .kpi { border: 1px solid var(--line); border-radius: 10px; padding: 9px; }
    .kpi b { display: block; margin-top: 4px; }
    .up { color: var(--good); }
    .down { color: var(--bad); }
    .news-item {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px;
      margin-bottom: 10px;
      background: #fff;
    }
    .news-thumb {
      width: 120px;
      height: 80px;
      object-fit: cover;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #f1f5f9;
    }
    .loading { cursor: progress !important; }
    .hide { display: none !important; }
    @media (max-width: 620px) {
      .grid { grid-template-columns: 1fr; }
      .news-item { grid-template-columns: 1fr; }
      .news-thumb { width: 100%; height: 160px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>S&P 500 Stock Tracker</h1>
      <div class="search-wrap">
        <input id="searchInput" type="text" placeholder="Search ticker or company name (e.g., AAPL / Apple)" autocomplete="off" />
        <div id="dropdown" class="dropdown"></div>
      </div>
      <p class="muted" style="margin-top:10px;">Tap the field to browse all S&P 500 symbols, then pick one to load details.</p>
    </div>

    <div id="stockCard" class="card hide"></div>
    <div id="newsCard" class="card hide"></div>
  </div>

<script>
let allStocks = [];
const input = document.getElementById('searchInput');
const dropdown = document.getElementById('dropdown');
const stockCard = document.getElementById('stockCard');
const newsCard = document.getElementById('newsCard');
const PLACEHOLDER_IMG = {{ placeholder_img | tojson }};

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function fmtMoney(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return 'N/A';
  return '$' + Number(n).toLocaleString(undefined, {maximumFractionDigits: 2});
}

function fmtCap(n) {
  if (!n) return 'N/A';
  const v = Number(n);
  if (v >= 1e12) return (v/1e12).toFixed(2) + 'T';
  if (v >= 1e9) return (v/1e9).toFixed(2) + 'B';
  if (v >= 1e6) return (v/1e6).toFixed(2) + 'M';
  return v.toLocaleString();
}

function renderDropdown(items) {
  dropdown.innerHTML = '';
  if (!items.length) {
    dropdown.innerHTML = '<div class="item muted">No matching symbols</div>';
    dropdown.style.display = 'block';
    return;
  }
  items.forEach(it => {
    const node = document.createElement('div');
    node.className = 'item';
    node.innerHTML = `<b>${esc(it.symbol)}</b> <span class="muted">- ${esc(it.name)}</span>`;
    node.onclick = () => selectStock(it);
    dropdown.appendChild(node);
  });
  dropdown.style.display = 'block';
}

async function loadSymbols() {
  const res = await fetch('/api/symbols');
  allStocks = await res.json();
}

async function selectStock(item) {
  input.value = `${item.symbol} - ${item.name}`;
  dropdown.style.display = 'none';
  document.body.classList.add('loading');

  try {
    const res = await fetch(`/api/stock/${encodeURIComponent(item.symbol)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Unable to load stock data');

    const changeClass = (data.quote.d || 0) >= 0 ? 'up' : 'down';
    stockCard.innerHTML = `
      <div class="row">
        <img class="logo" src="${esc(data.profile.logo || PLACEHOLDER_IMG)}" alt="logo" onerror="this.src='${PLACEHOLDER_IMG}'" />
        <div>
          <h2 style="margin:0; font-size:1.1rem;">${esc(data.profile.name || item.name)}</h2>
          <div class="muted">${esc(item.symbol)} • ${esc(data.profile.finnhubIndustry || 'N/A')}</div>
        </div>
      </div>
      <div style="margin-top:10px; font-size:1.2rem;"><b>${fmtMoney(data.quote.c)}</b>
        <span class="${changeClass}">(${Number(data.quote.d || 0).toFixed(2)} / ${Number(data.quote.dp || 0).toFixed(2)}%)</span>
      </div>
      <div class="grid">
        <div class="kpi"><span class="muted">Day High</span><b>${fmtMoney(data.quote.h)}</b></div>
        <div class="kpi"><span class="muted">Day Low</span><b>${fmtMoney(data.quote.l)}</b></div>
        <div class="kpi"><span class="muted">Open</span><b>${fmtMoney(data.quote.o)}</b></div>
        <div class="kpi"><span class="muted">Prev Close</span><b>${fmtMoney(data.quote.pc)}</b></div>
        <div class="kpi"><span class="muted">Market Cap</span><b>${fmtCap((data.profile.marketCapitalization || 0) * 1000000)}</b></div>
        <div class="kpi"><span class="muted">52W High / Low</span><b>${fmtMoney(data.metrics['52WeekHigh'])} / ${fmtMoney(data.metrics['52WeekLow'])}</b></div>
      </div>
    `;
    stockCard.classList.remove('hide');

    const articles = data.news || [];
    let html = '<h3 style="margin-top:0;">Top 5 Headlines</h3>';
    if (!articles.length) {
      html += '<p class="muted">No recent headlines found.</p>';
    } else {
      html += articles.slice(0, 5).map(n => `
      <article class="news-item">
        <img class="news-thumb" src="${esc(n.image || PLACEHOLDER_IMG)}" alt="news" onerror="this.src='${PLACEHOLDER_IMG}'" />
        <div>
          <a href="${esc(n.url || '#')}" target="_blank" rel="noopener noreferrer"><b>${esc(n.headline || 'Untitled')}</b></a>
          <p class="muted" style="margin:8px 0 0;">${esc((n.summary || '').slice(0, 180) || 'No summary available.')}</p>
        </div>
      </article>
      `).join('');
    }
    newsCard.innerHTML = html;
    newsCard.classList.remove('hide');

  } catch (err) {
    stockCard.innerHTML = `<p class="down"><b>Error:</b> ${esc(err.message)}</p>`;
    stockCard.classList.remove('hide');
    newsCard.classList.add('hide');
  } finally {
    document.body.classList.remove('loading');
  }
}

input.addEventListener('focus', () => renderDropdown(allStocks));

input.addEventListener('input', () => {
  const q = input.value.trim().toLowerCase();
  const filtered = !q
    ? allStocks
    : allStocks.filter(x => x.symbol.toLowerCase().includes(q) || x.name.toLowerCase().includes(q));
  renderDropdown(filtered.slice(0, 100));
});

document.addEventListener('click', (e) => {
  if (!dropdown.contains(e.target) && e.target !== input) dropdown.style.display = 'none';
});

loadSymbols().catch(() => {
  dropdown.innerHTML = '<div class="item down">Failed to load symbols.</div>';
});
</script>
</body>
</html>
""",
        placeholder_img=PLACEHOLDER_IMG,
    )


@app.route("/api/symbols")
def api_symbols() -> Any:
    try:
        return jsonify(load_symbols())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/api/stock/<symbol>")
def api_stock(symbol: str) -> Any:
    try:
        symbol = symbol.strip().upper()
        today = date.today()
        start = today - timedelta(days=7)

        quote = finnhub_get("quote", {"symbol": symbol})
        profile = finnhub_get("stock/profile2", {"symbol": symbol})
        metrics_payload = finnhub_get("stock/metric", {"symbol": symbol, "metric": "all"})
        news = finnhub_get(
            "company-news",
            {"symbol": symbol, "from": start.isoformat(), "to": today.isoformat()},
        )

        return jsonify(
            {
                "quote": quote,
                "profile": profile,
                "metrics": metrics_payload.get("metric", {}),
                "news": news[:5] if isinstance(news, list) else [],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True)
