import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Search,
  GitFork,
  Sparkles,
  Settings,
  Menu,
  X,
  Cpu,
  UserCheck,
  Briefcase,
  Mail
} from 'lucide-react';

interface SidebarLinkProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

const SidebarLink: React.FC<SidebarLinkProps> = ({ to, icon, label, onClick }) => {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));

  return (
    <Link
      to={to}
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
        isActive
          ? 'bg-brand-600/20 text-brand-500 border-l-4 border-brand-500 font-medium'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
      }`}
    >
      <span className={`transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-brand-500' : 'text-slate-400 group-hover:text-slate-300'}`}>
        {icon}
      </span>
      <span>{label}</span>
    </Link>
  );
};

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/') return 'Dashboard Hub';
    if (path.startsWith('/upload')) return 'Upload Resumes';
    if (path.startsWith('/search')) return 'Candidate Search';
    if (path.startsWith('/jobs')) return 'Job Management';
    if (path.startsWith('/candidate')) return 'Candidate Profile';
    if (path.startsWith('/graph')) return 'Relationship Explorer';
    if (path.startsWith('/ai-summary')) return 'AI Assessment Workspace';
    if (path.startsWith('/gmail-import')) return 'Gmail Resume Import';
    if (path.startsWith('/settings')) return 'System Settings';
    return 'Knowledge Graph Search';
  };

  return (
    <div className="min-h-screen bg-dark-bg text-slate-200 flex">
      {/* BACKGROUND GLOW DECORATIONS */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-brand-900/10 rounded-full blur-[120px] pointer-events-none -z-10 animate-pulse-slow" />
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] bg-blue-900/10 rounded-full blur-[120px] pointer-events-none -z-10" />

      {/* DESKTOP SIDEBAR */}
      <aside className="hidden lg:flex flex-col w-64 border-r border-dark-border bg-dark-bg/60 backdrop-blur-md p-6 justify-between shrink-0">
        <div className="space-y-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center glow-purple">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight leading-none">GraphCV</h1>
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">AI Search Engine</span>
            </div>
          </Link>

          {/* Nav Links */}
          <nav className="space-y-1.5">
            <SidebarLink to="/" icon={<LayoutDashboard size={20} />} label="Dashboard" />
            <SidebarLink to="/upload" icon={<UploadCloud size={20} />} label="Resume Upload" />
            <SidebarLink to="/search" icon={<Search size={20} />} label="Candidate Search" />
            <SidebarLink to="/jobs" icon={<Briefcase size={20} />} label="Job Management" />
            <SidebarLink to="/graph" icon={<GitFork size={20} />} label="Relationship Graph" />
            <SidebarLink to="/ai-summary" icon={<Sparkles size={20} />} label="AI Summaries" />
            <SidebarLink to="/gmail-import" icon={<Mail size={20} />} label="Gmail Import" />
            <SidebarLink to="/settings" icon={<Settings size={20} />} label="Settings" />
          </nav>
        </div>

        {/* Footer/User Profile info inside desktop sidebar */}
        <div className="border-t border-dark-border/60 pt-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-slate-800 border border-dark-border flex items-center justify-center">
            <UserCheck className="w-5 h-5 text-brand-500" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-200">HR Admin Panel</h4>
            <p className="text-[10px] text-slate-500">Enterprise Access</p>
          </div>
        </div>
      </aside>

      {/* MOBILE DRAWER */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <aside className="relative flex flex-col w-64 bg-dark-bg border-r border-dark-border p-6 justify-between animate-in slide-in-from-left duration-200">
            <div className="space-y-8">
              <div className="flex items-center justify-between">
                <Link to="/" className="flex items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center">
                    <Cpu className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white tracking-tight leading-none">GraphCV</h2>
                    <span className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold">AI Search Engine</span>
                  </div>
                </Link>
                <button 
                  onClick={() => setMobileMenuOpen(false)} 
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                >
                  <X size={20} />
                </button>
              </div>

              <nav className="space-y-1">
                <SidebarLink to="/" icon={<LayoutDashboard size={18} />} label="Dashboard" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/upload" icon={<UploadCloud size={18} />} label="Resume Upload" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/search" icon={<Search size={18} />} label="Candidate Search" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/jobs" icon={<Briefcase size={18} />} label="Job Management" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/graph" icon={<GitFork size={18} />} label="Relationship Graph" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/ai-summary" icon={<Sparkles size={18} />} label="AI Summaries" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/gmail-import" icon={<Mail size={18} />} label="Gmail Import" onClick={() => setMobileMenuOpen(false)} />
                <SidebarLink to="/settings" icon={<Settings size={18} />} label="Settings" onClick={() => setMobileMenuOpen(false)} />
              </nav>
            </div>

            <div className="border-t border-dark-border/60 pt-4 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
                <UserCheck className="w-4 h-4 text-brand-500" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-200">HR Admin Panel</h4>
                <p className="text-[10px] text-slate-500 text-left">Enterprise Access</p>
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* HEADER TOP BAR */}
        <header className="h-16 border-b border-dark-border/60 bg-dark-bg/40 backdrop-blur-md flex items-center justify-between px-6 shrink-0 z-30">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
            >
              <Menu size={20} />
            </button>
            <h2 className="text-lg font-bold text-white tracking-tight">{getPageTitle()}</h2>
          </div>

          <div className="flex items-center gap-4">
            {/* Quick Status indicators */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-dark-border text-[11px] text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Engine Status: Online</span>
            </div>
            
            {/* Action buttons or details */}
            <Link 
              to="/upload" 
              className="hidden sm:flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold py-2 px-4 rounded-xl shadow-lg shadow-brand-700/20 transition-all duration-200"
            >
              <UploadCloud size={14} />
              <span>Import Resume</span>
            </Link>
          </div>
        </header>

        {/* PAGE CONTENT CONTAINER */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
};
