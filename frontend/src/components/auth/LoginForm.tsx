import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useAuthStore } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';

import { authApi } from '../../api/auth';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormValues) => {
    try {
      setServerError(null);
      await login({
        email: data.email.trim().toLowerCase(),
        password: data.password.trim(),
      });
      navigate('/dashboard');
    } catch (err: any) {
      setServerError(err.response?.data?.detail || 'Invalid email or password');
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      setServerError(null);
      const res = await authApi.getGoogleOAuthUrl();
      if (res.url) {
        window.location.href = res.url;
      }
    } catch (err: any) {
      setServerError(err.response?.data?.detail || 'Failed to initialize Google login.');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 w-full">
      {serverError && (
        <div className="p-3 text-sm text-status-error bg-status-error/10 border border-status-error/20 rounded-md animate-shake">
          {serverError}
        </div>
      )}

      <Input
        label="Email address"
        placeholder="director@abhinavgroup.com"
        {...register('email')}
        error={errors.email?.message}
      />

      <Input
        label="Password"
        type={showPassword ? 'text' : 'password'}
        placeholder="••••••••"
        {...register('password')}
        error={errors.password?.message}
        rightIcon={
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="hover:text-text-primary transition-colors focus:outline-none"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        }
      />

      <div className="flex items-center justify-between text-sm">
        <label className="flex items-center gap-2 cursor-pointer group">
          <input type="checkbox" className="rounded border-dark-border bg-dark-bg text-primary-blue focus:ring-primary-blue/50" />
          <span className="text-text-secondary group-hover:text-text-primary transition-colors">Remember me</span>
        </label>
        <a href="#" className="text-primary-blue hover:text-secondary-blue transition-colors">
          Forgot password?
        </a>
      </div>

      <Button type="submit" fullWidth loading={isSubmitting}>
        Sign In
      </Button>

      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-dark-border"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-dark-card text-text-secondary">or</span>
        </div>
      </div>

      <Button
        type="button"
        variant="secondary"
        fullWidth
        leftIcon={
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
        }
        onClick={handleGoogleSignIn}
      >
        Continue with Google
      </Button>
    </form>
  );
}
