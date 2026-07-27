import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useAuthStore } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginForm({ onForgotPassword }: { onForgotPassword?: () => void }) {
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

      <div className="flex items-center justify-end text-sm">
        <button
          type="button"
          onClick={onForgotPassword}
          className="text-primary-blue hover:text-secondary-blue transition-colors"
        >
          Forgot password?
        </button>
      </div>

      <Button type="submit" fullWidth loading={isSubmitting}>
        Sign In
      </Button>
    </form>
  );
}
