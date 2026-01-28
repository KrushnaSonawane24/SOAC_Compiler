/**
 * Register Page
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useAuth } from '../auth/AuthContext';

export const RegisterPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setIsLoading(true);

        try {
            await register({ email, password });
            navigate('/');
        } catch (err: unknown) {
            if (err instanceof AxiosError && err.response) {
                const data = err.response.data;
                // Handle 409 Conflict (User exists)
                if (err.response.status === 409 && data.detail?.error) {
                    setError(data.detail.error);
                    return;
                }
                // Handle 422 Validation Error
                if (err.response.status === 422) {
                    if (Array.isArray(data.detail)) {
                        const firstError = data.detail[0];
                        setError(`Validation Error: ${firstError.msg} (${firstError.loc.join('.')})`);
                    } else {
                        setError('Validation failed. Please check your input.');
                    }
                    return;
                }
                // Handle other API errors
                if (data.detail) {
                    setError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
                    return;
                }
            }
            setError('Registration failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
            <div className="max-w-md w-full space-y-8">
                <div className="text-center">
                    <h1 className="text-4xl font-bold text-white">
                        <span className="text-indigo-500">SOAC</span>
                    </h1>
                    <p className="mt-2 text-gray-400">Create your account</p>
                </div>

                <div className="card">
                    <h2 className="text-2xl font-semibold text-white mb-6">Sign up</h2>

                    {error && (
                        <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Email
                            </label>
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
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="input w-full"
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Confirm Password
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="input w-full"
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="btn-primary w-full disabled:opacity-50"
                        >
                            {isLoading ? 'Creating account...' : 'Create account'}
                        </button>
                    </form>

                    <p className="mt-6 text-center text-gray-400">
                        Already have an account?{' '}
                        <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};
