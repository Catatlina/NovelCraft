import React, { Suspense, lazy, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { useAuthStore } from '@/store/authStore';

/**
 * 懒加载页面组件
 * 各页面模块将在此被动态导入，减少首屏包体积
 */
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const WritingWorkspace = lazy(() => import('@/pages/WritingWorkspace'));
const ForeshadowBoard = lazy(() => import('@/pages/ForeshadowBoard'));
const QualityDashboard = lazy(() => import('@/pages/QualityDashboard'));
const TrendAnalysis = lazy(() => import('@/pages/TrendAnalysis'));
const Settings = lazy(() => import('@/pages/Settings'));
const Login = lazy(() => import('@/pages/Login'));
const TranslatePage = lazy(() => import('@/pages/TranslatePage'));
const AnalyticsDashboard = lazy(() => import('@/pages/AnalyticsDashboard'));
const QuickStart = lazy(() => import('@/pages/QuickStart'));
const ConfigCenter = lazy(() => import('@/pages/ConfigCenter'));

/** 页面加载时的悬浮动画 */
const PageLoading: React.FC = () => (
  <div className="flex h-screen w-full items-center justify-center bg-[#F0F2F5] dark:bg-dark-bg">
    <LoadingSpinner size="lg" text="加载中…" />
  </div>
);

/**
 * 路由鉴权守卫：通过 /auth/me 验证 httpOnly cookie 认证状态
 */
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      checkAuth();
    }
  }, [isAuthenticated, checkAuth]);

  if (isLoading) {
    return <PageLoading />;
  }

  if (!isAuthenticated && location.pathname !== '/login') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

/** 带 Suspense + AuthGuard 的布局路由 */
const ProtectedLayout: React.FC = () => (
  <AuthGuard>
    <AppLayout>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route index element={<Dashboard />} />
          <Route path="config" element={<ConfigCenter />} />
          <Route path="quick-start" element={<QuickStart />} />
          <Route path="write/:projectId" element={<WritingWorkspace />} />
          <Route path="foreshadows/:projectId" element={<ForeshadowBoard />} />
          <Route path="quality/:projectId" element={<QualityDashboard />} />
          <Route path="trends" element={<TrendAnalysis />} />
          <Route path="settings" element={<Settings />} />
          <Route path="translate/:projectId" element={<TranslatePage />} />
          <Route path="analytics" element={<AnalyticsDashboard />} />
          {/* 404 处理：匹配 /write/、/foreshadows/、/quality/ 无 projectId 时 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </AppLayout>
  </AuthGuard>
);

/** 404 页面 */
const NotFoundPage: React.FC = () => (
  <div className="flex flex-col items-center justify-center py-20 text-center">
    <div className="mb-4 text-6xl font-bold text-gray-200 dark:text-gray-700">404</div>
    <h2 className="mb-2 text-xl font-semibold text-gray-700 dark:text-gray-200">
      页面未找到
    </h2>
    <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
      您访问的页面不存在或已被移除
    </p>
    <a href="/" className="btn-primary">
      返回总控驾驶舱
    </a>
  </div>
);

const App: React.FC = () => {
  const { checkAuth } = useAuthStore();

  // 应用启动时恢复认证状态
  useEffect(() => { checkAuth(); }, [checkAuth]);

  // 监听系统暗色模式切换，动态更新 dark class
  useEffect(() => {
    const mediaQuery: MediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent): void => {
      try {
        const saved: string | null = localStorage.getItem('novelcraft-theme');
        if (!saved) {
          if (e.matches) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
      } catch {
        // DOM 操作失败时静默处理
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        {/* 登录页无布局 */}
        <Route path="/login" element={<Login />} />

        {/* 受保护页面布局 */}
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </Suspense>
  );
};

export default App;
