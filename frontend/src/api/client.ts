/**
 * SOAC API Client
 * 
 * Axios instance with JWT interceptor.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

// Token storage (localStorage + in-memory)
let accessToken: string | null = localStorage.getItem('soac_token');

export const setAccessToken = (token: string | null) => {
    accessToken = token;
    if (token) {
        localStorage.setItem('soac_token', token);
    } else {
        localStorage.removeItem('soac_token');
    }
};

export const getAccessToken = () => accessToken;

// Create axios instance
const api = axios.create({
    baseURL: '',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor - add JWT
api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        if (accessToken) {
            config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            const hadToken = Boolean(accessToken);
            const pathname = window.location.pathname;
            const isPublicRoute = pathname === '/' || pathname.startsWith('/login') || pathname.startsWith('/register');
            const url = typeof error.config?.url === 'string' ? error.config.url : '';
            const isAuthRoute = url.startsWith('/api/auth/') || url.startsWith('/auth/');

            const data = error.response?.data as unknown;
            const detail =
                typeof data === 'object' && data !== null && 'detail' in data
                    ? (data as { detail?: unknown }).detail
                    : undefined;
            const errorCode =
                typeof detail === 'object' && detail !== null && 'error_code' in detail
                    ? (detail as { error_code?: unknown }).error_code
                    : undefined;
            const isMissingToken = errorCode === 'MISSING_TOKEN';

            if (hadToken) {
                setAccessToken(null);
                if (!isPublicRoute) window.location.href = '/login';
            } else if (!isAuthRoute && !isPublicRoute && !isMissingToken) {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;
