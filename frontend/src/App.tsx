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

  function updateForm(partial: Partial<TransactionInput>) {
    setFormData((prev) => ({ ...prev, ...partial }))
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
      <header className="app-header" style={{ position: 'relative' }}>
        <h1 onClick={handleTitleClick} style={{ cursor: 'pointer', userSelect: 'none' }}>
          מס שבח 360
        </h1>
        <p>מחשבון מס שבח מקרקעין</p>
        <button className="btn btn-secondary btn-sm" onClick={handleLogout} type="button" style={{ position: 'absolute', top: 12, left: 12 }}>
          התנתק
        </button>
      </header>

      {/* Upload contract + Steps */}
      <UploadContract token={token} onDataExtracted={updateForm} />

      {/* Steps indicator */}
      <nav className="steps" aria-label="שלבי הטופס">
        {STEPS.map((step, i) => {
          const isActive = i === currentStepIndex
          const isCompleted = i < currentStepIndex
          const isClickable = isCompleted
          return (
            <button
              key={step.key}
              className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              onClick={() => isClickable && setCurrentStep(step.key)}
              type="button"
              aria-current={isActive ? 'step' : undefined}
              aria-label={`שלב ${i + 1}: ${step.label}${isCompleted ? ' (הושלם)' : isActive ? ' (נוכחי)' : ''}`}
              tabIndex={isClickable ? 0 : -1}
            >
              <span className="step-number">{i + 1}</span>
              <span>{step.label}</span>
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
        <StepAcquisition formData={formData} updateForm={updateForm} onNext={goNext} onPrev={goPrev} />
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
    </div>
  )
}
