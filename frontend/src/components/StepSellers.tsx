import { useState } from 'react'
import type { TransactionInput, Seller } from '../types'

interface Props {
  formData: Partial<TransactionInput>
  updateForm: (partial: Partial<TransactionInput>) => void
  onNext: () => void
  onPrev: () => void
}

const emptySeller: Seller = {
  name: '',
  id_number: '',
  birth_date: '',
  share_percent: 100,
  is_israeli_resident: true,
  marital_status: 'single',
  annual_incomes: {},
  prisa_max_years: [],
}

export default function StepSellers({ formData, updateForm, onNext, onPrev }: Props) {
  const sellers = formData.sellers ?? []
  const [editIdx, setEditIdx] = useState<number | null>(sellers.length === 0 ? 0 : null)
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  const [showIncomePanel, setShowIncomePanel] = useState<number | null>(null)

  function markTouched(field: string) {
    setTouched(prev => ({ ...prev, [field]: true }))
  }

  function addSeller() {
    const remaining = 100 - sellers.reduce((s, sel) => s + sel.share_percent, 0)
    const newSeller: Seller = { ...emptySeller, share_percent: Math.max(0, remaining) }
    updateForm({ sellers: [...sellers, newSeller] })
    setEditIdx(sellers.length)
  }

  function updateSeller(idx: number, partial: Partial<Seller>) {
    const updated = sellers.map((s, i) => (i === idx ? { ...s, ...partial } : s))
    updateForm({ sellers: updated })
  }

  function removeSeller(idx: number) {
    updateForm({ sellers: sellers.filter((_, i) => i !== idx) })
    setEditIdx(null)
  }

  // Feature 5: Update annual income for a seller
  function updateSellerIncome(sellerIdx: number, year: number, amount: number) {
    const seller = sellers[sellerIdx]
    if (!seller) return
    const incomes = { ...seller.annual_incomes, [year]: amount }
    updateSeller(sellerIdx, { annual_incomes: incomes })
  }

  // Only require name to proceed (birth_date optional for companies)
  const canContinue = sellers.length > 0 && sellers.every((s) => s.name)

  // Feature 3: Validation
  const getSellerErrors = (seller: Seller, idx: number) => {
    const errors: Record<string, string> = {}
    if (touched[`name-${idx}`] && !seller.name) errors.name = 'שדה חובה'
    if (touched[`share-${idx}`] && (seller.share_percent <= 0 || seller.share_percent > 100)) errors.share = 'חלק חייב להיות בין 1-100%'
    return errors
  }

  // Determine the sale year for income guidance
  const saleYear = formData.sale_date ? new Date(formData.sale_date).getFullYear() : new Date().getFullYear()

  // If no sellers yet, start with one
  if (sellers.length === 0) {
    addSeller()
    return null
  }

  return (
    <div className="card">
      <h3 className="card-title">מוכרים</h3>

      {sellers.map((seller, idx) => {
        const errors = getSellerErrors(seller, idx)
        return (
        <div key={idx} className="seller-card">
          <div className="seller-header">
            <h4>מוכר {idx + 1}: {seller.name || '(חדש)'}</h4>
            <div>
              {editIdx !== idx && (
                <button className="btn btn-secondary btn-sm" onClick={() => setEditIdx(idx)} type="button">
                  ערוך
                </button>
              )}
              {sellers.length > 1 && (
                <button
                  className="btn btn-danger btn-sm"
                  style={{ marginInlineStart: 8 }}
                  onClick={() => removeSeller(idx)}
                  type="button"
                >
                  הסר
                </button>
              )}
            </div>
          </div>

          {editIdx === idx && (
            <>
            <div className="form-grid">
              <div className="form-group">
                <label>שם מלא <span className="required">*</span></label>
                <input
                  type="text"
                  value={seller.name}
                  onChange={(e) => updateSeller(idx, { name: e.target.value })}
                  onBlur={() => markTouched(`name-${idx}`)}
                  style={{ direction: 'rtl', textAlign: 'right' }}
                  aria-invalid={!!errors.name}
                  className={errors.name ? 'input-error' : ''}
                />
                {errors.name && <span className="error-msg" role="alert">{errors.name}</span>}
              </div>
              <div className="form-group">
                <label>ת.ז.</label>
                <input
                  type="text"
                  value={seller.id_number}
                  onChange={(e) => updateSeller(idx, { id_number: e.target.value })}
                  maxLength={9}
                />
              </div>
              <div className="form-group">
                <label>תאריך לידה</label>
                <input
                  type="date"
                  value={seller.birth_date}
                  onChange={(e) => updateSeller(idx, { birth_date: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>חלק בנכס (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={seller.share_percent}
                  onChange={(e) => updateSeller(idx, { share_percent: Number(e.target.value) })}
                  onBlur={() => markTouched(`share-${idx}`)}
                  aria-invalid={!!errors.share}
                  className={errors.share ? 'input-error' : ''}
                />
                {errors.share && <span className="error-msg" role="alert">{errors.share}</span>}
              </div>
              <div className="form-group">
                <label>מצב משפחתי</label>
                <select
                  value={seller.marital_status}
                  onChange={(e) => updateSeller(idx, { marital_status: e.target.value })}
                >
                  <option value="single">רווק/ה</option>
                  <option value="married">נשוי/אה</option>
                  <option value="divorced">גרוש/ה</option>
                  <option value="widowed">אלמן/ה</option>
                </select>
              </div>
              <div className="form-group">
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id={`resident-${idx}`}
                    checked={seller.is_israeli_resident}
                    onChange={(e) => updateSeller(idx, { is_israeli_resident: e.target.checked })}
                  />
                  <label htmlFor={`resident-${idx}`}>תושב ישראל</label>
                </div>
              </div>
            </div>

            {/* Feature 5: Annual Income Section - prominently displayed */}
            <div className="income-section">
              <div className="income-header" onClick={() => setShowIncomePanel(showIncomePanel === idx ? null : idx)}>
                <span className="income-title">
                  💰 הכנסות שנתיות (חשוב לפריסה ומס יסף)
                </span>
                <span className="income-toggle">{showIncomePanel === idx ? '▲' : '▼'}</span>
              </div>
              {showIncomePanel === idx && (
                <div className="income-panel">
                  <p className="income-description">
                    הכנסות שנתיות משפיעות על חישוב <strong>מס יסף</strong> (3% מעל ₪721,560) ועל <strong>פריסה</strong> (חלוקת השבח על פני שנים).
                    ככל שההכנסה נמוכה יותר — המס נמוך יותר.
                  </p>
                  <div className="income-grid">
                    {[saleYear - 3, saleYear - 2, saleYear - 1, saleYear].map(year => (
                      <div key={year} className="income-year">
                        <label htmlFor={`income-${idx}-${year}`}>{year}</label>
                        <input
                          id={`income-${idx}-${year}`}
                          type="number"
                          min={0}
                          value={seller.annual_incomes[year] || ''}
                          onChange={(e) => updateSellerIncome(idx, year, Number(e.target.value))}
                          placeholder="₪ הכנסה שנתית"
                          inputMode="numeric"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            </>
          )}
        </div>
        )
      })}

      <button className="btn btn-secondary btn-sm" onClick={addSeller} type="button">
        + הוסף מוכר
      </button>

      <div className="btn-group">
        <button className="btn btn-secondary" onClick={onPrev} type="button">
          הקודם →
        </button>
        <button className="btn btn-primary" onClick={onNext} disabled={!canContinue} type="button">
          ← הבא
        </button>
      </div>
    </div>
  )
}
