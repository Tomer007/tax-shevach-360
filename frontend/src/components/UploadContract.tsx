import { useRef, useState } from 'react'
import axios from 'axios'
import type { TransactionInput } from '../types'
import CodeNameModal from './CodeNameModal'

interface Props {
  token: string
  onDataExtracted: (partial: Partial<TransactionInput>) => void
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

export default function UploadContract({ token, onDataExtracted }: Props) {
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [codeVerified, setCodeVerified] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null)
  const [approved, setApproved] = useState(false)
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

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await axios.post('/api/upload-contract', formData, {
        headers: { Authorization: `Bearer ${token}` },
      })

      setExtractedData(data)
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

    if (!extractedData.sale_date) {
      missing.push({ field: 'sale_date', label: 'תאריך מכירה', critical: true })
    }
    if (!extractedData.sale_amount) {
      missing.push({ field: 'sale_amount', label: 'סכום מכירה', critical: true })
    }
    if (!extractedData.sellers?.length) {
      missing.push({ field: 'sellers', label: 'פרטי מוכרים', critical: true })
    } else {
      const hasBirthDate = extractedData.sellers.some(s => s.birth_date)
      if (!hasBirthDate) {
        missing.push({ field: 'birth_date', label: 'תאריך לידה (מוכרים)', critical: false })
      }
    }
    if (!extractedData.acquisitions?.length) {
      missing.push({ field: 'acquisitions', label: 'פרטי רכישה מקורית', critical: true })
    } else {
      const hasAmount = extractedData.acquisitions.some(a => a.amount && a.amount > 0)
      if (!hasAmount) {
        missing.push({ field: 'acquisition_amount', label: 'סכום רכישה מקורי', critical: true })
      }
    }

