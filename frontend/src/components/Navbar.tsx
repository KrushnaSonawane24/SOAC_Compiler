/**
 * Navbar Component
 */

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export const Navbar: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <nav className="bg-gray-800 border-b border-gray-700">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link to="/" className="flex items-center">
                        <span className="text-2xl font-bold text-indigo-500">SOAC</span>
                    </Link>

                    {/* Navigation */}
                    <div className="flex items-center gap-4">
                        <Link
                            to="/"
                            className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                        >
                            Dashboard
                        </Link>
                        <Link
                            to="/new"
                            className="btn-primary text-sm"
                        >
                            New Job
                        </Link>

                        {/* User Menu */}
                        <div className="flex items-center gap-3 ml-4 pl-4 border-l border-gray-600">
                            <span className="text-gray-400 text-sm">{user?.email}</span>
                            <button
                                onClick={handleLogout}
                                className="text-gray-400 hover:text-white text-sm"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
};
