import React, { useState, useCallback, useRef, useEffect, useMemo, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  PenLine,
  Network,
  BarChart3,
  TrendingUp,
  Settings,
  Moon,
  Sun,
  Menu,
  ChevronDown,
  Globe,
} from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import SearchBar from '@/components/shared/SearchBar';
import { useProjectStore } from '@/store/projectStore';
import { useAuthStore } from '@/store/authStore';
import { useProjects } from '@/hooks/useApi';

/** 侧边栏导航项定义 */
export interface NavItem {
  path: string;
  label: string;
  icon: ReactNode;
  disabled?: boolean;
  tooltip?: string;
}

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 简单的 toast 状态
  const [toastMsg, setToastMsg] = useState('');
  const showToast = (msg: string) => { setToastMsg(msg); setTimeout(() => setToastMsg(''), 2500); };

  // 监听 API client 的 toast 事件
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      showToast(`${detail.type === 'error' ? '❌ ' : ''}${detail.message}`);
    };
    window.addEventListener('novelcraft-toast', handler);
    return () => window.removeEventListener('novelcraft-toast', handler);
  }, []);

  // 暗色模式状态（class 策略 + localStorage 持久化）
  const [isDark, setIsDark] = useState<boolean>(() => {
    const saved: string | null = localStorage.getItem('novelcraft-theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // 项目选择器下拉
  const [projectMenuOpen, setProjectMenuOpen] = useState<boolean>(false);
  const projectMenuRef = useRef<HTMLDivElement>(null);
  const { data: projects = [] } = useProjects();

  // 切换暗色模式
  const toggleDark = useCallback((): void => {
    setIsDark((prev: boolean) => {
      const next: boolean = !prev;
      localStorage.setItem('novelcraft-theme', next ? 'dark' : 'light');
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return next;
    });
  }, []);

  // 初始化时同步 dark class
  useEffect(() => {
    const saved: string | null = localStorage.getItem('novelcraft-theme');
    const prefersDark: boolean = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (saved === 'dark' || (!saved && prefersDark)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  // 点击外部关闭项目选择器
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (projectMenuRef.current && !projectMenuRef.current.contains(e.target as Node)) {
        setProjectMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 判断当前激活的导航项
  const isActive = (path: string): boolean => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  // 当前用户信息（Mock）
  const userName: string = useAuthStore((s) => s.user?.username) || '开发者';
  const userPlan: string = useAuthStore((s) => s.isAuthenticated ? '专业版' : '未登录');

  // 当前选中的项目 ID（来自全局 store，用于拼接项目路由）
  const projectId: string | null = useProjectStore((s) => s.selectedProjectId);
  const setSelectedProjectId = useProjectStore((s) => s.setSelectedProjectId);
  const selectedProject = projects.find((p) => p.id === projectId)?.title || '请选择项目';

  /** 侧边栏导航项 — 根据 selectedProjectId 动态生成项目相关路径 */
  const NAV_ITEMS: NavItem[] = useMemo<NavItem[]>(
    () => [
      { path: '/', label: '总控驾驶舱', icon: <LayoutDashboard size={20} /> },
      {
        path: projectId ? `/write/${projectId}` : '#',
        label: '创作工作台',
        icon: <PenLine size={20} />,
        disabled: !projectId,
        tooltip: projectId ? undefined : '请先在总控驾驶舱选择一个项目',
      },
      {
        path: projectId ? `/foreshadows/${projectId}` : '#',
        label: '伏笔看板',
        icon: <Network size={20} />,
        disabled: !projectId,
        tooltip: projectId ? undefined : '请先在总控驾驶舱选择一个项目',
      },
      {
        path: projectId ? `/quality/${projectId}` : '#',
        label: '质量面板',
        icon: <BarChart3 size={20} />,
        disabled: !projectId,
        tooltip: projectId ? undefined : '请先在总控驾驶舱选择一个项目',
      },
      {
        path: projectId ? `/translate/${projectId}` : '#',
        label: '翻译发布',
        icon: <Globe size={20} />,
        disabled: !projectId,
        tooltip: projectId ? undefined : '请先在总控驾驶舱选择一个项目',
      },
      { path: '/trends', label: '爆款分析', icon: <TrendingUp size={20} /> },
      { path: '/analytics', label: '数据分析', icon: <BarChart3 size={20} /> },
      { path: '/settings', label: '设置', icon: <Settings size={20} /> },
    ],
    [projectId],
  );

  /** 移动端底部 Tab 导航项（5 个主要项） */
  const MOBILE_TABS: NavItem[] = useMemo<NavItem[]>(
    () => [
      { path: '/', label: '总控', icon: <LayoutDashboard size={22} /> },
      {
        path: projectId ? `/write/${projectId}` : '#',
        label: '创作',
        icon: <PenLine size={22} />,
        disabled: !projectId,
        tooltip: !projectId ? '请先选择项目' : undefined,
      },
      {
        path: projectId ? `/foreshadows/${projectId}` : '#',
        label: '伏笔',
        icon: <Network size={22} />,
        disabled: !projectId,
        tooltip: !projectId ? '请先选择项目' : undefined,
      },
      {
        path: projectId ? `/quality/${projectId}` : '#',
        label: '质量',
        icon: <BarChart3 size={22} />,
        disabled: !projectId,
        tooltip: !projectId ? '请先选择项目' : undefined,
      },
      { path: '/trends', label: '趋势', icon: <TrendingUp size={22} /> },
    ],
    [projectId],
  );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#F0F2F5] dark:bg-dark-bg">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl bg-gray-800 text-white text-sm font-medium shadow-lg animate-pulse">
          {toastMsg}
        </div>
      )}
      {/* ===== PC/平板：侧边栏 ===== */}
      <Sidebar
        navItems={NAV_ITEMS}
        isActive={isActive}
        userName={userName}
        userPlan={userPlan}
      />

      {/* ===== 主内容区 ===== */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* ---- 顶部栏 ---- */}
        <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-dark-surface lg:px-6">
          {/* 左侧：移动端菜单按钮 + 面包屑/标题 */}
          <div className="flex items-center gap-3">
            {/* 移动端侧边栏切换（未来扩展） */}
            <button
              className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 lg:hidden"
              aria-label="打开菜单"
            >
              <Menu size={20} />
            </button>

            {/* 项目选择器 */}
            <div className="relative" ref={projectMenuRef}>
              <button
                className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700 transition-colors"
                onClick={() => setProjectMenuOpen((prev: boolean) => !prev)}
                aria-haspopup="listbox"
                aria-expanded={projectMenuOpen}
              >
                <span className="max-w-[160px] truncate sm:max-w-[240px]">{selectedProject}</span>
                <ChevronDown
                  size={14}
                  className={`transition-transform duration-150 ${projectMenuOpen ? 'rotate-180' : ''}`}
                />
              </button>

              {/* 下拉菜单 */}
              {projectMenuOpen && (
                <div
                  className="absolute left-0 top-full mt-1 w-64 rounded-md border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-600 dark:bg-gray-800 z-50"
                  role="listbox"
                >
                  {projects.map((proj) => (
                    <button
                      key={proj.id}
                      className={`w-full px-4 py-2 text-left text-sm transition-colors hover:bg-primary-50 dark:hover:bg-gray-700 ${
                        proj.id === projectId
                          ? 'font-semibold text-primary-500'
                          : 'text-gray-700 dark:text-gray-200'
                      }`}
                      onClick={() => {
                        setSelectedProjectId(proj.id);
                        setProjectMenuOpen(false);
                      }}
                      role="option"
                      aria-selected={proj.id === projectId}
                    >
                      {proj.title}
                    </button>
                  ))}
                  <div className="border-t border-gray-100 dark:border-gray-600 mt-1 pt-1">
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-primary-500 hover:bg-primary-50 dark:hover:bg-gray-700"
                      onClick={() => {
                        setProjectMenuOpen(false);
                        navigate('/');
                      }}
                    >
                      + 新建项目
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 右侧：搜索 + 用户 + 暗色模式切换 */}
          <div className="flex items-center gap-3">
            {/* 全局搜索 */}
            <SearchBar />

            {/* 暗色模式切换 */}
            <button
              onClick={toggleDark}
              className="rounded-md p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
              aria-label={isDark ? '切换到亮色模式' : '切换到暗色模式'}
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            {/* 用户头像 */}
            <div className="flex items-center gap-2 cursor-pointer rounded-md px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-primary text-xs font-semibold text-white flex-shrink-0">
                {userName.charAt(0)}
              </div>
              <span className="hidden text-sm font-medium text-gray-700 dark:text-gray-200 sm:block">
                {userName}
              </span>
            </div>
          </div>
        </header>

        {/* ---- 内容区 ---- */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1440px] p-4 lg:p-6">
            {children}
          </div>
        </main>
      </div>

      {/* ===== 移动端底部 Tab 导航 ===== */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 flex h-14 items-center justify-around border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-dark-surface lg:hidden">
        {MOBILE_TABS.map((tab: NavItem) => {
          const active: boolean = !tab.disabled && isActive(tab.path);
          return (
            <button
              key={tab.label}
              onClick={() => tab.disabled ? showToast('请先在总控驾驶舱选择一个项目') : navigate(tab.path)}
              disabled={tab.disabled}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] transition-colors ${
                tab.disabled
                  ? 'text-gray-300 cursor-not-allowed opacity-40 dark:text-gray-600'
                  : active
                    ? 'text-primary-500'
                    : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              <span className={active ? 'text-primary-500' : ''}>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default AppLayout;
