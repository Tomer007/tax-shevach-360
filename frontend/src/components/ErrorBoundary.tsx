import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="login-page">
          <div className="login-card" style={{ textAlign: 'center' }}>
            <h2 style={{ color: '#ef4444', marginBottom: 12 }}>שגיאה בלתי צפויה</h2>
            <p style={{ color: '#a1a1aa', marginBottom: 20, fontSize: '0.85rem' }}>
              אירעה שגיאה. נסה לרענן את הדף.
            </p>
            <button
              className="login-btn"
              onClick={() => window.location.reload()}
              type="button"
            >
              רענן דף
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
