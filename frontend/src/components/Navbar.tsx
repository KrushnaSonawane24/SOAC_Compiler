/**
 * Navbar Component
 */

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useTheme } from '../theme/ThemeContext';

export const Navbar: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const { theme, toggleTheme } = useTheme();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <nav className="sticky top-0 z-50 backdrop-blur-md border-b transition-all duration-300 bg-[color:var(--soac-nav-bg)] border-[color:var(--soac-border)]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform bg-[color:var(--soac-primary)] shadow-[color:var(--soac-glow)]/30">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span className="text-xl font-semibold tracking-tight">
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-[color:var(--soac-primary)] to-[color:var(--soac-secondary)]">
                                SOAC
                            </span>
                            <span className="text-[color:var(--soac-muted)] font-normal ml-2 text-base">AI Lab</span>
                        </span>
                    </Link>

                    {/* Navigation */}
                    <div className="flex items-center gap-4">
                        <Link
                            to="/"
                            className="px-3 py-2 rounded-md text-sm font-medium transition-colors text-[color:var(--soac-muted)] hover:text-[color:var(--soac-text)]"
                        >
                            Dashboard
                        </Link>
                        <Link
                            to="/new"
                            className="btn-primary text-sm"
                        >
                            + New Job
                        </Link>

                        {/* User Menu */}
                        <div className="flex items-center gap-3 ml-4 pl-4 border-l border-[color:var(--soac-border)]">
                            <button
                                type="button"
                                onClick={toggleTheme}
                                className="p-2 rounded-lg transition-colors hover:bg-[color:var(--soac-card-hover)] text-[color:var(--soac-muted)] hover:text-[color:var(--soac-text)]"
                                title={theme === 'night' ? 'Switch to day mode' : 'Switch to night mode'}
                            >
                                {theme === 'night' ? (
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.364-6.364l-1.414 1.414M7.05 16.95l-1.414 1.414m12.728 0l-1.414-1.414M7.05 7.05 5.636 5.636M12 8a4 4 0 100 8 4 4 0 000-8z" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
                                    </svg>
                                )}
                            </button>
                            <div className="flex flex-col items-end">
                                <span className="text-sm font-medium text-[color:var(--soac-text)]">{user?.email?.split('@')[0]}</span>
                                <span className="text-xs text-[color:var(--soac-muted)]">{user?.email}</span>
                            </div>
                            <button
                                onClick={handleLogout}
                                className="p-2 rounded-lg transition-colors text-[color:var(--soac-muted)] hover:text-[color:var(--soac-text)] hover:bg-[color:var(--soac-card-hover)]"
                                title="Logout"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
};
