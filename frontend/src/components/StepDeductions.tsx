import type { TransactionInput, Deduction, Currency, DepreciationInput } from '../types'

interface Props {
  formData: Partial<TransactionInput>
  updateForm: (partial: Partial<TransactionInput>) => void
  onNext: () => void
  onPrev: () => void
}

const emptyDeduction: Deduction = {
  description: '',
  amount: 0,
  currency: 'ILS',
  deduction_date: '',
}

export default function StepDeductions({ formData, updateForm, onNext, onPrev }: Props) {
  const deductions = formData.deductions ?? []
  const depreciation = formData.depreciation ?? {
    mode: 'manual',
    manual_amount: 0,
    rental_periods: [],
    land_ratio: 1 / 3,
  }

  function addDeduction() {
    updateForm({ deductions: [...deductions, { ...emptyDeduction }] })
  }

  function updateDed(idx: number, partial: Partial<Deduction>) {
    const updated = deductions.map((d, i) => (i === idx ? { ...d, ...partial } : d))
    updateForm({ deductions: updated })
  }

  function removeDed(idx: number) {
    updateForm({ deductions: deductions.filter((_, i) => i !== idx) })
  }

  function updateDepreciation(partial: Partial<DepreciationInput>) {
    updateForm({ depreciation: { ...depreciation, ...partial } })
  }

  return (
    <div className="card">
      <h3 className="card-title">ניכויים והוצאות</h3>

      {/* Depreciation section */}
      <div style={{ marginBottom: 20 }}>
        <h4 style={{ fontSize: '0.95rem', marginBottom: 12 }}>פחת</h4>
        <div className="form-grid">
          <div className="form-group">
            <label>שיטת חישוב</label>
            <select
              value={depreciation.mode}
              onChange={(e) => updateDepreciation({ mode: e.target.value as 'manual' | 'auto' })}
            >
              <option value="manual">ידני</option>
              <option value="auto">אוטומטי (לפי תקופות השכרה)</option>
            </select>
          </div>
          {depreciation.mode === 'manual' && (
            <div className="form-group">
              <label>סכום פחת (₪)</label>
              <input
                type="number"
                min={0}
                value={depreciation.manual_amount || ''}
                onChange={(e) => updateDepreciation({ manual_amount: Number(e.target.value) })}
                placeholder="0"
              />
            </div>
          )}
        </div>
      </div>

      {/* Deductions list */}
      <h4 style={{ fontSize: '0.95rem', marginBottom: 12 }}>הוצאות מוכרות</h4>

      {deductions.map((ded, idx) => (
        <div key={idx} className="seller-card">
          <div className="seller-header">
            <h4 style={{ fontSize: '0.85rem' }}>הוצאה {idx + 1}</h4>
            <button className="btn btn-danger btn-sm" onClick={() => removeDed(idx)} type="button">
              הסר
            </button>
          </div>
          <div className="form-grid cols-3">
            <div className="form-group">
              <label>תיאור</label>
              <input
                type="text"
                value={ded.description}
                onChange={(e) => updateDed(idx, { description: e.target.value })}
                placeholder="שיפוץ, שכ״ט עו״ד..."
                style={{ direction: 'rtl', textAlign: 'right' }}
              />
            </div>
            <div className="form-group">
              <label>סכום</label>
              <input
                type="number"
                min={0}
                value={ded.amount || ''}
                onChange={(e) => updateDed(idx, { amount: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label>תאריך</label>
              <input
                type="date"
                value={ded.deduction_date}
                onChange={(e) => updateDed(idx, { deduction_date: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>מטבע</label>
              <select
                value={ded.currency}
                onChange={(e) => updateDed(idx, { currency: e.target.value as Currency })}
              >
                <option value="ILS">₪</option>
                <option value="USD">$</option>
                <option value="EUR">€</option>
              </select>
            </div>
          </div>
        </div>
      ))}

      <button className="btn btn-secondary btn-sm" onClick={addDeduction} type="button">
        + הוסף הוצאה
      </button>

      <div className="btn-group">
        <button className="btn btn-secondary" onClick={onPrev} type="button">
          הקודם →
        </button>
        <button className="btn btn-primary" onClick={onNext} type="button">
          ← הבא
        </button>
      </div>
    </div>
  )
}
