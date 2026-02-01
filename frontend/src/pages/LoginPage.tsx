import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [rememberEmail, setRememberEmail] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const savedEmail = useMemo(() => {
    const saved = localStorage.getItem('soac_login_email');
    return typeof saved === 'string' ? saved : '';
  }, []);

  useEffect(() => {
    const remembered = localStorage.getItem('soac_remember_email') === '1';
    setRememberEmail(remembered);
    if (remembered && savedEmail) setEmail(savedEmail);
  }, [savedEmail]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login({ email, password });
      if (rememberEmail) {
        localStorage.setItem('soac_login_email', email);
        localStorage.setItem('soac_remember_email', '1');
      } else {
        localStorage.removeItem('soac_login_email');
        localStorage.removeItem('soac_remember_email');
      }
      navigate('/dashboard');
    } catch {
      setError('Invalid email or password');
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
            <h2 className="auth-title">SYSTEM LOGIN</h2>

            {error ? (
              <div className="auth-link" style={{ color: '#ff7777', marginTop: 0 }}>
                {error}
              </div>
            ) : null}

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

            <button type="submit" className="cta-btn magnetic" disabled={isLoading}>
              <span>{isLoading ? 'ACCESSING…' : 'ACCESS SOAC'}</span>
            </button>

            <p className="auth-link">
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginRight: '0.75rem' }}>
                <input
                  type="checkbox"
                  checked={rememberEmail}
                  onChange={(e) => setRememberEmail(e.target.checked)}
                  style={{ width: 14, height: 14, margin: 0 }}
                />
                remember
              </label>
              New here? <Link to="/register">Create account</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
};
