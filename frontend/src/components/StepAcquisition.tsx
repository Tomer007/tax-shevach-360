import type { TransactionInput, AcquisitionPart, Currency, AcquisitionType } from '../types'

interface Props {
  formData: Partial<TransactionInput>
  updateForm: (partial: Partial<TransactionInput>) => void
  onNext: () => void
  onPrev: () => void
  filledFromContract?: boolean
}

const emptyAcquisition: AcquisitionPart = {
  acquisition_date: '',
  acquisition_type: 'purchase',
  amount: 0,
  currency: 'ILS',
  share_percent: 100,
  deceased_eligible_for_exemption: false,
}

export default function StepAcquisition({ formData, updateForm, onNext, onPrev, filledFromContract }: Props) {
  const acquisitions = formData.acquisitions ?? []

  function addAcquisition() {
    updateForm({ acquisitions: [...acquisitions, { ...emptyAcquisition }] })
  }

  function updateAcq(idx: number, partial: Partial<AcquisitionPart>) {
    const updated = acquisitions.map((a, i) => (i === idx ? { ...a, ...partial } : a))
    updateForm({ acquisitions: updated })
  }

  function removeAcq(idx: number) {
    updateForm({ acquisitions: acquisitions.filter((_, i) => i !== idx) })
  }

  const canContinue =
    acquisitions.length > 0 &&
    acquisitions.every((a) => a.acquisition_date)

  // Check if acquisition data is missing/empty (placeholder from contract upload)
  const isMissingData = acquisitions.length > 0 && acquisitions.some(a => !a.acquisition_date || !(a.amount ?? 0))

  // Start with one acquisition if empty
  if (acquisitions.length === 0) {
    addAcquisition()
    return null
  }

  return (
    <div className="card">
      <h3 className="card-title">פרטי הרכישה</h3>

      {/* Guidance when data is missing from contract */}
      {filledFromContract && isMissingData && (
        <div className="info-panel neutral" style={{ marginBottom: 20 }}>
          <div className="info-panel-title" style={{ color: 'var(--warning)' }}>
            ⚠️ פרטי הרכישה לא נמצאו בחוזה המכר
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: 0 }}>
            יש למלא את תאריך הרכישה וסכום הרכישה המקורי מהחוזה המקורי או מנסח הרישום.
          </p>
        </div>
      )}

      {acquisitions.map((acq, idx) => (
        <div key={idx} className="seller-card">
          <div className="seller-header">
            <h4>רכישה {idx + 1}</h4>
            {acquisitions.length > 1 && (
              <button className="btn btn-danger btn-sm" onClick={() => removeAcq(idx)} type="button">
                הסר
              </button>
            )}
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor={`acq-date-${idx}`}>תאריך רכישה</label>
              <input
                id={`acq-date-${idx}`}
                type="date"
                value={acq.acquisition_date}
                onChange={(e) => updateAcq(idx, { acquisition_date: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label htmlFor={`acq-type-${idx}`}>אופן הרכישה</label>
              <select
                id={`acq-type-${idx}`}
                value={acq.acquisition_type}
                onChange={(e) => updateAcq(idx, { acquisition_type: e.target.value as AcquisitionType })}
              >
                <option value="purchase">רכישה</option>
                <option value="inheritance">ירושה</option>
                <option value="gift">מתנה</option>
                <option value="divorce">גירושין</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor={`acq-amount-${idx}`}>סכום הרכישה</label>
              <input
                id={`acq-amount-${idx}`}
                type="number"
                min={0}
                value={acq.amount || ''}
                onChange={(e) => updateAcq(idx, { amount: Number(e.target.value) })}
                placeholder="סכום"
              />
            </div>
            <div className="form-group">
              <label htmlFor={`acq-currency-${idx}`}>מטבע</label>
              <select
                id={`acq-currency-${idx}`}
                value={acq.currency}
                onChange={(e) => updateAcq(idx, { currency: e.target.value as Currency })}
              >
                <option value="ILS">₪ שקל חדש</option>
                <option value="USD">$ דולר</option>
                <option value="EUR">€ אירו</option>
                <option value="GBP">£ לירה שטרלינג</option>
                <option value="ILP">לי"ר ישראלית</option>
                <option value="ILR">שקל ישן</option>
              </select>
              {acq.currency !== 'ILS' && acq.currency !== 'ILP' && acq.currency !== 'ILR' && (
                <span className="helper-text">שער ההמרה נלקח מבנק ישראל ליום הרכישה</span>
              )}
            </div>
            <div className="form-group">
              <label htmlFor={`acq-share-${idx}`}>חלק שנרכש (%)</label>
              <input
                id={`acq-share-${idx}`}
                type="number"
                min={0}
                max={100}
                value={acq.share_percent}
                onChange={(e) => updateAcq(idx, { share_percent: Number(e.target.value) })}
              />
            </div>
            {acq.acquisition_type === 'inheritance' && (
              <div className="form-group">
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id={`deceased-exempt-${idx}`}
                    checked={acq.deceased_eligible_for_exemption}
                    onChange={(e) => updateAcq(idx, { deceased_eligible_for_exemption: e.target.checked })}
                  />
                  <label htmlFor={`deceased-exempt-${idx}`}>המנוח היה זכאי לפטור</label>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}

      <button className="btn btn-secondary btn-sm" onClick={addAcquisition} type="button">
        + הוסף רכישה נוספת
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
