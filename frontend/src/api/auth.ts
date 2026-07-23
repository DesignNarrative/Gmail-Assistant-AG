import client from './client';
import { LoginCredentials, TokenResponse, User } from '../types/auth';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await client.post<TokenResponse>('/api/v1/auth/login', credentials);
    return response.data;
  },
  
  getMe: async (): Promise<User> => {
    const response = await client.get<User>('/api/v1/auth/me');
    return response.data;
  },

  getGoogleOAuthUrl: async (): Promise<{ url: string }> => {
    const response = await client.get<{ url: string }>('/api/v1/oauth/google');
    return response.data;
  }
};
