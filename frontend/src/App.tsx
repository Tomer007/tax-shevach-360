import { useCallback, useEffect, useRef, useState } from 'react'
import { calculateTax } from './api'
import type { CalculationResult, TransactionInput } from './types'
import { MOCK_TRANSACTION } from './mockData'
import { formatILS } from './utils'
import LoginPage from './components/LoginPage'
import UploadContract from './components/UploadContract'
import StepSale from './components/StepSale'
import StepSellers from './components/StepSellers'
import StepAcquisition from './components/StepAcquisition'
import StepDeductions from './components/StepDeductions'
import StepExemptions from './components/StepExemptions'
import Onboarding from './components/Onboarding'
import Results from './components/Results'

const STEPS = [
  { key: 'sale', label: 'פרטי מכירה' },
  { key: 'sellers', label: 'מוכרים' },
  { key: 'acquisition', label: 'רכישה' },
  { key: 'deductions', label: 'ניכויים' },
  { key: 'exemptions', label: 'פטורים' },
] as const

type StepKey = (typeof STEPS)[number]['key']

const STORAGE_KEY = 'mas-shevach-360-form'
const STEP_KEY = 'mas-shevach-360-step'
const ONBOARDING_KEY = 'mas-shevach-360-onboarding-done'

const DEFAULT_FORM: Partial<TransactionInput> = {
  sale_currency: 'ILS',
  sellers: [],
  acquisitions: [],
  deductions: [],
  depreciation: { mode: 'manual', manual_amount: 0, rental_periods: [], land_ratio: 1 / 3 },
  exemption: {
    is_single_apartment: false,
    ownership_months: 0,
    is_inheritance: false,
    has_building_rights: false,
    building_rights_value: 0,
    apartment_value_without_rights: 0,
  },
  prisa_years: 0,
  is_residential: true,
  betterment_levy: 0,
}

function loadSavedForm(): Partial<TransactionInput> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch { /* ignore corrupt data */ }
  return JSON.parse(JSON.stringify(DEFAULT_FORM))
}

