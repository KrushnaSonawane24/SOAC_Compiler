import React from 'react';
import { Link } from 'react-router-dom';
import { BrutalNav } from '../brutal/BrutalNav';
import { useAuth } from '../auth/AuthContext';

export const DocsPage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen">
      <BrutalNav variant="app" />

      <main className="brutal-scroll max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 pt-32">
        <header className="mb-10">
          <p className="text-xs tracking-[0.22em] text-[color:var(--soac-muted)]">DOCS</p>
          <h1 className="mt-3 text-4xl sm:text-5xl font-semibold soac-display text-[color:var(--soac-text)]">
            SOAC Documentation
          </h1>
          <p className="mt-4 text-base sm:text-lg text-[color:var(--soac-muted)] max-w-3xl">
            SOAC (Self-Optimizing AI Compiler) treats pretrained AI models like programs: it compiles them into optimized,
            secure, and deployable artifacts for real devices.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-primary magnetic">
                Open Dashboard
              </Link>
            ) : (
              <Link to="/login" className="btn-primary magnetic">
                Login to Start
              </Link>
            )}
            <a
              className="btn-secondary magnetic"
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
            >
              API Docs
            </a>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <aside className="lg:sticky lg:top-28 self-start">
            <div className="rounded-xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-4">
              <p className="text-xs tracking-[0.2em] text-[color:var(--soac-muted)]">ON THIS PAGE</p>
              <nav className="mt-3 flex flex-col gap-2 text-sm">
                <a className="nav-link magnetic" data-text="WHAT" href="#what-is-soac">
                  What is SOAC
                </a>
                <a className="nav-link magnetic" data-text="ARCH" href="#architecture">
                  Architecture
                </a>
                <a className="nav-link magnetic" data-text="PIPELINE" href="#pipeline">
                  Compiler Pipeline
                </a>
                <a className="nav-link magnetic" data-text="FORMATS" href="#formats">
                  Supported Formats
                </a>
                <a className="nav-link magnetic" data-text="OPTIM" href="#optimization">
                  Optimization and ALO
                </a>
                <a className="nav-link magnetic" data-text="ACCURACY" href="#accuracy">
                  Accuracy and Benchmarks
                </a>
                <a className="nav-link magnetic" data-text="SECURITY" href="#security">
                  Security and Privacy
                </a>
                <a className="nav-link magnetic" data-text="OUTPUTS" href="#outputs">
                  Deployment Outputs
                </a>
                <a className="nav-link magnetic" data-text="LIMITS" href="#limitations">
                  Limitations
                </a>
              </nav>
            </div>
          </aside>

          <section className="space-y-8">
            <article
              id="what-is-soac"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">What is SOAC?</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC compiles pretrained AI models into optimized, secure, and deployable artifacts, similar to how GCC/LLVM
                compile C/C++ programs or how Java is compiled into bytecode.
              </p>

              <div className="mt-5 grid gap-4 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">WHAT SOAC IS NOT</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>Not a training framework</li>
                    <li>Not AutoML</li>
                    <li>Not a simple model converter</li>
                    <li>Not a benchmark script</li>
                  </ul>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">WHAT SOAC IS</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>A compiler</li>
                    <li>Deterministic and reproducible</li>
                    <li>Constraint-based (accuracy enforced)</li>
                    <li>Explainable (every decision logged)</li>
                    <li>Secure by design</li>
                    <li>Produces real deployment demos</li>
                  </ul>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">ONE-LINE DEFINITION</p>
                <p className="mt-2 text-[color:var(--soac-text)]">
                  SOAC is a deterministic, constraint-based AI compiler that converts pretrained models into optimized, deployable artifacts with
                  accuracy guarantees.
                </p>
              </div>
            </article>

            <article
              id="architecture"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">SOAC Architecture</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC uses a layered compiler architecture: frontend formats are lowered into a dedicated IR, optimized by compiler passes,
                evaluated by cost models and constraints, then lowered into deployable outputs.
              </p>

              <pre className="mt-4 whitespace-pre-wrap rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm text-[color:var(--soac-text)]">
                {`Frontend Formats (ONNX / H5 / PyTorch)
        ↓
ONNX Frontend
        ↓
SOAC IR (Intermediate Representation)
        ↓
Compiler Passes
        ↓
Cost Models + Constraints
        ↓
Policy-Driven Selection
        ↓
Backend Lowering
        ↓
Deployment Artifacts (TFLite / TensorRT / ONNX Runtime)`}
              </pre>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">KEY LAYERS</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>Frontend layer: accepts pretrained inference models only</li>
                    <li>Compiler core: SOAC IR (all logic operates on IR, not ONNX)</li>
                    <li>Decision layer: variants, cost models, constraints, policies</li>
                    <li>Backend layer: emits deployable artifacts and demos</li>
                  </ul>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">WHY THE IR MATTERS</p>
                  <p className="mt-2 text-[color:var(--soac-muted)]">
                    ONNX is treated as a frontend format. The defining feature is lowering into SOAC IR and running compiler passes on IR
                    to guarantee determinism, traceability, and verifiable outputs.
                  </p>
                </div>
              </div>
            </article>

            <article
              id="pipeline"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Compiler Pipeline</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC runs explicit passes in a deterministic pipeline. Each pass has a single responsibility and produces traceable output.
              </p>

              <ol className="mt-4 space-y-3 text-[color:var(--soac-text)]">
                <li className="flex gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-card-border)] text-xs">
                    1
                  </span>
                  <div>
                    <p className="font-medium">Input validation</p>
                    <p className="text-sm text-[color:var(--soac-muted)]">
                      Extension allowlist, MIME + magic bytes, size limits, hashing, and training-graph rejection.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-card-border)] text-xs">
                    2
                  </span>
                  <div>
                    <p className="font-medium">Frontend conversion</p>
                    <p className="text-sm text-[color:var(--soac-muted)]">
                      TensorFlow and PyTorch are frontend languages; all inputs are converted into ONNX.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-card-border)] text-xs">
                    3
                  </span>
                  <div>
                    <p className="font-medium">Lowering to SOAC IR</p>
                    <p className="text-sm text-[color:var(--soac-muted)]">
                      ONNX graphs are lowered to IRTensor, IROperator, and IRGraph. IR is deterministic and hashable.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-card-border)] text-xs">
                    4
                  </span>
                  <div>
                    <p className="font-medium">Compiler passes and selection</p>
                    <p className="text-sm text-[color:var(--soac-muted)]">
                      Validate, canonicalize, infer shapes/memory, generate variants, benchmark, select via policy + constraints.
                    </p>
                  </div>
                </li>
                <li className="flex gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--soac-card-hover)] border border-[color:var(--soac-card-border)] text-xs">
                    5
                  </span>
                  <div>
                    <p className="font-medium">Backend lowering</p>
                    <p className="text-sm text-[color:var(--soac-muted)]">
                      Selected variant is lowered into deployable targets such as TFLite, TensorRT (if GPU available), and ONNX Runtime.
                    </p>
                  </div>
                </li>
              </ol>
            </article>

            <article
              id="formats"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Supported Model Formats</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">SOAC supports pretrained inference models only.</p>

              <ul className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <li className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">ONNX</p>
                  <p className="mt-1 text-[color:var(--soac-muted)]">.onnx (preferred)</p>
                </li>
                <li className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">TENSORFLOW / KERAS</p>
                  <p className="mt-1 text-[color:var(--soac-muted)]">.h5 (full saved model)</p>
                </li>
                <li className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">PYTORCH</p>
                  <p className="mt-1 text-[color:var(--soac-muted)]">.pt / .pth (full model only)</p>
                </li>
                <li className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">IMPORTANT</p>
                  <p className="mt-1 text-[color:var(--soac-muted)]">Training graphs are rejected (optimizers, loss, random ops).</p>
                </li>
              </ul>

              <div className="mt-4 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">COMMON UPLOAD MISTAKE</p>
                <p className="mt-2 text-[color:var(--soac-muted)]">This fails (weights only):</p>
                <pre className="mt-2 whitespace-pre-wrap text-[color:var(--soac-text)]">{`model.save_weights("model.h5")`}</pre>
                <p className="mt-3 text-[color:var(--soac-muted)]">Correct (full model):</p>
                <pre className="mt-2 whitespace-pre-wrap text-[color:var(--soac-text)]">{`model.save("model.h5")`}</pre>
              </div>
            </article>

            <article
              id="optimization"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Optimization and ALO</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC generates multiple optimized variants and selects the best one using compiler logic.
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">TECHNIQUES</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>FP16 quantization</li>
                    <li>INT8 quantization</li>
                    <li>Structured pruning</li>
                    <li>Baseline (no optimization)</li>
                  </ul>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">ALO</p>
                  <p className="mt-2 text-[color:var(--soac-muted)]">
                    ALO is not ML-based. It is a decision engine that generates variants, benchmarks them, estimates cost, checks constraints,
                    and selects the best valid variant using policies.
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">POLICIES</p>
                <p className="mt-2 text-[color:var(--soac-muted)]">
                  Latency-first (default), Accuracy-first, and Mobile-first. Policies never bypass constraints.
                </p>
              </div>
            </article>

            <article
              id="accuracy"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Accuracy and Benchmarks</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                In SOAC, accuracy is treated as a correctness constraint.
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">ACCURACY RULE</p>
                  <p className="mt-2 text-[color:var(--soac-muted)]">Accuracy drop must be &lt;= 2%. Violations are rejected.</p>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">METRICS</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>Top-1 accuracy</li>
                    <li>Latency (ms)</li>
                    <li>Model size (MB)</li>
                    <li>Memory usage</li>
                  </ul>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">REPORTS</p>
                <p className="mt-2 text-[color:var(--soac-muted)]">JSON, CSV, PDF, charts, and an explainability report.</p>
              </div>
            </article>

            <article
              id="security"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Security and Privacy</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC is designed as if it will be audited. Security and privacy are part of the compilation workflow.
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">UPLOAD SECURITY</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>Extension allowlist</li>
                    <li>MIME + magic byte validation</li>
                    <li>SHA-256 hashing</li>
                    <li>Size limits</li>
                    <li>Path traversal protection</li>
                  </ul>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">EXECUTION AND PRIVACY</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>Docker sandbox</li>
                    <li>No internet access during compilation</li>
                    <li>Temporary directories + auto cleanup</li>
                    <li>No telemetry</li>
                    <li>Per-user isolation</li>
                  </ul>
                </div>
              </div>
            </article>

            <article
              id="outputs"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Deployment and Demo Outputs</h2>
              <p className="mt-3 text-[color:var(--soac-muted)]">
                SOAC produces real deployment demos. Every demo has an explicit status so there are no silent failures.
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">GUARANTEED DEMO</p>
                  <p className="mt-2 text-[color:var(--soac-muted)]">Android TFLite demo (Android Studio project, runnable app, model bundled).</p>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">CONDITIONAL DEMO</p>
                  <p className="mt-2 text-[color:var(--soac-muted)]">TensorRT PC demo if GPU is available, otherwise a stub + setup guide.</p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">DEMO STATUS</p>
                <p className="mt-2 text-[color:var(--soac-muted)]">AVAILABLE, UNAVAILABLE (with reason), GENERATED, FAILED.</p>
              </div>
            </article>

            <article
              id="limitations"
              className="rounded-2xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-6"
            >
              <h2 className="text-2xl font-semibold soac-display text-[color:var(--soac-text)]">Limitations and Future Work</h2>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-[color:var(--soac-text)]">
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">LIMITATIONS</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>No training support</li>
                    <li>Limited model architectures</li>
                    <li>TensorRT depends on GPU availability</li>
                    <li>Analytical cost models are estimations</li>
                  </ul>
                </div>
                <div className="rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4">
                  <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">FUTURE WORK</p>
                  <ul className="mt-2 space-y-1 text-[color:var(--soac-muted)]">
                    <li>More backends (OpenVINO, WebGPU)</li>
                    <li>Better analytical models</li>
                    <li>IR visualization</li>
                    <li>Distributed compilation</li>
                  </ul>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[color:var(--soac-card-border)] bg-[color:var(--soac-card-hover)] p-4 text-sm">
                <p className="text-xs tracking-[0.18em] text-[color:var(--soac-muted)]">WHY SOAC MATTERS</p>
                <p className="mt-2 text-[color:var(--soac-text)]">
                  SOAC makes AI deployment behave like compilation: deterministic, traceable, and repeatable.
                  It replaces guesswork with explicit passes, constraints, and verifiable outputs.
                  That is the difference between “it runs” and “it ships safely.”
                </p>
              </div>
            </article>

            <footer className="py-6 text-sm text-[color:var(--soac-muted)]">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p>SOAC © 2026</p>
                <div className="flex flex-wrap gap-4">
                  <Link className="underline decoration-[color:var(--soac-border)] hover:text-[color:var(--soac-text)]" to="/">
                    Home
                  </Link>
                  <a
                    className="underline decoration-[color:var(--soac-border)] hover:text-[color:var(--soac-text)]"
                    href="http://127.0.0.1:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                  >
                    API Docs
                  </a>
                </div>
              </div>
            </footer>
          </section>
        </div>
      </main>
    </div>
  );
};
