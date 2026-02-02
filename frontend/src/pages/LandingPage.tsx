import React, { useEffect, useMemo, useRef, useState } from 'react';
import { BrutalNav } from '../brutal/BrutalNav';
import { authApi } from '../api/auth';
import { useAuth } from '../auth/AuthContext';
import './LandingPage.css';

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const heroWords = useMemo(() => ['BRUTAL', 'MAGIC'], []);
  const heroTitleContainerRef = useRef<HTMLDivElement | null>(null);
  const heroTitleRef = useRef<HTMLHeadingElement | null>(null);
  const [heroReady, setHeroReady] = useState(false);
  const featureSectionRef = useRef<HTMLElement | null>(null);
  const [featureInView, setFeatureInView] = useState(false);
  const pipelineStages = useMemo(
    () => [
      { key: 'normalizing', label: 'NORMALIZING' },
      { key: 'validating', label: 'VALIDATING' },
      { key: 'canonicalizing', label: 'CANONICALIZING' },
      { key: 'optimizing', label: 'OPTIMIZING' },
      { key: 'benchmarking', label: 'BENCHMARKING' },
      { key: 'selecting', label: 'SELECTING' },
      { key: 'deploying', label: 'DEPLOYING' },
    ],
    [],
  );
  const pipelineSectionRef = useRef<HTMLElement | null>(null);
  const pipelineStageListRef = useRef<HTMLDivElement | null>(null);
  const [pipelineRevealCount, setPipelineRevealCount] = useState(0);
  const [pipelineOutIndices, setPipelineOutIndices] = useState<number[]>([]);
  const pipelineOutTimersRef = useRef<Map<number, number>>(new Map());

  const heroLetters = useMemo(() => {
    let index = 0;
    return heroWords.map((word) => {
      const chars = word.split('').map((ch) => ({ ch, index: index++ }));
      return { word, chars };
    });
  }, [heroWords]);

  useEffect(() => {
    const t = window.requestAnimationFrame(() => setHeroReady(true));
    return () => window.cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    const container = heroTitleContainerRef.current;
    const title = heroTitleRef.current;
    if (!container || !title) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (!window.matchMedia('(pointer: fine)').matches) return;

    let rafId = 0;
    let lastX = 0;
    let lastY = 0;

    const apply = () => {
      rafId = 0;
      title.style.setProperty('--hero-tilt-x', `${lastY.toFixed(2)}deg`);
      title.style.setProperty('--hero-tilt-y', `${lastX.toFixed(2)}deg`);
    };

    const onMove = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      const nx = (e.clientX - rect.left) / Math.max(rect.width, 1) - 0.5;
      const ny = (e.clientY - rect.top) / Math.max(rect.height, 1) - 0.5;
      lastX = nx * 10;
      lastY = -ny * 8;
      if (!rafId) rafId = window.requestAnimationFrame(apply);
    };

    const onLeave = () => {
      title.style.setProperty('--hero-tilt-x', '0deg');
      title.style.setProperty('--hero-tilt-y', '0deg');
    };

    container.addEventListener('pointermove', onMove);
    container.addEventListener('pointerleave', onLeave);
    return () => {
      container.removeEventListener('pointermove', onMove);
      container.removeEventListener('pointerleave', onLeave);
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, []);

  const featureTokens = useMemo(() => {
    const tokens: Array<{ text: string; highlight: boolean }> = [
      { text: 'UPLOAD ', highlight: false },
      { text: 'ONNX', highlight: true },
      { text: ' ', highlight: false },
      { text: 'MODELS', highlight: true },
      { text: ', ', highlight: false },
      { text: 'RUN ', highlight: false },
      { text: 'POLICY-BASED', highlight: true },
      { text: ' ', highlight: false },
      { text: 'OPTIMIZATION, ', highlight: false },
      { text: 'GET ', highlight: false },
      { text: 'ARTIFACTS', highlight: true },
      { text: ' ', highlight: false },
      { text: 'AND ', highlight: false },
      { text: 'REPORTS', highlight: true },
      { text: '. ', highlight: false },
      { text: 'NO ', highlight: false },
      { text: 'GUESSWORK. ', highlight: false },
      { text: 'JUST ', highlight: false },
      { text: 'PURE', highlight: true },
      { text: ' ', highlight: false },
      { text: 'CODE', highlight: true },
      { text: ' ', highlight: false },
      { text: 'AND ', highlight: false },
      { text: 'RAW', highlight: true },
      { text: ' ', highlight: false },
      { text: 'AESTHETICS', highlight: true },
      { text: '.', highlight: false },
    ];

    const highlightCount = tokens.filter((t) => t.highlight).length;
    let hiIndex = 0;
    let normalIndex = 0;

    return tokens.map((t) => {
      const order = t.highlight ? hiIndex++ : highlightCount + normalIndex++;
      return { ...t, delay: `${order * 36}ms` };
    });
  }, []);

  useEffect(() => {
    const el = featureSectionRef.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setFeatureInView(true);
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        setFeatureInView(entry.isIntersecting);
      },
      { root: null, rootMargin: '-35% 0px -35% 0px', threshold: 0.01 },
    );

    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const sectionEl = pipelineSectionRef.current;
    const listEl = pipelineStageListRef.current;
    if (!sectionEl || !listEl) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    let rafId = 0;
    const exitMs = 320;

    const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

    const update = () => {
      rafId = 0;
      const vh = window.innerHeight;
      const listRect = listEl.getBoundingClientRect();
      const startLine = vh * 0.8;
      const endLine = vh * 0.35;
      const progress = clamp((startLine - listRect.top) / Math.max(startLine - endLine, 1), 0, 1);

      const n = pipelineStages.length;
      const adjusted = clamp((progress - 0.12) / 0.88, 0, 1);
      const reveal = adjusted <= 0 ? 0 : clamp(Math.floor(adjusted * n) + 1, 0, n);
      setPipelineRevealCount((prev) => {
        if (prev === reveal) return prev;

        if (reveal < prev) {
          const removed: number[] = [];
          for (let i = reveal; i < prev; i += 1) removed.push(i);

          setPipelineOutIndices((current) => {
            const set = new Set(current);
            removed.forEach((idx) => set.add(idx));
            return Array.from(set);
          });

          removed.forEach((idx) => {
            const prevTimer = pipelineOutTimersRef.current.get(idx);
            if (prevTimer) window.clearTimeout(prevTimer);
            const timer = window.setTimeout(() => {
              pipelineOutTimersRef.current.delete(idx);
              setPipelineOutIndices((current) => current.filter((x) => x !== idx));
            }, exitMs);
            pipelineOutTimersRef.current.set(idx, timer);
          });
        } else {
          const added: number[] = [];
          for (let i = prev; i < reveal; i += 1) added.push(i);
          if (added.length) {
            setPipelineOutIndices((current) => current.filter((x) => !added.includes(x)));
            added.forEach((idx) => {
              const prevTimer = pipelineOutTimersRef.current.get(idx);
              if (prevTimer) {
                window.clearTimeout(prevTimer);
                pipelineOutTimersRef.current.delete(idx);
              }
            });
          }
        }

        return reveal;
      });
    };

    const onScroll = () => {
      if (rafId) return;
      rafId = window.requestAnimationFrame(update);
    };

    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (rafId) window.cancelAnimationFrame(rafId);
      pipelineOutTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      pipelineOutTimersRef.current.clear();
    };
  }, [pipelineStages.length]);

  return (
    <div className="landing-page">
      <BrutalNav variant={isAuthenticated ? 'app' : 'public'} />

      <div className="brutal-scroll">
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-title-container" ref={heroTitleContainerRef}>
              <h1 ref={heroTitleRef} className={heroReady ? 'hero-title hero-title--ready' : 'hero-title'}>
                {heroLetters.map((w, idx) => (
                  <React.Fragment key={w.word}>
                    <div className="word">
                      {w.chars.map(({ ch, index }) => (
                        <span className="char" key={`${w.word}-${index}`} style={{ ['--i' as any]: index }}>
                          {ch}
                        </span>
                      ))}
                    </div>
                    {idx === 0 ? <br /> : null}
                  </React.Fragment>
                ))}
              </h1>
            </div>
          </div>

          <div className="hero-actions">
            {isAuthenticated ? (
              <a className="cta-btn magnetic" href="/dashboard">
                <span>DASHBOARD</span>
              </a>
            ) : (
              <>
                <a className="cta-btn magnetic" href="/login">
                  <span>ACCESS</span>
                </a>
                <a className="cta-btn cta-btn--ghost magnetic" href={authApi.getGoogleLoginUrl()}>
                  <span>CONTINUE WITH GOOGLE</span>
                </a>
              </>
            )}
          </div>

          <div className="tape-wrapper">
            <div className="tape-text">
              SOAC DIGITAL ✦ MODEL OPTIMIZATION ✦ EXPLAINABLE DECISIONS ✦ REPRODUCIBLE BUILDS ✦ SECURE MULTI-USER ✦
              SOAC DIGITAL ✦ MODEL OPTIMIZATION ✦ EXPLAINABLE DECISIONS ✦ REPRODUCIBLE BUILDS ✦ SECURE MULTI-USER ✦
            </div>
          </div>
        </section>

        <section className="section-dark" ref={featureSectionRef}>
          <div className="section-inner">
            <p className={featureInView ? 'big-text feature-stagger is-in' : 'big-text feature-stagger'}>
              {featureTokens.map((t, i) => (
                <span
                  key={`${t.text}-${i}`}
                  className={t.highlight ? 'feature-word feature-word--hi' : 'feature-word'}
                  style={{ ['--delay' as any]: t.delay }}
                >
                  {t.text}
                </span>
              ))}
            </p>
          </div>
        </section>

        <section className="section-dark pipeline-section" ref={pipelineSectionRef}>
          <div className="section-inner">
            <div className="pipeline-grid">
              <div className="pipeline-left">
                <p className={pipelineRevealCount > 0 ? 'pipeline-kicker is-in' : 'pipeline-kicker'}>STAGES</p>
                <div className="pipeline-stage-list" ref={pipelineStageListRef}>
                  {pipelineStages.map((stage, index) => (
                    <div
                      className={
                        index < pipelineRevealCount
                          ? 'pipeline-stage is-in'
                          : pipelineOutIndices.includes(index)
                            ? 'pipeline-stage is-out'
                            : 'pipeline-stage'
                      }
                      data-stage={stage.key}
                      key={stage.key}
                    >
                      {stage.label}
                    </div>
                  ))}
                </div>
              </div>
              <div className="pipeline-right">
                <p className="big-text">
                  PIPELINE
                  <br />
                  <span>REDEFINED</span>
                </p>
              </div>
            </div>
          </div>
        </section>

        <footer className="brutal-footer">
          <h2 className="brutal-footer-title">SOAC</h2>
          <p className="footer-meta">© 2026</p>
          <p className="footer-kicker">LINKS</p>
          <div className="footer-links">
            <a
              className="footer-link magnetic"
              data-text="GITHUB"
              href="https://github.com/aatif-shaikh19/SOAC-v2"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
            <button
              className="footer-link magnetic"
              data-text="ABOUT"
              type="button"
              onClick={() => window.open('/about', 'aboutWindow', 'width=980,height=720,menubar=no,toolbar=no')}
            >
              About
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};