function loadSavedStep(): StepKey {
  try {
    const saved = localStorage.getItem(STEP_KEY)
    if (saved && STEPS.some(s => s.key === saved)) return saved as StepKey
  } catch { /* ignore */ }
  return 'sale'
}

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem('token')
  )
  const [currentStep, setCurrentStep] = useState<StepKey>(loadSavedStep)
  const [formData, setFormData] = useState<Partial<TransactionInput>>(loadSavedForm)
  const [furthestStep, setFurthestStep] = useState<number>(() => {
    const savedStep = loadSavedStep()
    return STEPS.findIndex(s => s.key === savedStep)
  })
  const [result, setResult] = useState<CalculationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filledFromContract, setFilledFromContract] = useState(false)
  const [pendingExtraction, setPendingExtraction] = useState(false)
  const [preContractFormData, setPreContractFormData] = useState<Partial<TransactionInput> | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(() => !localStorage.getItem(ONBOARDING_KEY))
  const touchStartRef = useRef<number | null>(null)

  // Feature 1: Auto-save to localStorage (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(formData))
    }, 500)
    return () => clearTimeout(timer)
  }, [formData])

  useEffect(() => {
    localStorage.setItem(STEP_KEY, currentStep)
  }, [currentStep])

  // Triple-click on title to fill demo data
  const clickCountRef = useRef(0)
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function handleTitleClick() {
    clickCountRef.current += 1
    if (clickTimerRef.current) clearTimeout(clickTimerRef.current)
    clickTimerRef.current = setTimeout(() => {
      clickCountRef.current = 0
    }, 600)

    if (clickCountRef.current >= 3) {
      clickCountRef.current = 0
      setFormData({ ...MOCK_TRANSACTION })
      setCurrentStep('sale')
      setResult(null)
      setError(null)
      setFilledFromContract(false)
      setPreContractFormData(null)
    }
  }

  // Feature 7: Dismiss onboarding
  function handleDismissOnboarding() {
    localStorage.setItem(ONBOARDING_KEY, '1')
    setShowOnboarding(false)
  }

  // Feature 8: Touch/swipe navigation between steps
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    // Don't capture swipe if touching an input/select/textarea
    const tag = (e.target as HTMLElement).tagName?.toLowerCase()
    if (tag === 'input' || tag === 'select' || tag === 'textarea') return
    touchStartRef.current = e.touches[0]!.clientX
  }, [])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (touchStartRef.current === null) return
    const diff = touchStartRef.current - e.changedTouches[0]!.clientX
    const threshold = 80
    if (Math.abs(diff) > threshold) {
      const stepIdx = STEPS.findIndex(s => s.key === currentStep)
      if (diff > 0 && stepIdx < STEPS.length - 1) {
        // Swipe left (in RTL = next)
        setCurrentStep(STEPS[stepIdx + 1]!.key)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } else if (diff < 0 && stepIdx > 0) {
        // Swipe right (in RTL = prev)
        setCurrentStep(STEPS[stepIdx - 1]!.key)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    }
    touchStartRef.current = null
  }, [currentStep])

  const currentStepIndex = STEPS.findIndex((s) => s.key === currentStep)

  function handleLogin(newToken: string) {
    sessionStorage.setItem('token', newToken)
    setToken(newToken)
  }

  function handleLogout() {
    sessionStorage.removeItem('token')
    setToken(null)
  }

  // Gate: show login if not authenticated
  if (!token) {
    return <LoginPage onLogin={handleLogin} />
  }

  // Determine which steps are "complete" — must have valid data AND user must have moved past it
  function isStepComplete(stepKey: StepKey): boolean {
    const stepIdx = STEPS.findIndex(s => s.key === stepKey)
    // Only show as complete if user has navigated past this step (or contract filled it)
    if (!filledFromContract && stepIdx >= furthestStep) return false

    switch (stepKey) {
      case 'sale':
        return !!(formData.sale_date && formData.sale_amount && formData.sale_amount > 0)
      case 'sellers':
        return !!(formData.sellers?.length && formData.sellers.every(s => s.name))
      case 'acquisition':
        return !!(formData.acquisitions?.length && formData.acquisitions.every(a => a.acquisition_date))
      case 'deductions':
        return stepIdx < furthestStep || (filledFromContract && stepIdx < currentStepIndex)
      case 'exemptions':
        return false // Never pre-complete — it's the final step with the submit button
      default:
        return false
    }
  }

  function updateForm(partial: Partial<TransactionInput>) {
    setFormData((prev) => ({ ...prev, ...partial }))
  }

  // Called by UploadContract after auto-approve
  function handleContractData(partial: Partial<TransactionInput>) {
    // Feature 6: Save pre-contract state for undo
    setPreContractFormData(JSON.parse(JSON.stringify(formData)))
    setFormData((prev) => ({ ...prev, ...partial }))
    setFilledFromContract(true)
    // Mark all steps as visited since contract provides data
    setFurthestStep(STEPS.length - 1)
    // Auto-navigate to first incomplete step after a short delay
    setTimeout(() => {
      // Use the merged data directly since we know what we just set
      const updatedForm = { ...formData, ...partial }
      const hasSale = !!(updatedForm.sale_date && updatedForm.sale_amount)
      const hasSellers = !!(updatedForm.sellers?.length && updatedForm.sellers.every((s) => s.name))
      const hasAcquisition = !!(updatedForm.acquisitions?.length && updatedForm.acquisitions.every((a) => a.acquisition_date && (a.amount ?? 0) > 0))

      if (!hasSale) {
        setCurrentStep('sale')
      } else if (!hasSellers) {
        setCurrentStep('sellers')
      } else if (!hasAcquisition) {
        setCurrentStep('acquisition')
      } else {
        setCurrentStep('exemptions')
      }
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }, 300)
  }

  function goNext() {
    const nextIndex = currentStepIndex + 1
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex]!.key)
      setFurthestStep(prev => Math.max(prev, nextIndex))
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  function goPrev() {
    const prevIndex = currentStepIndex - 1
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex]!.key)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      // Validate required fields before submission
      if (!formData.sale_date || !formData.sale_amount || !formData.sellers?.length || !formData.acquisitions?.length) {
        setError('חסרים נתונים חיוניים: תאריך מכירה, סכום, מוכרים ורכישות.')
        return
      }
      const input = formData as TransactionInput
      const calcResult = await calculateTax(input)
      setResult(calcResult)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('שגיאה בחישוב. אנא בדוק את הנתונים ונסה שוב.')
      }
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setResult(null)
    setCurrentStep('sale')
    setFurthestStep(0)
    setFilledFromContract(false)
    setPreContractFormData(null)
    setShowPreview(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Feature 6: Undo contract fill
  function handleUndoContractFill() {
    if (preContractFormData) {
      setFormData(preContractFormData)
      setFilledFromContract(false)
      setPreContractFormData(null)
      setCurrentStep('sale')
    }
  }

  if (result) {
    return (
      <div className="app">
        <header className="app-header">
          <h1 onClick={handleTitleClick} style={{ cursor: 'pointer', userSelect: 'none' }}>
            מס שבח 360
          </h1>
          <p>תוצאות החישוב</p>
        </header>
        <div className="success-banner" role="status" aria-live="polite">
          החישוב הושלם בהצלחה
        </div>
        <Results result={result} onReset={handleReset} />
      </div>
    )
  }

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">דלג לתוכן הראשי</a>

      {/* Feature 7: Onboarding for new users */}
      {showOnboarding && <Onboarding onDismiss={handleDismissOnboarding} />}

      <header className="app-header" style={{ position: 'relative' }}>
        <h1 onClick={handleTitleClick} style={{ cursor: 'pointer', userSelect: 'none' }}>
          מס שבח 360
        </h1>
        <p>מחשבון מס שבח מקרקעין</p>
        <button className="btn btn-secondary btn-sm" onClick={handleLogout} type="button" style={{ position: 'absolute', top: 12, left: 12, zIndex: 1 }}>
          התנתק
        </button>
      </header>

      {/* Upload contract */}
      <UploadContract token={token} onDataExtracted={handleContractData} onPendingChange={setPendingExtraction} />

      {/* Feature 6: Undo contract fill button */}
      {filledFromContract && preContractFormData && (
        <div className="undo-banner" role="status">
          <span>📄 הטופס מולא מהחוזה</span>
          <button className="btn btn-secondary btn-sm" onClick={handleUndoContractFill} type="button">
            ↩ בטל מילוי מחוזה
          </button>
        </div>
      )}

      {/* Hide form while contract extraction is pending approval */}
      {!pendingExtraction && (
      <>
      {/* Steps indicator - Feature 8: Enhanced mobile indicator */}
      <nav className="steps" aria-label="שלבי הטופס" id="main-content">
        {STEPS.map((step, i) => {
          const isActive = i === currentStepIndex
          const stepComplete = isStepComplete(step.key)
          const isClickable = stepComplete || i < currentStepIndex
          return (
            <button
              key={step.key}
              className={`step ${isActive ? 'active' : ''} ${stepComplete && !isActive ? 'completed' : ''}`}
              onClick={() => isClickable && setCurrentStep(step.key)}
              type="button"
              aria-current={isActive ? 'step' : undefined}
              aria-label={`שלב ${i + 1}: ${step.label}${stepComplete ? ' (הושלם)' : isActive ? ' (נוכחי)' : ''}`}
              tabIndex={isClickable ? 0 : -1}
            >
              <span className="step-number">{i + 1}</span>
              <span className="step-label">{step.label}</span>
              {filledFromContract && stepComplete && !isActive && (
                <span className="step-contract-badge" title="מולא מהחוזה">📄</span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Feature 8: Mobile step progress bar */}
      <div className="mobile-step-progress" aria-hidden="true">
        <div className="mobile-step-bar">
          <div className="mobile-step-fill" style={{ width: `${((currentStepIndex + 1) / STEPS.length) * 100}%` }} />
        </div>
        <span className="mobile-step-text">שלב {currentStepIndex + 1} מתוך {STEPS.length}: {STEPS[currentStepIndex]!.label}</span>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Feature 1: Auto-save indicator */}
      <div className="autosave-indicator" aria-live="polite" aria-atomic="true">
        💾 הנתונים נשמרים אוטומטית
      </div>

      {/* Step content with Feature 8: swipe support */}
      <div
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {currentStep === 'sale' && (
          <StepSale formData={formData} updateForm={updateForm} onNext={goNext} highlightMissing={filledFromContract} />
        )}
        {currentStep === 'sellers' && (
          <StepSellers formData={formData} updateForm={updateForm} onNext={goNext} onPrev={goPrev} highlightMissing={filledFromContract} />
        )}
        {currentStep === 'acquisition' && (
          <StepAcquisition formData={formData} updateForm={updateForm} onNext={goNext} onPrev={goPrev} filledFromContract={filledFromContract} />
        )}
        {currentStep === 'deductions' && (
          <StepDeductions formData={formData} updateForm={updateForm} onNext={goNext} onPrev={goPrev} />
        )}
        {currentStep === 'exemptions' && (
          <StepExemptions
            formData={formData}
            updateForm={updateForm}
            onPrev={goPrev}
            onSubmit={() => setShowPreview(true)}
            loading={loading}
          />
        )}
      </div>

      {/* Feature 4: Preview before calculation */}
      {showPreview && (
        <div className="modal-overlay" onClick={() => setShowPreview(false)} onKeyDown={(e) => e.key === 'Escape' && setShowPreview(false)} role="dialog" aria-modal="true" aria-label="סיכום לפני חישוב">
          <div className="modal-card preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>סיכום לפני חישוב</h3>
              <button className="modal-close" onClick={() => setShowPreview(false)} type="button">✕</button>
            </div>
            <div className="preview-content">
              <div className="preview-row">
                <span className="preview-label">תאריך מכירה</span>
                <span className="preview-value">{formData.sale_date || '—'}</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">סכום מכירה</span>
                <span className="preview-value highlight">{formData.sale_amount ? formatILS(formData.sale_amount) : '—'}</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">מוכרים</span>
                <span className="preview-value">{formData.sellers?.map(s => s.name).join(', ') || '—'}</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">תאריך רכישה</span>
                <span className="preview-value">{formData.acquisitions?.[0]?.acquisition_date || '—'}</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">סכום רכישה</span>
                <span className="preview-value">{formData.acquisitions?.[0]?.amount ? formatILS(formData.acquisitions[0].amount) : '—'}</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">ניכויים</span>
                <span className="preview-value">{formData.deductions?.length || 0} הוצאות</span>
              </div>
              <div className="preview-row">
                <span className="preview-label">דירה יחידה</span>
                <span className="preview-value">{formData.exemption?.is_single_apartment ? 'כן' : 'לא'}</span>
              </div>
            </div>
            <div className="preview-actions">
              <button className="btn btn-secondary" onClick={() => setShowPreview(false)} type="button">
                ← חזור לעריכה
              </button>
              <button
                className="btn btn-primary"
                onClick={() => { setShowPreview(false); handleSubmit() }}
                disabled={loading}
                type="button"
              >
                {loading ? 'מחשב...' : '✓ אשר וחשב'}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-overlay" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          <span className="loading-text">מחשב את המס...</span>
        </div>
      )}
      </>
      )}
    </div>
  )
}
