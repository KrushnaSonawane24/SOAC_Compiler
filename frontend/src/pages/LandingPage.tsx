import React, { useMemo } from 'react';
import { BrutalNav } from '../brutal/BrutalNav';
import './LandingPage.css';

export const LandingPage: React.FC = () => {
  const heroWords = useMemo(() => ['BRUTAL', 'MAGIC'], []);

  return (
    <div className="landing-page">
      <BrutalNav variant="public" />

      <div className="brutal-scroll">
        <section className="hero">
          <div className="hero-title-container">
            <h1>
              {heroWords.map((word, idx) => (
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
          </div>

          <div className="tape-wrapper">
            <div className="tape-text">
              SOAC DIGITAL ✦ MODEL OPTIMIZATION ✦ EXPLAINABLE DECISIONS ✦ REPRODUCIBLE BUILDS ✦ SECURE MULTI-USER ✦
              SOAC DIGITAL ✦ MODEL OPTIMIZATION ✦ EXPLAINABLE DECISIONS ✦ REPRODUCIBLE BUILDS ✦ SECURE MULTI-USER ✦
            </div>
          </div>
        </section>

        <section className="section-dark">
          <p className="big-text">
            UPLOAD <span>ONNX MODELS</span>, RUN <span>POLICY-BASED</span> OPTIMIZATION, GET <span>ARTIFACTS</span> AND{' '}
            <span>REPORTS</span>. NO GUESSWORK. JUST <span>PURE CODE</span> AND <span>RAW AESTHETICS</span>.
          </p>
        </section>

        <section className="section-dark section-right">
          <p className="big-text">
            PIPELINE
            <br />
            <span>REDEFINED</span>
          </p>
        </section>

        <footer className="brutal-footer">
          <h2 className="brutal-footer-title">SOAC</h2>
          <p>© 2026</p>
        </footer>
      </div>
    </div>
  );
};
