import type { CalculationResult } from '../types'
import { formatILS, formatPercent, routeNameHebrew } from '../utils'

interface Props {
  result: CalculationResult
  onReset: () => void
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function generateHtmlReport(result: CalculationResult): string {
  const bestRoute = result.route_comparison.reduce((a, b) => a.tax_amount < b.tax_amount ? a : b)
  const worstRoute = result.route_comparison.reduce((a, b) => a.tax_amount > b.tax_amount ? a : b)
  const totalSavings = worstRoute.tax_amount - bestRoute.tax_amount

  // Calculate percentages for the infographic pie/donut
  const saleAmount = result.seller_results.reduce((sum, s) => sum + s.sale_amount_ils, 0)
  const totalCost = result.seller_results.reduce((sum, s) => sum + s.total_cost_indexed, 0)
  const inflationary = result.full_inflationary
  const realShevach = result.full_real_shevach
  const tax = result.full_tax

  // For the waterfall/flow chart
  const costPercent = saleAmount > 0 ? (totalCost / saleAmount * 100) : 0
  const inflationaryPercent = saleAmount > 0 ? (inflationary / saleAmount * 100) : 0
  const taxPercent = saleAmount > 0 ? (tax / saleAmount * 100) : 0
  // Net = what remains after cost and tax (clamped to avoid negative)
  const netPercent = saleAmount > 0 ? Math.max(0, 100 - costPercent - inflationaryPercent - taxPercent) : 0
  // For the flow chart display
  const realShevachPercent = saleAmount > 0 ? (realShevach / saleAmount * 100) : 0

  // Route bar chart - normalize to max
  const maxRouteTax = Math.max(...result.route_comparison.map(r => r.tax_amount), 1)

  const sellersHtml = result.seller_results.map((s) => `
    <div class="seller-section">
      <div class="seller-header-row">
        <h3>${escapeHtml(s.seller_name)}</h3>
        <span class="share-badge">${s.share_percent}%</span>
      </div>
      <div class="data-grid">
        <div class="data-cell">
          <span class="data-label">סכום מכירה</span>
          <span class="data-val">${formatILS(s.sale_amount_ils)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">עלות מתואמת</span>
          <span class="data-val">${formatILS(s.total_cost_indexed)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">שבח ריאלי</span>
          <span class="data-val accent">${formatILS(s.real_shevach)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">מס ליניארי</span>
          <span class="data-val">${formatILS(s.tax_linear)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">מס רגיל</span>
          <span class="data-val">${formatILS(s.tax_regular)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">מס יסף</span>
          <span class="data-val">${formatILS(s.mas_yesaf)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">יחס הצמדה</span>
          <span class="data-val">${s.indexation_ratio.toFixed(4)}</span>
        </div>
        <div class="data-cell">
          <span class="data-label">פחת</span>
          <span class="data-val">${formatILS(s.depreciation_amount)}</span>
        </div>
        <div class="data-cell highlight-cell">
          <span class="data-label">סה״כ מס</span>
          <span class="data-val big">${formatILS(s.total_tax)}</span>
        </div>
      </div>

      <div class="period-bar">
        <div class="period-title">חלוקה לתקופות (${s.period_breakdown.days_total} ימים)</div>
        <div class="period-visual">
          ${s.period_breakdown.days_before_2001_11_07 > 0 ? `<div class="period-segment seg-1" style="flex:${s.period_breakdown.days_before_2001_11_07}"><span>לפני 2001</span><small>${s.period_breakdown.days_before_2001_11_07}</small></div>` : ''}
          ${s.period_breakdown.days_2001_to_2012 > 0 ? `<div class="period-segment seg-2" style="flex:${s.period_breakdown.days_2001_to_2012}"><span>2001-2012</span><small>${s.period_breakdown.days_2001_to_2012}</small></div>` : ''}
          ${s.period_breakdown.days_after_2012 > 0 ? `<div class="period-segment seg-3" style="flex:${s.period_breakdown.days_after_2012}"><span>אחרי 2012</span><small>${s.period_breakdown.days_after_2012}</small></div>` : ''}
        </div>
      </div>

      ${s.prisa_result && s.prisa_result.savings > 0 ? `
      <div class="prisa-box">
        <div class="prisa-header">
          <span>פריסה (${s.prisa_result.years} שנים)</span>
          <span class="savings-badge">חיסכון: ${formatILS(s.prisa_result.savings)}</span>
        </div>
        <table class="prisa-table">
          <thead><tr><th>שנה</th><th>סכום לפריסה</th><th>הכנסה אחרת</th><th>מס</th><th>מצב</th></tr></thead>
          <tbody>
            ${s.prisa_result.year_results.map(yr => `
              <tr><td>${yr.year}</td><td>${formatILS(yr.spread_amount)}</td><td>${formatILS(yr.other_income)}</td><td>${formatILS(yr.tax_calculated)}</td><td>${yr.is_max_mode ? '⚡ מקס' : '—'}</td></tr>
            `).join('')}
          </tbody>
        </table>
      </div>` : ''}

      <div class="recommended-box">
        <span class="rec-label">מסלול מומלץ</span>
        <span class="rec-value">${routeNameHebrew(s.recommended_route)}</span>
      </div>
    </div>
  `).join('')

  const routesHtml = result.route_comparison.map(r => {
    const isBest = r.tax_amount === bestRoute.tax_amount
    return `
      <div class="route-card ${isBest ? 'best' : ''}">
        <div class="route-info">
          <span class="route-label">${routeNameHebrew(r.route_name)}</span>
          ${isBest ? '<span class="best-tag">מומלץ</span>' : ''}
        </div>
        <div class="route-nums">
          <span class="route-tax">${formatILS(r.tax_amount)}</span>
          <span class="route-rate">${formatPercent(r.effective_rate)}</span>
        </div>
        ${r.savings_vs_regular > 0 ? `<div class="route-savings">חיסכון: ${formatILS(r.savings_vs_regular)}</div>` : ''}
      </div>
    `
  }).join('')

  return `<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>דו״ח מס שבח 360</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;background:#0a0a0f;color:#e4e4e7;line-height:1.6;direction:rtl;min-height:100vh;padding:0}
.report{max-width:900px;margin:0 auto;padding:40px 24px 60px}

/* Header */
.report-header{text-align:center;padding:48px 24px 40px;position:relative;overflow:hidden;margin-bottom:32px;border-radius:20px;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);border:1px solid rgba(99,102,241,0.15)}
.report-header::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(99,102,241,0.08) 0%,transparent 60%);animation:pulse 6s ease-in-out infinite}
@keyframes pulse{0%,100%{transform:scale(1);opacity:0.5}50%{transform:scale(1.1);opacity:1}}
.report-header h1{font-size:2.2rem;font-weight:800;background:linear-gradient(135deg,#818cf8,#a78bfa,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px;position:relative}
.report-header .subtitle{color:#a1a1aa;font-size:0.9rem;position:relative}
.report-header .date-line{color:#71717a;font-size:0.8rem;margin-top:12px;position:relative}
.report-header .logo-mark{position:absolute;top:16px;left:16px;width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:1rem;color:#fff}

/* Summary cards */
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:32px}
.summary-card{background:linear-gradient(135deg,#1c1c2e,#1a1a2a);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:20px 16px;text-align:center;position:relative;overflow:hidden;transition:all 0.2s}
.summary-card::after{content:'';position:absolute;inset:0;border-radius:14px;background:linear-gradient(135deg,rgba(99,102,241,0.05),transparent);pointer-events:none}
.summary-card .sc-label{font-size:0.72rem;font-weight:500;color:#71717a;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px}
.summary-card .sc-value{font-size:1.4rem;font-weight:700;color:#f4f4f5;font-variant-numeric:tabular-nums}
.summary-card .sc-value.primary{color:#818cf8}
.summary-card .sc-value.green{color:#34d399}

/* Route comparison */
.routes-section{margin-bottom:32px}
.routes-section h2{font-size:1rem;font-weight:700;color:#e4e4e7;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.routes-section h2::before{content:'';width:3px;height:16px;background:linear-gradient(180deg,#6366f1,#8b5cf6);border-radius:4px}
.route-card{background:#1c1c2e;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:16px 20px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;transition:all 0.15s}
.route-card:hover{border-color:rgba(99,102,241,0.2);background:#1e1e32}
.route-card.best{border-color:rgba(99,102,241,0.4);background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.05))}
.route-info{display:flex;align-items:center;gap:10px}
.route-label{font-weight:600;font-size:0.9rem}
.best-tag{font-size:0.65rem;padding:3px 10px;border-radius:20px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:700;letter-spacing:0.03em}
.route-nums{display:flex;align-items:baseline;gap:10px}
.route-tax{font-size:1.1rem;font-weight:700;font-variant-numeric:tabular-nums;color:#f4f4f5}
.route-rate{font-size:0.78rem;color:#71717a}
.route-savings{font-size:0.75rem;color:#34d399;width:100%;text-align:start;padding-top:4px}

/* Seller section */
.seller-section{background:#1c1c2e;border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:24px;margin-bottom:20px}
.seller-header-row{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.seller-header-row h3{font-size:1.05rem;font-weight:700;color:#f4f4f5}
.share-badge{font-size:0.72rem;padding:4px 10px;border-radius:20px;background:rgba(99,102,241,0.15);color:#a5b4fc;font-weight:600}

/* Data grid */
.data-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.data-cell{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:10px;padding:14px 12px;display:flex;flex-direction:column;gap:4px}
.data-cell .data-label{font-size:0.72rem;color:#71717a;font-weight:500}
.data-cell .data-val{font-size:0.95rem;font-weight:600;color:#e4e4e7;font-variant-numeric:tabular-nums}
.data-cell .data-val.accent{color:#818cf8}
.data-cell .data-val.big{font-size:1.2rem;font-weight:700;color:#34d399}
.data-cell.highlight-cell{background:rgba(52,211,153,0.05);border-color:rgba(52,211,153,0.15)}

/* Period bar */
.period-bar{margin-bottom:20px}
.period-title{font-size:0.78rem;color:#71717a;margin-bottom:10px;font-weight:500}
.period-visual{display:flex;border-radius:8px;overflow:hidden;height:36px}
.period-segment{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:4px 8px;min-width:60px}
.period-segment span{font-size:0.65rem;font-weight:600;color:#fff}
.period-segment small{font-size:0.6rem;color:rgba(255,255,255,0.7)}
.seg-1{background:linear-gradient(135deg,#f59e0b,#d97706)}
.seg-2{background:linear-gradient(135deg,#6366f1,#4f46e5)}
.seg-3{background:linear-gradient(135deg,#10b981,#059669)}

/* Prisa */
.prisa-box{background:rgba(52,211,153,0.04);border:1px solid rgba(52,211,153,0.12);border-radius:12px;padding:16px;margin-bottom:20px}
.prisa-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-size:0.85rem;font-weight:600;color:#a7f3d0}
.savings-badge{font-size:0.75rem;padding:4px 12px;border-radius:20px;background:rgba(52,211,153,0.15);color:#34d399;font-weight:700}
.prisa-table{width:100%;border-collapse:collapse;font-size:0.78rem}
.prisa-table th{text-align:start;padding:6px 8px;color:#71717a;font-weight:500;border-bottom:1px solid rgba(255,255,255,0.06)}
.prisa-table td{padding:6px 8px;color:#d4d4d8;font-variant-numeric:tabular-nums}
.prisa-table tr:hover td{background:rgba(255,255,255,0.02)}

/* Recommended */
.recommended-box{display:flex;align-items:center;gap:12px;padding:14px 18px;background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.05));border:1px solid rgba(99,102,241,0.2);border-radius:10px}
.rec-label{font-size:0.8rem;color:#a1a1aa;font-weight:500}
.rec-value{font-size:0.95rem;font-weight:700;color:#a5b4fc}

/* Footer */
.report-footer{text-align:center;padding-top:32px;border-top:1px solid rgba(255,255,255,0.04);margin-top:32px}
.report-footer p{font-size:0.75rem;color:#52525b}
.powered{font-size:0.7rem;color:#3f3f46;margin-top:8px}

/* Infographics */
.infographic-section{background:#1c1c2e;border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:24px;margin-bottom:24px}
.infographic-title{font-size:1rem;font-weight:700;color:#e4e4e7;margin-bottom:20px;display:flex;align-items:center;gap:8px}

/* Flow Chart */
.flow-chart{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;padding:16px 0}
.flow-item{text-align:center;padding:16px 12px;border-radius:12px;min-width:100px}
.flow-sale{background:linear-gradient(135deg,rgba(99,102,241,0.1),rgba(139,92,246,0.08));border:1px solid rgba(99,102,241,0.2)}
.flow-cost{background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.12);border-radius:8px;padding:10px 8px;margin-bottom:6px}
.flow-inflation{background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);border-radius:8px;padding:10px 8px;margin-bottom:6px}
.flow-shevach{background:rgba(139,92,246,0.06);border:1px solid rgba(139,92,246,0.15);border-radius:8px;padding:10px 8px}
.flow-tax{background:linear-gradient(135deg,rgba(52,211,153,0.1),rgba(16,185,129,0.08));border:1px solid rgba(52,211,153,0.2)}
.flow-icon{font-size:1.5rem;margin-bottom:6px}
.flow-label{font-size:0.7rem;color:#a1a1aa;font-weight:500;margin-bottom:4px}
.flow-amount{font-size:0.9rem;font-weight:700;color:#f4f4f5;font-variant-numeric:tabular-nums}
.flow-pct{font-size:0.68rem;color:#71717a;margin-top:2px}
.flow-arrow{font-size:1.5rem;color:#52525b;font-weight:300}
.flow-breakdown{display:flex;flex-direction:column;gap:4px}

/* Stacked Bar */
.stacked-bar-container{padding:8px 0}
.stacked-bar{display:flex;height:40px;border-radius:8px;overflow:hidden;margin-bottom:14px}
.stacked-seg{display:flex;align-items:center;justify-content:center;min-width:2px;transition:all 0.3s}
.stacked-seg span{font-size:0.68rem;font-weight:700;color:#fff}
.seg-cost{background:linear-gradient(135deg,#6366f1,#4f46e5)}
.seg-inflation{background:linear-gradient(135deg,#f59e0b,#d97706)}
.seg-net{background:linear-gradient(135deg,#10b981,#059669)}
.seg-tax{background:linear-gradient(135deg,#ef4444,#dc2626)}
.stacked-legend{display:flex;flex-wrap:wrap;gap:16px;justify-content:center}
.legend-item{display:flex;align-items:center;gap:6px;font-size:0.75rem;color:#a1a1aa}
.legend-dot{width:10px;height:10px;border-radius:3px;flex-shrink:0}

/* Bar Chart */
.bar-chart{display:flex;flex-direction:column;gap:12px;padding:8px 0}
.bar-row{display:grid;grid-template-columns:120px 1fr 100px;align-items:center;gap:12px}
.bar-row.bar-best .bar-label{color:#34d399;font-weight:700}
.bar-label{font-size:0.8rem;color:#a1a1aa;font-weight:500;text-align:start}
.bar-track{height:24px;background:rgba(255,255,255,0.04);border-radius:6px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;transition:width 0.5s ease}
.bar-fill-best{background:linear-gradient(90deg,#10b981,#34d399)}
.bar-value{font-size:0.82rem;font-weight:700;color:#e4e4e7;text-align:left;font-variant-numeric:tabular-nums}

/* Savings Callout */
.savings-callout{display:flex;align-items:center;gap:16px;margin-top:20px;padding:18px 20px;background:linear-gradient(135deg,rgba(52,211,153,0.08),rgba(16,185,129,0.04));border:1px solid rgba(52,211,153,0.2);border-radius:12px}
.savings-icon{font-size:2rem}
.savings-content{flex:1}
.savings-title{font-size:0.78rem;color:#a7f3d0;font-weight:500;margin-bottom:4px}
.savings-amount{font-size:1.6rem;font-weight:800;color:#34d399;font-variant-numeric:tabular-nums;margin-bottom:4px}
.savings-desc{font-size:0.72rem;color:#71717a}

/* Gauge */
.gauge-container{text-align:center;padding:12px 0}
.gauge{position:relative;height:20px;background:rgba(255,255,255,0.06);border-radius:10px;margin-bottom:8px}
.gauge-fill{position:absolute;top:0;right:0;height:100%;background:linear-gradient(270deg,#10b981 0%,#f59e0b 50%,#ef4444 100%);border-radius:10px}
.gauge-marker{position:absolute;top:-8px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center}
.gauge-marker span{background:#1c1c2e;border:2px solid #34d399;border-radius:6px;padding:3px 10px;font-size:0.78rem;font-weight:700;color:#34d399;white-space:nowrap}
.gauge-labels{display:flex;justify-content:space-between;font-size:0.68rem;color:#52525b;margin-bottom:12px}
.gauge-explanation{font-size:0.75rem;color:#71717a;margin-top:8px}

/* Print */
@media print{
  body{background:#fff;color:#111}
  .report-header{background:#f8f9fc;border:1px solid #e4e4e7}
  .report-header h1{color:#4f46e5;-webkit-text-fill-color:#4f46e5}
  .summary-card,.seller-section,.route-card,.infographic-section{background:#fff;border:1px solid #e4e4e7}
  .sc-value,.data-val,.route-tax,.bar-value,.flow-amount{color:#111}
  .infographic-title{color:#111}
  .stacked-bar{opacity:1}
  .gauge{opacity:1}
  .savings-callout{background:#f0fdf4;border-color:#86efac}
  .savings-amount{color:#059669}
}

@media(max-width:640px){
  .summary-grid{grid-template-columns:1fr 1fr}
  .data-grid{grid-template-columns:1fr 1fr}
  .report{padding:20px 12px}
  .report-header{padding:32px 16px}
  .report-header h1{font-size:1.6rem}
  .flow-chart{flex-direction:column;gap:8px}
  .flow-arrow{transform:rotate(90deg)}
  .flow-breakdown{flex-direction:row;gap:6px;flex-wrap:wrap;justify-content:center}
  .bar-row{grid-template-columns:80px 1fr 70px;gap:8px}
  .bar-label{font-size:0.7rem}
  .savings-callout{flex-direction:column;text-align:center}
}
</style>
</head>
<body>
<div class="report">
  <div class="report-header">
    <div class="logo-mark">₪</div>
    <h1>דו״ח מס שבח</h1>
    <p class="subtitle">חישוב מס שבח מקרקעין — סיכום עסקה</p>
    <p class="date-line">הופק: ${new Date().toLocaleDateString('he-IL', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
  </div>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="sc-label">שבח מקרקעין</div>
      <div class="sc-value">${formatILS(result.full_shevach_mekarkein)}</div>
    </div>
    <div class="summary-card">
      <div class="sc-label">סכום אינפלציוני</div>
      <div class="sc-value">${formatILS(result.full_inflationary)}</div>
    </div>
    <div class="summary-card">
      <div class="sc-label">שבח ריאלי</div>
      <div class="sc-value primary">${formatILS(result.full_real_shevach)}</div>
    </div>
    <div class="summary-card">
      <div class="sc-label">מס לתשלום</div>
      <div class="sc-value green">${formatILS(result.full_tax)}</div>
    </div>
  </div>

  <!-- INFOGRAPHIC: Transaction Flow -->
  <div class="infographic-section">
    <h2 class="infographic-title">📊 תמונת העסקה במבט אחד</h2>
    
    <!-- Flow: Sale → Components -->
    <div class="flow-chart">
      <div class="flow-item flow-sale">
        <div class="flow-icon">🏠</div>
        <div class="flow-label">סכום מכירה</div>
        <div class="flow-amount">${formatILS(saleAmount)}</div>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-breakdown">
        <div class="flow-item flow-cost">
          <div class="flow-label">עלות מתואמת</div>
          <div class="flow-amount">${formatILS(totalCost)}</div>
          <div class="flow-pct">${costPercent.toFixed(0)}%</div>
        </div>
        <div class="flow-item flow-inflation">
          <div class="flow-label">סכום אינפלציוני</div>
          <div class="flow-amount">${formatILS(inflationary)}</div>
          <div class="flow-pct">${inflationaryPercent.toFixed(0)}%</div>
        </div>
        <div class="flow-item flow-shevach">
          <div class="flow-label">שבח ריאלי</div>
          <div class="flow-amount">${formatILS(realShevach)}</div>
          <div class="flow-pct">${realShevachPercent.toFixed(0)}%</div>
        </div>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-item flow-tax">
        <div class="flow-icon">💰</div>
        <div class="flow-label">מס לתשלום</div>
        <div class="flow-amount">${formatILS(tax)}</div>
        <div class="flow-pct">${taxPercent.toFixed(1)}% מהמכירה</div>
      </div>
    </div>
  </div>

  <!-- INFOGRAPHIC: Stacked Bar - Where does the money go? -->
  <div class="infographic-section">
    <h2 class="infographic-title">💸 לאן הולך הכסף?</h2>
    <div class="stacked-bar-container">
      <div class="stacked-bar">
        ${costPercent > 0 ? `<div class="stacked-seg seg-cost" style="width:${costPercent}%" title="עלות מתואמת">
          ${costPercent > 8 ? `<span>${costPercent.toFixed(0)}%</span>` : ''}
        </div>` : ''}
        ${inflationaryPercent > 0 ? `<div class="stacked-seg seg-inflation" style="width:${inflationaryPercent}%" title="אינפלציה">
          ${inflationaryPercent > 8 ? `<span>${inflationaryPercent.toFixed(0)}%</span>` : ''}
        </div>` : ''}
        ${netPercent > 0 ? `<div class="stacked-seg seg-net" style="width:${netPercent}%" title="רווח נקי">
          ${netPercent > 8 ? `<span>${netPercent.toFixed(0)}%</span>` : ''}
        </div>` : ''}
        ${taxPercent > 0 ? `<div class="stacked-seg seg-tax" style="width:${taxPercent}%" title="מס">
          ${taxPercent > 5 ? `<span>${taxPercent.toFixed(0)}%</span>` : ''}
        </div>` : ''}
      </div>
      <div class="stacked-legend">
        <div class="legend-item"><span class="legend-dot" style="background:#6366f1"></span>עלות מתואמת</div>
        <div class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span>אינפלציה</div>
        <div class="legend-item"><span class="legend-dot" style="background:#10b981"></span>רווח נקי (אחרי מס)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>מס</div>
      </div>
    </div>
  </div>

  <!-- INFOGRAPHIC: Route Comparison Bar Chart -->
  <div class="infographic-section">
    <h2 class="infographic-title">⚖️ השוואת מסלולי מיסוי</h2>
    <div class="bar-chart">
      ${result.route_comparison.map(r => {
        const barWidth = (r.tax_amount / maxRouteTax) * 100
        const isBest = r.tax_amount === bestRoute.tax_amount
        return `
        <div class="bar-row ${isBest ? 'bar-best' : ''}">
          <div class="bar-label">${routeNameHebrew(r.route_name)}${isBest ? ' ✓' : ''}</div>
          <div class="bar-track">
            <div class="bar-fill ${isBest ? 'bar-fill-best' : ''}" style="width:${barWidth}%"></div>
          </div>
          <div class="bar-value">${formatILS(r.tax_amount)}</div>
        </div>`
      }).join('')}
    </div>
    ${totalSavings > 0 ? `
    <div class="savings-callout">
      <div class="savings-icon">🎯</div>
      <div class="savings-content">
        <div class="savings-title">חיסכון במסלול המומלץ</div>
        <div class="savings-amount">${formatILS(totalSavings)}</div>
        <div class="savings-desc">הפרש בין מסלול ${routeNameHebrew(bestRoute.route_name)} לבין מסלול ${routeNameHebrew(worstRoute.route_name)}</div>
      </div>
    </div>` : ''}
  </div>

  <!-- INFOGRAPHIC: Effective Tax Rate Gauge -->
  <div class="infographic-section">
    <h2 class="infographic-title">📈 שיעור מס אפקטיבי</h2>
    <div class="gauge-container">
      <div class="gauge">
        <div class="gauge-fill" style="width:${Math.min(bestRoute.effective_rate * 2, 100)}%"></div>
        <div class="gauge-marker" style="left:${Math.min(bestRoute.effective_rate * 2, 100)}%">
          <span>${formatPercent(bestRoute.effective_rate)}</span>
        </div>
      </div>
      <div class="gauge-labels">
        <span>0%</span>
        <span>25%</span>
        <span>50%</span>
      </div>
      <p class="gauge-explanation">שיעור המס האפקטיבי מהשבח הריאלי — ככל שנמוך יותר, כך המסלול משתלם יותר</p>
    </div>
  </div>

  <div class="routes-section">
    <h2>השוואת מסלולים — פירוט</h2>
    ${routesHtml}
  </div>

  ${sellersHtml}

  <div class="report-footer">
    <p>הדו״ח מיועד להערכה בלבד ואינו מהווה ייעוץ משפטי או מיסויי</p>
    <p class="powered">מס שבח 360 — מחשבון מס שבח מקרקעין</p>
  </div>
</div>
</body>
</html>`
}

export default function Results({ result, onReset }: Props) {
  function exportHtml() {
    const html = generateHtmlReport(result)
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mas-shevach-report.html'
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportJson() {
    const json = JSON.stringify(result, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mas-shevach-result.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const bestRoute = result.route_comparison.reduce((a, b) => a.tax_amount < b.tax_amount ? a : b)
  const worstRoute = result.route_comparison.reduce((a, b) => a.tax_amount > b.tax_amount ? a : b)
  const totalSavings = worstRoute.tax_amount - bestRoute.tax_amount
  const maxRouteTax = Math.max(...result.route_comparison.map(r => r.tax_amount), 1)

  // Percentages for infographics
  const saleAmount = result.seller_results.reduce((sum, s) => sum + s.sale_amount_ils, 0)
  const totalCost = result.seller_results.reduce((sum, s) => sum + s.total_cost_indexed, 0)
  const taxAmount = result.full_tax
  const costPct = saleAmount > 0 ? (totalCost / saleAmount * 100) : 0
  const inflationPct = saleAmount > 0 ? (result.full_inflationary / saleAmount * 100) : 0
  const taxPct = saleAmount > 0 ? (taxAmount / saleAmount * 100) : 0
  const netPct = Math.max(0, 100 - costPct - inflationPct - taxPct)

  return (
    <div>
      {/* Summary */}
      <div className="card">
        <h2 className="card-title">סיכום</h2>
        <div className="result-summary">
          <div className="result-item">
            <div className="label">שבח מקרקעין</div>
            <div className="value">{formatILS(result.full_shevach_mekarkein)}</div>
          </div>
          <div className="result-item">
            <div className="label">סכום אינפלציוני</div>
            <div className="value">{formatILS(result.full_inflationary)}</div>
          </div>
          <div className="result-item">
            <div className="label">שבח ריאלי</div>
            <div className="value highlight">{formatILS(result.full_real_shevach)}</div>
          </div>
          <div className="result-item">
            <div className="label">מס לתשלום</div>
            <div className="value success">{formatILS(result.full_tax)}</div>
          </div>
        </div>
      </div>

      {/* INFOGRAPHIC: Transaction Flow - animated */}
      <div className="card">
        <h2 className="card-title">📊 תמונת העסקה במבט אחד</h2>
        <div className="flow-infographic">
          <div className="flow-node flow-node-sale flow-animate-1">
            <div className="flow-node-icon">🏠</div>
            <div className="flow-node-label">סכום מכירה</div>
            <div className="flow-node-amount">{formatILS(saleAmount)}</div>
          </div>

          <div className="flow-connector flow-animate-2">
            <div className="flow-connector-line" />
            <div className="flow-connector-arrow">→</div>
          </div>

          <div className="flow-breakdown-col">
            <div className="flow-node flow-node-cost flow-animate-3">
              <div className="flow-node-label">עלות מתואמת</div>
              <div className="flow-node-amount">{formatILS(totalCost)}</div>
              <div className="flow-node-pct">{costPct.toFixed(0)}%</div>
            </div>
            <div className="flow-node flow-node-inflation flow-animate-4">
              <div className="flow-node-label">סכום אינפלציוני</div>
              <div className="flow-node-amount">{formatILS(result.full_inflationary)}</div>
              <div className="flow-node-pct">{inflationPct.toFixed(0)}%</div>
            </div>
            <div className="flow-node flow-node-shevach flow-animate-5">
              <div className="flow-node-label">שבח ריאלי</div>
              <div className="flow-node-amount">{formatILS(result.full_real_shevach)}</div>
              <div className="flow-node-pct">{saleAmount > 0 ? (result.full_real_shevach / saleAmount * 100).toFixed(0) : 0}%</div>
            </div>
          </div>

          <div className="flow-connector flow-animate-6">
            <div className="flow-connector-line" />
            <div className="flow-connector-arrow">→</div>
          </div>

          <div className="flow-node flow-node-tax flow-animate-7">
            <div className="flow-node-icon">💰</div>
            <div className="flow-node-label">מס לתשלום</div>
            <div className="flow-node-amount flow-node-amount-tax">{formatILS(taxAmount)}</div>
            <div className="flow-node-pct">{taxPct.toFixed(1)}% מהמכירה</div>
          </div>
        </div>
      </div>

      {/* INFOGRAPHIC: Where does the money go? */}
      <div className="card">
        <h2 className="card-title">💸 לאן הולך הכסף?</h2>
        <div className="infographic-bar-container">
          <div className="infographic-stacked-bar">
            {costPct > 0 && (
              <div className="infographic-seg infographic-seg-cost" style={{ width: `${costPct}%` }}>
                {costPct > 10 && <span>{costPct.toFixed(0)}%</span>}
              </div>
            )}
            {inflationPct > 0 && (
              <div className="infographic-seg infographic-seg-inflation" style={{ width: `${inflationPct}%` }}>
                {inflationPct > 10 && <span>{inflationPct.toFixed(0)}%</span>}
              </div>
            )}
            {netPct > 0 && (
              <div className="infographic-seg infographic-seg-net" style={{ width: `${netPct}%` }}>
                {netPct > 10 && <span>{netPct.toFixed(0)}%</span>}
              </div>
            )}
            {taxPct > 0 && (
              <div className="infographic-seg infographic-seg-tax" style={{ width: `${taxPct}%` }}>
                {taxPct > 6 && <span>{taxPct.toFixed(0)}%</span>}
              </div>
            )}
          </div>
          <div className="infographic-legend">
            <div className="infographic-legend-item">
              <span className="infographic-legend-dot" style={{ background: '#6366f1' }} />
              <span>עלות מתואמת</span>
            </div>
            <div className="infographic-legend-item">
              <span className="infographic-legend-dot" style={{ background: '#f59e0b' }} />
              <span>אינפלציה</span>
            </div>
            <div className="infographic-legend-item">
              <span className="infographic-legend-dot" style={{ background: '#10b981' }} />
              <span>רווח נקי</span>
            </div>
            <div className="infographic-legend-item">
              <span className="infographic-legend-dot" style={{ background: '#ef4444' }} />
              <span>מס</span>
            </div>
          </div>
        </div>
      </div>

      {/* INFOGRAPHIC: Route comparison bar chart */}
      <div className="card">
        <h2 className="card-title">⚖️ השוואת מסלולי מיסוי</h2>
        <div className="infographic-routes">
          {result.route_comparison.map((route) => {
            const barWidth = (route.tax_amount / maxRouteTax) * 100
            const isBest = route.tax_amount === bestRoute.tax_amount
            return (
              <div key={route.route_name} className={`infographic-route-row ${isBest ? 'infographic-route-best' : ''}`}>
                <div className="infographic-route-label">
                  {routeNameHebrew(route.route_name)}
                  {isBest && <span className="badge" style={{ marginInlineStart: 8 }}>מומלץ</span>}
                </div>
                <div className="infographic-route-track">
                  <div
                    className={`infographic-route-fill ${isBest ? 'infographic-route-fill-best' : ''}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <div className="infographic-route-value">{formatILS(route.tax_amount)}</div>
              </div>
            )
          })}
        </div>
        {totalSavings > 0 && (
          <div className="infographic-savings">
            <span className="infographic-savings-icon">🎯</span>
            <div className="infographic-savings-content">
              <div className="infographic-savings-label">חיסכון במסלול המומלץ</div>
              <div className="infographic-savings-amount">{formatILS(totalSavings)}</div>
            </div>
          </div>
        )}
      </div>

      {/* INFOGRAPHIC: Effective tax rate */}
      <div className="card">
        <h2 className="card-title">📈 שיעור מס אפקטיבי</h2>
        <div className="infographic-gauge">
          <div className="infographic-gauge-track">
            <div
              className="infographic-gauge-fill"
              style={{ width: `${Math.min(bestRoute.effective_rate * 2, 100)}%` }}
            />
            <div
              className="infographic-gauge-marker"
              style={{ left: `${Math.min(bestRoute.effective_rate * 2, 100)}%` }}
            >
              <span>{formatPercent(bestRoute.effective_rate)}</span>
            </div>
          </div>
          <div className="infographic-gauge-labels">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
          </div>
          <p className="infographic-gauge-desc">
            שיעור המס האפקטיבי מהשבח הריאלי — ככל שנמוך יותר, כך המסלול משתלם יותר
          </p>
        </div>
      </div>

      {/* Route comparison - detailed */}
      <div className="card">
        <h2 className="card-title">השוואת מסלולים — פירוט</h2>
        <div className="route-comparison" role="list" aria-label="מסלולי מיסוי">
          {result.route_comparison.map((route) => {
            const isBest = route.tax_amount === bestRoute.tax_amount
            return (
              <div
                key={route.route_name}
                className={`route-row ${isBest ? 'recommended' : ''}`}
                role="listitem"
              >
                <div>
                  <span className="route-name">{routeNameHebrew(route.route_name)}</span>
                  {isBest && <span className="badge">מומלץ</span>}
                </div>
                <div>
                  <span className="route-amount">{formatILS(route.tax_amount)}</span>
                  <span className="helper-text" style={{ marginInlineStart: 8 }}>
                    ({formatPercent(route.effective_rate)})
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Per-seller details */}
      {result.seller_results.map((seller, idx) => (
        <div key={idx} className="card">
          <h2 className="card-title">
            {seller.seller_name} ({seller.share_percent}%)
          </h2>
          <div className="form-grid">
            <div className="form-group">
              <label>סכום מכירה</label>
              <div className="data-value">{formatILS(seller.sale_amount_ils)}</div>
            </div>
            <div className="form-group">
              <label>עלות מתואמת</label>
              <div className="data-value">{formatILS(seller.total_cost_indexed)}</div>
            </div>
            <div className="form-group">
              <label>שבח ריאלי</label>
              <div className="data-value">{formatILS(seller.real_shevach)}</div>
            </div>
            <div className="form-group">
              <label>מס ליניארי</label>
              <div className="data-value">{formatILS(seller.tax_linear)}</div>
            </div>
            <div className="form-group">
              <label>מס רגיל</label>
              <div className="data-value">{formatILS(seller.tax_regular)}</div>
            </div>
            <div className="form-group">
              <label>מס יסף</label>
              <div className="data-value">{formatILS(seller.mas_yesaf)}</div>
            </div>
            <div className="form-group">
              <label>יחס הצמדה</label>
              <div className="data-value">{seller.indexation_ratio.toFixed(4)}</div>
            </div>
            <div className="form-group">
              <label>מסלול מומלץ</label>
              <div className="data-value primary">{routeNameHebrew(seller.recommended_route)}</div>
            </div>
            <div className="form-group">
              <label>סה״כ מס</label>
              <div className="data-value large">{formatILS(seller.total_tax)}</div>
            </div>
          </div>

          {/* Period breakdown */}
          <div className="info-panel neutral">
            <div className="info-panel-title">חלוקה לתקופות</div>
            <div className="form-grid cols-3">
              <div>
                <div className="helper-text">לפני 7.11.2001</div>
                <div className="data-value">{seller.period_breakdown.days_before_2001_11_07} ימים</div>
              </div>
              <div>
                <div className="helper-text">2001-2012</div>
                <div className="data-value">{seller.period_breakdown.days_2001_to_2012} ימים</div>
              </div>
              <div>
                <div className="helper-text">אחרי 2012</div>
                <div className="data-value">{seller.period_breakdown.days_after_2012} ימים</div>
              </div>
            </div>
          </div>

          {/* Prisa */}
          {seller.prisa_result && seller.prisa_result.savings > 0 && (
            <div className="info-panel positive">
              <div className="info-panel-title">
                פריסה ({seller.prisa_result.years} שנים) — חיסכון: {formatILS(seller.prisa_result.savings)}
              </div>
              {seller.prisa_result.year_results.map((yr) => (
                <div key={yr.year} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
                  <span>{yr.year}: {formatILS(yr.spread_amount)}</span>
                  <span className="data-value">מס: {formatILS(yr.tax_calculated)} {yr.is_max_mode ? '(מקס)' : ''}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* Actions */}
      <div className="btn-group" style={{ justifyContent: 'center', borderTop: 'none' }}>
        <button className="btn btn-primary" onClick={exportHtml} type="button">
          📄 הורד דו״ח HTML
        </button>
        <button className="btn btn-secondary" onClick={exportJson} type="button">
          ייצוא JSON
        </button>
        <button className="btn btn-secondary" onClick={onReset} type="button">
          חישוב חדש
        </button>
      </div>
    </div>
  )
}
