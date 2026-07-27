import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { getInitials } from '../../utils/helpers';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Home',
  '/chat': 'AI Chat',
  '/settings': 'Settings',
};

export default function TopBar() {
  const { user } = useAuthStore();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || '';

  return (
    <header className="h-16 border-b border-dark-border bg-dark-bg/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-40">
      
      {/* Page title */}
      <h2 className="text-sm font-semibold text-text-primary">{title}</h2>

      {/* Profile */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-text-secondary hidden sm:block">{user?.full_name}</span>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-blue to-secondary-blue flex items-center justify-center text-xs font-bold text-white shadow-sm">
          {user ? getInitials(user.full_name) : 'U'}
        </div>
      </div>
    </header>
  );
}
