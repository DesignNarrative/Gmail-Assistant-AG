import React, { useState } from 'react';
import LoginForm from '../components/auth/LoginForm';
import RegisterForm from '../components/auth/RegisterForm';
import ForgotPasswordForm from '../components/auth/ForgotPasswordForm';
import { Search, Bot, ShieldCheck } from 'lucide-react';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot'>('login');
  const isLogin = mode === 'login';

  return (
    <div className="min-h-screen w-full flex bg-dark-bg animated-bg">
      {/* Left Panel */}
      <div className="hidden lg:flex flex-col justify-center w-[60%] p-16 relative overflow-hidden">
        {/* Floating shapes background */}
        <div className="absolute top-20 left-20 w-64 h-64 bg-primary-blue/20 rounded-full blur-3xl animate-pulse-glow" />
        <div className="absolute bottom-20 right-20 w-80 h-80 bg-secondary-blue/10 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: '1s' }} />
        
        <div className="relative z-10 max-w-2xl animate-fade-in">
          <div className="relative inline-block mb-12">
            <div className="absolute inset-0 bg-white/5 blur-xl rounded-full" />
            <img src="/AbhinavGrouplogo.png" alt="Abhinav Group" className="h-16 relative z-10 drop-shadow-lg" />
          </div>
          
          <h1 className="text-5xl font-bold tracking-tight text-white mb-6 leading-tight">
            Transform your inbox into <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-gold-accent to-gold-light">
              corporate intelligence
            </span>
          </h1>
          
          <div className="space-y-8 mt-12">
            <FeatureItem 
              icon={<Search className="w-6 h-6 text-secondary-blue" />}
              title="Ask anything, find everything"
              delay="0.2s"
            />
            <FeatureItem 
              icon={<Bot className="w-6 h-6 text-gold-accent" />}
              title="AI-powered with evidence-backed answers"
              delay="0.4s"
            />
            <FeatureItem 
              icon={<ShieldCheck className="w-6 h-6 text-status-success" />}
              title="Enterprise-grade security"
              delay="0.6s"
            />
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-full lg:w-[40%] flex items-center justify-center p-8 z-10">
        <div className="w-full max-w-md glass-card p-8 rounded-2xl animate-slide-up">
          <div className="lg:hidden mb-8 flex justify-center">
            <img src="/AbhinavGrouplogo.png" alt="Abhinav Group" className="h-12" />
          </div>
          
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">
              {isLogin ? 'Welcome back' : mode === 'register' ? 'Create your account' : 'Reset your password'}
            </h2>
            <p className="text-text-secondary text-sm">
              {isLogin
                ? 'Sign in to AI Intelligence Assistant'
                : mode === 'register'
                ? 'Join AI Intelligence Assistant'
                : 'Enter your email and choose a new password'}
            </p>
          </div>
          
          {isLogin ? (
            <LoginForm onForgotPassword={() => setMode('forgot')} />
          ) : mode === 'register' ? (
            <RegisterForm />
          ) : (
            <ForgotPasswordForm onDone={() => setMode('login')} />
          )}

          <div className="mt-6 text-center text-sm">
            {isLogin ? (
              <span className="text-text-secondary">
                Don't have an account?{' '}
                <button type="button" onClick={() => setMode('register')} className="text-primary-blue hover:text-secondary-blue transition-colors font-medium">
                  Sign up
                </button>
              </span>
            ) : (
              <span className="text-text-secondary">
                {mode === 'register' ? 'Already have an account?' : 'Remembered your password?'}{' '}
                <button type="button" onClick={() => setMode('login')} className="text-primary-blue hover:text-secondary-blue transition-colors font-medium">
                  Sign in
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title, delay }: { icon: React.ReactNode, title: string, delay: string }) {
  return (
    <div className="flex items-center gap-4 animate-slide-up" style={{ animationDelay: delay, animationFillMode: 'both' }}>
      <div className="w-12 h-12 rounded-lg bg-dark-card border border-dark-border flex items-center justify-center shadow-lg">
        {icon}
      </div>
      <span className="text-lg text-text-primary font-medium">{title}</span>
    </div>
  );
}
