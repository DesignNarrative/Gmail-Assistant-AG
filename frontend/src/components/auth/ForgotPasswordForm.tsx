import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { authApi } from '../../api/auth';

const forgotSchema = z
  .object({
    email: z.string().email('Please enter a valid email address'),
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type ForgotFormValues = z.infer<typeof forgotSchema>;

export default function ForgotPasswordForm({ onDone }: { onDone: () => void }) {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
  });

  const onSubmit = async (data: ForgotFormValues) => {
    try {
      setServerError(null);
      await authApi.forgotPassword(data.email.trim().toLowerCase(), data.newPassword);
      setSuccess(true);
      // Send the user back to the sign-in form after a short confirmation
      setTimeout(onDone, 2000);
    } catch (err: any) {
      setServerError(err.response?.data?.detail || 'Password reset failed. Please try again.');
    }
  };

  if (success) {
    return (
      <div className="p-4 text-sm text-status-success bg-status-success/10 border border-status-success/20 rounded-md flex items-center gap-2">
        <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
        Password reset successfully. Taking you back to sign in...
      </div>
    );
  }

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
        label="New password"
        type={showPassword ? 'text' : 'password'}
        placeholder="••••••••"
        {...register('newPassword')}
        error={errors.newPassword?.message}
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
        label="Confirm new password"
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
        Reset Password
      </Button>
    </form>
  );
}
