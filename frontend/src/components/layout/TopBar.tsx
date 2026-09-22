import React from 'react';
import { Search, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { getInitials } from '../../utils/helpers';
import { useNavigate } from 'react-router-dom';

export default function TopBar() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = React.useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };
  
  return (
    <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-20">
      
      {/* Quick Search */}
      <form onSubmit={handleSearchSubmit} className="w-full max-w-md relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input 
          type="text" 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search emails, documents, and notes..." 
          className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition-all shadow-xs"
        />
      </form>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        {/* Sync Status Badge */}
        {user?.is_gmail_connected ? (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Gmail Connected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Gmail Setup Required</span>
          </div>
        )}

        {/* Profile Avatar */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shadow-xs">
            {user ? getInitials(user.full_name) : 'U'}
          </div>
        </div>
      </div>
    </header>
  );
}
