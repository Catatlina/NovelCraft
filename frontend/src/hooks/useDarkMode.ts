import { useState, useEffect, useCallback } from 'react';

/**
 * 暗色模式 Hook
 * - 初始化：从 localStorage 读取，fallback 到系统偏好
 * - 切换：更新 html class/data-theme + localStorage
 * - 自动监听系统偏好变化
 */
export function useDarkMode(): {
  isDark: boolean;
  toggle: () => void;
  setDark: (dark: boolean) => void;
} {
  const [isDark, setIsDark] = useState<boolean>(() => {
    try {
      const saved: string | null = localStorage.getItem('novelcraft-theme');
      if (saved) return saved === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch {
      return false;
    }
  });

  // 应用主题到 DOM
  const apply = useCallback((dark: boolean): void => {
    try {
      localStorage.setItem('novelcraft-theme', dark ? 'dark' : 'light');
      if (dark) {
        document.documentElement.classList.add('dark');
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.removeAttribute('data-theme');
      }
    } catch {
      // DOM 不可用时静默失败
    }
  }, []);

  // 手动切换
  const toggle = useCallback((): void => {
    setIsDark((prev: boolean) => {
      const next: boolean = !prev;
      apply(next);
      return next;
    });
  }, [apply]);

  // 手动设置
  const setDark = useCallback(
    (dark: boolean): void => {
      setIsDark(dark);
      apply(dark);
    },
    [apply],
  );

  // 监听系统偏好变化（仅在用户未手动设置时生效）
  useEffect(() => {
    const mq: MediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent): void => {
      const saved: string | null = localStorage.getItem('novelcraft-theme');
      if (!saved) {
        setIsDark(e.matches);
        apply(e.matches);
      }
    };

    mq.addEventListener('change', handleChange);
    return () => mq.removeEventListener('change', handleChange);
  }, [apply]);

  return { isDark, toggle, setDark };
}
