import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

type BrutalNavVariant = 'public' | 'app';

type BrutalNavProps = {
  variant: BrutalNavVariant;
};

export const BrutalNav: React.FC<BrutalNavProps> = ({ variant }) => {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const showAppNav = variant === 'app' && isAuthenticated;

  return (
    <nav className="brutal-nav">
      <Link
        to="/"
        className="nav-logo magnetic"
        data-glitch="SOAC"
        style={{ textDecoration: 'none' }}
      >
        SOAC
      </Link>

      <ul className="nav-menu">
        {showAppNav ? (
          <>
            <li>
              <Link to="/dashboard" className="nav-link magnetic" data-text="DASHBOARD">
                DASHBOARD
              </Link>
            </li>
            <li>
              <Link to="/new" className="nav-link magnetic" data-text="UPLOAD">
                UPLOAD
              </Link>
            </li>
            <li>
              <Link to="/docs" className="nav-link magnetic" data-text="DOCS">
                DOCS
              </Link>
            </li>
          </>
        ) : (
          <>
            <li>
              <Link to="/docs" className="nav-link magnetic" data-text="DOCS">
                Docs
              </Link>
            </li>
            <li>
              <Link to="/login" className="nav-link magnetic" data-text="LOGIN">
                Login
              </Link>
            </li>
            <li>
              <Link to="/register" className="nav-link magnetic" data-text="REGISTER">
                Register
              </Link>
            </li>
          </>
        )}
      </ul>

      {showAppNav ? (
        <button type="button" className="cta-btn magnetic" onClick={handleLogout}>
          <span>DISCONNECT</span>
        </button>
      ) : (
        <Link to="/login" className="cta-btn magnetic">
          <span>ACCESS</span>
        </Link>
      )}
    </nav>
  );
};
