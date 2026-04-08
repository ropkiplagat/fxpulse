"""
Web Dashboard — Flask app showing live bot status.
Access from any device on your network: http://localhost:5000

Run alongside main.py: python web_app.py
Data is read from the shared state file written by main.py.
"""
import os
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
STATE_FILE = "logs/bot_state.json"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Forex AI Bot</title>
  <meta http-equiv="refresh" content="30">
  <style>
    body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:20px; }
    h1   { color:#58a6ff; }
    .card { background:#161b22; border:1px solid #30363d; padding:15px;
            margin:10px 0; border-radius:6px; }
    .green { color:#3fb950; } .red { color:#f85149; }
    .yellow { color:#d29922; }
    table { width:100%; border-collapse:collapse; }
    th,td { padding:8px; text-align:left; border-bottom:1px solid #30363d; }
    th { color:#8b949e; font-size:0.85em; }
    .badge { padding:2px 8px; border-radius:10px; font-size:0.8em; }
    .badge-green { background:#196c2e; color:#3fb950; }
    .badge-red   { background:#3d1214; color:#f85149; }
    .badge-yellow { background:#3d2b0e; color:#d29922; }
    .bar { display:inline-block; height:12px; background:#58a6ff; margin-right:4px; }
    .bar-neg { background:#f85149; }
  </style>
</head>
<body>
  <h1>🤖 Forex AI Bot Dashboard</h1>
  <p id="refresh">Auto-refreshes every 30s | <span id="now"></span></p>
  <script>document.getElementById('now').textContent = new Date().toUTCString();</script>

  <div id="content">Loading...</div>

  <script>
  fetch('/api/state').then(r=>r.json()).then(data=>{
    let html = '';

    // Account
    let acc = data.account || {};
    let dd  = ((acc.balance - acc.equity) / acc.balance * 100) || 0;
    html += `<div class="card">
      <b>Account</b><br>
      Balance: <span class="green">$${(acc.balance||0).toFixed(2)}</span> |
      Equity: <span class="${dd>3?'red':'green'}">$${(acc.equity||0).toFixed(2)}</span> |
      Drawdown: <span class="${dd>3?'red':'yellow'}">${dd.toFixed(1)}%</span> |
      Session: <span class="badge ${data.in_session?'badge-green':'badge-red'}">${data.session||'NONE'}</span> |
      Regime: <span class="badge ${data.regime_tradeable?'badge-green':'badge-yellow'}">${data.regime||'?'}</span>
    </div>`;

    // Currency Strength
    html += `<div class="card"><b>Currency Strength</b><br><table>
      <tr><th>#</th><th>Currency</th><th>Score</th><th>Slope</th><th>Bar</th></tr>`;
    let strength = data.strength || {};
    let sorted = Object.entries(strength).sort((a,b)=>a[1].rank-b[1].rank);
    sorted.forEach(([cur, s]) => {
      let barW = Math.min(Math.abs(s.score) * 40, 100);
      let neg  = s.score < 0 ? 'bar-neg' : '';
      let arrow = s.slope=='up'?'▲':s.slope=='down'?'▼':'─';
      html += `<tr>
        <td>#${s.rank}</td><td><b>${cur}</b></td>
        <td class="${s.score>=0?'green':'red'}">${s.score>=0?'+':''}${s.score.toFixed(4)}</td>
        <td>${arrow}</td>
        <td><span class="bar ${neg}" style="width:${barW}px"></span></td>
      </tr>`;
    });
    html += '</table></div>';

    // Top Pairs
    html += `<div class="card"><b>Top Pair Opportunities</b><br><table>
      <tr><th>#</th><th>Symbol</th><th>Dir</th><th>Gap</th><th>AI Prob</th><th>Confluence</th></tr>`;
    (data.top_pairs||[]).forEach((p,i) => {
      let prob = (data.win_probs||{})[p.symbol] || 0;
      let cls  = prob >= 0.65 ? 'green' : prob >= 0.5 ? 'yellow' : 'red';
      html += `<tr>
        <td>#${i+1}</td><td><b>${p.symbol}</b></td>
        <td class="${p.direction=='buy'?'green':'red'}">${p.direction.toUpperCase()}</td>
        <td>${p.gap>0?'+':''}${p.gap.toFixed(4)}</td>
        <td class="${cls}">${(prob*100).toFixed(0)}%</td>
        <td>${(p.score||0).toFixed(3)}</td>
      </tr>`;
    });
    html += '</table></div>';

    // Performance
    let perf = data.performance || {};
    html += `<div class="card"><b>Performance</b><br>
      Trades: ${perf.total||0} |
      Wins: <span class="green">${perf.wins||0}</span> |
      Losses: <span class="red">${perf.losses||0}</span> |
      Win Rate: <b class="${(perf.win_rate||0)>=0.65?'green':'yellow'}">${((perf.win_rate||0)*100).toFixed(1)}%</b> |
      P&L: <span class="${(perf.total_pnl||0)>=0?'green':'red'}">${(perf.total_pnl||0)>=0?'+':''}$${(perf.total_pnl||0).toFixed(2)}</span>
    </div>`;

    // News
    let news = data.news || [];
    if (news.length > 0) {
      html += `<div class="card"><b>Upcoming News</b><br><table>
        <tr><th>Currency</th><th>Event</th><th>In</th><th>Impact</th></tr>`;
      news.forEach(n => {
        let cls = n.impact=='HIGH'?'red':'yellow';
        html += `<tr>
          <td>${n.currency}</td><td>${n.name}</td>
          <td>${n.in_min>0?'in '+n.in_min+'m':n.in_min+'m ago'}</td>
          <td class="${cls}">${n.impact}</td>
        </tr>`;
      });
      html += '</table></div>';
    }

    document.getElementById('content').innerHTML = html;
  });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/state")
def state():
    if not os.path.exists(STATE_FILE):
        return jsonify({"error": "Bot not running or no data yet"})
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    print("[WEB] Dashboard: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
