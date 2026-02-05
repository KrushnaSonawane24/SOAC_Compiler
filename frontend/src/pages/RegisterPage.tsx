import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useAuth } from '../auth/AuthContext';
import { authApi } from '../api/auth';

export const RegisterPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const pwd = password;
      if (pwd.length < 8 || pwd.length > 14) {
        setError('Password must be 8–14 characters.');
        return;
      }
      if (pwd !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
      await register({ email, password, confirm_password: confirmPassword, display_name: username });
      navigate('/registered');
    } catch (err: unknown) {
      if (err instanceof AxiosError && err.response) {
        const data = err.response.data as unknown;
        if (typeof data === 'object' && data !== null && 'detail' in data) {
          const detail = (data as { detail?: unknown }).detail;
          if (typeof detail === 'string') {
            setError(detail);
          } else if (typeof detail === 'object' && detail !== null && 'error' in detail) {
            const maybeErr = (detail as { error?: unknown }).error;
            if (typeof maybeErr === 'string') setError(maybeErr);
          } else {
            setError('Registration failed. Please try again.');
          }
          return;
        }
      }
      setError('Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const isPasswordLengthValid = password.length >= 8 && password.length <= 14;
  const isPasswordMatch = password === confirmPassword;
  const canSubmit = Boolean(username) && Boolean(email) && Boolean(password) && Boolean(confirmPassword) && isPasswordLengthValid && isPasswordMatch;

  return (
    <div className="min-h-screen">
      <nav className="brutal-nav">
        <Link to="/" className="nav-logo magnetic" data-glitch="SOAC" style={{ textDecoration: 'none' }}>
          SOAC
        </Link>
        <ul className="nav-menu">
          <li>
            <Link to="/login" className="nav-link magnetic" data-text="LOGIN">
              LOGIN
            </Link>
          </li>
          <li>
            <Link to="/register" className="nav-link magnetic" data-text="REGISTER">
              REGISTER
            </Link>
          </li>
        </ul>
      </nav>

      <div className="brutal-scroll">
        <section className="section-dark" style={{ minHeight: '100vh', justifyContent: 'center' }}>
          <form className="auth-box" onSubmit={handleSubmit}>
            <h2 className="auth-title">CREATE OPERATOR</h2>

            {error ? (
              <div className="auth-link" style={{ color: '#ff7777', marginTop: 0 }}>
                {error}
              </div>
            ) : null}

            <input
              type="text"
              placeholder="Username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="email"
              placeholder="Email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              type="password"
              placeholder="Password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <input
              type="password"
              placeholder="Confirm Password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />

            <button type="submit" className="cta-btn magnetic" disabled={isLoading || !canSubmit}>
              <span>{isLoading ? 'INITIALIZING…' : 'INITIALIZE'}</span>
            </button>

            <button
              type="button"
              className="cta-btn cta-btn--ghost magnetic"
              style={{ marginTop: '0.75rem' }}
              onClick={() => {
                window.location.href = authApi.getGoogleLoginUrl();
              }}
            >
              <span>CONTINUE WITH GOOGLE</span>
            </button>

            <p className="auth-link">
              Already registered? <Link to="/login">Login</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
};
