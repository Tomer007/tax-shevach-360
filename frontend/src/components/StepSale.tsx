import type { TransactionInput, Currency } from '../types'

interface Props {
  formData: Partial<TransactionInput>
  updateForm: (partial: Partial<TransactionInput>) => void
  onNext: () => void
}

export default function StepSale({ formData, updateForm, onNext }: Props) {
  const canContinue = formData.sale_date && formData.sale_amount && formData.sale_amount > 0

  return (
    <div className="card">
      <h2 className="card-title">פרטי המכירה</h2>
      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="sale_date">
            תאריך מכירה <span className="required" aria-hidden="true">*</span>
          </label>
          <input
            id="sale_date"
            type="date"
            value={formData.sale_date ?? ''}
            onChange={(e) => updateForm({ sale_date: e.target.value })}
            required
            aria-required="true"
          />
          <span className="helper-text">תאריך חתימת החוזה</span>
        </div>
        <div className="form-group">
          <label htmlFor="sale_amount">
            סכום המכירה <span className="required" aria-hidden="true">*</span>
          </label>
          <input
            id="sale_amount"
            type="number"
            min={0}
            value={formData.sale_amount ?? ''}
            onChange={(e) => updateForm({ sale_amount: Number(e.target.value) })}
            placeholder="סכום בש״ח"
            required
            aria-required="true"
            inputMode="numeric"
          />
        </div>
        <div className="form-group">
          <label htmlFor="sale_currency">מטבע</label>
          <select
            id="sale_currency"
            value={formData.sale_currency ?? 'ILS'}
            onChange={(e) => updateForm({ sale_currency: e.target.value as Currency })}
          >
            <option value="ILS">₪ שקל חדש</option>
            <option value="USD">$ דולר</option>
            <option value="EUR">€ אירו</option>
            <option value="GBP">£ לירה שטרלינג</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="prisa_years">שנות פריסה</label>
          <select
            id="prisa_years"
            value={formData.prisa_years ?? 0}
            onChange={(e) => updateForm({ prisa_years: Number(e.target.value) })}
          >
            <option value={0}>אוטומטי (הכי משתלם)</option>
            <option value={1}>שנה 1</option>
            <option value={2}>שנתיים</option>
            <option value={3}>3 שנים</option>
            <option value={4}>4 שנים</option>
          </select>
          <span className="helper-text">המערכת תבחר אוטומטית את הפריסה המשתלמת ביותר</span>
        </div>
      </div>
      <div className="btn-group">
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={!canContinue}
          type="button"
          aria-label="המשך לשלב הבא - מוכרים"
        >
          ← הבא
        </button>
      </div>
    </div>
  )
}
