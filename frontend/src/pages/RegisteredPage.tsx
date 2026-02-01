import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';

export const RegisteredPage: React.FC = () => {
  const words = useMemo(() => ['ACCESS', 'GRANTED'], []);

  return (
    <div className="min-h-screen">
      <nav className="brutal-nav">
        <Link to="/" className="nav-logo magnetic" data-glitch="SOAC" style={{ textDecoration: 'none' }}>
          SOAC
        </Link>
      </nav>

      <div className="brutal-scroll">
        <section className="hero">
          <h1>
            {words.map((word, idx) => (
              <React.Fragment key={word}>
                <div className="word">
                  {word.split('').map((ch, i) => (
                    <span className="char" key={`${word}-${i}`}>
                      {ch}
                    </span>
                  ))}
                </div>
                {idx === 0 ? <br /> : null}
              </React.Fragment>
            ))}
          </h1>

          <p className="big-text" style={{ marginTop: '3rem' }}>
            ACCOUNT INITIALIZED.
            <br />
            PROCEED TO <span>PIPELINE CONTROL</span>.
          </p>

          <Link to="/dashboard" className="cta-btn magnetic" style={{ marginTop: '2rem' }}>
            <span>GO TO DASHBOARD</span>
          </Link>
        </section>
      </div>
    </div>
  );
};

