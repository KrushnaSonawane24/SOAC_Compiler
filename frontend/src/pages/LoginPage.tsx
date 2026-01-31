/**
 * Login Page
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { authApi } from '../api/auth';

export const LoginPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [rememberEmail, setRememberEmail] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();
    const shellRef = useRef<HTMLDivElement | null>(null);
    const rippleTimerRef = useRef<number | null>(null);

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
            navigate('/');
        } catch {
            setError('Invalid email or password');
        } finally {
            setIsLoading(false);
        }
    };

    const handleMouseMove: React.MouseEventHandler<HTMLDivElement> = (e) => {
        const el = shellRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        el.style.setProperty('--soac-cursor-x', `${x}%`);
        el.style.setProperty('--soac-cursor-y', `${y}%`);
    };

    const handleButtonPointerDown: React.PointerEventHandler<HTMLButtonElement> = (e) => {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        button.style.setProperty('--soac-ripple-x', `${x}%`);
        button.style.setProperty('--soac-ripple-y', `${y}%`);
        button.classList.add('soac-btn--ripple');
        if (rippleTimerRef.current) window.clearTimeout(rippleTimerRef.current);
        rippleTimerRef.current = window.setTimeout(() => {
            button.classList.remove('soac-btn--ripple');
        }, 560);
    };

    return (
        <div ref={shellRef} onMouseMove={handleMouseMove} className="min-h-screen soac-login-shell flex items-center justify-center px-4">
            <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 items-stretch">
                <div className="card flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg bg-[color:var(--soac-primary)] shadow-[color:var(--soac-glow)]/35">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <div>
                                <div className="soac-display text-2xl font-semibold">
                                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-[color:var(--soac-primary)] to-[color:var(--soac-secondary)]">
                                        SOAC
                                    </span>
                                    <span className="text-[color:var(--soac-muted)] font-normal ml-2">AI Lab</span>
                                </div>
                                <div className="text-sm text-[color:var(--soac-muted)]">sign in to continue</div>
                            </div>
                        </div>

                        <div className="mt-6">
                            <h1 className="soac-display text-3xl font-semibold text-[color:var(--soac-text)]">Welcome back</h1>
                            <p className="mt-2 text-sm text-[color:var(--soac-muted)]">your token is stored locally after sign in</p>
                        </div>

                        {error && (
                            <div className="mt-6 px-4 py-3 rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] text-[color:var(--soac-text)]">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-[color:var(--soac-muted)] mb-1">Email</label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="input w-full"
                                    placeholder="you@example.com"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-[color:var(--soac-muted)] mb-1">Password</label>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input w-full"
                                    placeholder="••••••••"
                                    required
                                />
                            </div>

                            <div className="flex items-center justify-between pt-1">
                                <label className="flex items-center gap-2 text-sm text-[color:var(--soac-muted)] select-none">
                                    <input
                                        type="checkbox"
                                        className="soac-check"
                                        checked={rememberEmail}
                                        onChange={(e) => setRememberEmail(e.target.checked)}
                                    />
                                    remember email
                                </label>
                                <Link to="/register" className="text-sm text-[color:var(--soac-secondary)] hover:underline">
                                    create account
                                </Link>
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                onPointerDown={handleButtonPointerDown}
                                className="btn-primary soac-btn w-full disabled:opacity-50"
                            >
                                {isLoading ? 'Signing in…' : 'Sign in'}
                            </button>
                        </form>

                        <div className="my-6 flex items-center gap-3">
                            <div className="soac-divider flex-1" />
                            <div className="text-xs text-[color:var(--soac-muted)]">or</div>
                            <div className="soac-divider flex-1" />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <a href={authApi.getGitHubLoginUrl()} className="btn-secondary flex items-center justify-center gap-2">
                                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                                </svg>
                                GitHub
                            </a>
                            <a href={authApi.getGoogleLoginUrl()} className="btn-secondary flex items-center justify-center gap-2">
                                <svg className="w-5 h-5" viewBox="0 0 24 24">
                                    <path fill="#EA4335" d="M5.26620003,9.76452941 C6.19878754,6.93863203 8.85444915,4.90909091 12,4.90909091 C13.6909091,4.90909091 15.2181818,5.50909091 16.4181818,6.49090909 L19.9090909,3 C17.7818182,1.14545455 15.0545455,0 12,0 C7.27006974,0 3.1977497,2.69829785 1.23999023,6.65002441 L5.26620003,9.76452941 Z" />
                                    <path fill="#34A853" d="M16.0407269,18.0125889 C14.9509167,18.7163016 13.5660892,19.0909091 12,19.0909091 C8.86648613,19.0909091 6.21911939,17.076871 5.27698177,14.2678769 L1.23746264,17.3349879 C3.19279051,21.2936293 7.26500293,24 12,24 C14.9328362,24 17.7353462,22.9573905 19.834192,20.9995801 L16.0407269,18.0125889 Z" />
                                    <path fill="#4A90E2" d="M19.834192,20.9995801 C22.0291676,18.9520994 23.4545455,15.903663 23.4545455,12 C23.4545455,11.2909091 23.3454545,10.5272727 23.1818182,9.81818182 L12,9.81818182 L12,14.4545455 L18.4363636,14.4545455 C18.1187732,16.013626 17.2662994,17.2212117 16.0407269,18.0125889 L19.834192,20.9995801 Z" />
                                    <path fill="#FBBC05" d="M5.27698177,14.2678769 C5.03832634,13.556323 4.90909091,12.7937589 4.90909091,12 C4.90909091,11.2182781 5.03443647,10.4668121 5.26620003,9.76452941 L1.23999023,6.65002441 C0.43658717,8.26043162 0,10.0753848 0,12 C0,13.9195484 0.444780743,15.7 L1.23746264,17.3349879 L5.27698177,14.2678769 Z" />
                                </svg>
                                Google
                            </a>
                        </div>
                    </div>

                    <div className="mt-6 text-xs text-[color:var(--soac-muted)]">
                        by signing in, you agree to run jobs responsibly and review logs for failures.
                    </div>
                </div>

                <div className="card soac-login-hero hidden lg:flex flex-col justify-between">
                    <div>
                        <div className="soac-display text-2xl font-semibold text-[color:var(--soac-text)]">pipeline overview</div>
                        <p className="mt-2 text-sm text-[color:var(--soac-muted)]">
                            validating → canonicalizing → optimizing → benchmarking → selecting → deploying
                        </p>
                        <div className="mt-6 rounded-xl border border-[color:var(--soac-border)] bg-[color:var(--soac-card)] p-5">
                            <svg className="soac-login-lines w-full" height="140" viewBox="0 0 520 140" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M40 70C90 20 140 20 190 70C240 120 290 120 340 70C390 20 440 20 480 70" stroke="rgba(255,255,255,0.55)" strokeWidth="2" />
                                <path d="M40 70H480" stroke="rgba(255,255,255,0.22)" strokeWidth="2" />
                                <path d="M40 70C120 70 160 100 220 100C280 100 320 70 400 70" stroke="rgba(255,255,255,0.28)" strokeWidth="2" />
                            </svg>
                            <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-[color:var(--soac-muted)]">
                                <div className="rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] px-3 py-2">stable logs</div>
                                <div className="rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] px-3 py-2">reproducible runs</div>
                                <div className="rounded-lg border border-[color:var(--soac-border)] bg-[color:var(--soac-card-hover)] px-3 py-2">artifacts</div>
                            </div>
                        </div>
                    </div>

                    <div className="text-sm text-[color:var(--soac-muted)]">
                        small delays and calm transitions are intentional.
                    </div>
                </div>
            </div>
        </div>
    );
};
