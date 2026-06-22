import { useRef, useState } from 'react'
import { calculateTax } from './api'
import type { CalculationResult, TransactionInput } from './types'
import { MOCK_TRANSACTION } from './mockData'
import LoginPage from './components/LoginPage'
import UploadContract from './components/UploadContract'
import StepSale from './components/StepSale'
import StepSellers from './components/StepSellers'
import StepAcquisition from './components/StepAcquisition'
import StepDeductions from './components/StepDeductions'
import StepExemptions from './components/StepExemptions'
import Results from './components/Results'

const STEPS = [
  { key: 'sale', label: 'פרטי מכירה' },
  { key: 'sellers', label: 'מוכרים' },
  { key: 'acquisition', label: 'רכישה' },
  { key: 'deductions', label: 'ניכויים' },
  { key: 'exemptions', label: 'פטורים' },
] as const

type StepKey = (typeof STEPS)[number]['key']

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem('token')
  )
  const [currentStep, setCurrentStep] = useState<StepKey>('sale')
  const [formData, setFormData] = useState<Partial<TransactionInput>>({
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
  })
  const [result, setResult] = useState<CalculationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filledFromContract, setFilledFromContract] = useState(false)
  const [pendingExtraction, setPendingExtraction] = useState(false)

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
    }
  }

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

  // Determine which steps are "complete" based on formData content
  function isStepComplete(stepKey: StepKey): boolean {
    switch (stepKey) {
      case 'sale':
        return !!(formData.sale_date && formData.sale_amount && formData.sale_amount > 0)
      case 'sellers':
        return !!(formData.sellers?.length && formData.sellers.every(s => s.name))
      case 'acquisition':
        return !!(formData.acquisitions?.length && formData.acquisitions.every(a => a.acquisition_date))
      case 'deductions':
        return currentStepIndex > STEPS.findIndex(s => s.key === 'deductions')
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
    setFormData((prev) => ({ ...prev, ...partial }))
    setFilledFromContract(true)
    // Auto-navigate to first incomplete step after a short delay
    setTimeout(() => {
      const updatedForm = { ...formData, ...partial }
      // Determine first incomplete step with the new data
      const hasSale = !!(updatedForm.sale_date && updatedForm.sale_amount)
      const hasSellers = !!(updatedForm.sellers?.length && updatedForm.sellers.every((s: { name: string }) => s.name))
      const hasAcquisition = !!(updatedForm.acquisitions?.length && updatedForm.acquisitions.every((a: { acquisition_date: string; amount: number | null }) => a.acquisition_date && (a.amount ?? 0) > 0))

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
    setFilledFromContract(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
      <header className="app-header" style={{ position: 'relative' }}>
        <h1 onClick={handleTitleClick} style={{ cursor: 'pointer', userSelect: 'none' }}>
          מס שבח 360
        </h1>
        <p>מחשבון מס שבח מקרקעין</p>
        <button className="btn btn-secondary btn-sm" onClick={handleLogout} type="button" style={{ position: 'absolute', top: 12, left: 12 }}>
          התנתק
        </button>
      </header>

      {/* Upload contract */}
      <UploadContract token={token} onDataExtracted={handleContractData} onPendingChange={setPendingExtraction} />

      {/* Hide form while contract extraction is pending approval */}
      {!pendingExtraction && (
      <>
      {/* Steps indicator */}
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
              <span>{step.label}</span>
              {filledFromContract && stepComplete && !isActive && (
                <span className="step-contract-badge" title="מולא מהחוזה">📄</span>
              )}
            </button>
          )
        })}
      </nav>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Step content */}
      {currentStep === 'sale' && (
        <StepSale formData={formData} updateForm={updateForm} onNext={goNext} />
      )}
      {currentStep === 'sellers' && (
        <StepSellers formData={formData} updateForm={updateForm} onNext={goNext} onPrev={goPrev} />
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
          onSubmit={handleSubmit}
          loading={loading}
        />
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
