/**
 * 主题状态管理 — Zustand Store
 * 管理亮色/暗色模式，支持系统偏好 + 手动覆盖
 */
import { create } from 'zustand';

interface ThemeState {
  isDark: boolean;

  /** 切换暗色模式 */
  toggle: () => void;
  /** 设置暗色模式 */
  setDark: (dark: boolean) => void;
}

/** 从系统偏好或 localStorage 初始化 */
const initDark = (): boolean => {
  try {
    const saved: string | null = localStorage.getItem('novelcraft-theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch {
    return false;
  }
};

/** 应用主题到 DOM */
const applyTheme = (dark: boolean): void => {
  try {
    localStorage.setItem('novelcraft-theme', dark ? 'dark' : 'light');
    if (dark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch {
    // DOM 操作失败时静默处理
  }
};

export const useThemeStore = create<ThemeState>((set, get) => ({
  isDark: initDark(),

  toggle: (): void => {
    const next: boolean = !get().isDark;
    applyTheme(next);
    set({ isDark: next });
  },

  setDark: (dark: boolean): void => {
    applyTheme(dark);
    set({ isDark: dark });
  },
}));
