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

  const canContinue = sellers.length > 0 && sellers.every((s) => s.name && s.birth_date)

  // If no sellers yet, start with one
  if (sellers.length === 0) {
    addSeller()
    return null
  }

  return (
    <div className="card">
      <h3 className="card-title">מוכרים</h3>

      {sellers.map((seller, idx) => (
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
            <div className="form-grid">
              <div className="form-group">
                <label>שם מלא</label>
                <input
                  type="text"
                  value={seller.name}
                  onChange={(e) => updateSeller(idx, { name: e.target.value })}
                  style={{ direction: 'rtl', textAlign: 'right' }}
                />
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
                />
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
          )}
        </div>
      ))}

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
