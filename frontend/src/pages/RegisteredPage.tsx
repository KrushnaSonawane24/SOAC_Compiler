import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import './RegisteredPage.css';

export const RegisteredPage: React.FC = () => {
  const words = useMemo(() => ['ACCESS', 'GRANTED'], []);

  return (
    <div className="min-h-screen registered-page">
      <nav className="brutal-nav">
        <Link to="/" className="nav-logo magnetic" data-glitch="SOAC" style={{ textDecoration: 'none' }}>
          SOAC
        </Link>
      </nav>

      <div className="brutal-scroll">
        <section className="registered-hero">
          <p className="registered-subtext">
            ACCOUNT INITIALIZED.
            <br />
            PROCEED TO <span>PIPELINE CONTROL</span>.
          </p>

          <h1 className="registered-title" aria-label="Access granted">
            {words.map((word, idx) => (
              <React.Fragment key={word}>
                <div className="registered-word">
                  {word.split('').map((ch, i) => (
                    <span className="registered-char" key={`${word}-${i}`}>
                      {ch}
                    </span>
                  ))}
                </div>
                {idx === 0 ? <br /> : null}
              </React.Fragment>
            ))}
          </h1>

          <Link to="/dashboard" className="cta-btn magnetic" style={{ marginTop: '2rem' }}>
            <span>GO TO DASHBOARD</span>
          </Link>
        </section>
      </div>
    </div>
  );
};

