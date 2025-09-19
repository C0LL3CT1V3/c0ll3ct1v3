import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';

function Landing() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="landing-page">
      <div className="landing-container">
        {/* Header */}
        <div className="landing-header">
          <h1 className="landing-title">C0ll3CT1V3 Business Management System</h1>
          <p className="landing-subtitle">Your Digital Command Center</p>
        </div>

        {/* Auth Card */}
        <div className="auth-card">
          <div className="auth-tabs">
            <button 
              className={`auth-tab ${isLogin ? 'active' : ''}`}
              onClick={() => setIsLogin(true)}
            >
              Login
            </button>
            <button 
              className={`auth-tab ${!isLogin ? 'active' : ''}`}
              onClick={() => setIsLogin(false)}
            >
              Create Account
            </button>
          </div>

          <div className="auth-form">
            {isLogin ? (
              <LoginForm />
            ) : (
              <SignupForm />
            )}
          </div>

          <div className="auth-footer">
            <p>Welcome to your business management system</p>
            <div className="feature-highlights">
              <span>🏦 Bank Accounts</span>
              <span>₿ Crypto Wallets</span>
              <span>📊 Ledgers</span>
              <span>📄 Documents</span>
            </div>
          </div>
        </div>

        {/* Demo Link */}
        <div className="demo-section">
          <p>Want to see the interface first?</p>
          <Link to="/dashboard" className="demo-btn">View Demo</Link>
        </div>
      </div>
    </div>
  );
}

function LoginForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      await authService.login(formData);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="form">
      <div className="form-group">
        <label>Email</label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
      </div>
      
      <div className="form-group">
        <label>Password</label>
        <input
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          required
        />
      </div>
      
      <button type="submit" className="auth-btn" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
      
      {error && <div className="error-message">{error}</div>}
      
      <div className="form-links">
        <button type="button" className="forgot-link">Forgot Password?</button>
      </div>
    </form>
  );
}

function SignupForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccess('');
    
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }
    
    try {
      await authService.register({
        name: formData.name,
        email: formData.email,
        password: formData.password
      });
      setSuccess('Account created successfully! Please login.');
      // Clear form
      setFormData({
        name: '',
        email: '',
        password: '',
        confirmPassword: ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="form">
      <div className="form-group">
        <label>Full Name</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          required
        />
      </div>
      
      <div className="form-group">
        <label>Email</label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
      </div>
      
      <div className="form-group">
        <label>Password</label>
        <input
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          required
        />
      </div>
      
      <div className="form-group">
        <label>Confirm Password</label>
        <input
          type="password"
          value={formData.confirmPassword}
          onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
          required
        />
      </div>
      
      <button type="submit" className="auth-btn" disabled={isLoading}>
        {isLoading ? 'Creating Account...' : 'Create Account'}
      </button>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      <div className="form-links">
        <p className="terms-text">
          By creating an account, you agree to our Terms of Service
        </p>
      </div>
    </form>
  );
}

export default Landing;
