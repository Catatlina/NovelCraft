/**
 * 认证状态管理 — Zustand Store
 * 管理用户登录/注册/登出及 token 持久化
 */
import { create } from 'zustand';
import type { User, LoginRequest, RegisterRequest } from '@/types';
import { authLogin, authRegister, authLogout, authMe } from '@/api/endpoints';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  /** 登录 */
  login: (data: LoginRequest) => Promise<void>;
  /** 注册 */
  register: (data: RegisterRequest) => Promise<void>;
  /** 登出 */
  logout: () => Promise<void>;
  /** 从 localStorage 恢复认证状态 */
  checkAuth: () => Promise<void>;
  /** 清除错误 */
  clearError: () => void;
  /** 直接设置 token（用于 OAuth 等场景） */
  setToken: (token: string, user: User) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('novelcraft-token'),
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (data: LoginRequest): Promise<void> => {
    set({ isLoading: true, error: null });
    try {
      const res = await authLogin(data);
      localStorage.setItem('novelcraft-token', res.access_token);
      set({
        user: res.user,
        token: res.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message: string =
        err instanceof Error ? err.message : '登录失败';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  register: async (data: RegisterRequest): Promise<void> => {
    set({ isLoading: true, error: null });
    try {
      const res = await authRegister(data);
      localStorage.setItem('novelcraft-token', res.access_token);
      set({
        user: res.user,
        token: res.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message: string =
        err instanceof Error ? err.message : '注册失败';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: async (): Promise<void> => {
    try {
      await authLogout();
    } catch {
      // 即使远端登出失败，也要清除本地状态
    }
    localStorage.removeItem('novelcraft-token');
    set({ user: null, token: null, isAuthenticated: false, error: null });
  },

  checkAuth: async (): Promise<void> => {
    const token: string | null = get().token || localStorage.getItem('novelcraft-token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    // 开发模式：无需 API 验证，直接视为已认证
    if (import.meta.env.DEV) {
      set({ user: { id: 'dev', username: '开发者', email: 'dev@local' } as User, isAuthenticated: true, isLoading: false, token });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('novelcraft-token');
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: (): void => {
    set({ error: null });
  },

  setToken: (token: string, user: User): void => {
    localStorage.setItem('novelcraft-token', token);
    set({ token, user, isAuthenticated: true });
  },
}));
