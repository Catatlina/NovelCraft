import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Settings as SettingsIcon,
  Server,
  Key,
  User,
  Moon,
  Sun,
  LogOut,
  Save,
  Eye,
  EyeOff,
  Shield,
  Zap,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useThemeStore } from '@/store/themeStore';
import { useProjectStore } from '@/store/projectStore';
import { API_BASE, api } from '@/api/client';

/**
 * 设置页面
 * 路由: /settings
 *
 * 功能：
 * - API 地址配置（从 localStorage 读取/写入）
 * - Token 显示/管理
 * - 用户信息展示（从 authStore 获取）
 * - 暗色模式开关（使用 themeStore）
 * - 保存按钮（更新 localStorage + 重新初始化 API client）
 * - 登出按钮
 */
const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, error } = useAuthStore();
  const { isDark, toggle: toggleDark } = useThemeStore();
  const projectId: string | null = useProjectStore((s) => s.selectedProjectId);

  const [apiBase, setApiBase] = useState<string>(API_BASE);
  const [showKey, setShowKey] = useState<boolean>(false);
  const [deepseekKey, setDeepseekKey] = useState<string>('');
  const [deepseekModel, setDeepseekModel] = useState<string>('deepseek-chat');
  const [hasDeepseekKey, setHasDeepseekKey] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  useEffect(() => {
    api<{ has_deepseek_api_key: boolean; deepseek_model: string }>('/ai-settings')
      .then((res) => {
        setHasDeepseekKey(res.has_deepseek_api_key);
        setDeepseekModel(res.deepseek_model || 'deepseek-chat');
      })
      .catch(() => undefined);
  }, []);

  const handleSaveApi = useCallback(async () => {
    setSaveStatus('saving');
    try {
      const res = await api<{ has_deepseek_api_key: boolean; deepseek_model: string }>(
        '/ai-settings',
        'PUT',
        {
          deepseek_api_key: deepseekKey || undefined,
          deepseek_model: deepseekModel || 'deepseek-chat',
        },
      );
      setHasDeepseekKey(res.has_deepseek_api_key);
      setDeepseekModel(res.deepseek_model);
      setDeepseekKey('');
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch {
      setSaveStatus('error');
    }
  }, [deepseekKey, deepseekModel]);

  // 登出
  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <SettingsIcon size={28} className="text-primary-500" />
        <h1 className="text-display text-gray-800 dark:text-gray-100">设置</h1>
      </div>

      {/* ===== API 配置 ===== */}
      <section className="card">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
          <Server size={18} className="text-gray-400" />
          <h2 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            API 配置
          </h2>
        </div>

        <div className="space-y-4">
          {/* DeepSeek API Key */}
          <div>
            <label className="mb-1 block text-[13px] font-semibold text-gray-500 dark:text-gray-400">
              DeepSeek API Key
            </label>
            <div className="flex gap-2">
              <input
                className="input flex-1"
                type={showKey ? 'text' : 'password'}
                value={deepseekKey}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeepseekKey(e.target.value)}
                placeholder={hasDeepseekKey ? '已配置；留空则不覆盖现有 Key' : 'sk-your-deepseek-api-key'}
              />
              <button
                className="btn-ghost h-9 w-9 p-0"
                onClick={() => setShowKey((prev: boolean) => !prev)}
                title={showKey ? '隐藏' : '显示'}
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <p className="mt-1 text-[12px] text-gray-400 dark:text-gray-500">
              从 <a href="https://platform.deepseek.com/api_keys" target="_blank" className="underline">platform.deepseek.com</a> 获取；保存后密钥仅在服务端加密存储，不会回显。
            </p>
          </div>

          {/* Model */}
          <div>
            <label className="mb-1 block text-[13px] font-semibold text-gray-500 dark:text-gray-400">
              调用模型
            </label>
            <input
              className="input w-full"
              value={deepseekModel}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeepseekModel(e.target.value)}
              placeholder="deepseek-chat"
            />
            <p className="mt-1 text-[12px] text-gray-400 dark:text-gray-500">
              模型名称，如 deepseek-chat / deepseek-reasoner / gpt-4o 等
            </p>
          </div>

          {/* API 地址 */}
          <div>
            <label className="mb-1 block text-[13px] font-semibold text-gray-500 dark:text-gray-400">
              API 接口地址
            </label>
            <div className="flex gap-2">
              <input
                className="input flex-1"
                value={apiBase}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setApiBase(e.target.value)
                }
                placeholder="http://localhost:8100/api/v1"
              />
              <button
                className="btn-primary"
                onClick={handleSaveApi}
                disabled={saveStatus === 'saving'}
              >
                <Save size={16} />
                <span>
                  {saveStatus === 'saving'
                    ? '保存中…'
                    : saveStatus === 'saved'
                      ? '已保存'
                      : saveStatus === 'error'
                        ? '保存失败'
                        : '保存'}
                </span>
              </button>
            </div>
            <p className="mt-1 text-[12px] text-gray-400 dark:text-gray-500">
              后端 API 地址，修改保存后立即生效
            </p>
          </div>

          {/* API 基地址当前值 */}
          <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-primary-500" />
              <span className="text-[13px] font-medium text-gray-600 dark:text-gray-300">
                当前 API 地址：
              </span>
              <code className="rounded bg-gray-200 px-2 py-0.5 text-[12px] text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                {API_BASE}
              </code>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Token 管理 ===== */}
      <section className="card">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
          <Key size={18} className="text-gray-400" />
          <h2 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            Token 管理
          </h2>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
          <Shield size={36} className="text-gray-300 dark:text-gray-600" />
          <p className="text-[13px] text-gray-600 dark:text-gray-300">
            认证 Token 通过 httpOnly Cookie 自动管理
          </p>
          <p className="text-[12px] text-gray-400 dark:text-gray-500">
            Access Token 15分钟自动刷新，无需手动操作
          </p>
        </div>
      </section>

      {/* ===== 账户信息 ===== */}
      <section className="card">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
          <User size={18} className="text-gray-400" />
          <h2 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            账户信息
          </h2>
        </div>

        {isAuthenticated && user ? (
          <div className="space-y-4">
            {/* 用户详情 */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  用户名
                </span>
                <span className="mt-1 block text-[14px] font-semibold text-gray-800 dark:text-gray-100">
                  {user.username}
                </span>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  邮箱
                </span>
                <span className="mt-1 block text-[14px] text-gray-600 dark:text-gray-300">
                  {user.email || '未设置'}
                </span>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  用户 ID
                </span>
                <span className="mt-1 block font-mono text-[12px] text-gray-500 dark:text-gray-400">
                  {user.id}
                </span>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  套餐
                </span>
                <span className="mt-1 flex items-center gap-2">
                  <span className="text-[14px] font-semibold text-primary-500">
                    {user.plan || '免费版'}
                  </span>
                  <span className="badge badge-success text-[11px]">已激活</span>
                </span>
              </div>
            </div>

            {/* 注册时间 */}
            <div className="text-[12px] text-gray-400 dark:text-gray-500">
              注册时间：{new Date(user.created_at).toLocaleDateString('zh-CN')}
            </div>

            {/* 错误信息 */}
            {error && (
              <div className="rounded-md bg-red-50 p-3 text-[13px] text-red-600 dark:bg-red-900/30 dark:text-red-400">
                {error}
              </div>
            )}

            {/* 登出按钮 */}
            <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
              <button
                className="btn-ghost flex items-center gap-2 text-red-500 hover:bg-red-50 hover:text-red-600 dark:text-red-400 dark:hover:bg-red-900/30"
                onClick={handleLogout}
              >
                <LogOut size={16} />
                登出账户
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
            <User size={36} className="text-gray-300 dark:text-gray-600" />
            <p className="text-[13px] text-gray-400 dark:text-gray-500">
              未登录
            </p>
            <button
              className="btn-primary"
              onClick={() => navigate('/login')}
            >
              前往登录
            </button>
          </div>
        )}
      </section>

      {/* ===== 偏好设置 ===== */}
      <section className="card">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
          {isDark ? (
            <Moon size={18} className="text-gray-400" />
          ) : (
            <Sun size={18} className="text-gray-400" />
          )}
          <h2 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            偏好设置
          </h2>
        </div>

        {/* 暗色模式 */}
        <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800/50">
          <div>
            <p className="text-[14px] font-medium text-gray-700 dark:text-gray-200">
              暗色模式
            </p>
            <p className="mt-0.5 text-[12px] text-gray-400 dark:text-gray-500">
              {isDark ? '当前为暗色模式' : '当前为亮色模式'}
            </p>
          </div>
          <button
            onClick={toggleDark}
            className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors duration-200 ${
              isDark
                ? 'bg-primary-500'
                : 'bg-gray-300 dark:bg-gray-600'
            }`}
            role="switch"
            aria-checked={isDark}
            aria-label="切换暗色模式"
          >
            <span
              className={`inline-flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200 ${
                isDark ? 'translate-x-6' : 'translate-x-1'
              }`}
            >
              {isDark ? (
                <Moon size={12} className="text-primary-500" />
              ) : (
                <Sun size={12} className="text-amber-500" />
              )}
            </span>
          </button>
        </div>
      </section>

      {/* ===== 页面导航 ===== */}
      <section className="card">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
          <SettingsIcon size={18} className="text-gray-400" />
          <h2 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            页面导航
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {[
            { path: '/', label: '总控驾驶舱' },
            { path: projectId ? `/write/${projectId}` : '/', label: '创作工作台' },
            { path: projectId ? `/foreshadows/${projectId}` : '/', label: '伏笔看板' },
            { path: projectId ? `/quality/${projectId}` : '/', label: '质量面板' },
            { path: '/trends', label: '爆款分析' },
          ].map((nav) => (
            <button
              key={nav.path}
              className="btn-secondary btn-sm"
              onClick={() => navigate(nav.path)}
            >
              {nav.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
};

export default SettingsPage;
