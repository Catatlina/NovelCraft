import React, { useState, useCallback, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

/** 登录/注册 Tab */
type AuthTab = 'login' | 'register';

/**
 * 登录页面
 * 路由: /login
 *
 * 功能：
 * - 登录表单（用户名 + 密码）
 * - 注册表单（用户名 + 密码 + 邮箱 + 确认密码）
 * - 登录/注册切换 Tab
 * - 调用 authStore.login / authStore.register
 * - 成功后跳转到 /
 * - 错误提示
 * - 品牌色渐变背景 + 白色卡片
 * - 响应式布局
 */
const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, register, isAuthenticated, isLoading, error, clearError } =
    useAuthStore();

  // Tab 切换
  const [tab, setTab] = useState<AuthTab>('login');

  // 表单字段
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [passwordConfirm, setPasswordConfirm] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);

  // 客户端验证错误
  const [validationError, setValidationError] = useState<string | null>(null);

  // 如果已登录，直接跳转到首页
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // 切换 Tab 时清除错误
  const handleTabChange = useCallback(
    (newTab: AuthTab) => {
      setTab(newTab);
      clearError();
      setValidationError(null);
    },
    [clearError],
  );

  // 客户端表单验证
  const validate = useCallback((): boolean => {
    if (!username.trim()) {
      setValidationError('请输入用户名');
      return false;
    }
    if (!password.trim()) {
      setValidationError('请输入密码');
      return false;
    }
    if (password.length < 6) {
      setValidationError('密码长度至少 6 位');
      return false;
    }
    if (tab === 'register') {
      if (!email.trim()) {
        setValidationError('请输入邮箱');
        return false;
      }
      const emailRegex: RegExp = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email.trim())) {
        setValidationError('请输入有效的邮箱地址');
        return false;
      }
      if (password !== passwordConfirm) {
        setValidationError('两次输入的密码不一致');
        return false;
      }
    }
    return true;
  }, [username, password, email, passwordConfirm, tab]);

  // 登录提交
  const handleLogin = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      clearError();
      setValidationError(null);

      if (!validate()) return;

      try {
        await login({ username: username.trim(), password });
        navigate('/', { replace: true });
      } catch {
        // 错误已由 authStore 设置
      }
    },
    [login, navigate, username, password, validate, clearError],
  );

  // 注册提交
  const handleRegister = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      clearError();
      setValidationError(null);

      if (!validate()) return;

      try {
        await register({
          username: username.trim(),
          email: email.trim(),
          password,
          password_confirm: passwordConfirm,
        });
        navigate('/', { replace: true });
      } catch {
        // 错误已由 authStore 设置
      }
    },
    [register, navigate, username, email, password, passwordConfirm, validate, clearError],
  );

  // 显示的错误（优先客户端校验，其次 store 错误）
  const displayError: string | null = validationError || error;

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 p-4 dark:from-dark-bg dark:via-dark-surface dark:to-primary-900/20 sm:p-6">
      {/* 背景装饰 */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-80 w-80 rounded-full bg-primary-200/30 blur-3xl dark:bg-primary-800/20" />
        <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-accent-200/30 blur-3xl dark:bg-accent-800/20" />
      </div>

      {/* 卡片容器 */}
      <div className="relative w-full max-w-[420px]">
        {/* Logo 区域 */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-primary text-2xl font-bold text-white shadow-primary">
            星
          </div>
          <h1 className="text-[22px] font-bold text-gray-800 dark:text-gray-100">
            星禾写作助手
          </h1>
          <p className="mt-2 text-[14px] text-gray-500 dark:text-gray-400">
            AI 驱动的智能写作平台
          </p>
        </div>

        {/* 白色卡片 */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-[0_4px_24px_rgba(0,0,0,0.06)] dark:border-gray-700 dark:bg-dark-surface sm:p-8">
          {/* Tab 切换 */}
          <div className="mb-6 flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
            <button
              className={`flex-1 rounded-md py-2 text-[14px] font-semibold transition-all duration-150 ${
                tab === 'login'
                  ? 'bg-white text-primary-500 shadow-sm dark:bg-dark-surface dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
              onClick={() => handleTabChange('login')}
              type="button"
            >
              <span className="inline-flex items-center gap-1.5">
                <LogIn size={16} />
                登录
              </span>
            </button>
            <button
              className={`flex-1 rounded-md py-2 text-[14px] font-semibold transition-all duration-150 ${
                tab === 'register'
                  ? 'bg-white text-primary-500 shadow-sm dark:bg-dark-surface dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
              onClick={() => handleTabChange('register')}
              type="button"
            >
              <span className="inline-flex items-center gap-1.5">
                <UserPlus size={16} />
                注册
              </span>
            </button>
          </div>

          {/* 错误提示 */}
          {displayError && (
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-[13px] text-red-600 dark:bg-red-900/30 dark:text-red-400">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          {/* 登录表单 */}
          {tab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              {/* 用户名 */}
              <div>
                <label
                  htmlFor="login-username"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  用户名
                </label>
                <div className="relative">
                  <User
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="login-username"
                    className="input pl-10"
                    type="text"
                    value={username}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setUsername(e.target.value)
                    }
                    placeholder="请输入用户名"
                    autoComplete="username"
                    autoFocus
                  />
                </div>
              </div>

              {/* 密码 */}
              <div>
                <label
                  htmlFor="login-password"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  密码
                </label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="login-password"
                    className="input pl-10 pr-10"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setPassword(e.target.value)
                    }
                    placeholder="请输入密码"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    onClick={() => setShowPassword((prev: boolean) => !prev)}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* 提交按钮 */}
              <button
                className="btn-primary btn-lg w-full mt-2"
                type="submit"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    登录中…
                  </>
                ) : (
                  <>
                    <LogIn size={18} />
                    登录
                  </>
                )}
              </button>
            </form>
          )}

          {/* 注册表单 */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              {/* 用户名 */}
              <div>
                <label
                  htmlFor="reg-username"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  用户名
                </label>
                <div className="relative">
                  <User
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="reg-username"
                    className="input pl-10"
                    type="text"
                    value={username}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setUsername(e.target.value)
                    }
                    placeholder="请输入用户名"
                    autoComplete="username"
                    autoFocus
                  />
                </div>
              </div>

              {/* 邮箱 */}
              <div>
                <label
                  htmlFor="reg-email"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  邮箱
                </label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="reg-email"
                    className="input pl-10"
                    type="email"
                    value={email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setEmail(e.target.value)
                    }
                    placeholder="请输入邮箱"
                    autoComplete="email"
                  />
                </div>
              </div>

              {/* 密码 */}
              <div>
                <label
                  htmlFor="reg-password"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  密码
                </label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="reg-password"
                    className="input pl-10 pr-10"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setPassword(e.target.value)
                    }
                    placeholder="至少 6 位密码"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    onClick={() => setShowPassword((prev: boolean) => !prev)}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* 确认密码 */}
              <div>
                <label
                  htmlFor="reg-password-confirm"
                  className="mb-1.5 block text-[13px] font-semibold text-gray-500 dark:text-gray-400"
                >
                  确认密码
                </label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="reg-password-confirm"
                    className="input pl-10 pr-10"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={passwordConfirm}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setPasswordConfirm(e.target.value)
                    }
                    placeholder="再次输入密码"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    onClick={() =>
                      setShowConfirmPassword((prev: boolean) => !prev)
                    }
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? (
                      <EyeOff size={16} />
                    ) : (
                      <Eye size={16} />
                    )}
                  </button>
                </div>
              </div>

              {/* 提交按钮 */}
              <button
                className="btn-primary btn-lg w-full mt-2"
                type="submit"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    注册中…
                  </>
                ) : (
                  <>
                    <UserPlus size={18} />
                    注册
                  </>
                )}
              </button>
            </form>
          )}
        </div>

        {/* 底部链接 */}
        <p className="mt-6 text-center text-[12px] text-gray-400 dark:text-gray-500">
          星禾写作助手 v7.0 · AI 驱动的智能写作平台
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
