import { create } from 'zustand';
import { AuthState, LoginCredentials, User } from '../types/auth';
import { authApi } from '../api/auth';

interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  initializeAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,
  
  login: async (credentials) => {
    set({ isLoading: true });
    try {
      const tokens = await authApi.login(credentials);
      localStorage.setItem('abhinav_ai_token', tokens.access_token);
      localStorage.setItem('abhinav_ai_refresh', tokens.refresh_token);
      
      const user = await authApi.getMe();
      set({ user, accessToken: tokens.access_token, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },
  
  logout: () => {
    localStorage.removeItem('abhinav_ai_token');
    localStorage.removeItem('abhinav_ai_refresh');
    set({ user: null, accessToken: null, isAuthenticated: false });
  },
  
  initializeAuth: async () => {
    const token = localStorage.getItem('abhinav_ai_token');
    if (token) {
      try {
        const user = await authApi.getMe();
        set({ user, accessToken: token, isAuthenticated: true, isLoading: false });
      } catch (e) {
        localStorage.removeItem('abhinav_ai_token');
        localStorage.removeItem('abhinav_ai_refresh');
        set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
      }
    } else {
      set({ isLoading: false });
    }
  },
  
  setUser: (user) => set({ user })
}));
