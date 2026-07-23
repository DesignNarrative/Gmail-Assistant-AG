import React from 'react';
import { Search, Bell } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { getInitials } from '../../utils/helpers';

export default function TopBar() {
  const { user } = useAuthStore();
  
  return (
    <header className="h-16 border-b border-dark-border bg-dark-bg/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-40">
      
      {/* Search */}
      <div className="w-full max-w-xl relative group">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary group-focus-within:text-secondary-blue transition-colors" />
        <input 
          type="text" 
          placeholder="Ask anything about your emails..." 
          className="w-full bg-dark-card border border-dark-border rounded-full pl-10 pr-4 py-2 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-secondary-blue focus:ring-1 focus:ring-secondary-blue transition-all"
        />
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-6">
        {/* Sync Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-card border border-dark-border">
          <div className="w-2 h-2 rounded-full bg-status-warning animate-pulse" />
          <span className="text-xs font-medium text-text-secondary">Sync Pending</span>
        </div>
        
        {/* Notifications */}
        <button className="relative p-2 text-text-secondary hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-secondary-blue rounded-full"></span>
        </button>

        {/* Mini profile */}
        <div className="flex items-center gap-2 pl-4 border-l border-dark-border">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-blue to-secondary-blue flex items-center justify-center text-xs font-bold text-white shadow-sm">
            {user ? getInitials(user.full_name) : 'U'}
          </div>
        </div>
      </div>
    </header>
  );
}
