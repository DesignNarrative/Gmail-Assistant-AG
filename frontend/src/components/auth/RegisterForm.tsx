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

const registerSchema = z
  .object({
    full_name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterForm() {
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormValues) => {
    try {
      setServerError(null);
      // Create the account. /auth/register returns the user (no tokens), so we
      // immediately sign in to obtain tokens and land the director in the app.
      await authApi.register({
        email: data.email.trim().toLowerCase(),
        full_name: data.full_name.trim(),
        password: data.password,
      });
      await login({
        email: data.email.trim().toLowerCase(),
        password: data.password,
      });
      navigate('/dashboard');
    } catch (err: any) {
      setServerError(err.response?.data?.detail || 'Registration failed. Please try again.');
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
        label="Full name"
        placeholder="Mayur Bangera"
        {...register('full_name')}
        error={errors.full_name?.message}
      />

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

      <Input
        label="Confirm password"
        type={showPassword ? 'text' : 'password'}
        placeholder="••••••••"
        {...register('confirmPassword')}
        error={errors.confirmPassword?.message}
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

      <Button type="submit" fullWidth loading={isSubmitting}>
        Create Account
      </Button>
    </form>
  );
}
