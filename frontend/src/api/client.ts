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
            // Token expired - clear and redirect
            setAccessToken(null);
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;
