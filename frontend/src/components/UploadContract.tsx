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
  sellers: Array<{ name?: string; id_number?: string; share_percent?: number }>
  acquisitions: Array<{ acquisition_date?: string; acquisition_type?: string; amount?: number }>
  property_address: string | null
  block_parcel: string | null
  notes: string | null
  confidence: string
}

export default function UploadContract({ token, onDataExtracted }: Props) {
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [codeVerified, setCodeVerified] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null)
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

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await axios.post('/api/upload-contract', formData, {
        headers: { Authorization: `Bearer ${token}` },
      })

      // Show extracted results
      setExtractedData(data)

      // Map extracted data to form format - fill ALL available fields
      const partial: Partial<TransactionInput> = {}
      
      // Sale details
      if (data.sale_date) partial.sale_date = data.sale_date
      if (data.sale_amount) partial.sale_amount = Number(data.sale_amount)
      if (data.sale_currency) partial.sale_currency = data.sale_currency
      
      // Sellers
      if (data.sellers?.length) {
        partial.sellers = data.sellers.map((s: Record<string, unknown>) => ({
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
      if (data.acquisitions?.length) {
        partial.acquisitions = data.acquisitions.map((a: Record<string, unknown>) => ({
          acquisition_date: String(a.acquisition_date || ''),
          acquisition_type: String(a.acquisition_type || 'purchase'),
          amount: Number(a.amount) || 0,
          currency: String(a.currency || 'ILS'),
          share_percent: Number(a.share_percent) || 100,
          deceased_eligible_for_exemption: false,
        }))
      }

      // Property type (always residential for contracts)
      partial.is_residential = true

      onDataExtracted(partial)
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

  function dismissResults() {
    setExtractedData(null)
  }

  const confidenceLabel = (c: string) =>
    c === 'high' ? 'גבוהה ✓' : c === 'medium' ? 'בינונית ⚠' : 'נמוכה'
  const confidenceColor = (c: string) =>
    c === 'high' ? 'var(--success)' : c === 'medium' ? '#fbbf24' : '#f87171'

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

      {/* Extracted Results Panel */}
      {extractedData && (
        <div className="extracted-results">
          <div className="extracted-header">
            <h3>📋 נתונים שחולצו מהחוזה</h3>
            <div className="extracted-badge" style={{ color: confidenceColor(extractedData.confidence) }}>
              {confidenceLabel(extractedData.confidence)}
            </div>
          </div>

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

          {extractedData.sellers.length > 0 && (
            <div className="extracted-section">
              <span className="extracted-section-title">מוכרים ({extractedData.sellers.length})</span>
              {extractedData.sellers.map((s, i) => (
                <div key={i} className="extracted-seller">
                  <span>{s.name || '—'}</span>
                  <span className="extracted-dim">{s.id_number || ''}</span>
                  <span className="extracted-badge-sm">{s.share_percent || 100}%</span>
                </div>
              ))}
            </div>
          )}

          {extractedData.acquisitions.length > 0 && (
            <div className="extracted-section">
              <span className="extracted-section-title">רכישות</span>
              {extractedData.acquisitions.map((a, i) => (
                <div key={i} className="extracted-seller">
                  <span>{a.acquisition_date || '—'}</span>
                  <span>{a.acquisition_type === 'purchase' ? 'רכישה' : a.acquisition_type === 'inheritance' ? 'ירושה' : a.acquisition_type || '—'}</span>
                  <span className="extracted-amount">{a.amount ? `₪${a.amount.toLocaleString()}` : '—'}</span>
                </div>
              ))}
            </div>
          )}

          {extractedData.notes && (
            <div className="extracted-notes">{extractedData.notes}</div>
          )}

          <div className="extracted-footer">
            <span className="extracted-dim">הנתונים מולאו בטופס אוטומטית. בדוק ותקן לפני חישוב.</span>
            <button className="btn btn-sm btn-secondary" onClick={dismissResults} type="button">הסתר</button>
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
