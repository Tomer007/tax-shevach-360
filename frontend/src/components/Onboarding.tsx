interface Props {
  onDismiss: () => void
}

export default function Onboarding({ onDismiss }: Props) {
  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-label="ברוכים הבאים">
      <div className="onboarding-card">
        <div className="onboarding-icon">₪</div>
        <h2>ברוכים הבאים למס שבח 360</h2>
        <p>מחשבון מס שבח מקרקעין מדויק ומקצועי</p>
        <div className="onboarding-steps">
          <div className="onboarding-step">
            <span className="onboarding-step-num">1</span>
            <span>העלה חוזה מכר או מלא ידנית את פרטי העסקה</span>
          </div>
          <div className="onboarding-step">
            <span className="onboarding-step-num">2</span>
            <span>השלם את 5 השלבים: מכירה, מוכרים, רכישה, ניכויים, פטורים</span>
          </div>
          <div className="onboarding-step">
            <span className="onboarding-step-num">3</span>
            <span>קבל חישוב מפורט עם השוואת מסלולים והמלצה</span>
          </div>
        </div>
        <div className="onboarding-tip">
          💡 טיפ: העלאת חוזה חוסכת הזנה ידנית — המערכת מחלצת נתונים אוטומטית
        </div>
        <button className="btn btn-primary onboarding-btn" onClick={onDismiss} type="button">
          בואו נתחיל →
        </button>
      </div>
    </div>
  )
}
