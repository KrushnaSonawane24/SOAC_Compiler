/**
 * Auth Context
 * 
 * Manages authentication state.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, type User, type LoginRequest, type RegisterRequest } from '../api/auth';
import { setAccessToken, getAccessToken } from '../api/client';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (data: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => void;
    error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchUser = useCallback(async () => {
        const token = getAccessToken();
        if (!token) {
            setIsLoading(false);
            return;
        }

        try {
            const userData = await authApi.getMe();
            setUser(userData);
        } catch {
            setAccessToken(null);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        // Check for token in URL (OAuth callback)
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            setAccessToken(token);
            window.history.replaceState({}, '', window.location.pathname);
        }

        fetchUser();
    }, [fetchUser]);

    const login = async (data: LoginRequest) => {
        setError(null);
        try {
            const response = await authApi.login(data);
            setAccessToken(response.access_token);
            await fetchUser();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Login failed';
            setError(message);
            throw err;
        }
    };

    const register = async (data: RegisterRequest) => {
        setError(null);
        try {
            const response = await authApi.register(data);
            setAccessToken(response.access_token);
            await fetchUser();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Registration failed';
            setError(message);
            throw err;
        }
    };

    const logout = () => {
        setAccessToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                register,
                logout,
                error,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};
