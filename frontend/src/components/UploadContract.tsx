import { useRef, useState } from 'react'
import axios from 'axios'
import type { TransactionInput } from '../types'
import CodeNameModal from './CodeNameModal'

interface Props {
  token: string
  onDataExtracted: (partial: Partial<TransactionInput>) => void
  onPendingChange?: (pending: boolean) => void
}

interface ExtractedData {
  sale_date: string | null
  sale_amount: number | null
  sale_currency: string | null
  sellers: Array<{ name?: string; id_number?: string; share_percent?: number; birth_date?: string; is_israeli_resident?: boolean }>
  buyers: Array<{ name?: string; id_number?: string }>
  acquisitions: Array<{ acquisition_date?: string; acquisition_type?: string; amount?: number | null; currency?: string; share_percent?: number }>
  property_address: string | null
  block_parcel: string | null
  property_type: string | null
  payment_schedule: string | null
  notes: string | null
  confidence: string
}

interface MissingField {
  field: string
  label: string
  critical: boolean
}

export default function UploadContract({ token, onDataExtracted, onPendingChange }: Props) {
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [codeVerified, setCodeVerified] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null)
  const [approved, setApproved] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [parserMode, setParserMode] = useState<'ai' | 'local' | 'smart'>('ai')
  const [uploadedFileName, setUploadedFileName] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  function handleUploadClick() {
    if (!codeVerified) {
      setShowCodeModal(true)
      return
    }
    fileRef.current?.click()
  }

  function handleCodeVerified() {
    setCodeVerified(true)
    setShowCodeModal(false)
    setTimeout(() => fileRef.current?.click(), 100)
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    setExtractedData(null)
    setApproved(false)
    setShowDetails(false)
    setUploadedFileName(file.name)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await axios.post(`/api/upload-contract?parser=${parserMode}`, formData, {
        headers: { Authorization: `Bearer ${token}` },
      })

      setExtractedData(data)

      // Signal that we have pending data (form should be hidden)
      onPendingChange?.(true)

      // Auto-approve if confidence is high and critical fields are present
      if (data.confidence === 'high' && data.sale_amount && data.sale_date) {
        autoApprove(data)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('שגיאה בקריאת החוזה')
      }
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  function getMissingFields(): MissingField[] {
    if (!extractedData) return []
    const missing: MissingField[] = []

    // Critical: sale amount and date
    if (!extractedData.sale_date) {
      missing.push({ field: 'sale_date', label: 'תאריך מכירה', critical: true })
    }
    if (!extractedData.sale_amount) {
      missing.push({ field: 'sale_amount', label: 'סכום המכירה', critical: true })
    }

    // Only flag fields the user needs to be aware they must fill
    if (!extractedData.sellers?.length) {
      missing.push({ field: 'sellers', label: 'פרטי מוכרים', critical: true })
    } else {
      const hasBirthDate = extractedData.sellers.some(s => s.birth_date)
      if (!hasBirthDate) {
        missing.push({ field: 'birth_date', label: 'תאריך לידה (מוכרים)', critical: false })
      }
    }

    if (!extractedData.acquisitions?.length) {
      missing.push({ field: 'acquisitions', label: 'תאריך רכישה מקורי', critical: false })
    }

    return missing
  }

  function autoApprove(data: ExtractedData) {
    const partial = buildPartial(data)
    if (partial) {
      setApproved(true)
      setShowDetails(false)
      onPendingChange?.(false)
      onDataExtracted(partial)
    }
  }

  function buildPartial(data: ExtractedData): Partial<TransactionInput> | null {
    if (!data.sale_amount || !data.sale_date) return null

    const partial: Partial<TransactionInput> = {}

    const d = data.sale_date.trim()
    if (/^\d{4}-\d{2}-\d{2}$/.test(d)) {
      partial.sale_date = d
    } else if (/^\d{2}\/\d{2}\/\d{4}$/.test(d)) {
      const [dd, mm, yyyy] = d.split('/')
      partial.sale_date = `${yyyy}-${mm}-${dd}`
    } else if (/^\d{2}\.\d{2}\.\d{4}$/.test(d)) {
      const [dd, mm, yyyy] = d.split('.')
      partial.sale_date = `${yyyy}-${mm}-${dd}`
    } else {
      partial.sale_date = d
    }

    partial.sale_amount = Number(data.sale_amount)
    if (data.sale_currency) partial.sale_currency = data.sale_currency as TransactionInput['sale_currency']

    if (data.sellers?.length) {
      partial.sellers = data.sellers.map((s) => ({
        name: String(s.name || ''),
        id_number: String(s.id_number || ''),
        birth_date: s.birth_date || '',
        share_percent: Number(s.share_percent) || 100,
        is_israeli_resident: s.is_israeli_resident !== false,
        marital_status: 'single',
        annual_incomes: {},
        prisa_max_years: [],
      }))
    }

    if (data.acquisitions?.length) {
      partial.acquisitions = data.acquisitions.map((a) => ({
        acquisition_date: String(a.acquisition_date || ''),
        acquisition_type: String(a.acquisition_type || 'purchase') as 'purchase' | 'inheritance' | 'gift' | 'divorce',
        amount: Number(a.amount) || 0,
        currency: (String(a.currency || 'ILS')) as TransactionInput['sale_currency'],
        share_percent: Number(a.share_percent) || 100,
        deceased_eligible_for_exemption: false,
      }))
    } else {
      // No acquisition data in contract - leave empty for user to fill
      partial.acquisitions = [{
        acquisition_date: '',
        acquisition_type: 'purchase' as const,
        amount: 0,
        currency: (data.sale_currency || 'ILS') as TransactionInput['sale_currency'],
        share_percent: 100,
        deceased_eligible_for_exemption: false,
      }]
    }

    if (data.property_type) {
      partial.is_residential = data.property_type === 'apartment' || data.property_type === 'house'
    }

    return partial
  }

  function handleApprove() {
    if (!extractedData) return

    console.log('[UploadContract] handleApprove called, extractedData:', JSON.stringify(extractedData, null, 2))

    // If critical fields are missing, expand details so user can fill them
    if (!extractedData.sale_amount || !extractedData.sale_date) {
      console.log('[UploadContract] Missing critical fields - sale_amount:', extractedData.sale_amount, 'sale_date:', extractedData.sale_date)
      setShowDetails(true)
      return
    }

    const partial = buildPartial(extractedData)
    if (!partial) return

    console.log('[UploadContract] Sending to form:', JSON.stringify(partial, null, 2))
    setApproved(true)
    setShowDetails(false)
    onPendingChange?.(false)
    onDataExtracted(partial)
  }

  function handleDismiss() {
    setExtractedData(null)
    setApproved(false)
    setShowDetails(false)
    onPendingChange?.(false)
  }

  const confidenceLabel = (c: string) =>
    c === 'high' ? 'גבוהה ✓' : c === 'medium' ? 'בינונית ⚠' : c === 'failed' ? 'נכשל ✗' : 'נמוכה'
  const confidenceColor = (c: string) =>
    c === 'high' ? 'var(--success)' : c === 'medium' ? '#fbbf24' : '#f87171'

  const missingFields = extractedData ? getMissingFields() : []
  const criticalMissing = missingFields.filter(f => f.critical)
  const optionalMissing = missingFields.filter(f => !f.critical)

  return (
    <>
      <div className="upload-section">
        <button
          className="btn btn-secondary"
          onClick={handleUploadClick}
          disabled={uploading}
          type="button"
        >
          {uploading ? (
            <>
              <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} aria-hidden="true" />
              קורא חוזה...
            </>
          ) : (
            '📄 העלה חוזה'
          )}
        </button>
        <select
          className="parser-select"
          value={parserMode}
          onChange={(e) => setParserMode(e.target.value as 'ai' | 'local' | 'smart')}
          title="בחר מנוע ניתוח"
        >
          <option value="ai">🌐 AI (OpenAI)</option>
          <option value="smart">⚡ ניתוח חכם</option>
          <option value="local">💻 Ollama</option>
        </select>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.pdf,.doc,.docx"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        {error && <span className="upload-error">{error}</span>}
      </div>

      {/* Extracted Results Panel */}
      {extractedData && (
        <div className="extracted-results" role="region" aria-label="נתונים שחולצו מהחוזה">
          <div className="extracted-header" onClick={() => approved && setShowDetails(!showDetails)} style={approved ? { cursor: 'pointer' } : undefined}>
            <h3>📋 נתונים שחולצו מהחוזה</h3>
            {uploadedFileName && <span className="extracted-dim" style={{ fontSize: '0.75rem' }}>קובץ: {uploadedFileName}</span>}
            <div className="extracted-badge" style={{ color: confidenceColor(extractedData.confidence) }}>
              רמת דיוק: {confidenceLabel(extractedData.confidence)}
            </div>
          </div>

          {/* When approved, show collapsed summary with expand option */}
          {approved && !showDetails && (
            <div className="extracted-footer">
              <span className="extracted-approved">✓ הנתונים אושרו ומולאו בטופס</span>
              <div className="extracted-actions">
                <button className="btn btn-sm btn-secondary" onClick={() => setShowDetails(true)} type="button">✏️ ערוך</button>
              </div>
            </div>
          )}

          {/* Full content - shown when not yet approved, or when expanded */}
          {(!approved || showDetails) && (
            <>
              {/* Quick summary - always visible */}
              <div className="extracted-summary">
                {extractedData.sale_date && <span className="extracted-chip">📅 {extractedData.sale_date}</span>}
                {extractedData.sale_amount && <span className="extracted-chip success">💰 ₪{extractedData.sale_amount.toLocaleString()}</span>}
                {extractedData.sellers.length > 0 && <span className="extracted-chip">👤 {extractedData.sellers.length} מוכרים</span>}
                {extractedData.buyers && extractedData.buyers.length > 0 && <span className="extracted-chip">🏠 {extractedData.buyers.length} קונים</span>}
                {extractedData.property_address && <span className="extracted-chip">📍 {extractedData.property_address}</span>}
              </div>

              {/* Missing Fields Warning */}
              {missingFields.length > 0 && !approved && (
                <div className="extracted-missing" role="alert">
                  <div className="extracted-missing-header">
                    ⚠️ שדות שיש למלא ידנית בטופס:
                  </div>
                  {criticalMissing.length > 0 && (
                    <ul className="extracted-missing-list critical">
                      {criticalMissing.map(f => (
                        <li key={f.field}>
                          <span className="missing-dot critical" />
                          {f.label} <span className="missing-tag">חובה</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {optionalMissing.length > 0 && (
                    <ul className="extracted-missing-list optional">
                      {optionalMissing.map(f => (
                        <li key={f.field}>
                          <span className="missing-dot optional" />
                          {f.label} <span className="missing-tag optional">אופציונלי</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

          {/* Toggle Details Button */}
          <button
            className="btn-toggle-details"
            onClick={() => setShowDetails(!showDetails)}
            type="button"
          >
            {showDetails ? '▲ הסתר פרטים' : '▼ הצג ועדכן שדות'}
          </button>

          {/* Editable Fields - collapsible */}
          {showDetails && (
            <div className="extracted-details">
              {/* Sale Details - Editable */}
              <div className="extracted-grid">
                <div className="extracted-item">
                  <label className="extracted-label" htmlFor="ext-sale-date">תאריך מכירה</label>
                  <input
                    id="ext-sale-date"
                    type="date"
                    className="extracted-input"
                    value={extractedData.sale_date || ''}
                    onChange={(e) => setExtractedData({ ...extractedData, sale_date: e.target.value || null })}
                  />
                </div>
                <div className="extracted-item">
                  <label className="extracted-label" htmlFor="ext-sale-amount">סכום מכירה (ש״ח)</label>
                  <input
                    id="ext-sale-amount"
                    type="number"
                    className="extracted-input"
                    min={0}
                    value={extractedData.sale_amount ?? ''}
                    onChange={(e) => setExtractedData({ ...extractedData, sale_amount: e.target.value ? Number(e.target.value) : null })}
                    placeholder="הזן סכום"
                    inputMode="numeric"
                  />
                </div>
                <div className="extracted-item">
                  <label className="extracted-label" htmlFor="ext-property-type">סוג נכס</label>
                  <select
                    id="ext-property-type"
                    className="extracted-input"
                    value={extractedData.property_type || ''}
                    onChange={(e) => setExtractedData({ ...extractedData, property_type: e.target.value || null })}
                  >
                    <option value="">—</option>
                    <option value="apartment">דירה</option>
                    <option value="house">בית</option>
                    <option value="land">מגרש</option>
                    <option value="commercial">מסחרי</option>
                    <option value="other">אחר</option>
                  </select>
                </div>
                <div className="extracted-item">
                  <label className="extracted-label" htmlFor="ext-currency">מטבע</label>
                  <select
                    id="ext-currency"
                    className="extracted-input"
                    value={extractedData.sale_currency || 'ILS'}
                    onChange={(e) => setExtractedData({ ...extractedData, sale_currency: e.target.value })}
                  >
                    <option value="ILS">₪ שקל</option>
                    <option value="USD">$ דולר</option>
                    <option value="EUR">€ אירו</option>
                  </select>
                </div>
                <div className="extracted-item full">
                  <label className="extracted-label" htmlFor="ext-address">כתובת</label>
                  <input
                    id="ext-address"
                    type="text"
                    className="extracted-input"
                    value={extractedData.property_address || ''}
                    onChange={(e) => setExtractedData({ ...extractedData, property_address: e.target.value || null })}
                    placeholder="כתובת הנכס"
                  />
                </div>
                <div className="extracted-item">
                  <label className="extracted-label" htmlFor="ext-block-parcel">גוש/חלקה</label>
                  <input
                    id="ext-block-parcel"
                    type="text"
                    className="extracted-input"
                    value={extractedData.block_parcel || ''}
                    onChange={(e) => setExtractedData({ ...extractedData, block_parcel: e.target.value || null })}
                    placeholder="גוש/חלקה"
                  />
                </div>
              </div>

              {/* Sellers - Editable */}
              <div className="extracted-section">
                <span className="extracted-section-title">מוכרים ({extractedData.sellers.length})</span>
                {extractedData.sellers.map((s, i) => (
                  <div key={i} className="extracted-seller-edit">
                    <div className="extracted-edit-row">
                      <input
                        type="text"
                        className="extracted-input"
                        value={s.name || ''}
                        onChange={(e) => {
                          const updated = [...extractedData.sellers]
                          updated[i] = { ...updated[i], name: e.target.value }
                          setExtractedData({ ...extractedData, sellers: updated })
                        }}
                        placeholder="שם מוכר"
                      />
                      <input
                        type="text"
                        className="extracted-input sm"
                        value={s.id_number || ''}
                        onChange={(e) => {
                          const updated = [...extractedData.sellers]
                          updated[i] = { ...updated[i], id_number: e.target.value }
                          setExtractedData({ ...extractedData, sellers: updated })
                        }}
                        placeholder="ת״ז"
                      />
                      <input
                        type="number"
                        className="extracted-input xs"
                        min={0}
                        max={100}
                        value={s.share_percent ?? 100}
                        onChange={(e) => {
                          const updated = [...extractedData.sellers]
                          updated[i] = { ...updated[i], share_percent: Number(e.target.value) }
                          setExtractedData({ ...extractedData, sellers: updated })
                        }}
                        placeholder="%"
                      />
                      <input
                        type="date"
                        className="extracted-input sm"
                        value={s.birth_date || ''}
                        onChange={(e) => {
                          const updated = [...extractedData.sellers]
                          updated[i] = { ...updated[i], birth_date: e.target.value }
                          setExtractedData({ ...extractedData, sellers: updated })
                        }}
                        title="תאריך לידה"
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Buyers - Editable */}
              {extractedData.buyers && extractedData.buyers.length > 0 && (
                <div className="extracted-section">
                  <span className="extracted-section-title">קונים ({extractedData.buyers.length})</span>
                  {extractedData.buyers.map((b, i) => (
                    <div key={i} className="extracted-seller-edit">
                      <div className="extracted-edit-row">
                        <input
                          type="text"
                          className="extracted-input"
                          value={b.name || ''}
                          onChange={(e) => {
                            const updated = [...extractedData.buyers]
                            updated[i] = { ...updated[i], name: e.target.value }
                            setExtractedData({ ...extractedData, buyers: updated })
                          }}
                          placeholder="שם קונה"
                        />
                        <input
                          type="text"
                          className="extracted-input sm"
                          value={b.id_number || ''}
                          onChange={(e) => {
                            const updated = [...extractedData.buyers]
                            updated[i] = { ...updated[i], id_number: e.target.value }
                            setExtractedData({ ...extractedData, buyers: updated })
                          }}
                          placeholder="ת״ז"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Acquisitions - Editable */}
              {extractedData.acquisitions.length > 0 && (
                <div className="extracted-section">
                  <span className="extracted-section-title">רכישה מקורית</span>
                  {extractedData.acquisitions.map((a, i) => (
                    <div key={i} className="extracted-seller-edit">
                      <div className="extracted-edit-row">
                        <input
                          type="date"
                          className="extracted-input sm"
                          value={a.acquisition_date || ''}
                          onChange={(e) => {
                            const updated = [...extractedData.acquisitions]
                            updated[i] = { ...updated[i], acquisition_date: e.target.value }
                            setExtractedData({ ...extractedData, acquisitions: updated })
                          }}
                          title="תאריך רכישה"
                        />
                        <select
                          className="extracted-input sm"
                          value={a.acquisition_type || 'purchase'}
                          onChange={(e) => {
                            const updated = [...extractedData.acquisitions]
                            updated[i] = { ...updated[i], acquisition_type: e.target.value }
                            setExtractedData({ ...extractedData, acquisitions: updated })
                          }}
                        >
                          <option value="purchase">רכישה</option>
                          <option value="inheritance">ירושה</option>
                          <option value="gift">מתנה</option>
                          <option value="divorce">גירושין</option>
                        </select>
                        <input
                          type="number"
                          className="extracted-input sm"
                          min={0}
                          value={a.amount ?? ''}
                          onChange={(e) => {
                            const updated = [...extractedData.acquisitions]
                            updated[i] = { ...updated[i], amount: e.target.value ? Number(e.target.value) : null }
                            setExtractedData({ ...extractedData, acquisitions: updated })
                          }}
                          placeholder="סכום רכישה"
                          inputMode="numeric"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Notes - Editable */}
              <div className="extracted-section">
                <label className="extracted-section-title" htmlFor="ext-notes">הערות</label>
                <textarea
                  id="ext-notes"
                  className="extracted-input extracted-textarea"
                  value={extractedData.notes || ''}
                  onChange={(e) => setExtractedData({ ...extractedData, notes: e.target.value || null })}
                  rows={2}
                  placeholder="הערות נוספות"
                />
              </div>
            </div>
          )}

          {/* Approve / Dismiss Actions */}
          <div className="extracted-footer">
            {!approved ? (
              <>
                <span className="extracted-dim">בדוק את הנתונים ואשר למילוי הטופס</span>
                <div className="extracted-actions">
                  <button className="btn btn-primary btn-sm" onClick={handleApprove} type="button">
                    ✓ אשר ומלא בטופס
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={handleDismiss} type="button">
                    ✗ בטל
                  </button>
                </div>
              </>
            ) : (
              <>
                <span className="extracted-approved">✓ הנתונים עודכנו</span>
                <div className="extracted-actions">
                  <button className="btn btn-primary btn-sm" onClick={handleApprove} type="button">
                    ↻ עדכן בטופס
                  </button>
                  <button className="btn btn-sm btn-secondary" onClick={() => setShowDetails(false)} type="button">סגור</button>
                </div>
              </>
            )}
          </div>
            </>
          )}
        </div>
      )}

      {showCodeModal && (
        <CodeNameModal
          onVerified={handleCodeVerified}
          onClose={() => setShowCodeModal(false)}
        />
      )}
    </>
  )
}
