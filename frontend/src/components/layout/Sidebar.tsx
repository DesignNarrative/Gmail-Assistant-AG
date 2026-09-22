import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Search, 
  Settings, 
  LogOut,
  ChevronLeft
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { getInitials } from '../../utils/helpers';
import { cn } from '../../utils/helpers';

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = React.useState(false);

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { name: 'AI Chat', icon: MessageSquare, path: '/chat' },
    { name: 'Search', icon: Search, path: '/search' },
    { name: 'Settings', icon: Settings, path: '/settings' },
  ];

  return (
    <div className={cn(
      "h-screen bg-white border-r border-slate-200 flex flex-col transition-all duration-200 z-30 shadow-sm",
      collapsed ? "w-18" : "w-64"
    )}>
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-100">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-base font-bold shadow-sm shadow-blue-500/20">
              ✉
            </div>
            <span className="text-lg font-bold text-slate-900 tracking-tight">InboxIQ</span>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-base font-bold mx-auto shadow-sm shadow-blue-500/20">
            ✉
          </div>
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors",
            collapsed && "hidden"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Nav Links */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group",
              isActive
                ? "bg-blue-50 text-blue-700 font-semibold shadow-xs"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium"
            )}
            title={collapsed ? item.name : undefined}
          >
            <item.icon className={cn(
              "w-5 h-5 shrink-0 transition-colors",
              "group-hover:text-blue-600"
            )} />
            {!collapsed && (
              <span className="truncate">{item.name}</span>
            )}
          </NavLink>
        ))}
      </div>

      {/* User Footer */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/50">
        <div className={cn("flex items-center gap-3", collapsed ? "justify-center" : "justify-between")}>
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-xs">
              {user ? getInitials(user.full_name) : 'U'}
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span className="text-xs font-semibold text-slate-800 truncate">{user?.full_name}</span>
                <span className="text-[11px] text-slate-500 truncate">{user?.email}</span>
              </div>
            )}
          </div>
          {!collapsed && (
            <button 
              onClick={logout}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors shrink-0"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
