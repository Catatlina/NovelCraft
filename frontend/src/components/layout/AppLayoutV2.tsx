import React, { useState, useCallback, useRef, useEffect, useMemo, type ReactNode } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { LayoutDashboard, PenLine, Network, BarChart3, TrendingUp, Settings, Sun, Moon, Search, Globe, Sparkles, Cog, Zap, ChevronDown } from 'lucide-react';
import { useProjectStore } from '@/store/projectStore';
import { useAuthStore } from '@/store/authStore';
import { useProjects } from '@/hooks/useApi';
import '@/styles/novelcraft-theme.css';

interface Props { children: ReactNode }

const NAV = [
  { path: '/', label: '总控驾驶舱', icon: LayoutDashboard },
  { path: '/quick-start', label: '快速开始', icon: Zap },
  { path: null, label: '创作工作台', icon: PenLine, needProject: true, projectPath: '/write' },
  { path: null, label: '伏笔看板', icon: Network, needProject: true, projectPath: '/foreshadows' },
  { path: null, label: '质量面板', icon: BarChart3, needProject: true, projectPath: '/quality' },
  { path: null, label: '翻译发布', icon: Globe, needProject: true, projectPath: '/translate' },
  { path: '/trends', label: '爆款分析', icon: TrendingUp },
  { path: '/analytics', label: '数据分析', icon: BarChart3 },
  { path: '/config', label: '配置中心', icon: Cog },
  { path: '/settings', label: '设置', icon: Settings },
];

export default function AppLayout({ children }: Props) {
  const nav = useNavigate();
  const loc = useLocation();
  const [toast, setToast] = useState('');
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();
  const [projectMenuOpen, setProjectMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'));

  const { data: projects = [] } = useProjects();
  const userName = useAuthStore(s => s.user?.username) || '开发者';
  const projectId = useProjectStore(s => s.selectedProjectId);
  const setProjectId = useProjectStore(s => s.setSelectedProjectId);
  const selectedLabel = projects.find((p: any) => p.id === projectId)?.title || '请选择项目';

  const showToast = (msg: string) => {
    setToast(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2500);
  };

  useEffect(() => {
    const h = (e: Event) => { const d = (e as CustomEvent).detail; showToast(d.message); };
    window.addEventListener('novelcraft-toast', h);
    return () => window.removeEventListener('novelcraft-toast', h);
  }, []);

  const toggleDark = () => {
    setIsDark(prev => {
      const next = !prev;
      localStorage.setItem('novelcraft-theme', next ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', next);
      return next;
    });
  };

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setProjectMenuOpen(false);
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  const isActive = (path: string) => loc.pathname === path || (path !== '/' && loc.pathname.startsWith(path));

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--nc-bg)' }}>
      {toast && (
        <div style={{ position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)', zIndex: 9999,
          padding: '8px 20px', borderRadius: 8, background: 'rgba(0,0,0,0.85)', color: '#fff', fontSize: 13,
          backdropFilter: 'blur(8px)', animation: 'fadeIn 0.3s' }}>{toast}</div>
      )}

      {/* Sidebar */}
      <aside style={{ position: 'fixed', left: 0, top: 0, bottom: 0, width: 220,
        background: 'rgba(10,10,20,0.95)', borderRight: '1px solid var(--nc-border)',
        backdropFilter: 'blur(20px)', zIndex: 100, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '18px 20px', fontSize: 18, fontWeight: 800,
          background: 'linear-gradient(135deg, var(--nc-primary), var(--nc-accent))',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: 2 }}>
          星禾写作助手
        </div>
        <nav style={{ flex: 1, padding: '4px 10px' }}>
          {NAV.map(item => {
            const realPath = item.needProject && projectId ? `${item.projectPath}/${projectId}` : item.path;
            const disabled = item.needProject && !projectId;
            const active = !disabled && realPath && isActive(realPath);
            return (
              <Link key={item.label}
                to={disabled ? '#' : (realPath || '#')}
                onClick={e => disabled && e.preventDefault()}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8,
                  color: active ? 'var(--nc-primary)' : disabled ? 'rgba(255,255,255,0.15)' : 'var(--nc-text-dim)',
                  fontSize: 13, fontWeight: 500, textDecoration: 'none', marginBottom: 1,
                  background: active ? 'linear-gradient(135deg, rgba(255,107,53,0.12), rgba(255,36,66,0.08))' : 'transparent',
                  transition: 'all 0.2s', pointerEvents: disabled ? 'none' : undefined,
                }}>
                <item.icon size={18} />
                <span>{item.label}</span>
                {disabled && <span style={{ marginLeft: 'auto', fontSize: 10 }}>🔒</span>}
              </Link>
            );
          })}
        </nav>
        <div style={{ padding: '14px 16px', borderTop: '1px solid var(--nc-border)', display: 'flex',
          alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--nc-primary), var(--nc-secondary))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
            {userName[0]}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text)' }}>{userName}</div>
            <div style={{ fontSize: 10, color: 'var(--nc-text-dim)' }}>专业版</div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, marginLeft: 220 }}>
        {/* Header */}
        <header style={{ position: 'sticky', top: 0, height: 52, zIndex: 50,
          background: 'rgba(10,10,20,0.85)', backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--nc-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div ref={menuRef} style={{ position: 'relative' }}>
              <button onClick={() => setProjectMenuOpen(p => !p)}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
                  borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--nc-glass-border)',
                  color: 'var(--nc-text)', fontSize: 13, cursor: 'pointer' }}>
                <span style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedLabel}
                </span>
                <ChevronDown size={14} />
              </button>
              {projectMenuOpen && (
                <div style={{ position: 'absolute', left: 0, top: '100%', marginTop: 4, width: 240,
                  background: 'var(--nc-card)', border: '1px solid var(--nc-glass-border)', borderRadius: 8,
                  backdropFilter: 'blur(16px)', padding: 4, zIndex: 100 }}>
                  {projects.map((p: any) => (
                    <div key={p.id} onClick={() => { setProjectId(p.id); setProjectMenuOpen(false); }}
                      style={{ padding: '8px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 13,
                        background: p.id === projectId ? 'rgba(255,107,53,0.1)' : 'transparent',
                        color: p.id === projectId ? 'var(--nc-primary)' : 'var(--nc-text)' }}>
                      {p.title}
                    </div>
                  ))}
                  <div style={{ borderTop: '1px solid var(--nc-border)', marginTop: 4, paddingTop: 4 }}>
                    <div onClick={() => { setProjectMenuOpen(false); nav('/quick-start'); }}
                      style={{ padding: '8px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 13, color: 'var(--nc-primary)' }}>
                      + 新建项目
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button onClick={toggleDark}
              style={{ padding: 6, borderRadius: 6, background: 'transparent', border: 'none',
                color: 'var(--nc-text-dim)', cursor: 'pointer' }}>
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Content */}
        <main style={{ padding: 24 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
