import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
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
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'nav-link nav-link--active magnetic' : 'nav-link magnetic';

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
              <NavLink to="/dashboard" end className={navLinkClass} data-text="DASHBOARD">
                DASHBOARD
              </NavLink>
            </li>
            <li>
              <NavLink to="/new" className={navLinkClass} data-text="UPLOAD">
                UPLOAD
              </NavLink>
            </li>
            <li>
              <NavLink to="/docs" className={navLinkClass} data-text="DOCS">
                DOCS
              </NavLink>
            </li>
          </>
        ) : (
          <>
            <li>
              <NavLink to="/docs" className={navLinkClass} data-text="DOCS">
                DOCS
              </NavLink>
            </li>
            <li>
              <NavLink to="/login" className={navLinkClass} data-text="LOGIN">
                LOGIN
              </NavLink>
            </li>
            <li>
              <NavLink to="/register" className={navLinkClass} data-text="REGISTER">
                REGISTER
              </NavLink>
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
