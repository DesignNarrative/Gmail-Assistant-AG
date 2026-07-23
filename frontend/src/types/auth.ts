export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'director';
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  is_gmail_connected: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  full_name: string;
  password: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
