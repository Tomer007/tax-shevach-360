import { useRef, useState } from 'react'
import axios from 'axios'
import type { TransactionInput } from '../types'
import CodeNameModal from './CodeNameModal'

interface Props {
  token: string
  onDataExtracted: (partial: Partial<TransactionInput>) => void
}

export default function UploadContract({ token, onDataExtracted }: Props) {
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [codeVerified, setCodeVerified] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
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
    // Now trigger file picker
    setTimeout(() => fileRef.current?.click(), 100)
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    setSuccess('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await axios.post('/api/upload-contract', formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      })

      // Map extracted data to form format
      const partial: Partial<TransactionInput> = {}
      if (data.sale_date) partial.sale_date = data.sale_date
      if (data.sale_amount) partial.sale_amount = data.sale_amount
      if (data.sale_currency) partial.sale_currency = data.sale_currency
      if (data.sellers?.length) {
        partial.sellers = data.sellers.map((s: Record<string, unknown>) => ({
          name: s.name || '',
          id_number: s.id_number || '',
          birth_date: s.birth_date || '',
          share_percent: s.share_percent || 100,
          is_israeli_resident: s.is_israeli_resident ?? true,
          marital_status: 'single',
          annual_incomes: {},
          prisa_max_years: [],
        }))
      }
      if (data.acquisitions?.length) {
        partial.acquisitions = data.acquisitions.map((a: Record<string, unknown>) => ({
          acquisition_date: a.acquisition_date || '',
          acquisition_type: a.acquisition_type || 'purchase',
          amount: a.amount || 0,
          currency: a.currency || 'ILS',
          share_percent: a.share_percent || 100,
          deceased_eligible_for_exemption: false,
        }))
      }

      onDataExtracted(partial)
      setSuccess(`חוזה נקרא בהצלחה (רמת ביטחון: ${data.confidence === 'high' ? 'גבוהה' : data.confidence === 'medium' ? 'בינונית' : 'נמוכה'})`)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('שגיאה בקריאת החוזה')
      }
    } finally {
      setUploading(false)
      // Reset file input
      if (fileRef.current) fileRef.current.value = ''
    }
  }

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
        {success && <span className="upload-success">{success}</span>}
      </div>

      {showCodeModal && (
        <CodeNameModal
          onVerified={handleCodeVerified}
          onClose={() => setShowCodeModal(false)}
        />
      )}
    </>
  )
}
