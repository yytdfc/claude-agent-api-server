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

  // Sign in
  const login = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      const result = await signIn({
        username: email,
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
  const signup = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      const result = await signUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email
          }
        }
      })

      return {
        success: true,
        userId: result.userId,
        nextStep: result.nextStep.signUpStep
      }
    } catch (err) {
      console.error('Signup error:', err)
      setError(err.message || 'Failed to sign up')
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [])

  // Confirm sign up
  const confirmSignup = useCallback(async (email, code) => {
    setLoading(true)
    setError(null)
    try {
      await confirmSignUp({
        username: email,
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
  const resendCode = useCallback(async (email) => {
    try {
      await resendSignUpCode({
        username: email
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

  const value = {
    user,
    loading,
    error,
    login,
    signup,
    confirmSignup,
    resendCode,
    logout,
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
