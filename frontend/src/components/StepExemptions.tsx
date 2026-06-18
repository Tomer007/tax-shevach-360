import type { TransactionInput, ExemptionCheck } from '../types'

interface Props {
  formData: Partial<TransactionInput>
  updateForm: (partial: Partial<TransactionInput>) => void
  onPrev: () => void
  onSubmit: () => void
  loading: boolean
}

export default function StepExemptions({ formData, updateForm, onPrev, onSubmit, loading }: Props) {
  const exemption = formData.exemption ?? {
    is_single_apartment: false,
    ownership_months: 0,
    is_inheritance: false,
    has_building_rights: false,
    building_rights_value: 0,
    apartment_value_without_rights: 0,
  }

  function updateExemption(partial: Partial<ExemptionCheck>) {
    updateForm({ exemption: { ...exemption, ...partial } })
  }

  return (
    <div className="card">
      <h2 className="card-title">פטורים ודירת מגורים</h2>

      <div className="form-grid">
        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="single_apartment"
              checked={exemption.is_single_apartment}
              onChange={(e) => updateExemption({ is_single_apartment: e.target.checked })}
            />
            <label htmlFor="single_apartment">דירה יחידה</label>
          </div>
          <span className="helper-text">פטור לפי סעיף 49ב(2) לדירה יחידה</span>
        </div>

        <div className="form-group">
          <label htmlFor="ownership_months">חודשי בעלות</label>
          <input
            id="ownership_months"
            type="number"
            min={0}
            value={exemption.ownership_months || ''}
            onChange={(e) => updateExemption({ ownership_months: Number(e.target.value) })}
            placeholder="18"
            inputMode="numeric"
          />
          <span className="helper-text">נדרשים לפחות 18 חודשים לפטור</span>
        </div>

        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="is_inheritance"
              checked={exemption.is_inheritance}
              onChange={(e) => updateExemption({ is_inheritance: e.target.checked })}
            />
            <label htmlFor="is_inheritance">נכס בירושה</label>
          </div>
        </div>

        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="has_building_rights"
              checked={exemption.has_building_rights}
              onChange={(e) => updateExemption({ has_building_rights: e.target.checked })}
            />
            <label htmlFor="has_building_rights">זכויות בנייה (49ז)</label>
          </div>
        </div>

        {exemption.has_building_rights && (
          <>
            <div className="form-group">
              <label htmlFor="building_rights_value">שווי זכויות בנייה (₪)</label>
              <input
                id="building_rights_value"
                type="number"
                min={0}
                value={exemption.building_rights_value || ''}
                onChange={(e) => updateExemption({ building_rights_value: Number(e.target.value) })}
                inputMode="numeric"
              />
            </div>
            <div className="form-group">
              <label htmlFor="apt_value">שווי דירה ללא זכויות (₪)</label>
              <input
                id="apt_value"
                type="number"
                min={0}
                value={exemption.apartment_value_without_rights || ''}
                onChange={(e) => updateExemption({ apartment_value_without_rights: Number(e.target.value) })}
                inputMode="numeric"
              />
            </div>
          </>
        )}
      </div>

      <div className="btn-group">
        <button className="btn btn-secondary" onClick={onPrev} type="button" aria-label="חזור לשלב הקודם">
          הקודם →
        </button>
        <button
          className="btn btn-primary"
          onClick={onSubmit}
          disabled={loading}
          type="button"
          aria-label="חשב מס שבח"
        >
          {loading ? (
            <>
              <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} aria-hidden="true" />
              מחשב...
            </>
          ) : (
            'חשב מס שבח'
          )}
        </button>
      </div>
    </div>
  )
}
