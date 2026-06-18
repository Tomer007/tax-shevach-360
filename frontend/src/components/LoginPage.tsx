import { useState } from 'react'
import axios from 'axios'

interface Props {
  onLogin: (token: string) => void
}

export default function LoginPage({ onLogin }: Props) {
  const [step, setStep] = useState<'code' | 'login'>('code')
  const [codeName, setCodeName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleCodeSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await axios.post('/api/auth/verify-code', { code_name: codeName })
      setStep('login')
    } catch {
      setError('קוד גישה שגוי')
    } finally {
      setLoading(false)
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await axios.post('/api/auth/login', { username, password })
      onLogin(data.access_token)
    } catch {
      setError('שם משתמש או סיסמה שגויים')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <h1>מס שבח 360</h1>
          <p>{step === 'code' ? 'הזן קוד גישה' : 'התחברות'}</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        {step === 'code' ? (
          <form onSubmit={handleCodeSubmit}>
            <div className="login-field">
              <label htmlFor="code_name">קוד גישה</label>
              <input
                id="code_name"
                type="text"
                value={codeName}
                onChange={(e) => setCodeName(e.target.value)}
                placeholder="הזן את קוד הגישה"
                autoFocus
                autoComplete="off"
                style={{ direction: 'ltr', textAlign: 'center', letterSpacing: '0.15em', fontWeight: 700 }}
              />
            </div>
            <button className="login-btn" type="submit" disabled={!codeName.trim() || loading}>
              {loading ? 'בודק...' : 'אמת קוד'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <div className="login-field">
              <label htmlFor="username">שם משתמש</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="שם משתמש"
                autoFocus
                autoComplete="username"
              />
            </div>
            <div className="login-field">
              <label htmlFor="password">סיסמה</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="סיסמה"
                autoComplete="current-password"
              />
            </div>
            <button className="login-btn" type="submit" disabled={!username || !password || loading}>
              {loading ? 'מתחבר...' : 'התחבר'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
