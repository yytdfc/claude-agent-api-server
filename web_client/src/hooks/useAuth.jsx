import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import { Amplify } from 'aws-amplify'
import {
  signIn,
  signUp,
  signOut,
  confirmSignUp,
  resendSignUpCode,
  getCurrentUser,
  fetchAuthSession
} from 'aws-amplify/auth'
import { authConfig } from '../config/cognito'

// Configure Amplify
Amplify.configure(authConfig)

// Create Auth Context
const AuthContext = createContext(null)

/**
 * Auth Provider Component
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Check if user is already authenticated
  const checkUser = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser()
      const session = await fetchAuthSession()

      setUser({
        username: currentUser.username,
        userId: currentUser.userId,
        signInDetails: currentUser.signInDetails,
        tokens: session.tokens
      })
      setError(null)
    } catch (err) {
      setUser(null)
      // Don't set error for unauthenticated state
      if (err.name !== 'UserUnAuthenticatedException') {
        console.error('Auth check error:', err)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkUser()
  }, [checkUser])

  // Sign in (accepts username or email)
  const login = useCallback(async (usernameOrEmail, password) => {
    setLoading(true)
    setError(null)
    try {
      const result = await signIn({
        username: usernameOrEmail,
        password
      })

      if (result.isSignedIn) {
        await checkUser()
        return { success: true }
      } else if (result.nextStep) {
        return {
          success: false,
          nextStep: result.nextStep.signInStep,
          message: 'Additional steps required'
        }
      }
    } catch (err) {
      console.error('Login error:', err)
      setError(err.message || 'Failed to sign in')
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [checkUser])

  // Sign up
  const signup = useCallback(async (username, email, password) => {
    setLoading(true)
    setError(null)
    try {
      console.log('📝 Starting signup for:', { username, email })

      const result = await signUp({
        username: username,
        password,
        options: {
          userAttributes: {
            email
          }
        }
      })

      console.log('✅ Signup result:', result)
      console.log('📧 Next step:', result.nextStep)
      console.log('🆔 User ID:', result.userId)

      return {
        success: true,
        userId: result.userId,
        nextStep: result.nextStep.signUpStep,
        isSignUpComplete: result.isSignUpComplete,
        nextStepDetails: result.nextStep
      }
    } catch (err) {
      console.error('❌ Signup error:', err)
      console.error('Error name:', err.name)
      console.error('Error message:', err.message)
      setError(err.message || 'Failed to sign up')
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [])

  // Confirm sign up
  const confirmSignup = useCallback(async (username, code) => {
    setLoading(true)
    setError(null)
    try {
      await confirmSignUp({
        username: username,
        confirmationCode: code
      })
      return { success: true }
    } catch (err) {
      console.error('Confirm signup error:', err)
      setError(err.message || 'Failed to confirm sign up')
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [])

  // Resend confirmation code
  const resendCode = useCallback(async (username) => {
    try {
      await resendSignUpCode({
        username: username
      })
      return { success: true }
    } catch (err) {
      console.error('Resend code error:', err)
      return { success: false, error: err.message }
    }
  }, [])

  // Sign out
  const logout = useCallback(async () => {
    setLoading(true)
    try {
      await signOut()
      setUser(null)
      setError(null)
      return { success: true }
    } catch (err) {
      console.error('Logout error:', err)
      setError(err.message || 'Failed to sign out')
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [])

  // Get valid access token (refreshes if needed)
  const getValidAccessToken = useCallback(async () => {
    try {
      const session = await fetchAuthSession({ forceRefresh: false })
      if (!session.tokens || !session.tokens.accessToken) {
        return null
      }

      const accessToken = session.tokens.accessToken
      const expiresAt = accessToken.payload.exp * 1000 // Convert to milliseconds
      const now = Date.now()
      const timeUntilExpiry = expiresAt - now

      // Token refresh threshold: 5 minutes
      const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000

      // If token expires soon, force refresh
      if (timeUntilExpiry < TOKEN_REFRESH_THRESHOLD) {
        console.log('🔄 Access token expiring soon, refreshing...')
        const refreshedSession = await fetchAuthSession({ forceRefresh: true })
        return refreshedSession.tokens?.accessToken?.toString() || null
      }

      return accessToken.toString()
    } catch (err) {
      console.error('Failed to get access token:', err)
      return null
    }
  }, [])

  const value = {
    user,
    loading,
    error,
    login,
    signup,
    confirmSignup,
    resendCode,
    logout,
    getValidAccessToken,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to use Auth context
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
