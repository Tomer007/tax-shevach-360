import { useState } from 'react'
import axios from 'axios'

interface Props {
  onVerified: () => void
  onClose: () => void
}

export default function CodeNameModal({ onVerified, onClose }: Props) {
  const [codeName, setCodeName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await axios.post('/api/auth/verify-code', { code_name: codeName })
      onVerified()
    } catch {
      setError('קוד גישה שגוי')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>קוד גישה נדרש</h3>
          <button className="modal-close" onClick={onClose} type="button" aria-label="סגור">
            ✕
          </button>
        </div>
        <p className="modal-desc">
          העלאת חוזה דורשת קוד גישה מיוחד. הזן את הקוד כדי להמשיך.
        </p>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="code_input">קוד גישה</label>
            <input
              id="code_input"
              type="text"
              value={codeName}
              onChange={(e) => setCodeName(e.target.value)}
              placeholder="הזן קוד"
              autoFocus
              autoComplete="off"
              style={{ direction: 'ltr', textAlign: 'center', letterSpacing: '0.15em', fontWeight: 700 }}
            />
          </div>
          <button className="login-btn" type="submit" disabled={!codeName.trim() || loading}>
            {loading ? 'בודק...' : 'אמת קוד'}
          </button>
        </form>
      </div>
    </div>
  )
}
