/**
 * AWS Cognito Configuration
 */

export const cognitoConfig = {
  region: 'us-west-2',
  userPoolId: 'us-west-2_Sw8yyFfBT',
  userPoolClientId: '2d2cqqjvpf1ecqjg6gh1u6fivl',

  // OAuth configuration (optional)
  oauth: {
    domain: '', // Add if using Cognito hosted UI
    scope: ['email', 'openid', 'profile'],
    redirectSignIn: window.location.origin,
    redirectSignOut: window.location.origin,
    responseType: 'code'
  }
}

// Amplify Auth configuration
export const authConfig = {
  Auth: {
    Cognito: {
      userPoolId: cognitoConfig.userPoolId,
      userPoolClientId: cognitoConfig.userPoolClientId,
      region: cognitoConfig.region,
      loginWith: {
        email: true,
        username: false
      }
    }
  }
}
