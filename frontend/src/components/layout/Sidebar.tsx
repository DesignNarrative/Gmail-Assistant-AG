import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Settings, 
  LogOut
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { getInitials } from '../../utils/helpers';
import { cn } from '../../utils/helpers';

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = React.useState(false);

  const navItems = [
    { name: 'AI Chat', icon: MessageSquare, path: '/chat' },
    { name: 'Home', icon: LayoutDashboard, path: '/dashboard' },
    { name: 'Settings', icon: Settings, path: '/settings' },
  ];

  return (
    <div className={cn(
      "h-screen bg-dark-card border-r border-dark-border flex flex-col transition-all duration-300",
      collapsed ? "w-20" : "w-64"
    )}>
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-dark-border">
        {!collapsed && (
          <img src="/AbhinavGrouplogo.png" alt="Logo" className="h-8 animate-fade-in" />
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-md text-text-secondary hover:text-text-primary hover:bg-dark-bg transition-colors"
        >
          {collapsed ? <img src="/AbhinavGrouplogo.png" alt="Logo" className="h-8" /> : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Nav Links */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1 custom-scrollbar">
        {navItems.map((item) => (
          <div key={item.name} className="relative group">
            <NavLink
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                isActive
                  ? "bg-primary-blue/10 text-white before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:bg-gold-accent before:rounded-r-md"
                  : "text-text-secondary hover:bg-dark-bg hover:text-text-primary"
              )}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              {!collapsed && (
                <span className="font-medium truncate">{item.name}</span>
              )}
            </NavLink>
            
            {/* Tooltip when collapsed */}
            {collapsed && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 bg-dark-bg border border-dark-border rounded text-xs text-text-primary opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity">
                {item.name}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-dark-border">
        <div className={cn("flex items-center gap-3", collapsed ? "justify-center" : "justify-between")}>
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-blue to-secondary-blue flex items-center justify-center text-sm font-bold text-white shrink-0">
              {user ? getInitials(user.full_name) : 'U'}
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span className="text-sm font-medium text-white truncate">{user?.full_name}</span>
                <span className="text-xs text-text-secondary capitalize">{user?.role}</span>
              </div>
            )}
          </div>
          {!collapsed && (
            <button 
              onClick={logout}
              className="p-2 text-text-secondary hover:text-status-error transition-colors rounded-md hover:bg-status-error/10"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
