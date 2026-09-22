import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Eye, EyeOff, UserPlus } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';

const registerSchema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirm_password: z.string(),
  terms: z.boolean().refine((v) => v === true, 'You must accept the terms to continue'),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { login } = useAuthStore();

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
      await authApi.register({
        full_name: data.full_name.trim(),
        email: data.email.trim().toLowerCase(),
        password: data.password,
      });
      // Auto-login after successful registration
      await login({
        email: data.email.trim().toLowerCase(),
        password: data.password,
      });
      navigate('/dashboard');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setServerError(detail);
      } else if (Array.isArray(detail) && detail[0]?.msg) {
        setServerError(detail[0].msg);
      } else if (!err.response && err.message) {
        setServerError('Cannot connect to server. Please ensure the server is running.');
      } else {
        setServerError('Registration failed. Please try again.');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 w-full">
      {serverError && (
        <div className="p-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl animate-shake">
          {serverError}
        </div>
      )}

      <Input
        label="Full name"
        placeholder="Your full name"
        {...register('full_name')}
        error={errors.full_name?.message}
      />

      <Input
        label="Email address"
        placeholder="you@example.com"
        {...register('email')}
        error={errors.email?.message}
      />

      <Input
        label="Password"
        type={showPassword ? 'text' : 'password'}
        placeholder="Min 8 chars, 1 uppercase, 1 number"
        {...register('password')}
        error={errors.password?.message}
        rightIcon={
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-slate-400 hover:text-slate-700 transition-colors focus:outline-none"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        }
      />

      <Input
        label="Confirm password"
        type={showConfirm ? 'text' : 'password'}
        placeholder="Re-enter your password"
        {...register('confirm_password')}
        error={errors.confirm_password?.message}
        rightIcon={
          <button
            type="button"
            onClick={() => setShowConfirm(!showConfirm)}
            className="text-slate-400 hover:text-slate-700 transition-colors focus:outline-none"
          >
            {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        }
      />

      <div className="flex items-start gap-2.5 pt-1">
        <input
          type="checkbox"
          id="terms"
          {...register('terms')}
          className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500/20"
        />
        <label htmlFor="terms" className="text-xs text-slate-600 leading-relaxed cursor-pointer select-none">
          I agree to the{' '}
          <a href="#" className="text-blue-600 hover:underline">Terms of Service</a>
          {' '}and{' '}
          <a href="#" className="text-blue-600 hover:underline">Privacy Policy</a>
        </label>
      </div>
      {errors.terms && (
        <p className="text-xs text-rose-600">{errors.terms.message}</p>
      )}

      <Button type="submit" fullWidth loading={isSubmitting} leftIcon={<UserPlus size={16} />}>
        Create Account
      </Button>

      <p className="text-center text-xs text-slate-500 pt-2">
        Already have an account?{' '}
        <Link to="/login" className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
          Sign in
        </Link>
      </p>
    </form>
  );
}
