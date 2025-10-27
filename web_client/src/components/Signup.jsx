import { useState } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { Mail, Lock, Loader2, AlertCircle, CheckCircle } from 'lucide-react'

function Signup({ onSwitchToLogin }) {
  const [step, setStep] = useState('signup') // 'signup' or 'confirm'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')

  const { signup, confirmSignup, resendCode } = useAuth()

  const handleSignup = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password strength (Cognito requires minimum 8 characters)
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setLoading(true)

    try {
      const result = await signup(email, password)

      if (result.success) {
        setSuccess('Account created! Check your email for verification code.')
        setStep('confirm')
      } else {
        setError(result.error || 'Signup failed. Please try again.')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const result = await confirmSignup(email, code)

      if (result.success) {
        setSuccess('Email verified! Redirecting to login...')
        setTimeout(() => {
          onSwitchToLogin()
        }, 2000)
      } else {
        setError(result.error || 'Verification failed. Please try again.')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleResendCode = async () => {
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const result = await resendCode(email)
      if (result.success) {
        setSuccess('Verification code sent! Check your email.')
      } else {
        setError(result.error || 'Failed to resend code')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>🤖 Claude Agent</h1>
          <h2>{step === 'signup' ? 'Create Account' : 'Verify Email'}</h2>
          <p>
            {step === 'signup'
              ? 'Sign up to start using Claude Agent'
              : 'Enter the verification code sent to your email'}
          </p>
        </div>

        {step === 'signup' ? (
          <form onSubmit={handleSignup} className="auth-form">
            {error && (
              <div className="auth-error">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="auth-success">
                <CheckCircle size={16} />
                <span>{success}</span>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="email">
                <Mail size={16} />
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">
                <Lock size={16} />
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="new-password"
                disabled={loading}
                minLength={8}
              />
              <small>Must be at least 8 characters</small>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">
                <Lock size={16} />
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="new-password"
                disabled={loading}
                minLength={8}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !email || !password || !confirmPassword}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spinning" />
                  Creating account...
                </>
              ) : (
                'Sign Up'
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirm} className="auth-form">
            {error && (
              <div className="auth-error">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="auth-success">
                <CheckCircle size={16} />
                <span>{success}</span>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="code">Verification Code</label>
              <input
                id="code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
                required
                disabled={loading}
                maxLength={6}
              />
              <small>Check your email for the 6-digit code</small>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !code}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spinning" />
                  Verifying...
                </>
              ) : (
                'Verify Email'
              )}
            </button>

            <button
              type="button"
              onClick={handleResendCode}
              className="btn btn-secondary btn-block"
              disabled={loading}
            >
              Resend Code
            </button>
          </form>
        )}

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="link-button"
              disabled={loading}
            >
              Sign In
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Signup
