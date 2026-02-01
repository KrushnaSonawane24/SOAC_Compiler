import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useAuth } from '../auth/AuthContext';

export const RegisterPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await register({ email, password });
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

            <button type="submit" className="cta-btn magnetic" disabled={isLoading || !username}>
              <span>{isLoading ? 'INITIALIZING…' : 'INITIALIZE'}</span>
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
