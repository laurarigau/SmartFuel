/**
 * SmartFuel - Authentication Manager
 * Handles user authentication state, local tokens, and Cognito integration stub.
 */

class AuthManager {
  constructor() {
    this.tokenKey = 'smartfuel_auth_token';
    this.userKey = 'smartfuel_auth_user';
    this.currentUser = this.loadUser();
  }

  loadUser() {
    try {
      const stored = localStorage.getItem(this.userKey);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  isAuthenticated() {
    return Boolean(localStorage.getItem(this.tokenKey));
  }

  getUser() {
    return this.currentUser;
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  async signIn(email, password) {
    // In production with AWS Cognito:
    // Uses amazon-cognito-identity-js or calls the Cognito token endpoint
    // For local demo, we simulate successful sign in
    if (!email || !password) {
      throw new Error('Please provide email and password');
    }

    const mockToken = 'mock-jwt-token-' + btoa(email) + '.' + Date.now();
    const user = {
      email,
      id: 'user-' + Math.random().toString(36).substring(2, 9),
      name: email.split('@')[0],
    };

    localStorage.setItem(this.tokenKey, mockToken);
    localStorage.setItem(this.userKey, JSON.stringify(user));
    this.currentUser = user;

    this.notifyAuthStateChange();
    return user;
  }

  async signUp(email, password) {
    if (!email || !password) {
      throw new Error('Please provide email and password');
    }
    if (password.length < 8) {
      throw new Error('Password must be at least 8 characters');
    }

    // Simulate Cognito sign up
    return this.signIn(email, password);
  }

  signOut() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUser = null;
    this.notifyAuthStateChange();
  }

  notifyAuthStateChange() {
    window.dispatchEvent(new CustomEvent('auth-changed', {
      detail: { user: this.currentUser, isAuthenticated: this.isAuthenticated() }
    }));
  }
}

// Global instance
window.authManager = new AuthManager();
