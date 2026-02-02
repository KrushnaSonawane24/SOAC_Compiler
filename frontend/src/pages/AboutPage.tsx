import React from 'react';
import { Link } from 'react-router-dom';
import { BrutalNav } from '../brutal/BrutalNav';

export const AboutPage: React.FC = () => {
  return (
    <div className="min-h-screen">
      <BrutalNav variant="public" />
      <main className="px-6 pb-16 pt-24">
        <div className="mx-auto w-full max-w-5xl">
          <p className="text-xs font-semibold tracking-[0.22em] text-[color:var(--soac-muted)]">ABOUT</p>
          <h1 className="soac-display mt-3 text-4xl font-extrabold tracking-tight text-[color:var(--soac-text)] sm:text-5xl">
            SOAC — Self-Optimizing AI Compiler
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-[color:var(--soac-muted)]">
            SOAC turns model optimization into a deterministic pipeline: clear inputs, explicit policies, repeatable passes, and verifiable artifacts.
            It is designed for teams that want performance gains without losing traceability, security, or deployment discipline.
          </p>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <section className="card">
              <p className="text-xs font-semibold tracking-[0.18em] text-[color:var(--soac-muted)]">WHAT YOU GET</p>
              <ul className="mt-4 space-y-3 text-[color:var(--soac-text)]">
                <li>
                  <span className="font-semibold">Policy-based optimization</span> that encodes constraints and priorities.
                </li>
                <li>
                  <span className="font-semibold">Artifacts</span> you can ship: optimized models, configs, and deployment-ready outputs.
                </li>
                <li>
                  <span className="font-semibold">Reports</span> for explainability and decision traceability.
                </li>
                <li>
                  <span className="font-semibold">Reproducibility</span> through stable passes and deterministic outputs.
                </li>
              </ul>
            </section>

            <section className="card">
              <p className="text-xs font-semibold tracking-[0.18em] text-[color:var(--soac-muted)]">HOW IT WORKS</p>
              <div className="mt-4 space-y-4 text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-4">
                  <p className="text-sm font-semibold">1) Ingest</p>
                  <p className="mt-1 text-sm text-[color:var(--soac-muted)]">Upload ONNX models and validate structure and compatibility.</p>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-4">
                  <p className="text-sm font-semibold">2) Optimize</p>
                  <p className="mt-1 text-sm text-[color:var(--soac-muted)]">Apply compiler-like passes guided by explicit policies.</p>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-4">
                  <p className="text-sm font-semibold">3) Export</p>
                  <p className="mt-1 text-sm text-[color:var(--soac-muted)]">Generate artifacts and reports that match your deployment targets.</p>
                </div>
              </div>
            </section>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            <section className="rounded-2xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-6">
              <p className="text-xs font-semibold tracking-[0.18em] text-[color:var(--soac-muted)]">SECURITY</p>
              <p className="mt-3 text-sm leading-relaxed text-[color:var(--soac-text)]">
                Authentication and authorization are designed to protect models, logs, and outputs in multi-user environments.
              </p>
            </section>
            <section className="rounded-2xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-6">
              <p className="text-xs font-semibold tracking-[0.18em] text-[color:var(--soac-muted)]">OBSERVABILITY</p>
              <p className="mt-3 text-sm leading-relaxed text-[color:var(--soac-text)]">
                Jobs produce structured logs and stage-aware progress so teams can diagnose and repeat results.
              </p>
            </section>
            <section className="rounded-2xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card)] p-6">
              <p className="text-xs font-semibold tracking-[0.18em] text-[color:var(--soac-muted)]">DEPLOYMENT</p>
              <p className="mt-3 text-sm leading-relaxed text-[color:var(--soac-text)]">
                Outputs are packaged to integrate with downstream systems and deployment pipelines.
              </p>
            </section>
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-4 text-sm">
            <Link className="btn-secondary" to="/">
              Back to Home
            </Link>
            <a className="btn-secondary" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              API Docs
            </a>
            <a className="btn-secondary" href="https://github.com/aatif-shaikh19/SOAC-v2" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </div>
        </div>
      </main>
    </div>
  );
};

