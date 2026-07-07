/**
 * 项目选择状态管理 — Zustand Store
 *
 * 存储当前用户选中的项目 ID，供侧边栏、快捷面板、设置页
 * 等全局组件使用，确保导航链接能正确拼接 projectId 参数。
 *
 * 持久化到 localStorage，刷新页面后保留选中状态。
 */
import { create } from 'zustand';

export interface ProjectStore {
  /** 当前选中的项目 ID，null 表示未选中任何项目 */
  selectedProjectId: string | null;

  /** 设置当前选中的项目 ID，同时持久化到 localStorage */
  setSelectedProjectId: (id: string | null) => void;
}

/** 从 localStorage 恢复上次选中的项目 */
const getInitialProjectId = (): string | null => {
  try {
    return localStorage.getItem('novelcraft-selected-project');
  } catch {
    return null;
  }
};

export const useProjectStore = create<ProjectStore>((set) => ({
  selectedProjectId: getInitialProjectId(),

  setSelectedProjectId: (id: string | null): void => {
    try {
      if (id) {
        localStorage.setItem('novelcraft-selected-project', id);
      } else {
        localStorage.removeItem('novelcraft-selected-project');
      }
    } catch {
      // localStorage 不可用时静默忽略
    }
    set({ selectedProjectId: id });
  },
}));