    return missing
  }

  function handleApprove() {
    if (!extractedData) return

    const partial: Partial<TransactionInput> = {}

    // Sale details
    if (extractedData.sale_date) partial.sale_date = extractedData.sale_date
    if (extractedData.sale_amount) partial.sale_amount = Number(extractedData.sale_amount)
    if (extractedData.sale_currency) partial.sale_currency = extractedData.sale_currency as TransactionInput['sale_currency']

    // Sellers
    if (extractedData.sellers?.length) {
      partial.sellers = extractedData.sellers.map((s) => ({
        name: String(s.name || ''),
        id_number: String(s.id_number || ''),
        birth_date: String(s.birth_date || ''),
        share_percent: Number(s.share_percent) || 100,
        is_israeli_resident: s.is_israeli_resident !== false,
        marital_status: 'single',
        annual_incomes: {},
        prisa_max_years: [],
      }))
    }

    // Acquisitions
    if (extractedData.acquisitions?.length) {
      partial.acquisitions = extractedData.acquisitions.map((a) => ({
        acquisition_date: String(a.acquisition_date || ''),
        acquisition_type: String(a.acquisition_type || 'purchase') as 'purchase' | 'inheritance' | 'gift' | 'divorce',
        amount: Number(a.amount) || 0,
        currency: (String(a.currency || 'ILS')) as TransactionInput['sale_currency'],
        share_percent: Number(a.share_percent) || 100,
        deceased_eligible_for_exemption: false,
      }))
    }

    // Property type → is_residential
    if (extractedData.property_type) {
      partial.is_residential = extractedData.property_type === 'apartment' || extractedData.property_type === 'house'
    }

    setApproved(true)
    onDataExtracted(partial)
  }

  function handleDismiss() {
    setExtractedData(null)
    setApproved(false)
  }

  const confidenceLabel = (c: string) =>
    c === 'high' ? 'גבוהה ✓' : c === 'medium' ? 'בינונית ⚠' : c === 'failed' ? 'נכשל ✗' : 'נמוכה'
  const confidenceColor = (c: string) =>
    c === 'high' ? 'var(--success)' : c === 'medium' ? '#fbbf24' : '#f87171'

  const propertyTypeLabel = (t: string | null) => {
    if (!t) return '—'
    const map: Record<string, string> = { apartment: 'דירה', house: 'בית', land: 'מגרש', commercial: 'מסחרי', other: 'אחר' }
    return map[t] || t
  }

  const acquisitionTypeLabel = (t: string | undefined) => {
    if (!t) return '—'
    const map: Record<string, string> = { purchase: 'רכישה', inheritance: 'ירושה', gift: 'מתנה', divorce: 'גירושין' }
    return map[t] || t
  }

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
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.pdf,.doc,.docx"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        {error && <span className="upload-error">{error}</span>}
      </div>

      {/* Extracted Results Panel - Review Before Approve */}
      {extractedData && (
        <div className="extracted-results" role="region" aria-label="נתונים שחולצו מהחוזה">
          <div className="extracted-header">
            <h3>📋 נתונים שחולצו מהחוזה</h3>
            <div className="extracted-badge" style={{ color: confidenceColor(extractedData.confidence) }}>
              רמת דיוק: {confidenceLabel(extractedData.confidence)}
            </div>
          </div>

          {/* Missing Fields Warning */}
          {missingFields.length > 0 && !approved && (
            <div className="extracted-missing" role="alert">
              <div className="extracted-missing-header">
                ⚠️ שדות חסרים — יש למלא ידנית בטופס:
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

          {/* Sale Details */}
          <div className="extracted-grid">
            {extractedData.sale_date && (
              <div className="extracted-item">
                <span className="extracted-label">תאריך מכירה</span>
                <span className="extracted-value">{extractedData.sale_date}</span>
              </div>
            )}
            {extractedData.sale_amount && (
              <div className="extracted-item">
                <span className="extracted-label">סכום מכירה</span>
                <span className="extracted-value extracted-amount">₪{extractedData.sale_amount.toLocaleString()}</span>
              </div>
            )}
            {extractedData.property_type && (
              <div className="extracted-item">
                <span className="extracted-label">סוג נכס</span>
                <span className="extracted-value">{propertyTypeLabel(extractedData.property_type)}</span>
              </div>
            )}
            {extractedData.property_address && (
              <div className="extracted-item full">
                <span className="extracted-label">כתובת</span>
                <span className="extracted-value">{extractedData.property_address}</span>
              </div>
            )}
            {extractedData.block_parcel && (
              <div className="extracted-item">
                <span className="extracted-label">גוש/חלקה</span>
                <span className="extracted-value">{extractedData.block_parcel}</span>
              </div>
            )}
          </div>

          {/* Sellers */}
          {extractedData.sellers.length > 0 && (
            <div className="extracted-section">
              <span className="extracted-section-title">מוכרים ({extractedData.sellers.length})</span>
              {extractedData.sellers.map((s, i) => (
                <div key={i} className="extracted-seller">
                  <span>{s.name || '—'}</span>
                  <span className="extracted-dim">ת״ז {s.id_number || '—'}</span>
                  <span className="extracted-badge-sm">{s.share_percent || 100}%</span>
                  {!s.birth_date && <span className="missing-inline">חסר: ת. לידה</span>}
                </div>
              ))}
            </div>
          )}

          {/* Buyers */}
          {extractedData.buyers && extractedData.buyers.length > 0 && (
            <div className="extracted-section">
              <span className="extracted-section-title">קונים ({extractedData.buyers.length})</span>
              {extractedData.buyers.map((b, i) => (
                <div key={i} className="extracted-seller">
                  <span>{b.name || '—'}</span>
                  <span className="extracted-dim">ת״ז {b.id_number || '—'}</span>
                </div>
              ))}
            </div>
          )}

          {/* Acquisitions */}
          {extractedData.acquisitions.length > 0 && (
            <div className="extracted-section">
              <span className="extracted-section-title">רכישה מקורית</span>
              {extractedData.acquisitions.map((a, i) => (
                <div key={i} className="extracted-seller">
                  <span>{a.acquisition_date || '—'}</span>
                  <span>{acquisitionTypeLabel(a.acquisition_type)}</span>
                  <span className="extracted-amount">
                    {a.amount ? `₪${a.amount.toLocaleString()}` : <span className="missing-inline">חסר: סכום רכישה</span>}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Payment Schedule */}
          {extractedData.payment_schedule && (
            <div className="extracted-section">
              <span className="extracted-section-title">לוח תשלומים</span>
              <div className="extracted-notes">{extractedData.payment_schedule}</div>
            </div>
          )}

          {/* Notes */}
          {extractedData.notes && (
            <div className="extracted-section">
              <span className="extracted-section-title">הערות</span>
              <div className="extracted-notes">{extractedData.notes}</div>
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
                <span className="extracted-approved">✓ הנתונים אושרו ומולאו בטופס</span>
                {missingFields.length > 0 && (
                  <span className="extracted-dim">השלם את השדות החסרים בטופס למטה</span>
                )}
                <button className="btn btn-sm btn-secondary" onClick={handleDismiss} type="button">הסתר</button>
              </>
            )}
          </div>
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
