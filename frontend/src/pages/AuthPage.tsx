import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import './AuthPage.css'

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { handleLogin, handleSignup, loading, error } = useAuth()

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    mode === 'login' ? handleLogin(email, password) : handleSignup(email, password)
  }

  return (
    <div className="auth-root">
      {/* Left panel */}
      <div className="auth-hero">
        <div className="auth-hero-content">
          <div className="auth-logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">Vector</span>
          </div>
          <h1 className="auth-headline">
           Discover your next opportunity<br />
          <em>with Vector.</em>
          </h1>
          <p className="auth-sub">
            Vector is your AI-powered career companion — delivering fresh job opportunities daily, 
            helping you tailor your resume, and guiding you toward roles that truly match your skills.
          </p>
          <div className="auth-stats">
            <div className="stat">
              <span className="stat-num">12k+</span>
              <span className="stat-label">Live Listings</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-num">98%</span>
              <span className="stat-label">Match Accuracy</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-num">Daily</span>
              <span className="stat-label">Updates</span>
            </div>
          </div>
        </div>
        <div className="auth-hero-glow" />
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />
      </div>

      {/* Right panel */}
      <div className="auth-panel">
        <div className="auth-card">
          {/* Tab switcher */}
          <div className="auth-tabs">
            <button
              className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => setMode('login')}
            >
              Sign In
            </button>
            <button
              className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => setMode('signup')}
            >
              Create Account
            </button>
          </div>

          <div className="auth-form-header">
            <h2>{mode === 'login' ? 'Welcome back' : 'Get started'}</h2>
            <p>{mode === 'login' ? 'Sign in to your account.' : 'Create your free account today.'}</p>
          </div>

          <form onSubmit={submit} className="auth-form">
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={8}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading
                ? 'Please wait…'
                : mode === 'login' ? 'Sign In →' : 'Create Account →'}
            </button>
          </form>

          <p className="auth-legal">
            By continuing you agree to our{' '}
            <a href="#">Terms</a> and <a href="#">Privacy Policy</a>.
          </p>
        </div>
      </div>
    </div>
  )
}
