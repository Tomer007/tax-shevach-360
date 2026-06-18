import type { CalculationResult } from '../types'
import { formatILS, formatPercent, routeNameHebrew } from '../utils'

interface Props {
  result: CalculationResult
  onReset: () => void
}

function generateHtmlReport(result: CalculationResult): string {
  const bestRoute = result.route_comparison.reduce((a, b) => a.tax_amount < b.tax_amount ? a : b)

  const sellersHtml = result.seller_results.map((s) => `
    <div class="seller-section">
      <div class="seller-header-row">
        <h3>${s.seller_name}</h3>
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

/* Print */
@media print{
  body{background:#fff;color:#111}
  .report-header{background:#f8f9fc;border:1px solid #e4e4e7}
  .report-header h1{color:#4f46e5;-webkit-text-fill-color:#4f46e5}
  .summary-card,.seller-section,.route-card{background:#fff;border:1px solid #e4e4e7}
  .sc-value,.data-val,.route-tax{color:#111}
}

@media(max-width:640px){
  .summary-grid{grid-template-columns:1fr 1fr}
  .data-grid{grid-template-columns:1fr 1fr}
  .report{padding:20px 12px}
  .report-header{padding:32px 16px}
  .report-header h1{font-size:1.6rem}
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

  <div class="routes-section">
    <h2>השוואת מסלולים</h2>
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

      {/* Route comparison */}
      <div className="card">
        <h2 className="card-title">השוואת מסלולים</h2>
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
