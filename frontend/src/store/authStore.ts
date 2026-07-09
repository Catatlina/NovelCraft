/**
 * 认证状态管理 — Zustand Store
 * 使用 httpOnly cookie 认证，不存储 JWT 到 localStorage
 */
import { create } from 'zustand';
import type { User, LoginRequest, RegisterRequest } from '@/types';
import { authLogin, authRegister, authLogout, authMe } from '@/api/endpoints';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (data: LoginRequest): Promise<void> => {
    set({ isLoading: true, error: null });
    try {
      const res = await authLogin(data);
      set({
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message: string = err instanceof Error ? err.message : '登录失败';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  register: async (data: RegisterRequest): Promise<void> => {
    set({ isLoading: true, error: null });
    try {
      const res = await authRegister(data);
      set({
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message: string = err instanceof Error ? err.message : '注册失败';
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
    set({ user: null, isAuthenticated: false, error: null });
  },

  checkAuth: async (): Promise<void> => {
    // 显式 feature flag：仅在明确设置时跳过认证
    const bypass = import.meta.env.DEV && false && import.meta.env.VITE_AUTH_BYPASS === 'true';
    if (bypass) {
      set({
        user: { id: 'dev', username: '开发者', email: 'dev@local' } as User,
        isAuthenticated: true,
        isLoading: false,
      });
      return;
    }

    set({ isLoading: true });
    try {
      const user = await authMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: (): void => {
    set({ error: null });
  },
}));
