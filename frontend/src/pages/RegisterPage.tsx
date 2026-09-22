import React from 'react';
import { Link } from 'react-router-dom';
import RegisterForm from '../components/auth/RegisterForm';
import { Search, Bot, ShieldCheck } from 'lucide-react';

export default function RegisterPage() {
  return (
    <div className="min-h-screen w-full flex bg-slate-50 animated-bg">
      {/* Left Panel */}
      <div className="hidden lg:flex flex-col justify-center w-[55%] p-16 relative overflow-hidden bg-gradient-to-br from-blue-900 via-indigo-900 to-slate-900 text-white">
        {/* Subtle glow accents */}
        <div className="absolute top-10 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-xl">
          <div className="flex items-center gap-2.5 mb-10">
            <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center text-white text-xl font-bold shadow-md shadow-blue-500/30">
              ✉
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">InboxIQ</span>
          </div>
          
          <h1 className="text-4xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Your inbox, your personal <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-amber-200 to-yellow-100">
              knowledge base
            </span>
          </h1>
          <p className="text-slate-300 text-base mb-10 leading-relaxed max-w-md">
            Connect your Gmail in seconds and start getting answers to any question about your past emails and files.
          </p>
          
          <div className="space-y-6">
            <FeatureItem 
              icon={<Search className="w-5 h-5 text-blue-300" />}
              title="Search emails and attachments instantly"
            />
            <FeatureItem 
              icon={<Bot className="w-5 h-5 text-amber-300" />}
              title="AI answers backed by exact source emails"
            />
            <FeatureItem 
              icon={<ShieldCheck className="w-5 h-5 text-emerald-300" />}
              title="Private, secure, and encrypted"
            />
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-8">
        <div className="w-full max-w-md bg-white p-8 sm:p-10 rounded-2xl border border-slate-200 shadow-sm animate-slide-up">
          <div className="lg:hidden mb-8 flex items-center justify-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-base font-bold">
              ✉
            </div>
            <span className="text-2xl font-bold text-slate-900">InboxIQ</span>
          </div>
          
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-1">Create your account</h2>
            <p className="text-slate-500 text-sm">Start exploring your inbox with AI</p>
          </div>
          
          <RegisterForm />

          <div className="mt-8 pt-4 border-t border-slate-100 text-center text-xs text-slate-400">
            <Link to="/privacy" className="hover:text-blue-600 transition-colors">Privacy Policy</Link>
            <span className="mx-2">•</span>
            <Link to="/terms" className="hover:text-blue-600 transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title }: { icon: React.ReactNode, title: string }) {
  return (
    <div className="flex items-center gap-3.5">
      <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/10 flex items-center justify-center shrink-0 backdrop-blur-xs">
        {icon}
      </div>
      <span className="text-base text-slate-100 font-medium">{title}</span>
    </div>
  );
}
