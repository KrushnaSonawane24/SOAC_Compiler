/**
 * Auth API
 */

import api from './client';

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user_id: string;
    email: string;
}

export interface User {
    user_id: string;
    email: string;
    provider: string;
}

export const authApi = {
    login: async (data: LoginRequest): Promise<AuthResponse> => {
        const response = await api.post<AuthResponse>('/auth/login', data);
        return response.data;
    },

    register: async (data: RegisterRequest): Promise<AuthResponse> => {
        const response = await api.post<AuthResponse>('/auth/register', data);
        return response.data;
    },

    getMe: async (): Promise<User> => {
        const response = await api.get<User>('/auth/me');
        return response.data;
    },

    getGitHubLoginUrl: () => '/auth/github/login',
    getGoogleLoginUrl: () => '/auth/google/login',
};
